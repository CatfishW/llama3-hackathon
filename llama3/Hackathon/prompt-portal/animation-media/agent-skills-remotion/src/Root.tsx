import React from 'react';
import { Composition } from 'remotion';
import { AgentSkillsComposition } from './Composition';
import { SEGMENTS } from './Segments';

export const RemotionRoot: React.FC = () => {
  const totalDuration = Math.ceil(SEGMENTS.reduce((acc, s) => acc + s.duration, 0) * 30) + 150; // Add some buffer

  return (
    <>
      <Composition
        id="AgentSkills"
        component={AgentSkillsComposition}
        durationInFrames={totalDuration}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
