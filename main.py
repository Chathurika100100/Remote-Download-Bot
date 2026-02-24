import os
import time
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- ඔයාගේ API විස්තර මෙතැන තියෙනවා ---
API_ID = 39747634
API_HASH = "df20c86b87c45acf8e409d36f42e6b6c"
# Bot Token එක Koyeb Environment Variables වලින් ලබාගනී
BOT_TOKEN = os.environ.get("TOKEN")

app = Client("my_2gb_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ලින්ක් තාවකාලිකව මතක තබා ගැනීමට
user_data = {}

async def progress(current, total, message, ud_type):
    now = time.time()
    if (now - progress.last_update) < 4:
        return
    progress.last_update = now
    percentage = current * 100 / total
    try:
        await message.edit_text(f"{ud_type}: {percentage:.1f}% ⏳")
    except:
        pass

progress.last_update = 0

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text("ආයුබෝවන්! මම 2GB දක්වා ෆයිල් බාගත කර දෙන බොට් කෙනෙක්. ලින්ක් එකක් එවන්න. 🚀")

@app.on_message(filters.text & filters.private)
async def handle_link(client, message):
    url = message.text
    if url.startswith("http"):
        user_data[message.from_user.id] = url
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("Download Now ✅", callback_data="dl")]])
        await message.reply_text("ඔබට මෙම ගොනුව බාගත කිරීමට අවශ්‍යද?", reply_markup=btn)
    else:
        await message.reply_text("කරුණාකර නිවැරදි URL එකක් එවන්න.")

@app.on_callback_query()
async def callback(client, query):
    if query.data == "dl":
        user_id = query.from_user.id
        url = user_data.get(user_id)
        
        if not url:
            await query.answer("Link not found!", show_alert=True)
            return

        status = await query.edit_message_text("බාගත කරමින් පවතී (Downloading)... 📥")
        file_name = url.split("/")[-1].split("?")[0] or "downloaded_file"

        try:
            # සර්වර් එකට ඩවුන්ලෝඩ් කිරීම
            r = requests.get(url, stream=True)
            with open(file_name, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk: f.write(chunk)

            await status.edit_text("බාගත කිරීම අවසන්! දැන් ඔබට එවමින් පවතී (Uploading)... 📤")

            # ටෙලිග්‍රෑම් එකට අප්ලෝඩ් කිරීම (2GB Limit)
            await client.send_document(
                chat_id=query.message.chat.id,
                document=file_name,
                progress=progress,
                progress_args=(status, "Uploading")
            )
            await status.delete()
        except Exception as e:
            await query.message.reply_text(f"දෝෂයක්: {str(e)}")
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)

app.run()
