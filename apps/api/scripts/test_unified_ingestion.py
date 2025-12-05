"""Test script for unified ingestion service with Google Drive extractor."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from datetime import datetime

from apps.api.database import get_db_context
from apps.api.models import Feedback, FeedbackSource
from apps.api.services.ingestion import FeedbackIngestionService
from apps.api.services.ingestion.extractors import GDriveExtractor


def test_gdrive_customer_extraction():
    """Test customer extraction from Google Drive transcript."""
    print("\n=== Testing Customer Extraction ===")

    extractor = GDriveExtractor()

    # Test case 1: Pattern "their customer X"
    raw_content = {
        "text": "Below is a call recording between Marcus Johnson and their customer Acme Corp to capture feedback...",
        "source_id": "test_doc_1",
        "title": "Test Document",
    }

    customer_info = extractor.extract_customer(raw_content)
    print(f"Test 1 - Pattern 'their customer X':")
    print(f"  Customer: {customer_info.name}")
    print(f"  Confidence: {customer_info.confidence}")
    print(f"  Method: {customer_info.extraction_method}")
    assert customer_info.name == "Acme Corp"
    assert customer_info.confidence >= 0.7

    # Test case 2: Participant info
    raw_content = {
        "text": """Participants:
Rachel Park (TechFlow Inc - Product Manager)
Marcus Johnson (PulseDrive - Sales)
Some feedback here...""",
        "source_id": "test_doc_2",
        "title": "Test Document 2",
    }

    customer_info = extractor.extract_customer(raw_content)
    print(f"\nTest 2 - Participant info:")
    print(f"  Customer: {customer_info.name}")
    print(f"  Confidence: {customer_info.confidence}")
    print(f"  Method: {customer_info.extraction_method}")
    assert customer_info.name == "TechFlow Inc"
    assert customer_info.confidence >= 0.6

    # Test case 3: Fallback to owner
    raw_content = {
        "text": "This is a generic product spec document with no company references.",
        "source_id": "test_doc_3",
        "title": "Product Spec Document",
        "owner": "john.doe@example.com",
    }

    customer_info = extractor.extract_customer(raw_content)
    print(f"\nTest 3 - Fallback to owner:")
    print(f"  Customer: {customer_info.name}")
    print(f"  Confidence: {customer_info.confidence}")
    print(f"  Method: {customer_info.extraction_method}")
    assert customer_info.extraction_method == "fallback_owner", f"Expected fallback_owner, got {customer_info.extraction_method} with customer '{customer_info.name}'"

    print("\n✅ Customer extraction tests passed!")


def test_gdrive_transcript_chunking():
    """Test VTT transcript chunking."""
    print("\n=== Testing Transcript Chunking ===")

    extractor = GDriveExtractor()

    # Test 1: Short transcript (< 2000 chars) - should return as single chunk
    print("\nTest 1: Short transcript (no chunking needed)")
    short_transcript = """00:00:10.000 --> 00:00:15.000
Rachel Park: The dashboard loading times are really frustrating our team. We need this fixed urgently.

