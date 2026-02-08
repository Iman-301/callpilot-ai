"""
CallPilot - An elite, autonomous AI scheduling agent
Flask application with ElevenLabs Conversational AI SDK integration
"""

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json
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

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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


# Global conversation instance
conversation: Optional[Conversation] = None


def init_conversation():
    """Initialize the conversation on startup"""
    global conversation
    # Only validate and initialize if credentials are provided
    if Config.ELEVENLABS_API_KEY and Config.ELEVENLABS_AGENT_ID:
        try:
            # Try to import ElevenLabs conversational AI (API may have changed)
            try:
                from elevenlabs.conversational_ai import Conversation, ConversationConfig
                Config.validate()
                
                # Create tools
                tools = []  # Tools will be configured in ElevenLabs dashboard
                
                config = ConversationConfig(
                    agent_id=AGENT_ID,
                    asr_settings=Config.get_asr_settings(),
                    tts_settings=Config.get_tts_settings(),
                    tools=tools,
                    system_prompt=CALLPILOT_SYSTEM_PROMPT,
                    enable_webhook=False,
                    enable_transcription=True,
                    enable_audio_recording=True
                )
                conversation = Conversation(config=config, client=elevenlabs_client)
                print("[OK] ElevenLabs conversation initialized successfully")
            except (ImportError, AttributeError) as import_error:
                print(f"[WARNING] ElevenLabs SDK API has changed: {import_error}")
                print("   Conversation endpoints will not work until SDK is updated.")
                print("   Basic endpoints (health, availability, booking) will work.")
        except Exception as e:
            print(f"[WARNING] Could not initialize ElevenLabs conversation: {e}")
            print("   Basic endpoints (health, availability, booking) will work.")
    else:
        print("[WARNING] ElevenLabs credentials not configured.")
        print("   Basic endpoints (health, availability, booking) will work.")


# Initialize on import
init_conversation()


@app.route("/", methods=["GET"])
def root():
    """Root endpoint"""
    return jsonify({
        "service": "CallPilot",
        "status": "operational",
        "version": "1.0.0"
    })


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "conversation_initialized": conversation is not None
    })


@app.route("/availability/<date>", methods=["GET"])
def get_availability(date: str):
    """Direct endpoint to check availability (for testing)"""
    result = check_availability(date)
    return jsonify(result)


@app.route("/book", methods=["POST"])
def book_direct():
    """Direct endpoint to book appointment (for testing)"""
    # Support both JSON body (from ElevenLabs) and query parameters (for testing)
    if request.is_json:
        body = request.get_json()
        date = body.get("date") or request.args.get("date")
        time = body.get("time") or request.args.get("time")
        service = body.get("service") or request.args.get("service")
    else:
        date = request.args.get("date")
        time = request.args.get("time")
        service = request.args.get("service")
    
    if not date or not time or not service:
        return jsonify({
            "error": "Missing required parameters",
            "message": "date, time, and service are required"
        }), 400
    
    result = book_appointment(date, time, service)
    return jsonify(result)


@app.route("/conversation/start", methods=["POST"])
def start_conversation():
    """Start a new conversation"""
    global conversation
    
    # Validate ElevenLabs configuration
    if not Config.validate_elevenlabs():
        return jsonify({
            "error": "ElevenLabs configuration missing",
            "message": "ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID must be set in .env file",
            "api_key_set": Config.ELEVENLABS_API_KEY is not None,
            "agent_id_set": Config.ELEVENLABS_AGENT_ID is not None
        }), 500
    
    if not elevenlabs_client:
        return jsonify({
            "error": "ElevenLabs client not initialized",
            "message": "Failed to initialize ElevenLabs client. Check your API key."
        }), 500
    
    try:
        if not conversation:
            init_conversation()
        
        if not conversation:
            return jsonify({
                "error": "Failed to create conversation",
                "message": "Check that your agent_id is valid and the SDK API is correct"
            }), 500
        
        # Start the conversation
        response = conversation.start()
        
        return jsonify({
            "conversation_id": response.conversation_id,
            "message": "Conversation started"
        })
    except Exception as e:
        return jsonify({
            "error": "Failed to start conversation",
            "message": str(e),
            "hint": "Verify your agent_id exists and is correct in ElevenLabs dashboard"
        }), 500


@app.route("/conversation/text", methods=["POST"])
def handle_text_input():
    """Handle text input (for testing)"""
    if not conversation:
        return jsonify({
            "error": "Conversation not initialized"
        }), 400
    
    data = request.get_json()
    text = data.get("text", "") if data else ""
    
    if not text:
        return jsonify({
            "error": "Text input is required"
        }), 400
    
    try:
        # Process text through the conversation
        response = conversation.text(text)
        
        return jsonify({
            "response": response.text,
            "audio_url": getattr(response, 'audio_url', None)
        })
    except Exception as e:
        return jsonify({
            "error": "Failed to process text",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=True)
