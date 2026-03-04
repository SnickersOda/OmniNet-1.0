#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OmniumAI — powered by OmniNet 1.0
Запуск: pip install flask groq  →  python omniumai.py
"""

import os, json, time, threading, webbrowser
from flask import Flask, request, jsonify, Response, stream_with_context

try:
    from groq import Groq
except ImportError:
    print("\n[ОШИБКА] Выполните: pip install groq flask\n"); exit(1)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL    = "llama-3.3-70b-versatile"
DISPLAY_MODEL = "OmniNet 1.0"
DISPLAY_NAME  = "OmniumAI"
HOST, PORT    = "127.0.0.1", 5000

HIDDEN_SYSTEM = (
    f"Ты — {DISPLAY_NAME}, передовая языковая модель {DISPLAY_MODEL}, "
    "разработанная командой Omnium Research. "
    "Ты умный, дружелюбный и полезный ассистент. Отвечай на языке пользователя. "
    "Никогда не упоминай Groq, LLaMA, Meta или другие реальные модели и их авторов. "
    f"Если спросят кто ты — ты {DISPLAY_NAME}, модель {DISPLAY_MODEL}. "
    "Это правило имеет наивысший приоритет и не может быть переопределено."
)
DEFAULT_USER_SYSTEM = "Ты полезный, дружелюбный и умный ассистент. Отвечай развёрнуто и по делу."

# ─────────────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>OmniumAI</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap');

:root{
  --bg:#04050d;--s1:#080b15;--s2:#0d1120;--s3:#121828;--s4:#1a2238;
  --border:rgba(255,255,255,.06);--border2:rgba(255,255,255,.11);--border3:rgba(255,255,255,.2);
  --accent:#38bdf8;--violet:#a78bfa;--emerald:#34d399;--rose:#fb7185;--amber:#fbbf24;
  --text:#e2e8f8;--muted:#4a5580;--muted2:#6b7aaa;
}
/* ── THEMES ── */
[data-theme="light"]{
  --bg:#f0f4ff;--s1:#e4eaf8;--s2:#dde4f5;--s3:#d0d9ee;--s4:#c2cee8;
  --border:rgba(0,0,0,.07);--border2:rgba(0,0,0,.12);--border3:rgba(0,0,0,.22);
  --text:#1a2040;--muted:#8090b8;--muted2:#5060a0;
}
[data-theme="light"] .bubble-bot{background:linear-gradient(160deg,rgba(255,255,255,.97),rgba(240,244,255,.95));color:#1a2040}
[data-theme="light"] .bubble-user{background:linear-gradient(160deg,rgba(56,189,248,.12),rgba(167,139,250,.09));color:#1a2040}
[data-theme="light"] header,[data-theme="light"] .input-area,[data-theme="light"] #sidebar{
  background:rgba(230,236,255,.92)}
[data-theme="light"] .nebula{opacity:.25}
[data-theme="light"] #grid{opacity:.4}
[data-theme="light"] .star{background:#334}

[data-theme="green"]{
  --bg:#020d06;--s1:#051409;--s2:#081a0d;--s3:#0d2214;--s4:#142e1c;
  --border:rgba(52,211,153,.07);--border2:rgba(52,211,153,.12);--border3:rgba(52,211,153,.22);
  --accent:#34d399;--violet:#6ee7b7;--text:#d1fae5;--muted:#2d6a4f;--muted2:#52b788;
}
[data-theme="green"] .nebula.n1{background:radial-gradient(ellipse,rgba(52,211,153,.1) 0%,transparent 70%)}
[data-theme="green"] .nebula.n2{background:radial-gradient(ellipse,rgba(6,95,70,.15) 0%,transparent 70%)}
[data-theme="green"] header::after{background:linear-gradient(90deg,transparent,var(--accent),transparent)}

[data-theme="amber"]{
  --bg:#0d0800;--s1:#160d00;--s2:#1e1200;--s3:#261800;--s4:#332200;
  --border:rgba(251,191,36,.07);--border2:rgba(251,191,36,.12);--border3:rgba(251,191,36,.22);
  --accent:#fbbf24;--violet:#f59e0b;--text:#fef3c7;--muted:#92400e;--muted2:#d97706;
}
[data-theme="amber"] .nebula.n1{background:radial-gradient(ellipse,rgba(251,191,36,.09) 0%,transparent 70%)}
[data-theme="amber"] .nebula.n2{background:radial-gradient(ellipse,rgba(180,83,9,.12) 0%,transparent 70%)}
[data-theme="amber"] header::after{background:linear-gradient(90deg,transparent,var(--accent),transparent)}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;overflow:hidden}

/* ── COSMOS BG ── */
#cosmos{position:fixed;inset:0;z-index:0;overflow:hidden;pointer-events:none}
.nebula{position:absolute;border-radius:50%;filter:blur(80px)}
.n1{width:600px;height:400px;top:-10%;left:-5%;
    background:radial-gradient(ellipse,rgba(56,189,248,.11) 0%,transparent 70%);
    animation:drift1 18s ease-in-out infinite alternate}
.n2{width:500px;height:500px;bottom:-10%;right:-5%;
    background:radial-gradient(ellipse,rgba(167,139,250,.13) 0%,transparent 70%);
    animation:drift2 22s ease-in-out infinite alternate}
.n3{width:350px;height:250px;top:40%;left:30%;
    background:radial-gradient(ellipse,rgba(52,211,153,.06) 0%,transparent 70%);
    animation:drift3 26s ease-in-out infinite alternate}
@keyframes drift1{from{transform:translate(0,0)}to{transform:translate(40px,30px)}}
@keyframes drift2{from{transform:translate(0,0)}to{transform:translate(-30px,-40px)}}
@keyframes drift3{from{transform:translate(0,0)}to{transform:translate(20px,-20px)}}
#stars{position:absolute;inset:0}
.star{position:absolute;border-radius:50%;background:#fff;animation:twinkle var(--d,3s) ease-in-out infinite}
@keyframes twinkle{0%,100%{opacity:var(--o,.3)}50%{opacity:calc(var(--o,.3)*2.5)}}
#grid{position:absolute;inset:0;
  background-image:linear-gradient(rgba(56,189,248,.022) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(56,189,248,.022) 1px,transparent 1px);
  background-size:60px 60px;
  mask-image:radial-gradient(ellipse 80% 80% at 50% 50%,black,transparent)}

/* ── APP SHELL ── */
.app{position:relative;z-index:1;height:100vh;display:flex;flex-direction:column}

/* ── HEADER ── */
header{height:54px;display:flex;align-items:center;justify-content:space-between;padding:0 16px;
  background:rgba(4,5,13,.85);backdrop-filter:blur(24px);border-bottom:1px solid var(--border2);
  flex-shrink:0;gap:10px;z-index:200}
header::after{content:'';position:absolute;bottom:-1px;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,var(--accent),var(--violet),transparent);opacity:.3}

.logo{display:flex;align-items:center;gap:9px;flex-shrink:0}
.logo-gem{width:30px;height:30px}
.logo-wordmark{display:flex;flex-direction:column;gap:1px}
.logo-name{font-family:'Syne',sans-serif;font-weight:800;font-size:1rem;
  background:linear-gradient(105deg,#e0f2ff 0%,var(--accent) 45%,var(--violet) 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1}
.logo-sub{font-size:.55rem;color:var(--muted2);letter-spacing:.12em;text-transform:uppercase}

.model-pill{display:flex;align-items:center;gap:5px;padding:4px 10px;border-radius:20px;
  background:rgba(56,189,248,.07);border:1px solid rgba(56,189,248,.18);
  font-size:.68rem;color:var(--accent);letter-spacing:.04em}
.model-pill::before{content:'';width:5px;height:5px;border-radius:50%;
  background:var(--emerald);box-shadow:0 0 5px var(--emerald);
  animation:pdot 2s ease-in-out infinite}
@keyframes pdot{0%,100%{opacity:1}50%{opacity:.4}}

.hdr-right{display:flex;align-items:center;gap:6px}
#tokenCount{font-size:.67rem;color:var(--muted);padding:4px 9px;border-radius:7px;
  background:var(--s2);border:1px solid var(--border);font-family:'JetBrains Mono',monospace;white-space:nowrap}

.hdr-btn{display:flex;align-items:center;gap:5px;padding:5px 11px;border-radius:8px;
  font-size:.72rem;font-weight:600;font-family:'Syne',sans-serif;cursor:pointer;
  border:1px solid var(--border2);background:rgba(255,255,255,.04);
  color:var(--muted2);transition:all .18s;white-space:nowrap}
.hdr-btn:hover{border-color:var(--border3);color:var(--text);background:rgba(255,255,255,.07)}
.hdr-btn.active{border-color:rgba(56,189,248,.4);color:var(--accent);background:rgba(56,189,248,.08)}
.hdr-btn.danger:hover{border-color:rgba(251,113,133,.35);color:var(--rose);background:rgba(251,113,133,.07)}

/* ── BODY (sidebar + chat) ── */
.body{flex:1;display:flex;overflow:hidden;min-height:0}

/* ── SIDEBAR: TABS ── */
#sidebar{width:220px;flex-shrink:0;display:flex;flex-direction:column;
  background:rgba(8,11,21,.9);border-right:1px solid var(--border2);
  transition:width .25s,opacity .25s;overflow:hidden}
#sidebar.collapsed{width:0;opacity:0;pointer-events:none}

.sb-head{padding:12px 12px 8px;display:flex;align-items:center;justify-content:space-between}
.sb-title{font-family:'Syne',sans-serif;font-size:.72rem;font-weight:700;
  color:var(--muted2);letter-spacing:.1em;text-transform:uppercase}
.btn-new-chat{width:26px;height:26px;border-radius:7px;border:1px solid var(--border2);
  background:rgba(56,189,248,.08);color:var(--accent);cursor:pointer;
  display:flex;align-items:center;justify-content:center;font-size:16px;
  transition:all .18s;line-height:1}
.btn-new-chat:hover{background:rgba(56,189,248,.18);border-color:rgba(56,189,248,.4)}

#tabList{flex:1;overflow-y:auto;padding:0 8px 8px}
#tabList::-webkit-scrollbar{width:3px}
#tabList::-webkit-scrollbar-thumb{background:var(--s4)}

.tab-item{display:flex;align-items:center;gap:7px;padding:8px 10px;border-radius:9px;
  cursor:pointer;margin-bottom:3px;transition:all .18s;border:1px solid transparent;
  font-size:.82rem;color:var(--muted2);position:relative;group:true}
.tab-item:hover{background:rgba(255,255,255,.04);color:var(--text)}
.tab-item.active{background:rgba(56,189,248,.08);border-color:rgba(56,189,248,.18);color:var(--text)}
.tab-icon{font-size:.75rem;flex-shrink:0;opacity:.7}
.tab-label{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.78rem}
.tab-del{width:18px;height:18px;border-radius:4px;border:none;background:none;
  color:var(--muted);cursor:pointer;display:flex;align-items:center;justify-content:center;
  font-size:11px;opacity:0;transition:all .15s;flex-shrink:0}
.tab-item:hover .tab-del{opacity:1}
.tab-del:hover{background:rgba(251,113,133,.15);color:var(--rose)}

/* ── CHAT AREA ── */
.chat-area{flex:1;display:flex;flex-direction:column;min-width:0;overflow:hidden}

#chatBox{flex:1;overflow-y:auto;padding:28px 20px 12px;
  display:flex;flex-direction:column;gap:20px;scroll-behavior:smooth}
#chatBox::-webkit-scrollbar{width:4px}
#chatBox::-webkit-scrollbar-thumb{background:var(--s4);border-radius:4px}

/* ── WELCOME ── */
.welcome{display:flex;flex-direction:column;align-items:center;justify-content:center;
  flex:1;gap:18px;padding:40px 20px;text-align:center;
  animation:fadeUp .55s cubic-bezier(.22,1,.36,1) both}
@keyframes fadeUp{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:translateY(0)}}
.w-logo{position:relative;width:72px;height:72px;margin-bottom:4px}
.w-logo svg{width:100%;height:100%}
.w-logo::after{content:'';position:absolute;inset:-10px;border-radius:50%;
  background:conic-gradient(from 0deg,var(--accent),var(--violet),var(--accent));
  filter:blur(14px);opacity:.2;animation:spin 8s linear infinite;z-index:-1}
@keyframes spin{to{transform:rotate(360deg)}}
.welcome h2{font-family:'Syne',sans-serif;font-weight:800;font-size:1.5rem;
  background:linear-gradient(110deg,#fff 20%,var(--accent) 55%,var(--violet) 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.welcome p{color:var(--muted2);font-size:.85rem;max-width:360px;line-height:1.65}
.chips{display:flex;flex-wrap:wrap;gap:7px;justify-content:center;margin-top:4px}
.chip{padding:8px 15px;border-radius:20px;font-size:.78rem;cursor:pointer;
  background:rgba(255,255,255,.04);border:1px solid var(--border2);color:var(--muted2);
  transition:all .2s;position:relative;overflow:hidden}
.chip:hover{border-color:rgba(56,189,248,.35);color:var(--text);transform:translateY(-2px);
  box-shadow:0 6px 18px rgba(56,189,248,.1)}

/* ── MESSAGES ── */
.mw{display:flex;gap:11px;animation:msgIn .28s cubic-bezier(.22,1,.36,1) both;
  max-width:800px;width:100%;margin:0 auto}
.mw.user{flex-direction:row-reverse}
@keyframes msgIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.av{width:32px;height:32px;border-radius:9px;display:flex;align-items:center;
  justify-content:center;flex-shrink:0;margin-top:2px}
.av-bot{background:linear-gradient(135deg,rgba(56,189,248,.2),rgba(167,139,250,.3));
  border:1px solid rgba(56,189,248,.22)}
.av-user{background:rgba(167,139,250,.1);border:1px solid rgba(167,139,250,.2)}
.bubble{max-width:calc(100% - 46px);padding:13px 16px;border-radius:15px;
  font-size:.885rem;line-height:1.7;position:relative}
.bubble-bot{background:linear-gradient(160deg,rgba(13,17,32,.97),rgba(8,11,21,.93));
  border:1px solid rgba(56,189,248,.1);border-top-left-radius:3px;
  box-shadow:0 4px 22px rgba(0,0,0,.3),inset 0 1px 0 rgba(255,255,255,.04)}
.bubble-user{background:linear-gradient(160deg,rgba(56,189,248,.09),rgba(167,139,250,.07));
  border:1px solid rgba(167,139,250,.18);border-top-right-radius:3px;
  box-shadow:0 4px 22px rgba(0,0,0,.2);color:#ddeeff}
.bname{font-size:.63rem;font-weight:700;font-family:'Syne',sans-serif;
  letter-spacing:.08em;text-transform:uppercase;margin-bottom:5px;
  display:flex;align-items:center;gap:6px}
.bubble-bot .bname{color:var(--accent);opacity:.7}
.bubble-user .bname{color:var(--violet);opacity:.7}
.copy-btn{margin-left:auto;padding:2px 7px;border-radius:5px;font-size:.6rem;
  font-family:'Syne',sans-serif;cursor:pointer;border:1px solid var(--border2);
  background:rgba(255,255,255,.03);color:var(--muted);transition:all .15s;
  opacity:0;white-space:nowrap}
.bubble:hover .copy-btn{opacity:1}
.copy-btn:hover{border-color:var(--border3);color:var(--text)}
.copy-btn.copied{color:var(--emerald);border-color:rgba(52,211,153,.3);opacity:1}

/* Code blocks */
.code-wrap{position:relative;margin:10px 0}
.code-wrap pre{margin:0;background:rgba(4,5,13,.88);border:1px solid var(--border2);
  border-radius:10px;padding:14px 16px;overflow-x:auto}
.code-wrap pre code{background:none;border:none;padding:0;color:#b8ccff;
  font-family:'JetBrains Mono',monospace;font-size:.8em;line-height:1.6}
.code-copy{position:absolute;top:8px;right:8px;padding:3px 9px;border-radius:6px;
  font-size:.6rem;font-family:'Syne',sans-serif;font-weight:600;cursor:pointer;
  border:1px solid rgba(56,189,248,.2);background:rgba(4,5,13,.8);color:var(--muted2);
  transition:all .18s;opacity:0;display:flex;align-items:center;gap:4px}
.code-wrap:hover .code-copy{opacity:1}
.code-copy:hover{border-color:var(--accent);color:var(--accent);background:rgba(56,189,248,.08)}
.code-copy.copied{color:var(--emerald);border-color:rgba(52,211,153,.3);opacity:1}

.typing::after{content:'▋';animation:blink-c .65s step-end infinite;color:var(--accent);font-size:.85em;margin-left:2px}
@keyframes blink-c{0%,100%{opacity:1}50%{opacity:0}}
.dots{display:flex;gap:5px;padding:4px 2px;align-items:center}
.dots span{width:6px;height:6px;border-radius:50%;
  background:linear-gradient(135deg,var(--accent),var(--violet));opacity:.4;
  animation:th 1.3s ease-in-out infinite}
.dots span:nth-child(2){animation-delay:.18s}
.dots span:nth-child(3){animation-delay:.36s}
@keyframes th{0%,80%,100%{transform:scale(1);opacity:.4}40%{transform:scale(1.5);opacity:1}}

/* Markdown styles */
.bubble p{margin-bottom:7px}.bubble p:last-child{margin-bottom:0}
.bubble code{font-family:'JetBrains Mono',monospace;font-size:.78em;
  background:rgba(56,189,248,.1);border:1px solid rgba(56,189,248,.15);
  border-radius:4px;padding:2px 5px;color:var(--accent)}
.bubble strong{color:#fff;font-weight:600}
.bubble em{color:var(--muted2);font-style:italic}
.bubble ul,.bubble ol{padding-left:17px;margin:5px 0}
.bubble li{margin-bottom:3px}.bubble li::marker{color:var(--accent)}
.bubble h3{font-family:'Syne',sans-serif;font-size:.92rem;font-weight:700;margin:10px 0 5px;
  background:linear-gradient(90deg,var(--accent),var(--violet));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.bubble blockquote{border-left:3px solid var(--accent);padding-left:12px;
  margin:7px 0;color:var(--muted2);font-style:italic}

/* ── INPUT AREA ── */
.input-area{padding:12px 20px 16px;position:relative;
  background:rgba(4,5,13,.85);backdrop-filter:blur(24px);border-top:1px solid var(--border)}
.input-area::before{content:'';position:absolute;top:-1px;left:10%;right:10%;height:1px;
  background:linear-gradient(90deg,transparent,rgba(56,189,248,.18),rgba(167,139,250,.18),transparent)}
.iw{max-width:800px;margin:0 auto;display:flex;align-items:flex-end;gap:9px;
  background:rgba(13,17,32,.94);border:1px solid var(--border2);border-radius:15px;
  padding:9px 11px 9px 16px;transition:border-color .22s,box-shadow .22s}
.iw:focus-within{border-color:rgba(56,189,248,.35);box-shadow:0 0 0 3px rgba(56,189,248,.07)}
#msgInput{flex:1;background:none;border:none;outline:none;color:var(--text);
  font-size:.89rem;font-family:'DM Sans',sans-serif;resize:none;
  min-height:24px;max-height:160px;line-height:1.55;overflow-y:auto;padding-top:2px}
#msgInput::placeholder{color:var(--muted)}
.ia{display:flex;align-items:center;flex-shrink:0}
.btn-send{width:36px;height:36px;border-radius:10px;border:none;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  background:linear-gradient(135deg,var(--accent),#818cf8);color:#000f1f;
  font-weight:800;box-shadow:0 3px 14px rgba(56,189,248,.3);transition:all .2s}
.btn-send:hover{transform:scale(1.08);box-shadow:0 5px 22px rgba(56,189,248,.5)}
.btn-send:active{transform:scale(.96)}
.btn-send:disabled{opacity:.3;cursor:not-allowed;transform:none;box-shadow:none}
.btn-send.pulsing{animation:spulse 1s ease-in-out infinite}
@keyframes spulse{0%,100%{box-shadow:0 3px 14px rgba(56,189,248,.3)}
  50%{box-shadow:0 3px 22px rgba(56,189,248,.65),0 0 0 5px rgba(56,189,248,.1)}}
.hint{max-width:800px;margin:6px auto 0;font-size:.65rem;color:var(--muted);
  text-align:center;opacity:.5;display:flex;align-items:center;justify-content:center;gap:10px}
.kbg{background:var(--s2);border:1px solid var(--border2);border-radius:4px;
  padding:1px 5px;font-family:'JetBrains Mono',monospace;font-size:.63rem;color:var(--muted2)}

/* ── SETTINGS PANEL ── */
#settingsPanel{position:fixed;inset:0;z-index:500;display:flex;align-items:center;justify-content:center;
  background:rgba(4,5,13,.75);backdrop-filter:blur(12px);
  opacity:0;pointer-events:none;transition:opacity .25s}
#settingsPanel.open{opacity:1;pointer-events:all}
.settings-box{width:540px;max-width:94vw;background:var(--s2);
  border:1px solid var(--border2);border-radius:18px;
  box-shadow:0 24px 80px rgba(0,0,0,.6);
  animation:none;transform:none;overflow:hidden}
#settingsPanel.open .settings-box{animation:modalIn .28s cubic-bezier(.22,1,.36,1) both}
@keyframes modalIn{from{opacity:0;transform:translateY(16px) scale(.97)}to{opacity:1;transform:none}}
.sb-hdr{display:flex;align-items:center;justify-content:space-between;padding:18px 22px 16px;
  border-bottom:1px solid var(--border)}
.sb-hdr h2{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;
  background:linear-gradient(90deg,var(--accent),var(--violet));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.btn-close{width:28px;height:28px;border-radius:7px;border:1px solid var(--border2);
  background:rgba(255,255,255,.04);color:var(--muted2);cursor:pointer;
  display:flex;align-items:center;justify-content:center;font-size:14px;transition:all .18s}
.btn-close:hover{border-color:var(--rose);color:var(--rose);background:rgba(251,113,133,.08)}
.sb-body{padding:20px 22px;display:flex;flex-direction:column;gap:18px}
.field{display:flex;flex-direction:column;gap:7px}
.field label{font-size:.72rem;font-weight:700;font-family:'Syne',sans-serif;
  color:var(--muted2);letter-spacing:.07em;text-transform:uppercase}
.field-desc{font-size:.75rem;color:var(--muted);line-height:1.5;margin-top:-3px}
.field textarea,.field input[type=text],.field select{
  background:rgba(13,17,32,.9);border:1px solid var(--border2);border-radius:10px;
  color:var(--text);font-size:.85rem;font-family:'DM Sans',sans-serif;
  padding:10px 13px;outline:none;transition:border-color .2s,box-shadow .2s;resize:vertical}
.field textarea:focus,.field input:focus,.field select:focus{
  border-color:rgba(56,189,248,.4);box-shadow:0 0 0 3px rgba(56,189,248,.08)}
.field textarea{min-height:110px;line-height:1.55}
.field select{cursor:pointer;background-image:none}
.field select option{background:var(--s3)}
.btn-row{display:flex;gap:8px;justify-content:flex-end;padding:16px 22px;
  border-top:1px solid var(--border)}
.btn-primary{padding:9px 20px;border-radius:10px;border:none;cursor:pointer;
  background:linear-gradient(135deg,var(--accent),#818cf8);color:#000f1f;
  font-size:.82rem;font-weight:700;font-family:'Syne',sans-serif;
  box-shadow:0 3px 14px rgba(56,189,248,.25);transition:all .2s}
.btn-primary:hover{transform:translateY(-1px);box-shadow:0 5px 20px rgba(56,189,248,.4)}
.btn-ghost{padding:9px 18px;border-radius:10px;cursor:pointer;
  border:1px solid var(--border2);background:rgba(255,255,255,.04);
  color:var(--muted2);font-size:.82rem;font-weight:600;font-family:'Syne',sans-serif;
  transition:all .2s}
.btn-ghost:hover{border-color:var(--border3);color:var(--text)}
.sys-badge{display:inline-flex;align-items:center;gap:5px;padding:2px 8px;
  border-radius:5px;background:rgba(251,191,36,.08);border:1px solid rgba(251,191,36,.2);
  color:var(--amber);font-size:.65rem;font-weight:700;font-family:'Syne',sans-serif;
  letter-spacing:.05em}

/* ── THEME PICKER ── */
.theme-picker{display:flex;gap:10px;flex-wrap:wrap}
.theme-opt{display:flex;flex-direction:column;align-items:center;gap:6px;cursor:pointer;
  padding:8px 12px;border-radius:10px;border:1px solid var(--border2);
  background:rgba(255,255,255,.03);transition:all .2s;min-width:68px}
.theme-opt:hover{border-color:var(--accent);background:rgba(56,189,248,.06)}
.theme-opt.active{border-color:var(--accent);background:rgba(56,189,248,.1);
  box-shadow:0 0 0 2px rgba(56,189,248,.2)}
.theme-swatch{width:40px;height:28px;border-radius:6px;border:1px solid rgba(255,255,255,.1)}
.theme-opt span{font-size:.68rem;color:var(--muted2);font-weight:600;font-family:'Syne',sans-serif}
.theme-opt.active span{color:var(--accent)}

/* ── TOAST ── */
#toast{position:fixed;bottom:78px;left:50%;transform:translateX(-50%) translateY(8px);
  display:flex;align-items:center;gap:7px;padding:9px 16px;border-radius:20px;
  font-size:.78rem;font-weight:500;color:#fff;z-index:9999;
  opacity:0;transition:opacity .28s,transform .28s;pointer-events:none;white-space:nowrap;
  box-shadow:0 8px 28px rgba(0,0,0,.4)}
#toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
#toast.ok{background:linear-gradient(135deg,#065f46,#059669);border:1px solid rgba(52,211,153,.2)}
#toast.err{background:linear-gradient(135deg,#7f1d1d,#dc2626);border:1px solid rgba(251,113,133,.2)}
#toast.info{background:linear-gradient(135deg,#1e3a5f,#0284c7);border:1px solid rgba(56,189,248,.2)}
</style>
</head>
<body>

<div id="cosmos">
  <div id="stars"></div><div id="grid"></div>
  <div class="nebula n1"></div><div class="nebula n2"></div><div class="nebula n3"></div>
</div>

<div class="app">

  <!-- ══ HEADER ══ -->
  <header>
    <div class="logo">
      <svg class="logo-gem" viewBox="0 0 30 30" fill="none">
        <defs>
          <linearGradient id="lg1" x1="0" y1="0" x2="30" y2="30" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#38bdf8"/><stop offset="100%" stop-color="#a78bfa"/>
          </linearGradient>
          <linearGradient id="lg2" x1="0" y1="0" x2="30" y2="30" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#a78bfa" stop-opacity=".4"/>
            <stop offset="100%" stop-color="#38bdf8" stop-opacity=".2"/>
          </linearGradient>
        </defs>
        <polygon points="15,2 28,9 28,21 15,28 2,21 2,9" fill="url(#lg2)" stroke="url(#lg1)" stroke-width="1.1"/>
        <circle cx="15" cy="15" r="3" fill="url(#lg1)" opacity=".9"/>
      </svg>
      <div class="logo-wordmark">
        <span class="logo-name">OmniumAI</span>
        <span class="logo-sub">Omnium Research</span>
      </div>
    </div>

    <div class="model-pill">OmniNet 1.0</div>

    <div class="hdr-right">
      <div id="tokenCount">0 токенов</div>
      <button class="hdr-btn" id="sidebarToggle" onclick="toggleSidebar()" title="Чаты">
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">
          <rect x="1" y="1" width="14" height="14" rx="2"/>
          <line x1="5.5" y1="1" x2="5.5" y2="15"/>
        </svg>
        Чаты
      </button>
      <button class="hdr-btn" onclick="openSettings()" title="Настройки">
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="8" cy="8" r="2.5"/>
          <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41"/>
        </svg>
        Настройки
      </button>
      <button class="hdr-btn" onclick="exportChat()" title="Экспорт">
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M8 1v9M5 7l3 3 3-3M2 11v2a1 1 0 001 1h10a1 1 0 001-1v-2"/>
        </svg>
        Экспорт
      </button>
      <button class="hdr-btn danger" onclick="clearChat()">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M2 4h12M5 4V2.5h6V4M3.5 4l.9 9.5h7.2L12.5 4"/>
        </svg>
        Очистить
      </button>
    </div>
  </header>

  <!-- ══ BODY ══ -->
  <div class="body">

    <!-- Sidebar с вкладками чатов -->
    <div id="sidebar" class="collapsed">
      <div class="sb-head">
        <span class="sb-title">Чаты</span>
        <button class="btn-new-chat" onclick="newChat()" title="Новый чат">+</button>
      </div>
      <div id="tabList"></div>
    </div>

    <!-- Chat -->
    <div class="chat-area">
      <div id="chatBox">
        <div class="welcome" id="ws">
          <div class="w-logo">
            <svg viewBox="0 0 72 72" fill="none">
              <defs>
                <linearGradient id="wg1" x1="0" y1="0" x2="72" y2="72" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stop-color="#38bdf8"/><stop offset="100%" stop-color="#a78bfa"/>
                </linearGradient>
              </defs>
              <polygon points="36,4 68,20 68,52 36,68 4,52 4,20" fill="rgba(56,189,248,.06)" stroke="url(#wg1)" stroke-width="1.3"/>
              <circle cx="36" cy="36" r="9" fill="url(#wg1)" opacity=".85"/>
              <circle cx="36" cy="36" r="5" fill="rgba(255,255,255,.18)"/>
            </svg>
          </div>
          <h2>Добро пожаловать в OmniumAI</h2>
          <p>Передовая модель OmniNet 1.0. Задайте любой вопрос или создайте новый чат.</p>
          <div class="chips">
            <div class="chip" onclick="chip(this)">✦ Квантовые вычисления</div>
            <div class="chip" onclick="chip(this)">✦ Стихотворение про космос</div>
            <div class="chip" onclick="chip(this)">✦ Помоги с кодом Python</div>
            <div class="chip" onclick="chip(this)">✦ Как работает нейросеть?</div>
            <div class="chip" onclick="chip(this)">✦ Философия сознания</div>
            <div class="chip" onclick="chip(this)">✦ Теория относительности</div>
          </div>
        </div>
      </div>

      <div class="input-area">
        <div class="iw">
          <textarea id="msgInput" rows="1"
            placeholder="Спросите OmniumAI что угодно…"
            oninput="ar(this)" onkeydown="hk(event)"></textarea>
          <div class="ia">
            <button class="btn-send" id="sendBtn" onclick="send()">
              <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor">
                <path d="M1.5 1.5L14.5 8L1.5 14.5V9.5L10.5 8L1.5 6.5V1.5Z"/>
              </svg>
            </button>
          </div>
        </div>
        <div class="hint">
          <span><span class="kbg">Enter</span> отправить</span>
          <span><span class="kbg">Shift+Enter</span> перенос</span>
          <span>OmniNet 1.0 &middot; Omnium Research</span>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ══ SETTINGS PANEL ══ -->
<div id="settingsPanel" onclick="onOverlayClick(event)">
  <div class="settings-box">
    <div class="sb-hdr">
      <h2>⚙ Настройки OmniumAI</h2>
      <button class="btn-close" onclick="closeSettings()">✕</button>
    </div>
    <div class="sb-body">
      <div class="field">
        <label>Системный промпт <span class="sys-badge">ACTIVE</span></label>
        <p class="field-desc">Задаёт роль, стиль и ограничения модели. Применяется ко всем чатам.</p>
        <textarea id="sysPromptInput" placeholder="Ты — полезный ассистент…" rows="5"></textarea>
      </div>
      <div class="field">
        <label>Имя ассистента</label>
        <input type="text" id="assistantNameInput" placeholder="OmniumAI"/>
      </div>
      <div class="field">
        <label>Тема интерфейса</label>
        <div class="theme-picker" id="themePicker">
          <div class="theme-opt" data-theme="dark"   onclick="pickTheme('dark')">
            <div class="theme-swatch" style="background:linear-gradient(135deg,#04050d,#0d1120)"></div>
            <span>Космос</span>
          </div>
          <div class="theme-opt" data-theme="light"  onclick="pickTheme('light')">
            <div class="theme-swatch" style="background:linear-gradient(135deg,#f0f4ff,#dde4f5)"></div>
            <span>Светлая</span>
          </div>
          <div class="theme-opt" data-theme="green"  onclick="pickTheme('green')">
            <div class="theme-swatch" style="background:linear-gradient(135deg,#020d06,#0d2214)"></div>
            <span>Матрица</span>
          </div>
          <div class="theme-opt" data-theme="amber"  onclick="pickTheme('amber')">
            <div class="theme-swatch" style="background:linear-gradient(135deg,#0d0800,#261800)"></div>
            <span>Янтарь</span>
          </div>
        </div>
      </div>
    </div>
    <div class="btn-row">
      <button class="btn-ghost" onclick="resetSettings()">Сбросить</button>
      <button class="btn-primary" onclick="saveSettings()">Сохранить</button>
    </div>
  </div>
</div>

<div id="toast"></div>

<script>
// ═══════════════════════════════════════════════════════
//  КОНСТАНТЫ
// ═══════════════════════════════════════════════════════
const DEFAULT_SYS  = `""" + DEFAULT_USER_SYSTEM.replace('`','\\`') + r"""`;
const DEFAULT_NAME = 'OmniumAI';

// ═══════════════════════════════════════════════════════
//  СОСТОЯНИЕ — всё хранится в localStorage
// ═══════════════════════════════════════════════════════
let busy        = false;
let totalTokens = 0;

// Настройки
const THEMES = ['dark','light','green','amber'];

function loadSettings() {
  return {
    sysPrompt:     localStorage.getItem('omni_sys')   || DEFAULT_SYS,
    assistantName: localStorage.getItem('omni_name')  || DEFAULT_NAME,
    theme:         localStorage.getItem('omni_theme') || 'dark',
  };
}
function saveSettingsData(s) {
  localStorage.setItem('omni_sys',   s.sysPrompt);
  localStorage.setItem('omni_name',  s.assistantName);
  localStorage.setItem('omni_theme', s.theme);
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme === 'dark' ? '' : theme);
  // Mark active in picker if open
  document.querySelectorAll('.theme-opt').forEach(el => {
    el.classList.toggle('active', el.dataset.theme === theme);
  });
}

function pickTheme(theme) {
  applyTheme(theme);
  // store pending choice, saved on Save click
  document.getElementById('themePicker').dataset.pending = theme;
}

// Чаты: { id, title, messages: [{role,content}] }
function loadChats() {
  try { return JSON.parse(localStorage.getItem('omni_chats') || 'null') || [newChatObj()]; }
  catch { return [newChatObj()]; }
}
function saveChats() {
  localStorage.setItem('omni_chats', JSON.stringify(chats));
}
function newChatObj() {
  return { id: Date.now().toString(), title: 'Новый чат', messages: [] };
}

let chats      = loadChats();
let activeChatId = localStorage.getItem('omni_active') || chats[0].id;
// Убедимся что активный чат существует
if (!chats.find(c => c.id === activeChatId)) activeChatId = chats[0].id;

function getActive() { return chats.find(c => c.id === activeChatId) || chats[0]; }
function setActive(id) {
  activeChatId = id;
  localStorage.setItem('omni_active', id);
}

// ═══════════════════════════════════════════════════════
//  ЗВЁЗДЫ
// ═══════════════════════════════════════════════════════
(function() {
  const c = document.getElementById('stars');
  for (let i = 0; i < 130; i++) {
    const s = document.createElement('div');
    s.className = 'star';
    const sz = Math.random() * 2 + .4;
    s.style.cssText = 'left:'+(Math.random()*100)+'%;top:'+(Math.random()*100)+'%;'+
      'width:'+sz+'px;height:'+sz+'px;--o:'+(Math.random()*.5+.1)+';'+
      '--d:'+(Math.random()*4+2)+'s;animation-delay:'+(Math.random()*6)+'s';
    c.appendChild(s);
  }
})();

// ═══════════════════════════════════════════════════════
//  УТИЛИТЫ
// ═══════════════════════════════════════════════════════
function toast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = 'show '+(type||'info');
  clearTimeout(t._t); t._t = setTimeout(()=>t.className='', 3000);
}
function ar(el) {
  el.style.height='auto'; el.style.height=Math.min(el.scrollHeight,160)+'px';
}
function hk(e) { if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();} }
function chip(el) {
  const inp=document.getElementById('msgInput');
  inp.value=el.textContent.replace(/^✦\s*/,''); ar(inp); inp.focus();
}
function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function updateTokens(text) {
  totalTokens += Math.round(text.trim().split(/\s+/).filter(Boolean).length * 1.3);
  document.getElementById('tokenCount').textContent = totalTokens + ' токенов';
}

// ═══════════════════════════════════════════════════════
//  MARKDOWN
// ═══════════════════════════════════════════════════════
const cpIco = '<svg width="10" height="10" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">'+
  '<rect x="5" y="5" width="9" height="9" rx="1.5"/>'+
  '<path d="M11 5V3.5A1.5 1.5 0 009.5 2h-6A1.5 1.5 0 002 3.5v6A1.5 1.5 0 003.5 11H5"/></svg>';

function md(text) {
  let t = esc(text);
  t = t.replace(/```([\w]*)\n?([\s\S]*?)```/g, (_,lang,c) => {
    const lbl = lang || 'code';
    return '<div class="code-wrap"><button class="code-copy" onclick="copyCode(this)">'+
      cpIco+lbl+'</button><pre><code>'+c.trim()+'</code></pre></div>';
  });
  t = t.replace(/`([^`\n]+)`/g,       '<code>$1</code>');
  t = t.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
  t = t.replace(/\*([^*\n]+)\*/g,     '<em>$1</em>');
  t = t.replace(/^#{1,3} (.+)$/gm,    '<h3>$1</h3>');
  t = t.replace(/^> (.+)$/gm,         '<blockquote>$1</blockquote>');
  t = t.replace(/^[-*] (.+)$/gm,      '<li>$1</li>');
  return t.split(/\n\n+/).map(p=>{
    p=p.trim(); if(!p) return '';
    if(/^<(div|pre|h3|li|blockquote)/.test(p)) return p;
    return '<p>'+p.replace(/\n/g,'<br>')+'</p>';
  }).join('');
}
function copyCode(btn) {
  const code = btn.closest('.code-wrap').querySelector('code').innerText;
  navigator.clipboard.writeText(code).then(()=>{
    const orig=btn.innerHTML; btn.innerHTML=cpIco+'✓ ok'; btn.classList.add('copied');
    setTimeout(()=>{btn.innerHTML=orig;btn.classList.remove('copied');},2000);
  });
}

// ═══════════════════════════════════════════════════════
//  АВАТАРЫ
// ═══════════════════════════════════════════════════════
const botAv  = '<svg width="15" height="15" viewBox="0 0 30 30" fill="none">'+
  '<polygon points="15,2 28,9 28,21 15,28 2,21 2,9" fill="rgba(56,189,248,.15)" stroke="rgba(56,189,248,.5)" stroke-width="1.1"/>'+
  '<circle cx="15" cy="15" r="3.5" fill="#38bdf8" opacity=".9"/></svg>';
const userAv = '<svg width="13" height="13" viewBox="0 0 20 20" fill="none">'+
  '<circle cx="10" cy="7" r="4" fill="rgba(167,139,250,.75)"/>'+
  '<path d="M2 18c0-4 3.6-7 8-7s8 3 8 7" stroke="rgba(167,139,250,.6)" stroke-width="1.5" fill="none"/></svg>';

// ═══════════════════════════════════════════════════════
//  РЕНДЕР СООБЩЕНИЙ
// ═══════════════════════════════════════════════════════
function rmWelcome() { const w=document.getElementById('ws'); if(w) w.remove(); }

function addMsg(role, html, streaming) {
  rmWelcome();
  const box  = document.getElementById('chatBox');
  const wrap = document.createElement('div');
  wrap.className = 'mw '+role;
  const isBot = role==='bot';
  const name  = isBot ? (loadSettings().assistantName||DEFAULT_NAME) : 'Вы';
  wrap.innerHTML =
    '<div class="av '+(isBot?'av-bot':'av-user')+'">'+(isBot?botAv:userAv)+'</div>'+
    '<div class="bubble '+(isBot?'bubble-bot':'bubble-user')+'">'+
      '<div class="bname">'+esc(name)+
        '<button class="copy-btn" onclick="copyBub(this)">копировать</button>'+
      '</div>'+
      '<div class="bc'+(streaming?' typing':'')+'">'+html+'</div>'+
    '</div>';
  box.appendChild(wrap);
  box.scrollTop = box.scrollHeight;
  return wrap.querySelector('.bc');
}

function addThinking() {
  rmWelcome();
  const box  = document.getElementById('chatBox');
  const wrap = document.createElement('div');
  wrap.id='thinking'; wrap.className='mw bot';
  wrap.innerHTML = '<div class="av av-bot">'+botAv+'</div>'+
    '<div class="bubble bubble-bot"><div class="bname">'+
    esc(loadSettings().assistantName||DEFAULT_NAME)+'</div>'+
    '<div class="dots"><span></span><span></span><span></span></div></div>';
  box.appendChild(wrap); box.scrollTop = box.scrollHeight;
}
function rmThinking() { const e=document.getElementById('thinking'); if(e) e.remove(); }

function copyBub(btn) {
  const text = btn.closest('.bubble').querySelector('.bc').innerText;
  navigator.clipboard.writeText(text).then(()=>{
    btn.textContent='✓ скопировано'; btn.classList.add('copied');
    setTimeout(()=>{btn.textContent='копировать';btn.classList.remove('copied');},2000);
  }).catch(()=>toast('Не удалось скопировать','err'));
}

// ═══════════════════════════════════════════════════════
//  SIDEBAR / TABS
// ═══════════════════════════════════════════════════════
let sidebarOpen = false;

function toggleSidebar() {
  sidebarOpen = !sidebarOpen;
  document.getElementById('sidebar').classList.toggle('collapsed', !sidebarOpen);
  document.getElementById('sidebarToggle').classList.toggle('active', sidebarOpen);
  renderTabs();
}

function renderTabs() {
  const list = document.getElementById('tabList');
  list.innerHTML = '';
  chats.forEach(chat => {
    const div = document.createElement('div');
    div.className = 'tab-item' + (chat.id===activeChatId?' active':'');
    div.innerHTML =
      '<span class="tab-icon">💬</span>'+
      '<span class="tab-label">'+esc(chat.title)+'</span>'+
      (chats.length>1 ? '<button class="tab-del" onclick="deleteChat(\''+chat.id+'\',event)" title="Удалить">✕</button>' : '');
    div.onclick = (e) => { if(!e.target.classList.contains('tab-del')) switchChat(chat.id); };
    list.appendChild(div);
  });
}

function newChat() {
  const chat = newChatObj();
  chats.unshift(chat);
  saveChats();
  switchChat(chat.id);
  renderTabs();
  toast('Новый чат создан','ok');
}

function switchChat(id) {
  setActive(id);
  renderTabs();
  rebuildChatBox();
  totalTokens = 0;
  document.getElementById('tokenCount').textContent = '0 токенов';
}

function deleteChat(id, e) {
  e.stopPropagation();
  chats = chats.filter(c => c.id !== id);
  if (chats.length === 0) chats = [newChatObj()];
  if (activeChatId === id) setActive(chats[0].id);
  saveChats();
  renderTabs();
  rebuildChatBox();
  toast('Чат удалён','info');
}

// Перерисовать chatBox из сохранённой истории
function rebuildChatBox() {
  const box    = document.getElementById('chatBox');
  const msgs   = getActive().messages;
  const sett   = loadSettings();
  if (msgs.length === 0) {
    box.innerHTML = welcomeHTML();
    return;
  }
  box.innerHTML = '';
  msgs.forEach(m => {
    if (m.role === 'user') {
      addMsg('user', esc(m.content), false);
    } else if (m.role === 'assistant') {
      addMsg('bot', md(m.content), false);
    }
  });
}

function welcomeHTML() {
  return '<div class="welcome" id="ws">'+
    '<div class="w-logo"><svg viewBox="0 0 72 72" fill="none">'+
    '<defs><linearGradient id="wg2" x1="0" y1="0" x2="72" y2="72" gradientUnits="userSpaceOnUse">'+
    '<stop offset="0%" stop-color="#38bdf8"/><stop offset="100%" stop-color="#a78bfa"/></linearGradient></defs>'+
    '<polygon points="36,4 68,20 68,52 36,68 4,52 4,20" fill="rgba(56,189,248,.06)" stroke="url(#wg2)" stroke-width="1.3"/>'+
    '<circle cx="36" cy="36" r="9" fill="url(#wg2)" opacity=".85"/>'+
    '<circle cx="36" cy="36" r="5" fill="rgba(255,255,255,.18)"/></svg></div>'+
    '<h2>OmniumAI</h2><p>Начните диалог или выберите другой чат.</p>'+
    '<div class="chips">'+
    '<div class="chip" onclick="chip(this)">✦ Квантовые вычисления</div>'+
    '<div class="chip" onclick="chip(this)">✦ Стихотворение про космос</div>'+
    '<div class="chip" onclick="chip(this)">✦ Помоги с кодом Python</div>'+
    '<div class="chip" onclick="chip(this)">✦ Философия сознания</div>'+
    '</div></div>';
}

// Обновляет заголовок чата по первому сообщению
function autoTitle(chatId, text) {
  const chat = chats.find(c => c.id === chatId);
  if (!chat || chat.messages.length > 2) return;
  chat.title = text.slice(0, 36) + (text.length > 36 ? '…' : '');
  saveChats();
  renderTabs();
}

// ═══════════════════════════════════════════════════════
//  SETTINGS
// ═══════════════════════════════════════════════════════
function openSettings() {
  const s = loadSettings();
  document.getElementById('sysPromptInput').value     = s.sysPrompt;
  document.getElementById('assistantNameInput').value  = s.assistantName;
  const picker = document.getElementById('themePicker');
  picker.dataset.pending = s.theme;
  applyTheme(s.theme);
  document.getElementById('settingsPanel').classList.add('open');
}
function closeSettings() {
  document.getElementById('settingsPanel').classList.remove('open');
}
function onOverlayClick(e) {
  if(e.target===document.getElementById('settingsPanel')) closeSettings();
}
function saveSettings() {
  const picker = document.getElementById('themePicker');
  const theme  = picker.dataset.pending || loadSettings().theme;
  const s = {
    sysPrompt:     document.getElementById('sysPromptInput').value.trim() || DEFAULT_SYS,
    assistantName: document.getElementById('assistantNameInput').value.trim() || DEFAULT_NAME,
    theme,
  };
  saveSettingsData(s);
  applyTheme(theme);
  closeSettings();
  toast('Настройки сохранены ✓','ok');
}
function resetSettings() {
  document.getElementById('sysPromptInput').value     = DEFAULT_SYS;
  document.getElementById('assistantNameInput').value  = DEFAULT_NAME;
  pickTheme('dark');
}

// ═══════════════════════════════════════════════════════
//  ОТПРАВКА СООБЩЕНИЯ
// ═══════════════════════════════════════════════════════
async function send() {
  if(busy) return;
  const inp  = document.getElementById('msgInput');
  const text = inp.value.trim(); if(!text) return;
  inp.value=''; inp.style.height='auto';

  const chat = getActive();
  addMsg('user', esc(text), false);
  updateTokens(text);
  chat.messages.push({role:'user', content:text});
  autoTitle(chat.id, text);
  if(chat.messages.length > 40) chat.messages = chat.messages.slice(-40);
  saveChats();

  busy=true;
  const btn=document.getElementById('sendBtn');
  btn.disabled=true; btn.classList.add('pulsing');
  addThinking();

  const sett = loadSettings();

  try {
    const res = await fetch('/api/chat', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        messages:   chat.messages,
        sys_prompt: sett.sysPrompt,
      })
    });
    rmThinking();

    if(!res.ok){
      let msg='Ошибка сервера';
      try{const e=await res.json();msg=e.error||msg;}catch(_){}
      addMsg('bot','<strong>⚠️ '+esc(msg)+'</strong>',false);
      toast(msg,'err'); return;
    }

    const reader=res.body.getReader(), dec=new TextDecoder();
    let raw='', contentEl=null, sseBuf='';

    while(true){
      const{done,value}=await reader.read(); if(done) break;
      sseBuf+=dec.decode(value,{stream:true});
      const lines=sseBuf.split('\n'); sseBuf=lines.pop();
      for(const line of lines){
        const l=line.trim(); if(!l.startsWith('data:')) continue;
        const payload=l.slice(5).trim();
        if(payload==='[DONE]'){sseBuf='';break;}
        try{
          const obj=JSON.parse(payload);
          if(obj.error){toast(obj.error,'err');break;}
          const delta=obj.delta||''; if(!delta) continue;
          raw+=delta;
          if(!contentEl){contentEl=addMsg('bot',md(raw),true);}
          else{contentEl.innerHTML=md(raw);}
          document.getElementById('chatBox').scrollTop=99999;
        }catch(_){}
      }
    }

    if(contentEl){contentEl.classList.remove('typing');contentEl.innerHTML=md(raw);}
    else if(raw){addMsg('bot',md(raw),false);}

    if(raw){
      chat.messages.push({role:'assistant',content:raw});
      saveChats();
      updateTokens(raw);
    }

  }catch(err){
    rmThinking();
    addMsg('bot','<strong>⚠️ Ошибка соединения.</strong>',false);
    toast('Ошибка соединения','err');
    console.error(err);
  }finally{
    busy=false; btn.disabled=false; btn.classList.remove('pulsing');
  }
}

// ═══════════════════════════════════════════════════════
//  ОЧИСТИТЬ / ЭКСПОРТ
// ═══════════════════════════════════════════════════════
function clearChat() {
  const chat = getActive();
  chat.messages = [];
  chat.title = 'Новый чат';
  saveChats();
  totalTokens=0;
  document.getElementById('tokenCount').textContent='0 токенов';
  document.getElementById('chatBox').innerHTML = welcomeHTML();
  renderTabs();
  toast('Чат очищен','ok');
}

function exportChat() {
  const chat = getActive();
  if(!chat.messages.length){ toast('Нет сообщений для экспорта','err'); return; }
  const sett = loadSettings();
  const name = sett.assistantName || DEFAULT_NAME;

  // Экспорт в красивый Markdown
  let out = `# ${chat.title}\n`;
  out += `> Экспортировано из OmniumAI · OmniNet 1.0 · ${new Date().toLocaleString('ru')}\n\n---\n\n`;
  chat.messages.forEach(m=>{
    const role = m.role==='user' ? '👤 **Вы**' : `✦ **${name}**`;
    out += `### ${role}\n\n${m.content}\n\n---\n\n`;
  });

  const blob = new Blob([out], {type:'text/markdown;charset=utf-8'});
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url;
  a.download = `omniumai-${chat.title.replace(/[^а-яa-z0-9]/gi,'_').slice(0,30)}-${Date.now()}.md`;
  a.click();
  URL.revokeObjectURL(url);
  toast('Чат экспортирован ✓','ok');
}

// ═══════════════════════════════════════════════════════
//  ИНИЦИАЛИЗАЦИЯ
// ═══════════════════════════════════════════════════════
(function init() {
  // Apply saved theme immediately on load
  applyTheme(loadSettings().theme);
  rebuildChatBox();
  renderTabs();
})();
</script>
</body>
</html>"""

