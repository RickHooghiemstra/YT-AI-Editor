# YT AI Editor

> Play. Stop. Done. — The AI builds and uploads your YouTube video while you grab a coffee.

---

## The WOW example

Here's exactly what happens when you use this tool:

**You play 45 minutes of Valorant.**

At your desk you have two terminals open — one running the pipeline daemon, one free. You press `Ctrl+Shift+R` and start playing. A small message appears: *"Recording started."* You forget about it and just play.

You get a sick clutch 1v4 round at minute 12. You die hilariously at minute 28. You ace an eco round at minute 37. You have no idea the AI will find all three moments by itself.

You press `Ctrl+Shift+R` again when you're done. The terminal prints:

```
Recording stopped — 44m 32s captured
```

Then the interview starts right there in the terminal:

```
What game were you playing?           → Valorant
Your channel name?                    → RickPlays
What type of video?                   → Highlights Reel  (2–5 min)
Target audience?                      → Casual
Tone / vibe?                          → Energetic / Hype
Target length in minutes?             → 4
Any specific moments to include?      → (blank — you trust the AI)
Anything else the AI should know?     → ranked match, Silver II
```

You answer in about 90 seconds. Then you sit back.

The AI does this — automatically, in order:

| Step | What happens | Time |
|---|---|---|
| Transcribe | Your voice gets converted to timestamped text by local Whisper | ~3 min |
| Analyze | Claude Vision studies 90 key frames, scores each moment 1–10 | ~5 min |
| Script | Claude writes a video structure: 8 segments, commentary cues, hook, outro | ~1 min |
| Edit | MoviePy cuts the footage, composites your webcam in the corner, adds captions | ~8 min |
| Thumbnail | Best gameplay frame + your face + bold title text, ready for YouTube | ~30 sec |
| Metadata | 3 title options, SEO description, 25 tags — all written by Claude | ~30 sec |

Terminal shows you the generated titles:

```
Generated Titles
  1. "1v4 Clutch in RANKED — Silver Has Never Looked This Clean"  [shock]
  2. "How I Almost Threw a Ranked Game (But Didn't)"              [personal]
  3. "Silver II Ranked Highlights — Valorant 2026"                [numbers]
```

You pick title 1. You choose `unlisted` so you can preview before publishing.

```
Uploading to YouTube ████████████████ 100%  (247 MB — 2 min 14 sec)
Thumbnail set.

Uploaded! https://www.youtube.com/watch?v=xXxXxXxXxX
```

**Total time from pressing stop to having a video on YouTube: ~20 minutes. Your effort: 90 seconds of answering questions.**

---

## What you need

### Hardware
- A PC that can run your game (anything modern)
- A webcam (built-in or USB)
- A microphone (headset, desktop, or built-in)
- A GPU helps for Whisper transcription — but CPU works too, just slower

### Software (one-time installs)

| Tool | Purpose | Install |
|---|---|---|
| Python 3.10+ | Runs everything | https://python.org |
| FFmpeg | Records your screen, webcam, and audio | `sudo apt install ffmpeg` / `brew install ffmpeg` |
| pip packages | All AI and video libraries | `pip install -r requirements.txt` |

### API keys (two, both free tiers available)

| Key | Used for | Get it at |
|---|---|---|
| Anthropic API | Claude Vision (frame analysis) + script + metadata | https://console.anthropic.com |
| Google OAuth2 | Uploading to your YouTube channel | See step 3 below |

> The Whisper transcription runs **locally on your machine** — no API key, no cost, no audio leaves your computer.

---

## Setup (do this once)

### Step 1 — Install Python dependencies

```bash
git clone https://github.com/rickhooghiemstra/yt-ai-editor
cd yt-ai-editor
pip install -r requirements.txt
```

### Step 2 — Configure your keys

```bash
cp .env.example .env
```

Open `.env` and fill in:

```env
ANTHROPIC_API_KEY=sk-ant-...          # from console.anthropic.com
SCREEN_RESOLUTION=1920x1080           # match your monitor
WEBCAM_DEVICE=/dev/video0             # run: ls /dev/video* to check
AUDIO_DEVICE=default                  # run: pactl list sources short to check
```

### Step 3 — Connect your YouTube channel

This is a one-time 5-minute process:

