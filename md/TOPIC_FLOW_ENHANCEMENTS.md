# Topic Flow D3 Visualization Enhancements

## Overview

Three major features have been added to the D3-based Topic Flow visualization while maintaining complete compatibility with the existing cluster layout, force simulation, and interactive features.

## Feature 1: Temporal Position for Top-Level Topics

### What It Does
Each top-level topic node now receives a `position` attribute representing its ordinal position in the temporal sequence of topic creation.

- Position is 0-based: first topic = 0, second topic = 1, etc.
- **Only applied to top-level (topic) nodes**
- Subtopics and detail nodes are NOT affected
- Enables the layout features below

### Implementation Details
```javascript
// In TopicFlowVisualization.jsx
const topicNodes = nodes.filter(n => n.level === 'topic');
topicNodes.forEach((node, index) => {
  node.position = index; // Temporal order
});
```

---

## Feature 2: Spiral / S-Shaped Layout for Top-Level Topics

### What It Does
Top-level topic circles are automatically positioned along either a **spiral path** or an **S-shaped path**, creating a visually organized timeline of topic emergence.

### Layout Types

#### Spiral
Topics spiral outward from the center in a logarithmic spiral pattern:
```
      Topic 3
    Topic 2
  Topic 1
Center
```

#### S-Shaped
Topics flow along an S-curve (sinusoidal wave):
```
Topic 4 ─── Topic 5
         ╲╱
      Topic 3
      ╱╲
Topic 1 ─── Topic 2
```

### Configuration

Located at the top of `TopicFlowVisualization.jsx`:

```javascript
const LAYOUT_CONFIG = {
  type: 'spiral',           // Choose: 'spiral' or 's-shaped'
  direction: 'top-bottom',  // Choose: 'top-bottom' or 'bottom-top'
  spacing: 80,              // Pixels between positions
  centerOffset: 150,        // Distance from center
  radiusMultiplier: 1.5     // Spiral only: radius growth factor
};
```

### Direction Options

| Direction | Flow | Use Case |
|-----------|------|----------|
| `'top-bottom'` | Earlier topics at top, later at bottom | Standard timeline reading |
| `'bottom-top'` | Earlier topics at bottom, later at top | Reverse chronological |

### Tuning Parameters

- **spacing**: Increase to spread topics further apart (default: 80)
- **centerOffset**: Increase to push spiral/S-curve away from center (default: 150)
- **radiusMultiplier** (spiral only): Control how quickly spiral expands
  - Lower values (0.5-1.0): tighter spiral
  - Higher values (1.5-2.5): wider spiral

### How It Works

1. Force simulation runs normally, positioning clusters
2. After each tick, top-level topics are repositioned along the spiral/S-curve
3. Velocity is damped (×0.3) to prevent oscillation from the layout path
4. Subtopics naturally follow their parent topic via force links
5. **Original cluster layout remains intact** — only top-level topics are overridden

---

## Feature 3: Semantic Similarity-Based Color Assignment

### What It Does
When creating a new topic:
1. Compute semantic similarity with all previously created topics
2. If similarity ≥ threshold: **reuse the color of the most similar topic**
3. Otherwise: **assign a new distinct color**
4. Color assignments persist across renders

### Similarity Methods

#### Keyword Overlap (Default)
Combines label word overlap with keyword set intersection:
```
similarity = (label_overlap × 0.6) + (keyword_overlap × 0.4)
```

**Advantages:**
- Fast computation
- Keyword-aware
- Good for topic-specific domains

**Example:**
- "Trust Metrics" vs "Trust Calibration" → High similarity (shared word)
- "Entropy Calculation" vs "Information Theory" → Medium similarity (keyword overlap)

#### Edit Distance (Levenshtein)
Normalized edit distance between topic labels:
```
similarity = 1 - (levenshtein_distance / max_length)
```

**Advantages:**
- String-based similarity
- Good for typos and variations
- Language-aware

**Example:**
- "Topic A" vs "Topic B" → Low similarity
- "Calibration" vs "Calibration" → Perfect match (1.0)

### Configuration

```javascript
const SIMILARITY_CONFIG = {
  threshold: 0.6,           // Similarity threshold (0-1)
  method: 'keyword-overlap' // Choose: 'keyword-overlap' or 'edit-distance'
};
```

### Threshold Tuning

| Threshold | Behavior | Use Case |
|-----------|----------|----------|
| 0.3-0.4 | Aggressive color reuse | Related domains (semantically loose) |
| 0.5-0.7 | Balanced (default 0.6) | General conversations |
| 0.8-1.0 | Conservative | Strict semantic matching |

### Color Reuse Example

```
Topic 1: "Trust Metrics"           → Color: Blue
Topic 2: "Trust Calibration"       → Color: Blue (0.75 similarity ≥ 0.6)
Topic 3: "Visualization"           → Color: Purple (0.15 similarity < 0.6)
Topic 4: "Trust Analysis"          → Color: Blue (0.82 similarity ≥ 0.6)
Topic 5: "User Experience"         → Color: Green (0.10 similarity < 0.6)
```

### Persistence

Color mappings are maintained in component state (`colorMapRef`) and survive:
- Component re-renders
- Animation frames
- Zoom/pan interactions

