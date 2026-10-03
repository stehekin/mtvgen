import React from 'react';
import { AbsoluteFill, Audio, staticFile } from 'remotion';
import { Background } from './components/Background';
import { VaporwaveTheme } from './components/VaporwaveTheme';
import { MinimalTheme } from './components/MinimalTheme';
import { CosmicTheme } from './components/CosmicTheme';
import { Particles } from './components/Particles';
import { SpectrumVisualizer } from './components/SpectrumVisualizer';
import { LyricsDisplay } from './components/LyricsDisplay';
import { TitleCard } from './components/TitleCard';
import type { MTVProps } from './Root';
import './styles.css';

export const MTV: React.FC<MTVProps> = ({ songData, audioFile, theme = 'neon' }) => {
  const audioSrc = staticFile(audioFile);

  const singingStartTime =
    songData.lyrics.length > 0 ? songData.lyrics[0].start : songData.duration;

  const renderBackground = () => {
    switch (theme) {
      case 'vaporwave':
        return <VaporwaveTheme />;
      case 'minimal':
        return <MinimalTheme />;
      case 'cosmic':
        return <CosmicTheme />;
      case 'neon':
      default:
        return (
          <>
            <Background />
            <Particles />
          </>
        );
    }
  };

  return (
    <AbsoluteFill style={{ fontFamily: "'Inter', sans-serif" }}>
      {renderBackground()}
      {theme !== 'minimal' && <SpectrumVisualizer audioSrc={audioSrc} />}
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
