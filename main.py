"""
CallPilot - An elite, autonomous AI scheduling agent
FastAPI application with ElevenLabs Conversational AI SDK integration
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
import asyncio
from config import Config

# Try to import ElevenLabs (may not be available or API may have changed)
elevenlabs_client = None
ConversationConfig = None
Conversation = None

try:
    from elevenlabs import ElevenLabs
    if Config.ELEVENLABS_API_KEY:
        try:
            elevenlabs_client = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)
        except Exception as e:
            print(f"Warning: Could not initialize ElevenLabs client: {e}")
except ImportError:
    print("Warning: ElevenLabs SDK not available or API has changed")
    print("Basic endpoints (health, availability, booking) will work without ElevenLabs")

app = FastAPI(title="CallPilot", version="1.0.0")

# Business configuration
BUSINESS_NAME = Config.BUSINESS_NAME
AGENT_ID = Config.ELEVENLABS_AGENT_ID

# System Prompt - The CallPilot Agentic System Prompt
CALLPILOT_SYSTEM_PROMPT = """You are CallPilot, an elite, autonomous AI scheduling agent.

IDENTITY & PERSONA:
- Name: CallPilot
- Role: An elite, autonomous AI scheduling agent
- Tone: Professional, crisp, and high-energy. You are helpful but value the user's time.
- Voice Style: Natural, use occasional filler words like "Let's see..." or "Got it" to mask latency. NEVER use bullet points or lists in your speech; speak in full, flowing sentences.

CORE MISSION:
Your sole objective is to move the user through the Booking Funnel:
1. Identify the service requested.
2. Check availability using the check_availability tool.
3. Negotiate a time slot.
4. Confirm details and execute the booking using book_appointment.

OPERATIONAL RULES (THE "STATE MACHINE"):
- Greeting: Start with: "Thanks for calling {business_name}, this is CallPilot. How can I help you get scheduled today?"
- Tool Usage: You must call check_availability before suggesting any specific date or time. Do not guess.
- Filler Word Injection: When calling check_availability, ALWAYS say "One second, checking the calendar..." or "Let me check the calendar for you..." BEFORE the tool executes. This masks latency and keeps the conversation natural.
- Constraint Handling: If the user's requested time is unavailable, look at the tool output and offer the two closest alternatives immediately. Do not ask "When else works?"—be proactive.
- Information Gathering: If the user is vague (e.g., "sometime next week"), ask for a specific day.
- Confirmation Flow: Before calling book_appointment, you must recap: "Okay, just to confirm, I'm booking your [Service] for [Date] at [Time]. Is that correct?"

EDGE CASE & GUARDRAIL PROTOCOLS:
- The "Barge-In": If the user interrupts you, stop speaking immediately and acknowledge the new information (e.g., "Oh, sorry, you said Wednesday instead? Let me re-check that.").
- Ambiguity: If the user asks for "the usual," and you don't have that data, politely ask: "I want to make sure I get this right—which service are we looking at today?"
- Off-Topic: If the user asks non-scheduling questions (e.g., "What's the weather?"), steer them back: "I'm not sure about the weather, but I can definitely get you booked for your appointment. Which day works for you?"
- Latency Masking: If a tool call takes longer than 2 seconds, provide a "thinking" vocalization: "One moment, the system is just pulling up those records..."

OUTPUT FORMATTING FOR TTS:
- Numbers: Say "Ten A M" instead of "10:00."
- Dates: Say "February tenth" instead of "02/10."
- Punctuation: Use commas frequently to create natural pauses in the ElevenLabs voice synthesis.

