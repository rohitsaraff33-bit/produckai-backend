"""Zoom API client for fetching meetings and transcripts."""

from datetime import datetime, timedelta
from typing import List, Optional

import httpx
import structlog
from sqlalchemy.orm import Session

from apps.api.config import get_settings
from apps.api.models import FeedbackSource, OAuthProvider, OAuthToken, TokenStatus
from apps.api.services.crypto import get_token_encryptor

logger = structlog.get_logger()
settings = get_settings()


class ZoomClient:
    """Client for interacting with Zoom API."""

    BASE_URL = "https://api.zoom.us/v2"

    def __init__(self, access_token: str):
        """
        Initialize Zoom client with access token.

        Args:
            access_token: OAuth access token
        """
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    @classmethod
    def from_db(cls, db: Session) -> Optional["ZoomClient"]:
        """
        Create Zoom client from database token.

        Args:
            db: Database session

        Returns:
            ZoomClient instance or None if no valid token found
        """
        # Get active token
        token = (
            db.query(OAuthToken)
            .filter(
                OAuthToken.provider == OAuthProvider.zoom,
                OAuthToken.status == TokenStatus.active,
                OAuthToken.expires_at > datetime.utcnow(),
            )
            .first()
        )

        if not token:
            logger.warning("No valid Zoom OAuth token found")
            return None

        # Decrypt access token
        encryptor = get_token_encryptor()
        try:
            access_token = encryptor.decrypt(token.access_token_enc)
        except Exception as e:
            logger.error("Failed to decrypt Zoom access token", error=str(e))
            return None

        return cls(access_token)

    async def get_user_info(self) -> dict:
        """
        Get current user information.

        Returns:
            User information dict
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/users/me",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def list_recordings(
        self,
        user_id: str = "me",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page_size: int = 100,
    ) -> List[dict]:
        """
        List meeting recordings.

        Args:
            user_id: User ID or 'me' for current user
            from_date: Start date for recordings (defaults to 30 days ago)
            to_date: End date for recordings (defaults to now)
            page_size: Number of recordings per page

        Returns:
            List of recording dicts
        """
        if from_date is None:
            from_date = datetime.utcnow() - timedelta(days=30)
        if to_date is None:
            to_date = datetime.utcnow()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/users/{user_id}/recordings",
                headers=self.headers,
                params={
                    "from": from_date.strftime("%Y-%m-%d"),
                    "to": to_date.strftime("%Y-%m-%d"),
                    "page_size": page_size,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("meetings", [])

    async def get_meeting_transcript(self, meeting_id: str) -> Optional[str]:
        """
        Get meeting transcript if available.

        Args:
            meeting_id: Meeting ID

        Returns:
            Transcript text or None if not available
        """
        try:
            # First, get recording details
            recordings = await self.list_recordings()

            # Find the meeting
            meeting_recording = None
            for recording in recordings:
                if str(recording.get("id")) == str(meeting_id):
                    meeting_recording = recording
                    break

            if not meeting_recording:
                logger.debug("No recording found for meeting", meeting_id=meeting_id)
                return None

            # Check if transcript is available
            recording_files = meeting_recording.get("recording_files", [])
            transcript_file = None
            for file in recording_files:
                if file.get("file_type") == "TRANSCRIPT":
                    transcript_file = file
                    break

            if not transcript_file:
                logger.debug("No transcript file found for meeting", meeting_id=meeting_id)
                return None

            # Download transcript
            download_url = transcript_file.get("download_url")
            if not download_url:
                return None

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    download_url,
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.text

        except Exception as e:
            logger.error("Failed to get meeting transcript", meeting_id=meeting_id, error=str(e))
            return None


async def sync_zoom_recordings(db: Session, days_back: int = 30) -> dict:
    """
    Sync Zoom recordings and transcripts to feedback database.

    Args:
        db: Database session
        days_back: Number of days back to fetch recordings

    Returns:
        Sync statistics dict
    """
    from apps.api.models import Feedback

    client = ZoomClient.from_db(db)
    if not client:
        return {"error": "No valid Zoom token found"}

    stats = {
        "recordings_found": 0,
        "transcripts_found": 0,
        "feedback_created": 0,
        "feedback_updated": 0,
        "errors": 0,
    }

    try:
        # Get user info
        user_info = await client.get_user_info()
        user_email = user_info.get("email", "")

        # Fetch recordings
        from_date = datetime.utcnow() - timedelta(days=days_back)
        recordings = await client.list_recordings(from_date=from_date)
        stats["recordings_found"] = len(recordings)

        logger.info("Found Zoom recordings", count=len(recordings))

        # Process each recording
        for recording in recordings:
            meeting_id = str(recording.get("id"))
            meeting_topic = recording.get("topic", "Untitled Meeting")
            meeting_start = recording.get("start_time")

            # Try to get transcript
            transcript = await client.get_meeting_transcript(meeting_id)
            if not transcript:
                continue

            stats["transcripts_found"] += 1

            # Check if feedback already exists
            existing_feedback = (
                db.query(Feedback)
                .filter(
                    Feedback.source == FeedbackSource.zoom,
                    Feedback.source_id == meeting_id,
                )
                .first()
            )

            if existing_feedback:
                # Update existing
                existing_feedback.text = transcript
                existing_feedback.meta = {
                    "topic": meeting_topic,
                    "start_time": meeting_start,
                    "host_email": user_email,
                }
                stats["feedback_updated"] += 1
            else:
                # Create new feedback
                feedback = Feedback(
                    source=FeedbackSource.zoom,
                    source_id=meeting_id,
                    text=transcript,
                    account=user_email.split("@")[0] if user_email else None,
                    created_at=datetime.fromisoformat(meeting_start.replace("Z", "+00:00"))
                    if meeting_start
                    else datetime.utcnow(),
                    meta={
                        "topic": meeting_topic,
                        "start_time": meeting_start,
                        "host_email": user_email,
                    },
                )
                db.add(feedback)
                stats["feedback_created"] += 1

        db.commit()
        logger.info("Zoom sync completed", stats=stats)

    except Exception as e:
        logger.error("Zoom sync failed", error=str(e))
        stats["errors"] += 1
        db.rollback()

    return stats
