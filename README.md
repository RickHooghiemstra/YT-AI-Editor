# YT AI Editor

> Play. Stop. Done. — The AI builds and uploads your YouTube video while you grab a coffee.

---

## The WOW example

**You play 45 minutes of Valorant.**

One terminal is running the pipeline daemon. You press `Ctrl+Shift+R` and start playing. *"Recording started."* You forget about it and just play.

You get a sick clutch 1v4 at minute 12 — your eyes go wide, jaw drops, you yell "LET'S GO". You die hilariously at minute 28. You ace an eco round at minute 37. You don't note any of this down. The AI knows Valorant — it's specifically watching for clutches, aces, and eco wins — and it finds all three by itself.

You press `Ctrl+Shift+R` again when done:

```
Recording stopped — 44m 32s captured
```

The interview starts right there. 90 seconds total:

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

Then you sit back. Here's what runs automatically:

| Step | What happens | Time |
|---|---|---|
| **Transcribe** | Your voice → timestamped text via local Whisper. Runs on your GPU, nothing leaves your machine | ~3 min |
| **Analyze** | Claude Vision studies 90 key frames, scores each moment 1–10 using Valorant-specific knowledge: clutches, aces, eco wins, spike plays | ~5 min |
| **Script** | Claude writes 8 segments, names each one, assigns music moods, writes the hook, outro, captions | ~1 min |
| **Avatar** | Webcam processed frame-by-frame — your wide eyes at the clutch go anime-enormous on screen, the jaw drop gets exaggerated into a cartoon reaction | ~4 min |
| **Edit** | Clips cut and assembled, caricature avatar composited in the corner, captions overlaid | ~8 min |
| **Music** | Mood-matched background track fades in under your audio at 15% volume — hype beat for the clutch, dramatic swell for the eco win | ~2 min |
| **Thumbnail** | Best gameplay frame + your face in a circle + bold title text, 1280×720 YouTube-ready | ~30 sec |
| **Metadata** | 3 title options, SEO description with chapter timestamps embedded, 25 tags — all Claude | ~30 sec |

Terminal shows you the titles and chapters:

```
Generated Titles
  1. "1v4 Clutch in RANKED — Silver Has Never Looked This Clean"  [shock]
  2. "How I Almost Threw a Ranked Game (But Didn't)"              [personal]
  3. "Silver II Ranked Highlights — Valorant 2026"                [numbers]

Chapter Markers
  0:00 Intro
  0:18 The Clutch
  1:12 Easy Rounds
  2:05 Almost Threw It
  3:10 Outro
```

The video opens in your media player. You watch it. Looks good.

```
? How does it look?
  ❯ Looks good — proceed with upload

Upload privacy: Unlisted

Uploading to YouTube ████████████████ 100%  (247 MB — 2 min 14 sec)
Thumbnail set.

Uploaded! https://www.youtube.com/watch?v=xXxXxXxXxX
```

**Total time from pressing stop to video on YouTube: ~25 minutes. Your effort: 90 seconds.**

The webcam corner shows a cartoon you with three-times-bigger reactions. The description has clickable chapter timestamps. There's music under the gameplay that automatically fades in and out per segment. Every clip was scored and selected by AI that knew exactly what to look for in Valorant.

And those three highlight moments — the clutch, the eco win, the funny death — just got saved to your clip library. Next Sunday you run `ytai best-of` and a weekly compilation builds itself.

---

## What you need

### Hardware
- A gaming PC (anything that runs your game)
- A webcam — built-in or USB
- A microphone — headset, desktop, or built-in
- A GPU helps Whisper run faster, but CPU works fine

### Software

| Tool | Purpose | Install |
|---|---|---|
| Python 3.10+ | Runs everything | python.org |
| FFmpeg | Records screen, webcam, and audio simultaneously | `sudo apt install ffmpeg` |
| pip packages | All AI, video, and face-tracking libraries | `pip install -r requirements.txt` |

### API keys

| Key | Used for | Get it at |
|---|---|---|
| Anthropic | Claude Vision (frame analysis) + script + metadata generation | console.anthropic.com |
| Google OAuth2 | Uploading to your YouTube channel | See setup step 3 below |

> Whisper transcription and the caricature avatar both run **entirely on your machine** — no API key, no cost, no data sent anywhere.

---

## Setup (do this once)

### Step 1 — Install dependencies

