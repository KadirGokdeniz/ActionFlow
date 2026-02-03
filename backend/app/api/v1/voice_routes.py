"""
Voice Routes - ActionFlow AI
Endpoints for Speech-to-Text and Text-to-Speech.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import Response, StreamingResponse
import logging
from app.services.voice.voice_service import transcribe_audio, text_to_speech
import io

router = APIRouter(prefix="/voice", tags=["Voice"])
logger = logging.getLogger("ActionFlow-VoiceRoutes")

@router.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    """
    Transcribe uploaded audio file to text.
    """
    try:
        logger.info(f"🎤 Received STT request: {file.filename}")
        
        # Read file contents
        audio_content = await file.read()
        audio_file = io.BytesIO(audio_content)
        
        # Transcribe
        text = await transcribe_audio(audio_file)
        
        return {"text": text}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("❌ STT request failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts")
async def text_to_speech_route(request_data: dict = Body(...)):
    """
    Convert text to speech and return audio stream.
    """
    text = request_data.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
        
    try:
        logger.info(f"🔊 Received TTS request for: {text[:50]}...")
        
        # Convert to speech
        audio_bytes = await text_to_speech(text)
        
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("❌ TTS request failed")
        raise HTTPException(status_code=500, detail=str(e))
