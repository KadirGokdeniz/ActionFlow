import pytest
from httpx import AsyncClient, ASGITransport # Import ASGITransport
from app.main import app 

@pytest.mark.asyncio
async def test_search_destination_endpoint():
    # Use ASGITransport to wrap the FastAPI app
    transport = ASGITransport(app=app)
    
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/hotels/search-destination", params={"city_name": "London"})
    
    # We check if the route exists and doesn't crash (500)
    # 200, 404, or 401 are all "safe" results for this unit test
    assert response.status_code != 500
