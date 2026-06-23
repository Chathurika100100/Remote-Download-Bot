import os
import threading
import speedtest
import time
import re
import random
import string
import math
import asyncio
import aiohttp
from urllib.parse import unquote
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- සර්වර් එක Online තබා ගැනීමට (Keep-Alive) ---
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "බොට් සාර්ථකව ක්‍රියාත්මකයි! 🚀"

def run_flask(): 
    flask_app.run(host='0.0.0.0', port=8000)

# --- Global Configurations & Multi-User Trackers ---
MAX_SINGLE_SIZE = 1.9 * 1024 * 1024 * 1024  # 1.9GB
SPLIT_CHUNK_SIZE = 500 * 1024 * 1024        # 500MB

active_downloads = {}   # යූසර්ලාගේ Download තත්ත්වය තනි තනිව බලාගැනීමට {chat_id: status}
progress_cooldowns = {} # Progress Bar එක හැමෝටම වෙන වෙනම Update වීමට {message_id: last_time}
user_temp_data = {} 

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}

# --- සැබෑ ෆයිල් නම නිවැරදිව ලබාගන්නා Function එක ---
def get_filename(url, headers):
    cd = headers.get('Content-Disposition') or headers.get('content-disposition')
    if cd:
        # 1. මුලින්ම UTF-8 filename එකක් තියෙනවද බලයි (filename*=)
        fname_asterisk = re.findall(r"filename\*=\s*UTF-8''([^;\n]+)", cd, re.IGNORECASE)
        if fname_asterisk:
            return unquote(fname_asterisk[0].strip()).replace("/", "_").replace("\\", "_")
        # 2. සාමාන්‍ය filename= එකක් තියෙනවද බලයි
        fname = re.findall(r'filename=["\']?([^"\';\n]+)["\']?', cd, re.IGNORECASE)
        if fname:
            return unquote(fname[0].strip()).replace("/", "_").replace("\\", "_")
            
    # 3. Header එකේ නැත්නම් විතරක් URL එකෙන් නම කපා ගනී
    name = url.split("/")[-1].split("?")[0]
    if name and "." in name:
        return unquote(name).replace("/", "_").replace("\\", "_")
        
    # 4. කිසිම දෙයක් නැති වුණොත් විතරක් පොදු නමක් දෙයි
    return f"file_{int(time.time())}.zip"

# --- Temp Mail Functions (Async වලින් මාරු කර ඇත) ---
def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

async def create_mail():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://api.mail.tm/domains") as res:
                domain_res = await res.json()
                domain = domain_res['hydra:member'][0]['domain']
            email = f"{generate_random_string()}@{domain}"
            password = "password123"
            data = {"address": email, "password": password}
            async with session.post("https://api.mail.tm/accounts", json=data) as res:
                if res.status == 201:
                    async with session.post("https://api.mail.tm/token", json=data) as token_res:
                        token_data = await token_res.json()
                        return email, token_data['token']
        except: pass
    return None, None

async def check_inbox_api(token):
    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://api.mail.tm/messages", headers=headers) as res:
                if res.status == 200:
                    msgs_data = await res.json()
                    msgs = msgs_data.get('hydra:member', [])
                    detailed_messages = []
                    for m in msgs[:3]:
                        m_id = m['id']
                        async with session.get(f"https://api.mail.tm/messages/{m_id}", headers=headers) as m_res:
                            detailed_messages.append(await m_res.json())
                    return detailed_messages
        except: pass
    return []

# --- Multi-User Progress Bar Function ---
async def progress(current, total, message, type_msg, fn):
    chat_id = message.chat.id
    if active_downloads.get(chat_id) == "stop": 
        raise Exception("STOPPED_BY_USER")
        
    now = time.time()
    msg_id = message.id
    last_update = progress_cooldowns.get(msg_id, 0)
    
    if now - last_update < 5 and current != total: return
    progress_cooldowns[msg_id] = now
    if total <= 0: return
    
    percent = current * 100 / total
    progress_bar = "".join(["▰" if i < int(percent / 10) else "▱" for i in range(10)])
    try:
        await message.edit(
            f"**{type_msg}:** `{fn}`\n"
            f"📊 `{progress_bar}` **{percent:.1f}%**\n"
            f"📦 **{current/(1024*1024):.1f}MB** / **{total/(1024*1024):.1f}MB**"
        )
    except: pass

