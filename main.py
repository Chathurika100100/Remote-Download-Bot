import os
import requests
import threading
import speedtest
import time
import re
import random
import string
import gdown
import shutil
from urllib.parse import unquote
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- සර්වර් එක Online තබා ගැනීමට (Flask) ---
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Remote Download Bot is Active! 🚀"

def run_flask(): 
    flask_app.run(host='0.0.0.0', port=8000)

# --- Global Variables ---
is_stopped = False
last_update_time = 0
user_temp_data = {}

# Settings
MAX_SINGLE_SIZE = 1.2 * 1024 * 1024 * 1024  # 1.2 GB (මේකට වඩා ලොකු නම් split වේ)
PART_SIZE = 500 * 1024 * 1024               # Split කරන කෑල්ලක සයිස් එක (500MB)

# --- Helper Functions ---
def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def create_mail():
    try:
        domain_res = requests.get("https://api.mail.tm/domains").json()
        domain = domain_res['hydra:member'][0]['domain']
        email = f"{generate_random_string()}@{domain}"
        password = "password123"
        data = {"address": email, "password": password}
        res = requests.post("https://api.mail.tm/accounts", json=data)
        if res.status_code == 201:
            token_res = requests.post("https://api.mail.tm/token", json=data).json()
            return email, token_res['token']
    except: pass
    return None, None

def check_inbox_api(token):
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get("https://api.mail.tm/messages", headers=headers)
    if res.status_code == 200:
        msgs = res.json().get('hydra:member', [])
        detailed_messages = []
        for m in msgs[:3]:
            m_id = m['id']
            m_res = requests.get(f"https://api.mail.tm/messages/{m_id}", headers=headers).json()
            detailed_messages.append(m_res)
        return detailed_messages
    return []

# --- Progress Bar (Downloading සහ Uploading දෙකටම වැඩ) ---
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

app = Client("remote_mega_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def get_filename(url, headers):
    cd = headers.get('content-disposition')
    if cd:
        fname = re.findall(r'filename\*?=["\']?(?:UTF-8\'\')?([^"\';\n]+)', cd)
        if fname: return unquote(fname[0].strip())
    name = url.split("/")[-1].split("?")[0]
    return unquote(name) if name and "." in name else f"file_{int(time.time())}.zip"

# ================= COMMAND HANDLERS =================

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    start_text = (
        "👋 **ආයුබෝවන් ප්‍රවීන්! මම Remote Download බොට්.**\n\n"
        "📜 **ප්‍රධාන විධානයන් (Commands):**\n"
        "🚀 `/download [links]` - ලින්ක් එකක් හෝ කිහිපයක් බාගත කිරීමට\n"
        "⚡ `/speed` - සර්වර් එකේ වේගය පරීක්ෂා කිරීමට\n"
        "📧 `/tempmail` - තාවකාලික ඊමේල් ලිපිනයක් ලබා ගැනීමට\n"
        "🛑 `/stop` - දැනට ක්‍රියාත්මක වන වැඩය නැවැත්වීමට\n\n"
        "💡 *විශාල ෆයිල් (1.2GB+) ස්වයංක්‍රීයව කොටස් වලට බෙදා එවනු ලැබේ.*"
    )
    await message.reply(start_text)

@app.on_message(filters.command("speed") & filters.private)
async def test_speed(client, message):
    msg = await message.reply("⚡ වේගය පරීක්ෂා කරමින් පවතී...")
    try:
        st = speedtest.Speedtest(secure=True)
        st.get_best_server()
        await msg.edit(f"🚀 **DL:** `{st.download()/1e6:.2f} Mbps` | **UP:** `{st.upload()/1e6:.2f} Mbps` | **Ping:** `{st.results.ping:.2f} ms`")
    except Exception as e: await msg.edit(f"❌ Error: {e}")

@app.on_message(filters.command("stop") & filters.private)
async def stop_h(client, message):
    global is_stopped
    is_stopped = True
    await message.reply("🛑 Stopped! සියලු වැඩ නැවැත්තුවා.")

@app.on_message(filters.command("tempmail") & filters.private)
async def get_temp(client, message):
    email, token = create_mail()
    if email:
        user_temp_data[message.chat.id] = {"email": email, "token": token}
        await message.reply(f"📧 `{email}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Inbox", callback_data="check_inbox")]]))

