# YT AI Editor

> Play. Stop. Done. — The AI builds and uploads your YouTube video while you grab a coffee.

A local browser app that turns raw gaming footage into a YouTube-ready video: AI highlight detection, caricature avatar, background music, chapter markers, thumbnail, and one-click upload. Runs entirely on your machine. Costs under $0.25 per video.

---

## Quick install

**Windows** — double-click `install_windows.bat`

**macOS** — double-click `install_mac.command`

Both scripts check Python and FFmpeg, create a virtual environment, install all dependencies, and drop a `launch` script. After that, just double-click `launch.bat` (Windows) or `launch_mac.command` (macOS) to open the app.

**Manual / Linux:**

```bash
git clone https://github.com/rickhooghiemstra/yt-ai-editor
cd yt-ai-editor
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
sudo apt install ffmpeg mpv        # mpv is for CLI preview before upload
python app.py
```

---

## The WOW example

**You play 45 minutes of Valorant.**

You double-click the app. Your browser opens at `http://localhost:8080`. You go to the **Record** page and hit the big start button. *"Recording started."* You forget about it and just play.

You get a sick clutch 1v4 at minute 12 — your eyes go wide, jaw drops, you yell "LET'S GO". You die hilariously at minute 28. You ace an eco round at minute 37. You don't note any of this down. The AI knows Valorant — it's specifically watching for clutches, aces, and eco wins — and it finds all three by itself.

You hit stop. The timer reads 44:32. You switch to the **Process** page — the file paths filled in automatically.

You fill in the form (takes 60 seconds):

| Field | You type |
|---|---|
| Game name | `Valorant` |
| Channel name | `RickPlays` |
| Video type | Highlights Reel |
| Audience | Casual |
| Tone | Energetic / Hype |
| Target length | `4` min |
| Thumbnail style | Action |
| Specific moments | *(blank — you trust the AI)* |
| Anything else | `ranked match, Silver II` |

You click **Start Processing**. The progress bars animate. You go make coffee.

| Step | What happens | Time |
|---|---|---|
| **Transcribe** | Your voice → timestamped text via local Whisper. Nothing leaves your machine | ~3 min |
| **Analyze** | Claude Vision studies 90 key frames, scores each moment 1–10 using Valorant-specific knowledge | ~5 min |
| **Script** | Claude writes 8 segments, names each, assigns music moods, writes hook + outro + captions | ~1 min |
| **Avatar** | Webcam processed frame-by-frame — your wide eyes go anime-enormous, jaw drop becomes exaggerated cartoon | ~4 min |
| **Edit** | Clips cut and assembled, caricature avatar in the corner, captions overlaid | ~8 min |
| **Music** | Mood-matched track from the built-in library fades in at 15% volume under your gameplay audio | ~2 min |
| **Thumbnail** | Best gameplay frame + your face in a circle + bold title, 1280×720 YouTube-ready | ~30 sec |
| **Metadata** | 3 title options, SEO description with chapters + hashtags + your social links, 25 tags | ~30 sec |

The **upload preview card** appears. You see:

- **Thumbnail** rendered in your chosen style, with one-click style-switch buttons (Action / Bold / Minimal) to try alternatives
- **Three title cards** — click to select, then edit the text inline before uploading
- **Description** — expandable, fully editable. Chapters, hashtags, and your social links already woven in
- **Tags** — shown as chips
- **Privacy** selector

```
Title 1: "1v4 Clutch in RANKED — Silver Has Never Looked This Clean"  [shock]
Title 2: "How I Almost Threw a Ranked Game (But Didn't)"              [personal]
Title 3: "Silver II Ranked Highlights — Valorant 2026"                [numbers]
```

You click title 1, tweak one word, set privacy to **Unlisted**, click **Upload to YouTube**.

```
Uploaded! https://www.youtube.com/watch?v=xXxXxXxXxX
```

**Total time from pressing stop to video on YouTube: ~25 minutes. Your effort: ~60 seconds.**

The webcam corner shows a cartoon you with three-times-bigger reactions. The description has clickable chapter timestamps, your Twitch link, and a hashtag block. There's mood-matched music from the built-in library under the gameplay. Every clip was scored and selected by AI that knew exactly what to look for in Valorant.

And those three highlight moments just got saved to your clip library. Next Sunday you open the **Clip Library** page, click **Generate Best-Of Video**, and a weekly compilation builds itself.

