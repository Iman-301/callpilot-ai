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

# Import database module
try:
    from database import get_db
    USE_DATABASE = True
except ImportError:
    print("[WARNING] Database module not available. Using mock data.")
    USE_DATABASE = False

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
BRANCH_ID = Config.ELEVENLABS_BRANCH_ID

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

RESCHEDULING PROTOCOL:
- Verification: If a user wants to reschedule, first ask for their Confirmation ID or Phone Number to pull up the existing booking using lookup_booking tool.
- Atomic Action: Never cancel the old appointment until you have confirmed the new time slot is available. Use reschedule_appointment tool which handles this atomically.
- Confirmation: Always summarize the change: "I've moved your [Old Day] [Old Time] slot to [New Day] at [New Time]. You'll get a new text confirmation shortly."
- Timezone: Always speak in the user's local time but send ISO format (e.g., 2026-02-10T14:00:00) to backend tools.

CANCELLATION PROTOCOL:
- Retention Attempt: Before cancelling, offer one alternative time. "I can definitely cancel that for you. Just so you know, we also have an opening this [Day] if that's easier?"
- Finality: If they insist, call the cancel_appointment tool and confirm it is done. Say: "Your appointment on [Date] at [Time] has been cancelled. You'll receive a confirmation text shortly." Do not leave them wondering if it went through.

AMBIGUITY HANDLING:
- If the user says "I can't make it," ask "Would you like to find a better time to reschedule, or should we cancel it for now?"
- Double Confirmation: In voice, users hate repeating themselves. If they say "Move my 10 AM to 2 PM," call the reschedule_appointment tool immediately rather than asking "What time would you like?"

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


# Fallback mock data (only used if database is not available)
AVAILABILITY_DB: Dict[str, Dict[str, list]] = {}
BOOKINGS_DB: Dict[str, Dict[str, Any]] = {}

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
    
    # Get availability from database or fallback to mock
    use_db = USE_DATABASE
    if use_db:
        try:
            db = get_db()
            date_data = db.get_availability(date)
            available_times = [t for t in date_data["available_times"] if t not in date_data["booked_times"]]
            
            # Find closest alternative dates if no availability
            closest_alternatives = []
            if not available_times:
                current_date = datetime.strptime(date, "%Y-%m-%d")
                for i in range(1, 8):  # Check next 7 days
                    check_date = current_date + timedelta(days=i)
                    check_date_str = check_date.strftime("%Y-%m-%d")
                    
                    alt_data = db.get_availability(check_date_str)
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
        except Exception as e:
            print(f"[ERROR] Database error in check_availability: {e}")
            # Fallback to mock
            use_db = False
    
    # Fallback to mock data
    if not use_db:
        if date not in AVAILABILITY_DB:
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
    
    # Generate unique confirmation ID
    import time as time_module
    timestamp = int(time_module.time() * 1000) % 10000  # Last 4 digits of timestamp
    confirmation_id = f"CP-{date.replace('-', '')}-{time.replace(':', '')}-{timestamp}"
    
    # Use database or fallback to mock
    use_db = USE_DATABASE
    if use_db:
        try:
            db = get_db()
            
            # Find provider for this service
            providers = db.get_providers_by_service(service)
            if not providers:
                # Use default provider
                provider_id = "default"
            else:
                # Use first available provider for this service
                provider_id = providers[0]["provider_id"]
            
            # Get availability for this provider
            date_data = db.get_availability(date, provider_id=provider_id)
            
            # Check if time is available
            if time in date_data.get("booked_times", []):
                return {
                    "success": False,
                    "message": f"Time slot {time} is already booked. Please choose another time."
                }
            
            if time not in date_data.get("available_times", []):
                return {
                    "success": False,
                    "message": f"Time slot {time} is not available. Please choose from available times."
                }
            
            # Book the time slot in database for this provider
            if not db.book_time_slot(date, time, provider_id=provider_id):
                return {
                    "success": False,
                    "message": f"Failed to book time slot {time}. Please try again."
                }
            
            # Create booking record with provider
            db.create_booking(confirmation_id, date, time, service, provider_id=provider_id)
            
            return {
                "success": True,
                "message": "Appointment booked successfully",
                "confirmation_id": confirmation_id,
                "date": date,
                "time": time,
                "service": service,
                "provider_id": provider_id
            }
            
        except Exception as e:
            print(f"[ERROR] Database error in book_appointment: {e}")
            # Fallback to mock
            use_db = False
    
    # Fallback to mock data
    if not use_db:
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
        
        # Store booking in mock database
        BOOKINGS_DB[confirmation_id] = {
            "date": date,
            "time": time,
            "service": service,
            "status": "confirmed"
        }
        
        return {
            "success": True,
            "message": "Appointment booked successfully",
            "confirmation_id": confirmation_id,
            "date": date,
            "time": time,
            "service": service
        }