To persist across sessions, extend with:
```javascript
// Optional: Save to localStorage
const savedColorMap = localStorage.getItem('topicColorMap');
if (savedColorMap) {
  colorMapRef.current = JSON.parse(savedColorMap);
}

// After coloring:
localStorage.setItem('topicColorMap', JSON.stringify(colorMapRef.current));
```

---

## Implementation Architecture

### File Structure
```
frontend/vite-project/src/components/panels/
├── TopicFlowPanel.jsx          (unchanged)
└── TopicFlowVisualization.jsx  (enhanced with all three features)
```

### Key Functions Added

#### Layout
- `getTopicPositionOnSpiral(position, width, height)` → {x, y}
- `getTopicPositionOnSCurve(position, width, height)` → {x, y}
- `getTopLevelTopicCoordinates(position, width, height)` → {x, y}

#### Similarity
- `calculateSimilarity(label1, label2, keywords1, keywords2)` → float
- `calculateEditDistanceSimilarity(s1, s2)` → float
- `assignColorsWithSimilarity(topicNodes, existingColorMap)` → Object

#### Color Management
- `buildColorMap(nodes, links)` → Object (updated with similarity logic)

### Data Flow

```
Raw Data (nodes + links)
    ↓
normalizeData() [existing]
    ↓
TopicFlowVisualization component
    ↓
├─ Assign position to topic nodes
├─ Build color map with similarity
│
├─ Create force simulation [existing]
│
├─ On each simulation tick:
│  ├─ Override top-level topic positions (spiral/S-curve)
│  ├─ Update link positions [existing]
│  └─ Update node positions [existing]
│
└─ Render D3 visualization [existing]
```

### Backward Compatibility

✅ **All changes are non-breaking:**
- Existing force simulation untouched
- New `position` attribute only on topic nodes
- Fallback colors if similarity not computable
- Layout override only affects top-level nodes
- Subtopic layout completely unchanged

---

## Usage Examples

### Example 1: Strict Chronological Spiral
```javascript
const LAYOUT_CONFIG = {
  type: 'spiral',
  direction: 'top-bottom',
  spacing: 100,
  centerOffset: 120,
  radiusMultiplier: 1.2
};
```

### Example 2: Bottom-Up S-Curve
```javascript
const LAYOUT_CONFIG = {
  type: 's-shaped',
  direction: 'bottom-top',
  spacing: 90,
  centerOffset: 180
};
```

### Example 3: Loose Color Grouping
```javascript
const SIMILARITY_CONFIG = {
  threshold: 0.4,      // Aggressive reuse
  method: 'keyword-overlap'
};
```

### Example 4: Strict Color Uniqueness
```javascript
const SIMILARITY_CONFIG = {
  threshold: 0.85,     // Conservative reuse
  method: 'edit-distance'
};
```

---

## Testing Checklist

- [ ] Load visualization with multiple topics
- [ ] Verify top-level topics arrange along spiral/S-curve
- [ ] Verify subtopics cluster around parent topics
- [ ] Verify colors reuse for similar topics
- [ ] Verify distinct colors for dissimilar topics
- [ ] Test zoom/pan still works smoothly
- [ ] Test hover interactions on topics
- [ ] Verify force simulation continues after layout override
- [ ] Test with both layout types and directions
- [ ] Test with both similarity methods

---

## Performance Notes

- **Layout calculation**: O(n) per simulation tick where n = topic nodes
- **Similarity computation**: O(m²) where m = number of topic nodes (one-time at render)
- **D3 force simulation**: Unchanged, no performance impact from new features
- **Memory**: Minimal overhead (position attribute + color map)

### Optimization Tips
If performance is an issue with many topics:
1. Increase `LAYOUT_CONFIG.spacing` to reduce clustering
2. Use `keyword-overlap` similarity (faster than edit-distance)
3. Increase `SIMILARITY_CONFIG.threshold` to reduce comparisons

---

## Debugging

Enable console logging in TopicFlowVisualization.jsx:

```javascript
// Line ~502
console.log(`[TopicFlowVisualization] Added position attributes to ${topicNodes.length} top-level topics`);

// Add custom logging:
console.log('[Layout] Top-level topic positions:', topicNodes.map(n => ({
  id: n.id,
  position: n.position,
  x: n.x,
  y: n.y
})));

console.log('[Colors] Color map:', colorMapRef.current);
```

---

## Future Enhancements

Possible extensions (not implemented, but architectural support):

1. **Interactive layout switching**: UI button to toggle spiral ↔ S-curve
2. **Dynamic threshold adjustment**: Slider to adjust similarity threshold in real-time
3. **Color persistence**: LocalStorage/IndexedDB for cross-session color stability
4. **Layout animations**: Smooth transitions when topics enter/exit
5. **Custom path layouts**: User-defined parametric curves

---

## Summary

| Feature | Status | Impact |
|---------|--------|--------|
| Temporal position | ✅ Complete | Enables layout features |
| Spiral layout | ✅ Complete | Visual timeline encoding |
| S-shaped layout | ✅ Complete | Alternative timeline layout |
| Similarity-based colors | ✅ Complete | Semantic color grouping |
| Backward compatibility | ✅ Complete | No breaking changes |

All three features work together to create a more intuitive, semantically-aware topic flow visualization while preserving the original D3 cluster dynamics.
