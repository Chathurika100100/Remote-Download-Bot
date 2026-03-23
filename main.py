import os
import requests
import threading
import speedtest
import time
import re
from urllib.parse import unquote
from flask import Flask
from pyrogram import Client, filters

# --- සර්වර් එක Online තබා ගැනීමට ---
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "බොට් වැඩ කරයි! 🚀"

def run_flask(): 
    flask_app.run(host='0.0.0.0', port=8000)

# --- පර්සන්ටේජ් සහ නම පෙන්වන Progress Function එක ---
last_update_time = 0

async def progress(current, total, message, type_msg, fn):
    global last_update_time
    now = time.time()
    
    # ටෙලිග්‍රෑම් එකෙන් Block නොවීමට තත්පර 4කට වරක් මැසේජ් එක Edit කරයි
    if now - last_update_time < 4 and current != total:
        return
        
    last_update_time = now
    if total <= 0: return
    
    percent = current * 100 / total
    # ප්‍රගති බාර් එක (Progress Bar)
    progress_bar = "".join(["▰" if i < int(percent / 10) else "▱" for i in range(10)])
    
    try:
        await message.edit(
            f"**{type_msg}:** `{fn}`\n"
            f"📊 `{progress_bar}` **{percent:.1f}%**\n"
            f"📦 **{current/(1024*1024):.1f}MB** / **{total/(1024*1024):.1f}MB**"
        )
    except:
        pass

# --- Configurations ---
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("remote_bot_v3", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

# --- ෆයිල් නම නිවැරදිව ලබා ගැනීම ---
def get_filename(url, headers):
    cd = headers.get('content-disposition')
    if cd:
        fname = re.findall(r'filename\*?=["\']?(?:UTF-8\'\')?([^"\';\n]+)', cd)
        if fname: return unquote(fname[0].strip())
    name = url.split("/")[-1].split("?")[0]
    return unquote(name) if name and "." in name else f"file_{int(time.time())}.zip"

@app.on_message(filters.command("download") & filters.private)
async def dl_handler(client, message):
    text = message.text.split(None, 1)
    if len(text) < 2:
        await message.reply("භාවිතය: `/download link` හෝ `/download link | නම.zip`")
        return
    
    raw_input = text[1]
    manual_name = None
    if "|" in raw_input:
        url, manual_name = raw_input.split("|", 1)
        url, manual_name = url.strip(), manual_name.strip()
    else:
        url = raw_input.strip()

    s_msg = await message.reply("සම්බන්ධ වෙමින්... 🔍")
    
    try:
        with requests.get(url, headers=HEADERS, stream=True, timeout=30, allow_redirects=True) as r:
            r.raise_for_status()
            fn = manual_name if manual_name else get_filename(url, r.headers)
            size = int(r.headers.get('content-length', 0))

            # --- DOWNLOAD පටන් ගැනීම ---
            with open(fn, 'wb') as f:
                dl = 0
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
                        dl += len(chunk)
                        # මෙතනදී නමත් එක්ක Progress එක පෙන්වයි
                        await progress(dl, size, s_msg, "📥 Downloading", fn)
            
            # --- UPLOAD පටන් ගැනීම ---
            await s_msg.edit(f"අප්ලෝඩ් කිරීමට සූදානම්: `{fn}`")
            
            await client.send_document(
                message.chat.id, 
                document=fn, 
                caption=f"✅ `{fn}`",
                progress=progress, 
                progress_args=(s_msg, "📤 Uploading", fn) # නම මෙතනටත් යවයි
            )
            
            os.remove(fn)
            await s_msg.delete()

    except Exception as e:
        if 'fn' in locals() and os.path.exists(fn): os.remove(fn)
        await s_msg.edit(f"❌ Error: {str(e)}")

# --- Start & Speed Commands ---
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply("ආයුබෝවන් ප්‍රවීන්! ලින්ක් එක එවන්න.")

@app.on_message(filters.command("speed") & filters.private)
async def test_speed(client, message):
    msg = await message.reply("වේගය පරීක්ෂා කරයි...")
    st = speedtest.Speedtest(secure=True)
    st.get_best_server()
    await msg.edit(f"🚀 Download: {st.download()/1e6:.2f} Mbps\n📤 Upload: {st.upload()/1e6:.2f} Mbps")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
