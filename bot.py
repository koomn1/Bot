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

# ================== تحميل المتغيرات ==================
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ================== OpenRouter ==================
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://t.me/zoza_bot",
    "X-Title": "ZOZA Telegram Bot"
}

# موديل مجاني
MODEL = "mistralai/mistral-7b-instruct:free"

# ================== إعدادات عامة ==================
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

SYSTEM_PROMPT = (
    "أنت مساعد ذكي اسمه زوزا. "
    "ترد باللغة العربية، بأسلوب محترم وواضح. "
    "اشرح ببساطة ولو السؤال تقني ادِ مثال."
)

BOT_NAMES = ["zoza", "zoza bot", "زوزا"]

memory = defaultdict(lambda: deque(maxlen=6))
last_request = defaultdict(float)
MIN_DELAY = 1.0

# ================== أوامر ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً 👋\n"
        "أنا زوزا 🤖 مساعد ذكي.\n"
        "في الجروبات كلّمني بالمنشن أو اعمل Reply."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "الاستخدام:\n"
        "- منشن @اسم_البوت\n"
        "- أو Reply على رسالة البوت\n"
        "- أو اكتب: زوزا / zoza"
    )

# ================== الرد الذكي ==================
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id
    text = msg.text.strip()

    is_group = msg.chat.type in ["group", "supergroup"]
    is_reply = msg.reply_to_message and msg.reply_to_message.from_user.is_bot
    is_mention = context.bot.username.lower() in text.lower()
    has_name = any(n in text.lower() for n in BOT_NAMES)

    if is_group and not (is_reply or is_mention or has_name):
        return

    now = time.time()
    if now - last_request[user_id] < MIN_DELAY:
        await msg.reply_text("استنى ثانية 👀")
        return
    last_request[user_id] = now

    memory[user_id].append(text)

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": " ".join(memory[user_id])}
        ],
        "temperature": 0.7
    }

    try:
        r = requests.post(OPENROUTER_URL, headers=HEADERS, json=payload, timeout=30)
        r.raise_for_status()
        reply_text = r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logging.error(e)
        reply_text = "حصلت مشكلة مؤقتة، جرّب تاني كمان شوية."

    await msg.reply_text(reply_text)

# ================== تشغيل ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    logging.info("ZOZA Bot running (OPENROUTER MODE)")
    app.run_polling()

if __name__ == "__main__":
    main()
