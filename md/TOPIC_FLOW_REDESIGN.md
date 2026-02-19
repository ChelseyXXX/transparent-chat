# Topic Flow System - Complete Redesign

## Overview

The Topic Flow system has been completely redesigned to extract **concrete, hierarchical topics** from conversation logs and visualize them as an interactive force-directed graph.

---

## Architecture

### 1. Backend Components

#### **topic_extraction.py** - LLM-Based Topic Extraction
- **Purpose**: Extract hierarchical topics from conversation messages
- **Key Features**:
  - Uses DeepSeek LLM with carefully crafted prompts
  - Extracts 3-level hierarchy: topic → subtopic → subsubtopic
  - Focuses on CONCRETE topics (e.g., "D3 force-directed graph"), not generic meta-topics
  - Semantic deduplication to merge similar concepts
  - Co-occurrence detection for graph edges

**Example Output**:
```json
[
  {
    "topic_label": "Trust Calibration System",
    "subtopic_label": "Uncertainty Metrics",
    "subsubtopic_label": "entropy-based confidence score",
    "confidence": 0.85,
    "keywords": ["trust", "calibration", "uncertainty", "confidence"],
    "source_messages": [1, 2, 3]
  }
]
```

#### **topic_storage.py** - Database Schema & Persistence
- **Table**: `topic_flow`
- **Schema**:
  ```sql
  CREATE TABLE topic_flow (
      topic_id TEXT PRIMARY KEY,              -- Unique: "topic::subtopic::subsubtopic"
      topic_label TEXT NOT NULL,
      subtopic_label TEXT NOT NULL,
      subsubtopic_label TEXT NOT NULL,
      first_seen_message_id INTEGER,          -- Provenance tracking
      last_seen_message_id INTEGER,
      frequency INTEGER DEFAULT 1,            -- Incremented on each reappearance
      confidence REAL DEFAULT 0.5,            -- 0-1 relevance score
      keywords TEXT,                          -- JSON array
      co_occurrence TEXT,                     -- JSON array of related topic_ids
      created_at DATETIME,
      updated_at DATETIME
  )
  ```

- **Key Functions**:
  - `insert_or_update_topic()`: Upsert with frequency tracking
  - `get_all_topics()`: Retrieve all topics
  - `convert_to_d3_format()`: Transform to graph format
  - `get_last_processed_message_id()`: For incremental updates

#### **topic_flow_service.py** - Orchestration Layer
- **Purpose**: Coordinate extraction, storage, and updates
- **Key Method**: `update_topic_flow(messages, force_full_recomputation=False)`
  - **Incremental mode** (default): Only process new messages since last update
  - **Full recomputation**: Reprocess all messages (for testing/reset)

**Workflow**:
```
1. Check last processed message ID
2. Extract topics from new messages only
3. Compute co-occurrences
4. Update database (upsert)
5. Generate D3 graph data
```

#### **main.py** - API Endpoints
- `GET /topic-flow`: Get current graph data (no processing)
- `POST /topic-flow/update?force_recompute=false`: Update with new messages
- `POST /topic-flow/reset`: Clear all topics

---

### 2. Frontend Components

#### **TopicFlowVisualization.jsx** - D3 Force-Directed Graph
- **Visualization Type**: Force-directed graph with hierarchical clustering
- **Node Levels**:
  - **Topic** (large, indigo): Main domains
  - **Subtopic** (medium, purple): Subdivisions
  - **Subsubtopic** (small, pink): Concrete details

- **Link Types**:
  - **Hierarchy links** (solid, gray): topic → subtopic → subsubtopic
  - **Co-occurrence links** (dashed, orange): Related concepts

- **Interactions**:
  - **Hover**: Highlight connected nodes, show tooltip with metadata
  - **Drag**: Reposition nodes
  - **Zoom/Pan**: Explore large graphs
  - **Click**: Trigger callback (extensible)