---

## What you need

### Hardware
- A gaming PC (anything that runs your game)
- A webcam — built-in or USB
- A microphone — headset, desktop, or built-in
- A GPU helps Whisper run faster, but CPU works fine

### Software

| Tool | Purpose | Get it |
|---|---|---|
| Python 3.10+ | Runs everything | python.org |
| FFmpeg | Records screen, webcam, and audio simultaneously | `winget install ffmpeg` / `brew install ffmpeg` / `apt install ffmpeg` |
| pip packages | All AI, video, and face-tracking libraries | `pip install -r requirements.txt` (handled by installer) |

### API keys

| Key | Used for | Get it at |
|---|---|---|
| Anthropic | Claude Vision (frame analysis) + script + metadata | console.anthropic.com |
| Google OAuth2 | Uploading to your YouTube channel | See YouTube setup below |

> Whisper transcription and the caricature avatar both run **entirely on your machine** — no API key, no cost, no data sent anywhere.

---

## App overview

```bash
python app.py        # starts the app, browser opens automatically at localhost:8080
```

The app runs as a local web server — nothing connects to the internet. All processing is local.

### Pages

| Page | What it does |
|---|---|
| **Record** | Big start/stop toggle, live recording timer, Quick Clip mode switch, hotkey info |
| **Process** | File path inputs (auto-filled), interview form, live pipeline progress bars, upload preview card |
| **Clip Library** | Filter highlight bank by game / time window / score, view clips table, generate best-of compilations |
| **Settings** | API keys, recording devices, avatar sliders, Whisper model, social links, YouTube credentials |

### Why browser-based?

Packaging MediaPipe, faster-whisper, and MoviePy into a native `.exe` or `.app` runs into serious issues with ML libraries. A local web server is cleaner: polished responsive UI, runs identically on Windows and macOS, no binary distribution problems. The app never touches the internet.

---

## Full setup (do this once)

### Step 1 — Install

**Windows:** double-click `install_windows.bat`
**macOS:** double-click `install_mac.command`
**Linux / manual:**

```bash
git clone https://github.com/rickhooghiemstra/yt-ai-editor
cd yt-ai-editor
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
sudo apt install ffmpeg mpv
```

### Step 2 — Add your Anthropic API key

Open the app → **Settings** → paste your key in the Anthropic API Key field → **Save Settings**.

Or edit `.env` directly:

```env
ANTHROPIC_API_KEY=sk-ant-...
```

### Step 3 — Configure recording devices

In **Settings**, set:

| Field | What to enter |
|---|---|
| Screen resolution | Match your monitor, e.g. `1920x1080` |
| Webcam device | Linux: `ls /dev/video*` to find yours. Windows: `0`, `1`, etc. |
| Audio device | Linux: `pactl list sources short`. Windows/macOS: `default` usually works |

### Step 4 — Add your social links (optional but recommended)

In **Settings → Channel & social links**, fill in your Twitter, Twitch, Instagram, and TikTok URLs. They're appended to every generated description automatically — you never have to paste them manually.

### Step 5 — Connect your YouTube channel

One-time, takes about 5 minutes:

