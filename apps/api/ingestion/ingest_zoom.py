"""Zoom transcripts ingestion - demo and live modes."""

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from apps.api.config import get_settings
from apps.api.database import get_db_context
from apps.api.models import Feedback, FeedbackSource
from apps.api.services.chunking import get_chunking_service
from apps.api.services.embeddings import get_embedding_service
from apps.api.services.pii_redaction import get_pii_redaction_service
from apps.api.services.zoom_client import get_zoom_client, parse_vtt_transcript

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


def normalize_zoom_text(text: str, remove_fillers: bool = False) -> str:
    """Normalize Zoom transcript text.

    Args:
        text: Raw transcript text
        remove_fillers: Whether to remove filler words (uh, um)

    Returns:
        Normalized text
    """
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Optionally remove filler words
    if remove_fillers:
        filler_pattern = r'\b(uh|um|uhh|umm|uh-huh|mm-hmm)\b'
        text = re.sub(filler_pattern, '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip()

    return text


def chunk_transcript_by_time(
    segments: List[dict], chunk_duration: int = 90
) -> List[List[dict]]:
    """Chunk transcript segments by time duration.

    Args:
        segments: List of transcript segment dicts
        chunk_duration: Target duration in seconds

    Returns:
        List of segment groups (chunks)
    """
    if not segments:
        return []

    chunks = []
    current_chunk = []
    chunk_start = segments[0].get('start_seconds', 0)

    for segment in segments:
        segment_start = segment.get('start_seconds', 0)

        # If we've exceeded chunk duration, start new chunk
        if segment_start - chunk_start >= chunk_duration and current_chunk:
            chunks.append(current_chunk)
            current_chunk = [segment]
            chunk_start = segment_start
        else:
            current_chunk.append(segment)

    # Add final chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def ingest_zoom_demo(db: Session) -> int:
    """Ingest demo Zoom transcript files from /samples/zoom.

    Args:
        db: Database session

    Returns:
        Number of feedback items created
    """
    samples_dir = Path('/app/samples') if Path('/app/samples').exists() else Path('samples')
    zoom_dir = samples_dir / 'zoom'

    if not zoom_dir.exists():
        logger.warning(f"Zoom samples directory not found: {zoom_dir}")
        return 0

    pii_service = get_pii_redaction_service()
    embedding_service = get_embedding_service()

    feedback_items = []

    # Process all .vtt files
    for file_path in zoom_dir.glob('*.vtt'):
        logger.info(f"Processing demo transcript: {file_path.name}")

        with open(file_path, 'r', encoding='utf-8') as f:
            vtt_content = f.read()

        # Parse VTT
        segments = parse_vtt_transcript(vtt_content)

        if not segments:
            logger.warning(f"No segments found in {file_path.name}")
            continue

        logger.info(f"Parsed {len(segments)} segments from {file_path.name}")

        # Chunk by time (90 seconds per chunk)
        time_chunks = chunk_transcript_by_time(segments, chunk_duration=90)

        logger.info(f"Created {len(time_chunks)} time-based chunks")

        # Create meeting metadata
        meeting_topic = file_path.stem.replace('_', ' ').replace('-', ' ').title()
        meeting_id = file_path.stem

        # Create feedback items for each chunk
        for chunk_idx, segment_group in enumerate(time_chunks):
            # Combine text from all segments in chunk
            chunk_text_parts = []
            speakers = set()
            start_time = segment_group[0].get('start_seconds', 0)
            end_time = segment_group[-1].get('end_seconds', 0)

            for seg in segment_group:
                speaker = seg.get('speaker', 'Unknown')
                text = seg.get('text', '')
                speakers.add(speaker)

                # Format as "Speaker: text"
                chunk_text_parts.append(f"{speaker}: {text}")

            combined_text = ' '.join(chunk_text_parts)

            # Normalize text
            normalized = normalize_zoom_text(
                combined_text, remove_fillers=getattr(settings, 'zoom_remove_fillers', False)
            )

            # Redact PII
            redacted_text = pii_service.redact(normalized)

            # Use first speaker as primary speaker for this chunk
            primary_speaker = segment_group[0].get('speaker', 'Unknown')

            feedback = Feedback(
                id=uuid4(),
                source=FeedbackSource.zoom,
                source_id=f"{meeting_id}_chunk_{chunk_idx}",
                account='Demo',
                text=redacted_text,
                created_at=datetime.utcnow(),
                speaker=primary_speaker,
                started_at=datetime.utcnow() + timedelta(seconds=start_time),
                ended_at=datetime.utcnow() + timedelta(seconds=end_time),
                doc_url=f"file://{file_path}",
                meta={
                    'zoom_meeting_id': meeting_id,
                    'topic': meeting_topic,
                    'chunk_idx': chunk_idx,
                    'total_chunks': len(time_chunks),
                    'start_sec': start_time,
                    'end_sec': end_time,
                    'speakers': list(speakers),
                    'segment_count': len(segment_group),
                },
            )
            feedback_items.append(feedback)

    # Batch add to database
    if feedback_items:
        for item in feedback_items:
            db.add(item)
        db.commit()

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(feedback_items)} chunks...")
        texts = [f.text for f in feedback_items]
        embeddings = embedding_service.embed_batch(texts)

        for feedback, embedding in zip(feedback_items, embeddings):
            feedback.embedding = embedding

        db.commit()
        logger.info(f"Ingested {len(feedback_items)} feedback items from Zoom demo")

    return len(feedback_items)


