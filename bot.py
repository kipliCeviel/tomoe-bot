import os
import random
import logging
import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Enable logging early so startup errors are visible in Railway logs
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

load_dotenv()

logging.info("[Startup] Importing agent and storage modules...")
try:
    from agent import process_message, build_spontaneous_prompt, self_study_persona
    from storage import save_chat_id, get_chat_id
    logging.info("[Startup] All imports successful.")
except Exception as _import_err:
    logging.critical(f"[Startup] IMPORT FAILED: {_import_err}", exc_info=True)
    raise


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_allowed_id() -> int | None:
    """Returns the whitelisted chat ID from env, or None if not set."""
    raw = os.getenv("ALLOWED_CHAT_ID", "").strip()
    if raw.isdigit():
        return int(raw)
    return None


def is_allowed(update: Update) -> bool:
    """Returns True only if the user is the whitelisted owner."""
    allowed_id = get_allowed_id()
    if allowed_id is None:
        return True  # Kalau belum diset, semua bisa akses (untuk setup awal)
    return update.effective_chat.id == allowed_id


async def _send_chunks(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, max_length: int = 4000):
    """Send a long text in chunks to avoid Telegram's 4096 char limit."""
    for i in range(0, len(text), max_length):
        try:
            await context.bot.send_message(chat_id=chat_id, text=text[i:i + max_length])
        except Exception as e:
            logging.error(f"Failed to send message chunk to {chat_id}: {e}")


# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Simple health check — no Redis, no AI. Just confirms bot is alive."""
    from storage import _using_redis
    redis_status = "✅ Redis terhubung" if _using_redis() else "⚠️ Redis tidak terhubung (pakai file lokal)"
    await update.message.reply_text(
        f"🏓 Pong! Bot hidup.\n{redis_status}\nChat ID: `{update.effective_chat.id}`",
        parse_mode="Markdown"
    )


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Returns the user's Telegram Chat ID."""
    await update.message.reply_text(f"Chat ID kamu: `{update.effective_chat.id}`", parse_mode="Markdown")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    if not is_allowed(update):
        return
    user = update.effective_user
    save_chat_id(update.effective_chat.id)
    await update.message.reply_html(
        f"Eh.. halo {user.mention_html()}.. kamu perlu apanih ? apa kamu mau ngobrol bebas sama aku? kebetulan aku gak sibuk sibuk banget kok"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    if not is_allowed(update):
        return
    await update.message.reply_text("Ngobrol aja santai bareng aku! Kalau butuh info dari internet, nanti aku bantu cariin ya.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the user message and send to agent."""
    if not is_allowed(update):
        return
    user_message = update.message.text
    save_chat_id(update.effective_chat.id)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    reply = process_message(user_message)

    max_length = 4000
    for i in range(0, len(reply), max_length):
        await update.message.reply_text(reply[i:i + max_length])


# ---------------------------------------------------------------------------
# Manual Test Commands
# ---------------------------------------------------------------------------

async def test_morning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to manually trigger morning update for testing."""
    if not is_allowed(update):
        return
    save_chat_id(update.effective_chat.id)
    await update.message.reply_text("Bentar ya Kak, Tomoe lagi nyiapin pesan pagi buat kamu...")
    await send_scheduled_message(context, "morning")


async def test_spontaneous(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to manually trigger a random spontaneous message."""
    if not is_allowed(update):
        return
    save_chat_id(update.effective_chat.id)
    await update.message.reply_text("Bentar, Tomoe lagi mikirin mau ngomong apa...")
    await send_scheduled_message(context, "random")


async def study_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manually trigger Tomoe's self-study session."""
    if not is_allowed(update):
        return
    await update.message.reply_text(
        "Oke oke, Tomoe lagi baca-baca dulu ya... bentar ya jangan ganggu dulu~ 📚"
    )
    try:
        result = self_study_persona()
        await update.message.reply_text(f"📖 Hasil belajar Tomoe:\n\n{result}")
    except Exception as e:
        logging.error(f"Self-study command error: {e}")
        await update.message.reply_text("Aduh, error pas lagi belajar. Coba lagi nanti ya.")


# ---------------------------------------------------------------------------
# Scheduled Message Senders
# ---------------------------------------------------------------------------

async def send_scheduled_message(context: ContextTypes.DEFAULT_TYPE, message_type: str) -> None:
    """Core function to build and send a spontaneous message of a given type."""
    chat_id = get_chat_id()
    if not chat_id:
        logging.warning(f"Scheduled message '{message_type}' triggered but no chat_id saved yet.")
        return

    logging.info(f"Sending spontaneous message type='{message_type}' to chat_id={chat_id}")
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action='typing')
    except Exception as e:
        logging.error(f"Failed to send chat action: {e}")

    prompt = build_spontaneous_prompt(message_type)
    reply = process_message(prompt)
    await _send_chunks(context, chat_id, reply)


async def send_morning_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job: 06:00 WIB — Morning greeting with weather."""
    await send_scheduled_message(context, "morning")


async def send_lunch_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job: 12:15 WIB — Istirahat siang di kantin."""
    await send_scheduled_message(context, "lunch")


async def send_afternoon_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job: 15:30 WIB — Habis sekolah / pulang."""
    await send_scheduled_message(context, "afternoon")


async def send_evening_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job: 20:00 WIB — Malam santai."""
    await send_scheduled_message(context, "evening")


async def send_late_night_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job: 22:30 WIB — Begadang iseng."""
    await send_scheduled_message(context, "late_night")


async def send_random_spontaneous(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job: runs every hour, 15% chance of sending a random spontaneous message."""
    chance = random.random()
    logging.info(f"Random spontaneous check: rolled {chance:.2f} (threshold 0.15)")
    if chance < 0.15:
        await send_scheduled_message(context, "random")
    else:
        logging.info("Random spontaneous: skipped this hour.")


async def run_daily_self_study(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job: 03:00 WIB daily — Tomoe studies her own persona from the internet."""
    logging.info("[Self-Study Job] Running daily persona self-study...")
    try:
        result = self_study_persona()
        logging.info(f"[Self-Study Job] Done: {result}")
    except Exception as e:
        logging.error(f"[Self-Study Job] Error: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Start the bot."""
    token = os.getenv("TELEGRAM_TOKEN")

    if not token or token == "your_telegram_bot_token_here":
        print("ERROR: TELEGRAM_TOKEN belum diatur di file .env. Silakan isi terlebih dahulu.")
        return

    application = ApplicationBuilder().token(token).build()

    job_queue = application.job_queue
    if job_queue:
        jakarta_tz = datetime.timezone(datetime.timedelta(hours=7))

        # --- Terjadwal harian ---
        job_queue.run_daily(send_morning_update,    time=datetime.time(hour=6,  minute=0,  tzinfo=jakarta_tz))
        job_queue.run_daily(send_lunch_update,      time=datetime.time(hour=12, minute=15, tzinfo=jakarta_tz))
        job_queue.run_daily(send_afternoon_update,  time=datetime.time(hour=15, minute=30, tzinfo=jakarta_tz))
        job_queue.run_daily(send_evening_update,    time=datetime.time(hour=20, minute=0,  tzinfo=jakarta_tz))
        job_queue.run_daily(send_late_night_update, time=datetime.time(hour=22, minute=30, tzinfo=jakarta_tz))

        # --- Self-study harian jam 03:00 WIB ---
        job_queue.run_daily(run_daily_self_study,   time=datetime.time(hour=3,  minute=0,  tzinfo=jakarta_tz))

        # --- Random spontaneous: cek tiap jam ---
        job_queue.run_repeating(
            send_random_spontaneous,
            interval=3600,
            first=60,
        )

        logging.info(
            "Scheduled jobs: morning(06:00), lunch(12:15), afternoon(15:30), "
            "evening(20:00), late_night(22:30), self_study(03:00), random_hourly."
        )
    else:
        logging.warning("JobQueue is not enabled. Scheduled messages will not work.")

    # Commands
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("myid", myid_command))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("testmorning", test_morning))
    application.add_handler(CommandHandler("testspontaneous", test_spontaneous))
    application.add_handler(CommandHandler("study", study_command))

    # Messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is starting... Press Ctrl-C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
