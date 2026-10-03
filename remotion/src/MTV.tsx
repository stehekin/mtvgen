import React from 'react';
import { AbsoluteFill, Audio, staticFile } from 'remotion';
import { Background } from './components/Background';
import { Particles } from './components/Particles';
import { SpectrumVisualizer } from './components/SpectrumVisualizer';
import { LyricsDisplay } from './components/LyricsDisplay';
import { TitleCard } from './components/TitleCard';
import type { MTVProps } from './Root';
import './styles.css';

export const MTV: React.FC<MTVProps> = ({ songData, audioFile }) => {
  const audioSrc = staticFile(audioFile);

  // Determine when singing starts (first lyric line's start time)
  const singingStartTime =
    songData.lyrics.length > 0 ? songData.lyrics[0].start : songData.duration;

  return (
    <AbsoluteFill style={{ fontFamily: "'Inter', sans-serif" }}>
      <Background />
      <Particles />
      <SpectrumVisualizer audioSrc={audioSrc} />
      <TitleCard
        title={songData.title}
        artist={songData.artist}
        singingStartTime={singingStartTime}
      />
      <LyricsDisplay lyrics={songData.lyrics} singingStartTime={singingStartTime} />
      <Audio src={audioSrc} />
    </AbsoluteFill>
  );
};
