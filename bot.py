import os
import time
import logging
import requests
from collections import defaultdict, deque
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# ================== إعدادات ==================
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
)

HEADERS = {"Content-Type": "application/json"}

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

SYSTEM_PROMPT = """
You are ZOZA, a professional AI assistant.
Your responses are clear, concise, and accurate.
Explain technical topics with simple examples.
Remain professional unless the user uses casual language.
Avoid repetition.
If unsure, say so honestly.
"""

# أسماء البوت (عربي + إنجليزي)
BOT_NAMES = ["zoza", "zoza bot", "زوزا"]

# ================== ذاكرة ==================
memory = defaultdict(lambda: deque(maxlen=12))
last_request = defaultdict(float)
MIN_DELAY = 1.2

# ================== أوامر ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome 👋\n"
        "I'm ZOZA, your professional AI assistant.\n"
        "Mention me or reply to my message in groups."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Usage:\n"
        "- Mention @botname\n"
        "- Reply to my message\n"
        "- Or say: زوزا / zoza\n\n"
        "Then send your question."
    )

# ================== الرد الذكي ==================
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    text = message.text.strip()

    # ---- تحكم الجروبات ----
    is_group = message.chat.type in ["group", "supergroup"]
    is_reply = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.is_bot
    )
    is_mention = context.bot.username.lower() in text.lower()
    has_name = any(name in text.lower() for name in BOT_NAMES)

    if is_group and not (is_reply or is_mention or has_name):
        return  # تجاهل الكلام العادي في الجروب

    # ---- Rate limit ----
    now = time.time()
    if now - last_request[user_id] < MIN_DELAY:
        await message.reply_text(
            "Please wait a moment before sending another message."
        )
        return
    last_request[user_id] = now

    logging.info(f"User {user_id}: {text}")

    # ---- الذاكرة ----
    memory[user_id].append(f"User: {text}")
    context_text = SYSTEM_PROMPT + "\n" + "\n".join(memory[user_id]) + "\nZOZA:"

    payload = {
        "contents": [
            {"parts": [{"text": context_text}]}
        ]
    }

    try:
        r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=25)
        r.raise_for_status()
        reply_text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logging.error(e)
        reply_text = (
            "The service is temporarily unavailable. "
            "Please try again shortly."
        )

    memory[user_id].append(f"ZOZA: {reply_text}")
    await message.reply_text(reply_text)

# ================== تشغيل ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

    logging.info("ZOZA Bot running (GROUP SAFE MODE)")
    app.run_polling()

if __name__ == "__main__":
    main().run_polling()

if __name__ == "__main__":
    main()