# --- Bot Initialization ---
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("remote_download_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================= COMMANDS =================

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply(
        "👋 **ආයුබෝවන් ප්‍රවීන්!**\n\n"
        "⚡ `/download [links]` - ලින්ක් download කිරීමට\n"
        "⚡ `/speed` - සර්වර් වේගය පරීක්ෂාවට\n"
        "📧 `/tempmail` - තාවකාලික ඊමේල් සෑදීමට\n"
        "🛑 `/stop` - ඔබගේ වැඩ විතරක් නවත්වන්න"
    )

@app.on_message(filters.command("speed") & filters.private)
async def test_speed(client, message):
    msg = await message.reply("⚡ වේගය පරීක්ෂා කරමින් පවතී...")
    try:
        st = speedtest.Speedtest(secure=True)
        st.get_best_server()
        await msg.edit(
            f"🚀 **Server Speed Test:**\n\n"
            f"📡 **Ping : ** `{st.results.ping:.2f} ms`\n"
            f"⬇️ **Download : ** `{st.download()/1e6:.2f} Mbps`\n"
            f"⬆️ **Upload : ** `{st.upload()/1e6:.2f} Mbps`"
        )
    except Exception as e: await msg.edit(f"❌ Speed Test Error: {e}")

@app.on_message(filters.command("stop") & filters.private)
async def stop_handler(client, message):
    chat_id = message.chat.id
    active_downloads[chat_id] = "stop"  # අනෙක් යූසර්ලට බලපෑමක් වෙන්නේ නැත
    await message.reply("🛑 **Stopped!** ඔබේ බාගත කිරීම නවතා සර්වර් එක Clear කරනු ඇත.")

@app.on_message(filters.command("tempmail") & filters.private)
async def get_temp(client, message):
    m = await message.reply("අලුත් Temp Mail එකක් සාදමින්... 📧")
    email, token = await create_mail()
    if email:
        user_temp_data[message.chat.id] = {"email": email, "token": token}
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Inbox පරීක්ෂා කරන්න", callback_data="check_inbox")]])
        await m.edit(f"✅ **ඔබේ තාවකාලික ඊමේල් ලිපිනය:**\n`{email}`", reply_markup=keyboard)
    else: await m.edit("❌ ඊමේල් එක සෑදීමට නොහැකි වුණා.")

@app.on_callback_query(filters.regex("^check_inbox$"))
async def check_inbox_callback(client, callback_query):
    data = user_temp_data.get(callback_query.message.chat.id)
    if not data: return await callback_query.answer("❌ සක්‍රීය ඊමේල් එකක් නැත.", show_alert=True)
    try:
        messages = await check_inbox_api(data["token"])
        if not messages:
            return await callback_query.message.edit_text(f"✅ **Email:** `{data['email']}`\n\n📭 **Inbox හිස්.**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="check_inbox")]]))
        text = f"✅ **Email:** `{data['email']}`\n\n**📥 පණිවිඩ:**\n\n"
        for msg in messages:
            text += f"👤 **From:** `{msg['from']['address']}`\n📝 **Subject:** `{msg['subject']}`\n📄 **Msg:** `{msg.get('text', '')[:500]}`\n━━━━━━━━━━━━\n"
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="check_inbox")]]))
    except: await callback_query.answer("❌ දෝෂයක් මතු විය.")