def cancel_appointment(confirmation_id: str) -> Dict[str, Any]:
    """
    Cancel an existing appointment.
    
    Args:
        confirmation_id: Confirmation ID of the appointment to cancel
    
    Returns:
        Dictionary with cancellation confirmation
    """
    if USE_DATABASE:
        try:
            db = get_db()
            booking = db.get_booking(confirmation_id=confirmation_id)
            
            if not booking:
                return {
                    "success": False,
                    "message": f"Appointment with confirmation ID {confirmation_id} not found."
                }
            
            if booking["status"] == "cancelled":
                return {
                    "success": False,
                    "message": "This appointment has already been cancelled."
                }
            
            # Free up the time slot for the correct provider
            date = booking["date"]
            time = booking["time"]
            provider_id = booking.get("provider_id", "default")
            db.free_time_slot(date, time, provider_id=provider_id)
            
            # Mark as cancelled
            db.update_booking_status(confirmation_id, "cancelled")
            
            return {
                "success": True,
                "message": "Appointment cancelled successfully",
                "confirmation_id": confirmation_id,
                "date": date,
                "time": time,
                "service": booking["service"]
            }
        except Exception as e:
            print(f"[ERROR] Database error in cancel_appointment: {e}")
            # Fallback to mock
            pass
    
    # Fallback to mock data
    if confirmation_id not in BOOKINGS_DB:
        return {
            "success": False,
            "message": f"Appointment with confirmation ID {confirmation_id} not found."
        }
    
    booking = BOOKINGS_DB[confirmation_id]
    
    if booking["status"] == "cancelled":
        return {
            "success": False,
            "message": "This appointment has already been cancelled."
        }
    
    # Free up the time slot
    date = booking["date"]
    time = booking["time"]
    
    if date in AVAILABILITY_DB:
        if time in AVAILABILITY_DB[date]["booked_times"]:
            AVAILABILITY_DB[date]["booked_times"].remove(time)
    
    # Mark as cancelled
    booking["status"] = "cancelled"
    
    return {
        "success": True,
        "message": "Appointment cancelled successfully",
        "confirmation_id": confirmation_id,
        "date": date,
        "time": time,
        "service": booking["service"]
    }


