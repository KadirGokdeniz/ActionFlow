"""
ActionFlow AI - Prometheus Metrics
Request latency, agent performance, end-to-end tracking

Metrics:
- http_requests_total: Total HTTP requests
- http_request_duration_seconds: Request latency histogram
- actionflow_agent_duration_seconds: Agent execution time
- actionflow_agent_calls_total: Agent call counts
- actionflow_end_to_end_latency_seconds: Full conversation turn latency
- actionflow_active_sessions: Current active sessions
- actionflow_external_api_duration_seconds: External API latencies
"""

import time
import logging
from typing import Callable, Optional
from functools import wraps
from contextlib import contextmanager

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY
)
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("ActionFlow-Metrics")

# ═══════════════════════════════════════════════════════════════════
# METRIC DEFINITIONS
# ═══════════════════════════════════════════════════════════════════

# HTTP Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Agent Metrics
AGENT_DURATION = Histogram(
    "actionflow_agent_duration_seconds",
    "Agent execution duration in seconds",
    ["agent"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
)

AGENT_CALLS = Counter(
    "actionflow_agent_calls_total",
    "Total agent calls",
    ["agent", "status"]
)

# End-to-End Metrics
END_TO_END_LATENCY = Histogram(
    "actionflow_end_to_end_latency_seconds",
    "End-to-end conversation turn latency",
    ["channel"],  # web, whatsapp, voice
    buckets=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.5, 10.0]
)

# Session Metrics
ACTIVE_SESSIONS = Gauge(
    "actionflow_active_sessions",
    "Number of active sessions",
    ["channel"]
)

# External API Metrics
EXTERNAL_API_DURATION = Histogram(
    "actionflow_external_api_duration_seconds",
    "External API call duration",
    ["service"],  # amadeus, openai, assemblyai, elevenlabs
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0]
)

EXTERNAL_API_CALLS = Counter(
    "actionflow_external_api_calls_total",
    "Total external API calls",
    ["service", "status"]
)

