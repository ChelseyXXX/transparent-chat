# Topic Flow System - Visual Guide

## 1. Old vs New System

### OLD SYSTEM ❌
```
User Message → Extract Keywords → Store in chat turn → Display timeline
                    ↓
              "analysis"
              "learning"
              "discussion"
```

**Problems:**
- Generic, meaningless topics
- Only from last turn
- No hierarchy
- Timeline incomplete
- No persistence

---

### NEW SYSTEM ✅
```
All Conversation History
         ↓
    LLM Extraction (batched)
         ↓
    topic → subtopic → subsubtopic
         ↓
    Database Table (topic_flow)
         ↓
    D3 Force-Directed Graph
```

**Improvements:**
- Concrete topics ("D3 force-directed graph")
- From ALL messages
- 3-level hierarchy
- Interactive graph
- Persistent storage
- Incremental updates

---

## 2. Topic Hierarchy Example

```
📊 Conversation about building a chat app

┌─────────────────────────────────────────┐
│  TOPIC: "Chat Application Development"  │  ← Main domain
└─────────────────────────────────────────┘
             ↓
    ┌────────────────────────────────┐
    │  SUBTOPIC: "Frontend UI"       │  ← Functional subdivision
    └────────────────────────────────┘
             ↓
    ┌────────────────────────────────┐
    │  SUBSUBTOPIC: "React hooks"    │  ← Concrete detail
    └────────────────────────────────┘

             ↓
    ┌────────────────────────────────┐
    │  SUBTOPIC: "Backend API"       │
    └────────────────────────────────┘
             ↓
    ┌────────────────────────────────┐
    │  SUBSUBTOPIC: "FastAPI routes" │
    └────────────────────────────────┘

┌─────────────────────────────────────────┐
│  TOPIC: "Database Design"               │
└─────────────────────────────────────────┘
             ↓
    ┌────────────────────────────────┐
    │  SUBTOPIC: "SQLite schema"     │
    └────────────────────────────────┘
             ↓
    ┌────────────────────────────────┐
    │  SUBSUBTOPIC: "messages table" │
    └────────────────────────────────┘
```

---

## 3. Database Schema Visual

```sql
topic_flow table
┌─────────────────┬──────────────────────────────────────────┐
│ topic_id        │ "chat-app::frontend-ui::react-hooks"     │  ← Unique ID
├─────────────────┼──────────────────────────────────────────┤
│ topic_label     │ "Chat Application Development"           │  ← Level 1
│ subtopic_label  │ "Frontend UI"                            │  ← Level 2
│ subsubtopic_l.. │ "React hooks"                            │  ← Level 3
├─────────────────┼──────────────────────────────────────────┤
│ first_seen_m... │ 5                                        │  ← Message ID
│ last_seen_mes.. │ 12                                       │  ← Message ID
│ frequency       │ 3                                        │  ← Appearances
│ confidence      │ 0.85                                     │  ← 0-1 score
├─────────────────┼──────────────────────────────────────────┤
│ keywords        │ ["react", "hooks", "useState", ...]      │  ← JSON array
│ co_occurrence   │ ["chat-app::backend-api::...", ...]      │  ← Related IDs
├─────────────────┼──────────────────────────────────────────┤
│ created_at      │ 2024-01-01 10:00:00                      │
│ updated_at      │ 2024-01-01 10:15:00                      │
└─────────────────┴──────────────────────────────────────────┘
```

**Key:**
- Each row = one (topic, subtopic, subsubtopic) triple
- `frequency` increments when topic reappears
- `co_occurrence` links to related topics
- `first_seen` / `last_seen` track provenance

---

## 4. D3 Graph Structure

### Node Types

```
     ⬤  Large (25-45px)
    Topic
    Color: Indigo (#6366f1)
    
         ⬤  Medium (18-30px)
       Subtopic
       Color: Purple (#8b5cf6)
       
             ⬤  Small (12-22px)
           Subsubtopic
           Color: Pink (#ec4899)
```

### Link Types

```
─────────  Hierarchy Link (solid gray)
           Connects: topic → subtopic → subsubtopic
           
- - - - -  Co-occurrence Link (dashed orange)
           Connects: related subsubtopics
```

### Example Graph

```
         ⬤ Chat App
        ╱ ╲
       ╱   ╲
      ⬤     ⬤ Database
   Frontend  ╲
      ╱ ╲     ╲
     ╱   ╲     ╲
    ⬤     ⬤     ⬤
  React  WebSocket  SQLite
    ╲     ╱
     ╲   ╱  (co-occurrence link)
      ╲ ╱
       ╳
```

---

## 5. Update Flow Diagram

