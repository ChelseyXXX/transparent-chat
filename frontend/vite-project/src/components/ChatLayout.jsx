import React, { useEffect, useRef, useState } from 'react';
import '../styles.css';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { sendMessageStreaming, getConversation, analyzeResponse, saveTrustAnalysis } from '../api/backend';
import InsightsPanel from './InsightsPanel';

/**
 * Main Chat Layout Component
 * Implements per-message trust analysis with instant switching
 */
export default function ChatLayout({ onLogout, user }) {
  // Core chat state
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);

  // Message selection for sidebar
  const [selectedMessageId, setSelectedMessageId] = useState(null);

  // UI state
  const [persona, setPersona] = useState({ role: 'rational_analyst', tone: 'friendly', personality: '' });
  const [topics, setTopics] = useState({ topics: [] });
  const [expandedReasoning, setExpandedReasoning] = useState({});

  // Refs
  const chatEndRef = useRef(null);
  const streamingMessageIdRef = useRef(null);
  const messageIdCounter = useRef(0);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load conversation history when user changes
  useEffect(() => {
    async function loadHistory() {
      try {
        const data = await getConversation(user?.id);
        console.log('[ChatLayout] Loaded conversation history:', data);

        if (data.messages && data.messages.length > 0) {
          // Convert backend messages to new format
          const convertedMessages = data.messages.map((msg, idx) => ({
            id: `history-${idx}`,
            dbId: msg.id,
            role: msg.role,
            content: msg.content,
            reasoning: msg.reasoning || '',  // Load reasoning from database
            trustAnalysis: msg.trust_analysis || (msg.confidence ? {
              status: 'yellow',  // Default to yellow for old messages without trust_analysis
              score: msg.confidence.score || 0.5,
              reasoning: msg.confidence.label || 'Analysis from previous session',
              markers: [],
              isAnalyzing: false
            } : null)
          }));

          setMessages(convertedMessages);
          console.log('[ChatLayout] Converted messages:', convertedMessages);
        } else {
          setMessages([]);
        }

        // Load topics if available
        if (data.topics) {
          setTopics({ topics: data.topics });
        } else {
          setTopics({ topics: [] });
        }
        setSelectedMessageId(null);
      } catch (err) {
        console.error('[ChatLayout] Failed to load conversation history:', err);
      }
    }

    if (!user?.id) {
      setMessages([]);
      setTopics({ topics: [] });
      setSelectedMessageId(null);
      setIsStreaming(false);
      streamingMessageIdRef.current = null;
      return;
    }

    setIsStreaming(false);
    streamingMessageIdRef.current = null;
    loadHistory();
  }, [user?.id]);

  // Generate unique message ID
  const generateMessageId = () => {
    messageIdCounter.current += 1;
    return `msg-${Date.now()}-${messageIdCounter.current}`;
  };

  // Map calibration data to trustAnalysis format
  const mapCalibrationToTrustAnalysis = (calibration) => {
    if (!calibration) return null;

    // Map visual_signal to status
    const status = calibration.visual_signal; // 'green' | 'yellow' | 'red'

    // Map confidence_level to score
    const levelToScore = {
      'High': 0.9,
      'Medium': 0.6,
      'Low': 0.3
    };
    const score = levelToScore[calibration.confidence_level] || 0.5;

    // Use analysis_explanation as the reasoning (context-specific explanation)
    const reasoning = calibration.analysis_explanation || '';

    return {
      status,
      score,
      reasoning,
      isAnalyzing: false
    };
  };

  /**
   * STEP 5: Message Click Handler
   * Instantly switches selected message WITHOUT making API calls
   */
  const handleMessageClick = (messageId) => {
    console.log('[ChatLayout] Message clicked:', messageId);
    setSelectedMessageId(messageId);
  };

  /**
   * Get selected message object for sidebar
   */
  const selectedMessage = messages.find(m => m.id === selectedMessageId) || null;

  /**
   * Send Message Handler - STEP 3-4: Per-Message Storage
   */
  async function handleSend() {
    if (!input.trim() || isStreaming) return;

    const userQueryText = input.trim();
    const userId = generateMessageId();
    const assistantId = generateMessageId();

    // Build conversation history BEFORE updating state (to capture current messages)
    const conversationHistory = messages.map(msg => ({
      role: msg.role,
      content: msg.content
    }));
    // Add current user message to history
    conversationHistory.push({
      role: 'user',
      content: userQueryText
    });

    // Add user message
    const newUserMsg = {
      id: userId,
      role: 'user',
      content: userQueryText,
      trustAnalysis: null  // Users don't have analysis
    };

    setMessages((prev) => [...prev, newUserMsg]);
    setInput('');

    // Add placeholder for assistant message
    const assistantPlaceholder = {
      id: assistantId,
      role: 'assistant',
      content: '',
      reasoning: '',
      trustAnalysis: {
        status: 'yellow',
        score: 0,
        reasoning: '',
        isAnalyzing: true  // Show spinner
      },
      isStreaming: true
    };

    setMessages((prev) => [...prev, assistantPlaceholder]);
    setIsStreaming(true);
    streamingMessageIdRef.current = assistantId;

    // Auto-expand reasoning for streaming message
    setExpandedReasoning(prev => ({ ...prev, [assistantId]: true }));

    // Auto-select the new assistant message
    setSelectedMessageId(assistantId);

    try {
      let finalCalibration = null;

      console.log('[ChatLayout] Sending conversation history:', conversationHistory);
      console.log('[ChatLayout] History length:', conversationHistory.length);

      await sendMessageStreaming(userQueryText, persona, (type, delta, accumulated) => {
        const msgId = streamingMessageIdRef.current;

        if (type === 'reasoning') {
          // Update reasoning in real-time
          console.log('[ChatLayout] Reasoning chunk:', accumulated.substring(0, 50));
          setMessages((prev) =>
            prev.map(m =>
              m.id === msgId
                ? { ...m, reasoning: accumulated }
                : m
            )
          );
        } else if (type === 'content') {
          // Update content in real-time
          console.log('[ChatLayout] Content chunk:', accumulated.substring(0, 50));
          setMessages((prev) =>
            prev.map(m =>
              m.id === msgId
                ? { ...m, content: accumulated }
                : m
            )
          );
        } else if (type === 'done') {
          console.log('[ChatLayout] Done event - reasoning length:', accumulated.reasoning?.length, 'content length:', accumulated.content?.length);
          console.log('[ChatLayout] Message ID for this streaming:', msgId);
          console.log('[ChatLayout] Current messages count:', messages.length);
          // STEP 7: Map DeepSeek response to trustAnalysis
          const calibration = accumulated.calibration;
          const assistantDbId = accumulated.assistantMessageId || null;
          finalCalibration = calibration;

          console.log('[ChatLayout] Received calibration:', calibration);

          const trustAnalysis = mapCalibrationToTrustAnalysis(calibration);
          console.log('[ChatLayout] Mapped to trustAnalysis:', trustAnalysis);

          // Finalize the message with trustAnalysis stored inside
          setMessages((prev) => {
            const updated = prev.map(m =>
              m.id === msgId
                ? {
                    ...m,
                    content: accumulated.content || '',
                    reasoning: accumulated.reasoning || '',
                    dbId: assistantDbId || m.dbId,
                    trustAnalysis: trustAnalysis,  // Store per-message
                    isStreaming: false
                  }
                : m
            );
            const updatedMsg = updated.find(m => m.id === msgId);
            console.log('[ChatLayout] After state update, message state:', {
              id: msgId,
              isStreaming: updatedMsg?.isStreaming,
              contentLength: updatedMsg?.content?.length,
              hasReasoning: !!updatedMsg?.reasoning
            });
            return updated;
          });

          console.log('[ChatLayout] Set isStreaming to false for message:', msgId);

          setIsStreaming(false);
          streamingMessageIdRef.current = null;

          // Update topic if provided
          if (finalCalibration) {
            // You can extract topic from calibration or content here if needed
          }

          // STEP 8: Trigger Judge Analysis asynchronously (non-blocking)
          // Fire the analysis in background without awaiting - UI stays responsive
          console.log('[ChatLayout] Triggering Judge analysis asynchronously...');

          (async () => {
            try {
              // First, update sidebar to show "Analyzing..." state
              console.log('[ChatLayout] Updating to show "Analyzing..." state');
              setMessages((prev) =>
                prev.map(m =>
                  m.id === msgId
                    ? {
                        ...m,
                        trustAnalysis: {
                          status: 'yellow',
                          score: 0.5,
                          reasoning: '',
                          isAnalyzing: true  // Show spinner
                        }
                      }
                    : m
                )
              );

              // Call Judge API with the response content and reasoning
              console.log('[ChatLayout] Calling analyzeResponse with:', {
                questionLength: userQueryText.length,
                answerLength: (accumulated.content || '').length,
                reasoningLength: (accumulated.reasoning || '').length
              });
              
              const analysis = await analyzeResponse(
                userQueryText,
                accumulated.content || '',
                accumulated.reasoning || ''
              );

              console.log('[ChatLayout] Judge analysis received:', analysis);
              
              // Check for error in analysis
              if (analysis.error || analysis.summary?.includes('unavailable')) {
                console.error('[ChatLayout] Judge analysis returned error or unavailable:', {
                  error: analysis.error,
                  summary: analysis.summary
                });
              }

              // DEBUG: Detailed marker inspection
              console.log('[ChatLayout] Analysis breakdown:', {
                confidence_level: analysis.confidence_level,
                overall_uncertainty: analysis.overall_uncertainty,
                summary: analysis.summary,
                markerCount: analysis.markers?.length || 0
              });

              if (analysis.markers && analysis.markers.length > 0) {
                console.log('[ChatLayout] Markers detail:');
                analysis.markers.forEach((marker, idx) => {
                  console.log(`  [${idx + 1}] ${marker.dimension} (${marker.severity}):`, {
                    type: marker.type,
                    evidenceCount: marker.evidence?.length || 0,
                    interpretationLength: marker.interpretation?.length || 0,
                    guidanceLength: marker.user_guidance?.length || 0
                  });
                  if (marker.interpretation) {
                    console.log(`      interpretation: "${marker.interpretation.substring(0, 100)}..."`);
                  }
                });
              } else {
                console.warn('[ChatLayout] ⚠️ No markers in Judge response - this should not happen!');
              }

              // Map Judge response to trustAnalysis format
              const judgetrustAnalysis = {
                status: analysis.confidence_level === 'green' ? 'green' :
                        analysis.confidence_level === 'yellow' ? 'yellow' : 'red',
                score: analysis.overall_uncertainty,
                reasoning: analysis.summary,
                markers: analysis.markers || [],
                isAnalyzing: false
              };

              // Update message with final analysis
              setMessages((prev) =>
                prev.map(m =>
                  m.id === msgId
                    ? {
                        ...m,
                        trustAnalysis: judgetrustAnalysis
                      }
                    : m
                )
              );

              console.log('[ChatLayout] Message updated with Judge analysis');
              
              // Save trust analysis to database (non-blocking)
              console.log('[ChatLayout] Saving trust analysis to database...');
              saveTrustAnalysis(assistantDbId, judgetrustAnalysis, user?.id, accumulated.content || '')
                .then(() => {
                  console.log('[ChatLayout] Trust analysis saved successfully');
                })
                .catch(err => {
                  console.error('[ChatLayout] Failed to save trust analysis:', err);
                  // Non-fatal error - analysis is still in state
                });
            } catch (err) {
              console.error('[ChatLayout] Judge analysis failed:', err);

              // Graceful fallback: show error state but keep response visible
              setMessages((prev) =>
                prev.map(m =>
                  m.id === msgId
                    ? {
                        ...m,
                        trustAnalysis: {
                          status: 'yellow',
                          score: 0.5,
                          reasoning: 'Analysis unavailable',
                          isAnalyzing: false
                        }
                      }
                    : m
                )
              );
            }
          })();
        }
      }, conversationHistory, user?.id);

    } catch (err) {
      console.error('Streaming error:', err);
      setIsStreaming(false);
      streamingMessageIdRef.current = null;

      // Show error in the assistant message
      const msgId = assistantId;
      const errMsg = err.message || 'Failed to send message, please try again';
      setMessages((prev) =>
        prev.map(m =>
          m.id === msgId
            ? {
                role: 'assistant',
                id: msgId,
                content: `❌ Error: ${errMsg}`,
                trustAnalysis: null,
                isStreaming: false
              }
            : m
        )
      );
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNavigateToMessage = (messageId) => {
    // Scroll to message and select it
    const messageElement = document.getElementById(`bubble-${messageId}`);
    if (messageElement) {
      messageElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setSelectedMessageId(messageId);

      // Highlight briefly
      messageElement.style.backgroundColor = '#fff3cd';
      setTimeout(() => {
        messageElement.style.backgroundColor = '';
      }, 1500);
    }
  };

  return (
    <div className="app-container">
      {/* Left Pane: Chat Interface */}
      <div className="left-pane">
        <div className="chat-header">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h1>Transparent Chat</h1>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <Link to="/register" style={{ fontSize: 14, color: '#6c63ff', textDecoration: 'none' }}>
                Register
              </Link>
              <button
                onClick={() => { onLogout && onLogout(); }}
                style={{ padding: '6px 10px', borderRadius: 6, border: 'none', background: '#eee' }}
              >
                Logout
              </button>
            </div>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="chat-messages" id="chatMessages">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`message-item ${m.role} ${selectedMessageId === m.id ? 'selected' : ''}`}
              onClick={() => m.role === 'assistant' && handleMessageClick(m.id)}
              style={{ cursor: m.role === 'assistant' ? 'pointer' : 'default' }}
            >
              {/* Reasoning section (only for assistant messages with reasoning) */}
              {m.role === 'assistant' && (m.reasoning || m.isStreaming) && (
                <div style={{
                  marginBottom: '8px',
                  padding: '8px 12px',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '6px',
                  border: '1px solid #e0e0e0',
                  fontSize: '13px',
                  color: '#555'
                }}>
                  <div
                    onClick={(e) => {
                      e.stopPropagation();
                      setExpandedReasoning(prev =>  ({ ...prev, [m.id]: !prev[m.id] }));
                    }}
                    style={{
                      cursor: 'pointer',
                      fontWeight: '600',
                      marginBottom: expandedReasoning[m.id] ? '8px' : '0',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <span style={{ fontSize: '16px' }}>
                      {expandedReasoning[m.id] ? '▼' : '▶'}
                    </span>
                    <span>💭 Thinking Process</span>
                    {m.isStreaming && (
                      <span style={{
                        marginLeft: 'auto',
                        fontSize: '11px',
                        color: '#6c63ff',
                        fontWeight: 'normal'
                      }}>
                        streaming...
                      </span>
                    )}
                  </div>
                  {expandedReasoning[m.id] && (
                    <div style={{
                      whiteSpace: 'pre-wrap',
                      lineHeight: '1.5',
                      fontSize: '12px',
                      color: '#666',
                      maxHeight: '300px',
                      overflowY: 'auto',
                      paddingLeft: '22px'
                    }}>
                      {m.reasoning}
                      {m.isStreaming && m.reasoning && (
                        <span style={{
                          animation: 'blink 1s infinite',
                          marginLeft: '2px',
                          color: '#6c63ff'
                        }}>▊</span>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Main message bubble */}
              <div
                className="message-bubble"
                id={`bubble-${m.id}`}
                style={{
                  border: selectedMessageId === m.id && m.role === 'assistant' ? '2px solid #6c63ff' : undefined
                }}
              >
                {m.role !== 'user' ? (
                  <div style={{ textAlign: 'left' }}>
                    <ReactMarkdown>{m.content || (m.isStreaming ? '' : '...')}</ReactMarkdown>
                    {m.isStreaming && m.content && (
                      <span style={{
                        animation: 'blink 1s infinite',
                        marginLeft: '2px',
                        color: '#6c63ff',
                        fontSize: '16px'
                      }}>▊</span>
                    )}
                    {m.isStreaming && !m.content && !m.reasoning && (
                      <span style={{ color: '#999', fontSize: '14px' }}>
                        Waiting for response...
                      </span>
                    )}
                  </div>
                ) : (
                  <div>{m.content}</div>
                )}
              </div>

              {/* Trust Badge (inline - optional, can be removed if only showing in sidebar) */}
              {m.trustAnalysis && !m.isStreaming && !m.trustAnalysis.isAnalyzing && (
                <div style={{
                  marginTop: '6px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '4px 8px',
                  borderRadius: '12px',
                  fontSize: '10px',
                  fontWeight: '600',
                  backgroundColor: m.trustAnalysis.status === 'green' ? '#e8f5e9' :
                                   m.trustAnalysis.status === 'yellow' ? '#fff9e6' :
                                   '#ffebee',
                  color: m.trustAnalysis.status === 'green' ? '#2e7d32' :
                         m.trustAnalysis.status === 'yellow' ? '#f57c00' :
                         '#c62828'
                }}>
                  <span>{m.trustAnalysis.status === 'green' ? '✓' : '⚠'}</span>
                  <span>{m.trustAnalysis.status === 'green' ? 'High' : m.trustAnalysis.status === 'yellow' ? 'Medium' : 'Low'} Trust</span>
                </div>
              )}
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        {/* Chat Input */}
        <div className="chat-input-area">
          <textarea
            className="input-textarea"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={isStreaming ? "Waiting for response..." : "Ask anything, and I'll explain my reasoning..."}
            rows={2}
            disabled={isStreaming}
          />
          <button
            className="send-button"
            onClick={handleSend}
            disabled={isStreaming}
            style={{
              opacity: isStreaming ? 0.5 : 1,
              cursor: isStreaming ? 'not-allowed' : 'pointer'
            }}
          >
            {isStreaming ? 'Streaming...' : 'Send'}
          </button>
        </div>
      </div>

      {/* Right Pane: Insights Panel - STEP 6 */}
      <div className="right-pane">
        <InsightsPanel
          topics={topics}
          persona={persona}
          onPersonaChange={(newPersona) => setPersona(newPersona)}
          selectedMessage={selectedMessage}  // Pass selected message
          onNavigateToMessage={handleNavigateToMessage}
          userId={user?.id}
        />
      </div>
    </div>
  );
}