**D3 Forces**:
```javascript
forceSimulation()
  .force('link', forceLink()
    .distance(d => d.type === 'hierarchy' ? 80 : 150)
    .strength(d => d.type === 'hierarchy' ? 0.8 : 0.3)
  )
  .force('charge', forceManyBody()
    .strength(d => d.level === 'topic' ? -800 : -200)
  )
  .force('center', forceCenter(width/2, height/2))
  .force('collision', forceCollide().radius(d => getRadius(d) + 8))
```

#### **TopicFlowPanel.jsx** - Container Component
- **Features**:
  - "Update Topic Flow" button: Triggers incremental processing
  - Statistics display: Total triples, unique topics, avg frequency/confidence
  - Error handling and loading states
  - Empty state with helpful instructions

---

## Data Flow

### Complete Pipeline

```
[User sends message]
      ↓
[Message saved to DB with ID]
      ↓
[User clicks "Update Topic Flow"]
      ↓
[TopicFlowService.update_topic_flow()]
      ↓
┌─────────────────────────────────────────┐
│ 1. Fetch messages since last_processed │
│    (incremental update)                 │
└─────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────┐
│ 2. TopicExtractor.extract_from_messages()│
│    - Batch messages (10 per batch)      │
│    - Call LLM with extraction prompt    │
│    - Parse JSON response                │
│    - Deduplicate similar topics         │
└─────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────┐
│ 3. Compute co-occurrences               │
│    (topics appearing in nearby messages)│
└─────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────┐
│ 4. insert_or_update_topic()             │
│    - If exists: increment frequency     │
│    - If new: create row                 │
│    - Update co_occurrence links         │
└─────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────┐
│ 5. convert_to_d3_format()               │
│    - Build nodes array                  │
│    - Build links array                  │
│    - Calculate sizes from frequency     │
└─────────────────────────────────────────┘
      ↓
[Return {nodes, links, stats} to frontend]
      ↓
[TopicFlowVisualization renders graph]
```

---

## Key Design Decisions

### ✅ Content-Specific Topics (Not Generic)
**Problem**: Old system extracted "analysis", "learning", "discussion"
**Solution**: LLM prompt explicitly forbids meta-topics, requires concrete nouns

### ✅ Hierarchical Structure
**Problem**: Flat list of keywords
**Solution**: 3-level hierarchy captures semantic organization

### ✅ Tabular Storage (Single Source of Truth)
**Problem**: Data scattered across chat turns
**Solution**: `topic_flow` table as canonical storage

### ✅ Incremental Updates
**Problem**: Full recomputation on every update is slow
**Solution**: Track `last_seen_message_id`, only process new messages

### ✅ D3 Force-Directed Graph
**Problem**: Previous timeline visualization was incomplete
**Solution**: Force-directed layout with hierarchical + co-occurrence links

### ✅ Semantic Deduplication
**Problem**: "uncertainty score" and "confidence metric" created duplicate nodes
**Solution**: Word-overlap similarity merging during extraction

---

## Usage Examples

### 1. First Time Use
```javascript
// User sends messages
await fetch('/chat', {method: 'POST', body: {content: "How do I implement D3 graphs?"}})

// Click "Update Topic Flow" in UI
// → Processes ALL messages, extracts topics, creates graph

Result:
  Nodes: 5 topics, 8 subtopics, 12 subsubtopics
  Links: 25 hierarchy + 8 co-occurrence
```

### 2. Incremental Update
```javascript
// User sends 3 more messages
// Click "Update Topic Flow" again

// → Only processes new 3 messages
// → Updates existing topics or adds new ones
// → Graph smoothly updates
```

### 3. Full Reset
```javascript
// Click "Reset" button
// → Calls /topic-flow/reset
// → Clears topic_flow table
// → Next update reprocesses all messages
```

---

## LLM Prompt Design

The extraction prompt is critical. Key elements:

