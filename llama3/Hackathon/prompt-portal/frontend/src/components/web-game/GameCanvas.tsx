import React, { useRef, useEffect } from 'react';
import { GameState, Vec2 } from './types';
import { THEME } from './theme';

interface GameCanvasProps {
  width: number;
  height: number;
  tile: number;
  gameState: GameState;
  canvasScale: number;
}

const GameCanvas: React.FC<GameCanvasProps> = ({ width, height, tile, gameState, canvasScale }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const texturesRef = useRef<{ wall: HTMLCanvasElement | null; floor: HTMLCanvasElement | null; floorAlt: HTMLCanvasElement | null }>({ wall: null, floor: null, floorAlt: null });

  function makeTileTexture(base1: string, base2: string, vein: string) {
    const c = document.createElement('canvas'); c.width = tile; c.height = tile;
    const g = c.getContext('2d')!;
    const rg = g.createRadialGradient(tile * 0.3, tile * 0.3, tile * 0.2, tile * 0.7, tile * 0.7, tile * 0.95);
    rg.addColorStop(0, base1); rg.addColorStop(1, base2);
    g.fillStyle = rg; g.fillRect(0, 0, tile, tile);
    g.strokeStyle = vein; g.globalAlpha = 0.18; g.lineWidth = 1;
    for (let i = 0; i < 3; i++) {
      g.beginPath();
      const yy = (i + 1) * tile / 4 + Math.sin(i * 1.7) * 2;
      g.moveTo(0, yy);
      for (let x = 0; x <= tile; x += 4) {
        const y = yy + Math.sin((x + i * 7) / 6) * 1.2;
        g.lineTo(x, y);
      }
      g.stroke();
    }
    g.globalAlpha = 1;
    return c;
  }

  useEffect(() => {
    const t = texturesRef.current;
    if (!t.wall) t.wall = makeTileTexture('#3b0f15', '#2b0f15', 'rgba(255,255,255,0.05)');
    if (!t.floor) t.floor = makeTileTexture('#5a1f1f', '#4a1f1f', 'rgba(255,255,255,0.06)');
    if (!t.floorAlt) t.floorAlt = makeTileTexture('#642121', '#521a1a', 'rgba(255,255,255,0.06)');
  }, []);

  function drawExitHole(ctx: CanvasRenderingContext2D, pos: Vec2, t: number) {
    const cx = pos.x * tile + tile / 2;
    const cy = pos.y * tile + tile / 2;
    const r = tile * 0.46;
    const g = ctx.createRadialGradient(cx, cy, r * 0.2, cx, cy, r);
    g.addColorStop(0, 'rgba(0,0,0,0.95)');
    g.addColorStop(0.6, 'rgba(20,10,12,0.7)');
    g.addColorStop(1, 'rgba(0,0,0,0.0)');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,0.25)';
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(cx, cy, r * 0.9, 0, Math.PI * 2); ctx.stroke();
    ctx.strokeStyle = 'rgba(255,255,255,0.15)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    const ang = (t * 0.002) % (Math.PI * 2);
    for (let a = 0; a < Math.PI * 1.6; a += Math.PI / 20) {
      const rr = r * (0.2 + a / (Math.PI * 1.6) * 0.7);
      const px = cx + Math.cos(a + ang) * rr;
      const py = cy + Math.sin(a + ang) * rr;
      if (a === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.stroke();
  }

  function drawVignette(ctx: CanvasRenderingContext2D) {
    const g = ctx.createRadialGradient(width / 2, height / 2, Math.min(width, height) * 0.2, width / 2, height / 2, Math.max(width, height) * 0.8);
    g.addColorStop(0, THEME.bgInner);
    g.addColorStop(1, THEME.bgOuter);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, width, height);
    const v = ctx.createRadialGradient(width / 2, height / 2, Math.max(width, height) * 0.55, width / 2, height / 2, Math.max(width, height) * 0.9);
    v.addColorStop(0, 'rgba(0,0,0,0)');
    v.addColorStop(1, 'rgba(0,0,0,0.6)');
    ctx.fillStyle = v;
    ctx.fillRect(0, 0, width, height);
  }

  function drawPlasma(ctx: CanvasRenderingContext2D) {
    for (const p of gameState.particles) {
      p.x -= p.spd;
      if (p.x < -p.r * 2) { p.x = width + Math.floor(Math.random() * 100); p.y = Math.floor(Math.random() * height); p.r = 6 + Math.random() * 18; p.alpha = 0.08 + Math.random() * 0.12; }
      ctx.fillStyle = `rgba(255,90,90,${p.alpha.toFixed(3)})`;
      ctx.beginPath(); ctx.ellipse(p.x, p.y, p.r, p.r * 0.6, 0, 0, Math.PI * 2); ctx.fill();
    }
  }

  function drawPlayer(ctx: CanvasRenderingContext2D, s: GameState, t: number) {
    const cx = s.player.x * tile + tile / 2;
    const cy = s.player.y * tile + tile / 2;
    const r = tile * 0.42;
    ctx.save();
    ctx.shadowColor = THEME.glow;
    ctx.shadowBlur = 16;
    ctx.fillStyle = THEME.playerRed;
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0;
    const grad = ctx.createRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 0.1, cx, cy, r);
    grad.addColorStop(0, THEME.playerBright); grad.addColorStop(1, THEME.playerRed);
    ctx.fillStyle = grad;
    ctx.beginPath(); ctx.arc(cx, cy, r * 0.85, 0, Math.PI * 2); ctx.fill();
    const e = s.emotion;
    ctx.fillStyle = '#1b0b0c';
    const eyeY = cy - r * 0.15;
    ctx.beginPath(); ctx.arc(cx - r * 0.22, eyeY, r * 0.09, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(cx + r * 0.22, eyeY, r * 0.09, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = '#1b0b0c'; ctx.lineWidth = 2;
    ctx.beginPath();
    if (e === 'happy' || e === 'excited') {
      ctx.arc(cx, cy + r * 0.1, r * 0.25, 0, Math.PI, false);
    } else if (e === 'scared') {
      ctx.arc(cx, cy + r * 0.15, r * 0.18, 0, Math.PI * 2);
    } else if (e === 'tired') {
      ctx.moveTo(cx - r * 0.2, cy + r * 0.15); ctx.lineTo(cx + r * 0.2, cy + r * 0.15);
    } else {
      ctx.arc(cx, cy + r * 0.15, r * 0.2, 0, Math.PI, true);
    }
    ctx.stroke();
    ctx.restore();
  }

  function drawOxygen(ctx: CanvasRenderingContext2D, o: { x: number; y: number }, t: number) {
    const cx = o.x * tile + tile / 2, cy = o.y * tile + tile / 2;
    const pulse = 1 + 0.15 * Math.sin(t * 0.006 + (o.x + o.y));
    const r = tile * 0.18 * pulse;
    const g = ctx.createRadialGradient(cx, cy, r * 0.2, cx, cy, r * 2.2);
    g.addColorStop(0, 'rgba(78,240,255,0.65)');
    g.addColorStop(1, 'rgba(78,240,255,0)');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(cx, cy, r * 2.2, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#8df6ff';
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = 'rgba(255,255,255,0.85)';
    ctx.beginPath(); ctx.arc(cx - r * 0.3, cy - r * 0.3, r * 0.35, 0, Math.PI * 2); ctx.fill();
  }

  function dist(a: { x: number; y: number }, b: { x: number; y: number }) { const dx = a.x - b.x, dy = a.y - b.y; return Math.hypot(dx, dy); }

  function drawGerm(ctx: CanvasRenderingContext2D, g: { pos: Vec2; dir: Vec2; speed: number }, t: number, player: Vec2) {
    const cx = g.pos.x * tile + tile / 2, cy = g.pos.y * tile + tile / 2;
    const spikes = 8;
    const baseR = tile * 0.32;
    const wobble = (Math.sin(t * 0.01 + (g.pos.x + g.pos.y)) + 1) * 0.5;
    const outerR = baseR * (1.1 + 0.12 * wobble);
    ctx.save();
    if (dist(g.pos, player) <= 3) {
      ctx.strokeStyle = 'rgba(239,68,68,0.35)';
      ctx.lineWidth = 3;
      ctx.beginPath(); ctx.arc(cx, cy, outerR * 1.6, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.beginPath();
    for (let i = 0; i < spikes; i++) {
      const a = (i / spikes) * Math.PI * 2 + t * 0.002;
      const r = i % 2 === 0 ? outerR : baseR;
      const px = cx + Math.cos(a) * r;
      const py = cy + Math.sin(a) * r;
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.closePath();
    const grad = ctx.createRadialGradient(cx, cy, baseR * 0.2, cx, cy, outerR);
    grad.addColorStop(0, THEME.germ);
    grad.addColorStop(1, THEME.germDark);
    ctx.fillStyle = grad;
    ctx.shadowColor = 'rgba(21,128,61,0.6)';
    ctx.shadowBlur = 12;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#052e16';
    ctx.beginPath(); ctx.arc(cx - baseR * 0.25, cy - baseR * 0.15, baseR * 0.12, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(cx + baseR * 0.25, cy - baseR * 0.15, baseR * 0.12, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      const s = gameState;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const shakeMag = s.cameraShake;
      if (shakeMag > 0) {
        ctx.save();
        const offX = (Math.random() * 2 - 1) * shakeMag;
        const offY = (Math.random() * 2 - 1) * shakeMag;
        ctx.translate(offX, offY);
        drawVignette(ctx);
        drawPlasma(ctx);
      } else {
        drawVignette(ctx);
        drawPlasma(ctx);
      }

      const tex = texturesRef.current;
      for (let y = 0; y < s.grid.length; y++) {
        for (let x = 0; x < s.grid[0].length; x++) {
          if (s.grid[y]?.[x] === 1) {
            if (tex.wall) ctx.drawImage(tex.wall, x * tile, y * tile);
          } else {
            if ((x + y) % 2 === 0) { if (tex.floor) ctx.drawImage(tex.floor, x * tile, y * tile); }
            else { if (tex.floorAlt) ctx.drawImage(tex.floorAlt, x * tile, y * tile); }
          }
        }
      }

      ctx.fillStyle = 'rgba(78,205,196,0.25)';
      for (const k of s.highlight.keys()) { const [x, y] = k.split(',').map(Number); ctx.fillRect(x * tile, y * tile, tile, tile); }

      if (s.lam.showPath && s.lam.path && s.lam.path.length) {
        ctx.fillStyle = 'rgba(255,255,0,0.22)';
        for (const p of s.lam.path) ctx.fillRect(p.x * tile, p.y * tile, tile, tile);
        ctx.strokeStyle = 'rgba(255,255,0,0.9)'; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(s.lam.path[0].x * tile + tile / 2, s.lam.path[0].y * tile + tile / 2);
        for (let i = 1; i < s.lam.path.length; i++) ctx.lineTo(s.lam.path[i].x * tile + tile / 2, s.lam.path[i].y * tile + tile / 2);
        ctx.stroke();
      }

      const t = performance.now();
      for (const o of s.oxy) drawOxygen(ctx, o, t);
      drawExitHole(ctx, s.exit, t);
      for (const g of s.germs) drawGerm(ctx, g as any, t, s.player);
      drawPlayer(ctx, s, t);

      if (s.wallBreakParts.length) {
        for (const p of s.wallBreakParts) {
          const lifeRatio = p.life / p.ttl;
          const alpha = 1 - lifeRatio;
          const pr = 3 + 3 * (1 - lifeRatio);
          ctx.globalAlpha = alpha;
          ctx.fillStyle = '#5a1f1f';
          ctx.beginPath(); ctx.arc(p.x, p.y, pr, 0, Math.PI * 2); ctx.fill();
          ctx.globalAlpha = 1;
        }
      }

      const now = performance.now();
      s.fxPopups = s.fxPopups.filter(p => now - p.t0 < p.ttl);
      for (const p of s.fxPopups) {
        const ratio = (now - p.t0) / p.ttl;
        const alpha = 1 - ratio;
        const yOff = -10 - ratio * 20;
        ctx.globalAlpha = alpha; ctx.fillStyle = '#ffffff'; ctx.font = 'bold 14px Inter';
        ctx.fillText(p.text, p.x * tile + tile / 2 - 28, p.y * tile + yOff);
        ctx.globalAlpha = 1;
      }

      const fallTexts = s.fallTexts || [];
      for (const ft of fallTexts) {
        const age = now - ft.t0;
        const ratio = age / ft.ttl;
        const alpha = 1 - ratio;
        ctx.globalAlpha = alpha;
        ctx.fillStyle = '#ffd1d1';
        ctx.font = 'bold 16px Inter';
        ctx.fillText(ft.text, ft.x - 50, ft.y);
        ctx.globalAlpha = 1;
      }

      if (shakeMag > 0) ctx.restore();
    };

    let rafId = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(rafId);
  }, [gameState, width, height, tile]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{ width: width * canvasScale, height: height * canvasScale, display: 'block', background: '#0b0507' }}
    />
  );
};

export default GameCanvas;
