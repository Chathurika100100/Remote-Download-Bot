import os
import requests
import threading
import random
import string
import speedtest
from flask import Flask
from pyrogram import Client, filters

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Online & Fully Fixed!"

def run_flask(): flask_app.run(host='0.0.0.0', port=8000)

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- SPEED TEST ---
@app.on_message(filters.command("speed") & filters.private)
async def test_speed(client, message):
    msg = await message.reply("වේගය පරීක්ෂා කරමින්... 🚀")
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download_speed = st.download() / 1_000_000
        upload_speed = st.upload() / 1_000_000
        await msg.edit(f"⚡ **සර්වර් වේගය:**\n\n⬇️ Download: {download_speed:.2f} Mbps\n⬆️ Upload: {upload_speed:.2f} Mbps")
    except Exception as e:
        await msg.edit(f"වේගය මැනීමේදී ගැටලුවක් විය: {e}")

# --- TEMP MAIL (FIXED INBOX) ---
@app.on_message(filters.command("getmail") & filters.private)
async def get_mail(client, message):
    user = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))
    domain = "1secmail.com"
    email = f"{user}@{domain}"
    await message.reply_text(f"📧 **ඔයාගේ Temp Mail එක:**\n`{email}`\n\n📥 Inbox පරීක්ෂා කිරීමට:\n/check_{user}")

@app.on_message(filters.regex("^/check_") & filters.private)
async def check_mail(client, message):
    user = message.text.split("_")[1]
    url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={user}&domain=1secmail.com"
    status_msg = await message.reply("Inbox පරීක්ෂා කරමින්... ⏳")
    
    try:
        response = requests.get(url)
        if response.status_code != 200:
            await status_msg.edit("API එකට සම්බන්ධ වීමට නොහැක. පසුව උත්සාහ කරන්න.")
            return
            
        res = response.json()
        if not res:
            await status_msg.edit("තවම පණිවිඩ ලැබී නැත. පණිවිඩයක් එවූ පසු විනාඩියක් පමණ රැඳී සිට බලන්න.")
        else:
            m_id = res[0]['id']
            d_url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={user}&domain=1secmail.com&id={m_id}"
            d_res = requests.get(d_url).json()
            await status_msg.edit(f"📩 **පණිවිඩයක් ඇත!**\n\n👤 **From:** {res[0]['from']}\n📝 **Subject:** {res[0]['subject']}\n\n📄 **Body:**\n{d_res['textBody'][:1000]}")
    except Exception as e:
        await status_msg.edit(f"ගැටලුවක් විය: {str(e)}")

# --- DOWNLOADER (LOKU & PODI) ---
@app.on_message(filters.command("download") & filters.private)
async def dl_handler(client, message):
    if len(message.command) < 2:
        await message.reply("Link එක එවන්න!")
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
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk: f.write(chunk)
            await s_msg.edit("Uploading... 📤")
            await client.send_document(message.chat.id, document=fn)
            os.remove(fn)
        else:
            await s_msg.edit("විශාල ෆයිල් එකක්. Part වලට කඩමින් පසුව එවනු ලැබේ. (මෙය දැනට process වෙමින් පවතී)")
    except Exception as e:
        await s_msg.edit(f"Error: {e}")

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text("⚡ /getmail | ⚡ /download | ⚡ /speed")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
