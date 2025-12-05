# Unified Ingestion Architecture

## Overview

We've implemented a unified feedback ingestion service that standardizes data extraction across all sources (Slack, Jira, Zoom, Google Drive, and future CRM integrations).

This solves critical issues with the previous approach:
- ❌ **Before**: Each source had custom logic, customer extraction was fragile and inconsistent
- ✅ **After**: Single pipeline, standardized extraction, automatic chunking and embedding generation

## Architecture

```
┌─────────────┐
│   Source    │ (Slack, Jira, Zoom, GDrive)
└──────┬──────┘
       │ raw_content
       ▼
┌──────────────────────┐
│  ContentExtractor    │ (Source-specific logic)
│  - extract_customer  │
│  - chunk_content     │
└──────┬───────────────┘
       │ ContentChunks + CustomerInfo
       ▼
┌─────────────────────────────┐
│ FeedbackIngestionService    │
│  - Normalize customer       │
│  - Generate embeddings      │
│  - Create Feedback records  │
└──────┬──────────────────────┘
       │
       ▼
┌──────────────┐
│   Database   │ (Feedback table with embeddings)
└──────────────┘
```

## Components

### 1. Base Classes (`apps/api/services/ingestion/base.py`)

**ContentChunk**
```python
@dataclass
class ContentChunk:
    id: str                    # Unique identifier
    text: str                  # Feedback text
    metadata: dict[str, Any]   # Source-specific metadata
```

**CustomerInfo**
```python
@dataclass
class CustomerInfo:
    name: str                  # Extracted customer name
    confidence: float          # 0.0 to 1.0
    extraction_method: str     # "structured", "regex", "llm", "fallback"
    metadata: dict | None      # Additional context
```

**ContentExtractor (Abstract Base Class)**
```python
class ContentExtractor(ABC):
    @abstractmethod
    def extract_customer(self, raw_content: dict) -> CustomerInfo:
        """Extract customer from source data."""

    @abstractmethod
    def chunk_content(self, raw_content: dict) -> list[ContentChunk]:
        """Break content into focused feedback items."""

    @abstractmethod
    def should_chunk(self, raw_content: dict) -> bool:
        """Determine if content needs chunking."""
```

### 2. Ingestion Service (`apps/api/services/ingestion/service.py`)

**FeedbackIngestionService**

Main service that orchestrates ingestion:

```python
service = FeedbackIngestionService(db, embedding_model)

# Ingest single item
feedback_items, stats = service.ingest_item(
    source=FeedbackSource.gdoc,
    raw_content={
        "text": "...",
        "source_id": "doc_123",
        "title": "Customer Feedback",
        ...
    },
    extractor=GDriveExtractor()
)

# Ingest batch
feedback_items, stats = service.ingest_batch(
    source=FeedbackSource.slack,
    raw_items=[...],
    extractor=SlackExtractor(),
    batch_size=50
)
```

**What It Does:**
1. ✅ Validates content structure
2. ✅ Extracts and normalizes customer name
3. ✅ Chunks long content (transcripts, documents)
4. ✅ Generates embeddings immediately (batch processing)
5. ✅ Creates or updates Feedback records
6. ✅ Tracks statistics and warnings
7. ✅ Handles errors gracefully

### 3. Source-Specific Extractors

#### **GDriveExtractor** (`apps/api/services/ingestion/extractors/gdrive.py`)

**Customer Extraction Strategy:**
1. Pattern matching: "their customer X", "customer X"
2. Participant info: "Name (Company - Title)"
3. Fallback: Google Drive owner email

**Chunking Strategy:**
- Transcripts (VTT format): Extract individual speaker statements with feedback keywords
- Documents: Return as single chunk
- Threshold: 2000+ characters

**Status:** ✅ **Fully Implemented** (includes VTT parsing, keyword filtering)

#### **ZoomExtractor** (`apps/api/services/ingestion/extractors/zoom.py`)

**Customer Extraction:**
1. Meeting topic parsing (e.g., "Customer Call - Acme Corp")
2. Fallback: Host email prefix

**Chunking:**
- Currently returns whole transcript
- TODO: Implement VTT parsing (same as GDrive)

**Status:** ⚠️ **Basic Implementation** (needs VTT chunking)

#### **SlackExtractor** (`apps/api/services/ingestion/extractors/slack.py`)

**Customer Extraction:**
1. Channel name patterns (e.g., "customer-acme-corp")
2. Fallback: "Demo" for internal channels

**Chunking:**
- Slack messages are typically short, no chunking needed
- Only chunks if > 2000 characters

**Status:** ⚠️ **Basic Implementation** (needs user profile lookup)

#### **JiraExtractor** (`apps/api/services/ingestion/extractors/jira.py`)

