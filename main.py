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

# --- Configurations (Koyeb Env Variables) ---
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("remote_bot_v2", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

# --- Filename එක නිවැරදිව සොයාගන්නා Function එක ---
def get_filename(url, headers):
    # 1. Content-Disposition එක පරීක්ෂා කිරීම
    cd = headers.get('content-disposition')
    if cd:
        # Regex එකකින් නම සොයයි (filename= හෝ filename*=)
        fname = re.findall(r'filename\*?=["\']?(?:UTF-8\'\')?([^"\';\n]+)', cd)
        if fname:
            return unquote(fname[0].strip())
    
    # 2. URL එකේ අන්තිම කොටස පරීක්ෂා කිරීම
    name = url.split("/")[-1].split("?")[0]
    if name and len(name) < 100 and "." in name:
        return unquote(name)
    
    # 3. කිසිවක් නැතිනම් Default නමක් දීම
    return f"file_{int(time.time())}.zip"

@app.on_message(filters.command("download") & filters.private)
async def dl_handler(client, message):
    text = message.text.split(None, 1)
    if len(text) < 2:
        await message.reply("භාවිතය: `/download link` හෝ `/download link | filename.rar`")
        return
    
    # Manual Rename එකක් තිබේදැයි බලයි (| ලකුණෙන් වෙන් කර තිබේ නම්)
    raw_input = text[1]
    manual_name = None
    if "|" in raw_input:
        url, manual_name = raw_input.split("|", 1)
        url = url.strip()
        manual_name = manual_name.strip()
    else:
        url = raw_input.strip()

    s_msg = await message.reply("සම්බන්ධ වෙමින්... 🔍")
    
    try:
        with requests.get(url, headers=HEADERS, stream=True, timeout=30, allow_redirects=True) as r:
            r.raise_for_status()
            
            # නම තීරණය කිරීම
            if manual_name:
                fn = manual_name
            else:
                fn = get_filename(url, r.headers)

            size = int(r.headers.get('content-length', 0))
            limit = 1990 * 1024 * 1024  # 2GB Limit

            await s_msg.edit(f"බාගත වෙමින්: `{fn}`\nසයිස් එක: {(size/1024**2):.2f} MB")

            # බාගත කිරීම
            if size <= limit:
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
                # 2GB ට වැඩි නම් කෑලි වලට කඩයි
                await s_msg.edit(f"විශාල ෆයිල් එකක්. කෑලි වශයෙන් එවමි... 📦")
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

# --- Start & Speed Commands ---
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply("ආයුබෝවන්! ලින්ක් එක එවන්න.")

@app.on_message(filters.command("speed") & filters.private)
async def test_speed(client, message):
    msg = await message.reply("පරීක්ෂා කරමින්...")
    st = speedtest.Speedtest(secure=True)
    st.get_best_server()
    await msg.edit(f"Download: {st.download()/1e6:.2f} Mbps\nUpload: {st.upload()/1e6:.2f} Mbps")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
