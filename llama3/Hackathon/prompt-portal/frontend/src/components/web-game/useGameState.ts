import { useState, useRef, useCallback } from 'react';
import { GameState, Vec2, Grid } from './types';
import { generateMaze, randInt } from './utils';

export const useGameState = (cols: number, rows: number, germCount: number) => {
  const [gameOverTrigger, setGameOverTrigger] = useState(0);
  const stateRef = useRef<GameState>({
    grid: [] as Grid,
    player: { x: 1, y: 1 } as Vec2,
    exit: { x: cols - 2, y: rows - 2 } as Vec2,
    oxy: [] as Vec2[],
    germs: [] as { pos: Vec2; dir: Vec2; speed: number }[],
    oxygenCollected: 0,
    startTime: 0,
    started: false,
    gameOver: false,
    win: false,
    endTime: undefined,
    finalScore: undefined,
    lam: { hint: '', path: [] as Vec2[], breaks: 0, error: '', showPath: false },
    effects: { speedBoostUntil: 0, slowGermsUntil: 0, freezeGermsUntil: 0 },
    highlight: new Map<string, number>(),
    revealMap: false,
    fxPopups: [],
    hitFlash: 0,
    particles: [],
    germStepFlip: false,
    emotion: 'neutral',
    wallBreakParts: [],
    cameraShake: 0,
  });

  const startGame = useCallback(() => {
    setGameOverTrigger(0);
    const grid = generateMaze(cols, rows);
    grid[1][1] = 0; grid[1][2] = 0; grid[2][1] = 0;

    const floors: Vec2[] = [];
    for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) if (grid[y][x] === 0) floors.push({ x, y });

    const start = { x: 1, y: 1 };
    const exit = { x: cols - 2, y: rows - 2 };
    const oxy: Vec2[] = [];
    const avail = floors.filter(p => !(p.x === start.x && p.y === start.y) && !(p.x === exit.x && p.y === exit.y));
    const count = Math.max(10, Math.floor(avail.length * 0.1));
    for (let i = 0; i < count && avail.length; i++) {
      const idx = randInt(avail.length);
      oxy.push(avail[idx]);
      avail.splice(idx, 1);
    }

    const germs: { pos: Vec2; dir: Vec2; speed: number }[] = [];
    for (let i = 0; i < germCount && avail.length; i++) {
      const idx = randInt(avail.length);
      const pos = avail[idx];
      avail.splice(idx, 1);
      const dirs = [{ x: 1, y: 0 }, { x: -1, y: 0 }, { x: 0, y: 1 }, { x: 0, y: -1 }];
      germs.push({ pos, dir: dirs[randInt(4)], speed: 4 });
    }

    stateRef.current = {
      ...stateRef.current,
      grid,
      player: start,
      exit,
      oxy,
      germs,
      oxygenCollected: 0,
      startTime: performance.now(),
      started: true,
      gameOver: false,
      win: false,
      endTime: undefined,
      finalScore: undefined,
      lam: { hint: '', path: [], breaks: 0, error: '', showPath: false },
      effects: { speedBoostUntil: 0, slowGermsUntil: 0, freezeGermsUntil: 0 },
      highlight: new Map(),
      revealMap: false,
      fxPopups: [],
      hitFlash: 0,
      particles: Array.from({ length: 80 }, () => ({ x: Math.random() * (cols*24), y: Math.random() * (rows*24), r: 6 + Math.random() * 18, spd: 0.3 + Math.random() * 0.8, alpha: 0.06 + Math.random() * 0.12 })),
      germStepFlip: false,
      emotion: 'neutral',
      wallBreakParts: [],
      cameraShake: 0,
    };
  }, [cols, rows, germCount]);

  return { stateRef, startGame, gameOverTrigger, setGameOverTrigger };
};
