"""
ActionFlow AI - Main Application Entry Point
FastAPI application with Prometheus metrics

Bu dosya mevcut main.py'ye eklenecek değişiklikleri gösterir.
Tüm dosyayı değiştirmeyin, sadece ilgili kısımları ekleyin.
"""

# ═══════════════════════════════════════════════════════════════════
# IMPORTS - Bu satırları main.py'nin import bölümüne ekleyin
# ═══════════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════════
# SETUP - app oluşturduktan sonra bu satırı ekleyin
# ═══════════════════════════════════════════════════════════════════

# Mevcut kodunuz:
# app = FastAPI(title="ActionFlow AI", ...)

# Bu satırı ekleyin (app oluşturduktan hemen sonra):


# ═══════════════════════════════════════════════════════════════════
# ÖRNEK: Chat endpoint'inde end-to-end tracking
# ═══════════════════════════════════════════════════════════════════

"""
Mevcut chat endpoint'inizi şöyle güncelleyin:

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    with track_end_to_end("web"):
        # Mevcut chat işleme kodunuz
        response = await orchestrator.chat(...)
        return response

Voice endpoint için:

@router.post("/voice/conversation")
async def voice_conversation(request: VoiceRequest):
    with track_end_to_end("voice"):
        # STT + Chat + TTS işlemleri
        ...

WhatsApp endpoint için:

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    with track_end_to_end("whatsapp"):
        # WhatsApp mesaj işleme
        ...
"""

# ═══════════════════════════════════════════════════════════════════
# TAM ÖRNEK main.py (referans için)
# ═══════════════════════════════════════════════════════════════════

"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Routers
from app.api.v1 import (
    chat_routes,
    voice_routes,
    flight_routes,
    booking_routes,
    policy_routes,
    whatsapp
)

# Metrics
from app.core.metrics import setup_metrics

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ActionFlow")

# Create app
app = FastAPI(
    title="ActionFlow AI",
    description="Travel Customer Support Automation",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Prometheus metrics
setup_metrics(app)

# Include routers
app.include_router(chat_routes.router, prefix="/api/v1")
app.include_router(voice_routes.router, prefix="/api/v1")
app.include_router(flight_routes.router, prefix="/api/v1")
app.include_router(booking_routes.router, prefix="/api/v1")  # YENİ
app.include_router(policy_routes.router, prefix="/api/v1")
app.include_router(whatsapp.router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "actionflow-backend"}

@app.get("/")
async def root():
    return {
        "name": "ActionFlow AI",
        "version": "1.0.0",
        "docs": "/docs",
        "metrics": "/metrics"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
