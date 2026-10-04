import React from 'react';
import { useCurrentFrame } from 'remotion';

export const MidnightTheme: React.FC = () => {
  const frame = useCurrentFrame();

  const pulse = Math.sin(frame / 100) * 0.1 + 0.9;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        background: 'linear-gradient(to bottom, #050b1e 0%, #0f172a 50%, #1e1b4b 100%)',
        overflow: 'hidden',
      }}
    >
      {/* Royal Indigo Glow */}
      <div
        style={{
          position: 'absolute',
          top: '30%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '800px',
          height: '800px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(99, 102, 241, 0.2) 0%, transparent 65%)',
          filter: 'blur(70px)',
          opacity: pulse,
        }}
      />
    </div>
  );
};