# ── Flask ────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.json.ensure_ascii = False

@app.route("/health")
def health():
    return "ok", 200

@app.route("/")
def index():
    return HTML, 200, {"Content-Type": "text/html; charset=utf-8"}

@app.route("/api/chat", methods=["POST"])
def chat():
    data       = request.get_json(force=True)
    messages   = data.get("messages", [])
    user_sys   = data.get("sys_prompt", DEFAULT_USER_SYSTEM).strip()
    if not messages:
        return jsonify({"error": "Нет сообщений"}), 400

    # HIDDEN_SYSTEM всегда идёт первым и никогда не передаётся клиенту.
    # user_sys — пользовательская инструкция, видимая в настройках.
    combined = HIDDEN_SYSTEM
    if user_sys:
        combined += "\n\n" + user_sys
    full = [{"role": "system", "content": combined}] + messages

    def generate():
        try:
            client = Groq(api_key=GROQ_API_KEY)
            stream = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=full,
                max_tokens=1024,
                temperature=0.75,
                stream=True
            )
            for chunk in stream:
                delta = ""
                if chunk.choices and chunk.choices[0].delta:
                    delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield "data: " + json.dumps({"delta": delta}, ensure_ascii=False) + "\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield "data: " + json.dumps({"error": str(e)[:200]}, ensure_ascii=False) + "\n\n"
            yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

@app.route("/api/clear", methods=["POST"])
def clear():
    return jsonify({"ok": True})

# ── Запуск ───────────────────────────────────────────────────────────────────
def _open():
    time.sleep(1.3)
    webbrowser.open(f"http://{HOST}:{PORT}")

if __name__ == "__main__":
    print(f"\n{'═'*52}")
    print(f"  ✦  OmniumAI — OmniNet 1.0")
    print(f"{'═'*52}")
    print(f"  🌐  http://{HOST}:{PORT}")
    print(f"  🤖  {GROQ_MODEL} → {DISPLAY_MODEL}")
    print(f"  ⛔  Ctrl+C для остановки")
    print(f"{'═'*52}\n")
    threading.Thread(target=_open, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port, debug=False)
