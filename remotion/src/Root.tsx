import { Composition } from 'remotion';
import { MTV } from './MTV';
import { SongData } from './utils/lyrics';
import './styles.css';

export type MTVTheme = 'neon' | 'minimal' | 'cosmic' | 'sunset' | 'aurora' | 'midnight';
export type MTVEffect = 'particles' | 'spectrum' | 'waveform' | 'all' | 'none';

export type MTVProps = {
  songData: SongData;
  audioFile: string;
  theme?: MTVTheme;
  effects?: string; // Comma-separated or single effect string
};

const FPS = 30;

const calculateMetadata = ({ props }: { props: MTVProps }) => {
  const durationInFrames = Math.ceil(props.songData.duration * FPS) + FPS;
  return {
    durationInFrames,
    fps: FPS,
    width: 1920,
    height: 1080,
    props,
  };
};

const defaultProps: MTVProps = {
  songData: {
    title: 'Sample Song',
    artist: 'Sample Artist',
    duration: 30,
    lyrics: [
      {
        text: 'This is a lyric line',
        start: 2.0,
        end: 5.0,
        words: [
          { word: 'This', start: 2.0, end: 2.5 },
          { word: 'is', start: 2.5, end: 3.0 },
          { word: 'a', start: 3.0, end: 3.5 },
          { word: 'lyric', start: 3.5, end: 4.2 },
          { word: 'line', start: 4.2, end: 5.0 },
        ],
      },
    ],
  },
  audioFile: 'audio.mp3',
  theme: 'neon',
  effects: 'all',
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MTV"
        component={MTV}
        calculateMetadata={calculateMetadata}
        defaultProps={defaultProps}
      />
    </>
  );
};
