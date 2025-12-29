"""Service layer for handling business logic and utility functions.

This module contains non-endpoint functions that handle core business logic,
background tasks, and utility functions used across the application.
"""

import os
import logging
import json
import uuid
import mimetypes
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from urllib.parse import unquote, quote

# FastAPI
from fastapi import HTTPException, status, UploadFile
from fastapi.responses import FileResponse

# Scheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Twilio
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# Application imports
from server.db import SessionLocal, Device, User, File as DBFile, Query, Session
from server.config import settings
from server.utils import (
    log_something,
    log_error,
    log_server_health,
    log_server_lifecycle,
    compute_sha256
)
from server.auth import get_password_hash, create_access_token

# AI Agent imports
from aiagent.handler import query as ai_query_handler
from aiagent.memory.memory_manager import LongTermMemoryManager, ShortTermMemoryManager
from aiagent.context.reference import read_references

# Initialize logger
logger = logging.getLogger(__name__)


# Initialize scheduler
scheduler = None


def get_status_message() -> str:
    """Generate a status message with current time and user count.
    
    Returns:
        str: Status message
    """
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"Thoth API is running. Users: {user_count}, Time: {current_time}"
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return f"Thoth API is running. Error getting status: {e}"
    finally:
        db.close()




def _generate_unique_encouragement() -> str:
    """Generate a unique encouraging message using AI based on previously sent messages.
    
    Returns:
        str: A unique, longer encouraging message that differs from recent ones.
    """
    from server.db import File as DBFile, User
    
    # Get previously sent messages to avoid repetition
    previous_messages = []
    db = SessionLocal()
    try:
        gad_user = db.query(User).filter(User.username == "gad").first()
        if gad_user:
            stm_file = db.query(DBFile).filter(
                DBFile.userId == gad_user.userId, 
                DBFile.filename == "short_term_memory.json"
            ).first()
            if stm_file and stm_file.content:
                try:
                    memory = json.loads(stm_file.content.decode("utf-8"))
                    sent_sms = memory.get("sent_sms", [])
                    # Get last 10 periodic encouragement messages
                    periodic_msgs = [
                        sms["message"] for sms in sent_sms 
                        if sms.get("source") == "periodic_encouragement"
                    ][-10:]
                    previous_messages = periodic_msgs
                except:
                    pass
    finally:
        db.close()
    
    # Build context about Gad for the AI
    gad_context = """
    Gad is a Computer Science PhD student at Western University, Canada.
    - Research: Privacy-preserving ML, Federated Learning, Differential Privacy, Wi-Fi Sensing, ISAC
    - Publications: 18+ papers, h-index 9, 213+ citations
    - Top venues: IEEE INFOCOM, ACM Computing Surveys
    - Background: From Egypt (Nile University) to Canada
    - Teaching: Award-winning instructor, 3+ years experience
    - Founder of Thothcraft
    - Working on groundbreaking privacy-preserving sensing systems
    """
    
    # Build the prompt for AI
    previous_msgs_text = ""
    if previous_messages:
        previous_msgs_text = "\\n\\nPREVIOUSLY SENT MESSAGES (DO NOT REPEAT THESE OR USE SIMILAR THEMES):\\n"
        for i, msg in enumerate(previous_messages, 1):
            previous_msgs_text += f"{i}. {msg}\\n"
    
    prompt = f"""Generate a unique, heartfelt encouraging SMS message for Gad. 

REQUIREMENTS:
1. The message MUST be 200-300 characters long (longer than typical SMS but still readable)
2. It MUST be COMPLETELY DIFFERENT from any previously sent messages in theme, structure, and content
3. Be creative - use different angles: his journey, specific achievements, future potential, daily motivation, philosophical insights, humor, etc.
4. Include 1-2 relevant emojis
5. Be personal and warm, like a supportive friend or mentor
6. Reference specific aspects of his work or journey when possible
7. Vary the tone: sometimes inspirational, sometimes reflective, sometimes celebratory, sometimes philosophical

CONTEXT ABOUT GAD:
{gad_context}
{previous_msgs_text}

Generate ONLY the message text, nothing else. Make it genuinely unique and different from anything sent before."""

    try:
        # Use the AI agent to generate the message
        result = ai_query_handler(
            query=prompt,
            chat_id="periodic_encouragement_generator",
            context={"purpose": "generate_unique_sms", "recipient": "gad"}
        )
        
        if result and result.get("success") and result.get("response"):
            generated_msg = result["response"].strip()
            # Ensure it's not too long for SMS (keep under 320 chars)
            if len(generated_msg) > 320:
                generated_msg = generated_msg[:317] + "..."
            return generated_msg
    except Exception as e:
        logger.error(f"Error generating AI encouragement: {e}")
    
    # Fallback to a default message if AI fails
    import random
    fallback_messages = [
        "Gad, your work on privacy-preserving ML is shaping the future of AI. Every line of code, every paper, every student you inspire - it all matters. The world needs researchers like you who care about both innovation AND ethics. Keep pushing boundaries! 🌟💪",
        "Hey Gad! Remember: the PhD journey isn't just about the destination. Every challenge you overcome, every late night, every 'aha' moment - they're all building the researcher and person you're becoming. Western U is lucky to have you! 🚀✨",
        "Thinking of you today, Gad! From the Nile to the Thames (Ontario's Thames!), your journey shows what determination looks like. 18 papers, countless students inspired, and you're just getting started. The best chapters are still being written! 📚🔥",
    ]
    return random.choice(fallback_messages)


