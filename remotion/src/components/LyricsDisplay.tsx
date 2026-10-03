import React from 'react';
import { useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';
import { LyricLine, getCurrentLineIndex, getWordProgress } from '../utils/lyrics';

export const LyricsDisplay: React.FC<{ lyrics: LyricLine[]; singingStartTime: number }> = ({ lyrics, singingStartTime }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  // Don't show lyrics until singing starts (with a slight lead-in for the fade)
  const fadeInStart = Math.max(0, singingStartTime - 0.5);
  const fadeInEnd = singingStartTime;
  const lyricsOpacity = interpolate(
    currentTime,
    [fadeInStart, fadeInEnd],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  if (currentTime < fadeInStart) return null;

  const currentLineIndex = getCurrentLineIndex(lyrics, currentTime);

  // We want to render previous, current, and next lines.
  const prevLine = currentLineIndex > 0 ? lyrics[currentLineIndex - 1] : null;
  const currentLine = currentLineIndex >= 0 ? lyrics[currentLineIndex] : null;
  const nextLine = currentLineIndex < lyrics.length - 1 ? lyrics[currentLineIndex + 1] : null;

  const renderLine = (line: LyricLine | null, isCurrent: boolean) => {
    if (!line) return <div style={{ height: '60px', margin: '20px 0' }} />;

    // Animate in when becoming current
    const startFrame = line.start * fps;
    const isVisible = frame >= startFrame - fps; // start animating 1 second before
    
    if (!isVisible && isCurrent) return <div style={{ height: '60px', margin: '20px 0' }} />;

    const translateY = isCurrent
      ? spring({ fps, frame: Math.max(0, frame - startFrame), config: { damping: 12 } }) * 10 - 10
      : 0;

    const opacity = isCurrent ? 1 : 0.3;
    const fontSize = isCurrent ? '60px' : '48px';
    const textShadow = isCurrent ? '0 0 20px rgba(0, 229, 255, 0.8), 0 0 40px rgba(255, 0, 127, 0.5)' : 'none';

    return (
      <div
        style={{
          fontSize,
          fontWeight: '900',
          color: 'white',
          opacity,
          textShadow,
          textAlign: 'center',
          transition: 'opacity 0.5s, font-size 0.5s, text-shadow 0.5s',
          margin: '20px 0',
          transform: `translateY(${translateY}px)`,
          whiteSpace: 'pre-wrap',
          display: 'flex',
          justifyContent: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        {line.words ? (
          line.words.map((word, i) => {
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
          })
        ) : (
          // Fallback if no words array is present
          <span>{line.text}</span>
        )}
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
        padding: '0 100px',
        zIndex: 10,
        opacity: lyricsOpacity,
      }}
    >
      <div style={{ transform: 'translateY(-20px)' }}>
        {renderLine(prevLine, false)}
        {renderLine(currentLine, true)}
        {renderLine(nextLine, false)}
      </div>
    </div>
  );
};
