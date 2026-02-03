"""
ActionFlow Orchestration Manual Test Script
============================================

Bu script, ActionFlow sistemini manuel olarak test etmek için kullanılır.
Otomatik pytest testlerinden farklı olarak, gerçek API endpoint'lerini kullanır.

Kullanım:
    python tests/test_orchestration_manual.py

Gereksinimler:
    - Docker containers ayakta olmalı
    - Backend API çalışıyor olmalı (http://localhost:8000)
"""

import asyncio
import json
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

API_BASE_URL = "http://localhost:8000/api/v1"
CUSTOMER_ID = f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


# ═══════════════════════════════════════════════════════════════════
# TEST UTILITIES
# ═══════════════════════════════════════════════════════════════════

class TestRunner:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0)
        self.conversation_id: Optional[str] = None
        self.test_results = []
        
    async def close(self):
        await self.client.aclose()
    
    def print_header(self, text: str):
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    def print_success(self, text: str):
        print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")
    
    def print_failure(self, text: str):
        print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")
    
    def print_info(self, text: str):
        print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")
    
    def print_warning(self, text: str):
        print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")
    
    async def send_message(
        self, 
        message: str, 
        conversation_id: Optional[str] = None,
        customer_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a chat message and return response"""
        payload = {
            "message": message,
            "customer_id": customer_id or CUSTOMER_ID,
        }
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        self.print_info(f"Sending: {message}")
        
        response = await self.client.post("/chat/", json=payload)
        
        if response.status_code != 200:
            self.print_failure(f"API Error: {response.status_code}")
            print(response.text)
            return {}
        
        data = response.json()
        
        # Update conversation_id if this is first message
        if not self.conversation_id and data.get("conversation_id"):
            self.conversation_id = data["conversation_id"]
            self.print_success(f"Conversation ID: {self.conversation_id}")
        
        self.print_success(f"Response: {data.get('message', '')[:200]}...")
        
        return data
    
    async def verify_database_state(self, conversation_id: str) -> bool:
        """Verify that conversation state is persisted in database"""
        # This would require database access - for now just check API
        response = await self.client.get(f"/chat/history/{conversation_id}")
        
        if response.status_code == 200:
            self.print_success("Database state verified")
            return True
        else:
            self.print_failure("Database state verification failed")
            return False
    
    def record_result(self, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def print_summary(self):
        """Print test summary"""
        self.print_header("TEST SUMMARY")
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = total - passed
        
        print(f"Total Tests: {total}")
        print(f"{Colors.OKGREEN}Passed: {passed}{Colors.ENDC}")
        print(f"{Colors.FAIL}Failed: {failed}{Colors.ENDC}")
        print(f"Success Rate: {(passed/total*100):.1f}%\n")
        
        for result in self.test_results:
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"{status} - {result['test']}")
            if result["details"]:
                print(f"    {result['details']}")


# ═══════════════════════════════════════════════════════════════════
# TEST SCENARIOS
# ═══════════════════════════════════════════════════════════════════

async def test_scenario_1_sharpener_basic(runner: TestRunner):
    """Test Scenario 1: Basic Information Collection (Sharpener Node)"""
    runner.print_header("SCENARIO 1: Basic Information Collection")
    
    try:
        # Reset conversation for this test
        runner.conversation_id = None
        
        # Turn 1: Initial vague request
        response1 = await runner.send_message("Paris'e seyahat etmek istiyorum")
        
        # Verify sharpener is asking for more info (flexible keywords)
        message_lower = response1.get("message", "").lower()
        asking_keywords = ["tarih", "date", "when", "ne zaman", "kaç", "how many"]
        if any(kw in message_lower for kw in asking_keywords):
            runner.print_success("Sharpener correctly asking for missing info")
            passed_turn1 = True
        else:
            runner.print_failure("Sharpener should ask for dates")
            passed_turn1 = False
        
        # Turn 2: Provide details
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        response2 = await runner.send_message(
            "Yarın gidip 5 gün kalacağım, 2 kişiyiz",
            conversation_id=runner.conversation_id
        )
        
        # Verify plan is ready
        if "plan" in response2.get("message", "").lower() or "ara" in response2.get("message", "").lower():
            runner.print_success("Plan summary created")
            passed_turn2 = True
        else:
            runner.print_warning("Expected plan summary in response")
            passed_turn2 = False
        
        # Verify database persistence
        db_ok = await runner.verify_database_state(runner.conversation_id)
        
        passed = passed_turn1 and passed_turn2 and db_ok
        runner.record_result("Scenario 1: Sharpener Basic", passed)
        
    except Exception as e:
        runner.print_failure(f"Test failed with error: {e}")
        runner.record_result("Scenario 1: Sharpener Basic", False, str(e))


async def test_scenario_2_tool_calling(runner: TestRunner):
    """Test Scenario 2: Tool Calling (Flight Search)"""
    runner.print_header("SCENARIO 2: Tool Calling - Flight Search")
    
    try:
        # Reset conversation for this test
        runner.conversation_id = None
        
        # First complete sharpening
        await runner.send_message("Amsterdam'a gitmek istiyorum")
        await runner.send_message(
            "Yarın gidip 3 gün kalacağım, 1 kişi",
            conversation_id=runner.conversation_id
        )
        
        # Now request flight search
        response = await runner.send_message(
            "Evet, uçuş seçeneklerini göster",
            conversation_id=runner.conversation_id
        )
        
        # Check if tool was called (response should contain flight info)
        message = response.get("message", "")
        if "uçuş" in message.lower() or "flight" in message.lower():
            runner.print_success("Tool calling appears to work")
            passed = True
        else:
            runner.print_warning("Expected flight search results")
            passed = False
        
        runner.record_result("Scenario 2: Tool Calling", passed)
        
    except Exception as e:
        runner.print_failure(f"Test failed with error: {e}")
        runner.record_result("Scenario 2: Tool Calling", False, str(e))


async def test_scenario_3_multi_turn_persistence(runner: TestRunner):
    """Test Scenario 3: Multi-Turn Context Persistence"""
    runner.print_header("SCENARIO 3: Multi-Turn Context Persistence")
    
    try:
        # Create new conversation
        runner.conversation_id = None
        
        # Turn 1
        await runner.send_message("Londra'ya gitmek istiyorum")
        conv_id_1 = runner.conversation_id
        
        # Turn 2
        await runner.send_message(
            "Yarın gidip 4 gün kalacağım",
            conversation_id=runner.conversation_id
        )
        conv_id_2 = runner.conversation_id
        
        # Turn 3
        await runner.send_message(
            "2 kişiyiz",
            conversation_id=runner.conversation_id
        )
        conv_id_3 = runner.conversation_id
        
        # Verify conversation ID stayed the same
        if conv_id_1 == conv_id_2 == conv_id_3:
            runner.print_success("Conversation ID consistent across turns")
            passed = True
        else:
            runner.print_failure("Conversation ID changed between turns")
            passed = False
        
        # Verify database
        db_ok = await runner.verify_database_state(runner.conversation_id)
        
        runner.record_result("Scenario 3: Multi-Turn Persistence", passed and db_ok)
        
    except Exception as e:
        runner.print_failure(f"Test failed with error: {e}")
        runner.record_result("Scenario 3: Multi-Turn Persistence", False, str(e))


async def test_scenario_4_info_agent(runner: TestRunner):
    """Test Scenario 4: Info Agent (Policy Search)"""
    runner.print_header("SCENARIO 4: Info Agent - Policy Search")
    
    try:
        # Create new conversation
        runner.conversation_id = None
        
        response = await runner.send_message("İptal politikanız nedir?")
        
        message = response.get("message", "")
        if "iptal" in message.lower() or "policy" in message.lower() or "cancel" in message.lower():
            runner.print_success("Info agent responded to policy question")
            passed = True
        else:
            runner.print_warning("Expected policy information in response")
            passed = False
        
        runner.record_result("Scenario 4: Info Agent", passed)
        
    except Exception as e:
        runner.print_failure(f"Test failed with error: {e}")
        runner.record_result("Scenario 4: Info Agent", False, str(e))


async def test_scenario_5_reactive_action(runner: TestRunner):
    """Test Scenario 5: Reactive Action (Booking List)"""
    runner.print_header("SCENARIO 5: Reactive Action - Booking List")
    
    try:
        # Create new conversation
        runner.conversation_id = None
        
        response = await runner.send_message("Rezervasyonlarımı göster")
        
        message = response.get("message", "")
        # Response should either show bookings or say no bookings found
        if "rezervasyon" in message.lower() or "booking" in message.lower():
            runner.print_success("Reactive action executed")
            passed = True
        else:
            runner.print_warning("Expected booking information")
            passed = False
        
        runner.record_result("Scenario 5: Reactive Action", passed)
        
    except Exception as e:
        runner.print_failure(f"Test failed with error: {e}")
        runner.record_result("Scenario 5: Reactive Action", False, str(e))


async def test_scenario_6_escalation(runner: TestRunner):
    """Test Scenario 6: Escalation"""
    runner.print_header("SCENARIO 6: Escalation")
    
    try:
        # Create new conversation
        runner.conversation_id = None
        
        response = await runner.send_message("Bir yetkiliyle görüşmek istiyorum")
        
        # More flexible keyword matching for escalation
        message_lower = response.get("message", "").lower()
        escalation_keywords = [
            "yetkili", "temsilci", "representative", "human", "agent",
            "bağlıyorum", "connecting", "müşteri", "customer", "destek", "support"
        ]
        if any(kw in message_lower for kw in escalation_keywords):
            runner.print_success("Escalation triggered")
            passed = True
        else:
            runner.print_warning("Expected escalation response")
            passed = False
        
        runner.record_result("Scenario 6: Escalation", passed)
        
    except Exception as e:
        runner.print_failure(f"Test failed with error: {e}")
        runner.record_result("Scenario 6: Escalation", False, str(e))


# ═══════════════════════════════════════════════════════════════════
# MAIN TEST RUNNER
# ═══════════════════════════════════════════════════════════════════

async def main():
    """Run all test scenarios"""
    runner = TestRunner()
    
    try:
        print(f"\n{Colors.BOLD}ActionFlow Orchestration Test Suite{Colors.ENDC}")
        print(f"Customer ID: {CUSTOMER_ID}")
        print(f"API Base URL: {API_BASE_URL}\n")
        
        # Health check
        runner.print_header("HEALTH CHECK")
        try:
            response = await runner.client.get("/chat/health")
            if response.status_code == 200:
                runner.print_success("API is healthy")
                health_data = response.json()
                runner.print_info(f"MCP Status: {health_data.get('mcp', {}).get('status')}")
            else:
                runner.print_failure("API health check failed")
                return
        except Exception as e:
            runner.print_failure(f"Cannot connect to API: {e}")
            return
        
        # Run test scenarios
        await test_scenario_1_sharpener_basic(runner)
        await asyncio.sleep(1)  # Small delay between tests
        
        await test_scenario_2_tool_calling(runner)
        await asyncio.sleep(1)
        
        await test_scenario_3_multi_turn_persistence(runner)
        await asyncio.sleep(1)
        
        await test_scenario_4_info_agent(runner)
        await asyncio.sleep(1)
        
        await test_scenario_5_reactive_action(runner)
        await asyncio.sleep(1)
        
        await test_scenario_6_escalation(runner)
        
        # Print summary
        runner.print_summary()
        
    finally:
        await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
