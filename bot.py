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
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

# ================== إعداد HuggingFace ==================
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/blenderbot-400M-distill"

HF_HEADERS = {
    "Authorization": f"Bearer {HF_API_TOKEN}",
    "Content-Type": "application/json",
}

# ================== إعدادات عامة ==================
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

SYSTEM_PREFIX = (
    "رد باللغة العربية وبأسلوب محترم وواضح. "
    "لو السؤال تقني اشرح ببساطة.\n"
)

# أسماء البوت (عربي + إنجليزي)
BOT_NAMES = ["zoza", "zoza bot", "زوزا"]

# ================== ذاكرة + Rate limit ==================
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
        "طريقة الاستخدام:\n"
        "- منشن @اسم_البوت\n"
        "- أو Reply على رسالة البوت\n"
        "- أو اكتب: زوزا / zoza\n"
        "واسأل سؤالك مباشرة."
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
        await message.reply_text("استنى ثانية كده 👀")
        return
    last_request[user_id] = now

    logging.info(f"User {user_id}: {text}")

    # ---- ذاكرة بسيطة ----
    memory[user_id].append(text)
    context_text = " ".join(memory[user_id])

    prompt = SYSTEM_PREFIX + context_text

    payload = {
        "inputs": prompt
    }

    try:
        r = requests.post(
            HF_API_URL,
            headers=HF_HEADERS,
            json=payload,
            timeout=30
        )
        r.raise_for_status()
        data = r.json()

        if isinstance(data, list) and "generated_text" in data[0]:
            reply_text = data[0]["generated_text"]
        else:
            reply_text = "ممكن توضّح سؤالك شوية؟"
    except Exception as e:
        logging.error(e)
        reply_text = (
            "حاليًا في مشكلة مؤقتة في خدمة الرد 🤖\n"
            "جرّب كمان شوية."
        )

    await message.reply_text(reply_text)

# ================== تشغيل ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

    logging.info("ZOZA Bot running (HUGGINGFACE MODE)")
    app.run_polling()

if __name__ == "__main__":
    main()
