# Linguistic Calibration - UI Update Test Guide

## ✅ Changes Made

### 1. **Backend**
- ✅ Added `linguistic_calibration.py` module
- ✅ Integrated into `/chat` streaming endpoint
- ✅ Added debug logging in `main.py`

### 2. **Frontend - Confidence Panel (COMPLETELY REWRITTEN)**
- ❌ **DELETED:** Old Gauge Chart (semicircle with %)
- ❌ **DELETED:** Progress Bar UI
- ❌ **DELETED:** Percentage Scores (82%, etc.)
- ✅ **ADDED:** Traffic Light Badge (Green/Yellow/Red)
- ✅ **ADDED:** Icon indicators (✓ / ⚠)
- ✅ **ADDED:** User-friendly summary text
- ✅ **ADDED:** Legend explaining what each color means
- ✅ **ADDED:** Debug panel (development mode only)

### 3. **Frontend - Data Flow**
- ✅ `backend.js`: Extract calibration from SSE stream
- ✅ `ChatLayout.jsx`: Store calibration in state
- ✅ `ChatLayout.jsx`: Pass calibration to InsightsPanel
- ✅ `InsightsPanel.jsx`: Added new "Linguistic Confidence" section
- ✅ All with debug console logging

### 4. **Frontend - Message Badges**
- ✅ Display calibration badge below each assistant message
- ✅ Color-coded (green/yellow/red)
- ✅ Shows confidence level + summary

---

## 🧪 Testing Steps

### Step 1: Check Backend Logs

1. **Start the backend:**
   ```bash
   cd backend
   python main.py
   ```

2. **Watch for debug logs** when sending a message:
   ```
   [DEBUG] Calibration result: {'confidence_level': 'High', 'visual_signal': 'green', ...}
   [DEBUG] Sending completion_data: ...
   ```

---

### Step 2: Check Frontend Console

1. **Open browser DevTools** (F12)
2. **Go to Console tab**
3. **Send a message in the chat**

You should see these logs:
```
[backend.js] Received "done" event with calibration: {confidence_level: "High", visual_signal: "green", ...}
[ChatLayout] Received calibration data: {confidence_level: "High", ...}
[ChatLayout] Updated message: {content: "...", calibration: {...}, ...}
[ChatLayout] Updated latestCalibration: {confidence_level: "High", ...}
```

---

### Step 3: Check Right Panel UI

**In the right sidebar (Insights Panel):**

1. **Look for "🚦 Linguistic Confidence" section**
   - Should be the **second section** (after Persona Setup)
   - Should be **OPEN by default**

2. **The Traffic Light Badge should show:**
   - **Green Badge** with ✓ icon (if High Confidence)
   - **Yellow Badge** with ⚠ icon (if Medium Confidence)
   - **Red Badge** with ⚠ icon (if Low Confidence)

3. **The Badge contains:**
   - Large icon (✓ or ⚠)
   - "High/Medium/Low Confidence" text
   - Summary text explaining why

4. **Below the badge:**
   - Legend explaining:
     - 🟢 High = Solid reasoning, no uncertainty
     - 🟡 Medium = Some hedging or uncertainty
     - 🔴 Low = Self-corrections or knowledge gaps

5. **In development mode:**
   - "Debug Data" collapsible section at bottom
   - Shows raw calibration JSON

---

### Step 4: Check Message Badges

**In the chat messages area:**

1. **Look below each assistant message**
2. **You should see a colored badge:**
   ```
   ┌───────────────────────────────────────────────┐
   │ ✓ High Confidence | Linear reasoning with... │
   └───────────────────────────────────────────────┘
   ```

3. **Badge changes color based on confidence:**
   - Green background for High
   - Yellow background for Medium
   - Red background for Low

---

## 🐛 Troubleshooting

### Issue: Right panel still shows old Progress Bar

**Cause:** Browser cache not refreshed

**Solution:**
1. Hard refresh: `Ctrl+F5` (Windows) or `Cmd+Shift+R` (Mac)
2. Or clear browser cache and reload

---

### Issue: Calibration badge shows "Medium Confidence" for everything

**Cause:** Backend not returning calibration data (using fallback)

**Solution:**
1. Check backend logs - do you see `[DEBUG] Calibration result:`?
2. If YES: Data is being generated, check frontend console
3. If NO: Check if `linguistic_calibration.py` is imported correctly

---

### Issue: Frontend console shows "calibration: null"

**Cause:** Backend not sending calibration in SSE stream

**Solution:**
1. Check backend code at `main.py:210-224`
2. Verify `evaluate_confidence()` is being called
3. Check if exception is being thrown

---

### Issue: UI shows no badge at all

**Cause:** React component not rendering

**Solution:**
1. Check browser console for errors
2. Verify `ConfidencePanel.jsx` has no syntax errors
3. Try: `npm run dev` to restart Vite dev server

---

## 📸 Expected UI (Before vs After)

### BEFORE (OLD):
```
┌────────────────────────┐
│   Assistant confidence │
│   ████████░░ (82%)     │  ← Progress bar
│        82%             │  ← Percentage
└────────────────────────┘
```

### AFTER (NEW):
```
┌─────────────────────────────────────┐
│   Confidence Assessment             │
│                                     │
│   ┌───────────────────────────────┐ │
│   │ ✓   High Confidence           │ │ ← Green badge
│   │     Linear reasoning with...  │ │
│   └───────────────────────────────┘ │
│                                     │
│   What this means:                  │
│   🟢 High = Solid reasoning...     │
│   🟡 Medium = Some hedging...      │
│   🔴 Low = Self-corrections...     │
└─────────────────────────────────────┘
```

---

## 🎯 Test Cases

### Test 1: High Confidence (Green)

**Ask:** "What is 2 + 2?"

**Expected:**
- Right Panel: 🟢 Green badge with "High Confidence"
- Message Badge: Green badge below answer
- Summary: "Linear reasoning with high certainty" (or similar)

---

### Test 2: Medium Confidence (Yellow)

**Ask:** "Is Python better than JavaScript?"

**Expected:**
- Right Panel: 🟡 Yellow badge with "Medium Confidence"
- Message Badge: Yellow badge below answer
- Summary: "Contains hedging language" (or similar)
- AI will likely use words like "depends", "might", "can be"

---

### Test 3: Low Confidence (Red)

**Ask:** "How many R's are in 'strawberry'?"

**Expected:**
- Right Panel: 🔴 Red badge with "Low Confidence"
- Message Badge: Red badge below answer
- Summary: "Self-correction detected" (or similar)
- AI will likely say "Wait, let me recount..."

---

## ✨ Success Criteria

✅ **Backend logs show calibration result**
✅ **Frontend console shows calibration received**
✅ **Right panel shows Traffic Light UI (NOT progress bar)**
✅ **Message badges appear below assistant responses**
✅ **Badges change color based on uncertainty**
✅ **Legend explains what each color means**
✅ **Old Gauge Chart / Progress Bar is GONE**

---

## 🔄 Quick Restart (if needed)

If UI doesn't update after code changes:

```bash
# Kill both frontend and backend
# Restart backend:
cd backend
python main.py

# Restart frontend (in new terminal):
cd frontend/vite-project
npm run dev

# Hard refresh browser: Ctrl+F5
```

---

## 📞 Still Not Working?

Check these debug points in order:

1. **Backend logs** → Is calibration being computed?
2. **Network tab** → Is calibration in SSE response?
3. **Frontend console** → Is calibration being received?
4. **React DevTools** → Is state being updated?
5. **DOM inspector** → Is the new UI being rendered?

Each step should reveal where the data flow is broken.
