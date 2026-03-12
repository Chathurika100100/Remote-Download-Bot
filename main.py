import os
import subprocess
import requests
import threading
import libtorrent as lt
import time
from flask import Flask
from pyrogram import Client, filters

# 1. Flask සර්වර් එක (Koyeb සජීවීව තබා ගැනීමට)
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Alive!"

def run_flask(): flask_app.run(host='0.0.0.0', port=8000)

# 2. Progress Bar පෙන්වන Function එක
async def progress(current, total, message, type_msg):
    percent = current * 100 / total
    if int(percent) % 10 == 0:
        try: await message.edit(f"🚀 {type_msg}: {percent:.1f}%...")
        except: pass

# 3. Telegram Bot විස්තර
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- START COMMAND ---
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        f"ආයුබෝවන් {message.from_user.first_name}! 🙏\n\n"
        "මම ඔයාගේ File Downloader බොට්. මට පුළුවන්:\n"
        "✅ Direct Links බාගන්න (/download [link])\n"
        "✅ Torrent Magnet Links බාගන්න (/torrent [magnet])\n\n"
        "ඔයාට උදව්වක් ඕනෙ නම් මට කියන්න!"
    )

# --- TORRENT DOWNLOADER ---
@app.on_message(filters.command("torrent") & filters.private)
async def torrent_download(client, message):
    if len(message.command) < 2:
        await message.reply("කරුණාකර Magnet Link එකක් දෙන්න. උදා: /torrent magnet:?xt=...")
        return

    link = message.text.split(" ")[1]
    status_msg = await message.reply("Torrent එක පරීක්ෂා කරමින්... ⏳")
    
    ses = lt.session()
    params = {"save_path": "./downloads/"}
    handle = lt.add_magnet_uri(ses, link, params)
    
    await status_msg.edit("Metadata ලබා ගනිමින්... (මඳක් රැඳී සිටින්න)")
    while not handle.has_metadata(): time.sleep(1)
    
    await status_msg.edit(f"බාගත වෙමින් පවතී: {handle.status().name}")
    
    while not handle.status().is_seeding:
        s = handle.status()
        await status_msg.edit(f"Downloading Torrent: {s.progress * 100:.2f}% \nSpeed: {s.download_rate / 1000:.2f} kB/s")
        time.sleep(5)

    await status_msg.edit("බාගත කිරීම අවසන්! දැන් ටෙලිග්‍රෑම් එකට එවමින් පවතී...")
    
    file_path = f"./downloads/{handle.status().name}"
    await client.send_document(message.chat.id, document=file_path)
    os.remove(file_path)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
