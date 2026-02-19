"""
Hierarchical Topic Extraction Module

This module extracts concrete, content-specific topics from conversation logs.
It uses an LLM-based approach to identify hierarchical topic structures:
  - topic: main domain (e.g., "Trust Calibration System")
  - subtopic: functional subdivision (e.g., "Uncertainty Metrics")
  - subsubtopic: concrete method/object (e.g., "entropy-based confidence score")

The extraction avoids generic meta-topics (e.g., "analysis", "learning", "discussion")
and focuses on what the user actually talked about.
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
from collections import defaultdict


class TopicExtractor:
    """
    Extracts hierarchical topics from conversation messages using LLM analysis.
    
    Design Principles:
    1. Content-specific over generic: Extract actual subjects discussed, not meta-concepts
    2. Hierarchical structure: topic → subtopic → subsubtopic
    3. Semantic deduplication: Merge similar concepts across turns
    4. Incremental updates: Process only new messages, update existing topics
    """
    
    def __init__(self, llm_client: OpenAI):
        self.client = llm_client
        self.extraction_prompt = self._build_extraction_prompt()
    
    def _build_extraction_prompt(self) -> str:
        """
        Constructs the system prompt for topic extraction.
        
        This prompt instructs the LLM to:
        - Extract concrete topics, not abstract meta-topics
        - Organize in 3-level hierarchy
        - Provide confidence scores
        - Identify semantic relationships
        """
        return """You are a topic extraction specialist. Analyze conversation messages and extract hierarchical topics.

CRITICAL RULES:
1. Extract CONCRETE topics, NOT generic meta-topics
   ✅ GOOD: "D3 force-directed graph", "LLM uncertainty estimation", "SQLite database schema"
   ❌ BAD: "analysis", "learning", "discussion", "knowledge", "study"

2. Three-level hierarchy (EXTRACT SPARINGLY):
   - topic: Main domain/subject (e.g., "Trust Calibration System")
   - subtopic: ONLY major functional subdivisions (e.g., "Uncertainty Metrics")
   - subsubtopic: ONLY if essential and significantly different from subtopic

3. IMPORTANT CONSTRAINTS:
   - Extract MAXIMUM 2-4 topic triples per batch of 10 messages
   - Only extract subtopics if they represent MAJOR distinct aspects
   - Only extract subsubtopics if they add SIGNIFICANT value (not minor details)
   - Prefer broader categories over detailed breakdowns
   - If in doubt, use EMPTY STRING "" for subsubtopic_label

4. For each topic triple, provide:
   - topic_label: The main domain name
   - subtopic_label: Major subdivision (or "" if topic alone is sufficient)
   - subsubtopic_label: Important detail (or "" if not needed)
   - confidence: 0-1 score (only extract if confidence >= 0.7)
   - keywords: List of 3-5 representative keywords

5. Avoid redundancy: If "Python programming" and "Python syntax" refer to same concept, use one
6. Focus on NOUNS and NOUN PHRASES, not verbs or actions

Output Format (strict JSON array):
[
  {
    "topic_label": "Main Domain",
    "subtopic_label": "Subdivision",
    "subsubtopic_label": "Concrete Detail",
    "confidence": 0.85,
    "keywords": ["keyword1", "keyword2", "keyword3"]
  }
]

Example conversation: "I'm building a D3 visualization for topic flow. I need to implement force-directed graph layout with hierarchical clustering. The nodes should be color-coded and interactive."

Good output (concise, high-level):
[
  {
    "topic_label": "D3 Visualization",
    "subtopic_label": "Force-Directed Graph",
    "subsubtopic_label": "",
    "confidence": 0.9,
    "keywords": ["D3", "force-directed", "graph", "visualization"]
  },
  {
    "topic_label": "Topic Flow System",
    "subtopic_label": "",
    "subsubtopic_label": "",
    "confidence": 0.8,
    "keywords": ["topic", "flow", "system"]
  }
]

