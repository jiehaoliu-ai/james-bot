import logging
import asyncio
from telegram import Update
from telegram.error import Conflict
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from settings import TELEGRAM_TOKEN, TIMEZONE
from message_handler import handle_message
from callback_handler import handle_callback
from command_handler import (
    start_command, digest_command, todos_command,
    expenses_command, monthly_command, ytd_command,
    personal_command, palfinger_command,
    thoughts_command, help_command
)
from digest_service import send_morning_digest, send_evening_digest

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(app: Application):
    scheduler = AsyncIOScheduler(timezone=pytz.timezone(TIMEZONE))
    scheduler.add_job(
        send_morning_digest,
        CronTrigger(hour=8, minute=0, timezone=pytz.timezone(TIMEZONE)),
        args=[app.bot], id='morning_digest'
    )
    scheduler.add_job(
        send_evening_digest,
        CronTrigger(hour=22, minute=0, timezone=pytz.timezone(TIMEZONE)),
        args=[app.bot], id='evening_digest'
    )
    scheduler.start()
    logger.info("Scheduler started — 8am and 10pm SGT digests active")


async def error_handler(update, context):
    if isinstance(context.error, Conflict):
        logger.warning("Conflict — another instance running, waiting 15s...")
        await asyncio.sleep(15)
    else:
        logger.error(f"Error: {context.error}")


def main():
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("digest", digest_command))
    app.add_handler(CommandHandler("todos", todos_command))
    app.add_handler(CommandHandler("expenses", expenses_command))
    app.add_handler(CommandHandler("monthly", monthly_command))
    app.add_handler(CommandHandler("ytd", ytd_command))
    app.add_handler(CommandHandler("personal", personal_command))
    app.add_handler(CommandHandler("palfinger", palfinger_command))
    app.add_handler(CommandHandler("thoughts", thoughts_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(error_handler)

    logger.info("James Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == '__main__':
    main()
