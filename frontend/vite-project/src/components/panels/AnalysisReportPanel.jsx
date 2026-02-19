import React from 'react';

/**
 * Analysis Report Panel - Epistemic Marker Display
 *
 * Displays detailed Judge analysis of an assistant response showing:
 * - Overall confidence level (green/yellow/red traffic light)
 * - Uncertainty percentage
 * - Detected epistemic markers with evidence and guidance
 *
 * Props:
 *   - trustAnalysis: TrustAnalysis object with markers and confidence_level
 *   - messageContent: The assistant's original response text (for context)
 */
export default function AnalysisReportPanel({ trustAnalysis, messageContent }) {
  // Handle empty states
  if (!messageContent) {
    return (
      <div style={{ padding: '24px', color: '#999' }}>
        No message selected
      </div>
    );
  }

  if (!trustAnalysis) {
    return (
      <div style={{ padding: '24px', color: '#999' }}>
        Analysis not available
      </div>
    );
  }

  // Show loading state
  if (trustAnalysis.isAnalyzing) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <div style={{
          display: 'inline-block',
          width: '24px',
          height: '24px',
          border: '3px solid #e0e0e0',
          borderTop: '3px solid #6c63ff',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite'
        }} />
        <div style={{ marginTop: '12px', color: '#666', fontSize: '14px' }}>
          Analyzing response...
        </div>
      </div>
    );
  }

  // Determine color based on confidence level
  const statusToColor = (status) => {
    if (status === 'green') return '#4caf50';
    if (status === 'yellow') return '#ffc107';
    return '#f44336'; // red
  };

  const overallColor = statusToColor(trustAnalysis.status);

  // Map status to label
  const statusToLabel = (status) => {
    if (status === 'green') return 'HIGH CONFIDENCE';
    if (status === 'yellow') return 'MEDIUM CONFIDENCE';
    return 'LOW CONFIDENCE';
  };

  const visibleMarkers = (trustAnalysis.markers || []).filter(marker => {
    // Only show stability markers for green confidence
    if (marker.type === 'stability' && trustAnalysis.status !== 'green') {
      return false;
    }
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* HEADER: Traffic Light + Summary */}
      <div style={{
        padding: '16px',
        backgroundColor: overallColor + '15',
        borderLeft: `4px solid ${overallColor}`,
        borderRadius: '8px'
      }}>
        <div style={{
          fontSize: '18px',
          fontWeight: '700',
          color: overallColor,
          marginBottom: '8px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <span style={{ fontSize: '20px' }}>
            {trustAnalysis.status === 'green' ? '✓' : '⚠'}
          </span>
          {statusToLabel(trustAnalysis.status)}
        </div>
        <div style={{ fontSize: '13px', color: '#555', marginTop: '8px', fontWeight: '500', lineHeight: '1.5' }}>
          {trustAnalysis.reasoning || 'No summary available'}
        </div>
      </div>

      {/* MARKERS SECTION */}
      {visibleMarkers.length > 0 && (
        <div>
          <div style={{
            fontSize: '12px',
            fontWeight: '700',
            color: '#6c63ff',
            textTransform: 'uppercase',
            marginBottom: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            Detection Report ({visibleMarkers.length} signal{visibleMarkers.length > 1 ? 's' : ''})
          </div>

          {visibleMarkers
            .map((marker, idx) => {
              const severityColorMap = {
                'high': '#f44336',
                'medium': '#ffc107',
                'low': '#4caf50'
              };
              const severityColor = severityColorMap[marker.severity] || '#999';
              const typeBadge = marker.type === 'uncertainty' ? '🚨' : '✅';

              return (
                <div key={idx} style={{
                  marginBottom: '12px',
                  padding: '12px',
                  backgroundColor: '#f8f9fc',
                  borderLeft: `3px solid ${severityColor}`,
                  borderRadius: '6px'
                }}>

                  {/* Marker Title */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '13px',
                    fontWeight: '600',
                    marginBottom: '8px',
                    flexWrap: 'wrap'
                  }}>
                    <span>{typeBadge}</span>
                    <span style={{ color: '#2b2f42' }}>{marker.dimension}</span>
                    <span style={{
                      fontSize: '10px',
                      color: severityColor,
                      fontWeight: '700',
                      textTransform: 'uppercase',
                      marginLeft: 'auto'
                    }}>
                      {marker.severity}
                    </span>
                  </div>

                  {/* Evidence Section */}
                  {marker.evidence && marker.evidence.length > 0 && (
                    <div style={{ marginBottom: '8px' }}>
                      <div style={{
                        fontSize: '11px',
                        fontWeight: '600',
                        color: '#6c63ff',
                        marginBottom: '4px'
                      }}>
                        Evidence:
                      </div>
                      {marker.evidence.map((quote, i) => (
                        <div key={i} style={{
                          fontSize: '12px',
                          color: '#555',
                          backgroundColor: '#fff',
                          padding: '6px 8px',
                          borderLeft: `2px solid #e0e0e0`,
                          borderRadius: '3px',
                          marginBottom: '4px',
                          fontStyle: 'italic',
                          fontFamily: 'monospace',
                          wordBreak: 'break-word'
                        }}>
                          "{quote}"
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Interpretation */}
                  <div style={{ marginBottom: '8px' }}>
                    <div style={{
                      fontSize: '11px',
                      fontWeight: '600',
                      color: '#6c63ff',
                      marginBottom: '3px'
                    }}>
                      Why it matters:
                    </div>
                    <div style={{
                      fontSize: '12px',
                      color: '#555',
                      lineHeight: '1.5'
                    }}>
                      {marker.interpretation || 'No interpretation available'}
                    </div>
                  </div>

                  {/* User Guidance */}
                  <div>
                    <div style={{
                      fontSize: '11px',
                      fontWeight: '600',
                      color: '#2e7d32',
                      marginBottom: '3px'
                    }}>
                      ✓ What you can do:
                    </div>
                    <div style={{
                      fontSize: '12px',
                      color: '#1b5e20',
                      lineHeight: '1.5',
                      backgroundColor: '#e8f5e9',
                      padding: '6px 8px',
                      borderRadius: '3px'
                    }}>
                      {marker.user_guidance || 'No guidance available'}
                    </div>
                  </div>
                </div>
              );
            })}
        </div>
      )}


      {/* NO MARKERS SECTION - Only show if green and no markers */}
      {(!trustAnalysis.markers || trustAnalysis.markers.length === 0) && trustAnalysis.status === 'green' && (
        <div style={{
          padding: '16px',
          backgroundColor: '#e8f5e9',
          borderRadius: '8px',
          color: '#2e7d32',
          fontSize: '13px',
          textAlign: 'center'
        }}>
          ✓ No uncertainty markers detected. Response appears reliable.
        </div>
      )}

      {/* FOOTER - Analysis Methodology */}
      <div style={{
        padding: '12px',
        backgroundColor: '#f5f5f5',
        borderRadius: '6px',
        fontSize: '11px',
        color: '#666',
        lineHeight: '1.6'
      }}>
        <div style={{ fontWeight: '600', marginBottom: '6px', color: '#333' }}>
          📋 Analysis Dimensions:
        </div>
        <div style={{ fontSize: '10px' }}>
          <strong>Uncertainty Markers:</strong> Hedging Language • Self-Correction • Knowledge Gaps • Lack of Specificity • Unsupported Claims<br/>
          <strong>Stability Marker:</strong> Stepwise Reasoning & Consistency
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
