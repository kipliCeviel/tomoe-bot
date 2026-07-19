import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from agent import process_message

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

load_dotenv()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"Eh.. halo {user.mention_html()}.. kamu perlu apanih ? apa kamu mau ngobrol bebas sama aku? kebetulan aku gak sibuk sibuk banget kok"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Ngobrol aja santai bareng aku! Kalau butuh info dari internet, nanti aku bantu cariin ya.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the user message and send to agent."""
    user_message = update.message.text
    
    # Send "typing..." action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    # Process message via LangChain Agent
    reply = process_message(user_message)
    
    # Batas maksimal teks Telegram adalah 4096 karakter
    max_length = 4000
    for i in range(0, len(reply), max_length):
        await update.message.reply_text(reply[i:i+max_length])

def main() -> None:
    """Start the bot."""
    token = os.getenv("TELEGRAM_TOKEN")
    
    if not token or token == "your_telegram_bot_token_here":
        print("ERROR: TELEGRAM_TOKEN belum diatur di file .env. Silakan isi terlebih dahulu.")
        return

    # Create the Application and pass it your bot's token.
    application = ApplicationBuilder().token(token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - process via AI agent
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    print("Bot is starting... Press Ctrl-C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
