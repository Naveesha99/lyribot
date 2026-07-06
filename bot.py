"""
Telegram Lyrics Bot
--------------------
Send this bot an audio file (song) or a voice-recorded clip of a song,
and it will:
  1. Identify the track using the AudD.io audio-recognition API
  2. Fetch the lyrics using the lyrics.ovh API
  3. Reply with the lyrics (split into chunks if long)

Setup:
  1. pip install -r requirements.txt
  2. Copy .env.example to .env and fill in your keys
  3. python bot.py
"""

import os
import asyncio
import logging
import tempfile
import requests
from dotenv import load_dotenv

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AUDD_API_TOKEN = os.getenv("AUDD_API_TOKEN")  # get one free at https://audd.io

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_MSG_LIMIT = 4096


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def recognize_song(file_path: str) -> dict | None:
    """
    Send the audio file to AudD.io for recognition.
    Returns a dict with 'title' and 'artist' if found, else None.
    """
    url = "https://api.audd.io/"
    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {
            "api_token": AUDD_API_TOKEN,
            "return": "apple_music,spotify",
        }
        response = requests.post(url, data=data, files=files, timeout=30)

    response.raise_for_status()
    result = response.json()

    if result.get("status") == "success" and result.get("result"):
        song = result["result"]
        return {"title": song.get("title"), "artist": song.get("artist")}

    return None


def fetch_lyrics(artist: str, title: str) -> str | None:
    """
    Fetch lyrics from the free lyrics.ovh API.
    Returns lyrics text, or None if not found.
    """
    url = f"https://api.lyrics.ovh/v1/{requests.utils.quote(artist)}/{requests.utils.quote(title)}"
    try:
        response = requests.get(url, timeout=15)
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    data = response.json()
    lyrics = data.get("lyrics")
    if lyrics:
        return lyrics.strip()
    return None


def chunk_text(text: str, limit: int = TELEGRAM_MSG_LIMIT):
    """Split long text into Telegram-safe chunks without cutting mid-line."""
    lines = text.split("\n")
    chunks = []
    current = ""

    for line in lines:
        # +1 accounts for the newline we'll add back
        if len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line

    if current:
        chunks.append(current)

    return chunks


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Send me an audio file (or a short recording) of a song, "
        "and I'll try to identify it and find the lyrics for you!"
    )


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    # Works for audio files, voice notes, or documents (e.g. mp3 sent as file)
    audio_obj = message.audio or message.voice or message.document
    if audio_obj is None:
        await message.reply_text("Please send an audio file, voice note, or song file.")
        return

    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    status_msg = await message.reply_text("🎧 Listening... identifying the song.")

    tg_file = await context.bot.get_file(audio_obj.file_id)

    tmp_file = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
    tmp_file.close()
    try:
        await tg_file.download_to_drive(tmp_file.name)

        try:
            song = recognize_song(tmp_file.name)
        except requests.RequestException as e:
            logger.exception("Recognition API error")
            await status_msg.edit_text(f"⚠️ Error contacting recognition service: {e}")
            return
    finally:
        os.unlink(tmp_file.name)

    if not song or not song.get("title"):
        await status_msg.edit_text(
            "❌ Couldn't identify that song. Try a clearer clip of the actual song audio."
        )
        return

    title = song["title"]
    artist = song.get("artist") or ""

    await status_msg.edit_text(f"✅ Identified: {title} — {artist}\n🔍 Fetching lyrics...")

    lyrics = fetch_lyrics(artist, title)

    if not lyrics:
        await status_msg.edit_text(
            f"Found the song ({title} — {artist}), but no lyrics were available "
            f"from the lyrics database."
        )
        return

    header = f"🎶 *{title}* — {artist}\n\n"
    full_text = header + lyrics

    chunks = chunk_text(full_text)
    await status_msg.delete()
    for chunk in chunks:
        await message.reply_text(chunk)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me an audio file of a song (not just text) and I'll find the lyrics for you 🎵"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set. Check your .env file.")
    if not AUDD_API_TOKEN:
        raise RuntimeError("AUDD_API_TOKEN is not set. Check your .env file.")

    asyncio.set_event_loop(asyncio.new_event_loop())
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.AUDIO | filters.VOICE | filters.Document.AUDIO, handle_audio
    ))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