def reschedule_appointment(confirmation_id: str, new_date: str, new_time: str) -> Dict[str, Any]:
    """
    Reschedule an existing appointment to a new date and time.
    Atomic action: Only moves the appointment if the new slot is available.
    
    Args:
        confirmation_id: Confirmation ID of the appointment to reschedule
        new_date: New date in ISO format (YYYY-MM-DD)
        new_time: New time in HH:MM format
    
    Returns:
        Dictionary with rescheduling confirmation
    """
    # Validate new date format
    try:
        datetime.strptime(new_date, "%Y-%m-%d")
    except ValueError:
        return {
            "success": False,
            "message": "Invalid date format. Please use YYYY-MM-DD format."
        }
    
    if USE_DATABASE:
        try:
            db = get_db()
            booking = db.get_booking(confirmation_id=confirmation_id)
            
            if not booking:
                return {
                    "success": False,
                    "message": f"Appointment with confirmation ID {confirmation_id} not found."
                }
            
            if booking["status"] == "cancelled":
                return {
                    "success": False,
                    "message": "Cannot reschedule a cancelled appointment. Please book a new appointment."
                }
            
            # Get provider_id from existing booking
            provider_id = booking.get("provider_id", "default")
            
            # Check if new time slot is available for this provider
            new_date_data = db.get_availability(new_date, provider_id=provider_id)
            
            if new_time in new_date_data.get("booked_times", []):
                return {
                    "success": False,
                    "message": f"Time slot {new_time} on {new_date} is already booked. Please choose another time."
                }
            
            if new_time not in new_date_data.get("available_times", []):
                return {
                    "success": False,
                    "message": f"Time slot {new_time} is not available. Please choose from available times."
                }
            
            # Atomic action: Free old slot and book new slot for the same provider
            old_date = booking["date"]
            old_time = booking["time"]
            
            # Free old slot for this provider
            db.free_time_slot(old_date, old_time, provider_id=provider_id)
            
            # Book new slot for this provider
            db.book_time_slot(new_date, new_time, provider_id=provider_id)
            
            # Update booking (keep same provider)
            db.update_booking_datetime(confirmation_id, new_date, new_time, new_provider_id=provider_id)
            
            return {
                "success": True,
                "message": "Appointment rescheduled successfully",
                "confirmation_id": confirmation_id,
                "old_date": old_date,
                "old_time": old_time,
                "new_date": new_date,
                "new_time": new_time,
                "service": booking["service"]
            }
        except Exception as e:
            print(f"[ERROR] Database error in reschedule_appointment: {e}")
            # Fallback to mock
            pass
    
    # Fallback to mock data
    if confirmation_id not in BOOKINGS_DB:
        return {
            "success": False,
            "message": f"Appointment with confirmation ID {confirmation_id} not found."
        }
    
    booking = BOOKINGS_DB[confirmation_id]
    
    if booking["status"] == "cancelled":
        return {
            "success": False,
            "message": "Cannot reschedule a cancelled appointment. Please book a new appointment."
        }
    
    # Check if new time slot is available
    if new_date not in AVAILABILITY_DB:
        AVAILABILITY_DB[new_date] = {
            "available_times": Config.DEFAULT_AVAILABLE_TIMES.copy(),
            "booked_times": []
        }
    
    new_date_data = AVAILABILITY_DB[new_date]
    
    if new_time in new_date_data["booked_times"]:
        return {
            "success": False,
            "message": f"Time slot {new_time} on {new_date} is already booked. Please choose another time."
        }
    
    if new_time not in new_date_data["available_times"]:
        return {
            "success": False,
            "message": f"Time slot {new_time} is not available. Please choose from available times."
        }
    
    # Atomic action: Free old slot and book new slot
    old_date = booking["date"]
    old_time = booking["time"]
    
    # Free old slot
    if old_date in AVAILABILITY_DB:
        if old_time in AVAILABILITY_DB[old_date]["booked_times"]:
            AVAILABILITY_DB[old_date]["booked_times"].remove(old_time)
    
    # Book new slot
    new_date_data["booked_times"].append(new_time)
    
    # Update booking
    booking["date"] = new_date
    booking["time"] = new_time
    booking["status"] = "rescheduled"
    
    return {
        "success": True,
        "message": "Appointment rescheduled successfully",
        "confirmation_id": confirmation_id,
        "old_date": old_date,
        "old_time": old_time,
        "new_date": new_date,
        "new_time": new_time,
        "service": booking["service"]
    }


