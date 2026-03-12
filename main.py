import os
import subprocess
import requests
import threading
from flask import Flask
from pyrogram import Client, filters

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Large File Bot is Running!"

def run_flask(): flask_app.run(host='0.0.0.0', port=8000)

async def progress(current, total, message, type_msg):
    percent = current * 100 / total
    if int(percent) % 10 == 0:
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
    original_fn = url.split("/")[-1].split("?")[0] or "large_file"
    status_msg = await message.reply("බාගත කිරීම ඇරඹුවා... ⏳")

    # 1. බාගත කිරීම (Downloading)
    r = requests.get(url, stream=True)
    with open(original_fn, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024*1024):
            if chunk: f.write(chunk)

    # 2. Split කිරීම (Zip නොකර කෙලින්ම 1.9GB බැගින්)
    await status_msg.edit("විශාල ෆයිල් එකක් නිසා කෑලි වලට කඩමින් පවතී... ✂️")
    subprocess.run(["split", "-b", "1900M", original_fn, "part_"])

    # 3. අප්ලෝඩ් කිරීම (Uploading)
    parts = sorted([f for f in os.listdir('.') if f.startswith("part_")])
    for part in parts:
        await status_msg.edit(f"අප්ලෝඩ් වෙමින්: {part}")
        await client.send_document(
            message.chat.id, 
            document=part, 
            file_name=f"{part}_{original_fn}",
            progress=progress,
            progress_args=(status_msg, f"Uploading {part}")
        )
        os.remove(part)

    if os.path.exists(original_fn): os.remove(original_fn)
    await message.reply("වැඩේ සම්පූර්ණයි! ✅")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
