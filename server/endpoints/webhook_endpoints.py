"""Webhook endpoints for external service integrations (Twilio, etc.)."""

import re
import json
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from sqlalchemy.orm import Session
from twilio.twiml.voice_response import VoiceResponse

from server.db import get_db, User, Query as DBQuery, File as DBFile
from server.utils.logging_utils import log_request_start, log_response, log_error, log_request_payload
from aiagent.handler.query import query_openai
from aiagent.memory.memory_manager import LongTermMemoryManager, ShortTermMemoryManager

router = APIRouter(prefix="/phone", tags=["webhooks"])

@router.post(
    "/incoming-message",
    summary="Handle Twilio incoming SMS",
    description="Process incoming SMS messages from Twilio webhook",
    responses={
        200: {"description": "Message processed successfully"},
        400: {"description": "Invalid message format"},
        401: {"description": "Unauthorized phone number"}
    }
)
async def handle_twilio_incoming_message(
    request: Request, 
    db: Session = Depends(get_db)
) -> Response:
    """
    Handle incoming SMS messages from Twilio and forward them to the query endpoint.
    
    Purpose: Process SMS messages and provide AI responses via Twilio
    
    Args:
        request: The incoming HTTP request containing Twilio webhook data
        db: Database session
        
    Returns:
        Response: TwiML response for Twilio
    """
    try:
        # Parse the form data from the request
        form_data = await request.form()
        from_number = form_data.get('From', '')
        body = form_data.get('Body', '').strip()
        
        endpoint_name = "/api/webhooks/twilio/incoming-message"
        log_request_start(endpoint_name, "POST", dict(request.headers), request.client.host if request.client else "unknown")
        log_request_payload(dict(form_data), endpoint_name)
        
        # Log the incoming message
        log_response(200, f"Incoming message from {from_number}: {body}", "/webhooks/twilio/incoming-message")
        
        # Normalize phone number (remove non-digits)
        normalized_from = re.sub(r'\D', '', from_number)
        
        # Gad's phone number - always allowed
        GAD_PHONE = "18073587137"
        
        # Find user by phone number
        user = db.query(User).filter(User.phone_number == int(normalized_from)).first() if normalized_from.isdigit() else None
        
        # If it's Gad's phone but no user found, find Gad's user account
        if not user and normalized_from == GAD_PHONE:
            user = db.query(User).filter(User.username == "gad").first()
        
        if not user:
            log_error(f"Unauthorized access attempt from {from_number}")
            return Response(
                content="<Response><Message>Unauthorized. Please register first.</Message></Response>",
                media_type="application/xml",
                status_code=200
            )
        
        # Create a chat ID for this conversation
        chat_id = f"sms_{normalized_from}"
        user_query_text = body
        
        # Save the query to database
        try:
            db_query = DBQuery(
                userId=user.userId,
                chatId=chat_id,
                query_text=user_query_text,
                response=None  # Will be updated with AI response
            )
            db.add(db_query)
            db.commit()
            db.refresh(db_query)
            
        except Exception as e:
            log_error(f"Database error: {str(e)}")
            return Response(
                content="<Response><Message>Service temporarily unavailable.</Message></Response>",
                media_type="application/xml",
                status_code=200
            )
        
        # Check if this is a task-setting message for accountability system
        task_set_response = None
        try:
            from server.periodic_intelligence import (
                get_todays_task, set_todays_tasks, get_time_context,
                update_task_progress, complete_task, get_stats_line,
                get_gamification_stats, get_level_info
            )
            
            ctx = get_time_context()
            current_task = get_todays_task()
            body_lower = body.lower().strip()
            
            # Check for progress updates (number 0-100)
            if body_lower.isdigit():
                progress = int(body_lower)
                if 0 <= progress <= 100 and current_task and current_task.get("tasks"):
                    result = update_task_progress("primary", progress)
                    if "error" not in result:
                        stats_line = get_stats_line()
                        if progress == 100:
                            comp_result = complete_task("primary")
                            xp_msg = f"+{comp_result['xp']['xp_awarded']} XP!" if comp_result.get('xp') else ""
                            task_set_response = f"🎉 PRIMARY TASK COMPLETE! {xp_msg}\n\n{stats_line}\n\nLegend status achieved. Keep going or rest - you've earned it.\n\n-𓂀 Thoth"
                        else:
                            task_set_response = f"📊 Progress updated: {progress}%\n\n{stats_line}\n\nKeep pushing! You're {100-progress}% away from victory.\n\n-𓂀 Thoth"
                        log_response(200, f"[Accountability] Progress updated: {progress}%", "/phone/incoming-message")
            
            # Check for "done" keywords
            done_keywords = ['done', 'finished', 'completed', 'did it', 'crushed it', 'nailed it', 'complete']
            if any(kw in body_lower for kw in done_keywords) and current_task:
                # Determine which task is done
                task_type = "primary"
                if "secondary" in body_lower or "2" in body_lower:
                    task_type = "secondary"
                elif "bonus" in body_lower or "3" in body_lower:
                    task_type = "bonus"
                
                if current_task.get("tasks") and task_type in current_task["tasks"]:
                    result = complete_task(task_type)
                    if "error" not in result:
                        stats_line = get_stats_line()
                        xp_info = result.get("xp", {})
                        xp_total = xp_info.get("xp_awarded", 0)
                        
                        # Add bonus XP info
                        bonus_msgs = []
                        if xp_info.get("bonus_xp"):
                            bonus_msgs.append(f"⚡ Early bird: +{xp_info['bonus_xp']['xp_awarded']} XP")
                        if xp_info.get("streak_xp"):
                            bonus_msgs.append(f"🔥 Streak: +{xp_info['streak_xp']['xp_awarded']} XP")
                        if xp_info.get("perfect_day_xp"):
                            bonus_msgs.append(f"💯 PERFECT DAY: +{xp_info['perfect_day_xp']['xp_awarded']} XP")
                        
                        bonus_text = "\n".join(bonus_msgs) if bonus_msgs else ""
                        level_up = "🆙 LEVEL UP!" if xp_info.get("leveled_up") else ""
                        
                        task_set_response = f"🎉 {task_type.upper()} COMPLETE! +{xp_total} XP {level_up}\n\n{bonus_text}\n\n{stats_line}\n\nYou absolute legend.\n\n-𓂀 Thoth"
                        log_response(200, f"[Accountability] {task_type} completed", "/phone/incoming-message")
                elif current_task.get("task"):
                    # Old format - single task
                    task = current_task.get("task")
                    task_set_response = f"🎉 VICTORY!\n\nTask: \"{task}\"\nStatus: CRUSHED ✓\n\nYou absolute legend.\n\n-𓂀 Thoth"
                    log_response(200, f"[Accountability] Task completed: {task}", "/phone/incoming-message")
            
            # Check for multi-task format: "task1 | task2 | task3"
            if not task_set_response and "|" in body and not ctx["is_night"]:
                parts = [p.strip() for p in body.split("|")]
                primary = parts[0] if len(parts) > 0 else None
                secondary = parts[1] if len(parts) > 1 else None
                bonus = parts[2] if len(parts) > 2 else None
                
                if primary:
                    result = set_todays_tasks(primary, secondary, bonus)
                    stats_line = get_stats_line()
                    
                    tasks_display = f"🎯 PRIMARY: {primary}"
                    if secondary:
                        tasks_display += f"\n📌 SECONDARY: {secondary}"
                    if bonus:
                        tasks_display += f"\n⭐ BONUS: {bonus}"
                    
                    xp_msg = f"+{result['xp']['xp_awarded']} XP" if result.get('xp') else ""
                    task_set_response = f"✅ TASKS LOCKED IN! {xp_msg}\n\n{tasks_display}\n\n{stats_line}\n\nI've got my eye on you. Now GO.\n\n-𓂀 Thoth"
                    log_response(200, f"[Accountability] Multi-tasks set", "/phone/incoming-message")
            
            # Single task (no pipe separator)
            if not task_set_response and not current_task and not ctx["is_night"]:
                is_likely_task = (
                    len(body) > 5 and
                    not body.endswith('?') and
                    not body_lower.startswith(('who', 'what', 'when', 'where', 'why', 'how', 'did', 'is', 'are', 'can')) and
                    not body_lower in ('yes', 'no', 'ok', 'okay', 'done', 'thanks', 'thank you')
                )
                
                if is_likely_task:
                    result = set_todays_tasks(primary=body)
                    stats_line = get_stats_line()
                    xp_msg = f"+{result['xp']['xp_awarded']} XP" if result.get('xp') else ""
                    task_set_response = f"✅ TASK LOCKED IN! {xp_msg}\n\n🎯 PRIMARY: {body}\n\n{stats_line}\n\nI've got my eye on you. First check-in in a few hours. Now GO.\n\n-𓂀 Thoth"
                    log_response(200, f"[Accountability] Task set: {body}", "/phone/incoming-message")
                    
        except Exception as e:
            log_error(f"Accountability check error: {e}")
        
        # If we have a task-related response, return it directly
        if task_set_response:
            twiml_response = f"<Response><Message>{task_set_response}</Message></Response>"
            return Response(
                content=twiml_response,
                media_type="application/xml",
                status_code=200
            )
        
        # Process with AI (simplified version)
        try:
            # Use basic memory managers for SMS
            long_term_memory = LongTermMemoryManager()
            short_term_memory = ShortTermMemoryManager()
            
            # Load sent SMS history to provide context about who requested messages
            sms_history_context = ""
            try:
                # Always read from Gad's account since that's where SMS history is stored
                gad_user = db.query(User).filter(User.username == "gad").first()
                log_response(200, f"[SMS History Read] Found gad user: {gad_user is not None}", "/phone/incoming-message")
                gad_user_id = gad_user.userId if gad_user else user.userId
                log_response(200, f"[SMS History Read] Using user_id: {gad_user_id}", "/phone/incoming-message")
                stm_file = db.query(DBFile).filter(DBFile.userId == gad_user_id, DBFile.filename == "short_term_memory.json").first()
                log_response(200, f"[SMS History Read] Found stm_file: {stm_file is not None}", "/phone/incoming-message")
                if stm_file and stm_file.content:
                    memory = json.loads(stm_file.content.decode("utf-8"))
                    sent_sms = memory.get("sent_sms", [])
                    log_response(200, f"[SMS History Read] Found {len(sent_sms)} SMS messages in history", "/phone/incoming-message")
                    if sent_sms:
                        # Get last 10 sent messages for context
                        recent_sms = sent_sms[-10:]
                        sms_history_context = "\n\nRECENT SMS MESSAGES YOU SENT TO GAD:\n"
                        for sms in recent_sms:
                            source = sms.get("source", "unknown")
                            original_req = sms.get("original_request", "Unknown")
                            msg = sms.get("message", "")[:100]
                            date = sms.get("date", "")
                            sms_history_context += f"- [{date}] Source: {source} | Request: '{original_req}' | Message: '{msg}...'\n"
            except Exception as e:
                log_error(f"Error loading SMS history: {e}")
            
            # Build context with SMS history
            sms_context = {
                "source": "sms_reply",
                "sms_history": sms_history_context,
                "instruction": "Gad is replying to an SMS. Check the SMS history above to see who requested the last message and why it was sent. If he asks who sent a message, tell him based on the history."
            }
            
            ai_response = query_openai(
                query=user_query_text,
                long_term_memory=long_term_memory,
                short_term_memory=short_term_memory,
                max_tokens=160,  # SMS character limit consideration
                temperature=0.7,
                aux_data={"current_user_id": user.userId, "source": "sms", "context": sms_context}
            )
            
            # Update query with response
            db_query.response = ai_response
            db.commit()
            
            # Truncate response if too long for SMS
            if len(ai_response) > 1500:  # Leave room for TwiML overhead
                ai_response = ai_response[:1500] + "..."
            
        except Exception as e:
            log_error(f"AI processing error: {str(e)}")
            ai_response = "I'm sorry, I'm experiencing technical difficulties. Please try again later."
        
        # Return TwiML response
        twiml_response = f"<Response><Message>{ai_response}</Message></Response>"
        
        log_response(200, "SMS response sent", "/webhooks/twilio/incoming-message")
        return Response(
            content=twiml_response,
            media_type="application/xml",
            status_code=200
        )
        
    except Exception as e:
        log_error(f"Webhook error: {str(e)}")
        return Response(
            content="<Response><Message>Error processing message.</Message></Response>",
            media_type="application/xml",
            status_code=200
        )

