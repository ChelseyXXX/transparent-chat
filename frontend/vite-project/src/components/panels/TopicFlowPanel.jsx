import React, { useMemo, useRef, useEffect, useState } from 'react';
import TopicFlowVisualization from './TopicFlowVisualization';
import { getTopicFlow, updateTopicFlow as updateTopicFlowRequest } from '../../api/backend';

/**
 * TopicFlowPanel - Container for Topic Flow visualization
 * 
 * Features:
 * - Displays hierarchical topic graph from conversation
 * - "Update Topic Flow" button triggers incremental processing
 * - Shows loading state during updates
 * - Displays statistics about extracted topics
 */

export default function TopicFlowPanel({ topics = [], onTopicClick, onNavigateToMessage, userId = null }) {
  const [topicFlowData, setTopicFlowData] = useState({ nodes: [], links: [] });
  const [isLoading, setIsLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const scrollContainerRef = useRef(null);

  // Handle topic node click - navigate to corresponding message
  const handleTopicNodeClick = (node) => {
    console.log('[TopicFlowPanel] Node clicked:', node);
    console.log('[TopicFlowPanel] first_seen_message_id:', node.first_seen_message_id);
    console.log('[TopicFlowPanel] last_seen_message_id:', node.last_seen_message_id);
    console.log('[TopicFlowPanel] onNavigateToMessage available:', !!onNavigateToMessage);
    
    // Use first_seen_message_id to jump to the earliest message for this topic
    const messageId = node.first_seen_message_id || node.last_seen_message_id;
    
    if (messageId && onNavigateToMessage) {
      console.log('[TopicFlowPanel] Calling onNavigateToMessage with ID:', messageId);
      onNavigateToMessage(messageId);
    } else {
      console.warn('[TopicFlowPanel] Cannot navigate - messageId:', messageId, ', onNavigateToMessage:', !!onNavigateToMessage);
      if (onTopicClick) {
        // Fallback to onTopicClick if provided
        onTopicClick(node);
      }
    }
  };

  // Load initial topic flow data on mount
  useEffect(() => {
    loadTopicFlow();
  }, []);

  async function loadTopicFlow() {
    try {
      console.log('[TopicFlowPanel] Loading topic flow from backend');
      const data = await getTopicFlow(userId);
      console.log('[TopicFlowPanel] Successfully loaded topic flow:', data);
      setTopicFlowData(data);
      setStats(data.stats);
      setError(null);
    } catch (err) {
      console.error('[TopicFlowPanel] Error loading topic flow:', err);
      const errorMsg =
        err?.message ||
        'Failed to load topic flow. Make sure backend is running on port 8000.';
      setError(errorMsg);
    }
  }

  async function updateTopicFlow(forceRecompute = false) {
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await updateTopicFlowRequest(forceRecompute, userId);
      console.log('[TopicFlowPanel] Update result:', {
        nodes: data.nodes?.length,
        links: data.links?.length,
        processed: data.processed_count,
        incremental: data.is_incremental
      });
      
      setTopicFlowData(data);
      setStats(data.stats);
      
      // Show success message
      if (data.processed_count > 0) {
        console.log(`[TopicFlowPanel] Processed ${data.processed_count} new messages`);
      } else {
        console.log('[TopicFlowPanel] No new messages to process');
      }
    } catch (err) {
      console.error('[TopicFlowPanel] Error updating topic flow:', err);
      setError(err?.message || 'Failed to update topic flow. Make sure backend is running.');
    } finally {
      setIsLoading(false);
    }
  }

  const isEmpty = !topicFlowData.nodes || topicFlowData.nodes.length === 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header with description and controls */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'flex-start',
        marginBottom: 12 
      }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12, color: '#4a4f6c', lineHeight: 1.4 }}>
            Hierarchical topic extraction from your conversation. Topics are organized as:
            <strong> topic → subtopic → detail</strong>
          </div>
        </div>

        {/* Update button */}
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => updateTopicFlow(false)}
            disabled={isLoading}
            style={{
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: 500,
              color: '#fff',
              background: isLoading ? '#94a3b8' : '#6366f1',
              border: 'none',
              borderRadius: '6px',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              transition: 'background 0.2s',
              whiteSpace: 'nowrap'
            }}
            onMouseEnter={(e) => {
              if (!isLoading) e.target.style.background = '#4f46e5';
            }}
            onMouseLeave={(e) => {
              if (!isLoading) e.target.style.background = '#6366f1';
            }}
          >
            {isLoading ? '⏳ Updating...' : '🔄 Update Topic Flow'}
          </button>

          {/* Full recompute button (for testing) */}
          <button
            onClick={() => updateTopicFlow(true)}
            disabled={isLoading}
            title="Reprocess all messages (slow)"
            style={{
              padding: '6px 10px',
              fontSize: '11px',
              color: '#64748b',
              background: '#f1f5f9',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              whiteSpace: 'nowrap'
            }}
          >
            ♻️ Reset
          </button>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div style={{
          padding: '10px 12px',
          marginBottom: 12,
          background: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '8px',
          color: '#dc2626',
          fontSize: '12px'
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Visualization container */}
      <div 
        ref={scrollContainerRef}
        style={{ 
          flex: 1,
          minHeight: 400,
          border: '1px solid #e5e7f3', 
          borderRadius: 10, 
          padding: 6, 
          background: '#f9faff', 
          position: 'relative',
          overflow: 'hidden'
        }}
      >
        {isEmpty && !isLoading ? (
          <div style={{ 
            position: 'absolute', 
            inset: 0, 
            display: 'flex', 
            flexDirection: 'column',
            alignItems: 'center', 
            justifyContent: 'center', 
            color: '#8a8fa3', 
            fontSize: 13 
          }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>🌐</div>
            <div>No topics extracted yet.</div>
            <div style={{ fontSize: 11, marginTop: 4 }}>
              Send messages, then click "Update Topic Flow"
            </div>
          </div>
        ) : (
          <TopicFlowVisualization 
            data={topicFlowData} 
            onTopicClick={handleTopicNodeClick}
          />
        )}

        {/* Loading overlay */}
        {isLoading && (
          <div style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(255, 255, 255, 0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 14,
            color: '#6366f1',
            fontWeight: 500
          }}>
            <div>
              <div style={{ fontSize: 24, marginBottom: 8 }}>⚡</div>
              Extracting topics from conversation...
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

