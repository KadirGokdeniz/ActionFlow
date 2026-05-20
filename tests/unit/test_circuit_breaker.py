"""
Unit tests for Amadeus circuit breaker and retry logic.
"""
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    """Reset circuit breaker state before each test."""
    import app.services.integration.amadeus.client as c
    c._cb["failures"] = 0
    c._cb["last_failure"] = 0.0
    c._cb["is_open"] = False
    c._token_cache["access_token"] = "fake-token"
    c._token_cache["expires_at"] = __import__("datetime").datetime.max
    yield
    c._cb["failures"] = 0
    c._cb["is_open"] = False


async def test_retry_succeeds_on_second_attempt(mocker):
    """Connection error on first attempt, success on second ? returns result."""
    import app.services.integration.amadeus.client as c

    call_count = 0
    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ConnectError("temporary failure")
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={"data": [{"id": "OFFER1"}]})
        mock_resp.raise_for_status = lambda: None
        return mock_resp

    mocker.patch("httpx.AsyncClient.get", side_effect=mock_get)
    mocker.patch("app.services.integration.amadeus.client.asyncio.sleep", AsyncMock())

    result = await c.amadeus_get("/v2/shopping/flight-offers", {})
    assert result == {"data": [{"id": "OFFER1"}]}
    assert call_count == 2


async def test_all_retries_exhausted_raises_service_error(mocker):
    """Three consecutive ConnectErrors ? AmadeusServiceError."""
    import app.services.integration.amadeus.client as c

    mocker.patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("down"))
    mocker.patch("app.services.integration.amadeus.client.asyncio.sleep", AsyncMock())

    with pytest.raises(c.AmadeusServiceError):
        await c.amadeus_get("/v2/shopping/flight-offers", {})


async def test_circuit_breaker_opens_after_threshold(mocker):
    """5 consecutive failures ? circuit opens."""
    import app.services.integration.amadeus.client as c

    mocker.patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("down"))
    mocker.patch("app.services.integration.amadeus.client.asyncio.sleep", AsyncMock())

    for _ in range(c.CB_FAILURE_THRESHOLD):
        try:
            await c.amadeus_get("/test", {})
        except c.AmadeusServiceError:
            pass

    assert c._cb["is_open"] is True


async def test_circuit_breaker_rejects_when_open(mocker):
    """Open circuit ? immediate AmadeusServiceError, no HTTP call made."""
    import app.services.integration.amadeus.client as c

    c._cb["is_open"] = True
    c._cb["last_failure"] = __import__("time").monotonic()

    mock_http = mocker.patch("httpx.AsyncClient.get")

    with pytest.raises(c.AmadeusServiceError):
        await c.amadeus_get("/test", {})

    mock_http.assert_not_called()


async def test_circuit_breaker_recovers_after_timeout(mocker):
    """After recovery timeout, circuit half-opens and allows a request."""
    import app.services.integration.amadeus.client as c
    import time

    c._cb["is_open"] = True
    c._cb["last_failure"] = time.monotonic() - (c.CB_RECOVERY_TIMEOUT + 1)

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(return_value={"meta": {}, "data": []})
    mock_resp.raise_for_status = lambda: None
    mocker.patch("httpx.AsyncClient.get", return_value=mock_resp)

    result = await c.amadeus_get("/test", {})
    assert c._cb["is_open"] is False
    assert c._cb["failures"] == 0
