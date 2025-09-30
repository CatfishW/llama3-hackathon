import { useEffect, useRef } from 'react';
import { GameState } from './types';
import { clamp, randInt, bfsPath } from './utils';

function dist(a: { x: number; y: number }, b: { x: number; y: number }) {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.hypot(dx, dy);
}

export const useGameLoop = (
  stateRef: React.MutableRefObject<GameState>,
  paused: boolean,
  autoPilot: boolean,
  cols: number,
  rows: number,
  publishState: () => void,
  setGameOverTrigger: (fn: (prev: number) => number) => void,
  height: number
) => {
  const keysRef = useRef<Record<string, boolean>>({});

  useEffect(() => {
    let raf = 0;
    let acc = 0;
    const stepMs = 100; // move step interval in ms

    const loop = () => {
      raf = requestAnimationFrame(loop);
      const s = stateRef.current;
      if (!paused && !s.gameOver) {
        const now = performance.now();
        acc += now - ((loop as any).last || 0);
        (loop as any).last = now;
        while (acc >= stepMs) {
          acc -= stepMs;
          updateOnce();
        }
      }
    };

    function updateOnce() {
      const s = stateRef.current;
      const now = performance.now();
      if (!s.started) return;

      const speedActive = now < s.effects.speedBoostUntil;
      const freezeActive = now < s.effects.freezeGermsUntil;
      const slowActive = !freezeActive && now < s.effects.slowGermsUntil;
      const moves = speedActive ? 2 : 1;

      const tryMove = (dx: number, dy: number) => {
        for (let i = 0; i < moves; i++) {
          const nx = clamp(s.player.x + dx, 0, cols - 1);
          const ny = clamp(s.player.y + dy, 0, rows - 1);
          if (s.grid[ny]?.[nx] === 0) {
            s.player.x = nx;
            s.player.y = ny;
            publishState();
          }
        }
      };

      if (!autoPilot) {
        if (keysRef.current['ArrowUp'] || keysRef.current['w']) tryMove(0, -1);
        if (keysRef.current['ArrowDown'] || keysRef.current['s']) tryMove(0, 1);
        if (keysRef.current['ArrowLeft'] || keysRef.current['a']) tryMove(-1, 0);
        if (keysRef.current['ArrowRight'] || keysRef.current['d']) tryMove(1, 0);
      } else {
        const path = (s.lam.showPath && s.lam.path.length) ? s.lam.path : (bfsPath(s.grid, s.player, s.exit) || []);
        if (path.length > 1) {
          const next = path[1];
          const dx = Math.sign(next.x - s.player.x);
          const dy = Math.sign(next.y - s.player.y);
          tryMove(dx, dy);
        }
      }

      const idx = s.oxy.findIndex(o => o.x === s.player.x && o.y === s.player.y);
      if (idx >= 0) {
        s.oxy.splice(idx, 1);
        s.oxygenCollected++;
        s.fxPopups.push({ x: s.player.x, y: s.player.y, text: '+100 O₂', t0: performance.now(), ttl: 700 });
        s.emotion = 'happy';
      }

      if (!freezeActive) {
        const allowStep = slowActive ? (s.germStepFlip = !s.germStepFlip) : true;
        if (allowStep) {
          for (const g of s.germs) {
            if (Math.random() < 0.1) {
              const dirs = [{ x: 1, y: 0 }, { x: -1, y: 0 }, { x: 0, y: 1 }, { x: 0, y: -1 }];
              g.dir = dirs[randInt(4)];
            }
            const nx = clamp(g.pos.x + g.dir.x, 0, cols - 1);
            const ny = clamp(g.pos.y + g.dir.y, 0, rows - 1);
            if (s.grid[ny]?.[nx] === 0) {
              g.pos.x = nx;
              g.pos.y = ny;
            } else {
              g.dir.x *= -1;
              g.dir.y *= -1;
            }
            if (g.pos.x === s.player.x && g.pos.y === s.player.y) s.hitFlash = 1;
          }
        }
      }

      const nearGerm = s.germs.some(g => dist(g.pos, s.player) <= 2);
      if (nearGerm) s.emotion = 'scared';
      else if (s.oxygenCollected > 0 && now - s.startTime > 30000) s.emotion = 'tired';
      else if (dist(s.player, s.exit) <= 3) s.emotion = 'excited';
      else if (s.emotion !== 'happy') s.emotion = 'neutral';

      if (s.germs.some(g => g.pos.x === s.player.x && g.pos.y === s.player.y)) {
        if (!s.gameOver) {
          s.gameOver = true;
          s.win = false;
          s.endTime = performance.now();
          const elapsedSec = (s.endTime - s.startTime) / 1000;
          s.finalScore = Math.round(s.oxygenCollected * 100 - elapsedSec * 5);
          setGameOverTrigger(prev => prev + 1);
        }
      }
      if (s.player.x === s.exit.x && s.player.y === s.exit.y) {
        if (!s.gameOver) {
          s.gameOver = true;
          s.win = true;
          s.endTime = performance.now();
          const elapsedSec = (s.endTime - s.startTime) / 1000;
          s.finalScore = Math.round(s.oxygenCollected * 100 - elapsedSec * 5);
          setGameOverTrigger(prev => prev + 1);
        }
      }

      for (const [k, v] of Array.from(s.highlight.entries())) if (now > v) s.highlight.delete(k);

      if (s.hitFlash > 0) s.hitFlash = Math.max(0, s.hitFlash - 0.1);

      if (s.wallBreakParts.length) {
        s.wallBreakParts = s.wallBreakParts.filter(p => {
          p.life += stepMs;
          p.x += p.vx;
          p.y += p.vy;
          p.vy += 0.04;
          return p.life < p.ttl;
        });
      }
      if (s.fallTexts?.length) {
        s.fallTexts = s.fallTexts.filter((ft) => {
          const age = now - ft.t0;
          ft.vy += 0.05;
          ft.x += ft.vx * (stepMs / 16);
          ft.y += ft.vy * (stepMs / 16);
          return age < ft.ttl && ft.y < height + 40;
        });
      }
      if (s.cameraShake > 0) s.cameraShake *= 0.88;
    }

    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [autoPilot, cols, rows, publishState, paused, setGameOverTrigger, height, stateRef]);

  return { keysRef };
};
