import React from 'react';
import { useCurrentFrame } from 'remotion';

export const SunsetTheme: React.FC = () => {
  const frame = useCurrentFrame();
  const shift = Math.sin(frame / 80) * 15;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        background: `linear-gradient(${135 + shift}deg, #1a051d 0%, #4a1235 45%, #8c2548 75%, #e05638 100%)`,
        overflow: 'hidden',
      }}
    >
      {/* Warm ambient radial glow */}
      <div
        style={{
          position: 'absolute',
          bottom: '-10%',
          left: '50%',
          transform: 'translateX(-50%)',
          width: '900px',
          height: '600px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(255, 140, 66, 0.25) 0%, transparent 70%)',
          filter: 'blur(60px)',
        }}
      />
    </div>
  );
};
