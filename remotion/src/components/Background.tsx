import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';

export const Background: React.FC = () => {
  const frame = useCurrentFrame();

  // Slow rotation
  const angle = interpolate(frame, [0, 3000], [0, 360], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'identity',
  });

  // Cycle colors slowly
  // Deep dark background (#0a0a1a), with neon accents — magenta (#ff007f), electric cyan (#00e5ff), purple (#7928ca)
  
  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        background: `linear-gradient(${angle}deg, #0a0a1a 0%, #1a0a2a 50%, #0a1a2a 100%)`,
      }}
    >
      <div 
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: `radial-gradient(circle at ${50 + Math.sin(frame/200)*20}% ${50 + Math.cos(frame/150)*20}%, rgba(121, 40, 202, 0.3) 0%, transparent 60%)`,
        }}
      />
      <div 
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: `radial-gradient(circle at ${50 + Math.cos(frame/180)*30}% ${50 + Math.sin(frame/220)*30}%, rgba(255, 0, 127, 0.2) 0%, transparent 50%)`,
        }}
      />
      <div 
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: `radial-gradient(circle at ${50 - Math.sin(frame/160)*25}% ${50 - Math.cos(frame/190)*25}%, rgba(0, 229, 255, 0.15) 0%, transparent 55%)`,
        }}
      />
    </div>
  );
};