Remember: Always be proactive, check availability before suggesting times, and confirm before booking.""".format(business_name=Config.BUSINESS_NAME)


# Mock availability data - In production, this would connect to a real calendar system
AVAILABILITY_DB: Dict[str, Dict[str, list]] = {
    "2026-02-10": {
        "available_times": ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"],
        "booked_times": []
    },
    "2026-02-11": {
        "available_times": ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"],
        "booked_times": []
    },
    "2026-02-12": {
        "available_times": ["09:00", "10:00", "14:00", "15:00", "16:00"],
        "booked_times": ["11:00"]
    }
}

# Service types (from config)
SERVICES = Config.SERVICES


def check_availability(date: str) -> Dict[str, Any]:
    """
    Check availability for a given date.
    
    Note: The agent is instructed via system prompt to say filler words like
    "One second, checking the calendar..." BEFORE calling this function.
    This masks latency and keeps the conversation natural.
    
    Args:
        date: ISO format date string (e.g., "2026-02-10")
    
    Returns:
        Dictionary with availability information
    """
    try:
        # Validate date format
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return {
            "available": False,
            "message": "Invalid date format. Please use YYYY-MM-DD format.",
            "available_times": [],
            "closest_alternatives": []
        }
    
    # Check if date exists in database
    if date not in AVAILABILITY_DB:
        # Generate default availability for future dates
        AVAILABILITY_DB[date] = {
            "available_times": Config.DEFAULT_AVAILABLE_TIMES.copy(),
            "booked_times": []
        }
    
    date_data = AVAILABILITY_DB[date]
    available_times = [t for t in date_data["available_times"] if t not in date_data["booked_times"]]
    
    # Find closest alternative dates if no availability
    closest_alternatives = []
    if not available_times:
        current_date = datetime.strptime(date, "%Y-%m-%d")
        for i in range(1, 8):  # Check next 7 days
            check_date = current_date + timedelta(days=i)
            check_date_str = check_date.strftime("%Y-%m-%d")
            
            if check_date_str in AVAILABILITY_DB:
                alt_data = AVAILABILITY_DB[check_date_str]
                alt_available = [t for t in alt_data["available_times"] if t not in alt_data["booked_times"]]
                if alt_available:
                    closest_alternatives.append({
                        "date": check_date_str,
                        "available_times": alt_available[:2]  # Top 2 alternatives
                    })
                    if len(closest_alternatives) >= 2:
                        break
    
    return {
        "available": len(available_times) > 0,
        "message": f"Found {len(available_times)} available time slots" if available_times else "No availability on this date",
        "available_times": available_times,
        "closest_alternatives": closest_alternatives
    }


def book_appointment(date: str, time: str, service: str) -> Dict[str, Any]:
    """
    Book an appointment for a given date, time, and service.
    
    Args:
        date: ISO format date string (e.g., "2026-02-10")
        time: Time string in HH:MM format (e.g., "10:00")
        service: Service type string
    
    Returns:
        Dictionary with booking confirmation
    """
    try:
        # Validate date format
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return {
            "success": False,
            "message": "Invalid date format. Please use YYYY-MM-DD format."
        }
    
    # Initialize date in database if not exists
    if date not in AVAILABILITY_DB:
        AVAILABILITY_DB[date] = {
            "available_times": Config.DEFAULT_AVAILABLE_TIMES.copy(),
            "booked_times": []
        }
    
    date_data = AVAILABILITY_DB[date]
    
    # Check if time is available
    if time in date_data["booked_times"]:
        return {
            "success": False,
            "message": f"Time slot {time} is already booked. Please choose another time."
        }
    
    if time not in date_data["available_times"]:
        return {
            "success": False,
            "message": f"Time slot {time} is not available. Please choose from available times."
        }
    
    # Book the appointment
    date_data["booked_times"].append(time)
    
    # Generate confirmation ID
    confirmation_id = f"CP-{date.replace('-', '')}-{time.replace(':', '')}"
    
    return {
        "success": True,
        "message": "Appointment booked successfully",
        "confirmation_id": confirmation_id,
        "date": date,
        "time": time,
        "service": service
    }


# Tool definitions for ElevenLabs
def create_tools():
    """Create tool definitions for the ElevenLabs Conversational AI SDK"""
    # Note: This function will need to be updated based on the actual ElevenLabs SDK API
    # The API structure has changed in newer versions
    # For now, return empty list - tools will be configured when ElevenLabs integration is updated
    try:
        # Try to import the Tool class (API may have changed)
        from elevenlabs.conversational_ai import Tool
        
        check_availability_tool = Tool(
            name="check_availability",
            description="Check available time slots for a specific date. Use this before suggesting any time to the user. Input must be in ISO format (YYYY-MM-DD).",
            parameters={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in ISO format (YYYY-MM-DD), e.g., '2026-02-10'"
                    }
                },
                "required": ["date"]
            },
            function=check_availability
        )
        
        book_appointment_tool = Tool(
            name="book_appointment",
            description="Book an appointment for a specific date, time, and service. Only call this after confirming with the user.",
            parameters={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in ISO format (YYYY-MM-DD), e.g., '2026-02-10'"
                    },
                    "time": {
                        "type": "string",
                        "description": "Time in HH:MM format, e.g., '10:00'"
                    },
                    "service": {
                        "type": "string",
                        "description": "Service type (e.g., 'consultation', 'follow-up', 'check-up', 'appointment')"
                    }
                },
                "required": ["date", "time", "service"]
            },
            function=book_appointment
        )
        
        return [check_availability_tool, book_appointment_tool]
    except (ImportError, AttributeError) as e:
        print(f"Warning: Could not create ElevenLabs tools: {e}")
        print("ElevenLabs integration will need to be updated for the new API")
        return []


# Create conversation configuration
def create_conversation_config():
    """Create the conversation configuration with Dynamic Latency Optimization"""
    if not AGENT_ID:
        raise ValueError("ELEVENLABS_AGENT_ID is required for conversation configuration")
    
    # Note: The ElevenLabs API has changed - this will need to be updated
    # For now, this is a placeholder that will need to match the new SDK structure
    try:
        from elevenlabs.conversational_ai import ConversationConfig
        tools = create_tools()
        
        # The actual API structure may differ - this is based on the original spec
        config = ConversationConfig(
            agent_id=AGENT_ID,
            # Crucial for Role 1: Dynamic Latency Optimization
            asr_settings=Config.get_asr_settings(),  # Fast STT
            tts_settings=Config.get_tts_settings(),  # Fast TTS
            tools=tools,
            system_prompt=CALLPILOT_SYSTEM_PROMPT,
            # Additional settings for better latency
            enable_webhook=False,  # Set to True if you need webhooks
            enable_transcription=True,
            enable_audio_recording=True
        )
        return config
    except (ImportError, AttributeError, TypeError) as e:
        raise ValueError(f"ElevenLabs SDK API has changed. Please update the integration. Error: {e}")


# Global conversation instance
conversation: Optional[Conversation] = None

# WebSocket connections for real-time transcripts (Role 3)
active_websockets: List[WebSocket] = []


@app.on_event("startup")
async def startup_event():
    """Initialize the conversation on startup"""
    global conversation
    # Only validate and initialize if credentials are provided
    # This allows testing basic endpoints without ElevenLabs setup
    if Config.ELEVENLABS_API_KEY and Config.ELEVENLABS_AGENT_ID:
        try:
            from elevenlabs.conversational_ai import Conversation
            Config.validate()
            config = create_conversation_config()
            conversation = Conversation(config=config, client=elevenlabs_client)
            print("✅ ElevenLabs conversation initialized successfully")
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize ElevenLabs conversation: {e}")
            print("   Basic endpoints (health, availability, booking) will work.")
            print("   Conversation endpoints require working ElevenLabs integration.")
            print("   Note: The ElevenLabs SDK API may have changed - check documentation.")
    else:
        print("⚠️  Warning: ElevenLabs credentials not configured.")
        print("   Basic endpoints (health, availability, booking) will work.")
        print("   Conversation endpoints require ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID in .env file.")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "CallPilot",
        "status": "operational",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "conversation_initialized": conversation is not None
    }


@app.post("/conversation/start")
async def start_conversation():
    """Start a new conversation"""
    global conversation
    
    # Validate ElevenLabs configuration before attempting to start
    if not Config.validate_elevenlabs():
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ElevenLabs configuration missing",
                "message": "ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID must be set in .env file",
                "api_key_set": Config.ELEVENLABS_API_KEY is not None,
                "agent_id_set": Config.ELEVENLABS_AGENT_ID is not None
            }
        )
    
    if not elevenlabs_client:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ElevenLabs client not initialized",
                "message": "Failed to initialize ElevenLabs client. Check your API key."
            }
        )
    
    try:
        if not conversation:
            config = create_conversation_config()
            if not config:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Failed to create conversation config",
                        "message": "Check that your agent_id is valid and the SDK API is correct"
                    }
                )
            conversation = Conversation(config=config, client=elevenlabs_client)
        
        # Start the conversation
        response = conversation.start()
        
        return {
            "conversation_id": response.conversation_id,
            "message": "Conversation started"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Configuration error",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to start conversation",
                "message": str(e),
                "hint": "Verify your agent_id exists and is correct in ElevenLabs dashboard"
            }
        )


@app.post("/conversation/audio")
async def handle_audio_stream(audio_data: bytes):
    """Handle incoming audio stream from the phone call"""
    if not conversation:
        raise HTTPException(status_code=400, detail="Conversation not initialized")
    
    try:
        # Process audio through the conversation
        response = conversation.audio(audio_data)
        
        # Pipe transcript to WebSocket (Role 3)
        if hasattr(response, 'text') and response.text:
            await broadcast_transcript({
                "type": "agent_response",
                "timestamp": datetime.now().isoformat(),
                "text": response.text,
                "conversation_id": getattr(response, 'conversation_id', None)
            })
        
        # Return audio response
        return StreamingResponse(
            response.audio_stream,
            media_type="audio/mpeg"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to process audio",
                "message": str(e)
            }
        )


@app.post("/conversation/text")
async def handle_text_input(request: Dict[str, str]):
    """Handle text input (for testing)"""
    if not conversation:
        raise HTTPException(status_code=400, detail="Conversation not initialized")
    
    text = request.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Text input is required")
    
    try:
        # Process text through the conversation
        response = conversation.text(text)
        
        # Pipe transcript to WebSocket (Role 3)
        if hasattr(response, 'text') and response.text:
            await broadcast_transcript({
                "type": "agent_response",
                "timestamp": datetime.now().isoformat(),
                "text": response.text,
                "conversation_id": getattr(response, 'conversation_id', None)
            })
        
        return {
            "response": response.text,
            "audio_url": response.audio_url if hasattr(response, 'audio_url') else None
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to process text",
                "message": str(e)
            }
        )


@app.get("/availability/{date}")
async def get_availability(date: str):
    """Direct endpoint to check availability (for testing)"""
    result = check_availability(date)
    return result


@app.post("/book")
async def book_direct(
    body: Optional[Dict[str, str]] = Body(None),
    date: Optional[str] = None,
    time: Optional[str] = None,
    service: Optional[str] = None
):
    """
    Direct endpoint to book appointment
    Accepts both JSON body (for ElevenLabs) and query parameters (for direct testing)
    """
    # Support both JSON body (from ElevenLabs) and query parameters (for testing)
    if body:
        date = body.get("date") or date
        time = body.get("time") or time
        service = body.get("service") or service
    
    if not date or not time or not service:
        raise HTTPException(
            status_code=400,
            detail="Missing required parameters: date, time, and service are required"
        )
    
    result = book_appointment(date, time, service)
    return result


# WebSocket endpoint for real-time transcripts (Role 3)
@app.websocket("/ws/transcripts")
async def websocket_transcripts(websocket: WebSocket):
    """WebSocket endpoint for real-time conversation transcripts"""
    await websocket.accept()
    active_websockets.append(websocket)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to CallPilot transcript stream"
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Echo back for ping/pong or handle commands
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        active_websockets.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in active_websockets:
            active_websockets.remove(websocket)


async def broadcast_transcript(transcript_data: Dict[str, Any]):
    """Broadcast transcript to all connected WebSocket clients (Role 3)"""
    if not active_websockets:
        return
    
    message = json.dumps(transcript_data)
    disconnected = []
    
    for websocket in active_websockets:
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"Error sending transcript to WebSocket: {e}")
            disconnected.append(websocket)
    
    # Remove disconnected websockets
    for ws in disconnected:
        if ws in active_websockets:
            active_websockets.remove(ws)


def callback_agent_response(response_data: Dict[str, Any]):
    """
    Callback function for agent responses - pipes transcripts to WebSocket (Role 3)
    This should be called by the ElevenLabs SDK when agent responds
    """
    transcript_data = {
        "type": "agent_response",
        "timestamp": datetime.now().isoformat(),
        "text": response_data.get("text", ""),
        "audio_url": response_data.get("audio_url"),
        "conversation_id": response_data.get("conversation_id")
    }
    
    # Broadcast to WebSocket clients asynchronously
    asyncio.create_task(broadcast_transcript(transcript_data))


if __name__ == "__main__":
    import uvicorn
    Config.validate()
    uvicorn.run(app, host=Config.HOST, port=Config.PORT)