### ✅ Clear Rules
```
1. Extract CONCRETE topics, NOT generic meta-topics
   ✅ GOOD: "D3 force-directed graph"
   ❌ BAD: "analysis"

2. Three-level hierarchy:
   - topic: Main domain
   - subtopic: Subdivision
   - subsubtopic: Concrete detail
```

### ✅ Output Format
```json
[
  {
    "topic_label": "...",
    "subtopic_label": "...",
    "subsubtopic_label": "...",
    "confidence": 0.85,
    "keywords": ["...", "..."]
  }
]
```

### ✅ Examples (Few-Shot)
Prompt includes good/bad examples to guide LLM

---

## Performance Considerations

### Batching
- **Messages**: Processed in batches of 10
- **Reduces LLM API calls**: 100 messages → 10 API calls

### Incremental Updates
- **Only new messages**: Typical update processes 1-5 messages
- **Database upsert**: Efficient topic merging

### D3 Simulation
- **Force calculation**: Runs in browser, no server load
- **Collision detection**: Prevents node overlap

---

## Testing & Debugging

### Backend Tests
```python
# Test topic extraction
from topic_extraction import TopicExtractor
from openai import OpenAI

client = OpenAI(api_key="...", base_url="https://api.deepseek.com")
extractor = TopicExtractor(client)

messages = [
    {"id": 1, "role": "user", "content": "How do I build a D3 graph?"},
    {"id": 2, "role": "assistant", "content": "Use force simulation..."}
]

topics = extractor.extract_from_messages(messages)
print(topics)
```

### Frontend Tests
```javascript
// Test API endpoint
const response = await fetch('http://localhost:8000/topic-flow/update', {
  method: 'POST'
});
const data = await response.json();
console.log('Nodes:', data.nodes.length);
console.log('Links:', data.links.length);
```

### Common Issues

**1. No topics extracted**
- Check: Are messages in database?
- Check: Is LLM API key valid?
- Check: Look at backend logs for extraction errors

**2. Generic topics ("analysis", "learning")**
- Issue: LLM not following prompt
- Fix: Adjust temperature (lower = more consistent)
- Fix: Add more examples to prompt

**3. Graph nodes overlapping**
- Issue: Too many nodes
- Fix: Increase repulsion force (`forceManyBody().strength(-800)`)
- Fix: Adjust collision radius

**4. Incremental update not working**
- Check: `last_seen_message_id` in database
- Check: Message IDs are sequential
- Debug: Use `force_recompute=true` to reset

---

## Future Enhancements

### 1. Multi-Language Support
- Extract topics in user's language
- Translate topic labels for visualization

### 2. Topic Ranking
- Weight topics by importance (not just frequency)
- Use TF-IDF or other ranking algorithms

### 3. Temporal Analysis
- Show topic evolution over time
- Animate graph as conversation progresses

### 4. User Feedback Loop
- Allow users to merge/split topics
- Learn from corrections

### 5. Export & Sharing
- Export graph as image (PNG/SVG)
- Share topic summary as text

---

## File Structure

```
backend/
  ├── topic_extraction.py      # LLM-based extraction logic
  ├── topic_storage.py          # Database schema & persistence
  ├── topic_flow_service.py     # Orchestration & incremental updates
  └── main.py                   # API endpoints

frontend/vite-project/src/components/panels/
  ├── TopicFlowPanel.jsx        # Container with update button
  └── TopicFlowVisualization.jsx # D3 force-directed graph

database/
  └── chatlog.db
      ├── messages              # Source messages
      └── topic_flow            # Extracted topics (NEW)
```

---

## Summary

This redesigned Topic Flow system:

✅ **Extracts concrete topics** from conversation (not generic keywords)
✅ **Organizes hierarchically** (topic → subtopic → subsubtopic)
✅ **Persists in tabular format** (single source of truth)
✅ **Updates incrementally** (efficient, no full recomputation)
✅ **Visualizes as force-directed graph** (interactive, informative)

The system accurately reflects **what the user actually talked about**, providing meaningful insights into conversation structure and topics.
