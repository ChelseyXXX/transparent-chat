import React, { useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';

/**
 * TopicFlowVisualization - Enhanced Hierarchical Force-Directed Graph
 * 
 * Features:
 * - Two-level hierarchy visible by default (topic → subtopic)
 * - Subsubtopics shown on hover/click for detail
 * - Color inheritance: subtopics inherit lighter versions of topic color
 * - Timeline encoding: position and color encode message timestamp
 * - Optimized readability: smaller nodes, better text contrast
 * - Full interactivity: hover, drag, zoom, detail toggle
 * - Spiral/S-shaped layout for top-level topics based on temporal order
 * - Semantic similarity-based color assignment for topics
 * 
 * Data format:
 * {
 *   nodes: [{ 
 *     id, label, level, size, group, 
 *     frequency, confidence, keywords,
 *     first_seen_message_id, last_seen_message_id,
 *     position (top-level topics only), timestamp (optional)
 *   }],
 *   links: [{ source, target, weight, type }]
 * }
 */

// Configuration for layout and similarity
const LAYOUT_CONFIG = {
  type: 's-shaped',        // 'spiral' or 's-shaped'
  direction: 'top-bottom',  // 'top-bottom' or 'bottom-top'
  spacing: 150,             // pixels between positions along path
  centerOffset: 200,        // distance from center for spiral/S-curve
  radiusMultiplier: 1.5,    // for spiral: how fast radius grows
  nodesPerRow: 4            // number of nodes per row in S-shaped layout
};

const SIMILARITY_CONFIG = {
  threshold: 0.25,          // 0-1: similarity score for color reuse (Reduce threshold to allow more topics to share colors)
  method: 'keyword-overlap' // 'keyword-overlap' or 'edit-distance'
};

/**
 * CONFIGURATION GUIDE
 * ===================
 * 
 * LAYOUT_CONFIG:
 * - type: Choose 'spiral' for logarithmic spiral or 's-shaped' for S-curve layout
 * - direction: 'top-bottom' (earlier→later going down) or 'bottom-top' (earlier→later going up)
 * - spacing: Vertical distance between topic positions (pixels)
 * - centerOffset: Initial distance from center; controls curve spread
 * - radiusMultiplier: For spiral only; controls radius growth rate
 * 
 * SIMILARITY_CONFIG:
 * - threshold: Topics with similarity ≥ threshold reuse the most similar topic's color
 *   Range: 0 (always reuse) to 1 (never reuse)
 *   Recommended: 0.5-0.7 for semantic similarity
 * - method: 'keyword-overlap' (faster, keyword-focused) or 'edit-distance' (levenshtein)
 * 
 * Examples:
 * // Spiral from top: topics flow outward in spiral starting from top
 * // LAYOUT_CONFIG = { type: 'spiral', direction: 'top-bottom', ... }
 * 
 * // S-curve from bottom: topics flow in S-shape starting from bottom
 * // LAYOUT_CONFIG = { type: 's-shaped', direction: 'bottom-top', ... }
 * 
 * // Strict color matching: only reuse colors for very similar topics
 * // SIMILARITY_CONFIG = { threshold: 0.8, ... }
 */

// Base topic colors - lighter, more readable palette
const TOPIC_COLORS = [
  '#60a5fa', // Light Blue
  '#a78bfa', // Light Purple  
  '#f472b6', // Light Pink
  '#fbbf24', // Light Amber
  '#34d399', // Light Emerald
  '#22d3ee', // Light Cyan
  '#818cf8', // Light Indigo
  '#fb7185'  // Light Red
];

const HIERARCHY_LINK_COLOR = '#e2e8f0';
const COOCCURRENCE_LINK_COLOR = '#fde047';

// Smaller, more readable node sizes
const SIZE_SCALE = {
  topic: { min: 14, max: 24 },      // Further reduced for clarity
  subtopic: { min: 6, max: 10 },    // Even smaller subtopics
  subsubtopic: { min: 6, max: 10 }  // Minimal detail nodes
};

// Node opacity settings for better text visibility
const NODE_OPACITY = {
  topic: 0.75,
  subtopic: 0.65,
  subsubtopic: 0.55
};

/**
 * Calculate position on spiral path for a top-level topic
 * @param {number} position - 0-based index of topic in temporal order
 * @param {number} width - SVG width
 * @param {number} height - SVG height
 * @returns {{x: number, y: number}} - coordinates
 */
function getTopicPositionOnSpiral(position, width, height) {
  const centerX = width / 2;
  const centerY = height / 2;
  
  const angle = (position * Math.PI) / 2; // Spiral angle increment
  const radius = LAYOUT_CONFIG.centerOffset + position * (LAYOUT_CONFIG.spacing / Math.PI) * LAYOUT_CONFIG.radiusMultiplier;
  
  const x = centerX + radius * Math.cos(angle);
  const y = centerY + radius * Math.sin(angle);
  
  return { x, y };
}

/**
 * Calculate position on S-shaped path for a top-level topic
 * @param {number} position - 0-based index of topic in temporal order
 * @param {number} width - SVG width
 * @param {number} height - SVG height
 * @returns {{x: number, y: number}} - coordinates
 */
function getTopicPositionOnSCurve(position, width, height) {
  const nodesPerRow = LAYOUT_CONFIG.nodesPerRow;
  const horizontalSpacing = 180; // Spacing between nodes in a row
  const verticalSpacing = LAYOUT_CONFIG.spacing;
  const startX = 180; // Left margin
  const startY = 120; // Top margin
  
  // Calculate which row this node is in (0-based)
  const row = Math.floor(position / nodesPerRow);
  // Calculate position within the row (0-based)
  const col = position % nodesPerRow;
  
  // For even rows (0, 2, 4...), go left to right
  // For odd rows (1, 3, 5...), go right to left
  const isEvenRow = row % 2 === 0;
  const actualCol = isEvenRow ? col : (nodesPerRow - 1 - col);
  
  const x = startX + actualCol * horizontalSpacing;
  const y = startY + row * verticalSpacing;
  
  return { x, y };
}

/**
 * Get coordinates for a top-level topic based on layout config
 * @param {number} position - temporal order (0-based)
 * @param {number} width - SVG width
 * @param {number} height - SVG height
 * @returns {{x: number, y: number}}
 */
function getTopLevelTopicCoordinates(position, width, height) {
  if (LAYOUT_CONFIG.type === 'spiral') {
    return getTopicPositionOnSpiral(position, width, height);
  } else if (LAYOUT_CONFIG.type === 's-shaped') {
    return getTopicPositionOnSCurve(position, width, height);
  } else {
    // Fallback: regular spiral
    return getTopicPositionOnSpiral(position, width, height);
  }
}

/**
 * Calculate semantic similarity between two topics using keyword overlap
 * @param {string} label1 - first topic label
 * @param {string} label2 - second topic label
 * @param {Array} keywords1 - keywords from first topic
 * @param {Array} keywords2 - keywords from second topic
 * @returns {number} - similarity score 0-1
 */
function calculateSimilarity(label1, label2, keywords1 = [], keywords2 = []) {
  if (SIMILARITY_CONFIG.method === 'edit-distance') {
    return calculateEditDistanceSimilarity(label1, label2);
  }
  
  // Default: keyword-overlap method
  const label1Words = label1.toLowerCase().split(/\s+/);
  const label2Words = label2.toLowerCase().split(/\s+/);
  
  // Label overlap score
  const labelOverlap = label1Words.filter(w => label2Words.includes(w)).length;
  const labelSimilarity = labelOverlap / Math.max(label1Words.length, label2Words.length);
  
  // Keyword overlap score
  let keywordSimilarity = 0;
  if (keywords1.length > 0 && keywords2.length > 0) {
    const keywordSet1 = new Set(keywords1.map(k => k.toLowerCase()));
    const keywordSet2 = new Set(keywords2.map(k => k.toLowerCase()));
    const overlap = Array.from(keywordSet1).filter(k => keywordSet2.has(k)).length;
    keywordSimilarity = overlap / Math.max(keywordSet1.size, keywordSet2.size);
  }
  
  // Weighted average: favor label similarity
  return (labelSimilarity * 0.6 + keywordSimilarity * 0.4);
}

/**
 * Calculate similarity using normalized edit distance
 * @param {string} s1 - first string
 * @param {string} s2 - second string
 * @returns {number} - similarity score 0-1
 */
function calculateEditDistanceSimilarity(s1, s2) {
  const s1Lower = s1.toLowerCase();
  const s2Lower = s2.toLowerCase();
  
  if (s1Lower === s2Lower) return 1;
  
  const len1 = s1Lower.length;
  const len2 = s2Lower.length;
  const maxLen = Math.max(len1, len2);
  
  // Levenshtein distance
  const dp = Array(len2 + 1).fill(0).map(() => Array(len1 + 1).fill(0));
  
  for (let i = 0; i <= len1; i++) dp[0][i] = i;
  for (let j = 0; j <= len2; j++) dp[j][0] = j;
  
  for (let j = 1; j <= len2; j++) {
    for (let i = 1; i <= len1; i++) {
      const cost = s1Lower[i - 1] === s2Lower[j - 1] ? 0 : 1;
      dp[j][i] = Math.min(
        dp[j][i - 1] + 1,      // insertion
        dp[j - 1][i] + 1,      // deletion
        dp[j - 1][i - 1] + cost // substitution
      );
    }
  }
  
  const distance = dp[len2][len1];
  return 1 - (distance / maxLen); // Convert to similarity (0-1)
}

/**
 * Assign colors to topics using semantic similarity
 * Reuses colors for similar topics, assigns new colors for distinct topics
 * @param {Array} topicNodes - filtered list of topic-level nodes
 * @param {Object} existingColorMap - previously persisted color assignments
 * @returns {Object} - topic_id -> color mapping
 */
function assignColorsWithSimilarity(topicNodes, existingColorMap = {}) {
  const colorMap = { ...existingColorMap };
  let nextColorIndex = Object.keys(existingColorMap).length;
  
  console.log(`[Color Assignment] Processing ${topicNodes.length} topics, threshold: ${SIMILARITY_CONFIG.threshold}`);
  
  topicNodes.forEach((node, idx) => {
    // If already colored, skip
    if (colorMap[node.id]) return;
    
    let assignedColor = null;
    let maxSimilarity = 0;
    let bestMatch = null;
    
    // Check similarity with all previously colored topics
    Object.entries(colorMap).forEach(([topicId, color]) => {
      // Find the previous topic node to get its keywords
      const prevTopicNode = topicNodes.find(n => n.id === topicId);
      if (!prevTopicNode) return;
      
      const similarity = calculateSimilarity(
        node.label,
        prevTopicNode.label,
        node.keywords || [],
        prevTopicNode.keywords || []
      );
      
      if (similarity > maxSimilarity) {
        maxSimilarity = similarity;
        bestMatch = prevTopicNode.label;
        assignedColor = similarity >= SIMILARITY_CONFIG.threshold ? color : null;
      }
    });
    
    // Assign color: reuse if similar, otherwise new color
    if (assignedColor) {
      colorMap[node.id] = assignedColor;
      console.log(`[Color Reuse] "${node.label}" similar to "${bestMatch}" (${maxSimilarity.toFixed(2)}) → ${assignedColor}`);
    } else {
      colorMap[node.id] = TOPIC_COLORS[nextColorIndex % TOPIC_COLORS.length];
      console.log(`[New Color] "${node.label}" → ${colorMap[node.id]} (best match: ${maxSimilarity.toFixed(2)})`);
      nextColorIndex++;
    }
  });
  
  return colorMap;
}

/**
 * Normalize and validate incoming data
 * Filters out subsubtopic (detail) nodes to reduce clutter
 */
function normalizeData(raw) {
  if (!raw || typeof raw !== 'object') {
    return { nodes: [], links: [] };
  }
  
  const nodes = Array.isArray(raw.nodes) ? raw.nodes : [];
  const links = Array.isArray(raw.links) ? raw.links : [];
  
  // Filter out subsubtopic nodes - only keep topic and subtopic
  const validNodes = nodes.filter(n => 
    n.id && n.label && n.level && n.level !== 'subsubtopic'
  );
  
  // Only keep links between remaining nodes
  const nodeIds = new Set(validNodes.map(n => n.id));
  const validLinks = links.filter(l => 
    nodeIds.has(typeof l.source === 'object' ? l.source.id : l.source) &&
    nodeIds.has(typeof l.target === 'object' ? l.target.id : l.target)
  );
  
  return { nodes: validNodes, links: validLinks };
}

/**
 * Calculate node radius based on level and size
 */
function getNodeRadius(node) {
  const scale = SIZE_SCALE[node.level] || SIZE_SCALE.subsubtopic;
  const baseSize = node.size || 10;
  
  // Map size to radius range
  const radius = scale.min + (Math.min(baseSize, 50) / 50) * (scale.max - scale.min);
  return radius;
}

/**
 * Get node color based on level
 */
function getNodeColor(node, colorMap) {
  return colorMap[node.id] || TOPIC_COLORS[0];
}

/**
 * Get link color based on type
 */
function getLinkColor(link) {
  return link.type === 'hierarchy' ? HIERARCHY_LINK_COLOR : COOCCURRENCE_LINK_COLOR;
}

/**
 * Create lighter/darker shade of a color
 */
function shadeColor(color, percent) {
  // Ensure color is valid
  if (!color || typeof color !== 'string' || !color.startsWith('#')) {
    return TOPIC_COLORS[0]; // Fallback to default color
  }

  let R = parseInt(color.substring(1, 3), 16);
  let G = parseInt(color.substring(3, 5), 16);
  let B = parseInt(color.substring(5, 7), 16);

  // Check for NaN
  if (isNaN(R) || isNaN(G) || isNaN(B)) {
    return TOPIC_COLORS[0];
  }

  R = parseInt((R * (100 + percent)) / 100);
  G = parseInt((G * (100 + percent)) / 100);
  B = parseInt((B * (100 + percent)) / 100);

  R = R < 255 ? (R < 0 ? 0 : R) : 255;
  G = G < 255 ? (G < 0 ? 0 : G) : 255;
  B = B < 255 ? (B < 0 ? 0 : B) : 255;

  const RR = R.toString(16).padStart(2, '0');
  const GG = G.toString(16).padStart(2, '0');
  const BB = B.toString(16).padStart(2, '0');

  return '#' + RR + GG + BB;
}

/**
 * Build topic ID to label mapping for color assignment
 */
function buildTopicMapping(nodes) {
  const topicIdToLabel = new Map();
  nodes.forEach(node => {
    if (node.level === 'topic') {
      topicIdToLabel.set(node.id, node.label || node.id);
    }
  });
  return topicIdToLabel;
}

/**
 * Assign colors to topics with similarity-based reuse
 * Then inherit colors to subtopics
 */
function buildColorMap(nodes, links) {
  const colorMap = {};
  
  // Get all topic-level nodes
  const topicNodes = nodes.filter(n => n.level === 'topic');
  
  // Initialize with empty existing color map (will be populated from session storage if needed)
  const existingColorMap = {};
  
  // Assign colors using semantic similarity
  const topicColorMap = assignColorsWithSimilarity(topicNodes, existingColorMap);
  
  // Apply topic colors to color map
  topicNodes.forEach(node => {
    colorMap[node.id] = topicColorMap[node.id];
  });

  // Find parent topic for each subtopic/subsubtopic via links
  const nodeToParent = new Map();
  links.forEach(link => {
    const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
    const targetId = typeof link.target === 'object' ? link.target.id : link.target;
    
    const sourceNode = nodes.find(n => n.id === sourceId);
    const targetNode = nodes.find(n => n.id === targetId);
    
    if (sourceNode && targetNode && link.type === 'hierarchy') {
      if (sourceNode.level === 'topic' && targetNode.level === 'subtopic') {
        nodeToParent.set(targetId, sourceId);
      } else if (sourceNode.level === 'subtopic' && targetNode.level === 'subsubtopic') {
        nodeToParent.set(targetId, sourceId);
      }
    }
  });

  // Assign colors to subtopics and subsubtopics (inherit from parent topic)
  nodes.forEach(node => {
    if (node.level === 'subtopic') {
      const parentTopicId = nodeToParent.get(node.id);
      if (parentTopicId && colorMap[parentTopicId]) {
        colorMap[node.id] = shadeColor(colorMap[parentTopicId], 20); // Lighter
      } else {
        colorMap[node.id] = shadeColor(TOPIC_COLORS[0], 20);
      }
    } else if (node.level === 'subsubtopic') {
      // Find parent subtopic first, then its topic
      const parentSubtopicId = nodeToParent.get(node.id);
      if (parentSubtopicId) {
        const parentTopicId = nodeToParent.get(parentSubtopicId);
        if (parentTopicId && colorMap[parentTopicId]) {
          colorMap[node.id] = shadeColor(colorMap[parentTopicId], 40); // Even lighter
        } else if (colorMap[parentSubtopicId]) {
          colorMap[node.id] = shadeColor(colorMap[parentSubtopicId], 20);
        } else {
          colorMap[node.id] = shadeColor(TOPIC_COLORS[0], 40);
        }
      } else {
        colorMap[node.id] = shadeColor(TOPIC_COLORS[0], 40);
      }
    }
  });

  return colorMap;
}

export default function TopicFlowVisualization({ data, onTopicClick }) {
  const svgRef = useRef(null);
  const wrapperRef = useRef(null);
  const simulationRef = useRef(null);
  const zoomBehaviorRef = useRef(null);
  const colorMapRef = useRef({});

  const normalized = useMemo(() => normalizeData(data), [data]);

  // Zoom control functions
  const handleZoomIn = () => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(300)
        .call(zoomBehaviorRef.current.scaleBy, 1.3);
    }
  };

  const handleZoomOut = () => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(300)
        .call(zoomBehaviorRef.current.scaleBy, 0.77);
    }
  };

  const handleZoomReset = () => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(500)
        .call(zoomBehaviorRef.current.transform, d3.zoomIdentity);
    }
  };

  useEffect(() => {
    const svgEl = svgRef.current;
    const wrapperEl = wrapperRef.current;
    if (!svgEl || !wrapperEl) return;

    const { width: containerWidth, height: containerHeight } = wrapperEl.getBoundingClientRect();
    const width = Math.max(600, containerWidth || 600);
    const height = Math.max(400, containerHeight || 400);

    // Clear previous content
    const svg = d3.select(svgEl)
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height])
      .attr('role', 'img')
      .attr('aria-label', 'Topic Flow force-directed graph');

    svg.selectAll('*').remove();

    const { nodes, links } = normalized;

    if (nodes.length === 0) {
      // Show empty state
      svg.append('text')
        .attr('x', width / 2)
        .attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', '#94a3b8')
        .attr('font-size', '14px')
        .text('No topics yet. Start chatting to populate the graph.');
      return;
    }

    try {
      // Add position attribute to top-level topics (temporal order)
      const topicNodes = nodes.filter(n => n.level === 'topic');
      
      // Sort by first_seen_message_id in REVERSE order (newest first)
      topicNodes.sort((a, b) => {
        const aId = a.first_seen_message_id || 0;
        const bId = b.first_seen_message_id || 0;
        return bId - aId; // Reversed: newest topics appear first (top)
      });
      
      // Assign position and fix coordinates based on sorted order
      topicNodes.forEach((node, index) => {
        node.position = index; // 0-based temporal order
        // Pre-calculate and fix position for topic nodes
        const coords = getTopLevelTopicCoordinates(index, width, height);
        node.fx = coords.x; // Fix x position
        node.fy = coords.y; // Fix y position
      });
      console.log(`[TopicFlowVisualization] Fixed positions for ${topicNodes.length} top-level topics in S-shaped layout (sorted by first_seen_message_id)`);

      // Build color map for inherited colors
      colorMapRef.current = buildColorMap(nodes, links);
    } catch (err) {
      console.error('[TopicFlowVisualization] Error in color mapping:', err);
      colorMapRef.current = {};
    }

    // Create zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.5, 3])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);
    zoomBehaviorRef.current = zoom; // Store zoom behavior for button controls

    const g = svg.append('g');

    // Tooltip
    const tooltip = d3.select(wrapperEl)
      .selectAll('div.topic-tooltip')
      .data([null])
      .join('div')
      .attr('class', 'topic-tooltip')
      .style('position', 'absolute')
      .style('pointer-events', 'none')
      .style('padding', '8px 12px')
      .style('background', 'rgba(255, 255, 255, 0.95)')
      .style('border', '1px solid #e2e8f0')
      .style('border-radius', '8px')
      .style('font-size', '13px')
      .style('color', '#1e293b')
      .style('box-shadow', '0 4px 12px rgba(0,0,0,0.1)')
      .style('opacity', 0)
      .style('z-index', 1000);

    // Create force simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links)
        .id(d => d.id)
        .distance(d => {
          // Very short distances for hierarchy to keep children tight around parents
          return d.type === 'hierarchy' ? 35 : 80;
        })
        .strength(d => d.type === 'hierarchy' ? 1.5 : 0.02)
      )
      .force('charge', d3.forceManyBody()
        .strength(d => {
          // Topic nodes are fixed, so minimal charge
          if (d.level === 'topic') return -60;
          // Subtopics need more repulsion to spread out
          if (d.level === 'subtopic') return -120;
          return -50;
        })
      )
      .force('collision', d3.forceCollide()
        .radius(d => getNodeRadius(d) + 10)
        .strength(1.0)
      )
      .alphaDecay(0.015)
      .velocityDecay(0.4);

    simulationRef.current = simulation;

    // Draw S-shaped path line connecting topic nodes in temporal order
    const topicNodesInOrder = nodes.filter(n => n.level === 'topic' && n.position !== undefined)
      .sort((a, b) => a.position - b.position);
    
    if (topicNodesInOrder.length > 1) {
      // Build smooth curve path using quadratic Bezier curves
      let pathData = '';
      topicNodesInOrder.forEach((node, i) => {
        const coords = getTopLevelTopicCoordinates(node.position, width, height);
        
        if (i === 0) {
          pathData = `M ${coords.x},${coords.y}`;
        } else {
          const prevNode = topicNodesInOrder[i - 1];
          const prevCoords = getTopLevelTopicCoordinates(prevNode.position, width, height);
          
          // Calculate control point for smooth curve (midpoint with slight offset)
          const midX = (prevCoords.x + coords.x) / 2;
          const midY = (prevCoords.y + coords.y) / 2;
          
          // Use quadratic bezier curve for smooth transition
          pathData += ` Q ${midX},${midY} ${coords.x},${coords.y}`;
        }
      });
      
      g.append('path')
        .attr('d', pathData)
        .attr('stroke', '#cbd5e1')
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', '8,4')
        .attr('fill', 'none')
        .attr('opacity', 0.4)
        .style('pointer-events', 'none');
    }

    // Draw links
    const linkGroup = g.append('g')
      .attr('class', 'links')
      .attr('stroke-opacity', 0.6);

    const linkElements = linkGroup.selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', getLinkColor)
      .attr('stroke-width', d => {
        // Hierarchy links: thicker
        return d.type === 'hierarchy' ? 2 : 1;
      })
      .attr('stroke-dasharray', d => {
        // Co-occurrence links: dashed
        return d.type === 'cooccurrence' ? '5,5' : null;
      });

    // Draw nodes
    const nodeGroup = g.append('g')
      .attr('class', 'nodes');

    const nodeElements = nodeGroup.selectAll('g')
      .data(nodes)
      .join('g')
      .attr('class', 'node')
      .style('cursor', 'pointer')
      .call(drag(simulation));

    // Node circles with optimized opacity and stroke
    nodeElements.append('circle')
      .attr('r', getNodeRadius)
      .attr('fill', d => getNodeColor(d, colorMapRef.current))
      .attr('fill-opacity', d => NODE_OPACITY[d.level] || 0.6)
      .attr('stroke', '#ffffff')
      .attr('stroke-width', d => {
        if (d.level === 'topic') return 2.5;
        if (d.level === 'subtopic') return 1.5;
        return 1;
      })
      .attr('stroke-opacity', 0.9)
      .style('filter', 'drop-shadow(0px 1px 3px rgba(0,0,0,0.08))');

    // Node labels - optimized for readability
    nodeElements.append('text')
      .attr('dy', d => {
        // Position text below node with smaller offset
        return getNodeRadius(d) + 12;
      })
      .attr('text-anchor', 'middle')
      .attr('font-size', d => {
        if (d.level === 'topic') return '12px';
        return '10px'; // subtopic
      })
      .attr('font-weight', d => d.level === 'topic' ? 600 : 500)
      .attr('fill', '#334155')
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .attr('paint-order', 'stroke')
      .style('pointer-events', 'none')
      .text(d => {
        const maxLen = d.level === 'topic' ? 18 : 12;
        return d.label.length > maxLen ? d.label.slice(0, maxLen) + '...' : d.label;
      });

    // Hover interactions
    nodeElements
      .on('mouseenter', function(event, d) {
        // Highlight node
        d3.select(this).select('circle')
          .transition().duration(200)
          .attr('fill-opacity', 1)
          .attr('stroke-width', d.level === 'topic' ? 3.5 : 2.5);

        // Show tooltip
        const tooltipContent = `
          <div style="font-weight: 600; margin-bottom: 4px; color: #1e293b;">${d.label}</div>
          <div style="font-size: 11px; color: #64748b;">
            <strong>Level:</strong> ${d.level}<br/>
            ${d.frequency ? `<strong>Frequency:</strong> ${d.frequency}<br/>` : ''}
            ${d.keywords && d.keywords.length ? `<strong>Keywords:</strong> ${d.keywords.slice(0, 3).join(', ')}` : ''}
          </div>
        `;
        
        tooltip
          .style('opacity', 1)
          .style('left', `${event.pageX - wrapperEl.getBoundingClientRect().left + 12}px`)
          .style('top', `${event.pageY - wrapperEl.getBoundingClientRect().top - 10}px`)
          .html(tooltipContent);

        // Highlight connected nodes and links
        const connectedNodeIds = new Set();
        links.forEach(link => {
          const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
          const targetId = typeof link.target === 'object' ? link.target.id : link.target;
          
          if (sourceId === d.id) connectedNodeIds.add(targetId);
          if (targetId === d.id) connectedNodeIds.add(sourceId);
        });

        nodeElements.style('opacity', node => 
          node.id === d.id || connectedNodeIds.has(node.id) ? 1 : 0.3
        );

        linkElements.style('opacity', link => {
          const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
          const targetId = typeof link.target === 'object' ? link.target.id : link.target;
          return sourceId === d.id || targetId === d.id ? 0.9 : 0.1;
        });
      })
      .on('mouseleave', function(event, d) {
        // Reset highlighting
        d3.select(this).select('circle')
          .transition().duration(200)
          .attr('fill-opacity', NODE_OPACITY[d.level] || 0.6)
          .attr('stroke-width', d.level === 'topic' ? 2.5 : 1.5);

        tooltip.style('opacity', 0);

        nodeElements.style('opacity', 1);
        linkElements.style('opacity', 0.6);
      })
      .on('click', (event, d) => {
        if (onTopicClick) onTopicClick(d);
      });

    // Update positions on simulation tick
    simulation.on('tick', () => {
      // Topic nodes are already fixed via fx/fy, no need to update them here
      
      linkElements
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      nodeElements
        .attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // Cleanup
    return () => {
      if (simulationRef.current) {
        simulationRef.current.stop();
      }
      tooltip.remove();
    };
  }, [normalized, onTopicClick]);

  // Drag behavior
  function drag(simulation) {
    function dragstarted(event) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    return d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended);
  }

  return (
    <div 
      ref={wrapperRef} 
      style={{ 
        position: 'relative', 
        width: '100%', 
        height: '100%',
        overflow: 'hidden'
      }}
    >
      <svg ref={svgRef} aria-label="Topic Flow visualization" />
      
      {/* Zoom Controls */}
      {normalized.nodes.length > 0 && (
        <div style={{
          position: 'absolute',
          bottom: 10,
          right: 10,
          display: 'flex',
          flexDirection: 'column',
          gap: '6px'
        }}>
          <button
            onClick={handleZoomIn}
            title="Zoom In"
            style={{
              width: 36,
              height: 36,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '18px',
              fontWeight: 600,
              color: '#6366f1',
              boxShadow: '0 2px 6px rgba(0,0,0,0.08)',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.target.style.background = '#6366f1';
              e.target.style.color = '#fff';
              e.target.style.transform = 'scale(1.05)';
            }}
            onMouseLeave={(e) => {
              e.target.style.background = 'rgba(255, 255, 255, 0.95)';
              e.target.style.color = '#6366f1';
              e.target.style.transform = 'scale(1)';
            }}
          >
            +
          </button>
          
          <button
            onClick={handleZoomOut}
            title="Zoom Out"
            style={{
              width: 36,
              height: 36,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '20px',
              fontWeight: 600,
              color: '#6366f1',
              boxShadow: '0 2px 6px rgba(0,0,0,0.08)',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.target.style.background = '#6366f1';
              e.target.style.color = '#fff';
              e.target.style.transform = 'scale(1.05)';
            }}
            onMouseLeave={(e) => {
              e.target.style.background = 'rgba(255, 255, 255, 0.95)';
              e.target.style.color = '#6366f1';
              e.target.style.transform = 'scale(1)';
            }}
          >
            −
          </button>
          
          <button
            onClick={handleZoomReset}
            title="Reset Zoom"
            style={{
              width: 36,
              height: 36,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '16px',
              color: '#6366f1',
              boxShadow: '0 2px 6px rgba(0,0,0,0.08)',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.target.style.background = '#6366f1';
              e.target.style.color = '#fff';
              e.target.style.transform = 'scale(1.05)';
            }}
            onMouseLeave={(e) => {
              e.target.style.background = 'rgba(255, 255, 255, 0.95)';
              e.target.style.color = '#6366f1';
              e.target.style.transform = 'scale(1)';
            }}
          >
            ⊙
          </button>
        </div>
      )}
    </div>
  );
}
