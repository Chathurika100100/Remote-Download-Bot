import os
import subprocess
import requests
import threading
import time
from flask import Flask
from pyrogram import Client, filters

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Online!"

def run_flask(): flask_app.run(host='0.0.0.0', port=8000)

# Progress Bar එක % සහ MB සමඟ පෙන්වීමට
async def progress(current, total, message, type_msg):
    percent = current * 100 / total
    # සෑම 15% කට වරක් මැසේජ් එක Edit කරයි
    if int(percent) % 15 == 0:
        try:
            await message.edit(f"🚀 {type_msg}: {percent:.1f}%\n📦 {current/(1024*1024):.1f}MB / {total/(1024*1024):.1f}MB")
        except:
            pass

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(f"ආයුබෝවන් {message.from_user.first_name}! 🙏\n\nමම දැන් පොඩි ෆයිල් වගේම ලොකු ෆයිල් බාන්නත් සූදානම්.\n\nභාවිතය: `/download [link]`")

@app.on_message(filters.command("ping") & filters.private)
async def ping(client, message):
    start_t = time.time()
    msg = await message.reply_text("Ping...")
    speed = round((time.time() - start_t) * 1000)
    await msg.edit(f"🏓 Pong! `{speed}ms` ⚡")

@app.on_message(filters.command("download") & filters.private)
async def download_handler(client, message):
    if len(message.command) < 2: return
    
    url = message.text.split(" ")[1]
    original_fn = url.split("/")[-1].split("?")[0] or "file"
    status_msg = await message.reply("සම්බන්ධ වෙමින්... ⏳")

    # 1. බාගත කිරීම
    r = requests.get(url, stream=True)
    total_size = int(r.headers.get('content-length', 0))
    
    with open(original_fn, 'wb') as f:
        dl = 0
        for chunk in r.
