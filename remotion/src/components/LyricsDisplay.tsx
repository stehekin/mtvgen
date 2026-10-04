import React from 'react';
import { useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';
import { LyricLine, getCurrentLineIndex, getWordProgress } from '../utils/lyrics';

export const LyricsDisplay: React.FC<{ lyrics: LyricLine[]; singingStartTime: number }> = ({
  lyrics,
  singingStartTime,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  // Global lyrics container fade-in when singing starts
  const fadeInStart = Math.max(0, singingStartTime - 0.6);
  const fadeInEnd = singingStartTime;
  const lyricsOpacity = interpolate(
    currentTime,
    [fadeInStart, fadeInEnd],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  if (currentTime < fadeInStart || lyrics.length === 0) return null;

  const currentLineIndex = getCurrentLineIndex(lyrics, currentTime);
  
  // Safe active line (default to line 0 during lead-in before singing)
  const activeIndex = Math.max(0, currentLineIndex);
  const activeLine = lyrics[activeIndex];
  const prevLine = activeIndex > 0 ? lyrics[activeIndex - 1] : null;
  const nextLine = activeIndex < lyrics.length - 1 ? lyrics[activeIndex + 1] : null;

  const renderLineContent = (line: LyricLine, isCurrent: boolean) => {
    if (!line.words) {
      return <span>{line.text}</span>;
    }

    return line.words.map((word, i) => {
      const progress = isCurrent ? getWordProgress(word, currentTime) : 0;
      const bgGradient = `linear-gradient(to right, #00e5ff ${progress * 100}%, white ${progress * 100}%)`;

      return (
        <span
          key={i}
          style={{
            background: isCurrent ? bgGradient : 'white',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: isCurrent ? 'transparent' : 'inherit',
            display: 'inline-block',
          }}
        >
          {word.word}
        </span>
      );
    });
  };

  const renderLineContainer = (line: LyricLine | null, role: 'prev' | 'current' | 'next') => {
    if (!line) {
      return <div style={{ height: '70px', minHeight: '70px' }} />;
    }

    const isCurrent = role === 'current';
    const startFrame = line.start * fps;
    const framesSinceStart = frame - startFrame;

    // Deterministic Remotion spring/interpolation for active line entrance
    let translateY = 0;
    let scale = 1;
    let opacity = 0.35;
    let fontSize = '46px';
    let textShadow = 'none';

    if (isCurrent) {
      // Spring animation when line starts
      const springProgress = spring({
        fps,
        frame: Math.max(0, framesSinceStart),
        config: { damping: 14, mass: 0.8 },
      });

      translateY = interpolate(springProgress, [0, 1], [15, 0]);
      scale = interpolate(springProgress, [0, 1], [0.92, 1.0]);
      opacity = interpolate(springProgress, [0, 1], [0.4, 1.0]);
      fontSize = '62px';
      textShadow = '0 0 25px rgba(0, 229, 255, 0.85), 0 0 50px rgba(255, 0, 127, 0.5)';
    } else if (role === 'next') {
      opacity = 0.3;
      fontSize = '44px';
    } else if (role === 'prev') {
      opacity = 0.25;
      fontSize = '42px';
    }

    return (
      <div
        style={{
          height: '70px',
          minHeight: '70px',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          margin: '12px 0',
        }}
      >
        <div
          style={{
            fontSize,
            fontWeight: '900',
            color: 'white',
            opacity,
            textShadow,
            textAlign: 'center',
            transform: `translateY(${translateY}px) scale(${scale})`,
            whiteSpace: 'pre-wrap',
            display: 'flex',
            justifyContent: 'center',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          {renderLineContent(line, isCurrent)}
        </div>
      </div>
    );
  };

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
        padding: '0 80px',
        zIndex: 10,
        opacity: lyricsOpacity,
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          transform: 'translateY(-10px)',
        }}
      >
        {renderLineContainer(prevLine, 'prev')}
        {renderLineContainer(activeLine, 'current')}
        {renderLineContainer(nextLine, 'next')}
      </div>
    </div>
  );
};
