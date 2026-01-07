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

# ========= تحميل المتغيرات =========
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ========= إعداد OpenAI =========
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json",
}

SYSTEM_PROMPT = (
    "أنت ZOZA، مساعد ذكي محترف.\n"
    "ترد باللغة العربية بشكل افتراضي.\n"
    "أسلوبك واضح، مختصر، ومحترم.\n"
    "اشرح التقني ببساطة، ولو مش متأكد قول بوضوح."
)

# أسماء البوت (عربي + إنجليزي)
BOT_NAMES = ["zoza", "zoza bot", "زوزا"]

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

# ذاكرة بسيطة + Rate limit
memory = defaultdict(lambda: deque(maxlen=8))
last_request = defaultdict(float)
MIN_DELAY = 1.2

# ========= أوامر =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً 👋 أنا زوزا.\n"
        "في الجروبات: منشن @اسم_البوت أو اعمل Reply على كلامي."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "الاستخدام:\n"
        "- منشن @اسم_البوت\n"
        "- Reply على رسالة البوت\n"
        "- أو اكتب: زوزا / zoza\n"
        "واسأل سؤالك مباشرة."
    )

# ========= الرد =========
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id
    text = msg.text.strip()

    # تحكم الجروبات
    is_group = msg.chat.type in ["group", "supergroup"]
    is_reply = msg.reply_to_message and msg.reply_to_message.from_user and msg.reply_to_message.from_user.is_bot
    is_mention = context.bot.username.lower() in text.lower()
    has_name = any(n in text.lower() for n in BOT_NAMES)
    if is_group and not (is_reply or is_mention or has_name):
        return

    # Rate limit
    now = time.time()
    if now - last_request[user_id] < MIN_DELAY:
        await msg.reply_text("استنى ثانية كده 👀")
        return
    last_request[user_id] = now

    memory[user_id].append(text)
    user_context = " ".join(memory[user_id])

    payload = {
        "model": "gpt-4o-mini",
        "temperature": 0.4,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_context},
        ],
    }

    try:
        r = requests.post(
            OPENAI_URL,
            headers=OPENAI_HEADERS,
            json=payload,
            timeout=30
        )
        r.raise_for_status()
        data = r.json()
        reply_text = data["choices"][0]["message"]["content"]
    except Exception as e:
        logging.error(e)
        reply_text = "حاليًا في مشكلة مؤقتة 🤖 جرّب كمان شوية."

    await msg.reply_text(reply_text)

# ========= تشغيل =========
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    logging.info("ZOZA Bot running (OPENAI MODE)")
    app.run_polling()

if __name__ == "__main__":
    main()