1. Go to [console.cloud.google.com](https://console.cloud.google.com) → **New Project**
2. **APIs & Services → Library** → search **YouTube Data API v3** → Enable
3. **APIs & Services → Credentials** → **+ Create Credentials → OAuth client ID**
4. Configure consent screen: External, add your Gmail as test user, scope `youtube.upload`
5. Application type: **Desktop app** → Create → **Download JSON**
6. Save the file as `client_secrets.json` in the project root

The first upload opens a browser tab for approval. After that it's fully silent. Full walkthrough is in **Settings → YouTube → setup guide**.

### Step 6 — Calibrate the avatar to your face

Take one selfie — neutral expression, facing the camera, decent lighting — then run:

```bash
python main.py calibrate my_photo.jpg
```

Takes 5 seconds. MediaPipe maps your resting face proportions to `recordings/neutral_baseline.json`. Without this, exaggeration is relative to a generic face model. With it, every reaction is amplified relative to *your* specific neutral — so it looks like you, just louder.

Preview the effect live:

```bash
python main.py avatar-preview                      # side-by-side: original | caricature
python main.py avatar-preview --exaggeration 3.0   # push it further
```

Press Q to close.

### Step 7 — Verify everything

```bash
python main.py setup
```

Green checkmarks for each dependency and key. Any red items include the specific fix.

---

## Daily use

### GUI (recommended — no terminal required)

```bash
python app.py       # or double-click launch.bat / launch_mac.command
```

1. **Record page** — hit Start, play your game, hit Stop
2. **Process page** — paths fill automatically, fill in the form, click Start Processing
3. **Upload card** appears — thumbnail preview, edit the title, review the description, set privacy, click Upload

### CLI — fully automatic

```bash
python main.py pipeline
```

`Ctrl+Shift+R` in-game to start recording. Press again when done. Answer 7 questions in the terminal. Walk away.

### CLI — record now, process later

```bash
python main.py record
# ... play your game ...
python main.py process recordings/raw/20260603_143022/screen.mp4 \
                            recordings/raw/20260603_143022/webcam.mp4 \
                            recordings/raw/20260603_143022/audio.wav
```

### CLI — fast highlights, no transcription

```bash
python main.py quick-clip screen.mp4 webcam.mp4
```

Skips transcription. Two questions. ~5–8 minutes. Good for days you just want something posted fast.

### CLI — use recordings from OBS or any other tool

```bash
python main.py process gameplay.mp4 facecam.mp4 mic_audio.wav
```

---

## Features

### Upload preview card

Before anything goes to YouTube, the Process page shows a full preview of what will be uploaded:

- **Thumbnail image** (320×180 preview) with style-switch buttons — switch between Action, Bold, and Minimal without re-running the pipeline
- **3 AI-generated titles** as clickable cards — pick one, then edit the text inline
- **Full description** in an expandable textarea — chapters, hashtags, and your social links already woven in, freely editable before upload
- **Tags panel** showing all generated tags as chips
- **Privacy selector** — Private / Unlisted / Public
- Upload button only activates on this card — there's no way to accidentally upload before you've reviewed everything

---

### Thumbnail styles

Pick a style per video from the Process form. Each uses the same best gameplay frame but with a different layout:

| Style | Look |
|---|---|
| **Action** (default) | Gameplay frame darkened + title in a coloured label pill + face circle top-right + left accent bar |
| **Bold** | Solid colour band fills the bottom quarter + large title inside the band + thin accent line at top |
| **Minimal** | Dark vignette around the frame + large centred title text + thin accent line at the bottom |

Tone sets the colour scheme — energetic = red/yellow, chill = blue/teal, funny = yellow/orange, dramatic = purple. You can switch styles after processing using the quick-swap buttons on the thumbnail preview.

---

### Caricature avatar

Your webcam corner in the final video isn't your raw face — it's a cartoon version of you where every expression is amplified.

| Your real expression | What the avatar shows |
|---|---|
| Slight smile | Wide grin |
| Raised eyebrow | Dramatic single-brow lift |
| Eyes going wide | Anime-large eyes |
| Mouth dropping open | Exaggerated jaw drop |
| Full surprise | Shock lines radiate from the frame |
| Panic / "oh no" | Blue sweat drop in the corner |

MediaPipe maps 468 face landmarks every frame, measures distance from your calibrated neutral, amplifies that delta by 2.5×, warps the actual face image, then runs a cartoon shader (bilateral smooth + edge overlay + saturation boost).

Tune the effect in **Settings → Caricature avatar**, or via CLI flags:

| Flag | Default | Effect |
|---|---|---|
| `--exaggeration` | `2.5` | 1.0 = off, 2.5 = noticeable, 3.5 = extreme |
| `--cartoon` | `0.75` | 0 = natural colour, 1 = full comic style |

The processed webcam is cached per session. To re-render with new settings, delete `recordings/raw/<session_id>/caricature_webcam.mp4` and re-run the pipeline.

---

### Game-specific AI

The analyzer and scriptwriter know about 14 games and what to look for in each:

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
| **Forza Horizon** | Perfect drift chains, Danger Sign jumps, Speed Trap records, Barn Find reveals |
| **World of Warcraft** | Raid boss kills, Mythic+ timed clears, rare item drops, close wipe saves |
| **Guild Wars 2** | WvW siege victories, Fractals boss kills, Legendary item reveals, 1vX fights |
| **Zoo Tycoon / Planet Zoo** | Animal habitat reveals, rare species births, escapes, five-star ratings |
| **Jurassic World Evolution** | Dinosaur breakouts, new species hatches, park chaos moments, dino fights |

Any other game gets a generic profile — Claude falls back to skill displays, close calls, wins, and visible reactions. Game name is fuzzy-matched: "val", "valo", and "valorant" all resolve to the same profile.

---

### Clip library

Every pipeline run automatically saves highlights scored 6/10 or above to `output/clip_library.json` — a permanent searchable bank across all sessions.

Browse in the **Clip Library** page, or via CLI:

```bash
python main.py library                           # summary: game / clips / avg score / date range
python main.py best-of --game valorant --days 7  # compile a video from the library
```

The `best-of` command pulls top clips for a game and time window, assembles a compilation, generates fresh YouTube metadata, and offers to upload — no re-recording, no re-analyzing.

| Flag | Default | What it does |
|---|---|---|
| `--game` | all games | Filter to one game |
| `--days` | `7` | Look back N days (0 = all time) |
| `--min-score` | `7` | Minimum highlight score to include |
| `--channel` | `My Gaming Channel` | Channel name for metadata |

---

### Background music

The library ships with **10 royalty-free tracks** (CC0 — no attribution required) ready to use out of the box:

| Folder | Tracks included |
|---|---|
| `energetic/` | Action Strike, Energizing |
| `chill/` | Be Chillin, Kalimba Relaxation Music |
| `dramatic/` | Epic Boss Battle, Kings Trailer |
| `funny/` | Circus of Freaks, Comic Game Loop Mischief |
| `inspirational/` | Inspiration, Journey of Hope |

All sourced from [FreePD.com](https://freepd.com) — CC0 public domain, commercial use allowed, no credit needed. License details in `music/CREDITS.txt`.

To add more, drop any MP3 or WAV into the matching folder:

```
music/
├── energetic/     ← hype beats, electronic, drums
├── chill/         ← lo-fi, ambient, acoustic
├── dramatic/      ← cinematic, orchestral swells
├── funny/         ← quirky, upbeat, cartoon-style
└── inspirational/ ← piano, uplifting synth
```

Claude assigns a mood to each video segment. The mixer picks a random matching track, loops if shorter than the video, fades in over 2s and out over 3s, mixes at 15% volume. See `music/README.md` for sources and attribution instructions.

---

### YouTube descriptions

Every generated description follows a structured format optimised for watch time and discoverability:

1. **Hook line** — references the best moment, written to earn the click
2. **What's in this video** — 2–3 natural sentences, no keyword stuffing
3. **Chapter timestamps** — clickable in YouTube's progress bar
4. **Call-to-action** — subscribe prompt
5. **Social links** — your Twitter, Twitch, Instagram, TikTok, and any custom footer (set once in Settings)
6. **Hashtags** — 3–5 game-relevant tags for YouTube search

The full description is shown in the upload preview card before anything is sent to YouTube — edit it freely.

---

### Chapter markers

Claude names each video segment during script generation. The pipeline calculates exact output timestamps accounting for speed changes and embeds them in the description.

```
0:00 Intro
0:18 The Clutch
1:02 Easy Rounds
1:45 Almost Threw It
2:30 Final Push
3:15 Outro
```

YouTube renders these as clickable chapters in the progress bar. Added when there are 3+ segments (YouTube's minimum). The first always starts at 0:00.

---

### Video types

One field changed in the form — completely different video from the same raw footage:

| Type | What gets built | Length |
|---|---|---|
| **Highlights Reel** | Top-scored moments only, fast cuts, hype energy | 2–5 min |
| **Full Commentary** | Full session structured around your voice narration | 10–30 min |
| **Tutorial / Guide** | Educational cut: strategy, decisions, tips | 5–15 min |
| **YouTube Short** | 60-second vertical clip, single best moment | ~60 sec |

---

## Output files

```
output/
├── videos/
│   └── valorant_20260603_143022.mp4        ← final video with music
├── thumbnails/
│   └── valorant_20260603_143022_thumb.jpg  ← 1280×720, YouTube-formatted
├── metadata/
│   └── valorant_20260603_143022_meta.json  ← titles, description, tags, chapters
└── clip_library.json                        ← all highlight moments across all sessions

recordings/
└── raw/
    └── 20260603_143022/
        ├── screen.mp4                ← original gameplay
        ├── webcam.mp4                ← original raw webcam
        ├── caricature_webcam.mp4     ← processed avatar (cached; delete to re-render)
        ├── audio.wav                 ← original audio
        ├── transcript.json           ← timestamped transcript (cached)
        └── analysis.json             ← scored moments (cached, used by clip library)

music/
├── energetic/    ← 2 tracks included + add your own
├── chill/        ← 2 tracks included
├── dramatic/     ← 2 tracks included
├── funny/        ← 2 tracks included
├── inspirational/← 2 tracks included
└── CREDITS.txt   ← license info for all included tracks
```

---

## Costs

| Component | Cost |
|---|---|
| Whisper transcription | Free — runs locally |
| Caricature avatar filter | Free — runs locally |
| Background music | Free — 10 CC0 tracks included, add your own |
| Claude Vision frame analysis | ~$0.05–0.20 per session |
| Claude script + metadata | ~$0.02 per video |
| YouTube upload | Free |
| **Total per video** | **< $0.25** |

---

## Whisper model

Default is `base` — fast and accurate for most commentary. Change it in **Settings → Whisper transcription**:

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

```bash
# App
python app.py                                         # launch browser app at localhost:8080

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
python main.py calibrate photo.jpg                   # calibrate to your face (run once)
python main.py avatar-preview                         # live side-by-side preview, Q to quit
python main.py avatar-preview --exaggeration 3.0     # tune exaggeration

# Setup
python main.py setup                                  # check all dependencies and API keys
```

---

## Troubleshooting

**App doesn't open in browser**
Navigate manually to `http://localhost:8080`. If that fails, check if port 8080 is in use: `lsof -i :8080` (Mac/Linux) or `netstat -ano | findstr 8080` (Windows).

**Hotkey doesn't trigger while in-game (Linux)**
On Wayland, `pynput` needs X11 compatibility. Launch your game with `DISPLAY=:0` or enable Xwayland in your compositor settings.

**Webcam not detected (Linux)**
Run `ls /dev/video*` to list devices. Update `WEBCAM_DEVICE` in Settings — it may be `/dev/video2` if you have multiple USB devices.

**Webcam not detected (Windows)**
Use a numeric index: `0` for the first webcam, `1` for the second. Check Device Manager if unsure.

**Audio is silent in recordings (Linux)**
Run `pactl list sources short`, find your microphone's full name, set it as `AUDIO_DEVICE` in Settings.

**Audio is silent in recordings (Windows/macOS)**
Try `AUDIO_DEVICE=default` in Settings. If that fails, list devices with `python -c "import sounddevice; print(sounddevice.query_devices())"` and use the device name or index.

**YouTube upload tries to open a browser on a server**
Run the first upload from your local machine to generate `youtube_token.json`, then copy it to the server. All future uploads are fully silent.

**Caption text doesn't appear on video**
Install ImageMagick: `sudo apt install imagemagick` (Linux) or `brew install imagemagick` (macOS). MoviePy's `TextClip` requires it.

**Avatar filter looks wrong / no face detected**
Use a photo where your face fills at least 20% of the frame, even lighting, no heavy shadows. MediaPipe needs a clear forward-facing view. The filter falls back to cartoon-shader-only during sessions if your face temporarily goes out of frame.

**Avatar reactions are too extreme or too subtle**
Tune in **Settings → Caricature avatar**, or run `python main.py avatar-preview --exaggeration 1.8` (dial back) / `--exaggeration 3.2` (push further). Delete `recordings/raw/<session_id>/caricature_webcam.mp4` and re-run to re-render.

**Best-of returns "no clips found"**
The library only contains sessions already processed by the pipeline. Process at least one session first. If clips exist but aren't showing, source recording files may have been moved — the library filters out clips with missing files automatically.

**Music isn't in the final video**
The 10 included tracks should work immediately. If you've added your own files, check `music/<mood>/` contains at least one MP3 or WAV: `ls music/energetic/`.

**Quick-clip misses obvious moments**
Without a transcript, the AI relies entirely on visual cues. Moments only obvious from audio (voice reactions, game sounds) may be missed. Use the full pipeline for sessions where your commentary carries the highlight.

**FFmpeg not found (Windows)**
Run `winget install ffmpeg` in a terminal, or download from ffmpeg.org and add the `bin` folder to your system PATH. Restart the terminal after.
