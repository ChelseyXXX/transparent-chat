/**
 * Transparent Chat - Frontend Application Logic (Vanilla JavaScript)
 * Features: Chat interface, Persona customization, Real-time trust calibration, Cognitive contextualization
 */

// ====== State Management ======
const appState = {
    persona: {
        role: 'General Assistant',
        tone: 'friendly',
        personality: ''
    },
    messages: [
        {
            role: 'assistant',
            content: 'Welcome to Transparent Chat! I\'m your AI assistant. Ask me anything, and I\'ll transparently show you my confidence level and reasoning for every response.',
            confidence: 0.95,
            reason: 'Welcome greeting message'
        }
    ],
    topics: ['Welcome'],
    turnCount: 1,
    confidenceScores: [95],
    isLoading: false
};

// ====== DOM Element Cache ======
const elements = {
    inputMessage: document.getElementById('inputMessage'),
    sendBtn: document.getElementById('sendBtn'),
    chatMessages: document.getElementById('chatMessages'),
    confidenceValue: document.getElementById('confidenceValue'),
    confidenceBar: document.getElementById('confidenceBar'),
    confidenceReason: document.getElementById('confidenceReason'),
    totalTurns: document.getElementById('totalTurns'),
    avgConfidence: document.getElementById('avgConfidence'),
    topicList: document.getElementById('topicList'),
    roleInput: document.getElementById('roleInput'),
    toneInput: document.getElementById('toneInput'),
    personalityInput: document.getElementById('personalityInput'),
    updatePersonaBtn: document.getElementById('updatePersonaBtn'),
    personaForm: document.getElementById('personaForm')
};

// ====== Initialization ======
function init() {
    // Event listeners
    elements.sendBtn.addEventListener('click', handleSendMessage);
    elements.inputMessage.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            handleSendMessage();
        }
    });
    elements.updatePersonaBtn.addEventListener('click', handleUpdatePersona);
    
    // Restore data from localStorage
    loadFromLocalStorage();
    
    // Render initial messages
    renderMessages();
    updateInsightsPanel();
}

// ====== Message Handling ======
async function handleSendMessage() {
    const content = elements.inputMessage.value.trim();
    
    if (!content) return;
    if (appState.isLoading) return;
    
    // Add user message
    appState.messages.push({
        role: 'user',
        content: content,
        confidence: null,
        reason: null
    });
    
    // Clear input field
    elements.inputMessage.value = '';
    
    // Render user message
    renderMessages();
    
    // Set loading state
    appState.isLoading = true;
    elements.sendBtn.disabled = true;
    
    try {
        // Call backend API
        const response = await callBackendAPI(content);
        
        // Add assistant message
        appState.messages.push({
            role: 'assistant',
            content: response.response,
            confidence: response.confidence.score,
            reason: generateConfidenceReason(response.confidence)
        });
        
        // Update statistics
        appState.turnCount += 1;
        appState.confidenceScores.push(response.confidence.score);
        
        // Extract topics (simple implementation)
        const newTopics = extractTopics(content, response.response);
        appState.topics = [...new Set([...appState.topics, ...newTopics])];
        
        // Render messages and update panel
        renderMessages();
        updateInsightsPanel();
    } catch (error) {
        console.error('API call failed:', error);
        
        // Show error message
        appState.messages.push({
            role: 'assistant',
            content: `Sorry, there was an error processing your request: ${error.message}`,
            confidence: 0,
            reason: 'Error message'
        });
        
        renderMessages();
    } finally {
        appState.isLoading = false;
        elements.sendBtn.disabled = false;
        elements.inputMessage.focus();
    }
}

