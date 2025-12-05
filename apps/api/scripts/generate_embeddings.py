"""Generate embeddings for feedback items that don't have them."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sentence_transformers import SentenceTransformer

from apps.api.database import get_db_context
from apps.api.models import Feedback


def main():
    """Generate embeddings for feedback without embeddings."""
    # Load embedding model
    print("Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    with get_db_context() as db:
        # Find feedback without embeddings
        feedback_without_embeddings = (
            db.query(Feedback)
            .filter(Feedback.embedding.is_(None))
            .all()
        )

        if not feedback_without_embeddings:
            print("✅ All feedback items already have embeddings")
            return

        print(f"Found {len(feedback_without_embeddings)} feedback items without embeddings")

        # Generate embeddings in batches
        texts = [f.text for f in feedback_without_embeddings]
        print("Generating embeddings...")
        embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

        # Update feedback with embeddings
        for feedback, embedding in zip(feedback_without_embeddings, embeddings):
            feedback.embedding = embedding.tolist()

        db.commit()
        print(f"✅ Generated embeddings for {len(feedback_without_embeddings)} feedback items")


if __name__ == "__main__":
    main()
