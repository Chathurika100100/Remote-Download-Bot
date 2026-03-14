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
def home(): return "Bot is Fully Loaded and Ready!"

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
    await message.reply_text(f"ආයුබෝවන් {message.from_user.first_name}! 🙏\n\n/download [link] - Direct Streaming\n/video [YT link] - YouTube Video\n/song [YT link] - YouTube MP3\n/speed - Test Speed")

@app.on_message(filters.command("speed") & filters.private)
async def speed_test(client, message):
    msg = await message.reply_text("වේගය පරීක්ෂා කරමින් පවතී... ⏳")
    try:
        st = speedtest.Speedtest(secure=True) 
        st.get_best_server()
        d, u = st.download() / 1_000_000, st.upload() / 1_000_000
        await msg.edit(f"🚀 **Server Speed**\n\n🌍 Region: {st.results.server['country']}\n⚡ Ping: {st.results.ping}ms\n📥 Down: {d:.2f}Mbps\n📤 Up: {u:.2f}Mbps")
    except Exception as e:
        await msg.edit(f"Speedtest Error: {e}")

# --- 1. YOUTUBE LOGIC (/video සහ /song) ---
@app.on_message(filters.command(["video", "song"]) & filters.private)
async def youtube_handler(client, message):
    if len(message.command) < 2:
        await message.reply("YouTube ලින්ක් එකක් එවන්න!")
        return
    url = message.text.split(None, 1)[1]
    cmd = message.command[0]
    status_msg = await message.reply("YouTube පරීක්ෂා කරමින්... 📡")
    
    ydl_opts = {
        'format': 'bestaudio/best' if cmd == "song" else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': '%(title)s.%(ext)s',
        'quiet': True,
        'add_header': ['User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36']
    }
    if cmd == "song":
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'video')
            file_name = ydl.prepare_filename(info)
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

# --- 2. DIRECT DOWNLOAD LOGIC (අර කෑලි වශයෙන් බාන ක්‍රමය - Streaming) ---
@app.on_message(filters.command("download") & filters.private)
async def download_handler(client, message):
    if len(message.command) < 2:
        await message.reply("ලින්ක් එකක් එවන්න!")
        return
    url = message.text.split(None, 1)[1]
    if not url.startswith(("http://", "https://")):
        await message.reply("වැරදි ලින්ක් එකක්! ❌")
        return

    original_fn = url.split("/")[-1].split("?")[0] or "file"
    status_msg = await message.reply("පරීක්ෂා කරමින්... 🔍")

    try:
        head = requests.head(url, allow_redirects=True, timeout=10)
        total_size = int(head.headers.get('content-length', 0))
        limit = 1900 * 1024 * 1024 # 1.9GB

        # --- පොඩි ෆයිල් නම් ---
        if total_size < limit:
            await status_msg.edit("බාගත කිරීම ඇරඹුවා... 📥")
            r = requests.get(url, stream=True)
            with open(original_fn, 'wb') as f:
                dl = 0
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
                        dl += len(chunk)
                        if total_size > 0 and dl % (15*1024*1024) < (1024*1024):
                            await progress(dl, total_size, status_msg, "බාගත වෙමින්")
            await status_msg.edit("අප්ලෝඩ් කරමින්... 📤")
            await client.send_document(message.chat.id, document=original_fn, progress=progress, progress_args=(status_msg, "අප්ලෝඩ් වෙමින්"))
            os.remove(original_fn)

        # --- ලොකු ෆයිල් නම් (කෑලි වශයෙන් බාන කොටස මෙන්න) ---
        else:
            await status_msg.edit(f"විශාල ෆයිල් එකක් ({(total_size/1024**3):.2f}GB). Streaming ඇරඹුවා... 📦")
            start_byte = 0
            part_num = 1
            while start_byte < total_size:
                end_byte = min(start_byte + limit - 1, total_size - 1)
                part_fn = f"Part_{part_num}_{original_fn}"
                curr_size = end_byte - start_byte + 1
                headers = {'Range': f'bytes={start_byte}-{end_byte}'}
                r = requests.get(url, headers=headers, stream=True)
                with open(part_fn, 'wb') as f:
                    dl = 0
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                            dl += len(chunk)
                            if dl % (20*1024*1024) < (1024*1024):
                                await status_msg.edit(f"📥 බාගත වෙමින් (Part {part_num}): {int(dl*100/curr_size)}%")

                await status_msg.edit(f"📤 අප්ලෝඩ් වෙමින් (Part {part_num})...")
                await client.send_document(message.chat.id, document=part_fn)
                os.remove(part_fn) # එක කෑල්ලක් යැවූ විගස මකනවා
                start_byte += limit
                part_num += 1
        await status_msg.edit("වැඩේ සම්පූර්ණයි! ✅")
    except Exception as e:
        await status_msg.edit(f"අවුලක් වුණා: {str(e)}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app.run()
