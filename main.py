import os
import requests
import threading
import speedtest
import time
from flask import Flask
from pyrogram import Client, filters

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Online - Library Speed Method!"

def run_flask(): flask_app.run(host='0.0.0.0', port=8000)

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

# --- 1. SPEED TEST (LIBRARY METHOD WITH RETRY) ---
@app.on_message(filters.command("speed") & filters.private)
async def test_speed(client, message):
    msg = await message.reply("වේගය පරීක්ෂා කරමින්... 🚀")
    
    # Retry 2 times if 403 Forbidden occurs
    for i in range(2):
        try:
            st = speedtest.Speedtest(secure=True)
            st.get_best_server()
            
            d_speed = st.download() / 1_000_000
            u_speed = st.upload() / 1_000_000
            ping = st.results.ping
            
            await msg.edit(f"⚡ **සර්වර් වේගය (Library Method):**\n\n"
                           f"⬇️ Download: {d_speed:.2f} Mbps\n"
                           f"⬆️ Upload: {u_speed:.2f} Mbps\n"
                           f"📡 Ping: {ping} ms")
            return # සාර්ථක නම් loop එකෙන් එලියට යනවා
            
        except Exception as e:
            if i == 0: # පළවෙනි පාර වැරදුණොත් තත්පර 3ක් ඉන්නවා
                time.sleep(3)
                continue
            await msg.edit(f"වේගය මැනීමේදී ගැටලුවක් විය: {e}\n(සර්වර් එකෙන් Block කර ඇත. පසුව උත්සාහ කරන්න.)")

# --- 2. DOWNLOADER ---
@app.on_message(filters.command("download") & filters.private)
async def dl_handler(client, message):
    if len(message.command) < 2:
        await message.reply("Link එකක් එවන්න!")
        return
    url = message.text.split(None, 1)[1]
    fn = url.split("/")[-1].split("?")[0] or "file"
    s_msg = await message.reply("සම්බන්ධ වෙමින්... 🔍")
    try:
        h = requests.head(url, allow_redirects=True)
        size = int(h.headers.get('content-length', 0))
        limit = 1900 * 1024 * 1024 
        
        if size < limit:
            r = requests.get(url, stream=True)
            with open(fn, 'wb') as f:
                dl = 0
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
                        dl += len(chunk)
                        if size > 0 and dl % (20*1024*1024) < (1024*1024):
                            await progress(dl, size, s_msg, "බාගත වෙමින්")
            await s_msg.edit("අප්ලෝඩ් කරමින්... 📤")
            await client.send_document(message.chat.id, document=fn, progress=progress, progress_args=(s_msg, "අප්ලෝඩ් වෙමින්"))
            os.remove(fn)
        else:
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

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