```bash
git clone https://github.com/rickhooghiemstra/yt-ai-editor
cd yt-ai-editor
pip install -r requirements.txt
sudo apt install ffmpeg mpv        # mpv is for video preview before upload
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

The first upload opens a browser tab for you to approve access. After that it's fully silent.

### Step 4 — Calibrate the avatar to your face

Take one selfie — neutral expression, facing the camera, decent lighting:

```bash
python main.py calibrate my_photo.jpg
```

Takes 5 seconds. MediaPipe maps your resting face proportions and saves them to `recordings/neutral_baseline.json`. Without this, exaggeration is based on a generic face and may look off. With it, the avatar reacts relative to *your* specific neutral — so it looks like you, just louder.

Preview the effect before your first session:

```bash
python main.py avatar-preview                         # side-by-side: original | caricature
python main.py avatar-preview --exaggeration 3.0      # push it further
```

Press Q to close.

### Step 5 — Verify everything

```bash
python main.py setup
```

Green checkmarks for each dependency and key. Any red items include the specific fix.

---

## App (browser-based GUI)

In addition to the CLI, YT AI Editor ships as a local browser app. No installation beyond the steps above — just run it:

```bash
python app.py
```

Your default browser opens automatically at `http://localhost:8080`. The app uses the same dark gaming aesthetic as the rest of the project.

### Pages

| Page | What it does |
|---|---|
| **Record** | Big start/stop toggle, live recording timer, Quick Clip mode switch, hotkey reminder |
| **Process** | File path inputs (auto-filled from last recording), full interview form, live pipeline progress bars, title picker, YouTube privacy selector, upload button |
| **Clip Library** | Filter your highlight bank by game / time window / score, view clips table, generate best-of compilations without touching the terminal |
| **Settings** | API keys, recording devices, avatar sliders, Whisper model selector, YouTube credentials status |

### Windows — quick start

Double-click **`install_windows.bat`** — it checks Python and FFmpeg, creates a virtual environment, installs all dependencies, and creates `launch.bat`. After that, double-click `launch.bat` to start the app.

### macOS — quick start

Double-click **`install_mac.command`** — same as above, creates `launch_mac.command`. Grant Screen Recording, Camera, and Microphone permissions in System Settings → Privacy when prompted.

### Why browser-based?

Packaging MediaPipe, faster-whisper, and MoviePy into a native `.exe` or `.app` via PyInstaller hits serious complexity with ML libraries. A local web server is cleaner: you get a polished responsive UI, it runs identically on Windows and macOS, and there are no binary distribution problems. The app never connects to the internet — everything runs locally on `localhost:8080`.

---

## Daily use

### Option A — Fully automatic (recommended)

```bash
python main.py pipeline
```

Press `Ctrl+Shift+R` in-game to start recording. Press again when done. Answer 7 questions. Walk away — the video is processed and uploaded while you do something else.

### Option B — Record now, process later

```bash
python main.py record
```

Hotkey daemon only — `Ctrl+Shift+R` to start/stop, `Ctrl+C` to exit. Process whenever you're ready:

```bash
python main.py process recordings/raw/20260602_143022/screen.mp4 \
                            recordings/raw/20260602_143022/webcam.mp4 \
                            recordings/raw/20260602_143022/audio.wav
```

### Option C — Fast highlights, no transcription

```bash
python main.py quick-clip screen.mp4 webcam.mp4
```

Skips transcription entirely. Two questions (game + tone). ~5–8 minutes total. Claude Vision scans more frames per minute to compensate, picks the top moments visually, assembles a 3-minute reel, and offers to upload. Good for days you just want something posted fast.

### Option D — Use your own recordings

Already recording with OBS or another tool? Just point the pipeline at your files:

```bash
python main.py process gameplay.mp4 facecam.mp4 mic_audio.wav
```

### Option E — GUI app (no terminal required)

```bash
python app.py
```

Browser opens at `http://localhost:8080`. Use the Record page to start/stop via the on-screen button, then switch to Process, fill in the form, and click Start. All options from options A–D are accessible through the UI — no terminal knowledge needed. Paths auto-fill from your last recording session.

---

## Features

### Caricature avatar

Your webcam corner in the final video isn't your raw face — it's a cartoon version of you where every expression is amplified.

| Your real expression | What the avatar shows |
|---|---|
| Slight smile | Wide grin |
| Raised eyebrow | Dramatic single-brow lift |
| Eyes going wide | Anime-large eyes |
| Mouth dropping open | Exaggerated jaw drop |
| Full surprise | Shock lines radiate from the frame center |
| Panic / "oh no" | Blue sweat drop in the corner |

