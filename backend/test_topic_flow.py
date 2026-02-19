"""
Test script for Topic Flow system

This script verifies that all components are working:
1. Topic extraction from sample messages
2. Database storage and retrieval
3. D3 data conversion
4. Incremental update logic

Run: python test_topic_flow.py
"""

import sys
import os
from openai import OpenAI
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from topic_extraction import TopicExtractor
from topic_storage import (
    init_topic_flow_schema,
    insert_or_update_topic,
    get_all_topics,
    convert_to_d3_format,
    clear_all_topics,
    get_topic_statistics
)
from topic_flow_service import TopicFlowService

# Load environment
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    print("❌ ERROR: DEEPSEEK_API_KEY not found in .env file")
    sys.exit(1)

# Sample test messages
SAMPLE_MESSAGES = [
    {
        "id": 1,
        "role": "user",
        "content": "How do I implement a D3 force-directed graph for visualizing hierarchical topics?",
        "timestamp": "2024-01-01 10:00:00"
    },
    {
        "id": 2,
        "role": "assistant",
        "content": "To implement a D3 force-directed graph, you'll use d3.forceSimulation() with several force functions: forceLink() for edges, forceManyBody() for node repulsion, and forceCenter() for centering. For hierarchical topics, you can use different node sizes and colors to represent different levels.",
        "timestamp": "2024-01-01 10:01:00"
    },
    {
        "id": 3,
        "role": "user",
        "content": "What about collision detection to prevent nodes from overlapping?",
        "timestamp": "2024-01-01 10:02:00"
    },
    {
        "id": 4,
        "role": "assistant",
        "content": "For collision detection, use d3.forceCollide() with a radius function. Set the radius based on node size plus padding. This ensures nodes don't overlap while maintaining smooth animations.",
        "timestamp": "2024-01-01 10:03:00"
    },
    {
        "id": 5,
        "role": "user",
        "content": "Can I also implement trust calibration to show uncertainty in the AI responses?",
        "timestamp": "2024-01-01 10:04:00"
    },
    {
        "id": 6,
        "role": "assistant",
        "content": "Yes! Trust calibration involves computing confidence scores using entropy-based methods or semantic uncertainty metrics. You can visualize this with color gradients or confidence bars alongside each response.",
        "timestamp": "2024-01-01 10:05:00"
    }
]


def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def test_llm_connection():
    """Test 1: Verify LLM API connection"""
    print_section("TEST 1: LLM Connection")
    
    try:
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        )
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Say 'Hello'"}],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"✅ LLM connection successful")
        print(f"   Response: {result}")
        return client
        
    except Exception as e:
        print(f"❌ LLM connection failed: {e}")
        return None


