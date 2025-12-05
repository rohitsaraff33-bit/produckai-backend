"""Unified feedback ingestion service."""

import structlog
from datetime import datetime
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from apps.api.models import Feedback, FeedbackSource
from apps.api.services.ingestion.base import (
    ContentExtractor,
    CustomerInfo,
    ExtractionStats,
)

logger = structlog.get_logger(__name__)


class FeedbackIngestionService:
    """Unified service for ingesting feedback from any source."""

    def __init__(self, db: Session, embedding_model: SentenceTransformer | None = None):
        """
        Initialize ingestion service.

        Args:
            db: Database session
            embedding_model: Optional pre-loaded embedding model
        """
        self.db = db
        self._embedding_model = embedding_model
        self._customer_cache: dict[str, str] = {}  # Simple normalization cache

    @property
    def embedding_model(self) -> SentenceTransformer:
        """Lazy-load embedding model."""
        if self._embedding_model is None:
            logger.info("Loading embedding model: all-MiniLM-L6-v2")
            self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._embedding_model

    def ingest_item(
        self,
        source: FeedbackSource,
        raw_content: dict,
        extractor: ContentExtractor,
    ) -> tuple[list[Feedback], ExtractionStats]:
        """
        Ingest a single item using source-specific extractor.

        Standard ingestion flow:
        1. Extract customer/account info
        2. Chunk long content into focused feedback items
        3. Generate embeddings immediately
        4. Create and store Feedback records

        Args:
            source: Feedback source type
            raw_content: Source-specific raw data
            extractor: Source-specific content extractor

        Returns:
            Tuple of (created feedback items, extraction stats)

        Raises:
            ValueError: If content is invalid
        """
        stats = ExtractionStats()

        try:
            # Validate content
            extractor.validate_content(raw_content)
            stats.total_items = 1

            # Step 1: Extract customer info
            customer_info = extractor.extract_customer(raw_content)
            normalized_customer = self._normalize_customer(customer_info)
            stats.customers_extracted = 1

            # Log low-confidence extractions
            if customer_info.confidence < 0.7:
                stats.add_warning(
                    f"Low confidence customer extraction: {customer_info.name} "
                    f"(confidence={customer_info.confidence:.2f}, "
                    f"method={customer_info.extraction_method})"
                )
                logger.warning(
                    "Low confidence customer extraction",
                    customer=customer_info.name,
                    confidence=customer_info.confidence,
                    method=customer_info.extraction_method,
                )

            # Step 2: Chunk content if needed
            chunks = extractor.chunk_content(raw_content)
            stats.chunks_created = len(chunks)

            # Step 3: Create feedback items with embeddings
            feedback_items = []
            texts_to_embed = [chunk.text for chunk in chunks]

            # Generate embeddings in batch for efficiency
            if texts_to_embed:
                logger.info(
                    "Generating embeddings",
                    count=len(texts_to_embed),
                    source=source.value,
                )
                embeddings = self.embedding_model.encode(
                    texts_to_embed, convert_to_numpy=True, show_progress_bar=False
                )
                stats.embeddings_generated = len(texts_to_embed)

                for chunk, embedding in zip(chunks, embeddings):
                    # Check if feedback already exists
                    existing = (
                        self.db.query(Feedback)
                        .filter(
                            Feedback.source == source, Feedback.source_id == chunk.id
                        )
                        .first()
                    )

                    if existing:
                        # Update existing feedback
                        existing.text = chunk.text
                        existing.account = normalized_customer
                        existing.embedding = embedding.tolist()
                        existing.meta = {
                            **chunk.metadata,
                            "customer_confidence": customer_info.confidence,
                            "extraction_method": customer_info.extraction_method,
                        }
                        feedback_items.append(existing)
                        logger.debug("Updated existing feedback", id=existing.id)
                    else:
                        # Create new feedback
                        feedback = Feedback(
                            source=source,
                            source_id=chunk.id,
                            text=chunk.text,
                            account=normalized_customer,
                            embedding=embedding.tolist(),
                            created_at=chunk.metadata.get("created_at", datetime.utcnow()),
                            meta={
                                **chunk.metadata,
                                "customer_confidence": customer_info.confidence,
                                "extraction_method": customer_info.extraction_method,
                            },
                        )
                        self.db.add(feedback)
                        feedback_items.append(feedback)
                        logger.debug("Created new feedback", source_id=chunk.id)

            self.db.flush()  # Flush to get IDs without committing

            logger.info(
                "Ingestion completed",
                source=source.value,
                customer=normalized_customer,
                chunks_created=stats.chunks_created,
                embeddings_generated=stats.embeddings_generated,
            )

            return feedback_items, stats

        except Exception as e:
            stats.errors += 1
            stats.add_warning(f"Ingestion error: {str(e)}")
            logger.error("Ingestion failed", error=str(e), source=source.value)
            raise

    def _normalize_customer(self, customer_info: CustomerInfo) -> str:
        """
        Normalize customer name for consistency.

        Basic normalization for now:
        - Trim whitespace
        - Handle common variations
        - Cache for performance

        Args:
            customer_info: Extracted customer information

        Returns:
            Normalized customer name
        """
        raw_name = customer_info.name.strip()

        # Check cache first
        if raw_name in self._customer_cache:
            return self._customer_cache[raw_name]

        # Basic normalization
        normalized = raw_name

        # Handle empty/unknown
        if not normalized or normalized.lower() in ["unknown", "none", ""]:
            normalized = "Unknown"

        # Handle common suffixes (optional - can be enhanced)
        # e.g., "Acme Corp" vs "Acme Corporation"
        # For now, just store as-is

        # Cache result
        self._customer_cache[raw_name] = normalized

        return normalized

    def ingest_batch(
        self,
        source: FeedbackSource,
        raw_items: list[dict],
        extractor: ContentExtractor,
        batch_size: int = 50,
    ) -> tuple[list[Feedback], ExtractionStats]:
        """
        Ingest multiple items in batches.

        Args:
            source: Feedback source type
            raw_items: List of source-specific raw data
            extractor: Source-specific content extractor
            batch_size: Number of items to process before committing

        Returns:
            Tuple of (all created feedback items, aggregated stats)
        """
        all_feedback = []
        total_stats = ExtractionStats()

        for i, raw_content in enumerate(raw_items):
            try:
                feedback_items, stats = self.ingest_item(source, raw_content, extractor)
                all_feedback.extend(feedback_items)

                # Aggregate stats
                total_stats.total_items += stats.total_items
                total_stats.chunks_created += stats.chunks_created
                total_stats.customers_extracted += stats.customers_extracted
                total_stats.embeddings_generated += stats.embeddings_generated
                total_stats.errors += stats.errors
                if stats.warnings:
                    total_stats.warnings.extend(stats.warnings)

                # Commit in batches
                if (i + 1) % batch_size == 0:
                    self.db.commit()
                    logger.info(
                        "Committed batch",
                        batch_num=(i + 1) // batch_size,
                        items_processed=i + 1,
                    )

            except Exception as e:
                total_stats.errors += 1
                total_stats.add_warning(f"Failed to ingest item {i}: {str(e)}")
                logger.error("Failed to ingest item", index=i, error=str(e))
                # Continue with next item

        # Final commit
        self.db.commit()

        logger.info(
            "Batch ingestion completed",
            source=source.value,
            total_items=total_stats.total_items,
            chunks_created=total_stats.chunks_created,
            errors=total_stats.errors,
        )

        return all_feedback, total_stats
