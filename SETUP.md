# Setup Guide

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

**FFmpeg** is also required (for recording):
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
winget install ffmpeg
```

---

## 2. API Keys

Copy the template and fill it in:
```bash
cp .env.example .env
```

### Anthropic API key (required)
1. Go to https://console.anthropic.com
2. Create an API key under **API Keys**
3. Paste it as `ANTHROPIC_API_KEY=...` in your `.env`

---

## 3. YouTube Upload Credentials

This is a one-time setup. You need a Google Cloud project with YouTube Data API access.

### Step 1 — Create a Google Cloud project
1. Go to https://console.cloud.google.com
2. Click **New Project** (top-left dropdown)
3. Name it anything (e.g. `yt-ai-editor`)

### Step 2 — Enable the YouTube Data API v3
1. In your project, go to **APIs & Services → Library**
2. Search for **YouTube Data API v3**
3. Click **Enable**

### Step 3 — Create OAuth 2.0 credentials
1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth client ID**
3. If prompted, configure the **OAuth consent screen** first:
   - User type: **External**
   - Fill in app name (e.g. `YT AI Editor`) and your email
   - Scopes: click **Add or remove scopes**, add `youtube.upload`
   - Test users: add your YouTube account's Gmail
   - Save and continue
4. Back in **Create OAuth client ID**:
   - Application type: **Desktop app**
   - Name: `YT AI Editor`
   - Click **Create**
5. Click **Download JSON** — save this file as `client_secrets.json` in the project root

### Step 4 — Authorize on first run
The first time you upload, a browser window opens asking you to sign in with your Google account and grant upload permission. After that, the token is cached in `youtube_token.json` and future uploads are fully automatic.

---

## 4. Recording setup

### Linux (X11)
Works out of the box. For Wayland, set `DISPLAY=:0` or use a compatibility layer.

### Webcam
Check your webcam device:
```bash
ls /dev/video*
```
Update `WEBCAM_DEVICE` in `.env` if it's not `/dev/video0`.

### Audio
Find your microphone's pulse name:
```bash
pactl list sources short
```
Update `AUDIO_DEVICE` in `.env` with the device name.

---

## 5. First run

```bash
python main.py setup    # check everything is configured
python main.py pipeline # start the full pipeline
```

Press `Ctrl+Shift+R` while in your game to start recording. Press again when done. The AI takes over from there.

---

## 6. Whisper model size

Edit `src/modules/transcriber.py` to change the model:

| Model | VRAM | Speed | Accuracy |
|---|---|---|---|
| `tiny` | 1 GB | Fastest | Good |
| `base` | 1 GB | Fast | Better |
| `small` | 2 GB | Medium | Great |
| `medium` | 5 GB | Slower | Excellent |
| `large-v3` | 10 GB | Slow | Best |

Default is `base`. Change to `large-v3` if you have a capable GPU and want the best transcription.