**Customer Extraction:**
1. Custom fields (Account, Organization, Customer)
2. Reporter email domain
3. Project name fallback

**Chunking:**
- Combines summary + description
- TODO: Include comments as separate chunks

**Status:** ⚠️ **Basic Implementation** (needs custom field mapping configuration)

## Usage Example

### Refactoring Existing Google Drive Sync

**Before:**
```python
# google_client.py - Mixed concerns, brittle regex
async def sync_google_docs(db: Session, folder_ids: list[str]):
    # ... fetch documents
    for doc in documents:
        # Extract customer with regex
        account = extract_customer_regex(doc['text'])

        # Create feedback directly
        feedback = Feedback(
            source=FeedbackSource.gdoc,
            text=doc['text'],  # Whole document!
            account=account,
            # No embedding generated here
        )
        db.add(feedback)
```

**After:**
```python
# Using unified ingestion service
from apps.api.services.ingestion import FeedbackIngestionService
from apps.api.services.ingestion.extractors import GDriveExtractor

async def sync_google_docs(db: Session, folder_ids: list[str]):
    ingestion_service = FeedbackIngestionService(db)
    extractor = GDriveExtractor()

    # ... fetch documents
    raw_items = []
    for doc in documents:
        raw_items.append({
            "text": doc['text'],
            "source_id": doc['id'],
            "title": doc['name'],
            "url": doc['webViewLink'],
            "owner": doc['owners'][0]['emailAddress'],
            "created_at": doc['createdTime'],
        })

    # Batch ingest with automatic chunking and embedding
    feedback_items, stats = ingestion_service.ingest_batch(
        source=FeedbackSource.gdoc,
        raw_items=raw_items,
        extractor=extractor,
        batch_size=10
    )

    logger.info(
        "Google Drive sync completed",
        chunks_created=stats.chunks_created,
        embeddings_generated=stats.embeddings_generated,
        errors=stats.errors
    )
```

## Benefits

### 1. **Consistency**
- All sources use same pipeline
- Customer extraction follows same patterns
- Embeddings always generated immediately

### 2. **Maintainability**
- Source-specific logic isolated in extractors
- Easy to add new sources (just implement `ContentExtractor`)
- Common functionality in one place (embedding, normalization)

### 3. **Quality**
- Confidence scores track extraction reliability
- Statistics help monitor data quality
- Warnings surface issues automatically

### 4. **Performance**
- Batch embedding generation (faster than one-by-one)
- Reuses existing feedback records (upsert logic)
- Lazy-loads embedding model

### 5. **Flexibility**
- Can swap extractors (e.g., regex → LLM)
- Can add preprocessing steps
- Can customize chunking per source

## Configuration & Extraction Methods

### Extraction Method Priority

Each extractor tries multiple strategies in order of reliability:

| Method | Confidence | Use Case |
|--------|-----------|----------|
| `structured_field` | 0.9 | Jira custom fields, CRM data |
| `regex_pattern` | 0.8 | "customer Acme Corp" in text |
| `regex_participant` | 0.7 | Transcript participant info |
| `channel_name` | 0.7 | Slack channel patterns |
| `meeting_topic` | 0.6 | Zoom meeting topic |
| `reporter_domain` | 0.5 | Email domain extraction |
| `project_name` | 0.4 | Jira project fallback |
| `fallback_owner` | 0.3 | File owner email |
| `fallback_unknown` | 0.1 | No extraction possible |

### Monitoring Low-Confidence Extractions

```python
# Service automatically logs warnings for confidence < 0.7
feedback_items, stats = service.ingest_item(...)

if stats.warnings:
    for warning in stats.warnings:
        print(f"⚠️  {warning}")

# Example output:
# ⚠️  Low confidence customer extraction: rohitsaraff33
#     (confidence=0.30, method=fallback_owner)
```

## Next Steps

### Phase 1: Refactor Existing Sources ⏳

1. **Google Drive** (`apps/api/services/google_client.py`)
   - Replace `sync_google_docs()` to use `FeedbackIngestionService`
   - Remove old customer extraction regex
   - Delete `chunk_google_transcripts.py` script (now built-in)

2. **Zoom** (`apps/api/services/zoom_client.py`)
   - Update `sync_zoom_recordings()` to use `FeedbackIngestionService`
   - Enhance `ZoomExtractor` with VTT parsing

3. **Slack** (when implemented)
   - Use `SlackExtractor` from the start
   - Configure channel patterns for customer extraction

4. **Jira** (when implemented)
   - Map custom fields to customer info
   - Use `JiraExtractor` for ingestion

### Phase 2: Enhanced Extraction 🚀

