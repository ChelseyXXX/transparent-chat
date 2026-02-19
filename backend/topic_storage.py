"""
Topic Flow Database Schema and Persistence

This module manages the tabular storage of hierarchical topics.
It provides:
1. Table schema for topic triples (topic → subtopic → subsubtopic)
2. Incremental update logic
3. Co-occurrence tracking
4. Query utilities for visualization

Schema Design:
- Single source of truth: topic_flow table
- One row = one (topic, subtopic, subsubtopic) triple
- Frequency tracking for recurring topics
- Message ID tracking for provenance
- Co-occurrence relationships for graph edges
"""

import sqlite3
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import os
from database import get_or_create_default_user


# Database path (same as main chatlog.db)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "chatlog.db")


def get_conn():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)


def init_topic_flow_schema():
    """
    Initialize the topic_flow table schema.
    
    Table: topic_flow
    Columns:
        - topic_id: Unique identifier for this topic triple (PRIMARY KEY)
        - topic_label: Main domain (e.g., "Trust Calibration System")
        - subtopic_label: Subdivision (e.g., "Uncertainty Metrics")
        - subsubtopic_label: Concrete detail (e.g., "entropy calculation")
        - first_seen_message_id: ID of first message where this topic appeared
        - last_seen_message_id: ID of most recent message
        - frequency: Number of times this topic appeared
        - confidence: 0-1 relevance score
        - keywords: JSON array of representative keywords
        - co_occurrence: JSON array of related topic_ids
        - created_at: Timestamp of first insertion
        - updated_at: Timestamp of last update
    """
    conn = get_conn()
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS topic_flow (
            topic_id TEXT PRIMARY KEY,
            user_id INTEGER,
            topic_label TEXT NOT NULL,
            subtopic_label TEXT DEFAULT '',
            subsubtopic_label TEXT DEFAULT '',
            first_seen_message_id INTEGER,
            last_seen_message_id INTEGER,
            frequency INTEGER DEFAULT 1,
            confidence REAL DEFAULT 0.5,
            keywords TEXT,
            co_occurrence TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Ensure user_id column exists (backwards compatibility)
    c.execute("PRAGMA table_info(topic_flow)")
    cols = [row[1] for row in c.fetchall()]
    if 'user_id' not in cols:
        c.execute("ALTER TABLE topic_flow ADD COLUMN user_id INTEGER")

    default_user_id = get_or_create_default_user()
    c.execute("UPDATE topic_flow SET user_id = ? WHERE user_id IS NULL", (default_user_id,))

    # Migrate legacy topic_id values to include user prefix and fix co_occurrence
    prefix = f"u{default_user_id}::"
    c.execute("SELECT topic_id, co_occurrence FROM topic_flow WHERE user_id = ?", (default_user_id,))
    rows = c.fetchall()
    for (topic_id, co_json) in rows:
        if co_json:
            try:
                co_list = json.loads(co_json)
            except Exception:
                co_list = []
        else:
            co_list = []

        updated_co_list = [cid if str(cid).startswith(prefix) else f"{prefix}{cid}" for cid in co_list]
        updated_co_json = json.dumps(updated_co_list) if updated_co_list else co_json

        if not topic_id.startswith(prefix):
            new_topic_id = f"{prefix}{topic_id}"
            c.execute(
                "UPDATE topic_flow SET topic_id = ?, co_occurrence = ? WHERE topic_id = ?",
                (new_topic_id, updated_co_json, topic_id)
            )
        elif updated_co_json != co_json:
            c.execute(
                "UPDATE topic_flow SET co_occurrence = ? WHERE topic_id = ?",
                (updated_co_json, topic_id)
            )
    
    # Create indices for efficient queries
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_topic_flow_topic 
        ON topic_flow(topic_label)
    """)

    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_topic_flow_user
        ON topic_flow(user_id)
    """)
    
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_topic_flow_updated 
        ON topic_flow(updated_at DESC)
    """)
    
    conn.commit()
    conn.close()


def generate_topic_id(user_id: int, topic: str, subtopic: str, subsubtopic: str) -> str:
    """
    Generate a unique but deterministic topic_id.
    
    Strategy: Concatenate normalized labels with separator.
    This allows same semantic triple to get same ID.
    Handles empty subtopic/subsubtopic gracefully.
    """
    # Normalize: lowercase, remove extra spaces
    t = topic.lower().strip()
    st = (subtopic or '').lower().strip()
    sst = (subsubtopic or '').lower().strip()
    
    # Create ID: use underscores, replace spaces with hyphens
    base_id = f"{t}::{st}::{sst}".replace(' ', '-')
    topic_id = f"u{user_id}::{base_id}"
    
    return topic_id


def insert_or_update_topic(
    user_id: int,
    topic_label: str,
    subtopic_label: str = '',
    subsubtopic_label: str = '',
    first_seen_message_id: Optional[int] = None,
    last_seen_message_id: Optional[int] = None,
    confidence: float = 0.5,
    keywords: Optional[List[str]] = None,
    co_occurrence: Optional[List[str]] = None
) -> str:
    """
    Insert a new topic triple or update existing one.
    
    subtopic_label and subsubtopic_label can be empty strings.
    
    If topic_id already exists:
        - Increment frequency
        - Update last_seen_message_id
        - Merge keywords
        - Update co_occurrence
        - Update timestamp
    
    Returns:
        topic_id of inserted/updated row
    """
    init_topic_flow_schema()
    
    # Normalize empty values
    subtopic_label = subtopic_label or ''
    subsubtopic_label = subsubtopic_label or ''
    
    topic_id = generate_topic_id(user_id, topic_label, subtopic_label, subsubtopic_label)
    keywords_json = json.dumps(keywords or [])
    co_occurrence_json = json.dumps(co_occurrence or [])
    
    conn = get_conn()
    c = conn.cursor()
    
    # Check if exists
    c.execute("SELECT frequency, keywords, co_occurrence FROM topic_flow WHERE topic_id = ? AND user_id = ?", (topic_id, user_id))
    existing = c.fetchone()
    
    if existing:
        # Update existing
        old_frequency, old_keywords_json, old_co_occurrence_json = existing
        
        # Merge keywords
        old_keywords = json.loads(old_keywords_json) if old_keywords_json else []
        new_keywords = list(dict.fromkeys(old_keywords + (keywords or [])))[:15]  # Keep top 15
        
        # Merge co_occurrence
        old_co_occur = json.loads(old_co_occurrence_json) if old_co_occurrence_json else []
        new_co_occur = list(dict.fromkeys(old_co_occur + (co_occurrence or [])))
        
        c.execute("""
            UPDATE topic_flow 
            SET frequency = frequency + 1,
                last_seen_message_id = ?,
                confidence = ?,
                keywords = ?,
                co_occurrence = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE topic_id = ? AND user_id = ?
        """, (
            last_seen_message_id,
            confidence,
            json.dumps(new_keywords),
            json.dumps(new_co_occur),
            topic_id,
            user_id
        ))
    else:
        # Insert new
        c.execute("""
            INSERT INTO topic_flow (
                topic_id, user_id, topic_label, subtopic_label, subsubtopic_label,
                first_seen_message_id, last_seen_message_id,
                frequency, confidence, keywords, co_occurrence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
        """, (
            topic_id, user_id, topic_label, subtopic_label, subsubtopic_label,
            first_seen_message_id, last_seen_message_id,
            confidence, keywords_json, co_occurrence_json
        ))
    
    conn.commit()
    conn.close()
    
    return topic_id


def get_all_topics(user_id: int) -> List[Dict]:
    """
    Retrieve all topics from topic_flow table.
    
    Returns:
        List of topic dicts with all fields
    """
    init_topic_flow_schema()
    
    conn = get_conn()
    c = conn.cursor()
    
    c.execute("""
        SELECT 
            topic_id, topic_label, subtopic_label, subsubtopic_label,
            first_seen_message_id, last_seen_message_id,
            frequency, confidence, keywords, co_occurrence,
            created_at, updated_at
        FROM topic_flow
        WHERE user_id = ?
        ORDER BY updated_at DESC
    """, (user_id,))
    
    rows = c.fetchall()
    conn.close()
    
    topics = []
    for row in rows:
        topics.append({
            'topic_id': row[0],
            'topic_label': row[1],
            'subtopic_label': row[2],
            'subsubtopic_label': row[3],
            'first_seen_message_id': row[4],
            'last_seen_message_id': row[5],
            'frequency': row[6],
            'confidence': row[7],
            'keywords': json.loads(row[8]) if row[8] else [],
            'co_occurrence': json.loads(row[9]) if row[9] else [],
            'created_at': row[10],
            'updated_at': row[11]
        })
    
    return topics


def get_topics_by_message_id_range(user_id: int, start_id: int, end_id: Optional[int] = None) -> List[Dict]:
    """
    Get topics that appeared in a specific message ID range.
    
    Useful for incremental updates: only fetch topics from new messages.
    """
    init_topic_flow_schema()
    
    conn = get_conn()
    c = conn.cursor()
    
    if end_id:
        c.execute("""
            SELECT 
                topic_id, topic_label, subtopic_label, subsubtopic_label,
                first_seen_message_id, last_seen_message_id,
                frequency, confidence, keywords, co_occurrence
            FROM topic_flow
            WHERE user_id = ? AND last_seen_message_id >= ? AND last_seen_message_id <= ?
            ORDER BY last_seen_message_id
        """, (user_id, start_id, end_id))
    else:
        c.execute("""
            SELECT 
                topic_id, topic_label, subtopic_label, subsubtopic_label,
                first_seen_message_id, last_seen_message_id,
                frequency, confidence, keywords, co_occurrence
            FROM topic_flow
            WHERE user_id = ? AND last_seen_message_id >= ?
            ORDER BY last_seen_message_id
        """, (user_id, start_id))
    
    rows = c.fetchall()
    conn.close()
    
    topics = []
    for row in rows:
        topics.append({
            'topic_id': row[0],
            'topic_label': row[1],
            'subtopic_label': row[2],
            'subsubtopic_label': row[3],
            'first_seen_message_id': row[4],
            'last_seen_message_id': row[5],
            'frequency': row[6],
            'confidence': row[7],
            'keywords': json.loads(row[8]) if row[8] else [],
            'co_occurrence': json.loads(row[9]) if row[9] else []
        })
    
    return topics


def get_last_processed_message_id(user_id: int) -> Optional[int]:
    """
    Get the ID of the last message that was processed for topic extraction.
    
    Uses the highest last_seen_message_id in topic_flow table.
    Returns None if no topics exist yet.
    """
    init_topic_flow_schema()
    
    conn = get_conn()
    c = conn.cursor()
    
    c.execute("SELECT MAX(last_seen_message_id) FROM topic_flow WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    return result[0] if result and result[0] else None


def clear_all_topics(user_id: int):
    """
    Clear all topics from topic_flow table.
    
    Use for testing or full reset.
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM topic_flow WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_topic_statistics(user_id: int) -> Dict:
    """
    Get aggregate statistics about topics.
    
    Returns:
        Dict with counts and metrics
    """
    init_topic_flow_schema()
    
    conn = get_conn()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM topic_flow WHERE user_id = ?", (user_id,))
    total_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT topic_label) FROM topic_flow WHERE user_id = ?", (user_id,))
    unique_topics = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT subtopic_label) FROM topic_flow WHERE user_id = ?", (user_id,))
    unique_subtopics = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT subsubtopic_label) FROM topic_flow WHERE user_id = ?", (user_id,))
    unique_subsubtopics = c.fetchone()[0]
    
    c.execute("SELECT AVG(frequency) FROM topic_flow WHERE user_id = ?", (user_id,))
    avg_frequency = c.fetchone()[0] or 0
    
    c.execute("SELECT AVG(confidence) FROM topic_flow WHERE user_id = ?", (user_id,))
    avg_confidence = c.fetchone()[0] or 0
    
    conn.close()
    
    return {
        'total_triples': total_count,
        'unique_topics': unique_topics,
        'unique_subtopics': unique_subtopics,
        'unique_subsubtopics': unique_subsubtopics,
        'avg_frequency': round(avg_frequency, 2),
        'avg_confidence': round(avg_confidence, 2)
    }


