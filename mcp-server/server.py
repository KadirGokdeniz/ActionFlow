"""
ActionFlow MCP Server - SSE (Server-Sent Events) Tabanlı
HTTP üzerinden erişilebilir, production-ready MCP Server

Bu server, LLM'lerin (Claude, GPT, vb.) ActionFlow backend'indeki
işlevleri tool olarak kullanmasını sağlar.

Mimari:
    Client (Orchestrator) → MCP Server → Backend API → Amadeus/Database
"""

import os
import json
import asyncio
import uuid
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Tool registry import
from tools import TOOLS, TOOL_FUNCTIONS, tool_exists

load_dotenv()

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
MCP_PORT = int(os.getenv("MCP_PORT", "3000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Logging setup
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MCP-Server")

# Global HTTP client
http_client: httpx.AsyncClient = None


# ═══════════════════════════════════════════════════════════════════
# FASTAPI APP LIFECYCLE
# ═══════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup ve shutdown işlemleri"""
    global http_client
    
    # Startup
    http_client = httpx.AsyncClient(
        base_url=BACKEND_URL,
        timeout=30.0,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=5)
    )
    logger.info(f"✅ MCP Server started. Backend: {BACKEND_URL}")
    logger.info(f"📦 Loaded {len(TOOLS)} tools: {[t['name'] for t in TOOLS]}")
    
    yield
    
    # Shutdown
    await http_client.aclose()
    logger.info("🛑 MCP Server stopped")


app = FastAPI(
    title="ActionFlow MCP Server",
    description="Travel AI Tool Server - SSE tabanlı MCP protokolü",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════
# HEALTH & INFO ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """Server bilgisi"""
    return {
        "name": "ActionFlow MCP Server",
        "version": "1.0.0",
        "protocol": "MCP over SSE",
        "tools_count": len(TOOLS),
        "tools": [t["name"] for t in TOOLS],
        "backend": BACKEND_URL
    }


@app.get("/health")
async def health():
    """Health check - backend bağlantısını da kontrol eder"""
    backend_status = "unknown"
    backend_latency = None
    
    try:
        import time
        start = time.time()
        response = await http_client.get("/health")
        backend_latency = round((time.time() - start) * 1000, 2)
        backend_status = "connected" if response.status_code == 200 else "error"
    except Exception as e:
        backend_status = f"disconnected: {str(e)}"
    
    return {
        "status": "healthy",
        "backend": {
            "status": backend_status,
            "url": BACKEND_URL,
            "latency_ms": backend_latency
        },
        "tools_loaded": len(TOOLS)
    }


# ═══════════════════════════════════════════════════════════════════
# MCP SSE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE bağlantısını açar (MCP protocol)"""
    async def event_generator():
        # Bağlantı kurulduğunda endpoint bilgisini gönder
        yield f"event: endpoint\ndata: /sse\n\n"
        
        # Keep-alive ping loop
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected")
                break
            await asyncio.sleep(30)
            yield f"data: {json.dumps({'type': 'ping'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Nginx buffering'i devre dışı bırak
        }
    )


@app.post("/sse")
async def sse_post_handler(request: Request):
    """SSE üzerinden gelen mesajları handle eder"""
    return await handle_mcp_message(request)


# ═══════════════════════════════════════════════════════════════════
# MCP MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════════════

@app.post("/message")
@app.post("/mcp/message")
async def handle_mcp_message(request: Request):
    """
    MCP JSON-RPC mesajlarını işler
    
    Desteklenen metodlar:
    - initialize: Protokol handshake
    - tools/list: Tool listesini döndür
    - tools/call: Tool çağır
    - notifications/initialized: Client hazır bildirimi
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}},
            status_code=400
        )
    
    method = body.get("method", "")
    params = body.get("params", {})
    msg_id = body.get("id", str(uuid.uuid4()))
    
    logger.debug(f"MCP Request: {method} (id={msg_id})")
    
    # ─────────────── INITIALIZE ───────────────
    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "ActionFlow MCP Server",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {"listChanged": True}
                }
            }
        })
    
    # ─────────────── TOOLS/LIST ───────────────
    elif method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": TOOLS
            }
        })
    
    # ─────────────── TOOLS/CALL ───────────────
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        # Tool var mı kontrol et
        if not tool_exists(tool_name):
            logger.warning(f"Tool not found: {tool_name}")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}"
                }
            })
        
        # Tool'u çalıştır
        try:
            logger.info(f"🔧 Calling tool: {tool_name} with args: {arguments}")
            
            # HTTP client'ı inject et
            tool_func = TOOL_FUNCTIONS[tool_name]
            result = await tool_func(**arguments, http_client=http_client)
            
            logger.info(f"✅ Tool {tool_name} completed successfully")
            
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            })
            
        except TypeError as e:
            # Argüman hatası
            logger.error(f"Tool argument error: {e}")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32602,
                    "message": f"Invalid params: {str(e)}"
                }
            })
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            })
    
    # ─────────────── NOTIFICATIONS ───────────────
    elif method == "notifications/initialized":
        logger.info("Client initialized notification received")
        return JSONResponse({"jsonrpc": "2.0", "id": msg_id, "result": {}})
    
    # ─────────────── UNKNOWN METHOD ───────────────
    else:
        logger.warning(f"Unknown method: {method}")
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        })


# ═══════════════════════════════════════════════════════════════════
# DIRECT TEST ENDPOINTS (Development/Debug)
# ═══════════════════════════════════════════════════════════════════

@app.get("/tools")
async def list_tools():
    """Tool listesini döndür (debug için)"""
    return {
        "count": len(TOOLS),
        "tools": TOOLS
    }


@app.get("/tools/{tool_name}")
async def get_tool_info(tool_name: str):
    """Tek bir tool'un bilgisini döndür"""
    for tool in TOOLS:
        if tool["name"] == tool_name:
            return tool
    return JSONResponse({"error": f"Tool not found: {tool_name}"}, status_code=404)


@app.post("/tools/{tool_name}/test")
async def test_tool(tool_name: str, request: Request):
    """
    Tool'u direkt test et (MCP protokolü olmadan)
    Debug ve development için kullanışlı
    """
    if not tool_exists(tool_name):
        return JSONResponse({"error": f"Tool not found: {tool_name}"}, status_code=404)
    
    try:
        body = await request.json()
    except:
        body = {}
    
    try:
        tool_func = TOOL_FUNCTIONS[tool_name]
        result = await tool_func(**body, http_client=http_client)
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=MCP_PORT,
        reload=True,
        log_level=LOG_LEVEL.lower()
    )