"""
Info Agent - RAG-Enhanced Policy Q&A
Uses Pinecone for semantic search of travel policies
"""

import logging
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.schemas import AgentState
from app.core.utils import get_system_context
from app.core.llm import llm
from app.core.rag_service import get_policy_context

logger = logging.getLogger("ActionFlow-InfoAgent")


async def info_agent_node(state: AgentState) -> dict:
    """
    Info Agent - Answers policy questions using RAG
    """
    logger.info("ℹ️ [INFO_AGENT] Processing information request...")
    
    # Get last user message
    last_user_message = None
    for msg in reversed(state["messages"]):
        if hasattr(msg, 'content') and msg.content:
            if isinstance(msg, HumanMessage) or (hasattr(msg, 'type') and msg.type == 'human'):
                last_user_message = msg.content
                break
    
    if not last_user_message:
        logger.warning("⚠️ [INFO_AGENT] No user message found")
        return {
            "messages": [SystemMessage(content="I didn't receive a question. How can I help?")],
            "completed_tasks": state.get("completed_tasks", []) + ["info_completed"]
        }
    
    # Retrieve relevant policy context from Pinecone
    logger.info(f"🔍 [INFO_AGENT] Searching policies for: {last_user_message[:50]}...")
    policy_context = get_policy_context(last_user_message)
    
    if "No relevant policy information found" in policy_context:
        logger.warning("⚠️ [INFO_AGENT] No relevant policies found")
    else:
        logger.info(f"✅ [INFO_AGENT] Retrieved policy context ({len(policy_context)} chars)")
    
    # Build system prompt with retrieved context
    context = get_system_context()
    system_prompt = f"""You are ActionFlow's travel policy expert assistant. {context}

**YOUR ROLE:**
You answer questions about travel policies using the most up-to-date information from our policy database.

**RELEVANT POLICY INFORMATION:**
{policy_context}

**INSTRUCTIONS:**
1. Answer based on the policy information provided above
2. Be specific with numbers, fees, and timeframes
3. If policy information is incomplete, say so honestly
4. Cite the relevant policy section when possible
5. Be helpful and professional
6. Keep answers concise but complete
7. If question is outside policies, politely redirect to customer service

**IMPORTANT:**
- ALWAYS answer in the user's language (detect from their message)
- Use the exact fees, times, and rules from the policy information
- Don't make up information not in the policies
"""
    
    # Generate response
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=last_user_message)
    ]
    
    try:
        response = await llm.ainvoke(messages)
        logger.info("✅ [INFO_AGENT] Response generated")
    except Exception as e:
        logger.error(f"❌ [INFO_AGENT] Error generating response: {e}")
        response = SystemMessage(content="I apologize, I'm having trouble accessing policy information right now. Please contact customer service.")
    
    # Mark task as completed
    new_tasks = state.get("completed_tasks", []).copy()
    if "info_completed" not in new_tasks:
        new_tasks.append("info_completed")
    
    return {
        "messages": [response],
        "completed_tasks": new_tasks
    }