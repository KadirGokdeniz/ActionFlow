"""
OpenAI Realtime API Service - ActionFlow
Browser WebSocket <-> OpenAI Realtime API proxy.
MCP tool calls handled mid-stream.
"""
import os
import json
import asyncio
import logging
import base64
import httpx
import websockets

logger = logging.getLogger("ActionFlow-Realtime")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:3000")
REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"

REALTIME_TOOLS = [
    {
        "type": "function",
        "name": "search_flights",
        "description": "Search available flights between two airports",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "Origin IATA code (e.g. IST)"},
                "destination": {"type": "string", "description": "Destination IATA code (e.g. CDG)"},
                "departure_date": {"type": "string", "description": "Date YYYY-MM-DD"},
                "adults": {"type": "integer", "default": 1}
            },
            "required": ["origin", "destination", "departure_date"]
        }
    },
    {
        "type": "function",
        "name": "search_hotels",
        "description": "Search hotels in a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city_code": {"type": "string"},
                "check_in": {"type": "string"},
                "check_out": {"type": "string"},
                "adults": {"type": "integer", "default": 1}
            },
            "required": ["city_code", "check_in", "check_out"]
        }
    },
    {
        "type": "function",
        "name": "search_policies",
        "description": "Search travel policies and terms",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    }
]

SESSION_CONFIG = {
    "modalities": ["text", "audio"],
    "instructions": (
        "You are ActionFlow, an AI travel assistant. "
        "Help users with flights, hotels, and travel policies. "
        "Be concise. Use tools when searching. "
        "Reply in the same language as the user (Turkish or English)."
    ),
    "voice": "alloy",
    "input_audio_format": "pcm16",
    "output_audio_format": "pcm16",
    "input_audio_transcription": {"model": "whisper-1"},
    "turn_detection": {
        "type": "server_vad",
        "threshold": 0.5,
        "prefix_padding_ms": 300,
        "silence_duration_ms": 600
    },
    "tools": REALTIME_TOOLS,
    "tool_choice": "auto",
    "temperature": 0.8,
    "max_response_output_tokens": 500
}


async def call_mcp_tool(tool_name: str, arguments: dict) -> str:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{MCP_SERVER_URL}/message",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                    "id": "rt-1"
                }
            )
            data = r.json()
            content = data.get("result", {}).get("content", [])
            if content:
                return content[0].get("text", "No result")
            return json.dumps(data.get("result", {}))
    except Exception as e:
        logger.error(f"MCP tool call failed: {e}")
        return f"Tool unavailable: {e}"


async def realtime_session_handler(browser_ws, customer_id: str):
    if not OPENAI_API_KEY:
        await browser_ws.send_text(json.dumps({
            "type": "error", "message": "OpenAI API key not configured"
        }))
        return

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }

    try:
        async with websockets.connect(REALTIME_URL, additional_headers=headers) as openai_ws:
            logger.info(f"Realtime session started: customer={customer_id}")

            await openai_ws.send(json.dumps({
                "type": "session.update",
                "session": SESSION_CONFIG
            }))

            async def browser_to_openai():
                try:
                    async for message in browser_ws.iter_text():
                        data = json.loads(message)
                        t = data.get("type")
                        if t == "audio":
                            await openai_ws.send(json.dumps({
                                "type": "input_audio_buffer.append",
                                "audio": data["audio"]
                            }))
                        elif t == "commit":
                            await openai_ws.send(json.dumps({
                                "type": "input_audio_buffer.commit"
                            }))
                        elif t == "text":
                            await openai_ws.send(json.dumps({
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [{"type": "input_text", "text": data["text"]}]
                                }
                            }))
                            await openai_ws.send(json.dumps({"type": "response.create"}))
                except Exception as e:
                    logger.error(f"browser->openai error: {e}")

            async def openai_to_browser():
                try:
                    async for raw in openai_ws:
                        event = json.loads(raw)
                        etype = event.get("type", "")

                        if etype == "session.created":
                            await browser_ws.send_text(json.dumps({"type": "ready"}))

                        elif etype == "input_audio_buffer.speech_started":
                            await browser_ws.send_text(json.dumps({"type": "speech_started"}))

                        elif etype == "input_audio_buffer.speech_stopped":
                            await browser_ws.send_text(json.dumps({"type": "speech_stopped"}))

                        elif etype == "conversation.item.input_audio_transcription.completed":
                            await browser_ws.send_text(json.dumps({
                                "type": "user_transcript",
                                "text": event.get("transcript", "")
                            }))

                        elif etype == "response.audio.delta":
                            await browser_ws.send_text(json.dumps({
                                "type": "audio",
                                "audio": event.get("delta", "")
                            }))

                        elif etype == "response.audio_transcript.delta":
                            await browser_ws.send_text(json.dumps({
                                "type": "ai_transcript",
                                "text": event.get("delta", "")
                            }))

                        elif etype == "response.function_call_arguments.done":
                            call_id = event.get("call_id")
                            func_name = event.get("name")
                            try:
                                arguments = json.loads(event.get("arguments", "{}"))
                            except Exception:
                                arguments = {}

                            logger.info(f"Tool call: {func_name}({arguments})")
                            await browser_ws.send_text(json.dumps({
                                "type": "tool_call", "name": func_name
                            }))

                            result = await call_mcp_tool(func_name, arguments)

                            await openai_ws.send(json.dumps({
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "function_call_output",
                                    "call_id": call_id,
                                    "output": result
                                }
                            }))
                            await openai_ws.send(json.dumps({"type": "response.create"}))

                        elif etype == "error":
                            logger.error(f"OpenAI error: {event}")
                            await browser_ws.send_text(json.dumps({
                                "type": "error",
                                "message": event.get("error", {}).get("message", "Unknown error")
                            }))

                except Exception as e:
                    logger.error(f"openai->browser error: {e}")

            await asyncio.gather(browser_to_openai(), openai_to_browser())

    except Exception as e:
        logger.error(f"Realtime session error: {e}")
        try:
            await browser_ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