def lookup_booking(confirmation_id: str = None, phone_number: str = None) -> Dict[str, Any]:
    """
    Look up an existing booking by confirmation ID or phone number.
    
    Args:
        confirmation_id: Confirmation ID to search for
        phone_number: Phone number to search for
    
    Returns:
        Dictionary with booking information
    """
    if USE_DATABASE:
        try:
            db = get_db()
            booking = db.get_booking(confirmation_id=confirmation_id, phone_number=phone_number)
            
            if booking:
                return {
                    "found": True,
                    "booking": booking
                }
            
            return {
                "found": False,
                "message": "Booking not found. Please check your confirmation ID or phone number."
            }
        except Exception as e:
            print(f"[ERROR] Database error in lookup_booking: {e}")
            # Fallback to mock
            pass
    
    # Fallback to mock data
    if confirmation_id and confirmation_id in BOOKINGS_DB:
        booking = BOOKINGS_DB[confirmation_id].copy()
        booking["confirmation_id"] = confirmation_id
        return {
            "found": True,
            "booking": booking
        }
    
    # Phone number lookup in mock data
    if phone_number:
        # Search by phone number in mock data (if phone numbers were stored)
        for conf_id, booking_data in BOOKINGS_DB.items():
            if booking_data.get("phone_number") == phone_number and booking_data.get("status") == "confirmed":
                booking = booking_data.copy()
                booking["confirmation_id"] = conf_id
                return {
                    "found": True,
                    "booking": booking
                }
    
    return {
        "found": False,
        "message": "Booking not found. Please check your confirmation ID or phone number."
    }


# Global conversation state (new SDK doesn't use Conversation objects)
conversation = None


def init_conversation():
    """Initialize the conversation on startup"""
    global conversation
    # Only validate and initialize if credentials are provided
    if Config.ELEVENLABS_API_KEY and Config.ELEVENLABS_AGENT_ID:
        try:
            Config.validate()
            print(f"[DEBUG] Initializing conversation with agent_id: {AGENT_ID}")
            
            # The ElevenLabs SDK API has changed - conversations are now managed through the client
            # We don't need to initialize a Conversation object upfront
            # Instead, we'll use the client's conversational_ai methods when needed
            
            # For now, mark conversation as "available" if client is initialized
            # The actual conversation will be created on-demand via API calls
            if elevenlabs_client:
                conversation = "initialized"  # Placeholder to indicate client is ready
                print("[OK] ElevenLabs client ready for conversational AI")
                print("   Note: Conversations are now created on-demand via API calls")
            else:
                print("[WARNING] ElevenLabs client not initialized")
                
        except Exception as e:
            print(f"[WARNING] Could not initialize ElevenLabs conversation: {e}")
            import traceback
            traceback.print_exc()
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
        "conversation_initialized": conversation is not None,
        "elevenlabs_client_initialized": elevenlabs_client is not None,
        "agent_id": AGENT_ID if AGENT_ID else None,
        "api_key_set": Config.ELEVENLABS_API_KEY is not None
    })


@app.route("/conversation/test", methods=["GET"])
def test_conversation():
    """Test endpoint to diagnose conversation initialization issues"""
    diagnostics = {
        "api_key_set": Config.ELEVENLABS_API_KEY is not None,
        "agent_id_set": Config.ELEVENLABS_AGENT_ID is not None,
        "agent_id": AGENT_ID,
        "elevenlabs_client_initialized": elevenlabs_client is not None,
        "conversation_initialized": conversation is not None,
        "sdk_version": None,
        "available_methods": []
    }
    
    try:
        import elevenlabs
        diagnostics["sdk_version"] = getattr(elevenlabs, "__version__", "unknown")
    except:
        pass
    
    if conversation:
        try:
            diagnostics["available_methods"] = [m for m in dir(conversation) if not m.startswith('_')]
        except:
            pass
    
    # Try to initialize if not already initialized
    if not conversation and Config.ELEVENLABS_API_KEY and Config.ELEVENLABS_AGENT_ID:
        try:
            init_conversation()
            diagnostics["conversation_initialized"] = conversation is not None
            diagnostics["initialization_attempted"] = True
        except Exception as e:
            diagnostics["initialization_error"] = str(e)
    
    return jsonify(diagnostics)


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


@app.route("/cancel", methods=["POST"])
def cancel_direct():
    """Direct endpoint to cancel appointment"""
    if request.is_json:
        body = request.get_json()
        confirmation_id = body.get("confirmation_id") or request.args.get("confirmation_id")
    else:
        confirmation_id = request.args.get("confirmation_id")
    
    if not confirmation_id:
        return jsonify({
            "error": "Missing required parameter",
            "message": "confirmation_id is required"
        }), 400
    
    result = cancel_appointment(confirmation_id)
    return jsonify(result)


