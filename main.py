import os
import requests
import threading
import random
import string
from flask import Flask
from pyrogram import Client, filters

# සර්වර් එක දිගටම පණගන්වා තැබීමට Flask App එක
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Online with Downloader & Temp Mail!"

def run_flask(): 
    flask_app.run(host='0.0.0.0', port=8000)

# ප්‍රගතිය පෙන්වන Function එක
async def progress(current, total, message, type_msg):
    percent = current * 100 / total
    if int(percent) % 15 == 0:
        try:
            await message.edit(f"🚀 {type_msg}: {percent:.1f}% \n📦 {current/(1024*1024):.1f}MB / {total/(1024*1024):.1f}MB")
        except: pass

# පරිසර විචල්‍යයන් (Environment Variables)
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- TEMP MAIL FUNCTIONS ---
def generate_username():
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))

@app.on_message(filters.command("getmail") & filters.private)
async def get_mail(client, message):
    user = generate_username()
    domain = "1secmail.com"
    email = f"{user}@{domain}"
    await message.reply_text(
        f"📧 **ඔයාගේ තාවකාලික ඊමේල් එක:**\n`{email}`\n\n"
        f"📥 Inbox එක පරීක්ෂා කිරීමට පහත ලින්ක් එක ක්ලික් කරන්න:\n/check_{user}"
    )

@app.on_message(filters.regex("^/check_") & filters.private)
async def check_mail(client, message):
    user = message.text.split("_")[1]
    domain = "1secmail.com"
    url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={user}&domain={domain}"
    status_msg = await message.reply("Inbox පරීක්ෂා කරමින්... ⏳")
    try:
        res = requests.get(url).json()
        if not res:
            await status_msg.edit("තවම පණිවිඩ ලැබී නැත. (සමහරවිට විනාඩියක් විතර යන්න පුළුවන්)")
        else:
            msg_id = res[0]['id']
            msg_from = res[0]['from']
            msg_sub = res[0]['subject']
            detail_url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={user}&domain={domain}&id={msg_id}"
            detail_res = requests.get(detail_url).json()
            body = detail_res['textBody']
            await status_msg.edit(f"📩 **පණිවිඩයක් ලැබුණා!**\n\n👤 **From:** {msg_from}\n📝 **Sub:** {msg_sub}\n\n📄 **Body:**\n{body[:1000]}")
    except Exception as e:
        await status_msg.edit(f"ගැටලුවක් විය: {e}")

# --- DOWNLOADER FUNCTIONS (LOKU & PODI FILES) ---
@app.on_message(filters.command("download") & filters.private)
async def download_handler(client, message):
    if len(message.command) < 2:
        await message.reply("ලින්ක් එකක් දෙන්න! උදා: `/download https://...`")
        return
    
    url = message.text.split(None, 1)[1]
    original_fn = url.split("/")[-1].split("?")[0] or "file"
    status_msg = await message.reply("සම්බන්ධ වෙමින්... 🔍")

    try:
        head = requests.head(url, allow_redirects=True, timeout=10)
        total_size = int(head.headers.get('content-length', 0))
        limit = 1900 * 1024 * 1024 # 1.9GB

        # 1. සාමාන්‍ය ෆයිල් (2GB ට අඩු)
        if total_size < limit:
            await status_msg.edit("බාගත කිරීම ඇරඹුවා... 📥")
            r = requests.get(url, stream=True)
            with open(original_fn, 'wb') as f:
                dl = 0
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
                        dl += len(chunk)
                        if total_size > 0 and dl % (20*1024*1024) < (1024*1024):
                            await progress(dl, total_size, status_msg, "බාගත වෙමින්")
            
            await status_msg.edit("අප්ලෝඩ් කරමින්... 📤")
            await client.send_document(message.chat.id, document=original_fn, progress=progress, progress_args=(status_msg, "අප්ලෝඩ් වෙමින්"))
            os.remove(original_fn)

        # 2. ඉතා විශාල ෆයිල් (Parts වලට කඩලා එවන්න)
        else:
            await status_msg.edit(f"විශාල ෆයිල් එකක් ({(total_size/1024**3):.2f}GB). කෑලි වශයෙන් එවමි... 📦")
            start_byte = 0
            part_num = 1
            while start_byte < total_size:
                end_byte = min(start_byte + limit - 1, total_size - 1)
                part_fn = f"Part_{part_num}_{original_fn}"
                headers = {'Range': f'bytes={start_byte}-{end_byte}'}
                r = requests.get(url, headers=headers, stream=True)
                with open(part_fn, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
                await status_msg.edit(f"📤 අප්ලෝඩ් වෙමින් Part {part_num}...")
                await client.send_document(message.chat.id, document=part_fn)
                os.remove(part_fn)
                start_byte += limit
                part_num += 1
        await status_msg.edit("වැඩේ ඉවරයි! ✅")
    except Exception as e:
        await status_msg.edit(f"අවුලක් වුණා: {str(e)}")

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        f"Welcome {message.from_user.first_name}! 👋\n\n"
        "⚡ /getmail - තාවකාලික ඊමේල් එකක් ගන්න\n"
        "⚡ /download [link] - ඕනෑම ෆයිල් එකක් බාන්න\n"
    )

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
