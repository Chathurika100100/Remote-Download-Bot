import os
import requests
import threading
import time
import subprocess
from flask import Flask
from pyrogram import Client, filters

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Fully Fixed and Running!"

def run_flask(): flask_app.run(host='0.0.0.0', port=8000)

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

CHUNK_SIZE = 1900 * 1024 * 1024 # 1.9GB

# --- START COMMAND ---
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(f"ආයුබෝවන් {message.from_user.first_name}! 🙏\nමම දැන් 100% නිවැරදියි. පොඩි ෆයිල් කෙලින්ම එවනවා, ලොකු ෆයිල් කෑලි කෑලි (Streaming) එවමි.\n\nභාවිතය: `/download [link]`\nවේගය: `/ping`")

# --- PING COMMAND ---
@app.on_message(filters.command("ping") & filters.private)
async def ping(client, message):
    t1 = time.time()
    msg = await message.reply_text("Pinging... ⏳")
    await msg.edit(f"🏓 **Pong!**\nSpeed: `{round((time.time() - t1) * 1000)}ms` ⚡")

# --- DOWNLOAD LOGIC ---
@app.on_message(filters.command("download") & filters.private)
async def download_handler(client, message):
    if len(message.command) < 2: return
    
    url = message.text.split(" ")[1]
    original_fn = url.split("/")[-1].split("?")[0] or "file"
    status_msg = await message.reply("පරීක්ෂා කරමින්... 🔍")

    try:
        head = requests.head(url, allow_redirects=True)
        total_size = int(head.headers.get('content-length', 0))
        limit = 1900 * 1024 * 1024

        # --- පොඩි ෆයිල් නම් (1.9GB ට අඩු) ---
        if total_size < limit:
            await status_msg.edit(f"පොඩි ෆයිල් එකක් ({(total_size/1024/1024):.1f}MB). එකපාර බාගත කරනවා... 📥")
            r = requests.get(url, stream=True)
            with open(original_fn, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk: f.write(chunk)
            
            await status_msg.edit("අප්ලෝඩ් කරමින්... 📤")
            await client.send_document(message.chat.id, document=original_fn)
            os.remove(original_fn)
            await status_msg.edit("වැඩේ ඉවරයි! ✅")

        # --- ලොකු ෆයිල් නම් (1.9GB ට වැඩි) ---
        else:
            await status_msg.edit(f"විශාල ෆයිල් එකක් ({(total_size/1024**3):.2f}GB). කෑලි වශයෙන් වැඩේ අරඹනවා... 📦")
            start_byte = 0
            part_num = 1
            while start_byte < total_size:
                end_byte = min(start_byte + CHUNK_SIZE - 1, total_size - 1)
                part_fn = f"Part_{part_num}_{original_fn}"
                
                # 1.9GB කෑල්ල බානවා
                await status_msg.edit(f"📥 බාගත කරමින්: කෑල්ල {part_num}")
                headers = {'Range': f'bytes={start_byte}-{end_byte}'}
                r = requests.get(url, headers=headers, stream=True)
                with open(part_fn, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)

                # අප්ලෝඩ් කරනවා
                await status_msg.edit(f"📤 අප්ලෝඩ් කරමින්: කෑල්ල {part_num}")
                await client.send_document(message.chat.id, document=part_fn)
                
                # එසැනින් මකනවා (සර්වර් ඉඩ ඉතිරි කිරීමට)
                os.remove(part_fn)
                start_byte += CHUNK_SIZE
                part_num += 1
            
            await status_msg.edit("ලොකු ෆයිල් එකේ සියලුම කෑලි එවා අවසන්! ✅")

    except Exception as e:
        await status_msg.edit(f"අවුලක් වුණා: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
