"""
AI Summarization
================

AI-powered document summarization.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)


@dataclass
class Summary:
    """AI-generated summary"""
    summary_id: str
    entity_id: str
    entity_type: str
    
    # Summaries at different lengths
    short_summary: str  # 1-2 sentences
    medium_summary: str  # 1 paragraph
    long_summary: str  # Multiple paragraphs
    
    # Key points
    key_points: List[str] = field(default_factory=list)
    takeaways: List[str] = field(default_factory=list)
    
    # Quality metrics
    confidence: float = 0.0  # How confident is the AI in this summary
    coverage: float = 0.0  # How much of the original is covered
    
    # Metadata
    generated_at: float = field(default_factory=time.time)
    model: str = "generic"
    tokens_used: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "entity_id": self.entity_id,
            "short_summary": self.short_summary,
            "key_points": self.key_points,
            "confidence": self.confidence,
            "generated_at": self.generated_at,
        }


class Summarizer:
    """
    AI-powered document summarization.
    
    In production, this would integrate with an LLM.
    For now, it provides a framework with extractive summarization.
    """
    
    def __init__(self):
        self._summary_cache: Dict[str, Summary] = {}
        self._llm_provider: Optional[Callable] = None
    
    def set_llm_provider(self, provider: Callable) -> None:
        """Set an LLM provider for generative summarization"""
        self._llm_provider = provider
    
    def summarize(
        self,
        content: str,
        entity_id: str,
        entity_type: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Summary:
        """Generate a summary of the content"""
        
        # Check cache
        cache_key = f"{entity_type}:{entity_id}"
        if cache_key in self._summary_cache:
            return self._summary_cache[cache_key]
        
        # Generate summaries
        short = self._generate_short_summary(content)
        medium = self._generate_medium_summary(content)
        long = self._generate_long_summary(content)
        
        key_points = self._extract_key_points(content)
        takeaways = self._extract_takeaways(content)
        
        # Calculate quality metrics
        confidence = self._calculate_confidence(content, medium)
        coverage = self._calculate_coverage(content, long)
        
        summary = Summary(
            summary_id=str(uuid.uuid4()),
            entity_id=entity_id,
            entity_type=entity_type,
            short_summary=short,
            medium_summary=medium,
            long_summary=long,
            key_points=key_points,
            takeaways=takeaways,
            confidence=confidence,
            coverage=coverage,
        )
        
        self._summary_cache[cache_key] = summary
        return summary
    
    def _generate_short_summary(self, content: str) -> str:
        """Generate a short 1-2 sentence summary"""
        # Extract first sentence(s)
        sentences = self._split_sentences(content)
        
        if not sentences:
            return ""
        
        # Try to get first 1-2 sentences
        short = sentences[0]
        if len(short) > 200 and len(sentences) > 1:
            short = sentences[1]
        
        # Truncate if too long
        if len(short) > 300:
            short = short[:297] + "..."
        
        return short
    
    def _generate_medium_summary(self, content: str) -> str:
        """Generate a medium 1-paragraph summary"""
        sentences = self._split_sentences(content)
        
        if not sentences:
            return ""
        
        # Select most important sentences
        # Simple extractive: first sentence + sentences with key terms
        key_terms = self._extract_key_terms(content)
        
        selected = [sentences[0]] if sentences else []
        
        for sentence in sentences[1:]:
            if len(selected) >= 3:
                break
            
            sentence_lower = sentence.lower()
            if any(term in sentence_lower for term in key_terms[:5]):
                selected.append(sentence)
        
        return " ".join(selected[:3])
    
    def _generate_long_summary(self, content: str) -> str:
        """Generate a longer multi-paragraph summary"""
        sentences = self._split_sentences(content)
        
        if not sentences:
            return ""
        
        # Group into paragraphs (simplified)
        paragraphs = []
        current_para = []
        
        for sentence in sentences:
            current_para.append(sentence)
            if len(" ".join(current_para)) > 300:
                paragraphs.append(" ".join(current_para))
                current_para = []
        
        if current_para:
            paragraphs.append(" ".join(current_para))
        
        # Return first 3 paragraphs or all if less
        return "\n\n".join(paragraphs[:3])
    
    def _extract_key_points(self, content: str) -> List[str]:
        """Extract key points from content"""
        sentences = self._split_sentences(content)
        
        if not sentences:
            return []
        
        key_terms = set(self._extract_key_terms(content))
        
        # Score sentences by key term density
        scored = []
        for sentence in sentences:
            score = sum(1 for term in key_terms if term in sentence.lower())
            scored.append((sentence, score))
        
        # Sort by score and select top points
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Deduplicate and select
        selected = []
        seen_phrases = set()
        
        for sentence, score in scored:
            # Skip very short sentences
            if len(sentence) < 50:
                continue
            
            # Skip very similar sentences
            short_phrase = sentence[:50].lower()
            if short_phrase in seen_phrases:
                continue
            
            seen_phrases.add(short_phrase)
            selected.append(sentence)
            
            if len(selected) >= 5:
                break
        
        return selected[:5]
    
    def _extract_takeaways(self, content: str) -> List[str]:
        """Extract actionable takeaways"""
        takeaways = []
        
        content_lower = content.lower()
        
        # Look for conclusion indicators
        conclusion_patterns = [
            r'in\s+conclusion[,\s]+(.+?)(?:\.|$)',
            r'to\s+sum\s+up[,\s]+(.+?)(?:\.|$)',
            r'key\s+takeaway[s]?[,\s]*:?(.+?)(?:\.|$)',
            r'most\s+important[ly]?[,\s]+(.+?)(?:\.|$)',
        ]
        
        sentences = self._split_sentences(content)
        
        for pattern in conclusion_patterns:
            import re
            matches = re.findall(pattern, content_lower)
            for match in matches:
                takeaways.append(match.strip())
        
        # If no explicit takeaways, use last sentences
        if not takeaways:
            for sentence in sentences[-3:]:
                if len(sentence) > 50:
                    takeaways.append(sentence)
        
        return takeaways[:3]
    
    def _extract_key_terms(self, content: str) -> List[str]:
        """Extract key terms from content"""
        # Common stopwords
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'can', 'this', 'that',
            'these', 'those', 'it', 'its', 'they', 'them', 'their', 'we', 'our',
            'you', 'your', 'he', 'she', 'his', 'her', 'i', 'me', 'my',
        }
        
        # Tokenize
        import re
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
        
        # Count frequencies
        freq = {}
        for word in words:
            if word not in stopwords:
                freq[word] = freq.get(word, 0) + 1
        
        # Sort by frequency
        sorted_terms = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        
        # Return top terms
        return [term for term, count in sorted_terms[:20]]
    
    def _split_sentences(self, content: str) -> List[str]:
        """Split content into sentences"""
        import re
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', content)
        return [s.strip() for s in sentences if s.strip()]
    
    def _calculate_confidence(self, content: str, summary: str) -> float:
        """Calculate confidence in the summary"""
        # Simple heuristic: coverage and length ratio
        if not content or not summary:
            return 0.0
        
        coverage = len(summary) / len(content)
        
        # Penalize very short summaries
        if len(summary) < 100:
            coverage *= 0.7
        
        # Ideal ratio is around 0.1-0.3
        if 0.1 <= coverage <= 0.5:
            return min(1.0, coverage * 2)
        
        return max(0.0, min(1.0, coverage * 1.5))
    
    def _calculate_coverage(self, content: str, summary: str) -> float:
        """Calculate how much of the original is covered"""
        if not content:
            return 0.0
        
        # Check key term coverage
        key_terms = set(self._extract_key_terms(content))
        
        summary_lower = summary.lower()
        covered_terms = sum(1 for term in key_terms if term in summary_lower)
        
        if not key_terms:
            return 1.0
        
        return covered_terms / len(key_terms)
    
    def summarize_batch(
        self,
        items: List[Dict[str, str]],  # List of {id, type, content}
        options: Optional[Dict[str, Any]] = None
    ) -> List[Summary]:
        """Summarize multiple items"""
        return [
            self.summarize(item["content"], item["id"], item["type"], options)
            for item in items
        ]
    
    def get_cached_summary(self, entity_id: str, entity_type: str) -> Optional[Summary]:
        """Get a cached summary"""
        cache_key = f"{entity_type}:{entity_id}"
        return self._summary_cache.get(cache_key)
    
    def invalidate_cache(self, entity_id: Optional[str] = None) -> None:
        """Invalidate summary cache"""
        if entity_id:
            # Remove specific entry
            self._summary_cache = {
                k: v for k, v in self._summary_cache.items()
                if entity_id not in k
            }
        else:
            self._summary_cache.clear()
