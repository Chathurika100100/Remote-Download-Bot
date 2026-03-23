import os
import requests
import threading
import speedtest
import time
from flask import Flask
from pyrogram import Client, filters

# 1. සර්වර් එක දිගටම පණගැන්වීමට (Koyeb/Heroku සඳහා)
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "බොට් වැඩ කරයි! 🚀"

def run_flask(): 
    flask_app.run(host='0.0.0.0', port=8000)

# 2. Progress Bar එක (බාගත වන ප්‍රමාණය පෙන්වීමට)
async def progress(current, total, message, type_msg):
    if total <= 0: return
    percent = current * 100 / total
    if int(percent) % 15 == 0: # හැම 15% කටම වරක් update වේ
        try:
            await message.edit(f"🚀 {type_msg}: {percent:.1f}% \n📦 {current/(1024*1024):.1f}MB / {total/(1024*1024):.1f}MB")
        except: pass

# Environment Variables (Koyeb settings වල ලබා දිය යුතුය)
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("remote_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Browser එකක් ලෙස පෙනී සිටීමට Headers (Direct Link ප්‍රශ්නය විසඳීමට මෙය වැදගත් වේ)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
    'Accept': '*/*'
}

# --- COMMANDS ---

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        "👋 **ආයුබෝවන් ප්‍රවීන්!**\n\n"
        "මම ඔයාගේ Remote Download Bot. මට පුළුවන් ඕනෑම ලින්ක් එකක් කෙලින්ම ටෙලිග්‍රෑම් එකට එවන්න.\n\n"
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
        await msg.edit(f"⚡ **සර්වර් වේගය:**\n\n⬇️ Download: {d_speed:.2f} Mbps\n⬆️ Upload: {u_speed:.2f} Mbps")
    except Exception as e:
        await msg.edit(f"Speed Test Error: {e}")

@app.on_message(filters.command("download") & filters.private)
async def dl_handler(client, message):
    if len(message.command) < 2:
        await message.reply("ලින්ක් එකක් එවන්න! උදා: `/download https://site.com/video.mp4`")
        return
    
    url = message.text.split(None, 1)[1]
    fn = url.split("/")[-1].split("?")[0] or f"file_{int(time.time())}.dat"
    s_msg = await message.reply("සම්බන්ධ වෙමින්... 🔍")
    
    try:
        # ලින්ක් එක Stream එකක් ලෙස ලබා ගැනීම
        with requests.get(url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            size = int(r.headers.get('content-length', 0))
            limit = 1990 * 1024 * 1024 # 2GB limit (ටෙලිග්‍රෑම් සීමාව)
            
            # ලින්ක් එක වෙබ් පිටුවක්ද (HTML) නැත්නම් Direct File එකක්ද කියා බලයි
            ctype = r.headers.get('Content-Type', '')
            if 'text/html' in ctype and size < 200000:
                await s_msg.edit("❌ මේක Direct Link එකක් නෙවෙයි. මට බාන්න බැහැ.")
                return

            await s_msg.edit(f"බාගත වෙමින් පවතී... 📥\nසයිස් එක: {(size/1024**2):.2f} MB")

            # ෆයිල් එක සර්වර් එකේ තාවකාලිකව Save කිරීම
            with open(fn, 'wb') as f:
                dl = 0
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
                        dl += len(chunk)
                        if dl % (40*1024*1024) < (1024*1024): # හැම 40MB කටම වරක් progress පෙන්වයි
                            try: await progress(dl, size if size > 0 else dl, s_msg, "Downloading")
                            except: pass

            if size > limit:
                await s_msg.edit("⚠️ ෆයිල් එක 2GB ට වැඩියි. ටෙලිග්‍රෑම් සාමාන්‍ය බොට් කෙනෙක්ට මේක එවන්න බැහැ.")
                os.remove(fn)
                return

            await s_msg.edit("ටෙලිග්‍රෑම් එකට අප්ලෝඩ් කරමින්... 📤")
            await client.send_document(
                message.chat.id, 
                document=fn, 
                caption=f"✅ `{fn}`",
                progress=progress, 
                progress_args=(s_msg, "Uploading")
            )
            os.remove(fn)
            await s_msg.delete()

    except Exception as e:
        if os.path.exists(fn): os.remove(fn)
        await s_msg.edit(f"❌ **දෝෂය:** `{str(e)}` \n(ලින්ක් එකේ ඇති අකුරු වැරදිදැයි බලන්න)")

if __name__ == "__main__":
    # Flask සර්වර් එක වෙනම thread එකක දුවවයි
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
