import asyncio
import os
import requests
import threading
from flask import Flask
from pyrogram import Client, filters, idle

# --- RENDER HEALTH CHECK ---
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "Manager Bot is Online", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- CONFIGURATION ---
API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
SESSION_STRING = os.environ.get('SESSION_STRING')
WORKER_USERNAME = os.environ.get('WORKER_USERNAME') # Your uploader bots' username
STICKER_ID = os.environ.get('STICKER_ID')

CHANNELS = {
    "ch1": int(os.environ.get('CHANNEL_1', 0)),
    "ch2": int(os.environ.get('CHANNEL_2', 0)),
    "ch3": int(os.environ.get('CHANNEL_3', 0)),
    "ch4": int(os.environ.get('CHANNEL_4', 0))
}

# 🟢 DEFAULTS: Ch2 & Ch3 ON | Ch1 & Ch4 OFF
FORWARD_SETTINGS = {"ch1": False, "ch2": True, "ch3": True, "ch4": False}

app = Client("manager_userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# --- ANILIST API & FORWARDING LOGIC ---
# (Include your get_anime_info_anilist function here from source: 174-180)

@app.on_message(filters.command(["upload", "fastupload"], prefixes="/"))
async def manager_upload_handler(client, message):
    cmd_text = message.text
    # When you send /upload, the Manager triggers the poster
    if "-post" in cmd_text:
        # 1. Get info from AniList
        # 2. Send Poster to CHANNELS where FORWARD_SETTINGS is True
        pass

@app.on_message(filters.document & filters.user(WORKER_USERNAME))
async def file_watcher(client, message):
    # Watches for files sent by your 3 Uploader Bots
    for key, is_on in FORWARD_SETTINGS.items():
        if is_on and CHANNELS[key] != 0:
            await message.copy(CHANNELS[key])
            await asyncio.sleep(1.5)

async def main():
    # Start Web Server for Render
    threading.Thread(target=run_flask, daemon=True).start()
    
    await app.start()
    print("✅ Manager Bot (Render) Started with Ch2/Ch3 ON by default.")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