1. **LLM-Based Extraction** (Recommended!)
   ```python
   class LLMExtractor(ContentExtractor):
       """Use Claude/GPT for intelligent extraction."""

       async def extract_customer_and_chunks(self, content: str):
           # Single LLM call extracts both customer + feedback items
           # Much more reliable than regex!
   ```

2. **Customer Entity Resolution**
   - Create `Customer` table with canonical names
   - Build alias mapping ("TechFlow" → "TechFlow Inc")
   - Fuzzy matching for variations
   - CRM sync for validation

3. **Confidence Tuning**
   - Track extraction accuracy over time
   - Adjust confidence thresholds per method
   - Add human-in-the-loop for low-confidence cases

### Phase 3: Advanced Features 🎯

1. **Automatic Categorization**
   - Tag feedback as "bug", "feature_request", "complaint"
   - Use LLM or keyword classifier

2. **Quality Monitoring Dashboard**
   - Show extraction confidence distribution
   - Flag suspicious extractions
   - Track customer name variations

3. **Preprocessing Pipeline**
   - Text cleaning (remove PII, format normalization)
   - Language detection
   - Duplicate detection

## File Structure

```
apps/api/services/ingestion/
├── __init__.py                 # Public exports
├── base.py                     # Abstract classes, data models
├── service.py                  # FeedbackIngestionService
└── extractors/
    ├── __init__.py
    ├── gdrive.py              # ✅ Full implementation
    ├── zoom.py                # ⚠️ Basic implementation
    ├── slack.py               # ⚠️ Basic implementation
    └── jira.py                # ⚠️ Basic implementation
```

## Testing

### Unit Test Example

```python
from apps.api.services.ingestion import FeedbackIngestionService
from apps.api.services.ingestion.extractors import GDriveExtractor

def test_gdrive_customer_extraction():
    extractor = GDriveExtractor()

    raw_content = {
        "text": "Below is a call recording between Marcus Johnson, "
                "a product manager at PulseDrive and their customer "
                "Zenith Solutions to capture feedback...",
        "source_id": "doc_123",
        "title": "Zenith Solutions Feedback",
    }

    customer_info = extractor.extract_customer(raw_content)

    assert customer_info.name == "Zenith Solutions"
    assert customer_info.confidence > 0.7
    assert customer_info.extraction_method == "regex_pattern"

def test_gdrive_transcript_chunking():
    extractor = GDriveExtractor()

    raw_content = {
        "text": """
00:00:10.000 --> 00:00:15.000
Rachel Park: The dashboard loading times are really frustrating our team.

00:00:20.000 --> 00:00:25.000
Marcus Johnson: Thanks for that feedback, let me look into it.
        """,
        "source_id": "doc_123",
        "title": "Customer Transcript",
    }

    chunks = extractor.chunk_content(raw_content)

    # Should extract Rachel's statement (has feedback keyword "frustrating")
    # Should skip Marcus's statement (PulseDrive employee)
    assert len(chunks) == 1
    assert "Rachel Park" in chunks[0].text
    assert "frustrating" in chunks[0].text
```

## Migration Guide

### For Existing Deployments

1. **No immediate action required** - Old code still works
2. **Recommended**: Refactor one source at a time
3. **After refactoring**: Run `generate_embeddings.py` to ensure all feedback has embeddings
4. **Monitor**: Check extraction confidence in logs

### Breaking Changes

None! This is additive architecture. Existing ingestion code continues to work.

## FAQ

**Q: Do I need to refactor all sources immediately?**
A: No. Start with the most problematic source (likely Google Drive transcripts) and refactor others gradually.

**Q: Can I use different extractors for the same source?**
A: Yes! For example, you could use `LLMExtractor` for some Google Drive docs and `GDriveExtractor` for others.

**Q: What if customer extraction fails?**
A: Falls back to "Unknown" with low confidence (0.1). You can review low-confidence extractions in logs.

**Q: How do I add a new data source (e.g., CRM)?**
A: Implement a `CRMExtractor` class, then use `FeedbackIngestionService` to ingest.

**Q: Can I customize chunking logic?**
A: Yes! Override `chunk_content()` and `should_chunk()` in your extractor.

## Summary

✅ **Implemented:**
- Unified ingestion pipeline
- 4 source extractors (GDrive fully functional, others basic)
- Automatic embedding generation
- Customer normalization
- Confidence tracking
- Batch processing
- Error handling & statistics

⏳ **Next Steps:**
- Refactor existing source sync code
- Enhance Zoom/Slack/Jira extractors
- Add LLM-based extraction
- Build customer entity resolution

🎯 **Impact:**
- Consistent customer extraction across all sources
- Automatic transcript chunking (no manual scripts!)
- Better data quality with confidence tracking
- Easier to add new sources
- Foundation for future enhancements (LLM extraction, entity resolution)
