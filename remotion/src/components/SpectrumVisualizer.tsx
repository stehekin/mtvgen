import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import { useAudioData, visualizeAudio } from '@remotion/media-utils';

export const SpectrumVisualizer: React.FC<{ audioSrc: string }> = ({ audioSrc }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const audioData = useAudioData(audioSrc);

  if (!audioData) {
    return null;
  }

  const numBars = 64;
  const visualization = visualizeAudio({
    fps,
    frame,
    audioData,
    numberOfSamples: numBars,
  });

  // Calculate bass intensity for scale pulse
  const bassSum = visualization.slice(0, 8).reduce((acc, v) => acc + v, 0);
  const bassAvg = bassSum / 8;
  const scale = 1 + bassAvg * 0.5;

  return (
    <div
      style={{
        position: 'absolute',
        bottom: '50px',
        left: 0,
        width: '100%',
        height: '200px',
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'center',
        gap: '4px',
        transform: `scale(${scale})`,
        transformOrigin: 'bottom center',
        transition: 'transform 0.1s ease-out',
      }}
    >
      {visualization.map((v, i) => {
        // height mapped to a reasonable range
        const height = Math.max(4, v * 300);
        
        return (
          <div
            key={i}
            style={{
              width: '8px',
              height: `${height}px`,
              background: 'linear-gradient(to top, #00e5ff, #ff007f)',
              borderRadius: '4px',
              boxShadow: '0 0 10px rgba(0, 229, 255, 0.5), 0 0 20px rgba(255, 0, 127, 0.3)',
            }}
          />
        );
      })}
    </div>
  );
};
