import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import get_connection

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def check_reminders(app):
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, title, event_date, event_time FROM events WHERE event_date = ? AND event_time = ?",
        (today, current_time)
    )
    events = cursor.fetchall()
    conn.close()

    for event in events:
        try:
            await app.bot.send_message(
                chat_id=event["user_id"],
                text=f" Reminder: {event['title']}"
            )
            logger.info(f"Reminder sent to user {event['user_id']} for event: {event['title']}")
        except Exception as e:
            logger.error(f"Failed to send reminder: {e}")

async def start_scheduler(app):
    scheduler.add_job(
        check_reminders,
        "interval",
        minutes=1,
        args=[app],
        id="reminder_check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started - checking reminders every minute")
