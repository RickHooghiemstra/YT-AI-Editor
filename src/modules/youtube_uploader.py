"""
YouTube upload via Google Data API v3.
Handles OAuth2 flow, resumable chunked upload, and metadata setting.
"""

from __future__ import annotations

import json
import os
import pickle
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, BarColumn, TaskProgressColumn, TextColumn, TransferSpeedColumn

from src.agents.scriptwriter import VideoMetadata
from src.utils.config import get_settings

console = Console()

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CHUNK_SIZE = 1024 * 1024 * 8  # 8 MB chunks

CATEGORY_IDS = {
    "gaming": "20",
    "entertainment": "24",
    "howto": "26",
    "science": "28",
}


def upload_to_youtube(
    video_path: Path,
    thumbnail_path: Path,
    metadata: VideoMetadata,
    title_index: int = 0,
    privacy: str = "private",
) -> str:
    """
    Upload video to YouTube. Returns the video URL.
    privacy: 'private' | 'unlisted' | 'public'
    title_index: which title from metadata.titles to use
    """
    settings = get_settings()

    youtube = _get_authenticated_service(settings)
    title = metadata.titles[title_index]["title"] if metadata.titles else "Gaming Video"

    body = {
        "snippet": {
            "title": title,
            "description": metadata.description,
            "tags": metadata.tags,
            "categoryId": metadata.category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    console.print(f"[cyan]Uploading:[/cyan] {title}")
    console.print(f"  Privacy: [bold]{privacy}[/bold]")
    console.print(f"  Tags: {', '.join(metadata.tags[:5])}...")

    video_id = _resumable_upload(youtube, video_path, body)

    if video_id and thumbnail_path.exists():
        console.print("[cyan]Setting thumbnail...[/cyan]")
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=str(thumbnail_path),
            ).execute()
            console.print("[green]Thumbnail set.[/green]")
        except Exception as e:
            console.print(f"[yellow]Thumbnail upload failed: {e}[/yellow]")

    url = f"https://www.youtube.com/watch?v={video_id}"
    console.print(f"[green bold]Uploaded![/green bold] {url}")
    return url


def _resumable_upload(youtube, video_path: Path, body: dict) -> str:
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(
        str(video_path),
        chunksize=CHUNK_SIZE,
        resumable=True,
        mimetype="video/mp4",
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    file_size = video_path.stat().st_size

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TransferSpeedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Uploading to YouTube...", total=file_size)
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress.update(task, completed=status.resumable_progress)

    return response.get("id", "")


def _get_authenticated_service(settings):
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    token_path = Path(settings.youtube_token_file)
    creds = None

    if token_path.exists():
        with open(token_path, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            secrets_path = Path(settings.youtube_client_secrets_file)
            if not secrets_path.exists():
                raise FileNotFoundError(
                    f"YouTube client secrets not found: {secrets_path}\n"
                    "See SETUP.md for instructions on getting YouTube API credentials."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(secrets_path), SCOPES
            )
            creds = flow.run_local_server(port=8090)

        with open(token_path, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


def select_title_interactively(metadata: VideoMetadata) -> int:
    """Let user pick which generated title to use."""
    import questionary

    if len(metadata.titles) <= 1:
        return 0

    choices = [
        questionary.Choice(
            f"{t['title']}  [{t['style']}]",
            value=i,
        )
        for i, t in enumerate(metadata.titles)
    ]
    idx = questionary.select("Which title do you want to use?", choices=choices).ask()
    return idx if idx is not None else 0