MediaPipe maps 468 face landmarks every frame, measures how far each feature is from your calibrated neutral, amplifies that delta by 2.5×, warps the actual face image, then runs a cartoon shader (bilateral smooth + edge overlay + saturation boost).

**Tuning:**

| Flag | Default | Effect |
|---|---|---|
| `--exaggeration` | `2.5` | 1.0 = off, 2.5 = noticeable, 3.5 = extreme |
| `--cartoon` | `0.75` | 0 = natural colour, 1 = full comic style |

The processed webcam is cached per session. To re-render with new settings, delete `recordings/raw/<session_id>/caricature_webcam.mp4` and re-run the pipeline.

---

### Game-specific AI

The analyzer and scriptwriter know about 9 games and what to look for in each:

| Game | What Claude specifically watches for |
|---|---|
| **Valorant** | Aces, clutches, spike defuses, eco round wins, operator plays |
| **CS2** | Aces, AWP one-taps, bomb plays, pistol round wins |
| **Minecraft** | Deaths (especially ironic), build reveals, boss fights, speedrun milestones |
| **Fortnite** | Victory Royales, box fight wins, creative edits, building outplays |
| **League of Legends** | Pentakills, Baron/Dragon steals, 1v5 outplays, teamfight wins |
| **Apex Legends** | Squad wipes, banner retrieves, third-party survivals, movement tech |
| **Call of Duty** | Nukes, Warzone wins, killstreaks, long-range snipes |
| **Overwatch** | Team wipe ults, clutch rezzes, environmental kills |
| **Rocket League** | Aerials, ceiling shots, flip resets, impossible saves |

Any other game gets a generic profile — Claude falls back to looking for skill displays, close calls, wins, and visible reactions. It still works well.

The game name is fuzzy-matched, so "val", "valo", and "valorant" all resolve to the same profile.

---

### Clip library

Every pipeline run automatically saves every highlight scored 6/10 or above to `output/clip_library.json`. This builds into a permanent searchable bank of your best moments across all sessions.

```bash
python main.py library                           # summary table: game / clips / avg score / date
python main.py best-of --game valorant --days 7  # compile a video from the library
```

The `best-of` command pulls your top-scored clips for the specified game and time window, assembles a compilation, generates fresh YouTube metadata for the compilation format ("Valorant Best Moments — Week of June 2"), and offers to upload. No re-recording, no re-analyzing.

| Flag | Default | What it does |
|---|---|---|
| `--game` | all games | Filter to one game |
| `--days` | `7` | Look back N days (0 = all time) |
| `--min-score` | `7` | Minimum highlight score to include |
| `--channel` | `My Gaming Channel` | Channel name for metadata |

```bash
python main.py best-of                              # all games, last 7 days
python main.py best-of --game "CS2" --days 30       # CS2, last month
python main.py best-of --days 0 --min-score 9       # all time, 9–10/10 moments only
```

---

### Background music

Drop royalty-free MP3 or WAV files into the mood subfolder that matches your content:

```
music/
├── energetic/     ← hype beats, electronic, drums
├── chill/         ← lo-fi, ambient, acoustic
├── dramatic/      ← cinematic, orchestral swells
├── funny/         ← quirky, upbeat, cartoon-style
└── inspirational/ ← piano, uplifting synth
```

Claude assigns a music mood to each video segment during script generation. The mixer picks a random matching track, loops it if shorter than the video, fades in over 2 seconds and out over 3, and mixes it at 15% volume under your gameplay audio.

If the `music/` folder is empty, this step is silently skipped — no error, no music.

**Where to get free tracks:** YouTube Audio Library, Incompetech (Kevin MacLeod — CC BY 4.0), Pixabay Music, FreeMusicArchive. See `music/README.md` for attribution instructions.

---

### Chapter markers

Every video automatically gets YouTube chapter timestamps embedded in its description. Claude names each segment during script generation. The pipeline calculates exact output timestamps accounting for speed changes.

```
0:00 Intro
0:18 The Clutch
1:02 Easy Rounds
1:45 Almost Threw It
2:30 Final Push
3:15 Outro
```