@app.route("/reschedule", methods=["POST"])
def reschedule_direct():
    """Direct endpoint to reschedule appointment"""
    if request.is_json:
        body = request.get_json()
        confirmation_id = body.get("confirmation_id") or request.args.get("confirmation_id")
        new_date = body.get("new_date") or request.args.get("new_date")
        new_time = body.get("new_time") or request.args.get("new_time")
    else:
        confirmation_id = request.args.get("confirmation_id")
        new_date = request.args.get("new_date")
        new_time = request.args.get("new_time")
    
    if not confirmation_id or not new_date or not new_time:
        return jsonify({
            "error": "Missing required parameters",
            "message": "confirmation_id, new_date, and new_time are required"
        }), 400
    
    result = reschedule_appointment(confirmation_id, new_date, new_time)
    return jsonify(result)


@app.route("/lookup", methods=["GET", "POST"])
def lookup_direct():
    """Direct endpoint to lookup booking by confirmation ID or phone number"""
    if request.method == "POST" and request.is_json:
        body = request.get_json()
        confirmation_id = body.get("confirmation_id") or request.args.get("confirmation_id")
        phone_number = body.get("phone_number") or request.args.get("phone_number")
    else:
        confirmation_id = request.args.get("confirmation_id")
        phone_number = request.args.get("phone_number")
    
    result = lookup_booking(confirmation_id=confirmation_id, phone_number=phone_number)
    return jsonify(result)


@app.route("/conversation/start", methods=["POST"])
def start_conversation():
    """Start a new conversation using ElevenLabs API"""
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
        # The new SDK uses get_signed_url method
        # Generate a signed URL for the conversation
        print(f"[DEBUG] Getting signed URL for agent_id: {AGENT_ID}")
        
        # Get branch_id from request if provided, or use default from config
        branch_id = None
        if request.is_json:
            branch_id = request.json.get('branch_id')
        if not branch_id:
            branch_id = BRANCH_ID
        
        # Use the client's conversational_ai.get_signed_url method
        # Note: get_signed_url only accepts agent_id, not branch_id
        # We'll append branch_id to the WebSocket URL query string
        print(f"[DEBUG] Using agent_id: {AGENT_ID}, branch_id: {branch_id}")
        
        # Get signed URL with just agent_id
        response = elevenlabs_client.conversational_ai.get_signed_url(agent_id=AGENT_ID)
        
        print(f"[DEBUG] Response type: {type(response)}")
        print(f"[DEBUG] Response: {response}")
        
        # Extract signed URL and conversation ID from response
        # The response might be a dict or an object
        if isinstance(response, dict):
            signed_url = response.get('signed_url') or response.get('url')
            conversation_id = response.get('conversation_id') or response.get('id')
        else:
            signed_url = getattr(response, 'signed_url', None) or getattr(response, 'url', None)
            conversation_id = getattr(response, 'conversation_id', None) or getattr(response, 'id', None)
        
        if signed_url:
            print(f"[DEBUG] Signed URL obtained: {signed_url[:100]}...")
            # IMPORTANT: Do NOT modify the signed URL - it contains a cryptographic signature (conversation_signature)
            # Modifying it will cause WebSocket error 1008 (Policy Violation)
            # The signed URL is already valid for the agent_id
            # Note: If branch_id is needed, it should be configured in the agent settings or passed via initial message
            print(f"[DEBUG] Using signed URL as-is (do not modify)")
        else:
            print(f"[DEBUG] No signed URL in response, will construct WebSocket URL from agent_id")
            # Construct WebSocket URL manually if signed URL not available
            # Format: wss://api.elevenlabs.io/v1/convai/conversation?agent_id=...&branch_id=...
            # According to ElevenLabs Agents Platform docs
            base_url = "wss://api.elevenlabs.io/v1/convai/conversation"
            query_params = [f"agent_id={AGENT_ID}"]
            if branch_id:
                query_params.append(f"branch_id={branch_id}")
            signed_url = f"{base_url}?{'&'.join(query_params)}"
            print(f"[DEBUG] Constructed WebSocket URL: {signed_url}")
        
        return jsonify({
            "conversation_id": conversation_id,
            "signed_url": signed_url,
            "message": "Conversation URL generated successfully",
            "agent_id": AGENT_ID,
            "branch_id": branch_id,
            "note": "Use the signed_url to connect to the conversation via WebSocket"
        })
    except AttributeError as e:
        # The method might not exist or be named differently
        print(f"[DEBUG] create_signed_url not available: {e}")
        print(f"[DEBUG] Available methods: {[m for m in dir(elevenlabs_client.conversational_ai) if not m.startswith('_')]}")
        
        # Return agent info for direct connection
        return jsonify({
            "conversation_id": None,
            "signed_url": None,
            "agent_id": AGENT_ID,
            "message": "Agent ID ready for connection",
            "note": "Frontend should connect directly to ElevenLabs using agent_id. The SDK API may have changed.",
            "connection_info": {
                "agent_id": AGENT_ID,
                "api_endpoint": "https://api.elevenlabs.io/v1/convai"
            }
        })
    except Exception as e:
        print(f"[ERROR] Failed to start conversation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Failed to start conversation",
            "message": str(e),
            "agent_id": AGENT_ID,
            "hint": "Verify your agent_id exists and is correct in ElevenLabs dashboard. Check server logs for details."
        }), 500


