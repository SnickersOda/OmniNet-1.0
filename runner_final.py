#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OmniumAI - Flask + Telegram Bot с модальным окном планов
"""

import os
import threading
import logging
from datetime import datetime, timedelta
import json
import asyncio

from flask import Flask, request, jsonify, Response, stream_with_context
from groq import Groq

from telegram import Update, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, PreCheckoutQueryHandler, filters, ContextTypes
from telegram import SuccessfulPayment

import firebase_admin
from firebase_admin import firestore, auth as fb_auth

# ============================================================================
# CONFIG
# ============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
PORT = int(os.environ.get("PORT", 10000))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "YOUR_BOT_NAME")

try:
    firebase_admin.initialize_app()
except ValueError:
    pass

db = firestore.client()
app = Flask(__name__)
app.json.ensure_ascii = False

# ============================================================================
# FIRESTORE
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
        logger.error(f"Error: {e}")
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
        logger.error(f"Error: {e}")
        return {"messages_today": 0}

def increment_usage(user_id: str):
    try:
        uid = str(user_id)
        usage = get_user_usage(user_id)
        usage["messages_today"] = usage.get("messages_today", 0) + 1
        usage["messages_this_month"] = usage.get("messages_this_month", 0) + 1
        db.collection("users").document(uid).collection("billing").document("usage").set(usage, merge=True)
    except Exception as e:
        logger.error(f"Error: {e}")

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
        logger.info(f"✓ PRO: {user_id}")
    except Exception as e:
        logger.error(f"Error: {e}")

def check_rate_limit(user_id: str, plan: str) -> tuple:
    usage = get_user_usage(user_id)
    
    if plan == "free":
        if usage.get("messages_today", 0) >= 50:
            return False, "❌ Дневной лимит (50/день)"
    
    return True, "OK"

# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def index():
    html = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>OmniumAI</title>
<style>
:root{--bg:#04050d;--s1:#080b15;--s2:#0d1120;--accent:#38bdf8;--text:#e2e8f8;--muted:#4a5580;--border:rgba(255,255,255,.06);}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:var(--bg);color:var(--text);font-family:sans-serif;overflow:hidden;}
#app{height:100%;display:flex;flex-direction:column;}
header{height:54px;display:flex;align-items:center;justify-content:space-between;padding:0 16px;border-bottom:1px solid var(--border);}
.logo{font-weight:bold;font-size:1.2rem;}
.btn-pricing{padding:10px 20px;border-radius:8px;border:1px solid var(--accent);background:transparent;color:var(--accent);cursor:pointer;font-weight:bold;}
.btn-pricing:hover{background:rgba(56,189,248,.1);}
#chatArea{flex:1;display:flex;flex-direction:column;overflow:hidden;}
#chatBox{flex:1;overflow-y:auto;padding:20px;}
.welcome{text-align:center;padding:40px 20px;}
.welcome h2{font-size:2rem;margin-bottom:20px;}
.welcome p{color:var(--muted);margin-bottom:20px;}
.msg-row{display:flex;gap:12px;margin:12px 0;}
.msg-row.user{flex-direction:row-reverse;}
.bubble{padding:12px 16px;border-radius:12px;background:rgba(13,17,32,.95);border:1px solid rgba(56,189,248,.1);word-wrap:break-word;white-space:pre-wrap;}
.bubble.user{background:rgba(56,189,248,.1);}
.input-area{padding:16px;border-top:1px solid var(--border);}
.iw{display:flex;align-items:flex-end;gap:8px;background:rgba(13,17,32,.94);border:1px solid var(--border);border-radius:12px;padding:8px 12px;}
#msgInput{flex:1;background:none;border:none;outline:none;color:var(--text);font-size:.9rem;resize:none;}
.btn-send{width:38px;height:38px;border-radius:8px;border:none;cursor:pointer;background:linear-gradient(135deg,var(--accent),#818cf8);color:#000;font-weight:bold;}

/* МОДАЛЬНОЕ ОКНО */
#pricingModal{display:none;position:fixed;inset:0;z-index:700;background:rgba(4,5,13,.95);align-items:center;justify-content:center;padding:20px;overflow-y:auto;}
#pricingModal.open{display:flex;}
.modal-content{background:var(--s2);border:1px solid var(--border);border-radius:20px;padding:40px;max-width:900px;width:100%;}
.modal-header{text-align:center;margin-bottom:40px;}
.modal-header h2{font-size:2rem;margin-bottom:10px;}
.modal-header p{color:var(--muted);font-size:1.1rem;}
.pricing-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:30px;margin-bottom:30px;}
.plan-card{border:1px solid var(--border);border-radius:16px;padding:30px;background:var(--s1);transition:all .3s;}
.plan-card:hover{border-color:var(--accent);}
.plan-card.pro{border-color:var(--accent);background:rgba(56,189,248,.05);}
.plan-badge{display:inline-block;background:var(--accent);color:#000;padding:6px 14px;border-radius:20px;font-size:.75rem;font-weight:bold;margin-bottom:12px;}
.plan-name{font-size:1.4rem;font-weight:bold;margin-bottom:8px;}
.plan-price{font-size:2.2rem;font-weight:bold;margin-bottom:4px;}
.plan-price span{font-size:.75rem;color:var(--muted);}
.plan-desc{color:var(--muted);font-size:.9rem;margin-bottom:20px;}
.plan-features{list-style:none;margin-bottom:25px;}
.plan-features li{padding:8px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:.9rem;}
.plan-features li::before{content:'✓ ';color:var(--accent);font-weight:bold;margin-right:8px;}
.plan-features li:last-child{border-bottom:none;}
.plan-btn{width:100%;padding:14px;border-radius:12px;border:none;cursor:pointer;font-weight:bold;font-size:.95rem;transition:all .2s;}
.plan-btn.free{background:rgba(255,255,255,.05);color:var(--text);border:1px solid var(--border);}
.plan-btn.free:hover{background:rgba(255,255,255,.1);}
.plan-btn.pro{background:var(--accent);color:#000;}
.plan-btn.pro:hover{transform:translateY(-2px);box-shadow:0 10px 30px rgba(56,189,248,.4);}

.close-modal{position:absolute;top:20px;right:30px;background:none;border:none;color:var(--text);font-size:32px;cursor:pointer;width:40px;height:40px;display:flex;align-items:center;justify-content:center;}
.close-modal:hover{color:var(--accent);}
</style>
</head>
<body>
<div id="app">
  <header>
    <div class="logo">🚀 OmniumAI</div>
    <button class="btn-pricing" onclick="openPricing()">💳 Тарифы</button>
  </header>

  <div id="chatArea">
    <div id="chatBox">
      <div class="welcome">
        <h2>✨ OmniumAI</h2>
        <p>Разговаривайте с AI</p>
      </div>
    </div>

    <div class="input-area">
      <div class="iw">
        <textarea id="msgInput" placeholder="Ваше сообщение..." rows="1"></textarea>
        <button class="btn-send" onclick="sendMsg()">→</button>
      </div>
    </div>
  </div>
</div>

<!-- МОДАЛЬНОЕ ОКНО С ПЛАНАМИ -->
<div id="pricingModal" onclick="closePricing(event)">
  <button class="close-modal" onclick="closePricing()">✕</button>
  
  <div class="modal-content" onclick="event.stopPropagation()">
    <div class="modal-header">
      <h2>Выберите свой план</h2>
      <p>Полный доступ к OmniumAI</p>
    </div>

    <div class="pricing-grid">
      <!-- БЕСПЛАТНЫЙ ПЛАН -->
      <div class="plan-card">
        <div class="plan-name">Бесплатный</div>
        <div class="plan-price">0 ₽<span>/месяц</span></div>
        <div class="plan-desc">Для начинающих</div>
        
        <ul class="plan-features">
          <li>50 сообщений в день</li>
          <li>Только текст</li>
          <li>Локальное хранилище</li>
          <li>Базовые функции</li>
        </ul>
        
        <button class="plan-btn free" onclick="closePricing()">Текущий план</button>
      </div>

      <!-- ПРОФЕССИОНАЛЬНЫЙ ПЛАН -->
      <div class="plan-card pro">
        <div class="plan-badge">РЕКОМЕНДУЕТСЯ ⭐</div>
        <div class="plan-name">Профессиональный</div>
        <div class="plan-price">199 ⭐<span>/месяц</span></div>
        <div class="plan-desc">Полный доступ</div>
        
        <ul class="plan-features">
          <li>500 сообщений в месяц</li>
          <li>Анализ изображений (10 МБ)</li>
          <li>Приоритетная очередь</li>
          <li>Облачная синхронизация</li>
          <li>Экспорт MD/PDF</li>
          <li>Поддержка 24/7</li>
        </ul>
        
        <button class="plan-btn pro" onclick="buyProPlan()">Купить PRO</button>
      </div>
    </div>

    <div style="text-align:center;margin-top:30px;padding-top:20px;border-top:1px solid var(--border);font-size:.85rem;color:var(--muted);">
      <p>💳 Платёж через Telegram Stars</p>
      <p>🔒 Безопасно | 📱 Быстро | 🌍 Без документов</p>
    </div>
  </div>
</div>

<script>
let busy = false;

function openPricing() {
  document.getElementById('pricingModal').classList.add('open');
}

function closePricing(e) {
  if (!e || e.target.id === 'pricingModal') {
    document.getElementById('pricingModal').classList.remove('open');
  }
}

function buyProPlan() {
  // Открыть бота и отправить /upgrade
  const botUrl = 'https://t.me/BOT_USERNAME_REPLACE?start=upgrade';
  window.open(botUrl, '_blank');
  closePricing();
}

async function sendMsg() {
  const inp = document.getElementById('msgInput');
  const text = inp.value.trim();
  if (!text || busy) return;
  
  busy = true;
  inp.value = '';
  
  addMsg('user', text);
  
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({messages: [{role: 'user', content: text}]})
    });
    
    if (!res.ok) {
      const d = await res.json();
      addMsg('bot', '❌ ' + (d.error || 'Ошибка'));
      return;
    }
    
    const r = res.body.getReader();
    const dec = new TextDecoder();
    let buf = '', el = null, full = '';
    
    while (true) {
      const {done, value} = await r.read();
      if (done) break;
      buf += dec.decode(value, {stream: true});
      const lines = buf.split('\n');
      buf = lines.pop();
      
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const d = line.slice(5).trim();
        if (d === '[DONE]') break;
        try {
          const o = JSON.parse(d);
          if (o.delta) {
            full += o.delta;
            if (!el) el = addMsg('bot', '');
            el.textContent = full;
          }
        } catch (e) {}
      }
    }
  } catch (err) {
    addMsg('bot', '❌ Ошибка соединения');
  } finally {
    busy = false;
  }
}

function addMsg(role, text) {
  const box = document.getElementById('chatBox');
  const w = box.querySelector('.welcome');
  if (w && role === 'bot') w.remove();
  
  const row = document.createElement('div');
  row.className = 'msg-row ' + role;
  
  const bubble = document.createElement('div');
  bubble.className = 'bubble ' + (role === 'user' ? 'user' : '');
  bubble.textContent = text;
  
  row.appendChild(bubble);
  box.appendChild(row);
  box.scrollTop = box.scrollHeight;
  
  return bubble;
}

document.getElementById('msgInput').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMsg();
  }
});
</script>
</body>
</html>"""
    
    html = html.replace('BOT_USERNAME_REPLACE', BOT_USERNAME)
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)
        messages = data.get("messages", [])
        
        if not messages:
            return jsonify({"error": "Нет сообщений"}), 400
        
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
    args = context.args
    
    # Если пришло с параметром upgrade
    if args and args[0] == 'upgrade':
        await upgrade(update, context)
        return
    
    user_id = update.effective_user.id
    plan = get_user_plan(str(user_id))
    
    if plan == "pro":
        msg = "👋 Привет! Вы на **PRO плане**!\n\n✓ 500 сообщений/месяц\n✓ Анализ изображений\n\nПишите сообщения для ответов!"
    else:
        msg = "👋 Привет! Вы на **БЕСПЛАТНОМ плане** (50 сообщений/день)\n\n💳 Нажмите /upgrade для покупки PRO (199 ⭐)"
    
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
        description="500 сообщений в месяц + анализ изображений + приоритет + облачная синхронизация",
        payload="omniumai_pro_monthly",
        currency="XTR",
        prices=prices,
        provider_token="",
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """🤖 OmniumAI Bot

Команды:
/start - Начало
/help - Помощь
/upgrade - Купить PRO (199 ⭐)
/status - Статус подписки

Просто пишите сообщения для ответов от AI!
    """
    await update.message.reply_text(msg, parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    plan = get_user_plan(str(user_id))
    usage = get_user_usage(str(user_id))
    
    if plan == "pro":
        msg = f"⭐ **PRO ПЛАН**\n\n📊 Сообщений: {usage.get('messages_today', 0)}/500\n✓ Анализ изображений включен\n✓ Приоритетная очередь активна"
    else:
        msg = f"📊 **БЕСПЛАТНЫЙ ПЛАН**\n\nСообщений сегодня: {usage.get('messages_today', 0)}/50\n\n💳 /upgrade на PRO (199 ⭐)"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if not text:
        return
    
    plan = get_user_plan(str(user_id))
    allowed, msg = check_rate_limit(str(user_id), plan)
    
    if not allowed:
        await update.message.reply_text(msg + "\n\n💳 /upgrade для покупки PRO")
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

🎉 Ваша подписка PRO активирована на 30 дней!

✓ 500 сообщений в месяц
✓ Анализ изображений (10 МБ)
✓ Приоритетная очередь
✓ Облачная синхронизация
✓ Экспорт MD/PDF

Теперь вы можете пользоваться всеми функциями!

Команда /status для проверки.
    """
    await context.bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")
    logger.info(f"✓ Payment: {user_id}")

# ============================================================================
# БОТ В ПОТОКЕ
# ============================================================================

async def run_bot():
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
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 OmniumAI - Flask + Telegram Bot")
    logger.info("=" * 60)
    
    bot_thread = threading.Thread(target=run_bot_in_thread, daemon=True)
    bot_thread.start()
    logger.info("✓ Telegram бот запущен в отдельном потоке")
    
    logger.info(f"✓ Flask запущен на порту {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
