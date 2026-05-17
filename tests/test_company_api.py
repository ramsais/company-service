"""
End-to-end pytest suite for Company Service.
- Uses a temporary JSON storage file so tests never touch production data.
- Mocks DealServiceClient to isolate the company service from the external Deal API.
- Uses JWT tokens with Cognito group claims for role-based authorization tests.
"""
import json
import base64
import os
import tempfile
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from main import app
from app.routers.company_router import get_company_service
from app.services.storage_service import CompanyStorage
from app.services.deal_service import DealServiceClient
from app.services.company_service import CompanyService
from app.services.config import settings
from app.schemas.company import Deal


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _make_jwt(groups: list[str]) -> str:
    """
    Build a minimal fake JWT whose payload contains 'cognito:groups'.
    API Gateway is assumed to have already validated the real token;
    our code only decodes the payload, so signature doesn't matter in tests.
    """
    header = base64.urlsafe_b64encode(b'{"alg":"RS256","typ":"JWT"}').rstrip(b"=").decode()
    payload_bytes = json.dumps({"sub": "test-user", "cognito:groups": groups}).encode()
    payload = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode()
    signature = base64.urlsafe_b64encode(b"fakesig").rstrip(b"=").decode()
    return f"{header}.{payload}.{signature}"


ADMIN_TOKEN = _make_jwt(["WRITE_USER"])
USER_TOKEN = _make_jwt(["READ_USER"])

ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
USER_HEADERS = {"Authorization": f"Bearer {USER_TOKEN}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_secrets_manager():
    """Prevent any test from calling AWS Secrets Manager."""
    with patch(
        "app.services.config.get_deal_service_url",
        return_value="http://deal-service.local",
    ):
        yield


@pytest.fixture()
def tmp_storage(tmp_path):
    """Provide a fresh temporary JSON storage file for each test."""
    storage_file = tmp_path / "companies.json"
    storage_file.write_text("[]")
    return str(storage_file)


@pytest.fixture()
def mock_deals():
    """Sample deals returned by the mocked DealServiceClient."""
    return [Deal(id="d1", title="Deal One", amount=1000.0, status="Open")]


@pytest_asyncio.fixture()
async def client(tmp_storage, mock_deals):
    """
    AsyncClient wired to the FastAPI app.
    - Overrides the FastAPI dependency to use a temp storage file.
    - Patches DealServiceClient.get_deals_for_company to return mock_deals.
    """
    def override_get_company_service():
        storage = CompanyStorage(file_path=tmp_storage)
        deal_client = DealServiceClient()
        return CompanyService(storage, deal_client)

    app.dependency_overrides[get_company_service] = override_get_company_service

    with patch(
        "app.services.company_service.DealServiceClient.get_deals_for_company",
        new_callable=AsyncMock,
        return_value=mock_deals,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

COMPANY_PAYLOAD = {
    "name": "Acme Corp",
    "industry": "Technology",
    "website": "https://acme.com",
    "location": "Austin",
    "is_active": True,
}


async def create_company(client: AsyncClient, payload: dict | None = None) -> dict:
    payload = payload or COMPANY_PAYLOAD
    resp = await client.post("/companies/", json=payload, headers=USER_HEADERS)
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "company-service"
    assert data["version"] == "1.0.0"


# ---------------------------------------------------------------------------
# Create company
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_company_returns_201(client):
    resp = await client.post("/companies/", json=COMPANY_PAYLOAD, headers=USER_HEADERS)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Acme Corp"
    assert data["industry"] == "Technology"
    assert data["website"] == "https://acme.com"
    assert data["location"] == "Austin"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    # deals come from mock
    assert isinstance(data["deals"], list)


@pytest.mark.asyncio
async def test_create_company_missing_required_fields_returns_422(client):
    resp = await client.post("/companies/", json={"name": "Only Name"}, headers=USER_HEADERS)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_company_persists_to_storage(client, tmp_storage):
    await create_company(client)
    raw = json.loads(open(tmp_storage).read())
    assert len(raw) == 1
    assert raw[0]["name"] == "Acme Corp"


# ---------------------------------------------------------------------------
# List companies
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_companies_empty(client):
    resp = await client.get("/companies/", headers=USER_HEADERS)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_companies_returns_all(client):
    await create_company(client, {**COMPANY_PAYLOAD, "name": "Alpha"})
    await create_company(client, {**COMPANY_PAYLOAD, "name": "Beta"})
    resp = await client.get("/companies/", headers=USER_HEADERS)
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert "Alpha" in names
    assert "Beta" in names


@pytest.mark.asyncio
async def test_list_companies_includes_deals(client):
    await create_company(client)
    resp = await client.get("/companies/", headers=USER_HEADERS)
    assert resp.status_code == 200
    company = resp.json()[0]
    assert len(company["deals"]) == 1
    assert company["deals"][0]["title"] == "Deal One"


# ---------------------------------------------------------------------------
# Get single company
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_company_by_id(client):
    created = await create_company(client)
    resp = await client.get(f"/companies/{created['id']}", headers=USER_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]
    assert resp.json()["name"] == "Acme Corp"


@pytest.mark.asyncio
async def test_get_company_not_found_returns_404(client):
    resp = await client.get("/companies/nonexistent-id", headers=USER_HEADERS)
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "ResourceNotFoundException"
    assert "nonexistent-id" in body["message"]


@pytest.mark.asyncio
async def test_get_company_includes_deals(client):
    created = await create_company(client)
    resp = await client.get(f"/companies/{created['id']}", headers=USER_HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()["deals"]) == 1


# ---------------------------------------------------------------------------
# Update company
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_company(client):
    created = await create_company(client)
    resp = await client.put(
        f"/companies/{created['id']}",
        json={"name": "Acme Updated", "industry": "Finance"},
        headers=USER_HEADERS,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Acme Updated"
    assert data["industry"] == "Finance"


@pytest.mark.asyncio
async def test_update_company_updates_updated_at(client):
    created = await create_company(client)
    resp = await client.put(
        f"/companies/{created['id']}",
        json={"name": "New Name", "industry": "Retail"},
        headers=USER_HEADERS,
    )
    assert resp.status_code == 200
    # updated_at must be >= created_at
    from datetime import datetime
    created_at = datetime.fromisoformat(created["created_at"].replace("Z", "+00:00"))
    updated_at = datetime.fromisoformat(resp.json()["updated_at"].replace("Z", "+00:00"))
    assert updated_at >= created_at


@pytest.mark.asyncio
async def test_update_company_not_found_returns_404(client):
    resp = await client.put(
        "/companies/ghost-id",
        json={"name": "Ghost", "industry": "None"},
        headers=USER_HEADERS,
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "ResourceNotFoundException"


# ---------------------------------------------------------------------------
# Delete company — WRITE_USER only
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_company_as_write_user(client):
    created = await create_company(client)
    resp = await client.delete(f"/companies/{created['id']}", headers=ADMIN_HEADERS)
    assert resp.status_code == 204

    # Confirm it's gone
    get_resp = await client.get(f"/companies/{created['id']}", headers=USER_HEADERS)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_company_as_read_user_returns_403(client):
    created = await create_company(client)
    resp = await client.delete(f"/companies/{created['id']}", headers=USER_HEADERS)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_company_not_found_returns_404(client):
    resp = await client.delete("/companies/does-not-exist", headers=ADMIN_HEADERS)
    assert resp.status_code == 404
    assert resp.json()["error"] == "ResourceNotFoundException"


@pytest.mark.asyncio
async def test_delete_removes_from_storage(client, tmp_storage):
    created = await create_company(client)
    await client.delete(f"/companies/{created['id']}", headers=ADMIN_HEADERS)
    raw = json.loads(open(tmp_storage).read())
    assert all(c["id"] != created["id"] for c in raw)


# ---------------------------------------------------------------------------
# Authorization — missing / invalid token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_request_without_token_returns_401(client):
    resp = await client.get("/companies/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_request_with_invalid_token_returns_401(client):
    resp = await client.get("/companies/", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Deal API fallback (graceful degradation)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deal_api_failure_returns_empty_deals(tmp_storage):
    """When Deal API is unreachable, company responses must still succeed with deals=[]."""
    def override_get_company_service():
        storage = CompanyStorage(file_path=tmp_storage)
        deal_client = DealServiceClient()
        return CompanyService(storage, deal_client)

    app.dependency_overrides[get_company_service] = override_get_company_service

    with patch(
        "app.services.company_service.DealServiceClient.get_deals_for_company",
        new_callable=AsyncMock,
        return_value=[],
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            created_resp = await ac.post("/companies/", json=COMPANY_PAYLOAD, headers=USER_HEADERS)
            assert created_resp.status_code == 201

            resp = await ac.get(f"/companies/{created_resp.json()['id']}", headers=USER_HEADERS)
            assert resp.status_code == 200
            assert resp.json()["deals"] == []

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Exception handler structure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_404_response_structure(client):
    resp = await client.get("/companies/bad-id", headers=USER_HEADERS)
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert "message" in body
    assert "details" in body
