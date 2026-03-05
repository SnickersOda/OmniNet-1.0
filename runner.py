#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OmniumAI - Runner для Flask + Telegram Bot
Запускает оба одновременно в одном процессе
"""

import os
import sys
import threading
import logging
from datetime import datetime, timedelta
import json

# Flask
from flask import Flask, request, jsonify, Response, stream_with_context
from groq import Groq

# Telegram
import asyncio
from telegram import Update, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, PreCheckoutQueryHandler, SuccessfulPaymentHandler, filters, ContextTypes

# Firebase
import firebase_admin
from firebase_admin import firestore, auth as fb_auth

# ============================================================================
# ЛОГИРОВАНИЕ
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIG
# ============================================================================

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
PORT = int(os.environ.get("PORT", 10000))

# Firebase
try:
    firebase_admin.initialize_app()
except ValueError:
    pass

db = firestore.client()

# ============================================================================
# FLASK APP
# ============================================================================

app = Flask(__name__)
app.json.ensure_ascii = False

# ============================================================================
# FIRESTORE ФУНКЦИИ (используются обеими частями)
# ============================================================================

def get_user_plan(user_id: str) -> str:
    try:
        uid = str(user_id)
        doc = db.collection("users").document(uid).collection("billing").document("subscription").get()
        if doc.exists:
            sub = doc.to_dict()
            if sub.get("status") == "active":
                return sub.get("plan", "free")
    except Exception as e:
        logger.error(f"Error getting plan: {e}")
    return "free"

def get_user_usage(user_id: str) -> dict:
    try:
        uid = str(user_id)
        doc = db.collection("users").document(uid).collection("billing").document("usage").get()
        
        if doc.exists:
            usage = doc.to_dict()
        else:
            usage = {
                "messages_today": 0,
                "messages_this_month": 0,
                "last_reset_day": datetime.utcnow().timestamp(),
                "last_reset_month": datetime.utcnow().replace(day=1).timestamp(),
            }
        
        last_reset_day = datetime.fromtimestamp(usage.get("last_reset_day", 0))
        if last_reset_day.date() != datetime.utcnow().date():
            usage["messages_today"] = 0
            usage["last_reset_day"] = datetime.utcnow().timestamp()
        
        return usage
    except Exception as e:
        logger.error(f"Error getting usage: {e}")
        return {"messages_today": 0, "messages_this_month": 0}

def increment_usage(user_id: str):
    try:
        uid = str(user_id)
        usage = get_user_usage(user_id)
        usage["messages_today"] = usage.get("messages_today", 0) + 1
        usage["messages_this_month"] = usage.get("messages_this_month", 0) + 1
        db.collection("users").document(uid).collection("billing").document("usage").set(usage, merge=True)
    except Exception as e:
        logger.error(f"Error incrementing usage: {e}")

def activate_pro(user_id: str):
    try:
        uid = str(user_id)
        now = datetime.utcnow()
        period_end = now + timedelta(days=30)
        
        db.collection("users").document(uid).collection("billing").document("subscription").set({
            "plan": "pro",
            "status": "active",
            "payment_method": "telegram_stars",
            "current_period_end": period_end.timestamp(),
            "created_at": now.timestamp(),
            "updated_at": now.timestamp(),
        })
        logger.info(f"✓ PRO activated for {user_id}")
    except Exception as e:
        logger.error(f"Error activating PRO: {e}")

def check_rate_limit(user_id: str, plan: str) -> tuple:
    usage = get_user_usage(user_id)
    
    if plan == "free":
        if usage.get("messages_today", 0) >= 50:
            return False, "❌ Дневной лимит (50/день). /upgrade на PRO!"
    
    return True, "OK"

# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "running"}), 200

@app.route("/", methods=["GET"])
def index():
    return """
    <html>
    <head><title>OmniumAI</title></head>
    <body style="background:#04050d;color:#e2e8f8;font-family:sans-serif;padding:40px;text-align:center">
    <h1>🚀 OmniumAI</h1>
    <p>Бот запущен!</p>
    <p>Откройте Telegram бота: @YOUR_BOT_NAME</p>
    <p>/start - начало</p>
    <p>/upgrade - купить PRO (199 ⭐)</p>
    </body>
    </html>
    """, 200, {"Content-Type": "text/html; charset=utf-8"}

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        uid = None
        
        if token:
            try:
                decoded = fb_auth.verify_id_token(token)
                uid = decoded["uid"]
            except:
                pass
        
        data = request.get_json(force=True)
        messages = data.get("messages", [])
        
        if not messages:
            return jsonify({"error": "Нет сообщений"}), 400
        
        if uid:
            plan = get_user_plan(uid)
            allowed, msg = check_rate_limit(uid, plan)
            if not allowed:
                return jsonify({"error": msg}), 429
        
        system_msg = "Ты - помощник OmniumAI. Ответь кратко на русском."
        full_messages = [{"role": "system", "content": system_msg}] + messages
        
        def generate():
            try:
                client = Groq(api_key=GROQ_API_KEY)
                stream = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=full_messages,
                    max_tokens=2048,
                    temperature=0.75,
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta:
                        delta = chunk.choices[0].delta.content or ""
                        if delta:
                            yield "data: " + json.dumps({"delta": delta}, ensure_ascii=False) + "\n\n"
                
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield "data: " + json.dumps({"error": str(e)[:300]}, ensure_ascii=False) + "\n\n"
                yield "data: [DONE]\n\n"
        
        if uid:
            increment_usage(uid)
        
        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================================
# TELEGRAM BOT
# ============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    plan = get_user_plan(str(user_id))
    
    if plan == "pro":
        msg = "👋 Привет! Вы на **PRO плане**!\n✓ 500 сообщений/месяц\n✓ Анализ изображений"
    else:
        msg = "👋 Привет! **БЕСПЛАТНЫЙ план** (50 сообщений/день)\n\n💳 /upgrade на PRO (199 ⭐)"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    plan = get_user_plan(str(user_id))
    
    if plan == "pro":
        await update.message.reply_text("✓ Вы уже на PRO плане!")
        return
    
    prices = [LabeledPrice("OmniumAI PRO месяц", 199)]
    
    await context.bot.send_invoice(
        chat_id=user_id,
        title="OmniumAI PRO",
        description="500 сообщений/месяц + анализ изображений",
        payload="omniumai_pro_monthly",
        currency="XTR",
        prices=prices,
        provider_token="",
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """
🤖 OmniumAI Bot

