import os
import asyncio
import requests
from pyrogram import Client, filters, idle
from aiohttp import web

# --- 1. CONFIGURATION ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

def load_channel(key):
    val = os.environ.get(key)
    if not val: return 0
    try: return int(val)
    except ValueError: return val

CHANNELS = {
    "ch1": load_channel("CHANNEL_1"),
    "ch2": load_channel("CHANNEL_2"),
    "ch3": load_channel("CHANNEL_3"),
    "ch4": load_channel("CHANNEL_4")
}

FORWARD_SETTINGS = {"ch1": False, "ch2": False, "ch3": False, "ch4": False}
STICKER_ID = os.environ.get("STICKER_ID", "")

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

# --- WEB SERVER ---
async def health_check(request): return web.Response(text="Running", status=200)

async def start_web_server():
    port = int(os.environ.get("PORT", 8080))
    web_app = web.Application()
    web_app.router.add_get("/", health_check)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌍 Web Server running on port {port}")

# ==========================================
# 🚀 1. AUTO-FORWARDER (DEBUG MODE)
# ==========================================
@app.on_message(filters.group & filters.document)
async def auto_forward_files(client, message):
    file_name = message.document.file_name
    if not file_name: return

    # 🟢 DEBUG PRINT: What did we see?
    print(f"[DEBUG] Saw file: {file_name}")

    # Case-Insensitive Check (.mp4, .MP4, .mkv, .MKV)
    if not (file_name.lower().endswith(".mp4") or file_name.lower().endswith(".mkv")):
        print(f"[DEBUG] Ignoring {file_name} (Not a video)")
        return

    print(f"[DETECTED] Video: {file_name} -> Checking settings...")

    for key, is_on in FORWARD_SETTINGS.items():
        target_id = CHANNELS.get(key)
        if is_on and target_id:
            try:
                await message.forward(target_id)
                print(f"[SUCCESS] Forwarded to {key}")
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"❌ Forward {key} Failed: {e}")

# ==========================================
# 🎛️ 2. COMMANDS
# ==========================================
@app.on_message(filters.command(["ch1", "ch2", "ch3", "ch4"]))
async def toggle_channel(client, message):
    cmd = message.command[0].lower()
    try: state = message.command[1].lower()
    except: return await message.reply(f"⚠️ Usage: `/{cmd} on` or `/{cmd} off`")
    if cmd in FORWARD_SETTINGS:
        FORWARD_SETTINGS[cmd] = (state == "on")
        await message.reply(f"✅ **{cmd.upper()} {'Enabled' if state=='on' else 'Disabled'}.**")

@app.on_message(filters.command("settings"))
async def check_settings(client, message):
    status = "\n".join([f"📢 {k.upper()}: {'✅ ON' if v else '❌ OFF'}" for k, v in FORWARD_SETTINGS.items()])
    await message.reply(f"**⚙️ Forwarding Status:**\n{status}")

@app.on_message(filters.command("post"))
async def post_info(client, message):
    query = message.text[6:].strip()
    if not query: return await message.reply("⚠️ Usage: `/post Name`")
    img, caption = get_anime_info(query)
    if img:
        count = 0
        for key, is_on in FORWARD_SETTINGS.items():
            target_id = CHANNELS.get(key)
            if is_on and target_id:
                try: 
                    await client.send_photo(target_id, photo=img, caption=caption)
                    count += 1
                except: pass
        await message.reply(f"✅ Post sent to {count} active channels.")
    else: await message.reply("❌ Anime not found.")

@app.on_message(filters.command("sticker"))
async def send_sticker_cmd(client, message):
    if not STICKER_ID: return
    count = 0
    for key, is_on in FORWARD_SETTINGS.items():
        target_id = CHANNELS.get(key)
        if is_on and target_id:
            try: 
                await client.send_sticker(target_id, sticker=STICKER_ID)
                count += 1
            except: pass
    await message.reply(f"✅ Sticker sent to {count} active channels.")

async def main():
    await start_web_server()
    print("🤖 MANAGER BOT STARTED (Debug Mode)")
    await app.start()
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())