Bad output (DO NOT DO THIS):
[
  {
    "topic_label": "Analysis",
    "subtopic_label": "Data Processing",
    "subsubtopic_label": "general computation",
    "confidence": 0.5,
    "keywords": ["data", "analysis", "processing"]
  }
]
"""
    
    def extract_from_messages(
        self, 
        messages: List[Dict[str, str]], 
        batch_size: int = 15
    ) -> List[Dict]:
        """
        Extract topics from a list of conversation messages.
        
        Args:
            messages: List of {role, content, timestamp} dicts
            batch_size: Number of messages to process in each LLM call
        
        Returns:
            List of extracted topic triples with metadata
        """
        if not messages:
            return []

        messages = self._sanitize_messages(messages)
        if not messages:
            return []
        
        # Group messages into batches for efficient processing
        batches = self._create_message_batches(messages, batch_size)
        all_topics = []
        
        for batch in batches:
            batch_topics = self._extract_from_batch(batch)
            all_topics.extend(batch_topics)
        
        # Deduplicate and merge similar topics
        merged_topics = self._merge_similar_topics(all_topics)
        
        # Filter out low-quality and overly detailed topics
        filtered_topics = self._filter_low_quality_topics(merged_topics)
        
        return filtered_topics
    
    def _create_message_batches(
        self, 
        messages: List[Dict], 
        batch_size: int
    ) -> List[List[Dict]]:
        """
        Split messages into batches for processing.
        
        Strategy: Group consecutive messages to maintain context
        """
        batches = []
        for i in range(0, len(messages), batch_size):
            batches.append(messages[i:i + batch_size])
        return batches

    def _sanitize_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Normalize and filter messages for topic extraction.

        - Only include user/assistant roles
        - Skip system/tool messages and non-string content
        """
        sanitized = []
        for msg in messages:
            role = (msg.get('role') or '').lower()
            if role not in {'user', 'assistant'}:
                continue
            content = msg.get('content', '')
            if not isinstance(content, str):
                continue
            content = content.strip()
            if not content:
                continue
            sanitized.append({**msg, 'role': role, 'content': content})
        return sanitized
    
    def _extract_from_batch(self, batch: List[Dict]) -> List[Dict]:
        """
        Extract topics from a single batch of messages using LLM.
        
        Returns:
            List of topic dicts with structure:
            {
                topic_label, subtopic_label, subsubtopic_label,
                confidence, keywords, source_messages
            }
        """
        # Format messages for LLM analysis
        conversation_text = self._format_messages_for_analysis(batch)
        
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": self.extraction_prompt},
                    {"role": "user", "content": f"Analyze this conversation segment and extract hierarchical topics:\n\n{conversation_text}"}
                ],
                temperature=0.3,  # Lower temperature for more consistent extraction
                max_tokens=1500
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            topics = self._parse_llm_response(response_text)
            
            # Add source message IDs
            message_ids = [msg.get('id') for msg in batch if msg.get('id')]
            for topic in topics:
                topic['source_messages'] = message_ids
                topic['first_seen_message_id'] = message_ids[0] if message_ids else None
                topic['last_seen_message_id'] = message_ids[-1] if message_ids else None
            
            return topics
            
        except Exception as e:
            print(f"[ERROR] Topic extraction failed: {e}")
            # Fallback to keyword-based extraction
            return self._fallback_keyword_extraction(batch)
    
    def _format_messages_for_analysis(self, messages: List[Dict]) -> str:
        """Format message batch into readable text for LLM analysis."""
        lines = []
        for i, msg in enumerate(messages, 1):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            lines.append(f"[{i}] {role.upper()}: {content}")
        return "\n".join(lines)
    
    def _parse_llm_response(self, response_text: str) -> List[Dict]:
        """
        Parse LLM JSON response into topic list.
        
        Handles:
        - Markdown code blocks
        - Malformed JSON
        - Missing fields
        """
        # Remove markdown code blocks if present
        response_text = re.sub(r'^```json\s*', '', response_text, flags=re.MULTILINE)
        response_text = re.sub(r'^```\s*$', '', response_text, flags=re.MULTILINE)
        response_text = response_text.strip()
        
        try:
            topics = json.loads(response_text)
            
            # Validate structure
            if not isinstance(topics, list):
                topics = [topics]
            
            # Ensure required fields
            validated_topics = []
            for topic in topics:
                if all(k in topic for k in ['topic_label', 'subtopic_label', 'subsubtopic_label']):
                    # Set defaults for optional fields
                    topic.setdefault('confidence', 0.5)
                    topic.setdefault('keywords', [])
                    validated_topics.append(topic)
            
            return validated_topics
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON parse error: {e}")
            print(f"[DEBUG] Response text: {response_text[:200]}...")
            return []
    
    def _fallback_keyword_extraction(self, messages: List[Dict]) -> List[Dict]:
        """
        Simple keyword-based fallback when LLM extraction fails.
        
        Uses TF-IDF-like approach to extract important terms.
        """
        from collections import Counter
        
        # Combine all message content
        text = " ".join([msg.get('content', '') for msg in messages])
        
        # Extract keywords (simple approach)
        words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b|\b[a-z]{4,}\b', text)
        
        # Remove stopwords
        stopwords = {'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                     'could', 'should', 'this', 'that', 'these', 'those'}
        
        filtered_words = [w.lower() for w in words if w.lower() not in stopwords and len(w) > 3]
        
        # Get top keywords
        word_counts = Counter(filtered_words)
        top_words = [w for w, _ in word_counts.most_common(10)]
        
        if not top_words:
            return []
        
        # Create a single generic topic (better than nothing)
        message_ids = [msg.get('id') for msg in messages if msg.get('id')]
        
        return [{
            'topic_label': top_words[0] if len(top_words) > 0 else 'Conversation',
            'subtopic_label': top_words[1] if len(top_words) > 1 else 'Discussion',
            'subsubtopic_label': top_words[2] if len(top_words) > 2 else 'Details',
            'confidence': 0.65,
            'keywords': top_words[:5],
            'source_messages': message_ids,
            'first_seen_message_id': message_ids[0] if message_ids else None,
            'last_seen_message_id': message_ids[-1] if message_ids else None
        }]
    
    def _merge_similar_topics(self, topics: List[Dict]) -> List[Dict]:
        """
        Merge semantically similar topics to avoid duplication.
        
        Strategy:
        1. Group by topic_label similarity
        2. Within groups, merge similar subtopics
        3. Combine metadata (frequencies, message IDs)
        """
        if not topics:
            return []
        
        # Simple keyword-overlap based merging
        merged = []
        used_indices = set()
        
        for i, topic1 in enumerate(topics):
            if i in used_indices:
                continue
            
            # Find similar topics
            similar_group = [topic1]
            used_indices.add(i)
            
            for j, topic2 in enumerate(topics[i+1:], start=i+1):
                if j in used_indices:
                    continue
                
                if self._are_topics_similar(topic1, topic2):
                    similar_group.append(topic2)
                    used_indices.add(j)
            
            # Merge the group
            merged_topic = self._merge_topic_group(similar_group)
            merged.append(merged_topic)
        
        return merged
    
    def _are_topics_similar(self, topic1: Dict, topic2: Dict, threshold: float = 0.5) -> bool:
        """
        Check if two topics are semantically similar.
        
        Uses keyword overlap and label similarity.
        """
        # Compare all three levels
        labels1 = [
            topic1.get('topic_label', '').lower(),
            topic1.get('subtopic_label', '').lower(),
            topic1.get('subsubtopic_label', '').lower()
        ]
        
        labels2 = [
            topic2.get('topic_label', '').lower(),
            topic2.get('subtopic_label', '').lower(),
            topic2.get('subsubtopic_label', '').lower()
        ]
        
        # Calculate word overlap at each level
        def word_overlap(s1: str, s2: str) -> float:
            words1 = set(s1.split())
            words2 = set(s2.split())
            if not words1 or not words2:
                return 0.0
            intersection = words1 & words2
            union = words1 | words2
            return len(intersection) / len(union) if union else 0.0
        
        # Average overlap across all levels
        overlaps = [word_overlap(l1, l2) for l1, l2 in zip(labels1, labels2)]
        avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0.0
        
        return avg_overlap >= threshold
    
    def _merge_topic_group(self, group: List[Dict]) -> Dict:
        """
        Merge a group of similar topics into one representative topic.
        
        Strategy:
        - Use the highest-confidence labels
        - Combine all keywords
        - Merge message IDs
        - Sum frequencies
        """
        if len(group) == 1:
            group[0].setdefault('frequency', 1)
            return group[0]
        
        # Sort by confidence
        group_sorted = sorted(group, key=lambda t: t.get('confidence', 0), reverse=True)
        
        # Use highest-confidence topic as base
        merged = group_sorted[0].copy()
        
        # Combine keywords from all topics
        all_keywords = []
        for topic in group:
            all_keywords.extend(topic.get('keywords', []))
        merged['keywords'] = list(dict.fromkeys(all_keywords))[:10]  # Deduplicate, keep order
        
        # Merge message IDs
        all_message_ids = []
        for topic in group:
            all_message_ids.extend(topic.get('source_messages', []))
        merged['source_messages'] = list(dict.fromkeys(all_message_ids))
        
        # Update first/last seen
        if merged['source_messages']:
            merged['first_seen_message_id'] = merged['source_messages'][0]
            merged['last_seen_message_id'] = merged['source_messages'][-1]
        
        # Frequency is number of times this topic appeared
        merged['frequency'] = len(group)
        
        # Average confidence
        merged['confidence'] = sum(t.get('confidence', 0) for t in group) / len(group)
        
        return merged

    def _filter_low_quality_topics(self, topics: List[Dict]) -> List[Dict]:
        """
        Filter out low-quality and overly detailed topics.

        Criteria:
        1. Confidence score >= 0.6
        2. Remove topics with generic/vague labels
        3. Limit number of topics based on importance
        """
        if not topics:
            return []

        filtered = []

        # Generic words to avoid
        generic_terms = {
            'discussion', 'analysis', 'learning', 'study', 'knowledge',
            'information', 'data', 'details', 'general', 'various',
            'other', 'miscellaneous', 'stuff', 'things', 'items'
        }

        for topic in topics:
            # Filter by confidence
            if topic.get('confidence', 0) < 0.6:
                continue

            # Filter generic labels
            topic_label = topic.get('topic_label', '').lower()
            subtopic_label = topic.get('subtopic_label', '').lower()

            if any(term in topic_label for term in generic_terms):
                continue
            if any(term in subtopic_label for term in generic_terms):
                continue

            # Normalize empty subsubtopics
            if not topic.get('subsubtopic_label') or topic['subsubtopic_label'].lower() in generic_terms:
                topic['subsubtopic_label'] = ''

            filtered.append(topic)

        # Sort by confidence and limit to top topics
        filtered.sort(key=lambda t: t.get('confidence', 0), reverse=True)

        # Keep top 15 most confident topics
        return filtered[:15]


def compute_co_occurrences(topics: List[Dict], window_size: int = 5) -> Dict:
    """
    Compute co-occurrence relationships between topics.
    
    Topics that appear in nearby messages are considered co-occurring.
    
    Args:
        topics: List of topic dicts with source_messages
        window_size: Number of messages to consider as "nearby"
    
    Returns:
        Dict mapping topic_id -> list of co-occurring topic_ids
    """
    co_occur = defaultdict(set)
    
    # Create message_id -> topic_ids mapping
    message_to_topics = defaultdict(list)
    
    for i, topic in enumerate(topics):
        topic_id = f"topic_{i}"
        for msg_id in topic.get('source_messages', []):
            message_to_topics[msg_id].append(topic_id)
    
    # For each topic, find topics in nearby messages
    for i, topic in enumerate(topics):
        topic_id = f"topic_{i}"
        source_msgs = topic.get('source_messages', [])
        
        for msg_id in source_msgs:
            # Look at nearby messages (within window)
            # Simplified: just use message_to_topics directly
            for other_topic_id in message_to_topics[msg_id]:
                if other_topic_id != topic_id:
                    co_occur[topic_id].add(other_topic_id)
    
    # Convert sets to lists
    return {k: list(v) for k, v in co_occur.items()}
