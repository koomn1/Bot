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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ================== إعداد Gemini ==================
API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
)
HEADERS = {"Content-Type": "application/json"}

# ================== إعدادات عامة ==================
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

SYSTEM_PROMPT = (
    "أنت مساعد ذكي اسمه زوزا. "
    "ترد باللغة العربية فقط، بأسلوب محترم وواضح. "
    "اشرح ببساطة، ولو السؤال تقني ادِ مثال. "
    "تجنب خلط الإنجليزية بالعربية."
)

# أسماء البوت (عربي + إنجليزي)
BOT_NAMES = ["zoza", "zoza bot", "زوزا"]

# ذاكرة قصيرة + Rate limit
memory = defaultdict(lambda: deque(maxlen=6))
last_request = defaultdict(float)
MIN_DELAY = 1.2

# ================== أوامر ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً 👋\n"
        "أنا زوزا 🤖 مساعد ذكي.\n"
        "في الجروبات كلّمني بالمنشن أو اعمل Reply على كلامي."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "الاستخدام:\n"
        "- منشن @اسم_البوت\n"
        "- Reply على رسالة البوت\n"
        "- أو اكتب: زوزا / zoza\n"
        "واسأل سؤالك."
    )

# ================== الرد الذكي ==================
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id
    text = msg.text.strip()

    # ---- تحكم الجروبات ----
    is_group = msg.chat.type in ["group", "supergroup"]
    is_reply = msg.reply_to_message and msg.reply_to_message.from_user.is_bot
    is_mention = context.bot.username.lower() in text.lower()
    has_name = any(n in text.lower() for n in BOT_NAMES)

    if is_group and not (is_reply or is_mention or has_name):
        return

    # ---- Rate limit ----
    now = time.time()
    if now - last_request[user_id] < MIN_DELAY:
        await msg.reply_text("استنى ثانية 👀")
        return
    last_request[user_id] = now

    logging.info(f"User {user_id}: {text}")

    # ---- ذاكرة ----
    memory[user_id].append(text)
    prompt = SYSTEM_PROMPT + "\nسؤال المستخدم:\n" + " ".join(memory[user_id])

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    try:
        r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        reply_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        logging.error(e)
        reply_text = (
            "حاليًا خدمة الذكاء الاصطناعي مش متاحة 🤖\n"
            "جرّب كمان شوية أو صيّغ سؤالك بشكل أبسط."
        )

    await msg.reply_text(reply_text)

# ================== تشغيل ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    logging.info("ZOZA Bot running (GEMINI 1.5 FLASH)")
    app.run_polling()

if __name__ == "__main__":
    main()
