import os
import requests
import threading
import time
from flask import Flask
from pyrogram import Client, filters

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Online and Accurate!"

def run_flask(): flask_app.run(host='0.0.0.0', port=8000)

# Progress Bar එක % සමඟ පෙන්වීමට
async def progress(current, total, message, type_msg):
    percent = current * 100 / total
    if int(percent) % 15 == 0:
        try:
            await message.edit(f"🚀 {type_msg}: {percent:.1f}% \n📦 {current/(1024*1024):.1f}MB / {total/(1024*1024):.1f}MB")
        except:
            pass

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(f"ආයුබෝවන් {message.from_user.first_name}! 🙏\nමම දැන් 100% හරි. ලොකු ෆයිල් කෑලි වශයෙන් බාද්දී % පෙන්වනවා.\n\n/download [link] | /ping")

@app.on_message(filters.command("ping") & filters.private)
async def ping(client, message):
    t1 = time.time()
    msg = await message.reply_text("Pinging...")
    await msg.edit(f"🏓 Pong! `{round((time.time() - t1) * 1000)}ms` ⚡")

@app.on_message(filters.command("download") & filters.private)
async def download_handler(client, message):
    if len(message.command) < 2: return
    
    url = message.text.split(" ")[1]
    original_fn = url.split("/")[-1].split("?")[0] or "file"
    status_msg = await message.reply("පරීක්ෂා කරමින්... 🔍")

    try:
        head = requests.head(url, allow_redirects=True)
        total_size = int(head.headers.get('content-length', 0))
        limit = 1900 * 1024 * 1024 # 1.9GB

        # --- 1. පොඩි ෆයිල් (කෙලින්ම බානවා) ---
        if total_size < limit:
            await status_msg.edit("පොඩි ෆයිල් එකක්. බාගත කිරීම අරඹනවා... 📥")
            r = requests.get(url, stream=True)
            with open(original_fn, 'wb') as f:
                dl = 0
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
                        dl += len(chunk)
                        if total_size > 0 and dl % (10*1024*1024) < (1024*1024):
                            await progress(dl, total_size, status_msg, "බාගත වෙමින්")
            
            await status_msg.edit("අප්ලෝඩ් කරමින්... 📤")
            await client.send_document(message.chat.id, document=original_fn, progress=progress, progress_args=(status_msg, "අප්ලෝඩ් වෙමින්"))
            os.remove(original_fn)

        # --- 2. ලොකු ෆයිල් (කෑලි වශයෙන් බාමින් මකමින් යනවා) ---
        else:
            await status_msg.edit(f"විශාල ෆයිල් එකක් ({(total_size/1024**3):.2f}GB). Streaming ඇරඹුවා... 📦")
            start_byte = 0
            part_num = 1
            while start_byte < total_size:
                end_byte = min(start_byte + limit - 1, total_size - 1)
                part_fn = f"Part_{part_num}_{original_fn}"
                curr_size = end_byte - start_byte + 1
                
                # කෑල්ල බානවා
                headers = {'Range': f'bytes={start_byte}-{end_byte}'}
                r = requests.get(url, headers=headers, stream=True)
                with open(part_fn, 'wb') as f:
                    dl = 0
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                            dl += len(chunk)
                            if dl % (20*1024*1024) < (1024*1024):
                                await status_msg.edit(f"📥 බාගත වෙමින් (Part {part_num}): {int(dl*100/curr_size)}%")

                # කෑල්ල අප්ලෝඩ් කරලා මකනවා
                await status_msg.edit(f"📤 අප්ලෝඩ් වෙමින් (Part {part_num})...")
                await client.send_document(message.chat.id, document=part_fn)
                os.remove(part_fn)
                start_byte += limit
                part_num += 1
            
        await status_msg.edit("වැඩේ සම්පූර්ණයි! ✅")

    except Exception as e:
        await status_msg.edit(f"අවුලක් වුණා: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
