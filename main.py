import os
import subprocess
import requests
from pyrogram import Client, filters

# Environment Variables හරහා රහස් විස්තර ලබා ගැනීම (ආරක්ෂිත ක්‍රමය)
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command("download"))
async def download_and_split(client, message):
    if len(message.command) < 2:
        await message.reply("කරුණාකර ලින්ක් එක ලබා දෙන්න. උදා: /download https://link.com/game.zip")
        return

    url = message.text.split(" ")[1]
    file_name = "large_game.zip"
    
    status = await message.reply("බාගත කරමින් පවතී... (Downloading...)")

    # 1. මුලින්ම ෆයිල් එක බාගැනීම
    r = requests.get(url, stream=True)
    with open(file_name, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024*1024*10): # 10MB chunks
            if chunk:
                f.write(chunk)

    await status.edit("ෆයිල් එක කෑලි වලට කඩමින් පවතී... (Splitting into 1.95GB chunks...)")

    # 2. Linux 'split' command එක පාවිච්චි කරලා 1.95GB කෑලි වලට කැඩීම
    # Koyeb Linux නිසා මේක වැඩ කරනවා.
    subprocess.run(["split", "-b", "1950M", file_name, "part_"])

    # මුල් ලොකු ෆයිල් එක මකා දැමීම (ඉඩ ඉතිරි කරගන්න)
    os.remove(file_name)

    # 3. එකින් එක ටෙලිග්‍රෑම් එකට අප්ලෝඩ් කිරීම සහ මැකීම
    parts = sorted([f for f in os.listdir('.') if f.startswith("part_")])
    
    for part in parts:
        await status.edit(f"අප්ලෝඩ් කරමින් පවතී: {part}")
        await client.send_document(message.chat.id, document=part)
        
        # අප්ලෝඩ් කළ පසු වහාම මකා දැමීම
        os.remove(part)
    
    await message.reply("සියලුම කෑලි සාර්ථකව යවන ලදී! Hosting website එක පිරිසිදු කරන ලදී. ✅")

print("Bot is started...")
app.run()

os.system("python3 -m http.server 8000 &")