YouTube renders these as clickable chapters in the video progress bar. Chapters are only added when there are 3 or more segments (YouTube's minimum) and the first always starts at 0:00.

---

### Video types

One interview question changed — completely different video from the same raw footage:

| Type | What gets built | Length |
|---|---|---|
| **Highlights Reel** | Top-scored moments only, fast cuts, hype energy | 2–5 min |
| **Full Commentary** | Full session structured around your voice narration | 10–30 min |
| **Tutorial / Guide** | Educational cut: strategy, decisions, tips | 5–15 min |
| **YouTube Short** | 60-second vertical clip, single best moment | ~60 sec |

---

### Preview before upload

After rendering, your video opens in a media player automatically. You watch it before anything goes to YouTube:

```
? How does it look?
  ❯ Looks good — proceed with upload
    Looks good — save locally, skip upload for now
    Something is wrong — abort
```

Player used: `mpv` → `vlc` → `xdg-open` on Linux, `open` on macOS. Install mpv: `sudo apt install mpv`.

---

## Output files

```
output/
├── videos/
│   └── valorant_20260602_143022.mp4        ← final video with music
├── thumbnails/
│   └── valorant_20260602_143022_thumb.jpg  ← 1280×720, YouTube-formatted
├── metadata/
│   └── valorant_20260602_143022_meta.json  ← all 3 titles, description, tags, chapters
└── clip_library.json                        ← all highlight moments across all sessions

recordings/
└── raw/
    └── 20260602_143022/
        ├── screen.mp4                ← original gameplay
        ├── webcam.mp4                ← original raw webcam
        ├── caricature_webcam.mp4     ← processed avatar (cached, re-render to change settings)
        ├── audio.wav                 ← original audio
        ├── transcript.json           ← timestamped transcript (cached)
        └── analysis.json             ← scored moments (cached, used by clip library)
```

---

## Costs

| Component | Cost |
|---|---|
| Whisper transcription | Free — runs locally |
| Caricature avatar filter | Free — runs locally |
| Background music | Free — your own files |
| Claude Vision frame analysis | ~$0.05–0.20 per session |
| Claude script + metadata | ~$0.02 per video |
| YouTube upload | Free |
| **Total per video** | **< $0.25** |

---

## Whisper model quality

Default is `base` — fast and accurate for most commentary. To change it, edit `src/modules/transcriber.py` and find `model_size="base"`:

| Model | Accuracy | GPU RAM needed | CPU speed |
|---|---|---|---|
| `tiny` | Good | 1 GB | Fast |
| `base` | Better | 1 GB | Fast |
| `small` | Great | 2 GB | Medium |
| `medium` | Excellent | 5 GB | Slow |
| `large-v3` | Best | 10 GB | Very slow |

The model downloads automatically on first use.

---

## CLI reference

```bash
# Main flows
python main.py pipeline                               # record + full pipeline + upload
python main.py record                                 # hotkey daemon only, no auto-process
python main.py process screen.mp4 cam.mp4 audio.wav  # run pipeline on existing files
python main.py quick-clip screen.mp4 webcam.mp4      # fast highlights, no transcription

# Clip library
python main.py best-of                                # best-of compilation, all games, last 7 days
python main.py best-of --game valorant --days 30      # filter by game and time window
python main.py library                                # show clip library summary table

# Avatar
python main.py calibrate photo.jpg                   # calibrate avatar to your face (run once)
python main.py avatar-preview                         # live side-by-side preview, press Q to quit
python main.py avatar-preview --exaggeration 3.0     # tune before recording

# Setup
python main.py setup                                  # check dependencies and API keys
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

**Avatar filter looks wrong / no face detected during calibration**
Use a photo where your face fills at least 20% of the frame, with even lighting and no heavy shadows. MediaPipe needs a clear forward-facing view. The filter falls back to cartoon-shader-only during live sessions if your face goes out of frame temporarily.

**Avatar reactions are too extreme or too subtle**
Run `python main.py avatar-preview --exaggeration 1.8` to dial back, or `--exaggeration 3.2` to push further. Then delete `recordings/raw/<session_id>/caricature_webcam.mp4` and re-run the pipeline to re-render with the new setting.

**Best-of returns "no clips found"**
The library only contains sessions already processed by the pipeline — record and process at least one session first. If clips exist but aren't showing up, the source recording files may have been moved or deleted; the library filters out clips with missing source files automatically.

**Music isn't in the final video**
Check that `music/<mood>/` contains at least one MP3 or WAV file: `ls music/energetic/`. The pipeline skips music silently if the folder is empty. See `music/README.md` for recommended free sources.

**Quick-clip misses obvious moments**
Without a transcript, the AI relies entirely on visual cues. Moments that are only obvious from audio (voice reactions, game sound effects) may be missed. Use the full pipeline for sessions where your commentary carries the highlight.
