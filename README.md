# YT AI Editor

> Play. Stop. Done. — The AI builds and uploads your YouTube video while you grab a coffee.

---

## The WOW example

Here's exactly what happens when you use this tool:

**You play 45 minutes of Valorant.**

At your desk you have a terminal open running the pipeline daemon. You press `Ctrl+Shift+R` and start playing. *"Recording started."* You forget about it and just play.

You get a sick clutch 1v4 at minute 12 — your eyes go wide, jaw drops, you yell "LET'S GO". You die hilariously at minute 28. You ace an eco round at minute 37. None of that needs to be noted down. The AI finds all of it.

You press `Ctrl+Shift+R` again when done. The terminal prints:

```
Recording stopped — 44m 32s captured
```

The interview starts right there:

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

90 seconds of answering. Then you sit back.

| Step | What happens | Time |
|---|---|---|
| **Transcribe** | Your voice converted to timestamped text by local Whisper — runs on your GPU, nothing leaves your machine | ~3 min |
| **Analyze** | Claude Vision studies 90 key frames from your gameplay, scores each moment 1–10 for entertainment value | ~5 min |
| **Script** | Claude writes a video structure: 8 segments, commentary cues, hook that grabs in 5 seconds, outro | ~1 min |
| **Avatar** | Your webcam recording is processed frame-by-frame — when you went wide-eyed at the clutch, the avatar in the corner goes anime-enormous; the yell becomes an open-jaw cartoon reaction | ~4 min |
| **Edit** | MoviePy cuts the footage, composites your caricature avatar in the corner, adds captions at the right moments | ~8 min |
| **Thumbnail** | Best gameplay frame + your face + bold title text, sized and formatted for YouTube | ~30 sec |
| **Metadata** | 3 title options, SEO-optimised description, 25 tags — all written by Claude | ~30 sec |

Terminal shows you the titles:

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

**Total time from pressing stop to having a video on YouTube: ~20 minutes. Your effort: 90 seconds.**

The webcam corner? Not your raw face — a cartoon version of you with reactions three times bigger than real life. Viewers see the clutch moment twice: in the gameplay, and in your avatar's exploding expression in the corner.

---

## What you need

### Hardware
- A gaming PC (anything that runs your game)
- A webcam — built-in or USB
- A microphone — headset, desktop, or built-in
- A GPU helps Whisper transcribe faster, but CPU works fine

### Software

| Tool | Purpose | Install |
|---|---|---|
| Python 3.10+ | Runs everything | python.org |
| FFmpeg | Records screen, webcam, and audio simultaneously | `sudo apt install ffmpeg` |
| pip packages | All AI, video, and face-tracking libraries | `pip install -r requirements.txt` |

### API keys

| Key | Used for | Get it at |
|---|---|---|
| Anthropic | Claude Vision (frame analysis) + script + metadata | console.anthropic.com |
| Google OAuth2 | Uploading to your YouTube channel | See setup step 3 below |

> Whisper transcription and the caricature avatar both run **entirely on your machine** — no API key, no cost, nothing sent to a server.

---

## Setup (do this once)

### Step 1 — Install dependencies

```bash
git clone https://github.com/rickhooghiemstra/yt-ai-editor
cd yt-ai-editor
pip install -r requirements.txt
sudo apt install ffmpeg
```

### Step 2 — Configure your environment

```bash
cp .env.example .env
```

Open `.env` and fill in:

```env
ANTHROPIC_API_KEY=sk-ant-...     # from console.anthropic.com
SCREEN_RESOLUTION=1920x1080      # match your monitor
WEBCAM_DEVICE=/dev/video0        # run: ls /dev/video* to find yours
AUDIO_DEVICE=default             # run: pactl list sources short to find yours
```

### Step 3 — Connect your YouTube channel

One-time, takes about 5 minutes:

