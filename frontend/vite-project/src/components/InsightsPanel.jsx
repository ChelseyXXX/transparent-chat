import React, { useState } from 'react';
import AnalysisReportPanel from './panels/AnalysisReportPanel';
import TopicFlowPanel from './panels/TopicFlowPanel';


export default function InsightsPanel({
  topics = { topics: [] },
  persona = { role: 'rational_analyst', tone: 'friendly', personality: '' },
  onPersonaChange = () => {},
  selectedMessage = null,  // Selected message with trustAnalysis
  onNavigateToMessage = () => {},
  userId = null,
}) {
  const [expanded, setExpanded] = useState({
    persona: false,
    trust: true,  // Trust Calibration open by default
    topics: false,
  });

  const toggleSection = (section) => {
    setExpanded((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  return (
    <div className="insights-panel">
      {/* Header */}
      <div className="insights-panel-header">
        <h2>🔮 Insights</h2>
      </div>

      {/* Scrollable content area */}
      <div className="insights-panel-content">

        {/* 1. Persona Setup Module */}
        <AccordionSection
          title="Persona Setup"
          icon="👤"
          isOpen={expanded.persona}
          onToggle={() => toggleSection('persona')}
        >
          <PersonaContent persona={persona} onPersonaChange={onPersonaChange} />
        </AccordionSection>

        {/* 2. Trust Calibration Module (Unified - Traffic Light UI) */}
        <AccordionSection
          title="AI Reliability Analysis"
          icon="🔍"
          isOpen={expanded.trust}
          onToggle={() => toggleSection('trust')}
        >
          <AnalysisReportPanel
            trustAnalysis={selectedMessage?.trustAnalysis || null}
            messageContent={selectedMessage?.content || ''}
          />
        </AccordionSection>

        {/* 3. Topic Flow Module */}
        <AccordionSection
          title="Topic Flow"
          icon="🌊"
          isOpen={expanded.topics}
          onToggle={() => toggleSection('topics')}
        >
          <TopicFlowPanel
            topics={topics}
            onNavigateToMessage={onNavigateToMessage}
            userId={userId}
          />
        </AccordionSection>
      </div>
    </div>
  );
}

/**
 * Accordion module component
 * Contains expandable/collapsible header and content area
 */
function AccordionSection({ title, icon, isOpen, onToggle, children }) {
  return (
    <div className="accordion-section">
      <div
        className="accordion-header"
        onClick={onToggle}
        role="button"
        tabIndex={0}
        aria-expanded={isOpen}
      >
        <div className="accordion-header-left">
          <span className="accordion-icon">{icon}</span>
          <span className="accordion-title">{title}</span>
        </div>
        <div className="accordion-chevron">
          {isOpen ? '▼' : '▶'}
        </div>
      </div>

      {isOpen && (
        <div className="accordion-content">
          {children}
        </div>
      )}
    </div>
  );
}

/**
 * Persona Setup content component
 */
function PersonaContent({ persona, onPersonaChange }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <label style={{ fontSize: 11, fontWeight: 600, color: '#6c63ff', textTransform: 'uppercase' }}>Role</label>
        <select
          value={persona.role}
          onChange={(e) => onPersonaChange({ ...persona, role: e.target.value })}
          style={{
            padding: '8px 10px',
            border: '1px solid #d9deff',
            borderRadius: 6,
            fontSize: 13,
            fontFamily: 'inherit',
            backgroundColor: '#fafbfd',
            cursor: 'pointer',
          }}
        >
          <option value="rational_analyst">Rational Analyst</option>
          <option value="creative_muse">Creative Muse</option>
          <option value="empathetic_companion">Empathetic Companion</option>
        </select>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <label style={{ fontSize: 11, fontWeight: 600, color: '#6c63ff', textTransform: 'uppercase' }}>Tone</label>
        <select
          value={persona.tone}
          onChange={(e) => onPersonaChange({ ...persona, tone: e.target.value })}
          style={{
            padding: '8px 10px',
            border: '1px solid #d9deff',
            borderRadius: 6,
            fontSize: 13,
            fontFamily: 'inherit',
            backgroundColor: '#fafbfd',
            cursor: 'pointer',
          }}
        >
          <option value="professional">Professional</option>
          <option value="friendly">Friendly</option>
          <option value="concise">Concise</option>
        </select>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <label style={{ fontSize: 11, fontWeight: 600, color: '#6c63ff', textTransform: 'uppercase' }}>Personality</label>
        <textarea
          value={persona.personality}
          onChange={(e) => onPersonaChange({ ...persona, personality: e.target.value })}
          placeholder="Describe your ideal assistant..."
          rows={2}
          style={{
            padding: '8px 10px',
            border: '1px solid #d9deff',
            borderRadius: 6,
            fontSize: 12,
            fontFamily: 'inherit',
            backgroundColor: '#fafbfd',
            resize: 'vertical',
          }}
        />
      </div>

      <button
        style={{
          padding: '8px 12px',
          background: '#6c63ff',
          color: 'white',
          border: 'none',
          borderRadius: 6,
          fontSize: 12,
          fontWeight: 600,
          cursor: 'pointer',
          transition: 'background 0.2s',
        }}
        onMouseEnter={(e) => e.target.style.background = '#5551e5'}
        onMouseLeave={(e) => e.target.style.background = '#6c63ff'}
      >
        Update Persona
      </button>
    </div>
  );
}
