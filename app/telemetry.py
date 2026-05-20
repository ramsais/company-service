"""
OpenTelemetry setup for CloudWatch Application Signals.

This module MUST be imported and configure_telemetry() called BEFORE the
FastAPI app object is created so that auto-instrumentation hooks are in place
before any routes or middleware are registered.

Trace propagation chain:
  API Gateway injects  →  X-Amzn-Trace-Id  (AWS X-Ray format)
  ALB passes through  →  all headers unchanged
  OTel SDK reads      →  AwsXRayPropagator parses X-Amzn-Trace-Id
  Span context set    →  trace_id / span_id available in every log line
  Outgoing httpx      →  HTTPXClientInstrumentor injects W3C + X-Ray headers
  Deal-service reads  →  same propagator reconstructs the span context
"""
import logging
import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.propagators.b3 import B3MultiFormat

# AWS X-Ray propagator — parses/generates X-Amzn-Trace-Id injected by API Gateway
try:
    from opentelemetry.propagators.aws import AwsXRayPropagator
    _AWS_PROPAGATOR_AVAILABLE = True
except ImportError:
    _AWS_PROPAGATOR_AVAILABLE = False

logger = logging.getLogger(__name__)

# ADOT Collector sidecar listens on gRPC 4317 inside the ECS task
_OTLP_ENDPOINT = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")


def configure_telemetry(service_name: str, service_version: str = "1.0.0") -> None:
    """
    Initialise the OTel SDK and wire it to the ADOT Collector sidecar.

    Call this ONCE at the very top of main.py, before `FastAPI()` is
    instantiated.  The function is idempotent — calling it twice is safe.

    Args:
        service_name:    Logical service name (e.g. "company-service").
                         Appears in CloudWatch Application Signals service map.
        service_version: Semver string; shown in Application Signals metadata.
    """
    # -----------------------------------------------------------------------
    # 1. Propagator — must be set BEFORE any instrumentation is activated
    #    AwsXRayPropagator reads/writes X-Amzn-Trace-Id so the trace chain
    #    from API Gateway is preserved end-to-end.
    # -----------------------------------------------------------------------
    if _AWS_PROPAGATOR_AVAILABLE:
        set_global_textmap(
            CompositePropagator([
                AwsXRayPropagator(),  # primary: API Gateway / ALB header
                B3MultiFormat(),      # fallback: inter-service calls
            ])
        )
    else:
        logger.warning(
            "opentelemetry-propagator-aws not installed; "
            "X-Amzn-Trace-Id from API Gateway will NOT be parsed. "
            "Install opentelemetry-propagator-aws to enable end-to-end tracing."
        )

    # -----------------------------------------------------------------------
    # 2. Resource — metadata attached to every span
    #    CloudWatch Application Signals uses SERVICE_NAME for the service map.
    # -----------------------------------------------------------------------
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "cloud.provider": "aws",
        "deployment.environment": os.getenv("ENVIRONMENT", "dev"),
    })

    # -----------------------------------------------------------------------
    # 3. Exporter → ADOT Collector sidecar (localhost:4317)
    #    The sidecar forwards spans to CloudWatch Application Signals and
    #    X-Ray trace storage simultaneously via its built-in config.
    # -----------------------------------------------------------------------
    exporter = OTLPSpanExporter(
        endpoint=_OTLP_ENDPOINT,
        insecure=True,  # local sidecar — no TLS needed
    )

    # -----------------------------------------------------------------------
    # 4. TracerProvider with BatchSpanProcessor
    #    Batch processor buffers spans and flushes asynchronously so the
    #    request path is not blocked by telemetry I/O.
    # -----------------------------------------------------------------------
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # -----------------------------------------------------------------------
    # 5. Auto-instrument httpx
    #    Every outgoing httpx request (inter-service calls via Cloud Map)
    #    will automatically inject trace-context headers so the receiving
    #    service can continue the same trace.
    # -----------------------------------------------------------------------
    HTTPXClientInstrumentor().instrument()

    logger.info(
        "otel_configured",
        extra={
            "service": service_name,
            "version": service_version,
            "otlp_endpoint": _OTLP_ENDPOINT,
            "aws_propagator": _AWS_PROPAGATOR_AVAILABLE,
        },
    )


def instrument_app(app, excluded_urls: str = "health") -> None:
    """
    Wire OTel auto-instrumentation to an existing FastAPI app instance.

    Call this AFTER `app = FastAPI(...)` is created.

    Args:
        app:           The FastAPI application instance.
        excluded_urls: Comma-separated URL patterns to skip (health checks).
                       Prevents health-poll spans from flooding trace storage.
    """
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls=excluded_urls,
        # tracer_provider is picked up automatically from the global provider
        # set in configure_telemetry().
    )
    logger.info(
        "fastapi_instrumented",
        extra={"excluded_urls": excluded_urls},
    )