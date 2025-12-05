"""File upload and parsing service for customer feedback.

Supports CSV, PDF, DOC, DOCX, and TXT file formats.
"""

import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

import structlog
from sqlalchemy.orm import Session

from apps.api.models import Customer, CustomerSegment, Feedback, FeedbackSource
from apps.api.services.embeddings import get_embedding_service
from apps.api.services.pii_redaction import get_pii_redaction_service

logger = structlog.get_logger()


@dataclass
class ParsedFeedback:
    """Parsed feedback item from uploaded file."""

    text: str
    customer_name: Optional[str] = None
    source_metadata: Optional[dict] = None
    timestamp: Optional[datetime] = None


class FileUploadService:
    """Service for uploading and parsing customer feedback files."""

    SUPPORTED_FORMATS = {
        "text/csv": "csv",
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/msword": "doc",
        "text/plain": "txt",
    }

    def __init__(self):
        """Initialize file upload service."""
        self.embedding_service = get_embedding_service()
        self.pii_service = get_pii_redaction_service()

    async def process_uploaded_files(
        self,
        files: List[tuple],  # List of (filename, content_type, file_bytes)
        db: Session,
    ) -> dict:
        """
        Process multiple uploaded files and ingest feedback.

        Args:
            files: List of tuples (filename, content_type, file_bytes)
            db: Database session

        Returns:
            Summary dict with counts and errors
        """
        logger.info("Processing uploaded files", file_count=len(files))

        results = {
            "total_files": len(files),
            "successful_files": 0,
            "failed_files": 0,
            "total_feedback_items": 0,
            "errors": [],
        }

        for filename, content_type, file_bytes in files:
            try:
                logger.info("Processing file", filename=filename, content_type=content_type)

                # Detect file format
                file_format = self._detect_format(filename, content_type)
                if not file_format:
                    error_msg = f"Unsupported file format: {content_type}"
                    logger.warning(error_msg, filename=filename)
                    results["errors"].append({"filename": filename, "error": error_msg})
                    results["failed_files"] += 1
                    continue

                # Parse file content
                parsed_items = await self._parse_file(
                    file_bytes, file_format, filename
                )

                if not parsed_items:
                    error_msg = "No feedback items found in file"
                    logger.warning(error_msg, filename=filename)
                    results["errors"].append({"filename": filename, "error": error_msg})
                    results["failed_files"] += 1
                    continue

                # Ingest feedback items
                ingested_count = await self._ingest_feedback(
                    parsed_items, filename, db
                )

                results["successful_files"] += 1
                results["total_feedback_items"] += ingested_count
                logger.info(
                    "File processed successfully",
                    filename=filename,
                    items=ingested_count,
                )

            except Exception as e:
                error_msg = f"Failed to process file: {str(e)}"
                logger.error(error_msg, filename=filename, error=str(e))
                results["errors"].append({"filename": filename, "error": error_msg})
                results["failed_files"] += 1

        return results

    def _detect_format(self, filename: str, content_type: str) -> Optional[str]:
        """
        Detect file format from content type and filename.

        Args:
            filename: Original filename
            content_type: MIME content type

        Returns:
            File format string or None if unsupported
        """
        # Check content type first
        if content_type in self.SUPPORTED_FORMATS:
            return self.SUPPORTED_FORMATS[content_type]

        # Fallback to file extension
        if filename.lower().endswith(".csv"):
            return "csv"
        elif filename.lower().endswith(".pdf"):
            return "pdf"
        elif filename.lower().endswith(".docx"):
            return "docx"
        elif filename.lower().endswith(".doc"):
            return "doc"
        elif filename.lower().endswith(".txt"):
            return "txt"

        return None

    async def _parse_file(
        self, file_bytes: bytes, file_format: str, filename: str
    ) -> List[ParsedFeedback]:
        """
        Parse file content based on format.

        Args:
            file_bytes: Raw file bytes
            file_format: Detected file format
            filename: Original filename

        Returns:
            List of parsed feedback items
        """
        if file_format == "csv":
            return await self._parse_csv(file_bytes)
        elif file_format == "pdf":
            return await self._parse_pdf(file_bytes)
        elif file_format in ["doc", "docx"]:
            return await self._parse_doc(file_bytes)
        elif file_format == "txt":
            return await self._parse_txt(file_bytes)
        else:
            raise ValueError(f"Unsupported format: {file_format}")

    async def _parse_csv(self, file_bytes: bytes) -> List[ParsedFeedback]:
        """Parse CSV file with feedback data."""
        items = []
        content = file_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))

        for row in reader:
            # Support multiple column name variations
            text = (
                row.get("Feedback")
                or row.get("feedback")
                or row.get("text")
                or row.get("comment")
                or row.get("description")
                or ""
            )

            customer_name = (
                row.get("Company Name")
                or row.get("customer")
                or row.get("customer_name")
                or row.get("company")
                or None
            )

            # Extract ACV if available
            acv_str = row.get("ACV") or row.get("acv") or row.get("annual_contract_value")
            acv = None
            if acv_str:
                try:
                    acv = float(acv_str)
                except:
                    pass

            # Extract contact email if available
            contact_email = (
                row.get("Company Contact")
                or row.get("contact")
                or row.get("email")
                or None
            )

            timestamp_str = row.get("date") or row.get("timestamp") or row.get("created_at")
            timestamp = None
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except:
                    pass

            if text and text.strip():
                metadata = {"csv_row": row}
                if acv:
                    metadata["acv"] = acv
                if contact_email:
                    metadata["contact_email"] = contact_email

                items.append(
                    ParsedFeedback(
                        text=text.strip(),
                        customer_name=customer_name,
                        timestamp=timestamp,
                        source_metadata=metadata,
                    )
                )

        return items

    async def _parse_pdf(self, file_bytes: bytes) -> List[ParsedFeedback]:
        """Parse PDF file and extract text."""
        try:
            import PyPDF2
        except ImportError:
            logger.warning("PyPDF2 not installed, cannot parse PDF files")
            raise ValueError("PDF parsing not available - PyPDF2 not installed")

        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        full_text = ""

        for page in pdf_reader.pages:
            full_text += page.extract_text() + "\n"

        # Split by paragraphs or double newlines
        paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]

        # Each paragraph becomes a feedback item
        items = []
        for para in paragraphs:
            if len(para) > 20:  # Filter out very short text
                items.append(ParsedFeedback(text=para))

        return items

    async def _parse_doc(self, file_bytes: bytes) -> List[ParsedFeedback]:
        """Parse DOC/DOCX file and extract text."""
        try:
            from docx import Document
        except ImportError:
            logger.warning("python-docx not installed, cannot parse DOC files")
            raise ValueError("DOC parsing not available - python-docx not installed")

        doc = Document(io.BytesIO(file_bytes))
        items = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if len(text) > 20:  # Filter out very short text
                items.append(ParsedFeedback(text=text))

        return items

    async def _parse_txt(self, file_bytes: bytes) -> List[ParsedFeedback]:
        """Parse plain text file."""
        content = file_bytes.decode("utf-8")

        # Split by double newlines (paragraphs) or single newlines
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        # If no paragraphs found, try single newlines
        if not paragraphs:
            paragraphs = [line.strip() for line in content.split("\n") if line.strip()]

        items = []
        for para in paragraphs:
            if len(para) > 20:  # Filter out very short text
                items.append(ParsedFeedback(text=para))

        return items

    async def _ingest_feedback(
        self, items: List[ParsedFeedback], filename: str, db: Session
    ) -> int:
        """
        Ingest parsed feedback items into database.

        Args:
            items: Parsed feedback items
            filename: Source filename
            db: Database session

        Returns:
            Number of items ingested
        """
        ingested_count = 0

        for item in items:
            try:
                # Apply PII redaction
                redacted_text = self.pii_service.redact(item.text)

                # Get or create customer if provided
                customer_id = None
                if item.customer_name:
                    customer = (
                        db.query(Customer)
                        .filter(Customer.name.ilike(item.customer_name))
                        .first()
                    )
                    if not customer:
                        # Determine segment based on ACV if available
                        # SMB: ACV <= $50,000
                        # MM: $50,000 < ACV <= $200,000
                        # ENT: ACV > $200,000
                        acv = item.source_metadata.get("acv", 0) if item.source_metadata else 0
                        if acv > 200000:
                            segment = CustomerSegment.ENT
                        elif acv > 50000:
                            segment = CustomerSegment.MM
                        else:
                            segment = CustomerSegment.SMB

                        customer = Customer(
                            id=uuid4(),
                            name=item.customer_name,
                            segment=segment,
                            acv=acv,
                        )
                        db.add(customer)
                        db.flush()
                    else:
                        # Update ACV if provided and different
                        acv = item.source_metadata.get("acv") if item.source_metadata else None
                        if acv and customer.acv != acv:
                            customer.acv = acv
                            # Update segment based on new ACV
                            # SMB: ACV <= $50,000
                            # MM: $50,000 < ACV <= $200,000
                            # ENT: ACV > $200,000
                            if acv > 200000:
                                customer.segment = CustomerSegment.ENT
                            elif acv > 50000:
                                customer.segment = CustomerSegment.MM
                            else:
                                customer.segment = CustomerSegment.SMB
                    customer_id = customer.id

                # Generate embedding
                embedding = self.embedding_service.embed_text(redacted_text)

                # Create feedback record
                feedback = Feedback(
                    id=uuid4(),
                    text=item.text,
                    embedding=embedding,
                    source=FeedbackSource.upload,
                    source_id=filename,
                    customer_id=customer_id,
                    meta={
                        "filename": filename,
                        **(item.source_metadata or {}),
                    },
                )

                db.add(feedback)
                ingested_count += 1

            except Exception as e:
                logger.error(
                    "Failed to ingest feedback item",
                    error=str(e),
                    text_preview=item.text[:100],
                )
                continue

        db.commit()
        logger.info(f"Ingested {ingested_count} feedback items from {filename}")

        return ingested_count


# Global instance
_upload_service: Optional[FileUploadService] = None


def get_upload_service() -> FileUploadService:
    """Get or create global upload service instance."""
    global _upload_service
    if _upload_service is None:
        _upload_service = FileUploadService()
    return _upload_service
