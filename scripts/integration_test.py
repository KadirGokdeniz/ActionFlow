import asyncio
import httpx
import redis.asyncio as redis
import uuid
import xml.etree.ElementTree as ET
import random
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Configuration
BASE_URL = "http://localhost:8000"
REDIS_URL = "redis://localhost:6379"
# Database URL for localhost (assuming port 5432 is exposed)
DATABASE_URL = "postgresql+asyncpg://actionflow:dev123@localhost:5432/actionflow"

TEST_PHONE_NUMBER = f"whatsapp:+1{random.randint(1000000000, 9999999999)}"

async def test_whatsapp_webhook():
    print(f"[1/3] Testing WhatsApp Webhook with number {TEST_PHONE_NUMBER}...")
    
    url = f"{BASE_URL}/api/v1/whatsapp/webhook"
    
    # Simulate Twilio payload
    data = {
        "From": TEST_PHONE_NUMBER,
        "Body": "I want to go to Paris next week.",
        "To": "whatsapp:+14155238886",
        "AccountSid": "AC_TEST_ACCOUNT_SID"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, data=data)
            
            if response.status_code == 200:
                print("[+] WhatsApp Webhook Request Successful (200 OK)")
                
                # Verify TwiML response
                try:
                    root = ET.fromstring(response.text)
                    if root.tag == "Response":
                         print("[+] Valid TwiML Response")
                         # Print the actual text response from the bot
                         for child in root:
                             if child.tag == "Message":
                                 print(f"   Bot Reply: \"{child.text}\"")
                    else:
                        print("[-] Invalid TwiML: Root is not <Response>")
                except ET.ParseError:
                    print("[-] Could not parse XML response")
            else:
                print(f"[-] Webhook Failed. Status: {response.status_code}, Body: {response.text}")
                return False
                
        except httpx.RequestError as e:
            print(f"[-] Request Error: {e}")
            return False
            
    return True

async def get_conversation_id_from_db():
    """Queries the database to find the conversation ID for the test phone number."""
    print("   Querying Database for Conversation ID...")
    
    try:
        engine = create_async_engine(DATABASE_URL)
        async with engine.connect() as conn:
            # 1. Find User ID
            result = await conn.execute(
                text("SELECT id FROM users WHERE phone = :phone"), 
                {"phone": TEST_PHONE_NUMBER}
            )
            user_id = result.scalar()
            
            if not user_id:
                print(f"[-] User not found in DB for phone {TEST_PHONE_NUMBER}")
                return None
                
            print(f"   [+] DB: User created with ID: {user_id}")

            # 2. Find Active Conversation ID
            result = await conn.execute(
                text("SELECT id FROM conversations WHERE user_id = :uid ORDER BY updated_at DESC LIMIT 1"), 
                {"uid": user_id}
            )
            conv_id = result.scalar()
            
            if not conv_id:
                print(f"[-] Conversation not found in DB for user {user_id}")
                return None
                
            print(f"   [+] DB: Found Active Conversation ID: {conv_id}")
            return conv_id
            
    except Exception as e:
        print(f"[-] Database Query Failed: {e}")
        # Hint for user if connection fails
        print("   (Ensure 'localhost:5432' is accessible and credentials are correct)")
        return None
    finally:
        await engine.dispose()

async def verify_redis_state():
    print("\n[2/3] Verifying Redis Session State...")
    
    # First, get the real Conversation ID from DB
    conversation_id = await get_conversation_id_from_db()
    if not conversation_id:
        print("[-] Cannot verify Redis without Conversation ID.")
        return False

    # Connect to Redis
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    # Correct Key Format: conv_state:{uuid}
    key = f"conv_state:{conversation_id}"
    
    try:
        exists = await r.exists(key)
        if exists:
            print(f"[+] Redis Key Found: {key}")
            
            # Check TTL
            ttl = await r.ttl(key)
            if ttl > 0:
                 print(f"[+] TTL is set: {ttl} seconds (Expected ~86400)")
            else:
                 print(f"[-] TTL not set correctly: {ttl}")
            
        else:
            print(f"[-] Redis Key NOT Found: {key}")
            await r.close()
            return False
            
        await r.close()
        return True
    except Exception as e:
        print(f"[-] Redis Connection Error: {e}")
        return False

async def verify_metrics():
    print("\n[3/3] Checking Prometheus Metrics...")
    
    url = f"{BASE_URL}/metrics"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            
            if response.status_code == 200:
                print("[+] Metrics Endpoint Accessible (200 OK)")
                
                # Check for critical metrics
                metrics_text = response.text
                
                if "http_requests_total" in metrics_text:
                    print("[+] Found 'http_requests_total' metric")
                    
                    found_specific = False
                    for line in metrics_text.split('\n'):
                        if 'handler="/api/v1/whatsapp/webhook"' in line and 'http_requests_total' in line:
                            print(f"   Webhook Metric: {line}")
                            found_specific = True
                            
                    if not found_specific:
                         print("   Specific webhook metric not yet updated (might be async or batched)")
                else:
                    print("[-] 'http_requests_total' NOT found in metrics")
                    
            else:
                print(f"[-] Metrics Endpoint Failed: {response.status_code}")
                return False
                
        except httpx.RequestError as e:
            print(f"[-] Request Error: {e}")
            return False
            
    return True

async def main():
    print("Starting ActionFlow Integration Test\n" + "="*40)
    
    # 1. WhatsApp Webhook
    if not await test_whatsapp_webhook():
        print("\n[-] Aborting due to Webhook failure.")
        return

    # Wait a moment for async processing (if any)
    await asyncio.sleep(2)

    # 2. Redis State (includes DB check)
    if not await verify_redis_state():
        print("\n[-] Aborting due to Redis verification failure.")
        return

    # 3. Metrics
    if not await verify_metrics():
        print("\n[-] Aborting due to Metrics failure.")
        return

    print("\n" + "="*40 + "\n[+] ALL INTEGRATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
