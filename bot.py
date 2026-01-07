import os
import asyncio
import requests
from pyrogram import Client, filters, idle
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid
from aiohttp import web

# --- 1. CONFIGURATION ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

# 🟢 TARGET WATCHING (Handle common mistakes like adding '@')
WORKER_RAW = os.environ.get("WORKER_USERNAME", "")
WORKER_USERNAME = WORKER_RAW.replace("@", "").strip()

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

app = Client("manager_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

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
async def health_check(request): return web.Response(text="Userbot Alive", status=200)

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
# 🛠️ NEW: DEBUG COMMAND (Test without Downloading)
# ==========================================
@app.on_message(filters.command("debug", prefixes="/"))
async def debug_message(client, message):
    if not message.reply_to_message:
        return await message.reply("⚠️ **Reply to a file/video to debug it.**")
    
    target = message.reply_to_message
    file_name = target.document.file_name if target.document else "Unknown/Video"
    sender = target.from_user.username if target.from_user else "Unknown"
    
    report = (
        f"🕵️ **DEBUG REPORT**\n"
        f"• **File Name:** `{file_name}`\n"
        f"• **Sent By:** @{sender}\n"
        f"• **My Target Worker:** @{WORKER_USERNAME}\n"
        f"• **Match?** {'✅ YES' if sender.lower() == WORKER_USERNAME.lower() else '❌ NO'}\n"
        f"• **Is Video?** {'✅ YES' if file_name.endswith(('.mp4', '.mkv')) else '❌ NO'}"
    )
    
    # Try a fake forward to test permissions
    try:
        active_ch = [k for k, v in FORWARD_SETTINGS.items() if v]
        if active_ch:
            dest = CHANNELS[active_ch[0]]
            await target.forward(dest)
            report += f"\n\n✅ **Test Forward Success:** Sent to {active_ch[0]}"
        else:
            report += "\n\n⚠️ **Test Skipped:** No channels turned ON."
    except Exception as e:
        report += f"\n\n❌ **Test Forward FAILED:** {e}"
        
    await message.reply(report)

# ==========================================
# 🎯 TARGETED AUTO-FORWARDER
# ==========================================
@app.on_message(filters.document & filters.user(WORKER_USERNAME))
async def auto_forward_files(client, message):
    file_name = message.document.file_name
    if not file_name: return

    print(f"[🎯 MATCH] Saw file from Worker: {file_name}")

    if not (file_name.lower().endswith(".mp4") or file_name.lower().endswith(".mkv")):
        return

    for key, is_on in FORWARD_SETTINGS.items():
        target_id = CHANNELS.get(key)
        if is_on and target_id:
            try:
                await message.forward(target_id)
                await asyncio.sleep(1.0)
            except Exception as e:
                print(f"❌ Forward {key} Failed: {e}")

# ==========================================
# 🎛️ COMMANDS
# ==========================================
@app.on_message(filters.command(["ch1", "ch2", "ch3", "ch4"], prefixes="/"))
async def toggle_channel(client, message):
    cmd = message.command[0].lower()
    try: state = message.command[1].lower()
    except: return await message.reply(f"⚠️ Usage: `/{cmd} on` or `/{cmd} off`")
    if cmd in FORWARD_SETTINGS:
        FORWARD_SETTINGS[cmd] = (state == "on")
        await message.reply(f"✅ **{cmd.upper()} {'Enabled' if state=='on' else 'Disabled'}.**")

@app.on_message(filters.command("settings", prefixes="/"))
async def check_settings(client, message):
    status = "\n".join([f"📢 {k.upper()}: {'✅ ON' if v else '❌ OFF'}" for k, v in FORWARD_SETTINGS.items()])
    await message.reply(f"**⚙️ Forwarding Status:**\n{status}")

@app.on_message(filters.command("post", prefixes="/"))
async def post_info(client, message):
    query = message.text[6:].strip()
    if not query: return await message.reply("⚠️ Usage: `/post Name`")
    img, caption = get_anime_info(query)
    if img:
        for key, is_on in FORWARD_SETTINGS.items():
            target_id = CHANNELS.get(key)
            if is_on and target_id:
                try: await client.send_photo(target_id, photo=img, caption=caption)
                except: pass
        await message.reply("✅ Post sent.")
    else: await message.reply("❌ Anime not found.")

@app.on_message(filters.command("sticker", prefixes="/"))
async def send_sticker_cmd(client, message):
    if not STICKER_ID: return
    for key, is_on in FORWARD_SETTINGS.items():
        target_id = CHANNELS.get(key)
        if is_on and target_id:
            try: await client.send_sticker(target_id, sticker=STICKER_ID)
            except: pass
    await message.reply("✅ Sticker sent.")

async def main():
    await start_web_server()
    print("🔄 Connecting to Telegram...")
    
    try:
        await app.start()
        me = await app.get_me()
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"✅ LOGGED IN SUCCESS: {me.first_name} (@{me.username})")
        print(f"👀 WATCHING TARGET: @{WORKER_USERNAME}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    except Exception as e:
        print(f"❌ LOGIN FAILED: {e}")
        return

    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())
