# Topic Flow - Quick Start Guide

## Prerequisites

1. **Backend dependencies** installed:
   ```bash
   cd backend
   pip install openai python-dotenv
   ```

2. **DeepSeek API key** configured in `backend/.env`:
   ```
   DEEPSEEK_API_KEY=your_key_here
   ```

3. **Backend server** running:
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```

4. **Frontend server** running:
   ```bash
   cd frontend/vite-project
   npm run dev
   ```

---

## Testing the New Topic Flow

### Step 1: Have a Conversation

1. Open the app: http://localhost:5173
2. Login or register
3. Send a few messages about specific topics:

   **Example conversation:**
   ```
   User: "How do I implement a D3 force-directed graph for topic visualization?"
   
   Assistant: "To implement a D3 force-directed graph, you'll use d3.forceSimulation()..."
   
   User: "What about hierarchical clustering? Can I group nodes by topic?"
   
   Assistant: "Yes! You can use force groups or manual clustering..."
   
   User: "How do I handle node collisions?"
   
   Assistant: "Use d3.forceCollide() with radius parameters..."
   ```

### Step 2: Update Topic Flow

1. Click **"Insights"** tab (top right)
2. Navigate to **"Topic Flow"** panel
3. Click **"🔄 Update Topic Flow"** button
4. Wait 5-10 seconds for processing

### Step 3: Explore the Graph

You should see:
- **Large nodes** (indigo): Main topics (e.g., "D3 Visualization")
- **Medium nodes** (purple): Subtopics (e.g., "Force-Directed Graph")
- **Small nodes** (pink): Details (e.g., "collision detection")

**Interactions:**
- **Hover** over nodes: See metadata (frequency, confidence, keywords)
- **Drag** nodes: Reposition the graph
- **Scroll** to zoom in/out
- Nodes highlight their connected neighbors on hover

---

## Verification Checklist

### ✅ Backend Working
```bash
# Test API endpoints
curl http://localhost:8000/topic-flow
# Should return: {"nodes": [...], "links": [...], "stats": {...}}

curl -X POST http://localhost:8000/topic-flow/update
# Should return: {"nodes": [...], "processed_count": N, "is_incremental": true}
```

### ✅ Topics Extracted
Check backend logs for:
```
[TopicFlowService] Processing 3 messages (incremental=True)
[TopicFlowService] Extracted 5 topic triples
```

### ✅ Database Populated
```bash
cd backend
sqlite3 chatlog.db
sqlite> SELECT COUNT(*) FROM topic_flow;
# Should show number of extracted topic triples

sqlite> SELECT topic_label, subtopic_label, subsubtopic_label, frequency FROM topic_flow LIMIT 5;
# Should show actual topics
```

### ✅ Frontend Visualization
- Graph renders without errors
- Nodes are positioned (not stacked)
- Links connect nodes
- Legend shows in top-right
- Controls hint shows in bottom-left

---

## Common Issues & Fixes

### Issue: "No topics extracted"
**Symptoms**: Graph empty after update
**Fixes**:
1. Check backend logs for LLM errors
2. Verify DeepSeek API key is valid
3. Ensure messages exist in database:
   ```sql
   SELECT COUNT(*) FROM messages;
   ```

### Issue: "Generic topics extracted" (e.g., "analysis")
**Symptoms**: Topics like "learning", "discussion", "knowledge"
**Fixes**:
1. LLM not following prompt properly
2. Lower temperature in `topic_extraction.py`:
   ```python
   temperature=0.2  # More consistent (was 0.3)
   ```
3. Add conversation context to prompt

### Issue: "Graph nodes overlapping"
**Symptoms**: All nodes clustered in center
**Fixes**:
1. Increase repulsion force in `TopicFlowVisualization.jsx`:
   ```javascript
   .force('charge', d3.forceManyBody()
     .strength(d => d.level === 'topic' ? -1200 : -400)  // Increase
   )
   ```
2. Decrease link distance:
   ```javascript
   .distance(d => d.type === 'hierarchy' ? 60 : 120)  // Decrease
   ```

### Issue: "Update button doesn't work"
**Symptoms**: Clicking button does nothing
**Fixes**:
1. Check browser console for CORS errors
2. Verify backend is running on port 8000
3. Check frontend is fetching correct URL:
   ```javascript
   fetch('http://localhost:8000/topic-flow/update')
   ```

### Issue: "Backend crashes on update"
**Symptoms**: 500 error, backend logs show traceback
**Fixes**:
1. Check for missing dependencies:
   ```bash
   pip install openai python-dotenv
   ```
2. Verify database schema exists:
   ```sql
   .schema topic_flow
   ```
3. Check LLM response parsing errors in logs

---

## Test with Sample Data

If you want to test without manual chatting:

### Script: Inject Test Messages

```python
# backend/inject_test_messages.py
from database import get_conn