@app.on_callback_query(filters.regex("^check_inbox$"))
async def check_inbox_callback(client, callback_query):
    data = user_temp_data.get(callback_query.message.chat.id)
    if not data: return
    messages = check_inbox_api(data["token"])
    text = f"✅ `{data['email']}`\n\n"
    if not messages: text += "Inbox එක හිස්."
    for msg in messages: text += f"👤 From: {msg['from']['address']}\n📝 {msg['subject']}\n📄 {msg.get('text','')[:500]}\n---\n"
    await callback_query.message.edit_text(text, reply_markup=callback_query.message.reply_markup)

# --- SMART QUEUE DOWNLOAD SYSTEM ---
@app.on_message(filters.command("download") & filters.private)
async def dl_handler(client, message):
    global is_stopped
    is_stopped = False
    input_text = message.text.split()
    if len(input_text) < 2: return await message.reply("❌ කරුණාකර ලින්ක් එකක් ලබා දෙන්න.")
    
    links = input_text[1:]
    for i, link in enumerate(links, 1):
        if is_stopped: break
        s_msg = await message.reply(f"⏳ ({i}/{len(links)}) සම්බන්ධ වෙමින්...")
        
        try:
            # --- Google Drive Link Handling ---
            if "drive.google.com" in link:
                folder_name = f"gdrive_{int(time.time())}"
                os.makedirs(folder_name, exist_ok=True)
                await s_msg.edit(f"📂 GDrive බාගත කරමින්...")
                if "/folder/" in link or "drive/folders/" in link:
                    gdown.download_folder(url=link, output=folder_name, quiet=True)
                else:
                    gdown.download(url=link, output=f"{folder_name}/", quiet=True, fuzzy=True)

                zip_path = shutil.make_archive(folder_name, 'zip', folder_name)
                fn = os.path.basename(zip_path)
                
                # Uploading GDrive Zip with Progress
                await client.send_document(
                    message.chat.id, 
                    document=fn, 
                    caption=f"✅ `{fn}` (GDrive)", 
                    progress=progress, 
                    progress_args=(s_msg, "📤 Uploading", fn)
                )
                if os.path.exists(fn): os.remove(fn)
                shutil.rmtree(folder_name)
            
            # --- Direct Link Handling ---
            else:
                with requests.get(link, headers=HEADERS, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get('content-length', 0))
                    fn = get_filename(link, r.headers)
                    
                    # 1.2GB ට වඩා වැඩි නම් SPLIT කරනවා
                    if total_size > MAX_SINGLE_SIZE:
                        part_num = 1
                        downloaded_total = 0
                        while downloaded_total < total_size:
                            if is_stopped: break
                            part_fn = f"{fn}.{part_num:03d}"
                            current_part_size = 0
                            with open(part_fn, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=1024*1024):
                                    if is_stopped: break
                                    f.write(chunk)
                                    current_part_size += len(chunk)
                                    downloaded_total += len(chunk)
                                    await progress(downloaded_total, total_size, s_msg, f"📥 Part {part_num} බාමින්", fn)
                                    if current_part_size >= PART_SIZE: break
                            
                            # Upload Part with Progress
                            await client.send_document(
                                message.chat.id, 
                                document=part_fn, 
                                caption=f"📦 Part {part_num} - `{fn}`",
                                progress=progress, 
                                progress_args=(s_msg, "📤 Uploading", part_fn)
                            )
                            if os.path.exists(part_fn): os.remove(part_fn)
                            part_num += 1
                    
                    # 1.2GB ට අඩු නම් සාමාන්‍ය බාගත කිරීම
                    else:
                        with open(fn, 'wb') as f:
                            dl = 0
                            for chunk in r.iter_content(chunk_size=1024*1024):
                                if is_stopped: break
                                f.write(chunk)
                                dl += len(chunk)
                                await progress(dl, total_size, s_msg, "📥 Downloading", fn)
                        
                        # Normal Upload with Progress
                        await client.send_document(
                            message.chat.id, 
                            document=fn, 
                            caption=f"✅ `{fn}`", 
                            progress=progress, 
                            progress_args=(s_msg, "📤 Uploading", fn)
                        )
                        if os.path.exists(fn): os.remove(fn)

            await s_msg.delete()
        except Exception as e:
            if str(e) == "STOPPED_BY_USER":
                await s_msg.edit("🛑 වැඩය නතර කළා!")
                break
            else:
                await s_msg.edit(f"❌ Error: {str(e)}")

    if not is_stopped: await message.reply("✅ පෝලිමේ තිබූ සියලුම ලින්ක් බාගත කර අවසන්!")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
