import os
import asyncio
import requests
from pyrogram import Client, filters
from aiohttp import web

# --- 1. CONFIGURATION ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Channels (0 if not set)
CHANNELS = {
    "ch1": int(os.environ.get("CHANNEL_1", 0)),
    "ch2": int(os.environ.get("CHANNEL_2", 0)),
    "ch3": int(os.environ.get("CHANNEL_3", 0)),
    "ch4": int(os.environ.get("CHANNEL_4", 0))
}

# 🟢 DEFAULT OFF STATE
# This dict controls forwarding. All False by default.
FORWARD_SETTINGS = {
    "ch1": False,
    "ch2": False,
    "ch3": False,
    "ch4": False
}

STICKER_ID = os.environ.get("STICKER_ID", "")

# Client Setup
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
# 🌐 0. WEB SERVER (RENDER HEALTH CHECK)
# ==========================================
async def health_check(request):
    return web.Response(text="Bot is Running!", status=200)

async def start_web_server():
    # Render provides the PORT env var
    port = int(os.environ.get("PORT", 8080))
    web_app = web.Application()
    web_app.router.add_get("/", health_check)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌍 Web Server running on port {port}")

# ==========================================
# 🚀 1. AUTO-FORWARDER (CONTROLLED)
# ==========================================
@app.on_message(filters.group & filters.document)
async def auto_forward_files(client, message):
    file_name = message.document.file_name
    if not file_name: return
    # Only forward mp4/mkv
    if not (file_name.endswith(".mp4") or file_name.endswith(".mkv")):
        return

    # Check which channels are ON
    for key, is_on in FORWARD_SETTINGS.items():
        target_id = CHANNELS.get(key)
        if is_on and target_id != 0:
            try:
                await message.forward(target_id)
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"❌ Forward {key} Failed: {e}")

# ==========================================
# 🎛️ 2. CHANNEL TOGGLE COMMANDS
# ==========================================
@app.on_message(filters.command(["ch1", "ch2", "ch3", "ch4"]))
async def toggle_channel(client, message):
    cmd = message.command[0].lower() # e.g. "ch1"
    try: state = message.command[1].lower() # "on" or "off"
    except: return await message.reply(f"⚠️ Usage: `/{cmd} on` or `/{cmd} off`")
    
    if cmd in FORWARD_SETTINGS:
        if state == "on":
            FORWARD_SETTINGS[cmd] = True
            await message.reply(f"✅ **{cmd.upper()} Enabled.**")
        elif state == "off":
            FORWARD_SETTINGS[cmd] = False
            await message.reply(f"❌ **{cmd.upper()} Disabled.**")
        else:
            await message.reply("⚠️ Use `on` or `off`")

@app.on_message(filters.command("settings"))
async def check_settings(client, message):
    status = "\n".join([f"📢 {k.upper()}: {'✅ ON' if v else '❌ OFF'}" for k, v in FORWARD_SETTINGS.items()])
    await message.reply(f"**⚙️ Forwarding Status:**\n{status}")

# ==========================================
# 📝 3. POST & STICKER
# ==========================================
@app.on_message(filters.command("post"))
async def post_info(client, message):
    query = message.text[6:].strip()
    if not query: return await message.reply("⚠️ Usage: `/post Name`")
    img, caption = get_anime_info(query)
    
    if img:
        count = 0
        for key, is_on in FORWARD_SETTINGS.items():
            target_id = CHANNELS.get(key)
            if is_on and target_id != 0:
                try: 
                    await client.send_photo(target_id, photo=img, caption=caption)
                    count += 1
                except: pass
        await message.reply(f"✅ Post sent to {count} active channels.")
    else:
        await message.reply("❌ Anime not found.")

@app.on_message(filters.command("sticker"))
async def send_sticker_cmd(client, message):
    if not STICKER_ID: return
    count = 0
    for key, is_on in FORWARD_SETTINGS.items():
        target_id = CHANNELS.get(key)
        if is_on and target_id != 0:
            try: 
                await client.send_sticker(target_id, sticker=STICKER_ID)
                count += 1
            except: pass
    await message.reply(f"✅ Sticker sent to {count} active channels.")

# START BOTH (BOT + WEB SERVER)
async def main():
    await start_web_server()
    print("🤖 MANAGER BOT STARTED (Web Service Active)")
    await app.start()
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())                f"{title} | {anime.get('title_japanese', '')}\n"
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
