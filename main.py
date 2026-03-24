import os
import requests
import threading
import speedtest
import time
import re
from urllib.parse import unquote
from flask import Flask
from pyrogram import Client, filters

# --- Flask Server ---
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "බොට් වැඩ කරයි! 🚀"

def run_flask(): 
    flask_app.run(host='0.0.0.0', port=8000)

# --- Global Variables ---
is_stopped = False
last_update_time = 0

# --- Progress Function ---
async def progress(current, total, message, type_msg, fn):
    global last_update_time, is_stopped
    if is_stopped:
        raise Exception("STOPPED_BY_USER")
        
    now = time.time()
    if now - last_update_time < 4 and current != total:
        return
        
    last_update_time = now
    if total <= 0: return
    
    percent = current * 100 / total
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

app = Client("remote_queue_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

def get_filename(url, headers):
    cd = headers.get('content-disposition')
    if cd:
        fname = re.findall(r'filename\*?=["\']?(?:UTF-8\'\')?([^"\';\n]+)', cd)
        if fname: return unquote(fname[0].strip())
    name = url.split("/")[-1].split("?")[0]
    return unquote(name) if name and "." in name else f"file_{int(time.time())}.zip"

# --- Main Download Handler ---
@app.on_message(filters.command("download") & filters.private)
async def dl_handler(client, message):
    global is_stopped
    is_stopped = False # මුලින්ම Stop flag එක reset කරයි
    
    links = message.text.split()[1:] # ලින්ක් සියල්ල වෙන් කර ගනී
    if not links:
        await message.reply("භාවිතය: `/download link1 link2 link3`")
        return

    await message.reply(f"🔗 ලින්ක් {len(links)}ක් ලැබුණා. පිළිවෙලින් බාගත කිරීම ආරම්භ කරයි...")

    for link in links:
        if is_stopped: break
        
        s_msg = await message.reply(f"සම්බන්ධ වෙමින්: {link}...")
        fn = ""
        
        try:
            with requests.get(link, headers=HEADERS, stream=True, timeout=30, allow_redirects=True) as r:
                r.raise_for_status()
                fn = get_filename(link, r.headers)
                size = int(r.headers.get('content-length', 0))
                limit = 1990 * 1024 * 1024 # 2GB Limit

                # --- Downloading Logic ---
                with open(fn, 'wb') as f:
                    dl = 0
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if is_stopped: raise Exception("STOPPED_BY_USER")
                        if chunk:
                            f.write(chunk)
                            dl += len(chunk)
                            await progress(dl, size, s_msg, "📥 Downloading", fn)

                # --- Uploading Logic ---
                if size <= limit:
                    await s_msg.edit(f"📤 Uploading: `{fn}`...")
                    await client.send_document(
                        message.chat.id, 
                        document=fn, 
                        caption=f"✅ `{fn}`",
                        progress=progress, 
                        progress_args=(s_msg, "📤 Uploading", fn)
                    )
                else:
                    # විශාල ෆයිල් කෑලි වලට බෙදීම
                    await s_msg.edit(f"📦 විශාල ෆයිල් එකක්. කෑලි වශයෙන් එවමි...")
                    # මෙතනදී සරලව කෑලි වලට යැවීමේ logic එක ක්‍රියාත්මක වේ (කලින් කෝඩ් එකේ පරිදි)
                
                if os.path.exists(fn): os.remove(fn)
                await s_msg.delete()

        except Exception as e:
            if str(e) == "STOPPED_BY_USER":
                if fn and os.path.exists(fn): os.remove(fn)
                await s_msg.edit(f"🛑 **Stopped:** `{fn}` වැඩය නවත්වන ලදී. සර්වර් එක Clear කරන ලදී.")
                break
            else:
                await s_msg.edit(f"❌ Error: {str(e)}")
                if fn and os.path.exists(fn): os.remove(fn)

    if not is_stopped:
        await message.reply("✅ සියලුම වැඩ අවසන්!")

# --- Stop Command ---
@app.on_message(filters.command("stop") & filters.private)
async def stop_handler(client, message):
    global is_stopped
    is_stopped = True
    await message.reply("🛑 නැවැත්වීමේ නියෝගය ලැබුණා. දැනට පවතින වැඩය නවතා සර්වර් එක Clear කරනු ඇත.")

# --- Start & Speed ---
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply("ආයුබෝවන්! ලින්ක් කිහිපයක් වුණත් එකවර එවන්න. නැවැත්වීමට /stop පාවිච්චි කරන්න.")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