Команды:
/start - Начало
/help - Помощь
/upgrade - Купить PRO (199 ⭐)
/status - Статус подписки

Просто пишите сообщения!
    """
    await update.message.reply_text(msg, parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    plan = get_user_plan(str(user_id))
    usage = get_user_usage(str(user_id))
    
    if plan == "pro":
        msg = f"⭐ **PRO ПЛАН**\n📊 Сообщений: {usage.get('messages_today', 0)}/500"
    else:
        msg = f"📊 **БЕСПЛАТНЫЙ ПЛАН**\n📊 Сообщений сегодня: {usage.get('messages_today', 0)}/50\n\n/upgrade на PRO"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if not text:
        return
    
    plan = get_user_plan(str(user_id))
    allowed, msg = check_rate_limit(str(user_id), plan)
    
    if not allowed:
        await update.message.reply_text(msg)
        return
    
    await context.bot.send_chat_action(chat_id=user_id, action="typing")
    
    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Ты помощник OmniumAI. Ответь кратко на русском."},
                {"role": "user", "content": text}
            ],
            max_tokens=1024,
            temperature=0.7,
        )
        
        answer = response.choices[0].message.content
        await update.message.reply_text(answer)
        increment_usage(str(user_id))
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:100]}")

async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    activate_pro(str(user_id))
    
    msg = """✅ **Спасибо за покупку!**

🎉 PRO активирован на 30 дней!

✓ 500 сообщений/месяц
✓ Анализ изображений
✓ Приоритетная очередь

/status для проверки
    """
    await context.bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")
    logger.info(f"✓ Payment: {user_id}")

# ============================================================================
# БОТ RUNNER
# ============================================================================

async def run_bot():
    """Запустить Telegram бота"""
    logger.info("🤖 Запуск Telegram бота...")
    
    telegram_app = Application.builder().token(BOT_TOKEN).build()
    
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_cmd))
    telegram_app.add_handler(CommandHandler("upgrade", upgrade))
    telegram_app.add_handler(CommandHandler("status", status))
    
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    telegram_app.add_handler(PreCheckoutQueryHandler(precheckout))
    telegram_app.add_handler(SuccessfulPaymentHandler(successful_payment))
    
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()

def run_bot_in_thread():
    """Запустить бота в отдельном потоке"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 OmniumAI - Запуск Flask + Telegram Bot")
    logger.info("=" * 60)
    
    # Запустить бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot_in_thread, daemon=True)
    bot_thread.start()
    logger.info("✓ Telegram бот запущен в отдельном потоке")
    
    # Запустить Flask
    logger.info(f"✓ Flask запущен на порту {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
