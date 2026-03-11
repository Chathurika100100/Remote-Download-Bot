import os
import subprocess
import requests
import threading
from flask import Flask
from pyrogram import Client, filters

# 1. Flask සර්වර් එක (Koyeb Health Check එක සමත් වීමට)
flask_app = Flask(__name__)

@flask_app.route('/')
def status():
    return "Bot is Running Alive!"

def run_flask():
    # Koyeb එක බලන 8000 පෝර්ට් එකේ සර්වර් එක දුවවන්න
    flask_app.run(host='0.0.0.0', port=8000)

# 2. Telegram Bot එකේ විස්තර (Environment Variables හරහා)
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("download"))
async def download_and_split(client, message):
    if len(message.command) < 2:
        await message.reply("කරුණාකර ලින්ක් එක ලබා දෙන්න. උදා: /download https://link.com/game.zip")
        return

    url = message.text.split(" ")[1]
    file_name = "large_game.zip"
    
    status_msg = await message.reply("බාගත කරමින් පවතී... (Downloading...)")

    # මුලින්ම ලොකු ෆයිල් එක බාගැනීම
    r = requests.get(url, stream=True)
    with open(file_name, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024*1024*10): # 10MB chunks
            if chunk:
                f.write(chunk)

    await status_msg.edit("1.95GB කෑලි වලට කඩමින් පවතී... (Splitting...)")

    # Linux 'split' command එකෙන් කෑලි වලට කැඩීම
    subprocess.run(["split", "-b", "1950M", file_name, "part_"])
    os.remove(file_name) # මුල් ෆයිල් එක මකන්න

    # කෑලි එකින් එක අප්ලෝඩ් කර මකා දැමීම (Auto-delete)
    parts = sorted([f for f in os.listdir('.') if f.startswith("part_")])
    
    for part in parts:
        await status_msg.edit(f"අප්ලෝඩ් කරමින් පවතී: {part}")
        await client.send_document(message.chat.id, document=part)
        os.remove(part)
    
    await message.reply("සියලුම කෑලි සාර්ථකව යවන ලදී! ✅")

# 3. ප්‍රධාන ක්‍රියාවලිය
if __name__ == "__main__":
    # Flask සර්වර් එක වෙනම ත්‍රෙඩ් එකක දුවවන්න
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("Bot is starting...")
    app.run()