1. Go to [console.cloud.google.com](https://console.cloud.google.com) → **New Project**
2. **APIs & Services → Library** → search **YouTube Data API v3** → Enable
3. **APIs & Services → Credentials** → **+ Create Credentials → OAuth client ID**
4. If prompted to configure consent screen: External, add your Gmail as test user, scope `youtube.upload`
5. Application type: **Desktop app** → Create → **Download JSON**
6. Save the file as `client_secrets.json` in the project root

The first upload opens a browser tab asking you to approve. After that it runs silently forever.

### Step 4 — Calibrate the avatar to your face

Take one selfie — neutral expression, looking at the camera, decent lighting. Then:

```bash
python main.py calibrate my_photo.jpg
```

This takes 5 seconds. MediaPipe maps your neutral face and saves the proportions to `recordings/neutral_baseline.json`. Every expression the avatar shows from that point on is exaggerated *relative to your specific face* — not a generic model.

Before your first session, preview it live:

```bash
python main.py avatar-preview
```

A side-by-side window opens: **Original | Caricature**. Make sure it looks right. Press Q to close. Tune with:

```bash
python main.py avatar-preview --exaggeration 3.0 --cartoon 0.9
```

### Step 5 — Verify everything

```bash
python main.py setup
```

Green checkmarks mean you're good. Any red items include the exact fix.

---

## Daily use

### Option A — Fully automatic (recommended)

```bash
python main.py pipeline
```

Press `Ctrl+Shift+R` to start. Play. Press again when done. Answer 7 questions. Walk away — video is uploaded by the time you're back.

### Option B — Record now, process later

```bash
python main.py record
```

Press `Ctrl+Shift+R` to start and stop. Ctrl+C to exit the daemon. Process whenever you're ready:

```bash
python main.py process recordings/raw/20260602_143022/screen.mp4 \
                            recordings/raw/20260602_143022/webcam.mp4 \
                            recordings/raw/20260602_143022/audio.wav
```

### Option C — Use your own recordings

Already record with OBS or another tool? Just point the pipeline at your files:

```bash
python main.py process gameplay.mp4 facecam.mp4 mic_audio.wav
```

---

## The caricature avatar

Your webcam corner in the final video isn't your raw face — it's a cartoon version of you where every reaction is amplified.

**What it detects and amplifies:**

| Your real expression | What the avatar shows |
|---|---|
| Slight smile | Wide grin |
| Raised eyebrow | Dramatic single-brow lift |
| Eyes going wide | Anime-large eyes |
| Mouth dropping open | Exaggerated jaw drop |
| Full surprise (eyes + brows) | Shock lines radiate from the frame center |
| Panic / "oh no" mouth | Blue sweat drop in the corner |

**How it works:** MediaPipe maps 468 face landmarks every frame. It measures how far each feature is from your neutral baseline (from the calibration photo), then amplifies that delta by 2.5× using a smooth curve — so subtle reactions become dramatic without looking broken. Then a cartoon shader (bilateral smooth + edge overlay + saturation boost) gives the whole thing a comic-book look.

**The calibration matters.** Without it, the system guesses your neutral face from averages and the exaggeration may look off. With it, it knows your face specifically and the effect is clean.

**Tuning:**

| Flag | Default | What it does |
|---|---|---|
| `--exaggeration` | `2.5` | Reaction amplifier. 1.0 = off, 2.5 = noticeable, 3.5 = extreme |
| `--cartoon` | `0.75` | Cartoon shader strength. 0 = natural colour, 1 = full comic style |

The processed webcam is cached per session. To re-render with different settings, delete `recordings/raw/<session_id>/caricature_webcam.mp4` and re-run the pipeline.

---

## Video types

Same raw footage. One question answered differently. Completely different video.

| Type | What gets built | Length |
|---|---|---|
| **Highlights Reel** | Best-scored moments only, fast cuts, hype energy | 2–5 min |
| **Full Commentary** | Full session structured around your voice narration | 10–30 min |
| **Tutorial / Guide** | Educational cut: strategy, decision moments, tips | 5–15 min |
| **YouTube Short** | 60-second vertical clip, single best moment | ~60 sec |

---

## What the AI finds in your footage

The analyzer sends batches of key frames to Claude Vision. For each frame it asks:

- What is happening in the game?
- Is this a highlight moment, and why?
- What is the energy level — calm, medium, intense, or peak?
- Would this engage a *[your chosen audience]* viewer?

Every moment gets a score from 1–10. The script only includes the highest-scoring moments trimmed to your target length. Nothing is random — every cut is justified by what Claude found in the frame combined with what you said out loud (from the transcript) at that timestamp.

---

## Output files

```
output/
├── videos/     valorant_20260602_143022.mp4        ← final video, ready to upload
├── thumbnails/ valorant_20260602_143022_thumb.jpg  ← 1280×720, YouTube-formatted
└── metadata/   valorant_20260602_143022_meta.json  ← all 3 titles, description, tags

recordings/
└── raw/
    └── 20260602_143022/
        ├── screen.mp4            ← original gameplay recording
        ├── webcam.mp4            ← original raw webcam
        ├── caricature_webcam.mp4 ← processed avatar version (cached)
        ├── audio.wav             ← original audio
        └── transcript.json       ← timestamped transcript (cached)
```

---

## Costs

| Component | Cost |
|---|---|
| Whisper transcription | Free — runs locally on your machine |
| Caricature avatar filter | Free — runs locally on your machine |
| Claude Vision (frame analysis) | ~$0.05–0.20 per session |
| Claude script + metadata | ~$0.02 per video |
| YouTube upload | Free |
| **Total per video** | **< $0.25** |

---

## Whisper quality

Default model is `base` — fast and accurate for most commentary. To change it, edit `src/modules/transcriber.py` and find `model_size="base"`:

| Model | Accuracy | GPU RAM | CPU speed |
|---|---|---|---|
| `tiny` | Good | 1 GB | Fast |
| `base` | Better | 1 GB | Fast |
| `small` | Great | 2 GB | Medium |
| `medium` | Excellent | 5 GB | Slow |
| `large-v3` | Best | 10 GB | Very slow |

Downloads automatically on first use.

---

## CLI reference

```
python main.py pipeline                          # record + process + upload, all-in-one
python main.py record                            # hotkey daemon only
python main.py process screen.mp4 cam.mp4 a.wav # process existing files
python main.py calibrate photo.jpg              # calibrate avatar to your face
python main.py avatar-preview                   # live side-by-side webcam preview
python main.py setup                            # check all dependencies and keys
```

---

## Troubleshooting

**Hotkey doesn't trigger while in-game**
On Linux with Wayland, `pynput` needs X11 compatibility. Launch your game with `DISPLAY=:0` or enable Xwayland in your compositor settings.

**Webcam not detected**
Run `ls /dev/video*` to list devices. Update `WEBCAM_DEVICE` in `.env` — it may be `/dev/video2` if you have multiple USB devices.

**Audio is silent in recordings**
Run `pactl list sources short`, find your microphone's full name, and set it as `AUDIO_DEVICE` in `.env`.

**YouTube upload tries to open a browser on a headless server**
Run the first upload from your local machine to generate `youtube_token.json`, then copy that file to the server. All future uploads are silent.

**Caption text doesn't appear on video**
Install ImageMagick: `sudo apt install imagemagick`. MoviePy's `TextClip` requires it. Everything else works without it.

**Avatar filter looks wrong / no face detected**
For calibration: use a photo where your face fills at least 20% of the frame, with even lighting and no heavy shadows — MediaPipe needs a clear forward-facing view. For live sessions: the filter falls back to cartoon-shader-only if your face goes out of frame temporarily, so partial detection is fine.

**Avatar reactions are too extreme or too subtle**
Run `python main.py avatar-preview --exaggeration 1.8` to dial back, or `--exaggeration 3.2` to push further. Once you find the right value, delete the cached `caricature_webcam.mp4` in the session folder and re-run the pipeline to render with the new setting.