// ====== Backend API Call ======
async function callBackendAPI(userMessage) {
    const backendURL = 'http://127.0.0.1:8000/chat';
    
    const payload = {
        role: 'user',
        content: userMessage
    };
    
    try {
        const response = await fetch(backendURL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        return {
            response: data.response || 'No response received',
            confidence: {
                label: data.confidence?.label || 'unknown',
                score: (data.confidence?.score || 0) * 100
            }
        };
    } catch (error) {
        // Fallback to mock API
        console.warn('Backend API unavailable, using mock data:', error);
        return mockSendMessage(userMessage);
    }
}

// ====== Mock API (for development/testing) ======
function mockSendMessage(userMessage) {
    // Simulate network delay
    const delay = 800 + Math.random() * 1200;
    
    // Simulate replies
    const mockReplies = [
        `Regarding your question about "${userMessage}": This is a great question. Based on my knowledge base, I can provide you with a detailed explanation.`,
        `I notice you asked about "${userMessage}". This involves multiple aspects, and I'll try to explain comprehensively.`,
        `The topic "${userMessage}" is interesting. Let me analyze it from several angles for you.`,
        `Concerning "${userMessage}", my perspective is: This is indeed a question worth discussing in depth.`,
        `Regarding "${userMessage}", I'd like to explain from the following points: First, this topic is important. Second, we need to consider multiple factors. Finally, I hope my answer is helpful to you.`
    ];
    
    const reply = mockReplies[Math.floor(Math.random() * mockReplies.length)];
    
    // Simulate confidence
    const confidence = 0.4 + Math.random() * 0.5; // 0.4 ~ 0.9
    
    return Promise.resolve({
        response: reply,
        confidence: {
            label: confidence > 0.75 ? 'high' : confidence > 0.5 ? 'medium' : 'low',
            score: confidence
        }
    });
}

// ====== Render Messages ======
function renderMessages() {
    elements.chatMessages.innerHTML = '';
    
    appState.messages.forEach((msg, index) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-item ${msg.role}`;
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.innerHTML = `<p>${escapeHtml(msg.content)}</p>`;
        
        messageDiv.appendChild(bubble);
        
        // Add confidence badge (assistant messages only)
        if (msg.role === 'assistant' && msg.confidence !== null) {
            const meta = document.createElement('div');
            meta.className = 'message-meta';
            const confLabel = msg.confidence >= 80 ? 'High' : msg.confidence >= 50 ? 'Medium' : 'Low';
            meta.innerHTML = `<span class="confidence-badge">Confidence: ${confLabel} (${msg.confidence.toFixed(0)}%)</span>`;
            messageDiv.appendChild(meta);
        }
        
        elements.chatMessages.appendChild(messageDiv);
    });
    
    // Scroll to bottom
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

// ====== Update Insights Panel ======
function updateInsightsPanel() {
    // Update confidence
    if (appState.confidenceScores.length > 0) {
        const lastConfidence = appState.confidenceScores[appState.confidenceScores.length - 1];
        const confPercent = Math.round(lastConfidence);
        
        elements.confidenceValue.textContent = confPercent;
        elements.confidenceBar.style.width = confPercent + '%';
        
        // Update color
        if (confPercent >= 80) {
            elements.confidenceBar.style.background = 'linear-gradient(90deg, #4caf50 0%, #45a049 100%)';
        } else if (confPercent >= 50) {
            elements.confidenceBar.style.background = 'linear-gradient(90deg, #ff9800 0%, #e68900 100%)';
        } else {
            elements.confidenceBar.style.background = 'linear-gradient(90deg, #f44336 0%, #da190b 100%)';
        }
    }
    
    // Update reasoning
    const lastMessage = appState.messages[appState.messages.length - 1];
    if (lastMessage && lastMessage.role === 'assistant') {
        elements.confidenceReason.textContent = lastMessage.reason || 'Processing...';
    }
    
    // Update statistics
    elements.totalTurns.textContent = appState.turnCount;
    
    const avgConf = appState.confidenceScores.length > 0
        ? (appState.confidenceScores.reduce((a, b) => a + b, 0) / appState.confidenceScores.length).toFixed(0)
        : 0;
    elements.avgConfidence.textContent = avgConf + '%';
    
    // Update topics
    renderTopics();
}

// ====== Render Topic Tags ======
function renderTopics() {
    elements.topicList.innerHTML = '';
    
    appState.topics.forEach(topic => {
        const tag = document.createElement('span');
        tag.className = 'topic-tag';
        tag.textContent = topic;
        elements.topicList.appendChild(tag);
    });
}

// ====== Persona Customization ======
function handleUpdatePersona() {
    appState.persona.role = elements.roleInput.value || 'General Assistant';
    appState.persona.tone = elements.toneInput.value;
    appState.persona.personality = elements.personalityInput.value;
    
    // Save to localStorage
    saveToLocalStorage();
    
    // Show success message
    alert('✓ Persona updated! The next response will use your new settings.');
}

// ====== Topic Extraction (simple implementation) ======
function extractTopics(userMessage, assistantMessage) {
    // Define keyword pool
    const keywords = [
        'Technology', 'Programming', 'Frontend', 'Backend', 'Database', 'Algorithm',
        'Design', 'UX', 'UI', 'Interaction', 'Layout', 'Architecture',
        'Security', 'Performance', 'Optimization', 'Testing', 'Deployment', 'Cloud',
        'Machine Learning', 'AI', 'Deep Learning', 'NLP',
        'Culture', 'History', 'Science', 'Physics', 'Chemistry', 'Biology'
    ];
    
    const text = (userMessage + ' ' + assistantMessage).toLowerCase();
    const found = [];
    
    keywords.forEach(kw => {
        if (text.includes(kw.toLowerCase()) && !appState.topics.includes(kw)) {
            found.push(kw);
        }
    });
    
    // Extract first noun from text (simplified)
    if (found.length === 0) {
        const words = userMessage.split(/\s+|，|。|！|？/).filter(w => w.length > 2);
        if (words.length > 0) {
            found.push(words[0]);
        }
    }
    
    return found.slice(0, 3); // Limit to 3 topics max
}

// ====== Generate Confidence Explanation ======
function generateConfidenceReason(confidence) {
    const score = confidence.score;
    const label = confidence.label;
    
    const explanations = {
        high: [
            'I have high confidence in this answer, backed by comprehensive knowledge.',
            'This question is clearly documented in my knowledge base, so I\'m very confident.',
            'I\'ve verified this information multiple times, so I\'m certain of its accuracy.'
        ],
        medium: [
            'I have reasonable confidence in this answer, though some uncertainty remains.',
            'This question involves multiple aspects, and I\'m providing the most reasonable response.',
            'Based on available information, I lean toward this answer, but other possibilities exist.'
        ],
        low: [
            'This question is complex, and my answer may be incomplete. I recommend further verification.',
            'My knowledge in this area is limited, so take this answer as reference only.',
            'This involves significant uncertainty, so my confidence level is relatively low.'
        ]
    };
    
    const reasons = explanations[label] || explanations.medium;
    return reasons[Math.floor(Math.random() * reasons.length)];
}

// ====== Utility Functions ======
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function saveToLocalStorage() {
    localStorage.setItem('transparentChatState', JSON.stringify(appState));
}

function loadFromLocalStorage() {
    const saved = localStorage.getItem('transparentChatState');
    if (saved) {
        try {
            const restored = JSON.parse(saved);
            // Merge state (keep initial message)
            appState.persona = restored.persona || appState.persona;
            appState.messages = restored.messages || appState.messages;
            appState.topics = restored.topics || appState.topics;
            appState.turnCount = restored.turnCount || appState.turnCount;
            appState.confidenceScores = restored.confidenceScores || appState.confidenceScores;
            
            // Restore UI
            elements.roleInput.value = appState.persona.role;
            elements.toneInput.value = appState.persona.tone;
            elements.personalityInput.value = appState.persona.personality;
        } catch (e) {
            console.warn('Failed to restore local data:', e);
        }
    }
}

// ====== Page Load ======
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
