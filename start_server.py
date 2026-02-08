"""
Simple server startup script for CallPilot
Handles missing credentials gracefully
"""

import sys
import os
from config import Config

def main():
    """Start the server with proper error handling"""
    print("=" * 50)
    print("CallPilot Server")
    print("=" * 50)
    print()
    
    # Check configuration
    if not Config.ELEVENLABS_API_KEY or not Config.ELEVENLABS_AGENT_ID:
        print("⚠️  Warning: ElevenLabs credentials not configured")
        print("   Basic endpoints (health, availability, booking) will work.")
        print("   Conversation endpoints require:")
        print("   - ELEVENLABS_API_KEY")
        print("   - ELEVENLABS_AGENT_ID")
        print("   Add these to your .env file")
        print()
    else:
        print("✅ ElevenLabs credentials configured")
        print()
    
    print("Starting server on http://localhost:8000")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    print()
    
    # Import and run uvicorn
    try:
        import uvicorn
        uvicorn.run(
            "main:app",
            host=Config.HOST,
            port=Config.PORT,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
