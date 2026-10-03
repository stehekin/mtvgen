import { Composition } from 'remotion';
import { MTV } from './MTV';
import { SongData } from './utils/lyrics';
import './styles.css';

export type MTVProps = {
  songData: SongData;
  audioFile: string;
  theme?: 'neon' | 'vaporwave' | 'minimal' | 'cosmic';
};

const FPS = 30;

// Calculate metadata from input props (allows dynamic duration)
const calculateMetadata = ({ props }: { props: MTVProps }) => {
  const durationInFrames = Math.ceil(props.songData.duration * FPS) + FPS; // +1s padding
  return {
    durationInFrames,
    fps: FPS,
    width: 1920,
    height: 1080,
    props,
  };
};

// Default props for Remotion Studio preview
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
      {
        text: 'Another line goes here',
        start: 6.0,
        end: 9.0,
        words: [
          { word: 'Another', start: 6.0, end: 6.8 },
          { word: 'line', start: 6.8, end: 7.5 },
          { word: 'goes', start: 7.5, end: 8.2 },
          { word: 'here', start: 8.2, end: 9.0 },
        ],
      },
      {
        text: 'The music plays on',
        start: 12.0,
        end: 15.0,
        words: [
          { word: 'The', start: 12.0, end: 12.5 },
          { word: 'music', start: 12.5, end: 13.2 },
          { word: 'plays', start: 13.2, end: 14.0 },
          { word: 'on', start: 14.0, end: 15.0 },
        ],
      },
    ],
  },
  audioFile: 'audio.mp3',
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