@router.post(
    "/message-status",
    summary="Handle Twilio message status",
    description="Process message delivery status updates from Twilio",
    responses={
        200: {"description": "Status update processed"}
    }
)
async def handle_twilio_message_status(
    request: Request,
    MessageSid: str = Form(...),
    MessageStatus: str = Form(...),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Handle Twilio message status updates.
    
    Purpose: Track SMS delivery status for monitoring and debugging
    
    Args:
        request: HTTP request
        MessageSid: Twilio message ID
        MessageStatus: Message delivery status
        db: Database session
        
    Returns:
        Dict: Status acknowledgment
    """
    try:
        log_request_start("POST", "/api/webhooks/twilio/message-status", None)
        
        # Log the status update
        log_response(200, f"Message {MessageSid} status: {MessageStatus}", "/webhooks/twilio/message-status")
        
        # You could store this in a message_status table if needed
        # For now, just log it
        
        return {"status": "received"}
        
    except Exception as e:
        log_error(f"Message status webhook error: {str(e)}")
        return {"status": "error"}

@router.post(
    "/incoming-call",
    summary="Handle Twilio incoming calls",
    description="Process incoming voice calls from Twilio webhook",
    responses={
        200: {"description": "Call handled successfully"}
    }
)
async def handle_twilio_incoming_call(
    request: Request,
    From: str = Form(None),
    To: str = Form(None),
    db: Session = Depends(get_db)
) -> Response:
    """
    Handle incoming voice calls from Twilio.
    
    Purpose: Provide voice interaction capabilities via Twilio
    
    Args:
        request: HTTP request
        From: Caller's phone number
        To: Called number
        db: Database session
        
    Returns:
        Response: TwiML response for call handling
    """
    try:
        log_request_start("POST", "/webhooks/twilio/incoming-call", None)
        
        # Normalize phone number
        normalized_from = re.sub(r'\D', '', From) if From else ""
        
        # Find user by phone number
        user = db.query(User).filter(User.phone_number == int(normalized_from)).first() if normalized_from.isdigit() else None
        
        # Create TwiML response
        resp = VoiceResponse()
        
        if not user:
            resp.say("Sorry, this number is not registered. Please register first.")
            resp.hangup()
        else:
            resp.say(f"Hello {user.username}! Welcome to the AI assistant.")
            resp.say("Please speak your question after the beep, and I'll provide an answer.")
            
            # Record the user's question
            resp.record(
                timeout=10,
                transcribe=True,
                transcribe_callback="/webhooks/twilio/transcription-callback",
                max_length=30
            )
            
            resp.say("Thank you. Processing your request.")
        
        log_response(200, "Call handled", "/webhooks/twilio/incoming-call")
        return Response(content=str(resp), media_type="application/xml", status_code=200)
        
    except Exception as e:
        log_error(f"Call webhook error: {str(e)}")
        resp = VoiceResponse()
        resp.say("Sorry, there was an error processing your call.")
        resp.hangup()
        return Response(content=str(resp), media_type="application/xml", status_code=200)

@router.post(
    "/transcription-callback",
    summary="Handle Twilio transcription callback",
    description="Process voice transcription from Twilio and provide AI response",
    responses={
        200: {"description": "Transcription processed successfully"}
    }
)
async def handle_transcription_callback(
    request: Request,
    From: str = Form(...),
    TranscriptionText: str = Form(...),
    TranscriptionStatus: str = Form(...),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Handle voice transcription callback from Twilio.
    
    Purpose: Process voice-to-text transcription and provide AI responses
    
    Args:
        request: HTTP request
        From: Caller's phone number
        TranscriptionText: Transcribed text
        TranscriptionStatus: Transcription status
        db: Database session
        
    Returns:
        Dict: Processing acknowledgment
    """
    try:
        log_request_start("POST", "/webhooks/twilio/transcription-callback", None)
        
        if TranscriptionStatus != "completed":
            log_error(f"Transcription failed: {TranscriptionStatus}")
            return {"status": "transcription_failed"}
        
        # Normalize phone number
        normalized_from = re.sub(r'\D', '', From)
        
        # Find user by phone number
        user = db.query(User).filter(User.phone_number == int(normalized_from)).first() if normalized_from.isdigit() else None
        
        if not user:
            log_error(f"User not found for transcription callback: {From}")
            return {"status": "user_not_found"}
        
        # Process transcription with AI
        try:
            # Save query to database
            chat_id = f"voice_{normalized_from}"
            db_query = DBQuery(
                userId=user.userId,
                chatId=chat_id,
                query_text=TranscriptionText,
                response=None
            )
            db.add(db_query)
            db.commit()
            db.refresh(db_query)
            
            # Process with AI
            long_term_memory = LongTermMemoryManager()
            short_term_memory = ShortTermMemoryManager()
            
            ai_response = query_openai(
                query=TranscriptionText,
                long_term_memory=long_term_memory,
                short_term_memory=short_term_memory,
                max_tokens=500,
                temperature=0.7,
                aux_data={"current_user_id": user.userId, "source": "voice"}
            )
            
            # Update query with response
            db_query.response = ai_response
            db.commit()
            
            # Send SMS response (since voice callback is async)
            try:
                from server.services import send_twilio_message
                send_twilio_message(From, f"Voice Response: {ai_response}")
            except Exception as sms_error:
                log_error(f"Failed to send SMS response: {str(sms_error)}")
            
            log_response(200, "Transcription processed and response sent", "/webhooks/twilio/transcription")
            return {"status": "processed"}
            
        except Exception as e:
            log_error(f"AI processing error in transcription: {str(e)}")
            return {"status": "processing_error"}
        
    except Exception as e:
        log_error(f"Transcription callback error: {str(e)}")
        return {"status": "error"}
