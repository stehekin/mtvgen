import React from 'react';
import { useCurrentFrame } from 'remotion';

export const AuroraTheme: React.FC = () => {
  const frame = useCurrentFrame();

  const wave1 = Math.sin(frame / 70) * 20;
  const wave2 = Math.cos(frame / 90) * 25;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        backgroundColor: '#021314',
        overflow: 'hidden',
      }}
    >
      {/* Emerald Aurora Ribbon 1 */}
      <div
        style={{
          position: 'absolute',
          top: '-20%',
          left: `${10 + wave1}%`,
          width: '80%',
          height: '140%',
          background: 'radial-gradient(ellipse at center, rgba(16, 185, 129, 0.28) 0%, rgba(5, 150, 105, 0.15) 45%, transparent 70%)',
          transform: 'rotate(-25deg)',
          filter: 'blur(50px)',
        }}
      />
      {/* Teal Aurora Ribbon 2 */}
      <div
        style={{
          position: 'absolute',
          bottom: '-20%',
          right: `${10 + wave2}%`,
          width: '75%',
          height: '130%',
          background: 'radial-gradient(ellipse at center, rgba(6, 182, 212, 0.25) 0%, rgba(14, 116, 144, 0.12) 50%, transparent 70%)',
          transform: 'rotate(20deg)',
          filter: 'blur(60px)',
        }}
      />
    </div>
  );
};
