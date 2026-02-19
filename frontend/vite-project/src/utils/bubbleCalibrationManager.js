/**
 * Bubble Calibration Manager
 * 
 * Manages calibration data for message bubbles in the chat interface.
 * Stores metadata about selected bubbles for trust calibration and analysis.
 */

class BubbleCalibrationManager {
  constructor() {
    this.calibrationData = new Map();
  }

  /**
   * Set calibration data for a bubble
   * @param {string} bubbleId - Unique identifier for the bubble
   * @param {Object} data - Calibration data (message, role, index, timestamp, etc.)
   */
  setCalibration(bubbleId, data) {
    if (!bubbleId) {
      console.warn('[BubbleCalibrationManager] Invalid bubbleId provided');
      return;
    }

    const existing = this.calibrationData.get(bubbleId) || {};
    const mergedMetadata = data?.metadata
      ? { ...(existing.metadata || {}), ...data.metadata }
      : existing.metadata;

    this.calibrationData.set(bubbleId, {
      ...existing,
      ...data,
      metadata: mergedMetadata,
      updatedAt: new Date().toISOString()
    });

    console.log(`[BubbleCalibrationManager] Set calibration for ${bubbleId}:`, data);
  }

  /**
   * Set calibration result for a bubble
   * @param {string} bubbleId - Unique identifier for the bubble
   * @param {Object} calibrationResult - Raw calibration response
   * @param {Object} [metadata={}] - Additional metadata (userQuery, assistantAnswer, role, etc.)
   */
  setCalibrationResult(bubbleId, calibrationResult, metadata = {}) {
    if (!bubbleId || !calibrationResult) {
      console.warn('[BubbleCalibrationManager] Invalid calibration result provided');
      return;
    }

    const existing = this.calibrationData.get(bubbleId) || {};
    const mergedMetadata = {
      ...(existing.metadata || {}),
      ...metadata,
      rawCalibration: calibrationResult,
    };

    this.setCalibration(bubbleId, {
      confidenceScore:
        calibrationResult.overall_confidence ??
        calibrationResult.confidenceScore ??
        null,
      uncertaintyType:
        calibrationResult.uncertainty_type ??
        calibrationResult.uncertaintyType ??
        [],
      explanationText:
        calibrationResult.explanation ??
        calibrationResult.explanationText ??
        '',
      metadata: mergedMetadata,
    });
  }

  /**
   * Get calibration data for a bubble
   * @param {string} bubbleId - Unique identifier for the bubble
   * @returns {Object|undefined} Calibration data or undefined if not found
   */
  getCalibration(bubbleId) {
    return this.calibrationData.get(bubbleId);
  }

  /**
   * Get all calibration data
   * @returns {Object} Map of all calibration data
   */
  getAllCalibrations() {
    return new Map(this.calibrationData);
  }

  /**
   * Clear calibration data for a specific bubble
   * @param {string} bubbleId - Unique identifier for the bubble
   */
  clearCalibration(bubbleId) {
    if (this.calibrationData.has(bubbleId)) {
      this.calibrationData.delete(bubbleId);
      console.log(`[BubbleCalibrationManager] Cleared calibration for ${bubbleId}`);
    }
  }

  /**
   * Clear all calibration data
   */
  clearAll() {
    this.calibrationData.clear();
    console.log('[BubbleCalibrationManager] Cleared all calibration data');
  }

  /**
   * Get calibration summary
   * @returns {Object} Summary of calibration data
   */
  getSummary() {
    return {
      totalBubbles: this.calibrationData.size,
      bubbleIds: Array.from(this.calibrationData.keys()),
      lastUpdated: this.calibrationData.size > 0
        ? Array.from(this.calibrationData.values())[this.calibrationData.size - 1].updatedAt
        : null
    };
  }
}

// Export singleton instance
export const bubbleCalibrationManager = new BubbleCalibrationManager();

export default bubbleCalibrationManager;
