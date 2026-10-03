import React from 'react';
import { useCurrentFrame } from 'remotion';

export const VaporwaveTheme: React.FC = () => {
  const frame = useCurrentFrame();

  // Moving grid offset
  const gridOffset = (frame * 3) % 40;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        background: 'linear-gradient(to bottom, #11052c 0%, #3d085a 45%, #f4306e 70%, #ff8a00 100%)',
        overflow: 'hidden',
      }}
    >
      {/* Synthwave Sun */}
      <div
        style={{
          position: 'absolute',
          bottom: '28%',
          left: '50%',
          transform: 'translateX(-50%)',
          width: '420px',
          height: '420px',
          borderRadius: '50%',
          background: 'linear-gradient(to bottom, #ffe600 0%, #ff0055 100%)',
          boxShadow: '0 0 80px rgba(255, 0, 85, 0.8), 0 0 160px rgba(255, 230, 0, 0.5)',
        }}
      />

      {/* Perspective Synthwave Grid */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: '-50%',
          width: '200%',
          height: '35%',
          perspective: '600px',
        }}
      >
        <div
          style={{
            width: '100%',
            height: '100%',
            transform: 'rotateX(65deg)',
            transformOrigin: 'bottom center',
            backgroundImage: `
              linear-gradient(to right, rgba(0, 229, 255, 0.4) 2px, transparent 2px),
              linear-gradient(to bottom, rgba(0, 229, 255, 0.4) 2px, transparent 2px)
            `,
            backgroundSize: `40px 40px`,
            backgroundPosition: `0px ${gridOffset}px`,
            boxShadow: '0 0 40px rgba(0, 229, 255, 0.6) inset',
          }}
        />
      </div>
    </div>
  );
};
