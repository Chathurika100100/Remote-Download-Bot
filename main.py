import os
import requests
import threading
import time
from flask import Flask
from pyrogram import Client, filters

# 1. Koyeb Health Check
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Streaming Bot is Online!"

def run_flask(): flask_app.run(host='0.0.0.0', port=8000)

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

CHUNK_SIZE = 1900 * 1024 * 1024 # 1.9GB

# --- START COMMAND ---
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        f"ආයුබෝවන් {message.from_user.first_name}! 🙏\n\n"
        "මම ඔයාගේ Smart Downloader බොට්. මම දැන් ලොකු ෆයිල් බාන්නේ කෑලි වශයෙන්.\n\n"
        "භාවිතය: `/download [link]`\n"
        "වේගය බැලීමට: `/ping`"
    )

# --- PING COMMAND ---
@app.on_message(filters.command("ping") & filters.private)
async def ping(client, message):
    start_time = time.time()
    msg = await message.reply_text("පරීක්ෂා කරමින්... ⏳")
    end_time = time.time()
    speed = round((end_time - start_time) * 1000)
    await msg.edit(f"🏓 **Pong!**\nවේගය: `{speed}ms` ⚡")

# --- DOWNLOAD COMMAND (CHUNK METHOD) ---
@app.on_message(filters.command("download") & filters.private)
async def chunk_downloader(client, message):
    if len(message.command) < 2:
        await message.reply("කරුණාකර ලින්ක් එකක් ලබා දෙන්න.")
        return
    
    url = message.text.split(" ")[1]
    original_fn = url.split("/")[-1].split("?")[0] or "file"
    status_msg = await message.reply("ෆයිල් එක පරීක්ෂා කරමින්... 🔍")

    try:
        # 1. ෆයිල් එකේ මුළු සයිස් එක බලනවා
        head = requests.head(url, allow_redirects=True)
        total_size = int(head.headers.get('content-length', 0))

        if total_size == 0:
            await status_msg.edit("Error: ෆයිල් එකේ සයිස් එක ගන්න බැහැ. Direct Link එකක්දැයි පරීක්ෂා කරන්න.")
            return

        await status_msg.edit(f"මුළු ප්‍රමාණය: {total_size / (1024*1024*1024):.2f} GB\nකෑලි වශයෙන් වැඩේ අරඹනවා... 🚀")

        start_byte = 0
        part_num = 1

        while start_byte < total_size:
            end_byte = min(start_byte + CHUNK_SIZE - 1, total_size - 1)
            part_fn = f"Part_{part_num}_{original_fn}"
            
            await status_msg.edit(f"📥 බාගත කරමින්: කෑල්ල {part_num}")
            
            # Range Request භාවිතා කර අදාළ කොටස බා ගැනීම
            headers = {'Range': f'bytes={start_byte}-{end_byte}'}
            r = requests.get(url, headers=headers, stream=True)
            
            with open(part_fn, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk: f.write(chunk)

            await status_msg.edit(f"📤 අප්ලෝඩ් කරමින්: කෑල්ල {part_num}")
            await client.send_document(message.chat.id, document=part_fn, caption=f"Part {part_num}")
            
            # සර්වර් එකේ ඉඩ ඉතිරි කර ගැනීමට එසැනින් මැකීම
            os.remove(part_fn)
            
            start_byte += CHUNK_SIZE
            part_num += 1

        await status_msg.edit("සියලුම කෑලි සාර්ථකව යවා අවසන්! ✅")

    except Exception as e:
        await status_msg.edit(f"අවුලක් වුණා: {str(e)}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
