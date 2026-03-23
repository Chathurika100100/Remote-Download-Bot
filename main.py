import os
import requests
import threading
import speedtest
import time
import re
from flask import Flask
from pyrogram import Client, filters

# --- සර්වර් එක Online තබා ගැනීමට (Koyeb/Heroku) ---
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Online! 🚀"

def run_flask(): 
    flask_app.run(host='0.0.0.0', port=8000)

# --- Progress Bar එක ---
async def progress(current, total, message, type_msg):
    if total <= 0: return
    percent = current * 100 / total
    if int(percent) % 15 == 0:
        try:
            await message.edit(f"🚀 {type_msg}: {percent:.1f}% \n📦 {current/(1024*1024):.1f}MB / {total/(1024*1024):.1f}MB")
        except: pass

# --- Configurations ---
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_remote_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Browser එකක් ලෙස පෙනී සිටීමට Headers (Direct Link ප්‍රශ්නය මෙයින් විසඳේ)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
}

# --- බොට්ගේ වැඩකටයුතු ---

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        "👋 **ආයුබෝවන් ප්‍රවීන්!**\n\nමම ඔයාගේ Remote Bot. මට පුළුවන් ඕනෑම ලින්ක් එකක් ටෙලිග්‍රෑම් එකට එවන්න.\n\n"
        "⚡ /download [link] - ෆයිල් බාගත කිරීමට\n"
        "⚡ /speed - සර්වර් වේගය පරීක්ෂා කිරීමට"
    )

@app.on_message(filters.command("speed") & filters.private)
async def test_speed(client, message):
    msg = await message.reply("වේගය පරීක්ෂා කරමින්... 🚀")
    try:
        st = speedtest.Speedtest(secure=True)
        st.get_best_server()
        d_speed = st.download() / 1_000_000
        u_speed = st.upload() / 1_000_000
        await msg.edit(f"⚡ **Server Speed:**\n\n⬇️ Down: {d_speed:.2f} Mbps\n⬆️ Up: {u_speed:.2f} Mbps")
    except Exception as e:
        await msg.edit(f"Speed Test Error: {e}")

@app.on_message(filters.command("download") & filters.private)
async def dl_handler(client, message):
    if len(message.command) < 2:
        await message.reply("ලින්ක් එකක් එවන්න!")
        return
    
    url = message.text.split(None, 1)[1]
    s_msg = await message.reply("සම්බන්ධ වෙමින්... 🔍")
    
    try:
        # 1. ලින්ක් එක පරීක්ෂා කර ඇත්තම නම (Filename) සොයා ගැනීම
        with requests.get(url, headers=HEADERS, stream=True, timeout=20) as r:
            r.raise_for_status()
            
            # Content-Disposition එකෙන් නම බැලීම (FitGirl වගේ සයිට් වලට වැදගත් වේ)
            cd = r.headers.get('content-disposition')
            if cd and 'filename=' in cd:
                fn = re.findall('filename=(.+)', cd)[0].replace('"', '').replace("'", "")
            else:
                fn = url.split("/")[-1].split("?")[0] or f"file_{int(time.time())}.zip"

            size = int(r.headers.get('content-length', 0))
            limit = 1990 * 1024 * 1024  # 2GB Limit
            
            # වෙබ් පිටුවක්ද කියා පරීක්ෂා කිරීම
            if 'text/html' in r.headers.get('Content-Type', '') and size < 100000:
                await s_msg.edit("❌ මේක Direct Link එකක් නෙවෙයි. මට බාන්න බැහැ.")
                return

            await s_msg.edit(f"බාගත වෙමින්: `{fn}`\nසයිස් එක: {(size/1024**2):.2f} MB")

            # 2. ෆයිල් එක බාගත කිරීම (2GB ට වැඩි නම් කෑලි වලට කඩයි)
            if size <= limit:
                # සාමාන්‍ය ෆයිල් (එකම කෑල්ලයි)
                with open(fn, 'wb') as f:
                    dl = 0
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                            dl += len(chunk)
                            if dl % (40*1024*1024) < (1024*1024):
                                try: await progress(dl, size, s_msg, "Downloading")
                                except: pass
                
                await s_msg.edit(f"අප්ලෝඩ් කරමින්: `{fn}`...")
                await client.send_document(message.chat.id, document=fn, caption=f"✅ `{fn}`")
                os.remove(fn)
            
            else:
                # ලොකු ෆයිල් - කෑලි වලට (Parts) බෙදීම
                await s_msg.edit(f"විශාල ෆයිල් එකක් ({(size/1024**3):.2f}GB). කෑලි වශයෙන් එවමි... 📦")
                start_byte = 0
                part_num = 1
                while start_byte < size:
                    end_byte = min(start_byte + limit - 1, size - 1)
                    part_fn = f"Part_{part_num}_{fn}"
                    range_header = {'Range': f'bytes={start_byte}-{end_byte}', **HEADERS}
                    
                    with requests.get(url, headers=range_header, stream=True) as part_r:
                        with open(part_fn, 'wb') as f:
                            for chunk in part_r.iter_content(chunk_size=1024*1024):
                                if chunk: f.write(chunk)
                    
                    await client.send_document(message.chat.id, document=part_fn, caption=f"📦 {part_fn}")
                    os.remove(part_fn)
                    start_byte += limit
                    part_num += 1

            await s_msg.delete()

    except Exception as e:
        await s_msg.edit(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