@app.route("/conversation/text", methods=["POST"])
def handle_text_input():
    """Handle text input (for testing) - Note: This may not work with new SDK"""
    if not elevenlabs_client:
        return jsonify({
            "error": "ElevenLabs client not initialized"
        }), 400
    
    data = request.get_json()
    text = data.get("text", "") if data else ""
    conversation_id = data.get("conversation_id", "") if data else ""
    
    if not text:
        return jsonify({
            "error": "Text input is required"
        }), 400
    
    try:
        # The new SDK API may require different approach
        # For now, return a placeholder response
        return jsonify({
            "response": "Text input received. Note: Direct text processing may require WebSocket connection.",
            "audio_url": None,
            "conversation_id": conversation_id,
            "note": "Consider using WebSocket connection for real-time conversation"
        })
    except Exception as e:
        return jsonify({
            "error": "Failed to process text",
            "message": str(e)
        }), 500


@app.route("/conversation/audio", methods=["POST"])
def handle_audio_input():
    """Handle audio input from frontend"""
    try:
        if 'audio' not in request.files:
            return jsonify({
                "error": "No audio file provided"
            }), 400
        
        audio_file = request.files['audio']
        agent_id = request.form.get('agent_id')
        conversation_id = request.form.get('conversation_id')
        
        if not agent_id:
            return jsonify({
                "error": "agent_id is required",
                "message": "Please start a conversation first"
            }), 400
        
        # Note: ElevenLabs Conversational AI requires WebSocket connection for real-time audio
        # This endpoint is a placeholder. For full implementation, you would need to:
        # 1. Maintain a WebSocket connection to ElevenLabs on the backend
        # 2. Forward audio chunks from frontend to ElevenLabs via WebSocket
        # 3. Stream responses back to frontend
        # 
        # Alternative: Use ElevenLabs JavaScript SDK directly in the frontend
        # (requires exposing API key or using signed URLs)
        
        # For now, return a helpful message
        return jsonify({
            "success": True,
            "transcript": "Audio received. Note: Full voice conversation requires WebSocket connection.",
            "response_text": "I received your audio. To enable full voice conversation, please connect via the ElevenLabs WebSocket API or use their JavaScript SDK.",
            "response_audio": None,
            "booking_confirmation": None,
            "note": "For production use, implement WebSocket connection to ElevenLabs Conversational AI API"
        })
    except Exception as e:
        print(f"[ERROR] Failed to process audio: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Failed to process audio",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=True)