messages = [
    ("user", "How do I implement a D3 force-directed graph?"),
    ("assistant", "Use d3.forceSimulation() with forceLink and forceManyBody..."),
    ("user", "What about hierarchical clustering?"),
    ("assistant", "You can group nodes by topic using force groups..."),
    ("user", "How do I handle node collisions?"),
    ("assistant", "Use d3.forceCollide() with radius parameters..."),
]

conn = get_conn()
c = conn.cursor()

for role, content in messages:
    c.execute("INSERT INTO messages (role, content) VALUES (?, ?)", (role, content))

conn.commit()
conn.close()
print(f"Inserted {len(messages)} test messages")
```

Run:
```bash
cd backend
python inject_test_messages.py
```

Then click "Update Topic Flow" in the UI.

---

## Expected Results

After following the steps above, you should see:

### Statistics
```
📊 5-10 triples
🏷️ 2-4 topics
📈 Avg freq: 1.2
✨ Avg conf: 75-85%
```

### Graph Structure
```
[D3 Visualization] (large indigo node)
  ├─ [Force-Directed Graph] (medium purple node)
  │   ├─ [forceSimulation method] (small pink node)
  │   └─ [collision detection] (small pink node)
  └─ [Hierarchical Clustering] (medium purple node)
      └─ [topic grouping] (small pink node)
```

### Sample Topic Triple
```json
{
  "topic_id": "d3-visualization::force-directed-graph::forcesimulation-method",
  "topic_label": "D3 Visualization",
  "subtopic_label": "Force-Directed Graph",
  "subsubtopic_label": "forceSimulation method",
  "frequency": 2,
  "confidence": 0.85,
  "keywords": ["D3", "force", "simulation", "graph"]
}
```

---

## Next Steps

Once basic functionality works:

1. **Test incremental updates**: Send more messages, click update again
2. **Test full recompute**: Click "♻️ Reset" button
3. **Test edge cases**: Empty conversation, single message, very long messages
4. **Customize visualization**: Adjust colors, sizes, forces in `TopicFlowVisualization.jsx`
5. **Tune extraction**: Modify prompt in `topic_extraction.py` for better quality

---

## Debugging Tips

### Enable Verbose Logging

**Backend** (`main.py`):
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Frontend** (Browser Console):
- Network tab: Check API requests/responses
- Console tab: Look for React errors

### Inspect Database

```bash
cd backend
sqlite3 chatlog.db

# View all topics
SELECT * FROM topic_flow;

# Count topics by level
SELECT topic_label, COUNT(*) FROM topic_flow GROUP BY topic_label;

# View recent messages
SELECT id, role, content FROM messages ORDER BY id DESC LIMIT 10;
```

### Test API Manually

```bash
# Get current graph
curl http://localhost:8000/topic-flow | jq

# Trigger update
curl -X POST http://localhost:8000/topic-flow/update | jq

# Reset
curl -X POST http://localhost:8000/topic-flow/reset
```

---

## Success Criteria

✅ Backend extracts topics without errors
✅ Database contains topic_flow rows
✅ API returns valid graph data
✅ Frontend renders force-directed graph
✅ Graph shows concrete topics (not generic)
✅ Incremental updates work (only new messages processed)
✅ Hover/drag/zoom interactions functional

---

## Need Help?

Check:
1. Backend logs in terminal
2. Browser console (F12)
3. Network tab for API errors
4. Database content: `SELECT * FROM topic_flow LIMIT 5;`

If issues persist:
- Verify all dependencies installed
- Check API key is valid
- Ensure ports 8000 and 5173 are free
- Try full reset and reprocess
