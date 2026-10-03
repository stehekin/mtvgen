import React, { useMemo } from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';

const NUM_PARTICLES = 50;

interface ParticleData {
  id: number;
  xStart: number;
  yStart: number;
  size: number;
  speed: number;
  opacity: number;
  xDrift: number;
  driftSpeed: number;
}

// Pseudo-random generator to make it deterministic
function mulberry32(a: number) {
  return function() {
    var t = a += 0x6D2B79F5;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  }
}

export const Particles: React.FC = () => {
  const frame = useCurrentFrame();
  const { height, width } = useVideoConfig();

  const particles = useMemo(() => {
    const random = mulberry32(12345);
    const p: ParticleData[] = [];
    for (let i = 0; i < NUM_PARTICLES; i++) {
      p.push({
        id: i,
        xStart: random(),
        yStart: random(),
        size: 2 + random() * 6,
        speed: 0.5 + random() * 1.5,
        opacity: 0.1 + random() * 0.3,
        xDrift: random() * 50,
        driftSpeed: 0.01 + random() * 0.02,
      });
    }
    return p;
  }, []);

  return (
    <div style={{ position: 'absolute', width: '100%', height: '100%', pointerEvents: 'none' }}>
      {particles.map((p) => {
        // Calculate current position
        // Particles drift upwards, wrapping around
        const yDist = (frame * p.speed) % (height + 100);
        const y = height + 50 - yDist;
        
        // Particles drift side to side
        const xOffset = Math.sin(frame * p.driftSpeed + p.yStart * 100) * p.xDrift;
        const x = (p.xStart * width) + xOffset;

        return (
          <div
            key={p.id}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: p.size,
              height: p.size,
              borderRadius: '50%',
              backgroundColor: 'white',
              opacity: p.opacity,
              boxShadow: `0 0 ${p.size * 2}px ${p.size / 2}px rgba(255, 255, 255, ${p.opacity})`,
            }}
          />
        );
      })}
    </div>
  );
};
