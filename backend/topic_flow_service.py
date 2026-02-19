"""
Incremental Topic Flow Update Service

This module orchestrates the incremental update process:
1. Detect new messages since last processing
2. Extract topics from new messages only
3. Update topic_flow table
4. Compute co-occurrences
5. Return updated D3 data

Key Design:
- No full recomputation unless explicitly requested
- Efficient: only process new messages
- Maintains consistency with existing topics
"""

from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from topic_extraction import TopicExtractor, compute_co_occurrences
from topic_storage import (
    get_all_topics,
    get_last_processed_message_id,
    insert_or_update_topic,
    convert_to_d3_format,
    init_topic_flow_schema
)
from database import get_or_create_default_user, _ensure_messages_schema


class TopicFlowService:
    """
    Service for managing Topic Flow updates.
    
    Handles:
    - Incremental updates when new messages arrive
    - Full recomputation when requested
    - D3 data generation
    """
    
    def __init__(self, llm_client: OpenAI):
        self.extractor = TopicExtractor(llm_client)
        init_topic_flow_schema()
    
    def update_topic_flow(
        self, 
        messages: List[Dict],
        user_id: int,
        force_full_recomputation: bool = False
    ) -> Dict:
        """
        Update topic flow with new conversation messages.
        
        Args:
            messages: List of {id, role, content, timestamp} dicts
            force_full_recomputation: If True, reprocess all messages
        
        Returns:
            {
                'nodes': [...],
                'links': [...],
                'stats': {...},
                'processed_count': int,
                'is_incremental': bool
            }
        """
        if user_id is None:
            user_id = get_or_create_default_user()

        if not messages:
            # Return empty graph
            return {
                'nodes': [],
                'links': [],
                'stats': {},
                'processed_count': 0,
                'is_incremental': False
            }
        
        # Determine which messages to process
        if force_full_recomputation:
            messages_to_process = messages
            is_incremental = False
        else:
            last_processed_id = get_last_processed_message_id(user_id)
            
            if last_processed_id is None:
                # First time: process all messages
                messages_to_process = messages
                is_incremental = False
            else:
                # Incremental: only new messages
                messages_to_process = [
                    msg for msg in messages 
                    if msg.get('id', 0) > last_processed_id
                ]
                is_incremental = True
        
        print(f"[TopicFlowService] Processing {len(messages_to_process)} messages (incremental={is_incremental})")
        
        if not messages_to_process:
            # No new messages, return current state
            topics = get_all_topics(user_id)
            d3_data = convert_to_d3_format(topics)
            return {
                **d3_data,
                'stats': self._get_stats(user_id),
                'processed_count': 0,
                'is_incremental': is_incremental
            }
        
        # Extract topics from messages
        extracted_topics = self.extractor.extract_from_messages(messages_to_process)
        
        print(f"[TopicFlowService] Extracted {len(extracted_topics)} topic triples")
        
        # Compute co-occurrences
        co_occurrences = compute_co_occurrences(extracted_topics)
        
        # Persist to database
        for i, topic in enumerate(extracted_topics):
            topic_id_key = f"topic_{i}"
            co_occur_list = co_occurrences.get(topic_id_key, [])
            
            # Convert topic_N IDs to actual topic_ids
            co_occur_topic_ids = []
            for co_key in co_occur_list:
                idx = int(co_key.split('_')[1])
                if idx < len(extracted_topics):
                    co_topic = extracted_topics[idx]
                    from topic_storage import generate_topic_id
                    co_topic_id = generate_topic_id(
                        user_id,
                        co_topic['topic_label'],
                        co_topic['subtopic_label'],
                        co_topic['subsubtopic_label']
                    )
                    co_occur_topic_ids.append(co_topic_id)
            
            insert_or_update_topic(
                user_id=user_id,
                topic_label=topic['topic_label'],
                subtopic_label=topic['subtopic_label'],
                subsubtopic_label=topic['subsubtopic_label'],
                first_seen_message_id=topic.get('first_seen_message_id'),
                last_seen_message_id=topic.get('last_seen_message_id'),
                confidence=topic.get('confidence', 0.5),
                keywords=topic.get('keywords', []),
                co_occurrence=co_occur_topic_ids
            )
        
        # Generate D3 data from updated database
        all_topics = get_all_topics(user_id)
        d3_data = convert_to_d3_format(all_topics)
        
        return {
            **d3_data,
            'stats': self._get_stats(user_id),
            'processed_count': len(messages_to_process),
            'is_incremental': is_incremental
        }
    
    def get_current_topic_flow(self, user_id: int) -> Dict:
        """
        Get current topic flow without processing new messages.
        
        Returns:
            Current D3 graph data
        """
        if user_id is None:
            user_id = get_or_create_default_user()

        topics = get_all_topics(user_id)
        d3_data = convert_to_d3_format(topics)
        
        return {
            **d3_data,
            'stats': self._get_stats(user_id)
        }
    
    def _get_stats(self, user_id: int) -> Dict:
        """Get topic statistics."""
        from topic_storage import get_topic_statistics
        return get_topic_statistics(user_id)
    
    def reset_topic_flow(self, user_id: int):
        """
        Clear all topics and reset.
        
        Use for testing or when conversation is cleared.
        """
        if user_id is None:
            user_id = get_or_create_default_user()

        from topic_storage import clear_all_topics
        clear_all_topics(user_id)
        print("[TopicFlowService] Topic flow reset")


def get_messages_with_ids_from_db(user_id: Optional[int]) -> List[Dict]:
    """
    Fetch all messages from database with IDs.
    
    Returns:
        List of {id, role, content, timestamp} dicts
    """
    from database import get_conn
    
    if user_id is None:
        user_id = get_or_create_default_user()

    _ensure_messages_schema(default_user_id=user_id)
    conn = get_conn()
    c = conn.cursor()
    
    c.execute("""
        SELECT id, role, content, timestamp 
        FROM messages 
        WHERE user_id = ?
        ORDER BY id
    """, (user_id,))
    
    rows = c.fetchall()
    conn.close()
    
    messages = []
    for row in rows:
        messages.append({
            'id': row[0],
            'role': row[1],
            'content': row[2],
            'timestamp': row[3]
        })
    
    return messages
