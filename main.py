import os
import requests
import threading
import random
import string
import speedtest
from flask import Flask
from pyrogram import Client, filters

# Server එක පණගන්වා තැබීමට
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Online & Fully Fixed!"

def run_flask(): 
    flask_app.run(host='0.0.0.0', port=8000)

# Progress Bar එක
async def progress(current, total, message, type_msg):
    percent = current * 100 / total
    if int(percent) % 15 == 0:
        try:
            await message.edit(f"🚀 {type_msg}: {percent:.1f}% \n📦 {current/(1024*1024):.1f}MB / {total/(1024*1024):.1f}MB")
        except: pass

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- 1. SPEED TEST WITH IMAGE ---
@app.on_message(filters.command("speed") & filters.private)
async def test_speed(client, message):
    msg = await message.reply("වේගය පරීක්ෂා කරමින්... පින්තූරය සකසමින් පවතී 🚀")
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        st.download()
        st.upload()
        res = st.results.dict()
        image_url = res['share']
        caption = (f"⚡ **සර්වර් වේගය:**\n\n⬇️ Download: {res['download']/1_000_000:.2f} Mbps\n"
                   f"⬆️ Upload: {res['upload']/1_000_000:.2f} Mbps\n📡 Ping: {res['ping']} ms")
        await message.reply_photo(photo=image_url, caption=caption)
        await msg.delete()
    except Exception as e:
        await msg.edit(f"වේගය මැනීමේදී ගැටලුවක් විය: {e}")

# --- 2. TEMP MAIL (FIXED) ---
@app.on_message(filters.command("getmail") & filters.private)
async def get_mail(client, message):
    user = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))
    await message.reply_text(f"📧 **ඔයාගේ Temp Mail එක:**\n`{user}@1secmail.com`\n\n📥 Inbox බලන්න:\n/check_{user}")

@app.on_message(filters.regex("^/check_") & filters.private)
async def check_mail(client, message):
    user = message.text.split("_")[1]
    url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={user}&domain=1secmail.com"
    status_msg = await message.reply("Inbox පරීක්ෂා කරමින්... ⏳")
    try:
        response = requests.get(url, timeout=10)
        res = response.json()
        if not res:
            await status_msg.edit("තවම පණිවිඩ ලැබී නැත. විනාඩියක් පමණ රැඳී සිට නැවත බලන්න.")
        else:
            m_id = res[0]['id']
            d_url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={user}&domain=1secmail.com&id={m_id}"
            d_res = requests.get(d_url).json()
            await status_msg.edit(f"📩 **පණිවිඩයක් ලැබුණා!**\n\n👤 **From:** {res[0]['from']}\n📝 **Sub:** {res[0]['subject']}\n\n📄 **Body:**\n{d_res['textBody'][:1000]}")
    except:
        await status_msg.edit("API සම්බන්ධතාවයේ ගැටලුවක්. පසුව උත්සාහ කරන්න.")

# --- 3. DOWNLOADER (LOKU & PODI FILES) ---
@app.on_message(filters.command("download") & filters.private)
async def dl_handler(client, message):
    if len(message.command) < 2:
        await message.reply("Link එකක් එවන්න!")
        return
    url = message.text.split(None, 1)[1]
    fn = url.split("/")[-1].split("?")[0] or "file"
    s_msg = await message.reply("සම්බන්ධ වෙමින්... 🔍")
    try:
        h = requests.head(url, allow_redirects=True)
        size = int(h.headers.get('content-length', 0))
        limit = 1900 * 1024 * 1024 
        
        if size < limit: # සාමාන්‍ය ෆයිල්
            r = requests.get(url, stream=True)
            with open(fn, 'wb') as f:
                dl = 0
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
                        dl += len(chunk)
                        if size > 0 and dl % (20*1024*1024) < (1024*1024):
                            await progress(dl, size, s_msg, "බාගත වෙමින්")
            await s_msg.edit("අප්ලෝඩ් කරමින්... 📤")
            await client.send_document(message.chat.id, document=fn, progress=progress, progress_args=(s_msg, "අප්ලෝඩ් වෙමින්"))
            os.remove(fn)
        else: # විශාල ෆයිල් (කෑලි වලට කඩන කොටස)
            await s_msg.edit(f"විශාල ෆයිල් එකක් ({(size/1024**3):.2f}GB). කෑලි වශයෙන් එවමි... 📦")
            start_byte = 0
            part_num = 1
            while start_byte < size:
                end_byte = min(start_byte + limit - 1, size - 1)
                part_fn = f"Part_{part_num}_{fn}"
                headers = {'Range': f'bytes={start_byte}-{end_byte}'}
                r = requests.get(url, headers=headers, stream=True)
                with open(part_fn, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
                await client.send_document(message.chat.id, document=part_fn)
                os.remove(part_fn)
                start_byte += limit
                part_num += 1
        await s_msg.edit("වැඩේ ඉවරයි! ✅")
    except Exception as e:
        await s_msg.edit(f"Error: {e}")

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text("👋 මම වැඩ!\n⚡ /getmail | ⚡ /speed | ⚡ /download")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
