import React from 'react';
import { useCurrentFrame } from 'remotion';

export const CosmicTheme: React.FC = () => {
  const frame = useCurrentFrame();

  const pulse = Math.sin(frame / 60) * 0.15 + 0.85;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        backgroundColor: '#03020d',
        overflow: 'hidden',
      }}
    >
      {/* Nebula 1 */}
      <div
        style={{
          position: 'absolute',
          top: '10%',
          left: '20%',
          width: '600px',
          height: '600px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(147, 51, 234, 0.25) 0%, transparent 70%)',
          transform: `scale(${pulse})`,
          filter: 'blur(40px)',
        }}
      />
      {/* Nebula 2 */}
      <div
        style={{
          position: 'absolute',
          bottom: '15%',
          right: '15%',
          width: '700px',
          height: '700px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(14, 165, 233, 0.2) 0%, transparent 70%)',
          transform: `scale(${1.2 - pulse * 0.2})`,
          filter: 'blur(50px)',
        }}
      />
    </div>
  );
};
