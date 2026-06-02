"""All Claude prompt templates for the video pipeline."""

from __future__ import annotations


ANALYZER_SYSTEM = """\
You are an expert gaming video analyst. You analyze gameplay footage and identify:
- Key moments (kills, deaths, big plays, funny moments, fails, achievements)
- Game state (score, health, resources, objectives)
- Player skill level and style
- Pacing and energy of the session
- Moments with highest entertainment or educational value

Be specific with timestamps. Rate each moment 1-10 for entertainment value.
"""

ANALYZER_FRAMES_PROMPT = """\
Game: {game_name}
Session duration: {duration}

Analyze these key frames from the gameplay session. For each frame, identify:
1. What is happening in the game?
2. Is this a highlight moment? Why?
3. What is the energy level (calm/medium/intense/peak)?
4. Would this engage a {audience} audience?

Return a JSON object with this structure:
{{
  "moments": [
    {{
      "frame_index": 0,
      "timestamp_seconds": 0,
      "description": "...",
      "energy": "calm|medium|intense|peak",
      "highlight_score": 1-10,
      "category": "kill|death|objective|funny|fail|achievement|general",
      "include_in_highlights": true|false
    }}
  ],
  "session_summary": "...",
  "best_clip_timestamps": [start, end],
  "recommended_thumbnail_frame": 0
}}
"""

SCRIPTWRITER_SYSTEM = """\
You are a professional YouTube video editor and scriptwriter specializing in gaming content.
You create engaging video structures that maximize watch time and viewer retention.
You understand pacing, storytelling, and what makes gaming content go viral.
"""

SCRIPTWRITER_PROMPT = """\
Create a complete video production plan for this gaming session:

Game: {game_name}
Player: {channel_name}
Video type: {video_type}
Tone: {tone}
Target length: {target_length_minutes} minutes
Target audience: {audience}
Special moments to include: {special_moments}

Session analysis:
{analysis_summary}

Transcript excerpt:
{transcript_excerpt}

Generate a video structure with:
1. Intro hook (first 15 seconds - must grab attention)
2. Main segments with timestamps from the raw footage
3. Commentary suggestions for each segment
4. Outro with call-to-action
5. Music mood for each segment

Return as JSON:
{{
  "title_options": ["...", "...", "..."],
  "hook_script": "...",
  "segments": [
    {{
      "name": "...",
      "source_start": 0.0,
      "source_end": 0.0,
      "speed_multiplier": 1.0,
      "commentary": "...",
      "music_mood": "energetic|chill|dramatic|funny|inspirational",
      "include_webcam": true|false,
      "caption": "..."
    }}
  ],
  "outro_script": "...",
  "estimated_duration_seconds": 0
}}
"""

METADATA_SYSTEM = """\
You are a YouTube SEO and growth expert. You write titles, descriptions, and tags
that maximize click-through rate, watch time, and discoverability.
You know what titles go viral in gaming niches and how to write descriptions
that rank in YouTube search.
"""

METADATA_PROMPT = """\
Game: {game_name}
Video type: {video_type}
Channel: {channel_name}
Target audience: {audience}
Tone: {tone}
Key moments in this video: {key_moments}
Video script summary: {script_summary}
Current date: {current_date}

Generate YouTube metadata optimized for maximum reach:

Return as JSON:
{{
  "titles": [
    {{"title": "...", "style": "curiosity|shock|how-to|numbers|personal"}},
    {{"title": "...", "style": "curiosity|shock|how-to|numbers|personal"}},
    {{"title": "...", "style": "curiosity|shock|how-to|numbers|personal"}}
  ],
  "description": "...",
  "tags": ["tag1", "tag2", ...],
  "category_id": "20",
  "thumbnail_text": "...",
  "thumbnail_subtext": "..."
}}
"""

HIGHLIGHT_SELECTOR_PROMPT = """\
Given this transcript and frame analysis, identify the TOP {count} most entertaining
moments for a highlights reel targeting {audience} viewers who enjoy {tone} content.

Game: {game_name}
Transcript: {transcript}
Frame analysis: {frame_analysis}

For each highlight, provide:
- Start/end timestamps
- Why it's entertaining
- Suggested caption text
- Energy level

Return as JSON array of highlight objects.
"""
