import os
import requests
import threading
import speedtest
import time
import re
import random
import string
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

# --- Global Variables ---
is_stopped = False
last_update_time = 0
user_temp_data = {} # Temp Mail දත්ත තාවකාලිකව තබා ගැනීමට

# --- Temp Mail Functions ---
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
    except:
        pass
    return None, None

def check_inbox_api(token):
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get("https://api.mail.tm/messages", headers=headers)
    if res.status_code == 200:
        msgs = res.json().get('hydra:member', [])
        detailed_messages = []
        # අලුත්ම මැසේජ් 3ක ඇතුළත විස්තර (Body) ලබා ගැනීම
        for m in msgs[:3]:
            m_id = m['id']
            m_res = requests.get(f"https://api.mail.tm/messages/{m_id}", headers=headers).json()
            detailed_messages.append(m_res)
        return detailed_messages
    return []

# --- Progress Bar Function ---
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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115.0.0.0 Safari/537.36'
}

def get_filename(url, headers):
    cd = headers.get('content-disposition')
    if cd:
        fname = re.findall(r'filename\*?=["\']?(?:UTF-8\'\')?([^"\';\n]+)', cd)
        if fname: return unquote(fname[0].strip())
    name = url.split("/")[-1].split("?")[0]
    return unquote(name) if name and "." in name else f"file_{int(time.time())}.zip"

# ================= COMMANDS =================

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply(
        "👋 **ආයුබෝවන් ප්‍රවීන්!**\n\n"
        "⚡ `/download [links]` - ලින්ක් download කිරීමට\n"
        "⚡ `/speed` - සර්වර් වේගය පරීක්ෂාවට\n"
        "📧 `/tempmail` - තාවකාලික ඊමේල් සෑදීමට\n"
        "🛑 `/stop` - දැනට පවතින වැඩ නවත්වන්න"
    )

# --- 1. Speed Test ---
@app.on_message(filters.command("speed") & filters.private)
async def test_speed(client, message):
    msg = await message.reply("⚡ වේගය පරීක්ෂා කරමින් පවතී... කරුණාකර රැඳී සිටින්න.")
    try:
        st = speedtest.Speedtest(secure=True)
        st.get_best_server()
        ping = st.results.ping
        await msg.edit(
            f"🚀 **Server Speed Test:**\n\n"
            f"📡 **Ping : ** `{ping:.2f} ms`\n"
            f"⬇️ **download speed : ** `{st.download()/1e6:.2f} Mbps`\n"
            f"⬆️ **upload speed : ** `{st.upload()/1e6:.2f} Mbps`"
        )
    except Exception as e:
        await msg.edit(f"❌ Speed Test Error: {e}")

# --- 2. Stop Command ---
@app.on_message(filters.command("stop") & filters.private)
async def stop_handler(client, message):
    global is_stopped
    is_stopped = True
    await message.reply("🛑 **Stopped!** දැනට පවතින වැඩය නවතා සර්වර් එක Clear කරනු ඇත.")

# --- 3. Temp Mail Command ---
@app.on_message(filters.command("tempmail") & filters.private)
async def get_temp(client, message):
    m = await message.reply("අලුත් Temp Mail එකක් සාදමින්... 📧")
    email, token = create_mail()
    
    if email:
        user_temp_data[message.chat.id] = {"email": email, "token": token}
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Inbox පරීක්ෂා කරන්න", callback_data="check_inbox")]])
        await m.edit(
            f"✅ **ඔබේ තාවකාලික ඊමේල් ලිපිනය:**\n`{email}`\n\n"
            f"පහත බොත්තම ඔබා Inbox එක පරීක්ෂා කරන්න.", 
            reply_markup=keyboard
        )
    else:
        await m.edit("❌ ඊමේල් එක සෑදීමට නොහැකි වුණා. පසුව උත්සාහ කරන්න.")

# --- 4. Temp Mail Callback (Button) ---
@app.on_callback_query(filters.regex("^check_inbox$"))
async def check_inbox_callback(client, callback_query):
    chat_id = callback_query.message.chat.id
    data = user_temp_data.get(chat_id)
    
    if not data:
        await callback_query.answer("❌ ඔබට දැනට සක්‍රීය ඊමේල් එකක් නැත.", show_alert=True)
        return
    
    await callback_query.answer("සම්පූර්ණ විස්තර පරීක්ෂා කරමින්... 🔍")
    try:
        messages = check_inbox_api(data["token"])
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh Inbox", callback_data="check_inbox")]])
        
        if not messages:
            await callback_query.message.edit_text(
                f"✅ **Email:** `{data['email']}`\n\n📭 **Inbox එක තවම හිස්.**", 
                reply_markup=keyboard
            )
            return
        
        inbox_text = f"✅ **Email:** `{data['email']}`\n\n**📥 ලැබී ඇති පණිවිඩ:**\n\n"
        for msg in messages:
            from_addr = msg['from']['address']
            subject = msg['subject']
            body = msg.get('text', 'No content available.')
            
            inbox_text += f"👤 **From:** `{from_addr}`\n"
            inbox_text += f"📝 **Subject:** `{subject}`\n"
            inbox_text += f"📄 **Message:**\n`{body[:800]}`\n" # අකුරු 800ක් දක්වා පෙන්වයි
            inbox_text += "━━━━━━━━━━━━━━━━━━\n"
            
        await callback_query.message.edit_text(inbox_text, reply_markup=keyboard)
    except:
        await callback_query.answer("❌ දෝෂයක් මතු විය.", show_alert=True)

# --- 5. Download Queue System ---
@app.on_message(filters.command("download") & filters.private)
async def dl_handler(client, message):
    global is_stopped
    is_stopped = False
    
    links = message.text.split()[1:]
    if not links:
        await message.reply("භාවිතය: `/download link1 link2`")
        return

    await message.reply(f"🔗 ලින්ක් {len(links)}ක් ලැබුණා. වැඩේ පටන් ගත්තා!")

    for link in links:
        if is_stopped: break
        s_msg = await message.reply(f"සම්බන්ධ වෙමින්: `{link}`")
        fn = ""
        try:
            with requests.get(link, headers=HEADERS, stream=True, timeout=30, allow_redirects=True) as r:
                r.raise_for_status()
                fn = get_filename(link, r.headers)
                size = int(r.headers.get('content-length', 0))
                limit = 1990 * 1024 * 1024 # 2GB limit

                with open(fn, 'wb') as f:
                    dl = 0
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if is_stopped: raise Exception("STOPPED_BY_USER")
                        if chunk:
                            f.write(chunk)
                            dl += len(chunk)
                            await progress(dl, size, s_msg, "📥 Downloading", fn)

                if size <= limit:
                    await client.send_document(
                        message.chat.id, 
                        document=fn, 
                        caption=f"✅ `{fn}`",
                        progress=progress, 
                        progress_args=(s_msg, "📤 Uploading", fn)
                    )
                else:
                    await s_msg.edit(f"📦 විශාල ෆයිල් එකක්. (2GB ට වැඩියි)")
                
                if os.path.exists(fn): os.remove(fn)
                await s_msg.delete()

        except Exception as e:
            if str(e) == "STOPPED_BY_USER":
                if fn and os.path.exists(fn): os.remove(fn)
                await s_msg.edit(f"🛑 **Stopped:** වැඩය නැවැත්තුවා. සර්වර් එක Clear.")
                break
            else:
                await s_msg.edit(f"❌ Error: {str(e)}")
                if fn and os.path.exists(fn): os.remove(fn)

    if not is_stopped:
        await message.reply("✅ සියලුම ලින්ක් download කර අවසන්!")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
