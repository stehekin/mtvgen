import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import { useAudioData, visualizeAudio } from '@remotion/media-utils';

export const WaveformVisualizer: React.FC<{ audioSrc: string }> = ({ audioSrc }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const audioData = useAudioData(audioSrc);

  if (!audioData) return null;

  const numPoints = 120;
  const visualization = visualizeAudio({
    fps,
    frame,
    audioData,
    numberOfSamples: numPoints,
  });

  const width = 1920;
  const height = 1080;
  const centerY = height * 0.72;

  // Build smooth SVG curve path
  const points = visualization.map((val: number, i: number) => {
    const x = (i / (numPoints - 1)) * width;
    const amplitude = val * 180;
    const y = centerY + (i % 2 === 0 ? -amplitude : amplitude);
    return `${x},${y}`;
  });

  const pathData = `M 0,${centerY} ` + points.map((p: string) => `L ${p}`).join(' ') + ` L ${width},${centerY}`;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 5,
      }}
    >
      <svg width={width} height={height} style={{ overflow: 'visible' }}>
        <path
          d={pathData}
          fill="none"
          stroke="url(#waveGradient)"
          strokeWidth="4"
          strokeLinecap="round"
          style={{
            filter: 'drop-shadow(0 0 12px rgba(0, 229, 255, 0.8))',
          }}
        />
        <defs>
          <linearGradient id="waveGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#00e5ff" />
            <stop offset="50%" stopColor="#7928ca" />
            <stop offset="100%" stopColor="#ff007f" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
};
