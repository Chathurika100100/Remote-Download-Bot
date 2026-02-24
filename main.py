import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

# --- Koyeb Port Error එක විසඳීමට කුඩා වෙබ් සර්වර් එකක් ---
app_web = Flask('')

@app_web.route('/')
def home():
    return "Bot is running!"

def run_web():
    # Koyeb එක ඉල්ලන Port එකට බොට්ව සම්බන්ධ කරයි
    port = int(os.environ.get("PORT", 8000))
    app_web.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()
# ---------------------------------------------------

# Environment Variables (Koyeb එකේදී අපි ලබා දුන් දත්ත)
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("TOKEN", "")

# Bot එක පණගැන්වීම
app = Client(
    "remote_dl_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message(filters.command("start"))
async def start(client, message):
    user_name = message.from_user.first_name
    await message.reply_text(
        f"හලෝ {user_name}!\n\nමම Remote Download බොට්. මට ඕනෑම direct link එකක් එවන්න, මම ඒක ඔයාට ලේසියෙන් ඩවුන්ලෝඩ් කරගන්න උදව් කරන්නම්.",
        reply_markup=InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("Developer", url="https://t.me/Chathurika100100")
            ]]
        )
    )

@app.on_message(filters.regex(r'http[s]?://'))
async def link_handler(client, message):
    url = message.text
    await message.reply_text(
        "ලින්ක් එක ලැබුණා! ඔයාට මේක දැන්ම ඩවුන්ලෝඩ් කරන්න අවශ්‍යද?",
        reply_markup=InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("Download Now", url=url)
            ]]
        )
    )

if __name__ == "__main__":
    print("Web Server එක පණගැන්වෙනවා...")
    keep_alive()  # මෙතැනින් වෙබ් සර්වර් එක පටන් ගන්නවා
    print("බොට් සාර්ථකව පණගැන්වුණා...")
    app.run()     # මෙතැනින් ටෙලිග්‍රෑම් බොට් වැඩ පටන් ගන්නවා
