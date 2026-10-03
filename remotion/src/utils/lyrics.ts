export interface WordToken {
  word: string;
  start: number;
  end: number;
}

export interface LyricLine {
  text: string;
  start: number;
  end: number;
  words?: WordToken[];
}

export interface SongData {
  title: string;
  artist: string;
  duration: number;
  lyrics: LyricLine[];
}

export const timeToFrame = (timeInSeconds: number, fps: number) => {
  return Math.floor(timeInSeconds * fps);
};

export const getCurrentLineIndex = (lyrics: LyricLine[], currentTime: number) => {
  // Find the last line that started before or exactly at currentTime
  let currentIndex = -1;
  for (let i = 0; i < lyrics.length; i++) {
    if (currentTime >= lyrics[i].start) {
      currentIndex = i;
    } else {
      break;
    }
  }
  return currentIndex;
};

export const getWordProgress = (word: WordToken, currentTime: number) => {
  if (currentTime < word.start) return 0;
  if (currentTime > word.end) return 1;
  const duration = word.end - word.start;
  if (duration === 0) return 1;
  return (currentTime - word.start) / duration;
};
