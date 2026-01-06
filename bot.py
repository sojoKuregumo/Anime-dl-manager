import os
import asyncio
import requests
from pyrogram import Client, filters, enums

# --- 1. CONFIGURATION ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

CHANNELS = [
    int(os.environ.get("CHANNEL_1", 0)),
    int(os.environ.get("CHANNEL_2", 0)),
    int(os.environ.get("CHANNEL_3", 0))
]

STICKER_ID = os.environ.get("STICKER_ID", "CAACAgUAAxkBAAEQj6hpV0JDpDDOI68yH7lV879XbIWiFwACGAADQ3PJEs4sW1y9vZX3OAQ")

app = Client("manager_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- JIKAN API ---
def get_anime_info(query):
    try:
        url = f"https://api.jikan.moe/v4/anime?q={query}&limit=1"
        res = requests.get(url).json()
        if res['data']:
            anime = res['data'][0]
            img = anime['images']['jpg']['large_image_url']
            
            title = anime['title']
            if "[English Dub]" in query: title += " [English Dub]"
            
            first_word = title.split()[0]
            tag = "#" + "".join(filter(str.isalnum, first_word))

            caption = (
                f"{title} | {anime.get('title_japanese', '')}\n"
                f"{tag}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"• Type: {anime.get('type', 'TV')}\n"
                f"• Episodes: {anime.get('episodes', '?')}\n"
                f"• Duration: {anime.get('duration', '24 min').replace(' per ep', '')}\n"
                f"• Status: {anime.get('status', 'Finished')}"
            )
            return img, caption
    except: return None, None

# ==========================================
# 🚀 1. AUTO-FORWARDER (STRICT DOCUMENT MODE)
# ==========================================
@app.on_message(filters.group & filters.document)
async def auto_forward_files(client, message):
    # 1. Get the file name
    file_name = message.document.file_name
    
    # 2. Check if it is a video file (mp4/mkv)
    if not file_name: return
    if not (file_name.endswith(".mp4") or file_name.endswith(".mkv")):
        return # Ignore non-video documents (like subtitles or zips)

    print(f"[DETECTED] Video Document: {file_name}")

    # 3. Forward to Channels
    for ch_id in CHANNELS:
        if ch_id != 0:
            try:
                await message.forward(ch_id)
                await asyncio.sleep(0.5) 
            except Exception as e:
                print(f"❌ Forward Error {ch_id}: {e}")

# ==========================================
# 📝 2. MANUAL POST
# ==========================================
@app.on_message(filters.command("post"))
async def post_info(client, message):
    query = message.text[6:].strip()
    if not query: return await message.reply("⚠️ Usage: `/post Name`")
    
    status = await message.reply(f"🔎 Fetching: {query}...")
    img, caption = get_anime_info(query)
    
    if img:
        for ch_id in CHANNELS:
            if ch_id != 0:
                try: await client.send_photo(ch_id, photo=img, caption=caption)
                except: pass
        await status.edit_text("✅ Post Sent.")
    else:
        await status.edit_text("❌ Not found.")

# ==========================================
# 🎨 3. MANUAL STICKER
# ==========================================
@app.on_message(filters.command("sticker"))
async def send_sticker_cmd(client, message):
    if not STICKER_ID: return
    for ch_id in CHANNELS:
        if ch_id != 0:
            try: await client.send_sticker(ch_id, sticker=STICKER_ID)
            except: pass
    await message.reply("✅ Sticker Sent.")

print("🤖 MANAGER BOT STARTED (Document Mode)...")
app.run()
