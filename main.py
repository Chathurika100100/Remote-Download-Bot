import os
import subprocess
import requests
import threading
import shutil
from flask import Flask
from pyrogram import Client, filters

# 1. Koyeb එකට අවශ්‍ය Flask සර්වර් එක
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Running Successfully!"

def run_flask():
    flask_app.run(host='0.0.0.0', port=8000)

# 2. Progress Bar පෙන්වන Function එක
async def progress(current, total, message, type_msg):
    percent = current * 100 / total
    if int(percent) % 10 == 0:
        try:
            await message.edit(f"🚀 {type_msg}: {percent:.1f}%...")
        except:
            pass

# 3. Telegram Bot Setup
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        f"ආයුබෝවන් {message.from_user.first_name}! 🙏\n\n"
        "මම ඔයාගේ Remote Downloader බොට්.\n"
        "ඔයාට ඕනෑම Direct Download ලින්ක් එකක් එවන්න.\n\n"
        "භාවිතය: `/download https://link-here.com/file.zip`"
    )

@app.on_message(filters.command("download") & filters.private)
async def download_handler(client, message):
    if len(message.command) < 2:
        await message.reply("කරුණාකර ලින්ක් එකක් ලබා දෙන්න.")
        return

    url = message.text.split(" ")[1]
    file_name = url.split("/")[-1] if "/" in url else "downloaded_file"
    status_msg = await message.reply("බාගත කරමින් පවතී... ⏳")

    # Download folder සෑදීම
    if not os.path.exists("downloads"): os.makedirs("downloads")
    filepath = os.path.join("downloads", file_name)

    # 1. බාගත කිරීම (Downloading)
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    
    with open(filepath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024*1024):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    await progress(downloaded, total_size, status_msg, "Downloading")

    # 2. Zip කිරීම (Zipping)
    await status_msg.edit("බාගත කිරීම අවසන්. දැන් Zip කරමින් පවතී... 📦")
    zip_path = f"{filepath}.zip"
    shutil.make_archive(filepath, 'zip', "downloads", file_name)

    # 3. කෑලි වලට කැඩීම (Splitting 1.95GB)
    await status_msg.edit("Zip එක 1.95GB කෑලි වලට කඩමින් පවතී... ✂️")
    subprocess.run(["split", "-b", "1950M", zip_path, f"{zip_path}.part"])

    # 4. අප්ලෝඩ් කිරීම (Uploading)
    parts = sorted([f for f in os.listdir('.') if f.startswith(f"{file_name}.zip.part")])
    for part in parts:
        await status_msg.edit(f"Uploading: {part} 📤")
        await client.send_document(
            message.chat.id, 
            document=part, 
            progress=progress, 
            progress_args=(status_msg, f"Uploading {part}")
        )
        os.remove(part)

    # Cleanup
    if os.path.exists(zip_path): os.remove(zip_path)
    shutil.rmtree("downloads")
    await message.reply("සියලුම කෑලි සාර්ථකව යවා අවසන්! ✅")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
