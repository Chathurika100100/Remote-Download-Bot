import os
import requests
import threading
import time
from flask import Flask
from pyrogram import Client, filters

# සර්වර් එක Online තබා ගැනීමට
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Online - Fully Fixed Version!"

def run_flask(): 
    flask_app.run(host='0.0.0.0', port=8000)

# ප්‍රගතිය පෙන්වන Function එක
async def progress(current, total, message, type_msg):
    percent = current * 100 / total
    if int(percent) % 15 == 0:
        try:
            await message.edit(f"🚀 {type_msg}: {percent:.1f}% \n📦 {current/(1024*1024):.1f}MB / {total/(1024*1024):.1f}MB")
        except: pass

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- 1. SPEED TEST (No Error Method) ---
@app.on_message(filters.command("speed") & filters.private)
async def test_speed(client, message):
    msg = await message.reply("සර්වර් වේගය පරීක්ෂා කරමින්... 🚀")
    try:
        # 100MB ෆයිල් එකක් පාවිච්චි කරලා වේගය මැනීම
        url = "https://speed.hetzner.de/100MB.bin"
        start_t = time.time()
        r = requests.get(url, timeout=30)
        end_t = time.time()
        
        duration = end_t - start_t
        mbps = (100 * 8) / duration # Megabits per second
        
        await msg.edit(f"⚡ **සර්වර් වේගය (Real-time):**\n\n📊 Download Speed: {mbps:.2f} Mbps\n⏱️ ගතවූ කාලය: {duration:.2f} s")
    except Exception as e:
        await msg.edit(f"වේගය බැලීමේදී ගැටලුවක් විය: {e}")

# --- 2. DOWNLOADER (LOKU & PODI) ---
@app.on_message(filters.command("download") & filters.private)
async def dl_handler(client, message):
    if len(message.command) < 2:
        await message.reply("ලින්ක් එකක් එවන්න!")
        return
    url = message.text.split(None, 1)[1]
    fn = url.split("/")[-1].split("?")[0] or "file"
    s_msg = await message.reply("සම්බන්ධ වෙමින්... 🔍")
    try:
        h = requests.head(url, allow_redirects=True)
        size = int(h.headers.get('content-length', 0))
        limit = 1900 * 1024 * 1024 
        
        if size < limit: # සාමාන්‍ය ෆයිල්
            r = requests.get(url, stream=True)
            with open(fn, 'wb') as f:
                dl = 0
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
                        dl += len(chunk)
                        if size > 0 and dl % (30*1024*1024) < (1024*1024):
                            await progress(dl, size, s_msg, "බාගත වෙමින්")
            await s_msg.edit("අප්ලෝඩ් කරමින්... 📤")
            await client.send_document(message.chat.id, document=fn, progress=progress, progress_args=(s_msg, "අප්ලෝඩ් වෙමින්"))
            os.remove(fn)
        else: # ඉතා විශාල ෆයිල් (Parts)
            await s_msg.edit(f"විශාල ෆයිල් එකක් ({(size/1024**3):.2f}GB). කෑලි වශයෙන් එවමි... 📦")
            start_byte = 0
            part_num = 1
            while start_byte < size:
                end_byte = min(start_byte + limit - 1, size - 1)
                part_fn = f"Part_{part_num}_{fn}"
                headers = {'Range': f'bytes={start_byte}-{end_byte}'}
                r = requests.get(url, headers=headers, stream=True)
                with open(part_fn, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
                await client.send_document(message.chat.id, document=part_fn)
                os.remove(part_fn)
                start_byte += limit
                part_num += 1
        await s_msg.edit("වැඩේ සම්පූර්ණයි! ✅")
    except Exception as e:
        await s_msg.edit(f"Error: {e}")

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text("👋 බොට් සූදානම්!\n\n⚡ /download [link]\n⚡ /speed")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
