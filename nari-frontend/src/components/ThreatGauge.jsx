import React from 'react';

const ThreatGauge = ({ score = 15, state = 'Normal' }) => {
  // Score range: 0 to 100
  const normalizedScore = Math.min(Math.max(score, 0), 100);
  const strokeDasharray = 283; // Circumference for r=45 (2 * PI * 45)
  const strokeDashoffset = strokeDasharray - (strokeDasharray * normalizedScore) / 100;

  const getColor = () => {
    if (state === 'Emergency' || normalizedScore > 70) return '#FF3B30';
    if (state === 'Warning' || normalizedScore > 35) return '#FF9500';
    return '#34C759';
  };

  const getLabel = () => {
    if (state === 'Emergency' || normalizedScore > 70) return 'CRITICAL';
    if (state === 'Warning' || normalizedScore > 35) return 'ELEVATED';
    return 'SAFE';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
      <svg width="160" height="160" viewBox="0 0 100 100">
        {/* Background track */}
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke="var(--bg-input)"
          strokeWidth="8"
        />
        {/* Animated Gauge Arc */}
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke={getColor()}
          strokeWidth="8"
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
          style={{ transition: 'stroke-dashoffset 0.8s ease, stroke 0.5s ease' }}
        />
      </svg>
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        textAlign: 'center'
      }}>
        <div style={{ fontSize: '28px', fontWeight: '800', color: getColor() }}>
          {normalizedScore}%
        </div>
        <div style={{ fontSize: '11px', fontWeight: '700', letterSpacing: '1px', color: 'var(--text-muted)' }}>
          {getLabel()}
        </div>
      </div>
    </div>
  );
};

export default ThreatGauge;
