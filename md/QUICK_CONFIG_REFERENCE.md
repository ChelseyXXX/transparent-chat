# Quick Configuration Reference

## Location
File: `frontend/vite-project/src/components/panels/TopicFlowVisualization.jsx`
Lines: 27-45 (LAYOUT_CONFIG and SIMILARITY_CONFIG objects)

## Copy-Paste Configurations

### 1. Clockwise Spiral (Default)
```javascript
const LAYOUT_CONFIG = {
  type: 'spiral',
  direction: 'top-bottom',
  spacing: 80,
  centerOffset: 150,
  radiusMultiplier: 1.5
};
```

### 2. Tight Counter-Clockwise Spiral
```javascript
const LAYOUT_CONFIG = {
  type: 'spiral',
  direction: 'bottom-top',
  spacing: 60,
  centerOffset: 120,
  radiusMultiplier: 1.2
};
```

### 3. Loose Outward Spiral
```javascript
const LAYOUT_CONFIG = {
  type: 'spiral',
  direction: 'top-bottom',
  spacing: 120,
  centerOffset: 200,
  radiusMultiplier: 2.0
};
```

### 4. S-Curve from Top
```javascript
const LAYOUT_CONFIG = {
  type: 's-shaped',
  direction: 'top-bottom',
  spacing: 80,
  centerOffset: 150
};
```

### 5. S-Curve from Bottom
```javascript
const LAYOUT_CONFIG = {
  type: 's-shaped',
  direction: 'bottom-top',
  spacing: 100,
  centerOffset: 180
};
```

### 6. Aggressive Color Reuse (Related Topics)
```javascript
const SIMILARITY_CONFIG = {
  threshold: 0.4,
  method: 'keyword-overlap'
};
```

### 7. Moderate Color Reuse (Default)
```javascript
const SIMILARITY_CONFIG = {
  threshold: 0.6,
  method: 'keyword-overlap'
};
```

### 8. Conservative Color Reuse (Distinct Topics)
```javascript
const SIMILARITY_CONFIG = {
  threshold: 0.8,
  method: 'edit-distance'
};
```

### 9. Never Reuse Colors
```javascript
const SIMILARITY_CONFIG = {
  threshold: 1.0,
  method: 'keyword-overlap'
};
```

### 10. Always Reuse Colors
```javascript
const SIMILARITY_CONFIG = {
  threshold: 0.0,
  method: 'keyword-overlap'
};
```

## Tuning Guide

### Layout Feels Too Crowded
→ Increase `spacing` (default: 80 → try 120)
→ Increase `centerOffset` (default: 150 → try 200)

### Layout Feels Too Sparse
→ Decrease `spacing` (default: 80 → try 50)
→ Decrease `centerOffset` (default: 150 → try 100)

### Spiral Expands Too Fast
→ Decrease `radiusMultiplier` (default: 1.5 → try 1.0)

### Spiral Expands Too Slow
→ Increase `radiusMultiplier` (default: 1.5 → try 2.5)

### Colors Group Too Aggressively
→ Increase threshold (default: 0.6 → try 0.8)

### Colors Too Spread Out
→ Decrease threshold (default: 0.6 → try 0.4)

### Need Language-Aware Similarity
→ Switch method: `'keyword-overlap'` → `'edit-distance'`

### Need Faster Computation
→ Switch method: `'edit-distance'` → `'keyword-overlap'`

## Parameter Ranges

| Parameter | Min | Default | Max | Unit |
|-----------|-----|---------|-----|------|
| spacing | 30 | 80 | 200 | px |
| centerOffset | 50 | 150 | 300 | px |
| radiusMultiplier | 0.5 | 1.5 | 3.0 | factor |
| threshold | 0.0 | 0.6 | 1.0 | ratio |

## Enable Debug Logging

Add after line 502 in TopicFlowVisualization.jsx:

```javascript
console.log('[Layout] Top-level positions:', 
  topicNodes.map(n => ({ label: n.label, position: n.position }))
);
console.log('[Colors] Color map:', colorMapRef.current);
console.log('[Similarity] Config:', SIMILARITY_CONFIG);
```

## Test with Terminal

No frontend build needed for config changes — just refresh browser after editing.

## Verify Changes

Open DevTools Console and look for:
```
[TopicFlowVisualization] Added position attributes to N top-level topics
```

## Rollback

Restore default configuration:
```javascript
const LAYOUT_CONFIG = {
  type: 'spiral',
  direction: 'top-bottom',
  spacing: 80,
  centerOffset: 150,
  radiusMultiplier: 1.5
};

const SIMILARITY_CONFIG = {
  threshold: 0.6,
  method: 'keyword-overlap'
};
```
