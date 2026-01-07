import os
import asyncio
import re
import requests
from pyrogram import Client, filters, idle
from aiohttp import web

# ==============================
# 🔐 CONFIGURATION (FROM RENDER ENV)
# ==============================
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
WORKER_USERNAME = os.environ.get("WORKER_USERNAME")

# Helper to load channels safely
def load_channel(key):
    val = os.environ.get(key)
    if not val: return 0
    try: return int(val)
    except ValueError: return 0

CHANNELS = {
    "ch1": load_channel("CHANNEL_1"),
    "ch2": load_channel("CHANNEL_2"),
    "ch3": load_channel("CHANNEL_3"),
    "ch4": load_channel("CHANNEL_4")
}

STICKER_ID = os.environ.get("STICKER_ID", "")

# Default Settings (Reset on Restart)
FORWARD_SETTINGS = {"ch1": False, "ch2": False, "ch3": False, "ch4": False}
BATCH_STATE = {"sticker_pending": False}

# ==============================
# 🤖 MANAGER CLIENT
# ==============================
app = Client(
    "manager_userbot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    session_string=SESSION_STRING
)

# ==============================
# 🎨 ANIME INFO FETCH (CLEAN STYLE)
# ==============================
def get_anime_info(query):
    try:
        url = f"https://api.jikan.moe/v4/anime?q={query}&limit=1"
        res = requests.get(url).json()
        if not res['data']: return None, None
        anime = res['data'][0]

        img = anime['images']['jpg']['large_image_url']
        title_eng = anime.get('title_english', anime['title'])
        title_jp = anime.get('title_japanese', '')
        
        # Hashtag (First Word)
        first_word = title_eng.split(' ')[0]
        hashtag = "#" + "".join(c for c in first_word if c.isalnum())

        # Audio
        audio_txt = "Japanese [English Sub]"
        if "dub" in query.lower() or "english" in query.lower():
             audio_txt = "English [Dub]"

        # Duration
        duration_raw = anime.get('duration', '24 min')
        duration_clean = duration_raw.replace(' per ep', '').replace(' min.', ' min').strip() + "/Ep"

        caption = (
            f"{title_eng} | {title_jp}\n"
            f"{hashtag}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• Audio: {audio_txt}\n"
            f"• Duration: {duration_clean}\n"
            f"• Quality: 360p, 720p, 1080p"
        )
        return img, caption
    except Exception as e:
        print(f"API Error: {e}")
        return None, None

# ==============================
# 🧠 1. COMMAND PARSER (/dl Spy)
# ==============================
@app.on_message(filters.text & filters.regex(r"^/dl"))
async def command_parser(client, message):
    cmd_text = message.text
    active_channels = [k for k,v in FORWARD_SETTINGS.items() if v]
    
    # Flags Logic
    if "-post" in cmd_text:
        name_match = re.search(r'-a\s+["\']([^"\']+)["\']', cmd_text)
        if name_match and active_channels:
            anime_name = name_match.group(1)
            # Check for Dub flag in command to adjust post text
            is_dub = "-o eng" in cmd_text
            search_q = anime_name + (" dub" if is_dub else "")
            
            img, caption = get_anime_info(search_q)
            if img:
                for key in active_channels:
                    tid = CHANNELS.get(key)
                    if tid:
                        try: await client.send_photo(tid, photo=img, caption=caption)
                        except: pass

    if "-sticker" in cmd_text:
        BATCH_STATE["sticker_pending"] = True
    else:
        BATCH_STATE["sticker_pending"] = False

# ==============================
# 📦 2. FILE COPIER (No Tags)
# ==============================
@app.on_message(filters.document & filters.user(WORKER_USERNAME))
async def auto_forward_files(client, message):
    file_name = message.document.file_name
    if not file_name: return
    if not (file_name.lower().endswith(".mp4") or file_name.lower().endswith(".mkv")): return

    print(f"[👀 SAW FILE] {file_name}")

    for key, is_on in FORWARD_SETTINGS.items():
        target_id = CHANNELS.get(key)
        if is_on and target_id != 0:
            try:
                await message.copy(target_id)
                await asyncio.sleep(1.5)
            except Exception as e:
                print(f"[❌ FAILED] {key}: {e}")

# ==============================
# 🏁 3. BATCH FINISHER (Sticker)
# ==============================
@app.on_message(filters.text & filters.user(WORKER_USERNAME) & filters.regex("Batch Complete"))
async def batch_finisher(client, message):
    if BATCH_STATE["sticker_pending"]:
        await asyncio.sleep(0.5)
        for key, is_on in FORWARD_SETTINGS.items():
            target_id = CHANNELS.get(key)
            if is_on and target_id != 0 and STICKER_ID:
                try: await client.send_sticker(target_id, sticker=STICKER_ID)
                except: pass
        BATCH_STATE["sticker_pending"] = False

# ==============================
# 🎛️ COMMANDS
# ==============================
@app.on_message(filters.command(["ch1", "ch2", "ch3", "ch4"], prefixes="/"))
async def toggle(client, message):
    cmd = message.command[0].lower()
    try: state = message.command[1].lower()
    except: return
    if cmd in FORWARD_SETTINGS:
        FORWARD_SETTINGS[cmd] = (state == "on")
        await message.reply(f"✅ **{cmd.upper()} {'Enabled' if state=='on' else 'Disabled'}.**")

@app.on_message(filters.command("settings", prefixes="/"))
async def settings_cmd(client, message):
    status = "\n".join([f"📢 {k.upper()}: {'✅ ON' if v else '❌ OFF'}" for k, v in FORWARD_SETTINGS.items()])
    await message.reply(f"**⚙️ Forwarding Status:**\n{status}")

# ==============================
# 🌐 WEB SERVER (KEEP-ALIVE)
# ==============================
async def health_check(request):
    return web.Response(text="Manager Userbot is Running!", status=200)

async def start_web_server():
    # Render assigns a random port to the PORT env var
    port = int(os.environ.get("PORT", 8080))
    web_app = web.Application()
    web_app.router.add_get("/", health_check)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌍 Web Server running on port {port}")

# ==============================
# 🚀 MAIN LOOP
# ==============================
async def main():
    await start_web_server()
    print("🔄 Starting Userbot...")
    await app.start()
    me = await app.get_me()
    print(f"✅ LOGGED IN AS: {me.first_name}")
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())
