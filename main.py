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
def home(): return "Bot is Ready!"

def run_flask(): flask_app.run(host='0.0.0.0', port=8000)

# 2. Progress Bar එක (%)
async def progress(current, total, message, type_msg):
    percent = current * 100 / total
    # පණිවිඩය අප්ඩේට් කරන්නේ සෑම 15% කට වරක් (Telegram Limit එක නිසා)
    if int(percent) % 15 == 0:
        try:
            await message.edit(f"🚀 {type_msg}: {percent:.1f}% [{current/(1024*1024):.1f}MB / {total/(1024*1024):.1f}MB]")
        except:
            pass

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(f"ආයුබෝවන් {message.from_user.first_name}! 🙏\n\nමම ඔයාගේ Downloader බොට්. \n\nභාවිතය: `/download [link]`")

@app.on_message(filters.command("ping") & filters.private)
async def ping(client, message):
    start_t = time.time()
    msg = await message.reply_text("Pinging...")
    speed = round((time.time() - start_t) * 1000)
    await msg.edit(f"🏓 Pong! `{speed}ms` ⚡")

@app.on_message(filters.command("download") & filters.private)
async def download_handler(client, message):
    if len(message.command) < 2: return
    
    url = message.text.split(" ")[1]
    original_fn = url.split("/")[-1].split("?")[0] or "file"
    status_msg = await message.reply("Downloading... ⏳")

    # 1. බාගත කිරීම
    r = requests.get(url, stream=True)
    total_size = int(r.headers.get('content-length', 0))
    
    with open(original_fn, 'wb') as f:
        dl = 0
        for chunk in r.iter_content(chunk_size=1024*1024):
            if chunk:
                f.write(chunk)
                dl += len(chunk)
                if total_size > 0:
                    await progress(dl, total_size, status_msg, "බාගත වෙමින්")

    file_size = os.path.getsize(original_fn)
    limit = 1900 * 1024 * 1024 

    # 2. Upload හෝ Split කිරීම
    if file_size < limit:
        await status_msg.edit("අප්ලෝඩ් කරමින්... 📤")
        await client.send_document(message.chat.id, document=original_fn, progress=progress, progress_args=(status_msg, "අප්ලෝඩ් වෙමින්"))
        os.remove(original_fn)
    else:
        await status_msg.edit("ලොකු ෆයිල් එකක් නිසා කෑලි වලට කඩනවා... ✂️")
        # Split command එක
        subprocess.run(["split", "-b", "1900M", original_fn, "part_"])
        
        parts = sorted([f for f in os.listdir('.') if f.startswith("part_")])
        for part in parts:
            await status_msg.edit(f"අප්ලෝඩ් වෙමින්: {part} 📤")
            await client.send_document(message.chat.id, document=part, file_name=f"{part}_{original_fn}")
            os.remove(part)
        
        os.remove(original_fn)

    await message.reply("වැඩේ සාර්ථකව අවසන්! ✅")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
