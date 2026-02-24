import os
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Environment Variables හරහා දත්ත ලබා ගැනීම (මෙය ආරක්ෂිතයි)
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("TOKEN", "")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        f"හලෝ {message.from_user.first_name}!\nමම Remote Download බොට්. මට ඕනෑම ලින්ක් එකක් එවන්න.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Developer", url="https://t.me/your_username")]]
        )
    )

@app.on_message(filters.regex(r'http[s]?://'))
async def download_link(client, message):
    url = message.text
    await message.reply_text(
        "ලින්ක් එක ලැබුණා! මම මේක ඩවුන්ලෝඩ් කරන්නද?",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Download Now", url=url)]]
        )
    )

print("බොට් වැඩ කරන්න පටන් ගත්තා...")
app.run()
