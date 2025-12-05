"""Clustering service using HDBSCAN."""

import logging
from dataclasses import dataclass
from typing import List, Optional

try:
    import hdbscan
    HAS_HDBSCAN = True
except ImportError:
    HAS_HDBSCAN = False
    from sklearn.cluster import KMeans

import numpy as np
from keybert import KeyBERT

from apps.api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ClusterResult:
    """Result of clustering operation."""

    cluster_id: int
    label: str
    description: Optional[str]
    centroid: List[float]
    member_indices: List[int]
    member_confidences: List[float]


class ClusteringService:
    """Service for clustering feedback using HDBSCAN."""

    def __init__(self):
        """Initialize clustering service."""
        self.keybert = KeyBERT()
        logger.info("Clustering service initialized")

    def cluster_embeddings(
        self,
        embeddings: List[List[float]],
        texts: List[str],
        min_cluster_size: Optional[int] = None,
        min_samples: Optional[int] = None,
    ) -> List[ClusterResult]:
        """
        Cluster embeddings using HDBSCAN and generate labels.

        Args:
            embeddings: List of embedding vectors
            texts: Corresponding texts for labeling
            min_cluster_size: Minimum size for a cluster (default from config)
            min_samples: Minimum samples for core points (default from config)

        Returns:
            List of ClusterResult objects (excluding noise cluster -1)
        """
        if len(embeddings) < settings.clustering_min_feedback_count:
            logger.warning(
                f"Not enough feedback for clustering: {len(embeddings)} < {settings.clustering_min_feedback_count}"
            )
            return []

        min_cluster_size = min_cluster_size or settings.hdbscan_min_cluster_size
        min_samples = min_samples or settings.hdbscan_min_samples

        logger.info(f"Clustering {len(embeddings)} embeddings...")

        # Convert to numpy array
        X = np.array(embeddings)

        # Run clustering
        if HAS_HDBSCAN:
            # Use HDBSCAN (preferred)
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=min_samples,
                metric="cosine",
                cluster_selection_method="eom",
            )
            cluster_labels = clusterer.fit_predict(X)
            probabilities = clusterer.probabilities_
        else:
            # Fallback to KMeans
            logger.warning("HDBSCAN not available, using KMeans as fallback")
            n_clusters = max(3, min(10, len(embeddings) // 10))  # Estimate clusters
            clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = clusterer.fit_predict(X)
            # Approximate probabilities for KMeans
            distances = clusterer.transform(X)
            min_distances = distances.min(axis=1)
            probabilities = 1 / (1 + min_distances)  # Convert distance to probability-like score

        logger.info(f"Found {cluster_labels.max() + 1} clusters (excluding noise)")

        # Build cluster results
        results = []
        for cluster_id in range(cluster_labels.max() + 1):
            # Get members of this cluster
            mask = cluster_labels == cluster_id
            member_indices = np.where(mask)[0].tolist()
            member_confidences = probabilities[mask].tolist()
            cluster_embeddings = X[mask]
            cluster_texts = [texts[i] for i in member_indices]

            # Compute centroid
            centroid = np.mean(cluster_embeddings, axis=0).tolist()

            # Generate label
            label = self._generate_label(cluster_texts)

            # Optional: Generate description (could use LLM here)
            description = None

            results.append(
                ClusterResult(
                    cluster_id=cluster_id,
                    label=label,
                    description=description,
                    centroid=centroid,
                    member_indices=member_indices,
                    member_confidences=member_confidences,
                )
            )

        return results

    def _generate_label(self, texts: List[str]) -> str:
        """
        Generate a label for a cluster using KeyBERT.

        Args:
            texts: List of texts in the cluster

        Returns:
            Generated label (comma-separated keywords)
        """
        # Combine all texts
        combined_text = " ".join(texts[:20])  # Use first 20 to avoid being too long

        try:
            # Extract keywords
            keywords = self.keybert.extract_keywords(
                combined_text,
                keyphrase_ngram_range=(1, 3),
                stop_words="english",
                top_n=5,  # Get more keywords so we can filter and still have enough
                use_maxsum=True,
                nr_candidates=20,
            )

            # Format as label - extract just the keyword strings
            if keywords:
                keyword_strings = [kw[0] for kw in keywords]
                # Filter out names before creating label
                filtered_keywords = self._filter_names_from_keywords(keyword_strings)

                if filtered_keywords:
                    # Use top 3 filtered keywords
                    label = ", ".join(filtered_keywords[:3])
                    return label.title()
                else:
                    return "Feature Request"
            else:
                return "Unlabeled Theme"

        except Exception as e:
            logger.warning(f"Failed to generate label with KeyBERT: {e}")
            return "Unlabeled Theme"

    def refine_label_with_llm(self, label: str, sample_texts: List[str]) -> str:
        """
        Generate an actionable insight title using LLM.

        This creates business-focused, actionable titles instead of keyword lists.

        Args:
            label: Initial label from KeyBERT
            sample_texts: Sample texts from the cluster

        Returns:
            Actionable insight title
        """
        if not settings.openai_api_key:
            logger.info("No OpenAI API key, using fallback title generation")
            return self._generate_actionable_title_fallback(label, sample_texts)

        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)

            prompt = f"""Given these product feedback quotes:

{chr(10).join(f"- {text[:200]}" for text in sample_texts[:5])}

Generate a concise, actionable insight title (MAX 6 words) that:
1. Focuses on the business impact or customer need
2. Uses active voice and clear language
3. Must be under 45 characters total
4. Avoids generic phrases like "requires immediate attention"

Good examples:
- "SSO/SAML blocks enterprise deals"
- "Mobile crashes drive churn"
- "Export performance affects workflows"
- "Dark mode frequently requested"

Bad examples:
- "Devices & Frontend Refactor requires immediate attention" (too long!)
- "Tool Maxes Like & Segment Data Analysis requires..." (too long!)

Return ONLY the title (under 45 chars), nothing else."""

            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a senior product manager creating actionable insight titles from customer feedback."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=50,
                temperature=0.7,
            )

            refined_label = response.choices[0].message.content.strip()
            # Remove quotes if LLM added them
            refined_label = refined_label.strip('"\'')
            logger.info(f"Generated actionable title: {refined_label}")
            return refined_label

        except Exception as e:
            logger.warning(f"Failed to generate title with LLM: {e}")
            return self._generate_actionable_title_fallback(label, sample_texts)

    def _filter_names_from_keywords(self, keywords: List[str]) -> List[str]:
        """
        Filter out customer names, person names, and company names from keywords.

        Args:
            keywords: List of keyword strings

        Returns:
            Filtered keywords without names
        """
        # Common business suffixes that indicate company names
        company_suffixes = ['llc', 'inc', 'corp', 'ltd', 'co', 'company', 'industries', 'solutions']

        # Common technical/product terms that should be kept (lowercase for comparison)
        keep_terms = [
            'api', 'sso', 'saml', 'oauth', 'auth', 'login', 'security', 'export', 'import',
            'csv', 'excel', 'pdf', 'mobile', 'dashboard', 'analytics', 'reporting', 'search',
            'filter', 'webhook', 'integration', 'data', 'user', 'admin', 'access', 'permissions',
            'dark mode', 'theme', 'ui', 'ux', 'design', 'performance', 'loading', 'speed',
            'error', 'handling', 'batch', 'operations', 'compliance', 'requirements', 'file',
            'upload', 'download', 'timeout', 'limit', 'size', 'format', 'validation', 'notification',
            'email', 'sync', 'backup', 'restore', 'archive', 'delete', 'edit', 'create', 'update',
            'view', 'list', 'detail', 'summary', 'overview', 'settings', 'configuration', 'setup',
            'devices', 'providers', 'registration', 'delivery', 'plan', 'upgrades', 'segment',
            'analysis', 'tool', 'maxes', 'priorities', 'implement', 'need', 'visibility', 'usage',
            'failing', 'optimize', 'increase', 'small', 'like', 'okta', 'identity', 'q1', 'q2',
            'q3', 'q4', 'direct', 'exports', 'users', 'chang', 'robert'
        ]

        # Common first/last names to filter (lowercase)
        common_names = [
            'nguyen', 'robert', 'chang', 'techflow', 'smallbiz', 'rivera', 'smith', 'johnson',
            'williams', 'brown', 'jones', 'garcia', 'miller', 'davis', 'rodriguez', 'martinez',
            'hernandez', 'lopez', 'gonzalez', 'wilson', 'anderson', 'thomas', 'taylor', 'moore',
            'jackson', 'martin', 'lee', 'perez', 'thompson', 'white', 'harris', 'kim', 'chen',
            'wang', 'liu', 'singh', 'kumar', 'patel'
        ]

        # Non-descriptive words to filter (lowercase)
        generic_words = [
            'yes', 'no', 'weeks', 'days', 'months', 'years', 'concern', 'million', 'works',
            'says', 'told', 'asked', 'mentioned', 'discussed', 'screens', 'wide', 'large',
            'small', 'medium', 'big', 'thing', 'things', 'stuff', 'way', 'ways'
        ]

        filtered = []
        for kw in keywords:
            kw_lower = kw.lower().strip()

            # Skip empty keywords
            if not kw_lower:
                continue

            # Check if it's a company name (contains business suffix)
            has_company_suffix = any(suffix in kw_lower.split() for suffix in company_suffixes)
            if has_company_suffix:
                continue

            # Split multi-word keywords and filter out names
            words = kw_lower.split()

            # Filter out common names and generic words from words
            filtered_words = []
            for word in words:
                # Skip if it's a common person name
                if word in common_names:
                    continue
                # Skip if it's a generic non-descriptive word
                if word in generic_words:
                    continue
                # Skip if it's a number (like "60", "90", etc.)
                if word.isdigit():
                    continue
                # Skip single capitalized words that aren't technical terms
                if len(words) == 1 and kw[0].isupper() and word not in keep_terms:
                    continue
                filtered_words.append(word)

            # If all words were filtered out, skip this keyword
            if not filtered_words:
                continue

            # Reconstruct the keyword from filtered words
            reconstructed = ' '.join(filtered_words).title()

            # Only add if it's not just a number or very short
            if len(reconstructed) > 2 and not reconstructed.isdigit():
                filtered.append(reconstructed)

        return filtered

    def _generate_actionable_title_fallback(self, label: str, sample_texts: List[str]) -> str:
        """
        Generate actionable title without LLM (fallback).

        Uses templates to create business-focused titles.
        """
        # Extract and filter keywords to remove names
        keywords = [kw.strip() for kw in label.split(',')]
        filtered_keywords = self._filter_names_from_keywords(keywords)

        # Use first 2-3 filtered keywords
        if not filtered_keywords:
            # Fallback if all keywords were filtered out
            filtered_keywords = ['Feature Request']

        main_keywords = filtered_keywords[:2]
        main_concept = ' & '.join(main_keywords).title()

        # Detect patterns to choose appropriate template
        label_lower = label.lower()

        # Pattern detection - keep titles under 45 chars
        if any(word in label_lower for word in ['sso', 'saml', 'auth', 'login', 'security']):
            return f"{main_concept} blocks enterprise deals"
        elif any(word in label_lower for word in ['export', 'import', 'csv', 'excel', 'pdf']):
            return f"{main_concept} affects workflows"
        elif any(word in label_lower for word in ['mobile', 'crash', 'responsive', 'tablet']):
            return f"{main_concept} impacts mobile users"
        elif any(word in label_lower for word in ['search', 'filter', 'query', 'find']):
            return f"{main_concept} needs improvement"
        elif any(word in label_lower for word in ['dark mode', 'theme', 'ui', 'design']):
            return f"{main_concept} frequently requested"
        elif any(word in label_lower for word in ['api', 'webhook', 'integration']):
            return f"{main_concept} in high demand"
        elif any(word in label_lower for word in ['performance', 'slow', 'loading', 'speed']):
            return f"{main_concept} frustrates users"
        elif any(word in label_lower for word in ['dashboard', 'analytics', 'reporting']):
            return f"{main_concept} needs optimization"
        else:
            return f"{main_concept} needs attention"


# Global instance
_clustering_service: ClusteringService | None = None


def get_clustering_service() -> ClusteringService:
    """Get or create the global clustering service instance."""
    global _clustering_service
    if _clustering_service is None:
        _clustering_service = ClusteringService()
    return _clustering_service
