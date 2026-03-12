import os
import subprocess
import requests
import threading
import time
from flask import Flask
from pyrogram import Client, filters

# 1. Koyeb Health Check
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Alive and Fast!"

def run_flask(): flask_app.run(host='0.0.0.0', port=8000)

async def progress(current, total, message, type_msg):
    percent = current * 100 / total
    if int(percent) % 20 == 0:
        try: await message.edit(f"🚀 {type_msg}: {percent:.1f}%")
        except: pass

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- START COMMAND ---
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(f"ආයුබෝවන් {message.from_user.first_name}! 🙏\n\nමම ඔයාගේ Remote Downloader බොට්. \n\nභාවිතය: `/download [link]` \nසර්වර් එක චෙක් කිරීමට: `/ping` භාවිතා කරන්න.")

# --- PING COMMAND ---
@app.on_message(filters.command("ping") & filters.private)
async def ping(client, message):
    start_time = time.time()
    msg = await message.reply_text("පරීක්ෂා කරමින්... ⏳")
    end_time = time.time()
    # වේගය මිලි තත්පර වලින් (ms)
    speed = round((end_time - start_time) * 1000)
    await msg.edit(f"🏓 **Pong!**\n\nSpeed: `{speed}ms` ⚡")

# --- DOWNLOAD COMMAND ---
@app.on_message(filters.command("download") & filters.private)
async def download_handler(client, message):
    if len(message.command) < 2: return
    
    url = message.text.split(" ")[1]
    original_fn = url.split("/")[-1].split("?")[0] or "file"
    status_msg = await message.reply("බාගත කරමින් පවතී... ⏳")

    # 1. බාගත කිරීම
    r = requests.get(url, stream=True)
    with open(original_fn, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024*1024):
            if chunk: f.write(chunk)

    file_size = os.path.getsize(original_fn)
    limit = 1900 * 1024 * 1024 # 1.9GB

    # 2. Upload Logic (ෆයිල් 2ක් එන එක මෙතනින් නතර වෙනවා)
    if file_size < limit:
        # ෆයිල් එක කුඩා නම් කෙලින්ම යවනවා
        await status_msg.edit("අප්ලෝඩ් කරමින් පවතී... 📤")
        await client.send_document(message.chat.id, document=original_fn, progress=progress, progress_args=(status_msg, "Uploading"))
        os.remove(original_fn)
    else:
        # ෆයිල් එක ලොකු නම් විතරක් කෑලි වලට කඩනවා
        await status_msg.edit("ලොකු ෆයිල් එකක් නිසා කෑලි වලට කඩමින් පවතී... ✂️")
        subprocess.run(["split", "-b", "1900M", original_fn, "part_"])
        parts = sorted([f for f in os.listdir('.') if f.startswith("part_")])
        for part in parts:
            await client.send_document(message.chat.id, document=part, file_name=f"{part}_{original_fn}")
            os.remove(part)
        os.remove(original_fn)

    await message.reply("වැඩේ සාර්ථකව අවසන්! ✅")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