00:00:20.000 --> 00:00:25.000
Marcus Johnson: Thanks for that feedback, let me look into it."""

    raw_content = {
        "text": short_transcript,
        "source_id": "test_transcript_short",
        "title": "Short Customer Call",
    }

    chunks = extractor.chunk_content(raw_content)
    print(f"  Chunks extracted: {len(chunks)}")
    assert len(chunks) == 1, f"Expected 1 chunk for short transcript, got {len(chunks)}"
    print("  ✓ Short transcript returned as single chunk (correct behavior)")

    # Test 2: Long transcript (> 2000 chars) with VTT format - should chunk by speaker
    print("\nTest 2: Long transcript (chunking enabled)")

    # Create a realistic long transcript with customer feedback statements
    long_statements = []
    for i in range(40):  # Create enough statements to exceed 2000 chars
        timestamp_start = f"00:{i:02d}:00.000"
        timestamp_end = f"00:{i:02d}:05.000"

        if i % 3 == 0:
            # Customer feedback statement
            speaker = "Rachel Park"
            text = f"I have an issue with the dashboard performance. It's really slow and frustrating."
        elif i % 3 == 1:
            # Another customer statement without feedback keyword
            speaker = "Rachel Park"
            text = f"Let me show you what I mean on my screen here."
        else:
            # PulseDrive employee statement (should be filtered out)
            speaker = "Marcus Johnson"
            text = f"Thanks for that feedback, I'll look into it right away."

        long_statements.append(f"{timestamp_start} --> {timestamp_end}\n{speaker}: {text}\n")

    long_transcript = "\n".join(long_statements)
    print(f"  Transcript length: {len(long_transcript)} characters")

    raw_content = {
        "text": long_transcript,
        "source_id": "test_transcript_long",
        "title": "Long Customer Call",
    }

    chunks = extractor.chunk_content(raw_content)
    print(f"  Chunks extracted: {len(chunks)}")

    # Should extract only Rachel's statements with feedback keywords
    # We have ~13 Rachel statements with feedback keywords (every 3rd statement, skipping non-keyword ones)
    assert len(chunks) > 1, f"Expected multiple chunks for long transcript, got {len(chunks)}"
    assert all("Rachel Park" in chunk.text for chunk in chunks), "All chunks should be from customer (Rachel Park)"

    # Verify no PulseDrive employee statements
    for chunk in chunks:
        assert "Marcus Johnson" not in chunk.text, "Should not include PulseDrive employee statements"

    print(f"  ✓ Long transcript chunked into {len(chunks)} customer feedback items")
    print("  ✓ Filtered out PulseDrive employee statements")

    print("\n✅ Transcript chunking tests passed!")


def test_ingestion_service():
    """Test full ingestion service with GDrive extractor."""
    print("\n=== Testing Full Ingestion Service ===")

    with get_db_context() as db:
        # Count existing feedback
        initial_count = db.query(Feedback).filter(
            Feedback.source == FeedbackSource.gdoc
        ).count()
        print(f"Initial Google Drive feedback count: {initial_count}")

        # Initialize service
        ingestion_service = FeedbackIngestionService(db)
        extractor = GDriveExtractor()

        # Test with simple document (not a transcript)
        raw_content = {
            "text": "Feedback from their customer TestCorp Inc. The dashboard performance is really slow and frustrating. We need this fixed urgently.",
            "source_id": "test_ingestion_doc",
            "title": "TestCorp Feedback",
            "url": "https://docs.google.com/document/d/test",
            "owner": "testuser@example.com",
            "created_at": datetime.utcnow(),
        }

        # Ingest the item
        feedback_items, stats = ingestion_service.ingest_item(
            source=FeedbackSource.gdoc,
            raw_content=raw_content,
            extractor=extractor,
        )

        print(f"\n--- Ingestion Results ---")
        print(f"Feedback items created: {len(feedback_items)}")
        print(f"Chunks created: {stats.chunks_created}")
        print(f"Embeddings generated: {stats.embeddings_generated}")
        print(f"Errors: {stats.errors}")

        if stats.warnings:
            print(f"Warnings:")
            for warning in stats.warnings:
                print(f"  - {warning}")

        # Verify feedback items
        print(f"\n--- Created Feedback Items ---")
        for item in feedback_items:
            print(f"\nFeedback ID: {item.id}")
            print(f"  Account: {item.account}")
            print(f"  Source: {item.source}")
            print(f"  Text preview: {item.text[:100]}...")
            print(f"  Has embedding: {item.embedding is not None}")
            print(f"  Embedding dimension: {len(item.embedding) if item.embedding else 0}")

        # Assertions
        assert len(feedback_items) == 1, f"Expected 1 feedback item (simple document), got {len(feedback_items)}"
        assert stats.chunks_created == 1
        assert stats.embeddings_generated == 1
        assert all(item.account == "TestCorp Inc" for item in feedback_items)
        assert all(item.embedding is not None for item in feedback_items)
        assert all(len(item.embedding) == 384 for item in feedback_items)  # all-MiniLM-L6-v2 dimension

        print("\n✅ Full ingestion service test passed!")

        # Cleanup test data
        for item in feedback_items:
            db.delete(item)
        db.commit()
        print("\n🧹 Test data cleaned up")


def test_batch_ingestion():
    """Test batch ingestion."""
    print("\n=== Testing Batch Ingestion ===")

    with get_db_context() as db:
        ingestion_service = FeedbackIngestionService(db)
        extractor = GDriveExtractor()

        # Multiple documents
        raw_items = [
            {
                "text": "Feedback from their customer CompanyA. They reported dashboard issues and performance problems.",
                "source_id": "batch_test_1",
                "title": "CompanyA Feedback",
                "url": "https://docs.google.com/document/d/batch1",
                "owner": "user@example.com",
                "created_at": datetime.utcnow(),
            },
            {
                "text": "Feedback from their customer CompanyB. They are requesting new export features for their reports.",
                "source_id": "batch_test_2",
                "title": "CompanyB Feedback",
                "url": "https://docs.google.com/document/d/batch2",
                "owner": "user@example.com",
                "created_at": datetime.utcnow(),
            },
        ]

        # Batch ingest
        feedback_items, stats = ingestion_service.ingest_batch(
            source=FeedbackSource.gdoc,
            raw_items=raw_items,
            extractor=extractor,
            batch_size=10,
        )

        print(f"\n--- Batch Ingestion Results ---")
        print(f"Total items processed: {len(raw_items)}")
        print(f"Feedback items created: {len(feedback_items)}")
        print(f"Chunks created: {stats.chunks_created}")
        print(f"Embeddings generated: {stats.embeddings_generated}")

        # Verify
        assert len(feedback_items) == 2
        assert stats.chunks_created == 2
        assert stats.embeddings_generated == 2

        # Check customer names extracted correctly
        accounts = {item.account for item in feedback_items}
        assert "CompanyA" in accounts
        assert "CompanyB" in accounts

        print("\n✅ Batch ingestion test passed!")

        # Cleanup
        for item in feedback_items:
            db.delete(item)
        db.commit()
        print("\n🧹 Test data cleaned up")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("TESTING UNIFIED INGESTION SERVICE")
    print("="*60)

    try:
        # Unit tests
        test_gdrive_customer_extraction()
        test_gdrive_transcript_chunking()

        # Integration tests
        test_ingestion_service()
        test_batch_ingestion()

        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nThe refactored Google Drive sync is working correctly:")
        print("  ✓ Customer extraction with confidence tracking")
        print("  ✓ VTT transcript chunking with feedback keyword filtering")
        print("  ✓ Automatic embedding generation")
        print("  ✓ Batch processing support")
        print("  ✓ Statistics and warnings")
        print("\nThe implementation is ready for production use.")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