def send_status(message: str = "", to_phone_number: str = ""):
    """Send an encouraging message to Gad periodically using AI to generate unique messages."""
    from server.db import File as DBFile, User
    
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Always send to Gad's phone
        recipient_phone = "+18073587137"
        
        # If no message provided, generate one using AI based on previous messages
        if not message:
            message = _generate_unique_encouragement()
        
        success = send_twilio_message(recipient_phone, message)
        
        # Record this as a periodic message in Gad's memory
        db = SessionLocal()
        try:
            gad_user = db.query(User).filter(User.username == "gad").first()
            if gad_user:
                stm_file = db.query(DBFile).filter(DBFile.userId == gad_user.userId, DBFile.filename == "short_term_memory.json").first()
                memory = {}
                if stm_file and stm_file.content:
                    try:
                        memory = json.loads(stm_file.content.decode("utf-8"))
                    except:
                        memory = {}
                
                sent_sms = memory.get("sent_sms", [])
                sent_sms.append({
                    "to": recipient_phone,
                    "message": message,
                    "date": current_time,
                    "source": "periodic_encouragement",
                    "original_request": "Automated periodic encouragement message from your AI assistant",
                })
                if len(sent_sms) > 100:
                    sent_sms = sent_sms[-100:]
                memory["sent_sms"] = sent_sms
                
                encoded = json.dumps(memory).encode("utf-8")
                if stm_file:
                    stm_file.content = encoded
                    stm_file.size = len(encoded)
                else:
                    new_file = DBFile(
                        userId=gad_user.userId,
                        filename="short_term_memory.json",
                        content=encoded,
                        content_type="application/json",
                    )
                    new_file.size = len(encoded)
                    db.add(new_file)
                db.commit()
        finally:
            db.close()
        
        if not success:
            log_error(f"[send_status] Failed to send SMS to {recipient_phone}")
        else:
            log_something(f"[send_status] Encouraging SMS sent to Gad at {current_time}", endpoint="send_status")
    except Exception as e:
        log_error(f"[send_status] Error: {e}")


def auto_disconnect_stale_devices():
    """Mark devices as offline if they haven't sent a heartbeat recently."""
    db = SessionLocal()
    try:
        # Check for devices that haven't been seen in the last 5 minutes
        stale_time = datetime.utcnow() - timedelta(minutes=5)
        
        # Get devices that haven't been seen recently and are currently online
        stale_devices = db.query(Device).filter(
            Device.last_seen < stale_time,
            Device.online == True
        ).all()
        
        if stale_devices:
            for device in stale_devices:
                device.online = False
                if hasattr(device, 'disconnected_at'):
                    device.disconnected_at = datetime.utcnow()
                if hasattr(device, 'updated_at'):
                    device.updated_at = datetime.utcnow()
                
                logger.info(f"Marked device {getattr(device, 'id', 'unknown')} as offline")
            
            db.commit()
            logger.info(f"Marked {len(stale_devices)} devices as offline")
        
        return len(stale_devices)
        
    except Exception as e:
        logger.error(f"Error in auto_disconnect_stale_devices: {e}")
        db.rollback()
        return 0
    finally:
        db.close()


def start_scheduler():
    """Start the background scheduler for periodic tasks."""
    global scheduler
    if scheduler is not None:
        logger.warning("Scheduler already running")
        return scheduler
    
    try:
        scheduler = BackgroundScheduler()
        
        # Add status update job (every ~3.3 hours)
        scheduler.add_job(
            send_status,
            trigger=IntervalTrigger(hours=1),
            id='send_status_job',
            name='Send status periodically',
            replace_existing=True
        )
        
        # Add device status check job (every 2 minutes)
        scheduler.add_job(
            auto_disconnect_stale_devices,
            trigger=IntervalTrigger(minutes=2),
            id='auto_disconnect_job',
            name='Auto disconnect stale devices',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Scheduler started successfully with jobs: %s", 
                   [job.name for job in scheduler.get_jobs()])
        
        # Register shutdown handler
        import atexit
        atexit.register(lambda: scheduler.shutdown() if scheduler else None)
        
        return scheduler
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        if scheduler is not None:
            try:
                scheduler.shutdown()
            except:
                pass
            scheduler = None
        raise


def send_twilio_message(to_phone_number: str, message: str) -> Dict[str, Any]:
    """Send an SMS message using Twilio.
    
    Args:
        to_phone_number: Recipient's phone number in E.164 format
        message: The message content to send
        
    Returns:
        Dict containing the message SID and status if successful
        
    Raises:
        HTTPException: If there's an error sending the message
    """
    try:
        # Initialize Twilio client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # Send message
        twilio_message = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to_phone_number
        )
        
        return {
            "message_sid": twilio_message.sid,
            "status": twilio_message.status,
            "to": twilio_message.to,
            "date_created": twilio_message.date_created.isoformat() if twilio_message.date_created else None
        }
        
    except TwilioRestException as e:
        logger.error(f"Twilio API error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error sending Twilio message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while sending the message"
        )
