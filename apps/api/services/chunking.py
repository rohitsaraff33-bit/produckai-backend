"""Text chunking utilities for splitting documents into processable segments."""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""

    text: str
    start_idx: int
    end_idx: int
    chunk_idx: int
    metadata: dict = None


class ChunkingService:
    """Service for chunking text into manageable segments."""

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50,
        split_on_headers: bool = True
    ):
        """Initialize chunking service.

        Args:
            chunk_size: Target token count per chunk (approx. 4 chars = 1 token)
            overlap: Token overlap between chunks
            split_on_headers: Whether to split on markdown headers first
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.split_on_headers = split_on_headers

        # Approximate tokens by character count (rough heuristic: ~4 chars per token)
        self.char_per_token = 4
        self.chunk_chars = chunk_size * self.char_per_token
        self.overlap_chars = overlap * self.char_per_token

    def chunk_text(self, text: str, metadata: Optional[dict] = None) -> List[TextChunk]:
        """Chunk text into segments with overlap.

        Args:
            text: Input text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of TextChunk objects
        """
        if not text or len(text.strip()) == 0:
            return []

        chunks = []
        metadata = metadata or {}

        # If splitting on headers, try that first
        if self.split_on_headers:
            header_chunks = self._split_by_headers(text)
            if len(header_chunks) > 1:
                # Further split large header sections
                for header_text, header_level in header_chunks:
                    sub_chunks = self._split_by_tokens(header_text)
                    for idx, (chunk_text, start, end) in enumerate(sub_chunks):
                        chunks.append(
                            TextChunk(
                                text=chunk_text,
                                start_idx=start,
                                end_idx=end,
                                chunk_idx=len(chunks),
                                metadata={**metadata, 'header_level': header_level},
                            )
                        )
                return chunks

        # Default: split by tokens
        token_chunks = self._split_by_tokens(text)
        for idx, (chunk_text, start, end) in enumerate(token_chunks):
            chunks.append(
                TextChunk(
                    text=chunk_text,
                    start_idx=start,
                    end_idx=end,
                    chunk_idx=idx,
                    metadata=metadata,
                )
            )

        return chunks

    def _split_by_headers(self, text: str) -> List[Tuple[str, int]]:
        """Split text by markdown headers (H1, H2, H3).

        Args:
            text: Input markdown text

        Returns:
            List of (text, header_level) tuples
        """
        # Pattern to match markdown headers
        header_pattern = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)

        matches = list(header_pattern.finditer(text))
        if not matches:
            return [(text, 0)]

        sections = []
        for i, match in enumerate(matches):
            header_level = len(match.group(1))
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_text = text[start:end].strip()

            if section_text:
                sections.append((section_text, header_level))

        return sections if sections else [(text, 0)]

    def _split_by_tokens(self, text: str) -> List[Tuple[str, int, int]]:
        """Split text by token count with overlap.

        Args:
            text: Input text

        Returns:
            List of (chunk_text, start_idx, end_idx) tuples
        """
        if len(text) <= self.chunk_chars:
            return [(text, 0, len(text))]

        chunks = []
        start = 0

        while start < len(text):
            end = min(start + self.chunk_chars, len(text))

            # Try to break on sentence boundary if not at end
            if end < len(text):
                # Look for sentence ending within last 20% of chunk
                search_start = max(start, end - int(self.chunk_chars * 0.2))
                sentence_end = self._find_sentence_boundary(text, search_start, end)
                if sentence_end > start:
                    end = sentence_end

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append((chunk_text, start, end))

            # Move start forward with overlap
            start = max(start + 1, end - self.overlap_chars)

        return chunks

    def _find_sentence_boundary(self, text: str, start: int, end: int) -> int:
        """Find the nearest sentence boundary in text[start:end].

        Args:
            text: Full text
            start: Search start index
            end: Search end index

        Returns:
            Index of sentence boundary, or end if none found
        """
        # Look for sentence endings: . ! ? followed by space or newline
        sentence_pattern = re.compile(r'[.!?]\s+')

        # Search backwards from end
        search_text = text[start:end]
        matches = list(sentence_pattern.finditer(search_text))

        if matches:
            # Return position after the last match
            last_match = matches[-1]
            return start + last_match.end()

        return end


def get_chunking_service(
    chunk_size: int = 500, overlap: int = 50, split_on_headers: bool = True
) -> ChunkingService:
    """Get chunking service instance.

    Args:
        chunk_size: Target token count per chunk
        overlap: Token overlap between chunks
        split_on_headers: Whether to split on headers

    Returns:
        ChunkingService instance
    """
    return ChunkingService(
        chunk_size=chunk_size, overlap=overlap, split_on_headers=split_on_headers
    )
