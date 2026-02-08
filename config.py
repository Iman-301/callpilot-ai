"""
Configuration file for CallPilot
Centralized configuration management
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


class Config:
    """CallPilot configuration"""
    
    # ElevenLabs Configuration
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
    
    # Business Configuration
    BUSINESS_NAME = os.getenv("BUSINESS_NAME", "CallPilot Services")
    
    # Server Configuration
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8001))  # Changed to 8001 to avoid conflicts
    
    # ASR/TTS Settings for Dynamic Latency Optimization
    ASR_MODEL = os.getenv("ASR_MODEL", "deepgram_bolt")  # Fast STT
    TTS_MODEL = os.getenv("TTS_MODEL", "eleven_turbo_v2_5")  # Fast TTS
    
    # Availability Settings
    DEFAULT_AVAILABLE_TIMES = [
        "09:00", "10:00", "11:00", 
        "14:00", "15:00", "16:00"
    ]
    
    # Service Types
    SERVICES = [
        "consultation",
        "follow-up", 
        "check-up",
        "appointment"
    ]
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present for ElevenLabs"""
        if not cls.ELEVENLABS_API_KEY:
            raise ValueError("ELEVENLABS_API_KEY environment variable is required for ElevenLabs integration")
        if not cls.ELEVENLABS_AGENT_ID:
            raise ValueError("ELEVENLABS_AGENT_ID environment variable is required for ElevenLabs integration")
        return True
    
    @classmethod
    def validate_elevenlabs(cls) -> bool:
        """Validate ElevenLabs configuration (for conversation endpoints)"""
        return cls.ELEVENLABS_API_KEY is not None and cls.ELEVENLABS_AGENT_ID is not None
    
    @classmethod
    def get_asr_settings(cls) -> Dict[str, Any]:
        """Get ASR settings for ConversationConfig"""
        return {
            "model": cls.ASR_MODEL
        }
    
    @classmethod
    def get_tts_settings(cls) -> Dict[str, Any]:
        """Get TTS settings for ConversationConfig"""
        return {
            "model_id": cls.TTS_MODEL
        }