```
┌──────────────────┐
│ User clicks      │
│ "Update Topic    │
│ Flow" button     │
└─────────┬────────┘
          ↓
┌─────────────────────────────────────────┐
│ Frontend: POST /topic-flow/update       │
└─────────┬───────────────────────────────┘
          ↓
┌─────────────────────────────────────────┐
│ Backend: Get messages from DB           │
│   last_processed_id = 10                │
│   new_messages = [11, 12, 13]           │
└─────────┬───────────────────────────────┘
          ↓
┌─────────────────────────────────────────┐
│ TopicExtractor: Process new messages    │
│   Batch 1: messages 11-13               │
│   LLM call → extract topics             │
│   Result: 2 topic triples               │
└─────────┬───────────────────────────────┘
          ↓
┌─────────────────────────────────────────┐
│ Database: Insert or update              │
│   Triple 1: EXISTS → frequency++        │
│   Triple 2: NEW → insert row            │
└─────────┬───────────────────────────────┘
          ↓
┌─────────────────────────────────────────┐
│ Convert to D3 format                    │
│   Nodes: 15 (5 topics, 7 sub, 3 subsub)│
│   Links: 22 (14 hierarchy, 8 co-occur) │
└─────────┬───────────────────────────────┘
          ↓
┌─────────────────────────────────────────┐
│ Return JSON to frontend                 │
│   {nodes, links, stats, processed: 3}   │
└─────────┬───────────────────────────────┘
          ↓
┌─────────────────────────────────────────┐
│ D3: Render force-directed graph         │
│   - Position nodes with forces          │
│   - Draw links between nodes            │
│   - Enable hover/drag/zoom              │
└─────────────────────────────────────────┘
```

---

## 6. Incremental Update Example

### Scenario: User has 10 messages, sends 2 more

**State 1: Initial**
```
Messages: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
Topics extracted: 8 triples
Last processed: message ID 10
```

**Event: User sends messages 11, 12**
```
Messages: 1, 2, ..., 10, [11, 12]  ← New
```

**Update Process:**
```
1. Check last_processed_id = 10
2. Filter new messages: [11, 12]
3. Extract topics from ONLY [11, 12]
   - Topic A: "New concept" → NEW → insert
   - Topic B: "Previous topic" → EXISTS → frequency++
4. Update last_processed_id = 12
5. Return updated graph
```

**State 2: After Update**
```
Messages: 1, 2, ..., 10, 11, 12
Topics extracted: 9 triples (1 new, 1 updated)
Last processed: message ID 12
```

**Efficiency:**
- ❌ Old: Reprocess all 12 messages (slow)
- ✅ New: Process only 2 messages (fast)

---

## 7. Topic Extraction Prompt Visual

```
┌─────────────────────────────────────────────────────┐
│  LLM SYSTEM PROMPT                                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  RULES:                                             │
│  1. Extract CONCRETE topics (not "analysis")        │
│  2. Three levels: topic → subtopic → subsubtopic    │
│  3. Include confidence score (0-1)                  │
│  4. List 3-5 keywords per topic                     │
│                                                     │
│  OUTPUT FORMAT:                                     │
│  [                                                  │
│    {                                                │
│      "topic_label": "...",                          │
│      "subtopic_label": "...",                       │
│      "subsubtopic_label": "...",                    │
│      "confidence": 0.85,                            │
│      "keywords": [...]                              │
│    }                                                │
│  ]                                                  │
│                                                     │
│  EXAMPLES:                                          │
│  ✅ Good: "D3 Visualization" → "Force Graph" →      │
│           "collision detection"                     │
│  ❌ Bad: "Analysis" → "Processing" → "General"      │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│  USER INPUT                                         │
├─────────────────────────────────────────────────────┤
│  [1] USER: How do I implement D3 graphs?           │
│  [2] ASSISTANT: Use d3.forceSimulation() with...   │
│  [3] USER: What about collision detection?         │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│  LLM OUTPUT                                         │
├─────────────────────────────────────────────────────┤
│  [                                                  │
│    {                                                │
│      "topic_label": "D3 Visualization",             │
│      "subtopic_label": "Force-Directed Graph",      │
│      "subsubtopic_label": "forceSimulation API",    │
│      "confidence": 0.9,                             │
│      "keywords": ["D3", "force", "simulation"]      │
│    },                                               │
│    {                                                │
│      "topic_label": "D3 Visualization",             │
│      "subtopic_label": "Force-Directed Graph",      │
│      "subsubtopic_label": "collision detection",    │
│      "confidence": 0.85,                            │
│      "keywords": ["collision", "forceCollide"]      │
│    }                                                │
│  ]                                                  │
└─────────────────────────────────────────────────────┘
```

---

## 8. Frontend Component Structure