# Tool Metrics
TOOL_DURATION = Histogram(
    "actionflow_tool_duration_seconds",
    "MCP tool execution duration",
    ["tool"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

TOOL_CALLS = Counter(
    "actionflow_tool_calls_total",
    "Total tool calls",
    ["tool", "status"]
)


# ═══════════════════════════════════════════════════════════════════
# MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic request metrics
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        method = request.method
        # Normalize endpoint (remove IDs)
        endpoint = self._normalize_path(request.url.path)
        
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            status = str(response.status_code)
        except Exception as e:
            status = "500"
            raise
        finally:
            duration = time.perf_counter() - start_time
            
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()
            
            HTTP_REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path by replacing IDs with placeholders
        /api/v1/bookings/BK12345678 → /api/v1/bookings/{id}
        """
        import re
        
        # Replace UUIDs
        path = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '{uuid}', path)
        
        # Replace booking IDs (BK + 8 chars)
        path = re.sub(r'BK[A-Z0-9]{8}', '{booking_id}', path)
        
        # Replace numeric IDs
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        
        return path


# ═══════════════════════════════════════════════════════════════════
# CONTEXT MANAGERS & DECORATORS
# ═══════════════════════════════════════════════════════════════════

@contextmanager
def track_agent_duration(agent_name: str):
    """
    Context manager to track agent execution time
    
    Usage:
        with track_agent_duration("supervisor"):
            result = await supervisor_node(state)
    """
    start_time = time.perf_counter()
    status = "success"
    
    try:
        yield
    except Exception as e:
        status = "error"
        raise
    finally:
        duration = time.perf_counter() - start_time
        AGENT_DURATION.labels(agent=agent_name).observe(duration)
        AGENT_CALLS.labels(agent=agent_name, status=status).inc()
        
        if duration > 3.0:
            logger.warning(f"⚠️ Slow agent execution: {agent_name} took {duration:.2f}s")


@contextmanager
def track_end_to_end(channel: str = "web"):
    """
    Context manager to track end-to-end latency
    
    Usage:
        with track_end_to_end("voice"):
            response = await process_message(message)
    """
    start_time = time.perf_counter()
    
    try:
        yield
    finally:
        duration = time.perf_counter() - start_time
        END_TO_END_LATENCY.labels(channel=channel).observe(duration)
        
        if duration > 3.0:
            logger.warning(f"⚠️ High end-to-end latency: {channel} took {duration:.2f}s")


@contextmanager
def track_external_api(service: str):
    """
    Context manager to track external API calls
    
    Usage:
        with track_external_api("amadeus"):
            response = await amadeus_client.search_flights(...)
    """
    start_time = time.perf_counter()
    status = "success"
    
    try:
        yield
    except Exception as e:
        status = "error"
        raise
    finally:
        duration = time.perf_counter() - start_time
        EXTERNAL_API_DURATION.labels(service=service).observe(duration)
        EXTERNAL_API_CALLS.labels(service=service, status=status).inc()


@contextmanager
def track_tool_call(tool_name: str):
    """
    Context manager to track MCP tool execution
    
    Usage:
        with track_tool_call("search_flights"):
            result = await mcp_client.call_tool("search_flights", args)
    """
    start_time = time.perf_counter()
    status = "success"
    
    try:
        yield
    except Exception as e:
        status = "error"
        raise
    finally:
        duration = time.perf_counter() - start_time
        TOOL_DURATION.labels(tool=tool_name).observe(duration)
        TOOL_CALLS.labels(tool=tool_name, status=status).inc()


def track_agent(agent_name: str):
    """
    Decorator to track agent execution
    
    Usage:
        @track_agent("supervisor")
        async def supervisor_node(state):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            with track_agent_duration(agent_name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════
# SESSION TRACKING
# ═══════════════════════════════════════════════════════════════════

def increment_active_sessions(channel: str = "web"):
    """Increment active session count"""
    ACTIVE_SESSIONS.labels(channel=channel).inc()


def decrement_active_sessions(channel: str = "web"):
    """Decrement active session count"""
    ACTIVE_SESSIONS.labels(channel=channel).dec()


def set_active_sessions(channel: str, count: int):
    """Set active session count directly"""
    ACTIVE_SESSIONS.labels(channel=channel).set(count)


# ═══════════════════════════════════════════════════════════════════
# METRICS ENDPOINT
# ═══════════════════════════════════════════════════════════════════

async def metrics_endpoint():
    """
    Prometheus metrics endpoint
    Returns metrics in Prometheus text format
    """
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )


# ═══════════════════════════════════════════════════════════════════
# SETUP FUNCTION
# ═══════════════════════════════════════════════════════════════════

def setup_metrics(app):
    """
    Setup Prometheus metrics for FastAPI app
    
    Usage in main.py:
        from app.core.metrics import setup_metrics
        setup_metrics(app)
    """
    from fastapi import FastAPI
    
    # Add middleware
    app.add_middleware(PrometheusMiddleware)
    
    # Add metrics endpoint
    app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], tags=["Monitoring"])
    
    logger.info("✅ Prometheus metrics enabled at /metrics")


# ═══════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════

__all__ = [
    # Setup
    "setup_metrics",
    "PrometheusMiddleware",
    "metrics_endpoint",
    
    # Tracking
    "track_agent_duration",
    "track_end_to_end",
    "track_external_api",
    "track_tool_call",
    "track_agent",
    
    # Sessions
    "increment_active_sessions",
    "decrement_active_sessions",
    "set_active_sessions",
    
    # Raw metrics (for custom tracking)
    "HTTP_REQUESTS_TOTAL",
    "HTTP_REQUEST_DURATION",
    "AGENT_DURATION",
    "AGENT_CALLS",
    "END_TO_END_LATENCY",
    "ACTIVE_SESSIONS",
    "EXTERNAL_API_DURATION",
    "EXTERNAL_API_CALLS",
    "TOOL_DURATION",
    "TOOL_CALLS",
]