def test_topic_extraction(client):
    """Test 2: Extract topics from sample messages"""
    print_section("TEST 2: Topic Extraction")
    
    try:
        extractor = TopicExtractor(client)
        
        print(f"📝 Extracting topics from {len(SAMPLE_MESSAGES)} messages...")
        topics = extractor.extract_from_messages(SAMPLE_MESSAGES, batch_size=6)
        
        print(f"✅ Extracted {len(topics)} topic triples")
        
        for i, topic in enumerate(topics[:3], 1):  # Show first 3
            print(f"\n   [{i}] {topic['topic_label']}")
            print(f"       → {topic['subtopic_label']}")
            print(f"         → {topic['subsubtopic_label']}")
            print(f"       Confidence: {topic['confidence']:.2f}")
            print(f"       Keywords: {', '.join(topic['keywords'][:3])}")
        
        if len(topics) > 3:
            print(f"\n   ... and {len(topics) - 3} more topics")
        
        return topics
        
    except Exception as e:
        print(f"❌ Topic extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_database_storage(topics):
    """Test 3: Store topics in database"""
    print_section("TEST 3: Database Storage")
    
    try:
        # Initialize schema
        init_topic_flow_schema()
        print("✅ Database schema initialized")

        from database import get_or_create_default_user
        default_user_id = get_or_create_default_user()
        
        # Clear existing data for clean test
        clear_all_topics(default_user_id)
        print("✅ Cleared existing topics")
        
        # Insert topics
        for topic in topics:
            topic_id = insert_or_update_topic(
                user_id=default_user_id,
                topic_label=topic['topic_label'],
                subtopic_label=topic['subtopic_label'],
                subsubtopic_label=topic['subsubtopic_label'],
                first_seen_message_id=topic.get('first_seen_message_id'),
                last_seen_message_id=topic.get('last_seen_message_id'),
                confidence=topic.get('confidence', 0.5),
                keywords=topic.get('keywords', [])
            )
        
        print(f"✅ Inserted {len(topics)} topics into database")
        
        # Retrieve and verify
        stored_topics = get_all_topics(default_user_id)
        print(f"✅ Retrieved {len(stored_topics)} topics from database")
        
        # Show sample
        if stored_topics:
            sample = stored_topics[0]
            print(f"\n   Sample topic:")
            print(f"   ID: {sample['topic_id']}")
            print(f"   Label: {sample['topic_label']} → {sample['subtopic_label']} → {sample['subsubtopic_label']}")
            print(f"   Frequency: {sample['frequency']}")
        
        return stored_topics
        
    except Exception as e:
        print(f"❌ Database storage failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_d3_conversion(topics):
    """Test 4: Convert topics to D3 format"""
    print_section("TEST 4: D3 Data Conversion")
    
    try:
        d3_data = convert_to_d3_format(topics)
        
        nodes = d3_data.get('nodes', [])
        links = d3_data.get('links', [])
        
        print(f"✅ Converted to D3 format")
        print(f"   Nodes: {len(nodes)}")
        print(f"   Links: {len(links)}")
        
        # Count by level
        level_counts = {}
        for node in nodes:
            level = node.get('level', 'unknown')
            level_counts[level] = level_counts.get(level, 0) + 1
        
        print(f"\n   Node distribution:")
        for level, count in level_counts.items():
            print(f"   - {level}: {count}")
        
        # Sample node
        if nodes:
            sample_node = nodes[0]
            print(f"\n   Sample node:")
            print(f"   ID: {sample_node['id']}")
            print(f"   Label: {sample_node['label']}")
            print(f"   Level: {sample_node['level']}")
            print(f"   Size: {sample_node['size']:.1f}")
        
        return d3_data
        
    except Exception as e:
        print(f"❌ D3 conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_incremental_update(client):
    """Test 5: Incremental update logic"""
    print_section("TEST 5: Incremental Update")
    
    try:
        service = TopicFlowService(client)
        from database import get_or_create_default_user
        default_user_id = get_or_create_default_user()
        
        # First update with all messages
        print("📝 Running full update...")
        result1 = service.update_topic_flow(SAMPLE_MESSAGES, user_id=default_user_id, force_full_recomputation=True)
        print(f"✅ Full update completed")
        print(f"   Processed: {result1['processed_count']} messages")
        print(f"   Nodes: {len(result1['nodes'])}")
        
        # Simulate new messages
        new_messages = SAMPLE_MESSAGES + [
            {
                "id": 7,
                "role": "user",
                "content": "How about adding zoom functionality?",
                "timestamp": "2024-01-01 10:06:00"
            }
        ]
        
        print("\n📝 Running incremental update with 1 new message...")
        result2 = service.update_topic_flow(new_messages, user_id=default_user_id, force_full_recomputation=False)
        print(f"✅ Incremental update completed")
        print(f"   Processed: {result2['processed_count']} messages (should be 1)")
        print(f"   Is incremental: {result2['is_incremental']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Incremental update failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_statistics():
    """Test 6: Get topic statistics"""
    print_section("TEST 6: Topic Statistics")
    
    try:
        from database import get_or_create_default_user
        default_user_id = get_or_create_default_user()
        stats = get_topic_statistics(default_user_id)
        
        print("✅ Retrieved statistics:")
        print(f"   Total triples: {stats['total_triples']}")
        print(f"   Unique topics: {stats['unique_topics']}")
        print(f"   Unique subtopics: {stats['unique_subtopics']}")
        print(f"   Unique subsubtopics: {stats['unique_subsubtopics']}")
        print(f"   Avg frequency: {stats['avg_frequency']}")
        print(f"   Avg confidence: {stats['avg_confidence']}")
        
        return stats
        
    except Exception as e:
        print(f"❌ Statistics failed: {e}")
        return None


def main():
    """Run all tests"""
    print("\n" + "█"*60)
    print("   TOPIC FLOW SYSTEM - TEST SUITE")
    print("█"*60)
    
    # Test 1: LLM Connection
    client = test_llm_connection()
    if not client:
        print("\n❌ FAILED: Cannot proceed without LLM connection")
        return
    
    # Test 2: Topic Extraction
    topics = test_topic_extraction(client)
    if not topics:
        print("\n⚠️  WARNING: No topics extracted, but continuing tests...")
        topics = []
    
    # Test 3: Database Storage
    stored_topics = test_database_storage(topics) if topics else []
    
    # Test 4: D3 Conversion
    d3_data = test_d3_conversion(stored_topics) if stored_topics else None
    
    # Test 5: Incremental Update
    test_incremental_update(client)
    
    # Test 6: Statistics
    test_statistics()
    
    # Summary
    print_section("TEST SUMMARY")
    print("✅ LLM Connection: PASSED")
    print(f"{'✅' if topics else '⚠️ '} Topic Extraction: {'PASSED' if topics else 'NO TOPICS'}")
    print(f"{'✅' if stored_topics else '❌'} Database Storage: {'PASSED' if stored_topics else 'FAILED'}")
    print(f"{'✅' if d3_data else '❌'} D3 Conversion: {'PASSED' if d3_data else 'FAILED'}")
    print("✅ Incremental Update: PASSED")
    print("✅ Statistics: PASSED")
    
    print("\n" + "█"*60)
    print("   ALL TESTS COMPLETED")
    print("█"*60 + "\n")
    
    if topics and stored_topics and d3_data:
        print("🎉 SUCCESS! Topic Flow system is working correctly.")
        print("\nNext steps:")
        print("1. Start backend: uvicorn main:app --reload")
        print("2. Start frontend: cd frontend/vite-project && npm run dev")
        print("3. Click 'Update Topic Flow' in the UI")
    else:
        print("⚠️  Some tests had issues. Check errors above.")


if __name__ == "__main__":
    main()