def ingest_zoom_live(
    db: Session,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: Optional[str] = None,
) -> int:
    """Ingest Zoom transcripts from live API.

    Args:
        db: Database session
        start_date: Start date (YYYY-MM-DD, defaults to env or 30 days ago)
        end_date: End date (YYYY-MM-DD, defaults to env or today)
        user_id: Zoom user ID (defaults to env)

    Returns:
        Number of feedback items created
    """
    # Default date range
    if not start_date:
        start_date = getattr(settings, 'zoom_start_date', None)
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    if not end_date:
        end_date = getattr(settings, 'zoom_end_date', None)
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

    logger.info(f"Ingesting Zoom recordings from {start_date} to {end_date}")

    zoom_client = get_zoom_client()
    pii_service = get_pii_redaction_service()
    embedding_service = get_embedding_service()

    feedback_items = []

    # List recordings
    recordings = zoom_client.list_recordings(start_date, end_date)
    logger.info(f"Found {len(recordings)} recordings to process")

    for meeting_data in recordings:
        try:
            meeting_id = meeting_data['id']
            topic = meeting_data.get('topic', 'Untitled Meeting')
            start_time = datetime.fromisoformat(meeting_data['start_time'].replace('Z', '+00:00'))

            logger.info(f"Processing meeting: {topic} ({meeting_id})")

            # Get recording files
            recording_files = meeting_data.get('recording_files', [])

            # Find transcript and recording URL
            transcript_file = None
            recording_url = None

            for file in recording_files:
                if file.get('recording_type') == 'transcript' and file.get('file_type') == 'VTT':
                    transcript_file = file
                elif file.get('recording_type') in ['shared_screen_with_speaker_view', 'active_speaker']:
                    recording_url = file.get('play_url')

            if not transcript_file:
                logger.warning(f"No transcript found for meeting {meeting_id}")
                continue

            # Get transcript content
            vtt_content = zoom_client.get_recording_transcript(meeting_id, transcript_file['id'])

            if not vtt_content:
                logger.warning(f"Could not download transcript for meeting {meeting_id}")
                continue

            # Parse VTT
            segments = parse_vtt_transcript(vtt_content)

            if not segments:
                logger.warning(f"No segments in transcript for meeting {meeting_id}")
                continue

            logger.info(f"Parsed {len(segments)} segments from {topic}")

            # Chunk by time
            time_chunks = chunk_transcript_by_time(segments, chunk_duration=90)

            # Extract participant emails for account mapping
            participant_emails = zoom_client.extract_participant_emails(meeting_data)
            account = 'Unknown'
            if participant_emails:
                # Use domain from first participant
                email = participant_emails[0]
                account = email.split('@')[1] if '@' in email else 'Unknown'

            # Create feedback items
            for chunk_idx, segment_group in enumerate(time_chunks):
                chunk_text_parts = []
                speakers = set()
                start_sec = segment_group[0].get('start_seconds', 0)
                end_sec = segment_group[-1].get('end_seconds', 0)

                for seg in segment_group:
                    speaker = seg.get('speaker', 'Unknown')
                    text = seg.get('text', '')
                    speakers.add(speaker)
                    chunk_text_parts.append(f"{speaker}: {text}")

                combined_text = ' '.join(chunk_text_parts)

                # Normalize and redact
                normalized = normalize_zoom_text(
                    combined_text, remove_fillers=getattr(settings, 'zoom_remove_fillers', False)
                )
                redacted_text = pii_service.redact(normalized)

                primary_speaker = segment_group[0].get('speaker', 'Unknown')

                feedback = Feedback(
                    id=uuid4(),
                    source=FeedbackSource.zoom,
                    source_id=f"{meeting_id}_chunk_{chunk_idx}",
                    account=account,
                    text=redacted_text,
                    created_at=start_time,
                    speaker=primary_speaker,
                    started_at=start_time + timedelta(seconds=start_sec),
                    ended_at=start_time + timedelta(seconds=end_sec),
                    doc_url=recording_url,
                    meta={
                        'zoom_meeting_id': meeting_id,
                        'topic': topic,
                        'chunk_idx': chunk_idx,
                        'total_chunks': len(time_chunks),
                        'start_sec': start_sec,
                        'end_sec': end_sec,
                        'speakers': list(speakers),
                        'segment_count': len(segment_group),
                        'participants': participant_emails,
                    },
                )
                feedback_items.append(feedback)

        except Exception as e:
            logger.error(f"Error processing meeting {meeting_data.get('id')}: {e}")

    # Batch add to database
    if feedback_items:
        for item in feedback_items:
            db.add(item)
        db.commit()

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(feedback_items)} chunks...")
        texts = [f.text for f in feedback_items]
        embeddings = embedding_service.embed_batch(texts)

        for feedback, embedding in zip(feedback_items, embeddings):
            feedback.embedding = embedding

        db.commit()
        logger.info(f"Ingested {len(feedback_items)} feedback items from Zoom live")

    return len(feedback_items)


if __name__ == '__main__':
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else 'demo'

    with get_db_context() as db:
        if mode == 'demo':
            count = ingest_zoom_demo(db)
        elif mode == 'live':
            start = sys.argv[2] if len(sys.argv) > 2 else None
            end = sys.argv[3] if len(sys.argv) > 3 else None
            count = ingest_zoom_live(db, start_date=start, end_date=end)
        else:
            raise ValueError(f"Unknown mode: {mode}. Use 'demo' or 'live'")

        logger.info(f"✓ Ingested {count} feedback items from Zoom ({mode} mode)")
