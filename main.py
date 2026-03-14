import os
import requests
import threading
import time
import speedtest
import yt_dlp
from flask import Flask
from pyrogram import Client, filters

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Alive with YouTube Downloader!"

def run_flask(): flask_app.run(host='0.0.0.0', port=8000)

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

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(f"ආයුබෝවන් {message.from_user.first_name}! 🙏\n\n/download [link] - Direct Link\n/video [YT link] - YouTube Video\n/song [YT link] - YouTube MP3\n/speed - Server Speed")

@app.on_message(filters.command("speed") & filters.private)
async def speed_test(client, message):
    msg = await message.reply_text("වේගය පරීක්ෂා කරමින් පවතී... ⏳")
    try:
        st = speedtest.Speedtest(secure=True) 
        st.get_best_server()
        d, u = st.download() / 1_000_000, st.upload() / 1_000_000
        await msg.edit(f"🚀 **Server Speed**\n\n🌍 Region: {st.results.server['country']}\n📥 Down: {d:.2f}Mbps | 📤 Up: {u:.2f}Mbps")
    except Exception as e:
        await msg.edit(f"Speedtest Error: {e}")

# --- YOUTUBE DOWNLOAD LOGIC (/video සහ /song) ---
@app.on_message(filters.command(["video", "song"]) & filters.private)
async def youtube_handler(client, message):
    if len(message.command) < 2:
        await message.reply("කරුණාකර YouTube ලින්ක් එකක් ලබා දෙන්න!")
        return
    
    url = message.text.split(None, 1)[1]
    cmd = message.command[0]
    status_msg = await message.reply("YouTube වෙත සම්බන්ධ වෙමින්... 📡")

    ydl_opts = {
        'format': 'bestaudio/best' if cmd == "song" else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': '%(title)s.%(ext)s',
        'quiet': True,
    }

    if cmd == "song":
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'video')
            await status_msg.edit(f"බාගත කරමින්: **{title}**... 📥")
            
            # ඇත්තටම ඩවුන්ලෝඩ් කිරීම
            file_info = ydl.extract_info(url, download=True)
            file_name = ydl.prepare_filename(file_info)
            if cmd == "song": file_name = file_name.rsplit('.', 1)[0] + ".mp3"

        await status_msg.edit("ටෙලිග්‍රෑම් වෙත අප්ලෝඩ් කරමින්... 📤")
        
        if cmd == "song":
            await client.send_audio(message.chat.id, audio=file_name, caption=title)
        else:
            await client.send_video(message.chat.id, video=file_name, caption=title)
        
        os.remove(file_name)
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit(f"YouTube වැරැද්දක්: {str(e)}")

# --- DIRECT DOWNLOAD LOGIC (කලින් තිබුණ එකමයි) ---
@app.on_message(filters.command("download") & filters.private)
async def download_handler(client, message):
    if len(message.command) < 2:
        await message.reply("ලින්ක් එකක් එවන්න!")
        return
    url = message.text.split(None, 1)[1]
    status_msg = await message.reply("සම්බන්ධ වෙමින්... 🔍")
    try:
        head = requests.head(url, allow_redirects=True, timeout=10)
        total_size = int(head.headers.get('content-length', 0))
        fn = url.split("/")[-1].split("?")[0] or "file"
        
        # මෙතන ඔයාගේ පරණ Streaming logic එක තියෙනවා...
        # (ඉඩ මදි නිසා මම කෙටියෙන් දැම්මේ, ඔයාගේ පරණ කෝඩ් එකේ තිබුණ කොටසම මෙතනට එනවා)
        r = requests.get(url, stream=True)
        with open(fn, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk: f.write(chunk)
        await client.send_document(message.chat.id, document=fn)
        os.remove(fn)
        await status_msg.edit("වැඩේ ඉවරයි! ✅")
    except Exception as e:
        await status_msg.edit(f"Error: {e}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
