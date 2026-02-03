"""
Voice Service - ActionFlow AI
Handles Speech-to-Text (AssemblyAI) and Text-to-Speech (ElevenLabs) integrations.
"""

import os
import logging
from typing import Optional, BinaryIO
import assemblyai as aai
from elevenlabs.client import ElevenLabs
from elevenlabs import save
import io

# Logging
logger = logging.getLogger("ActionFlow-VoiceService")

# API Keys
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "cgSgspJ2msm6clMCkdW9")

# Initialize SDKs
if ASSEMBLYAI_API_KEY:
    aai.settings.api_key = ASSEMBLYAI_API_KEY

if ELEVENLABS_API_KEY:
    eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
else:
    eleven_client = None


async def transcribe_audio(audio_file: BinaryIO) -> str:
    """
    Transcribe audio file using AssemblyAI.
    
    Args:
        audio_file: File-like object or path to audio file
        
    Returns:
        Transcribed text
    """
    if not ASSEMBLYAI_API_KEY:
        logger.error("ASSEMBLYAI_API_KEY is not set")
        raise ValueError("Speech-to-Text service is not configured")

    try:
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_file)
        
        if transcript.status == aai.TranscriptStatus.error:
            logger.error(f"AssemblyAI Error: {transcript.error}")
            raise Exception(f"Transcription failed: {transcript.error}")
            
        logger.info("✅ Transcription completed")
        return transcript.text
    except Exception as e:
        logger.exception("❌ Error during transcription")
        raise


async def text_to_speech(text: str) -> bytes:
    """
    Convert text to speech using ElevenLabs.
    
    Args:
        text: Text to convert
        
    Returns:
        Audio bytes (MP3)
    """
    if not eleven_client:
        logger.error("ELEVENLABS_API_KEY is not set")
        raise ValueError("Text-to-Speech service is not configured")

    try:
        logger.info(f"🔊 Converting text to speech: {text[:50]}...")
        
        # Generate audio
        audio_generator = eleven_client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=text,
            model_id="eleven_multilingual_v2"
        )
        
        # Convert generator/iterator to bytes
        audio_bytes = b"".join(audio_generator)
        
        logger.info("✅ Text-to-Speech completed")
        return audio_bytes
    except Exception as e:
        logger.exception("❌ Error during text-to-speech conversion")
        raise