def convert_to_d3_format(topics: List[Dict]) -> Dict:
    """
    Convert topic table to D3-compatible graph format.
    
    Returns:
        {
            nodes: [
                {id, label, level, size, group, ...}
            ],
            links: [
                {source, target, weight}
            ]
        }
    
    Node levels: 'topic', 'subtopic', 'subsubtopic'
    Node size: based on frequency × confidence
    Link weight: based on co-occurrence frequency
    """
    if not topics:
        return {'nodes': [], 'links': []}
    
    nodes = []
    links = []
    node_id_set = set()
    
    # Build hierarchical nodes
    for topic in topics:
        topic_id = topic['topic_id']
        topic_label = topic['topic_label']
        subtopic_label = topic['subtopic_label']
        subsubtopic_label = topic['subsubtopic_label']
        frequency = topic.get('frequency', 1)
        confidence = topic.get('confidence', 0.5)
        
        # Node size: frequency × confidence × scale factor
        base_size = frequency * confidence * 10
        
        # Create node IDs (normalized)
        topic_node_id = topic_label.lower().replace(' ', '-')
        subtopic_node_id = f"{topic_node_id}::{subtopic_label.lower().replace(' ', '-')}"
        subsubtopic_node_id = topic_id  # Use full topic_id for subsubtopic
        
        # Add topic node (if not exists)
        if topic_node_id not in node_id_set:
            nodes.append({
                'id': topic_node_id,
                'label': topic_label,
                'level': 'topic',
                'size': base_size + 20,  # Larger for top-level
                'group': topic_label,
                'frequency': frequency,
                'confidence': confidence,
                'first_seen_message_id': topic.get('first_seen_message_id'),
                'last_seen_message_id': topic.get('last_seen_message_id')
            })
            node_id_set.add(topic_node_id)
        
        # Add subtopic node (if not exists)
        if subtopic_node_id not in node_id_set:
            nodes.append({
                'id': subtopic_node_id,
                'label': subtopic_label,
                'level': 'subtopic',
                'size': base_size + 10,
                'group': topic_label,
                'frequency': frequency,
                'confidence': confidence,
                'first_seen_message_id': topic.get('first_seen_message_id'),
                'last_seen_message_id': topic.get('last_seen_message_id')
            })
            node_id_set.add(subtopic_node_id)
        
        # Add subsubtopic node
        if subsubtopic_node_id not in node_id_set:
            nodes.append({
                'id': subsubtopic_node_id,
                'label': subsubtopic_label,
                'level': 'subsubtopic',
                'size': base_size,
                'group': topic_label,
                'frequency': frequency,
                'confidence': confidence,
                'keywords': topic.get('keywords', []),
                'first_seen_message_id': topic.get('first_seen_message_id'),
                'last_seen_message_id': topic.get('last_seen_message_id')
            })
            node_id_set.add(subsubtopic_node_id)
        
        # Add hierarchical links
        links.append({
            'source': topic_node_id,
            'target': subtopic_node_id,
            'weight': frequency,
            'type': 'hierarchy'
        })
        
        links.append({
            'source': subtopic_node_id,
            'target': subsubtopic_node_id,
            'weight': frequency,
            'type': 'hierarchy'
        })
    
    # Add co-occurrence links
    for topic in topics:
        subsubtopic_id = topic['topic_id']
        co_occur_ids = topic.get('co_occurrence', [])
        
        for co_id in co_occur_ids:
            # Only add if both nodes exist
            if subsubtopic_id in node_id_set and co_id in node_id_set:
                # Avoid duplicate links (only add one direction)
                if subsubtopic_id < co_id:
                    links.append({
                        'source': subsubtopic_id,
                        'target': co_id,
                        'weight': 1,
                        'type': 'cooccurrence'
                    })
    
    return {
        'nodes': nodes,
        'links': links
    }
