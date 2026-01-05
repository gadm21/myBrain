"""
Daily Reset Job for Task Management

This job runs at the start of each day to:
1. Clear/reset daily tasks
2. Send SMS to Gad asking for today's tasks
"""

import logging
import schedule
import time
from datetime import datetime
from server.periodic_intelligence import get_daily_tasks, get_stats_line, MORNING_ASK_TEMPLATES
import random
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_morning_sms(message: str):
    """Send SMS via Twilio."""
    try:
        from twilio.rest import Client
        
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
        gad_number = "+18073587137"
        
        if not all([account_sid, auth_token, twilio_number]):
            logger.error("[Daily Reset] Missing Twilio credentials")
            return False
        
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body=message,
            from_=twilio_number,
            to=gad_number
        )
        
        logger.info(f"[Daily Reset] Morning SMS sent successfully. SID: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"[Daily Reset] Error sending SMS: {e}", exc_info=True)
        return False

def daily_reset_job():
    """
    Daily reset job that:
    1. Checks if tasks exist for today
    2. If not, sends morning SMS asking for tasks
    """
    logger.info("[Daily Reset] Running daily reset job...")
    
    try:
        # Check if tasks already set for today
        current_tasks = get_daily_tasks()
        today = datetime.now().strftime("%Y-%m-%d")
        
        if current_tasks and current_tasks.get("date") == today:
            logger.info(f"[Daily Reset] Tasks already set for today ({today}). Skipping SMS.")
            return
        
        # No tasks set - send morning SMS
        stats_line = get_stats_line()
        template = random.choice(MORNING_ASK_TEMPLATES)
        message = template.format(stats_line=stats_line)
        
        logger.info(f"[Daily Reset] No tasks for today. Sending morning SMS...")
        success = send_morning_sms(message)
        
        if success:
            logger.info("[Daily Reset] ✅ Daily reset completed successfully")
        else:
            logger.error("[Daily Reset] ❌ Failed to send morning SMS")
            
    except Exception as e:
        logger.error(f"[Daily Reset] Error in daily reset job: {e}", exc_info=True)

def start_daily_reset_scheduler():
    """
    Start the daily reset scheduler.
    Runs at 5:00 AM every day.
    """
    logger.info("[Daily Reset] Starting daily reset scheduler...")
    
    # Schedule job for 5:00 AM every day
    schedule.every().day.at("05:00").do(daily_reset_job)
    
    logger.info("[Daily Reset] Scheduler started. Job will run at 5:00 AM daily.")
    
    # Run the scheduler loop
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    # For testing: run the job immediately
    logger.info("[Daily Reset] Running job immediately for testing...")
    daily_reset_job()
    
    # Uncomment to start the scheduler
    # start_daily_reset_scheduler()
