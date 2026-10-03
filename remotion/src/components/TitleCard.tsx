import React from 'react';
import { useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';

interface TitleCardProps {
  title: string;
  artist: string;
  singingStartTime: number; // seconds — when the first lyric line begins
}

export const TitleCard: React.FC<TitleCardProps> = ({ title, artist, singingStartTime }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  // Fade out before singing starts (start fading 1.5s before first lyric)
  const fadeOutStart = Math.max(0, singingStartTime - 2.0);
  const fadeOutEnd = Math.max(0.5, singingStartTime - 0.5);

  // Don't render after fully faded
  if (currentTime > fadeOutEnd + 0.5) return null;

  // Title fade-in: scale up + fade in during first 1.5s
  const titleEntryProgress = spring({
    fps,
    frame,
    config: { damping: 14, mass: 0.8 },
  });

  // Artist fade-in: slightly delayed (starts at 0.6s)
  const artistDelay = Math.floor(0.6 * fps);
  const artistEntryProgress = spring({
    fps,
    frame: Math.max(0, frame - artistDelay),
    config: { damping: 14, mass: 0.8 },
  });

  // Decorative line between title and artist (appears at 0.4s)
  const lineDelay = Math.floor(0.4 * fps);
  const lineProgress = spring({
    fps,
    frame: Math.max(0, frame - lineDelay),
    config: { damping: 16 },
  });

  // Fade out when approaching singing start
  const fadeOutOpacity = interpolate(
    currentTime,
    [fadeOutStart, fadeOutEnd],
    [1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  const overallOpacity = fadeOutOpacity;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 20,
        opacity: overallOpacity,
      }}
    >
      {/* Song Title */}
      <div
        style={{
          fontSize: '80px',
          fontWeight: '900',
          color: 'white',
          textAlign: 'center',
          opacity: titleEntryProgress,
          transform: `scale(${interpolate(titleEntryProgress, [0, 1], [0.8, 1])}) translateY(${interpolate(titleEntryProgress, [0, 1], [30, 0])}px)`,
          textShadow: '0 0 30px rgba(0, 229, 255, 0.6), 0 0 60px rgba(121, 40, 202, 0.4)',
          letterSpacing: '2px',
          padding: '0 80px',
          maxWidth: '1600px',
        }}
      >
        {title}
      </div>

      {/* Decorative line */}
      <div
        style={{
          width: `${lineProgress * 200}px`,
          height: '3px',
          background: 'linear-gradient(to right, transparent, #00e5ff, #ff007f, transparent)',
          margin: '30px 0',
          borderRadius: '2px',
          boxShadow: '0 0 15px rgba(0, 229, 255, 0.5)',
        }}
      />

      {/* Artist Name */}
      <div
        style={{
          fontSize: '40px',
          fontWeight: '400',
          color: 'rgba(255, 255, 255, 0.85)',
          textAlign: 'center',
          opacity: artistEntryProgress,
          transform: `translateY(${interpolate(artistEntryProgress, [0, 1], [20, 0])}px)`,
          textShadow: '0 0 20px rgba(255, 0, 127, 0.4)',
          letterSpacing: '6px',
          textTransform: 'uppercase',
        }}
      >
        {artist}
      </div>
    </div>
  );
};
