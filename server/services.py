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




def send_status(message: str = "", to_phone_number: str = ""):
    """Send an encouraging message to Gad periodically."""
    import random
    from server.db import File as DBFile, User
    
    encouraging_messages = [
        "Hey Gad! Your PhD research on privacy-preserving ML is groundbreaking. 18 publications and counting - you're making real impact! Keep pushing! 💪",
        "Gad, federated learning is the future and you're at the forefront. Your h-index of 9 shows your work matters. Keep innovating! 🚀",
        "Remember Gad: from Nile University to Western University - look how far you've come! Your journey inspires others. Keep going! ⭐",
        "Hey Gad! 213 citations means 213+ researchers building on YOUR work. You're shaping the field of Wi-Fi sensing! 🌟",
        "Gad, IEEE INFOCOM and ACM Computing Surveys - top-tier venues recognize your brilliance. The PhD finish line is closer than you think! 💡",
        "Just checking in, Gad! Your passion for teaching has earned you awards. You're not just a researcher - you're a mentor! 🎯",
        "Hey Gad! Privacy-preserving ML will define the next decade of AI. You chose the right path. Trust your vision! 🔥",
        "Gad, 4 years of experience, 3 years of teaching excellence. You're building a legacy at Western University! 🌈",
        "Remember Gad: every paper you publish, every student you teach - you're making the world better. Keep at it! ✨",
        "Hey Gad! From Egypt to Canada, you've overcome so much. This PhD is just another challenge you'll conquer! 🏆",
    ]
    
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Always send to Gad's phone
        recipient_phone = "+18073587137"
        # Use provided message or pick a random encouraging one
        message = message or random.choice(encouraging_messages)
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