```
TopicFlowPanel.jsx
├── State Management
│   ├── topicFlowData (nodes, links)
│   ├── isLoading
│   ├── stats
│   └── error
│
├── Functions
│   ├── loadTopicFlow() → GET /topic-flow
│   └── updateTopicFlow() → POST /topic-flow/update
│
└── Render
    ├── Header (description + stats)
    ├── Controls ("Update" button)
    ├── Error message (if any)
    └── TopicFlowVisualization
        │
        ├── D3 Setup
        │   ├── SVG container
        │   ├── Zoom behavior
        │   └── Tooltip
        │
        ├── Force Simulation
        │   ├── forceLink (hierarchy + co-occurrence)
        │   ├── forceManyBody (repulsion)
        │   ├── forceCenter (centering)
        │   └── forceCollide (collision)
        │
        ├── Visual Elements
        │   ├── Links (lines)
        │   ├── Nodes (circles)
        │   └── Labels (text)
        │
        └── Interactions
            ├── Hover (highlight + tooltip)
            ├── Drag (reposition)
            ├── Zoom/Pan
            └── Click (callback)
```

---

## 9. Data Transformation Pipeline

```
Raw Conversation
└─ Messages: [{id, role, content, timestamp}, ...]
         ↓
   Topic Extraction
└─ Topics: [{topic_label, subtopic_label, subsubtopic_label, ...}, ...]
         ↓
   Database Storage
└─ Rows in topic_flow table
         ↓
   D3 Conversion
└─ Graph Format:
   {
     nodes: [
       {id: "topic1", label: "...", level: "topic", size: 25},
       {id: "topic1::sub1", label: "...", level: "subtopic", size: 18},
       ...
     ],
     links: [
       {source: "topic1", target: "topic1::sub1", type: "hierarchy"},
       ...
     ]
   }
         ↓
   D3 Rendering
└─ Force-directed graph visualization
```

---

## 10. Interaction Examples

### Hover on Node
```
Before:                After:
  ⬤ Node A              ⬤ Node A (highlighted)
  │                     │
  ⬤ Node B              ⬤ Node B (highlighted)
                        │
  ⬤ Node C              ⚫ Node C (dimmed)
                        
                        + Tooltip appears:
                        ┌──────────────────┐
                        │ Node A           │
                        │ Level: topic     │
                        │ Frequency: 3     │
                        │ Confidence: 85%  │
                        └──────────────────┘
```

### Drag Node
```
Before:                After:
  ⬤ A ─── ⬤ B           ⬤ A
                           ╲
                            ╲
                             ⬤ B (moved)
```

### Zoom
```
Before:                After (zoomed in):
  ⬤ ─ ⬤ ─ ⬤            ⬤────⬤────⬤
  Nodes small           Nodes large
```

---

## 11. Testing Workflow Visual

```
1. Setup
   ├─ Install dependencies
   ├─ Configure .env
   └─ Start servers

2. Run Tests
   └─ python backend/test_topic_flow.py
      ├─ ✅ LLM connection
      ├─ ✅ Topic extraction
      ├─ ✅ Database storage
      ├─ ✅ D3 conversion
      └─ ✅ Incremental update

3. Manual Testing
   ├─ Send messages in UI
   ├─ Click "Update Topic Flow"
   └─ Verify graph renders

4. Verification
   ├─ Check backend logs
   ├─ Inspect database: SELECT * FROM topic_flow
   └─ Test interactions (hover/drag/zoom)
```

---

## 12. Performance Visualization

```
Number of Messages vs Processing Time

Messages │
100      │              ●  (50s - full recompute)
         │
50       │         ●  (25s)
         │
20       │    ●  (10s)
         │
10       │  ●  (5s)
         │●  (2s - incremental update for 5 new msgs)
         └────────────────────────────
           Time (seconds)

Legend:
● = Full recompute (process all messages)
● = Incremental update (process only new messages)
```

---

## 13. Success Criteria Checklist

```
Backend:
☐ topic_extraction.py created
☐ topic_storage.py created
☐ topic_flow_service.py created
☐ API endpoints added to main.py
☐ Test script passes

Frontend:
☐ TopicFlowVisualization.jsx rewritten
☐ TopicFlowPanel.jsx rewritten
☐ D3 graph renders
☐ Interactions work (hover/drag/zoom)

Database:
☐ topic_flow table created
☐ Indices created
☐ Data persists across sessions

Quality:
☐ Topics are content-specific (not generic)
☐ Hierarchy is meaningful
☐ Incremental updates work
☐ Graph is informative and clear

Documentation:
☐ TOPIC_FLOW_REDESIGN.md
☐ TOPIC_FLOW_QUICKSTART.md
☐ TOPIC_FLOW_IMPLEMENTATION_SUMMARY.md
☐ TOPIC_FLOW_VISUAL_GUIDE.md (this file)
```

---

## Conclusion

This visual guide illustrates the complete Topic Flow system architecture, from data extraction to interactive visualization. The system transforms raw conversation into a hierarchical, queryable, and visual representation of discussion topics.

**Key Visual Concepts:**
- 🔵 Three-level hierarchy (topic → subtopic → subsubtopic)
- 🔴 Force-directed graph (not timeline)
- 🟢 Incremental updates (efficiency)
- 🟡 Database-driven (single source of truth)
- 🟣 Interactive visualization (hover/drag/zoom)

The visual design ensures topics are **concrete, meaningful, and accurately reflect what the user talked about**.