1. Go to [console.cloud.google.com](https://console.cloud.google.com) → **New Project**
2. Go to **APIs & Services → Library** → search **YouTube Data API v3** → Enable
3. Go to **APIs & Services → Credentials** → **+ Create Credentials → OAuth client ID**
4. Configure consent screen if prompted: External, add your Gmail as a test user, scope: `youtube.upload`
5. Application type: **Desktop app** → Create → **Download JSON**
6. Save the downloaded file as `client_secrets.json` in the project root

The first time you upload, a browser tab opens asking you to approve access. After that it's fully silent and automatic.

### Step 4 — Verify everything works

```bash
python main.py setup
```

You'll see green checkmarks or specific instructions if anything is missing.

---

## Daily use

### Option A — Fully automatic (recommended)

```bash
python main.py pipeline
```

Press `Ctrl+Shift+R` to start recording. Play your game. Press `Ctrl+Shift+R` again when done. Answer 7 questions. Walk away.

### Option B — Record now, process later

Start recording:
```bash
python main.py record
```
Press `Ctrl+Shift+R` in-game to toggle. Stop the daemon with `Ctrl+C` when done.

Process the files later:
```bash
python main.py process recordings/raw/20260602_143022/screen.mp4 \
                            recordings/raw/20260602_143022/webcam.mp4 \
                            recordings/raw/20260602_143022/audio.wav
```

### Option C — Use your own recordings (OBS, etc.)

If you already record with OBS or any other tool, just point the pipeline at your files:

```bash
python main.py process gameplay.mp4 facecam.mp4 mic_audio.wav
```

---

## Video types

Answer one question differently and you get a completely different video from the same footage:

| Type | What the AI builds | Length |
|---|---|---|
| **Highlights Reel** | Best moments only, fast cuts, hype energy | 2–5 min |
| **Full Commentary** | Full session with your voice as narration structure | 10–30 min |
| **Tutorial / Guide** | Educational cut: explains decisions, tips-focused | 5–15 min |
| **YouTube Short** | 60-second vertical clip, top moment only | ~60 sec |

---

## Output files

After each run you'll find:

```
output/
├── videos/     valorant_20260602_143022.mp4       ← the final video
├── thumbnails/ valorant_20260602_143022_thumb.jpg  ← ready-to-use thumbnail
└── metadata/   valorant_20260602_143022_meta.json  ← titles, description, tags
```

The metadata JSON is useful if you want to review or tweak the YouTube copy before it goes live.

---

## Tuning Whisper quality

The default model (`base`) is fast and accurate enough for most commentary. If you want better transcription (especially for fast speech or background noise):

Edit `src/modules/transcriber.py`, find `model_size="base"` and change it:

| Model | Accuracy | GPU RAM needed | Speed on CPU |
|---|---|---|---|
| `tiny` | Good | 1 GB | Fast |
| `base` | Better | 1 GB | Fast |
| `small` | Great | 2 GB | Medium |
| `medium` | Excellent | 5 GB | Slow |
| `large-v3` | Best | 10 GB | Very slow |

The model downloads automatically on first use.

---

## How the AI makes editing decisions

When Claude analyzes your footage it looks at:

- **Energy spikes** — moments where the action clearly escalates
- **Win/loss moments** — kills, deaths, objectives, clutches
- **Rare events** — aces, comebacks, funny fails, achievements
- **Your voice** — the transcript tells it when *you* react with excitement

Each frame gets a score from 1–10. The script only uses moments with the highest scores, trimmed to fit your target length. Nothing is random — every cut is justified by what the AI found in the footage.

---

## Costs

| Component | Cost |
|---|---|
| Whisper transcription | Free (runs locally) |
| Claude Vision analysis | ~$0.05–0.20 per session (depends on session length) |
| Claude script + metadata | ~$0.02 per video |
| YouTube upload | Free |
| **Total per video** | **< $0.25** |

---

## Troubleshooting

**Hotkey doesn't work while in-game**
On Linux with Wayland, `pynput` needs X11 compatibility mode. Run the game with `DISPLAY=:0` or enable Xwayland.

**Webcam not found**
Run `ls /dev/video*` to list devices. Update `WEBCAM_DEVICE` in `.env`.

**Audio is silent in the recording**
Run `pactl list sources short`, find your microphone's name, and set `AUDIO_DEVICE` in `.env`.

**YouTube upload opens a browser on a remote server**
Run the first upload locally once to generate `youtube_token.json`, then copy that file to your server. All future uploads will be silent.

**MoviePy caption text doesn't appear**
Install ImageMagick: `sudo apt install imagemagick`. Captions require it; everything else works without it.
