import React from 'react';
import { AbsoluteFill, Audio, staticFile } from 'remotion';
import { Background } from './components/Background';
import { MinimalTheme } from './components/MinimalTheme';
import { CosmicTheme } from './components/CosmicTheme';
import { SunsetTheme } from './components/SunsetTheme';
import { AuroraTheme } from './components/AuroraTheme';
import { MidnightTheme } from './components/MidnightTheme';

import { Particles } from './components/Particles';
import { SpectrumVisualizer } from './components/SpectrumVisualizer';
import { WaveformVisualizer } from './components/WaveformVisualizer';
import { LyricsDisplay } from './components/LyricsDisplay';
import { TitleCard } from './components/TitleCard';
import type { MTVProps } from './Root';
import './styles.css';

export const MTV: React.FC<MTVProps> = ({
  songData,
  audioFile,
  theme = 'neon',
  effects = 'all',
}) => {
  const audioSrc = staticFile(audioFile);

  const singingStartTime =
    songData.lyrics.length > 0 ? songData.lyrics[0].start : songData.duration;

  // Parse enabled effects
  const activeEffects = (effects || 'all').split(',').map((e) => e.trim().toLowerCase());
  const isEffectEnabled = (name: string) => {
    if (activeEffects.includes('none')) return false;
    if (activeEffects.includes('all')) return true;
    return activeEffects.includes(name);
  };

  const renderBackground = () => {
    switch (theme) {
      case 'minimal':
        return <MinimalTheme />;
      case 'cosmic':
        return <CosmicTheme />;
      case 'sunset':
        return <SunsetTheme />;
      case 'aurora':
        return <AuroraTheme />;
      case 'midnight':
        return <MidnightTheme />;
      case 'neon':
      default:
        return <Background />;
    }
  };

  return (
    <AbsoluteFill style={{ fontFamily: "'Inter', sans-serif" }}>
      {renderBackground()}

      {/* Dynamic Overlay Effects */}
      {isEffectEnabled('particles') && <Particles />}
      {isEffectEnabled('spectrum') && <SpectrumVisualizer audioSrc={audioSrc} />}
      {isEffectEnabled('waveform') && <WaveformVisualizer audioSrc={audioSrc} />}

      {/* Main UI Elements */}
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
