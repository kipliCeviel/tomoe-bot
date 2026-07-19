import os
import logging
import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from agent import process_message

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

load_dotenv()

CHAT_ID_FILE = "chat_id.txt"

def save_chat_id(chat_id: int):
    with open(CHAT_ID_FILE, "w") as f:
        f.write(str(chat_id))

def get_chat_id():
    if os.path.exists(CHAT_ID_FILE):
        with open(CHAT_ID_FILE, "r") as f:
            try:
                return int(f.read().strip())
            except ValueError:
                return None
    return None

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

async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Returns the user's Telegram Chat ID."""
    await update.message.reply_text(f"Chat ID kamu: `{update.effective_chat.id}`", parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    if not is_allowed(update):
        return  # Diam-diam abaikan user lain
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
        return  # Diam-diam abaikan user lain
    user_message = update.message.text
    save_chat_id(update.effective_chat.id)
    
    # Send "typing..." action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    # Process message via LangChain Agent
    reply = process_message(user_message)
    
    # Batas maksimal teks Telegram adalah 4096 karakter
    max_length = 4000
    for i in range(0, len(reply), max_length):
        await update.message.reply_text(reply[i:i+max_length])

async def send_morning_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends daily weather and motivation at 6 AM."""
    chat_id = get_chat_id()
    if not chat_id:
        logging.warning("Daily morning update triggered but no chat_id is saved yet.")
        return

    logging.info(f"Sending daily morning update to chat_id: {chat_id}")
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action='typing')
    except Exception as e:
        logging.error(f"Failed to send chat action: {e}")

    jakarta_tz = datetime.timezone(datetime.timedelta(hours=7))
    now = datetime.datetime.now(jakarta_tz)
    time_str = now.strftime("%-H:%M")  # e.g. "6:00" or "22:15"
    day_str = now.strftime("%A, %-d %B %Y")  # e.g. "Sunday, 19 July 2025"

    prompt = (
        f"[SISTEM] Sekarang jam {time_str} WIB, hari {day_str}. "
        "Kamu sebagai Koga Tomoe, pacar yang tsundere, sedang MENGIRIM PESAN SENDIRI ke pacarmu (bukan menjawab pertanyaan). "
        "Cariin dulu info cuaca hari ini di Bekasi, lalu kirim pesan yang terasa natural sesuai waktu sekarang — "
        "kalau pagi, semangatin buat kerja; kalau siang, tanyain kabar sambil malu-maluin; kalau malam, tunjukin perhatian tapi gengsi. "
        "Mulai dengan cara yang spontan dan alami dari kamu. Jangan pakai bahasa Jepang romaji."
    )
    reply = process_message(prompt)
    
    max_length = 4000
    for i in range(0, len(reply), max_length):
        try:
            await context.bot.send_message(chat_id=chat_id, text=reply[i:i+max_length])
        except Exception as e:
            logging.error(f"Failed to send morning message to {chat_id}: {e}")

async def test_morning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to manually trigger morning update for testing."""
    save_chat_id(update.effective_chat.id)
    await update.message.reply_text("Bentar ya Kak, Tomoe lagi nyiapin pesan pagi buat kamu...")
    await send_morning_update(context)

def main() -> None:
    """Start the bot."""
    token = os.getenv("TELEGRAM_TOKEN")
    
    if not token or token == "your_telegram_bot_token_here":
        print("ERROR: TELEGRAM_TOKEN belum diatur di file .env. Silakan isi terlebih dahulu.")
        return

    # Create the Application and pass it your bot's token.
    application = ApplicationBuilder().token(token).build()

    # Get the job queue
    job_queue = application.job_queue
    if job_queue:
        # Jakarta time (UTC+7)
        jakarta_tz = datetime.timezone(datetime.timedelta(hours=7))
        target_time = datetime.time(hour=6, minute=0, second=0, tzinfo=jakarta_tz)
        job_queue.run_daily(send_morning_update, time=target_time)
        logging.info("Daily morning update job scheduled for 06:00 AM Jakarta time.")
    else:
        logging.warning("JobQueue is not enabled. Daily updates will not work.")

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("myid", myid_command))  # No whitelist - semua bisa pakai untuk setup
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("testmorning", test_morning))

    # on non command i.e message - process via AI agent
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    print("Bot is starting... Press Ctrl-C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
