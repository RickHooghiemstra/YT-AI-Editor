# Background Music

Drop royalty-free audio files (MP3 or WAV) into the matching mood subfolder.
The pipeline picks a random track from the folder that matches the segment mood,
fades it in and out, and mixes it under your gameplay audio at low volume.

## Folder → Mood mapping

| Folder | Used when | Works well with |
|---|---|---|
| `energetic/` | Highlights, intense moments, fast cuts | Drums, electronic, hype beats |
| `chill/` | Commentary, slow sections, intros | Lo-fi, ambient, acoustic |
| `dramatic/` | Clutch moments, comeback segments | Cinematic, orchestral swells |
| `funny/` | Fail moments, comedy clips | Quirky, upbeat, cartoon-style |
| `inspirational/` | Tutorial outros, achievement moments | Uplifting, piano, soft synth |

## Where to get royalty-free tracks

- **YouTube Audio Library** — youtube.com/audiolibrary (free, some need attribution in description)
- **Incompetech** — incompetech.com (Kevin MacLeod, CC BY 4.0 — credit in description)
- **FreeMusicArchive** — freemusicarchive.org (mixed licenses, check each track)
- **Pixabay Music** — pixabay.com/music (free for commercial use, no attribution required)
- **ccMixter** — ccmixter.org (Creative Commons, check license per track)

## Attribution

If a track requires attribution, add the credit to your video description.
The pipeline appends the `music/CREDITS.txt` file (if it exists) to every generated description automatically.

Create `music/CREDITS.txt` and add one line per credited track:
```
Music: "Track Name" by Artist Name — license URL
```

## Volume

Music is mixed at 15% of the gameplay audio volume by default — audible but not distracting.
To change this, set `MUSIC_VOLUME=0.20` in your `.env` file (range 0.0–1.0).