# --- සම්පූර්ණයෙන්ම Async කර සකසන ලද Download System එක ---
@app.on_message(filters.command("download") & filters.private)
async def dl_handler(client, message):
    chat_id = message.chat.id
    active_downloads[chat_id] = "running"
    
    links = message.text.split()[1:]
    if not links: return await message.reply("භාවිතය: `/download link`")

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        for link in links:
            if active_downloads.get(chat_id) == "stop": break
            s_msg = await message.reply(f"🔗 සම්බන්ධ වෙමින්: `{link}`")
            fn = None
            try:
                # 1. මුලින්ම සැබෑ ෆයිල් එකේ විස්තර සහ නම ලබාගැනීමට stream එකක් අරඹයි
                async with session.get(link, allow_redirects=True) as response:
                    if response.status not in [200, 206]:
                        await s_msg.edit(f"❌ Error: සර්වර් එක ප්‍රතිචාර දක්වන්නේ නැත ({response.status})")
                        continue
                    
                    total_size = int(response.headers.get('content-length', 0))
                    fn = get_filename(link, response.headers) # සැබෑ නම මෙතනින් වෙන්කර ගනී
                    
                    if total_size > MAX_SINGLE_SIZE:
                        active_chunk = SPLIT_CHUNK_SIZE
                        num_chunks = math.ceil(total_size / active_chunk)
                        await s_msg.edit(f"📦 විශාල ෆයිල් එකක්. කොටස් {num_chunks} කට (500MB බැගින්) බෙදා බාගත කරයි...")
                    else:
                        active_chunk = total_size
                        num_chunks = 1

                # 2. කොටස් වශයෙන් හෝ සම්පූර්ණයෙන් බාගත කිරීමේ ක්‍රියාවලිය
                for i in range(num_chunks):
                    if active_downloads.get(chat_id) == "stop": break
                    
                    part_fn = f"part_{i+1}_{fn}" if num_chunks > 1 else fn
                    
                    if num_chunks > 1:
                        start = i * active_chunk
                        end = min(start + active_chunk - 1, total_size - 1) if total_size > 0 else None
                        r_headers = {'Range': f'bytes={start}-{end}'}
                        req_context = session.get(link, headers=r_headers, allow_redirects=True)
                    else:
                        req_context = session.get(link, allow_redirects=True)

                    async with req_context as r:
                        if r.status not in [200, 206]:
                            raise Exception(f"ෆයිල් කොටස ලබාගැනීම අසාර්ථකයි (Status {r.status})")
                        
                        p_size = int(r.headers.get('content-length', 0))
                        
                        with open(part_fn, 'wb') as f:
                            dl = 0
                            async map for chunk in r.content.iter_chunked(512 * 1024):
                                if active_downloads.get(chat_id) == "stop": raise Exception("STOPPED_BY_USER")
                                f.write(chunk)
                                dl += len(chunk)
                                label = f"📥 Part {i+1}/{num_chunks}" if num_chunks > 1 else "📥 Downloading"
                                await progress(dl, p_size, s_msg, label, part_fn)
                                await asyncio.sleep(0.01)

                    # 3. ටෙලිග්‍රෑම් වෙත අප්ලෝඩ් කිරීම
                    await client.send_document(
                        chat_id, 
                        document=part_fn, 
                        caption=f"✅ `{fn}`" + (f" - Part {i+1}/{num_chunks}" if num_chunks > 1 else ""),
                        progress=progress, 
                        progress_args=(s_msg, f"📤 Uploading" + (f" Part {i+1}" if num_chunks > 1 else ""), part_fn)
                    )
                    if os.path.exists(part_fn): os.remove(part_fn)
                    await asyncio.sleep(1)

                await s_msg.delete()
            except Exception as e:
                err_msg = str(e)
                if err_msg == "STOPPED_BY_USER": await s_msg.edit("🛑 Stopped!")
                else: await s_msg.edit(f"❌ Error: {err_msg}")
                
                # Cleanup (වැඩේ කැඩුණොත් සර්වර් එකේ ඉතිරි වන ෆයිල් මකා දැමීම)
                for f in os.listdir("."):
                    if f.startswith("part_") or (fn and f == fn):
                        try: os.remove(f)
                        except: pass
                break

    if active_downloads.get(chat_id) != "stop": 
        await message.reply("✅ සියලුම වැඩ අවසන්!")
    active_downloads[chat_id] = None

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
