import os
import subprocess
import requests
import threading
from flask import Flask
from pyrogram import Client, filters

# 1. HTTP Protocol එකට ගැලපෙන Flask සර්වර් එක
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is Alive and Running on HTTP Port 8000!"

def run_flask():
    # Koyeb ඉල්ලන 8000 පෝර්ට් එකේ HTTP සර්වර් එක දුවවන්න
    flask_app.run(host='0.0.0.0', port=8000)

# 2. Progress Bar පෙන්වන Function එක
async def progress(current, total, message, type_msg):
    percent = current * 100 / total
    if int(percent) % 10 == 0: # සෑම 10% කටම වරක් මැසේජ් එක අප්ඩේට් කරයි
        try:
            await message.edit(f"🚀 {type_msg}: {percent:.1f}%...")
        except:
            pass

# 3. Telegram Bot විස්තර
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("download"))
async def download_and_split(client, message):
    if len(message.command) < 2:
        await message.reply("කරුණාකර ලින්ක් එක ලබා දෙන්න.")
        return

    url = message.text.split(" ")[1]
    file_name = "large_game.zip"
    status_msg = await message.reply("Downloading... ⏳")

    # බාගත කිරීම
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    with open(file_name, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024*1024):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    await progress(downloaded, total_size, status_msg, "Downloading")

    await status_msg.edit("Splitting into 1.95GB chunks... ✂️")
    subprocess.run(["split", "-b", "1950M", file_name, "part_"])
    os.remove(file_name)

    # අප්ලෝඩ් කිරීම
    parts = sorted([f for f in os.listdir('.') if f.startswith("part_")])
    for part in parts:
        await status_msg.edit(f"Uploading: {part}")
        await client.send_document(
            message.chat.id, 
            document=part,
            progress=progress,
            progress_args=(status_msg, f"Uploading {part}")
        )
        os.remove(part)
    
    await message.reply("සියලුම කෑලි සාර්ථකව යවන ලදී! ✅")

if __name__ == "__main__":
    # Flask HTTP සර්වර් එක Background එකේ දුවවන්න
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
