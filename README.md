# Telegram Lyrics Bot

Send this bot a song audio file (or a short voice recording of a song) and it will
identify the track and reply with its lyrics.

## How it works

1. **Recognition** — the audio is sent to [AudD.io](https://audd.io), an audio
   fingerprinting API, which returns the song title and artist.
2. **Lyrics lookup** — the title/artist are used to query
   [lyrics.ovh](https://lyricsovh.docs.apiary.io/), a free public lyrics API.
3. **Delivery** — the bot replies with the lyrics, automatically split into
   multiple messages if they exceed Telegram's 4096-character limit.

## Setup

1. **Create a Telegram bot**
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Run `/newbot` and follow the prompts
   - Copy the token it gives you

2. **Get an AudD.io API token**
   - Sign up at https://audd.io — there's a free tier suitable for testing
   - Copy your API token

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # then edit .env and paste in your two tokens
   ```

5. **Run the bot**
   ```bash
   python bot.py
   ```

6. Open Telegram, find your bot, and send it an audio file (mp3, voice note,
   or a song file sent as a document) — it'll reply with the lyrics.

## Notes & things to consider

- **Telegram audio types**: the bot listens for `audio`, `voice`, and audio
  documents (e.g. an mp3 sent as a "file"). Voice notes recorded near a
  speaker also work reasonably well for recognition.
- **Recognition accuracy**: AudD works best with at least 5–10 seconds of
  clear, non-distorted audio matching a released track.
- **Lyrics availability**: lyrics.ovh doesn't have every song. For broader
  coverage in production, consider swapping in the Genius API (requires
  fetching lyrics pages separately, as Genius's API only returns metadata/URLs)
  or Musixmatch's API (needs a paid tier for full lyrics text).
- **Copyright**: lyrics are copyrighted content. This bot pulls them live
  from a third-party lyrics service rather than storing/hardcoding any —
  check that service's terms of use if you plan to run this at scale or
  commercially.
- **Rate limits**: both AudD's free tier and lyrics.ovh have rate limits;
  add caching (e.g. a local dict or Redis keyed by title+artist) if you
  expect repeat requests for the same songs.

## Extending it

- Add a `/help` command explaining usage.
- Cache lyrics results in a local SQLite DB to reduce repeated API calls.
- Add inline buttons to let users pick between multiple recognition matches.
- Deploy with a webhook (instead of polling) on a service like Render,
  Railway, or a small VPS for production use.
