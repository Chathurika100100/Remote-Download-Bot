import os
import subprocess
import requests
import threading
from flask import Flask
from pyrogram import Client, filters

# Koyeb Health Check
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Alive!"

def run_flask(): flask_app.run(host='0.0.0.0', port=8000)

async def progress(current, total, message, type_msg):
    percent = current * 100 / total
    if int(percent) % 20 == 0: # Update less often to avoid flood
        try: await message.edit(f"🚀 {type_msg}: {percent:.1f}%")
        except: pass

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("download"))
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
                # Download progress එක පෙන්වීම
                if total_size > 0 and int(dl * 100 / total_size) % 20 == 0:
                    try: await status_msg.edit(f"Downloading: {int(dl * 100 / total_size)}%")
                    except: pass

    file_size = os.path.getsize(original_fn)
    limit = 1900 * 1024 * 1024  # 1.9GB

    # 2. පරීක්ෂා කිරීම සහ යැවීම
    if file_size < limit:
        # ෆයිල් එක කුඩා නම් කෙලින්ම යවනවා
        await status_msg.edit("Uploading file... 📤")
        await client.send_document(message.chat.id, document=original_fn, progress=progress, progress_args=(status_msg, "Uploading"))
    else:
        # ෆයිල් එක ලොකු නම් කෑලි වලට කඩනවා
        await status_msg.edit("Splitting large file... ✂️")
        subprocess.run(["split", "-b", "1900M", original_fn, "part_"])
        parts = sorted([f for f in os.listdir('.') if f.startswith("part_")])
        
        for part in parts:
            await status_msg.edit(f"Uploading: {part}")
            await client.send_document(message.chat.id, document=part, file_name=f"{part}_{original_fn}")
            os.remove(part)

    if os.path.exists(original_fn): os.remove(original_fn)
    await message.reply("වැඩේ සාර්ථකව අවසන්! ✅")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
