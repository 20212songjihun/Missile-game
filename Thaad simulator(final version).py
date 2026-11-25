<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" />
  <title>THAAD BATTERY COMMAND // MULTI-LAYER BMD INTERCEPT SIMULATOR</title>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
      -webkit-user-select: none;
      -webkit-touch-callout: none;
      touch-action: none;
    }
    html, body {
      width: 100%;
      height: 100%;
      background-color: #05070c;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: Menlo, Consolas, "DejaVu Sans Mono", "Lucida Console", monospace;
    }
    #sim-wrapper {
      width: 100vw;
      height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left);
    }
    canvas {
      display: block;
      max-width: 100%;
      max-height: 100%;
      aspect-ratio: 1440 / 900;
      box-shadow: 0 0 36px rgba(0, 230, 255, 0.14);
      background: #000;
    }
  </style>
</head>
<body>
<div id="sim-wrapper">
  <canvas id="gameCanvas" width="1440" height="900"></canvas>
</div>

<script>
(() => {
  "use strict";

  // ============================================================================
  // 1. SYSTEM CONFIGURATION, POLYFILLS & MATH UTILITIES
  // ============================================================================
  const SCREEN_WIDTH = 1440;
  const SCREEN_HEIGHT = 900;
  const BATTLE_HEIGHT = 645;
  const CONSOLE_TOP = BATTLE_HEIGHT;
  const CONSOLE_HEIGHT = SCREEN_HEIGHT - BATTLE_HEIGHT;
  const GROUND_Y = BATTLE_HEIGHT - 30;
  const FPS = 60;
  const FRAME_MS = 1000 / FPS;

  const canvas = document.getElementById("gameCanvas");
  const ctx = canvas.getContext("2d");

  // iPadOS Safari 하위 버전 호환용 roundRect 폴리필
  if (typeof CanvasRenderingContext2D !== "undefined" && !CanvasRenderingContext2D.prototype.roundRect) {
    CanvasRenderingContext2D.prototype.roundRect = function (x, y, w, h, radii) {
      let r = [0, 0, 0, 0];
      if (typeof radii === "number") {
        r = [radii, radii, radii, radii];
      } else if (Array.isArray(radii)) {
        if (radii.length === 1) r = [radii[0], radii[0], radii[0], radii[0]];
        else if (radii.length === 2) r = [radii[0], radii[1], radii[0], radii[1]];
        else if (radii.length >= 4) r = [radii[0], radii[1], radii[2], radii[3]];
      }
      this.moveTo(x + r[0], y);
      this.lineTo(x + w - r[1], y);
      this.quadraticCurveTo(x + w, y, x + w, y + r[1]);
      this.lineTo(x + w, y + h - r[2]);
      this.quadraticCurveTo(x + w, y + h, x + w - r[2], y + h);
      this.lineTo(x + r[3], y + h);
      this.quadraticCurveTo(x, y + h, x, y + h - r[3]);
      this.lineTo(x, y + r[0]);
      this.quadraticCurveTo(x, y, x + r[0], y);
      this.closePath();
      return this;
    };
  }

  const FONT_XS = 'bold 11px Menlo, Consolas, "DejaVu Sans Mono", "Lucida Console", monospace';
  const FONT_SM = 'bold 13px Menlo, Consolas, "DejaVu Sans Mono", "Lucida Console", monospace';
  const FONT_MD = 'bold 15px Menlo, Consolas, "DejaVu Sans Mono", "Lucida Console", monospace';
  const FONT_LG = 'bold 22px Menlo, Consolas, "DejaVu Sans Mono", "Lucida Console", monospace';
  const FONT_XL = 'bold 40px Menlo, Consolas, "DejaVu Sans Mono", "Lucida Console", monospace';

  const ThreatType = Object.freeze({
    SRBM: "SRBM", // 단거리 탄도미사일
    MRBM: "MRBM", // 준중거리 고각 탄도미사일
    MIRV: "MIRV", // 다탄두 분리형 탄도미사일
    HGV: "HGV",   // 극초음속 활공체
    MARV: "MARV", // 종말 회피 기동 탄두
    DECOY: "DECOY" // 대기권 감속 식별 기만탄
  });

  const Palette = Object.freeze({
    SKY_TOP: [6, 10, 20],
    SKY_MID: [15, 24, 42],
    SKY_LOW: [34, 46, 66],
    HORIZON_DUST: [58, 64, 74],

    DESERT_DARK: [28, 29, 32],
    DESERT_MID: [42, 41, 40],
    OLIVE_DRAB: [68, 76, 64],
    OLIVE_LIGHT: [92, 102, 86],
    STEEL_DARK: [36, 42, 50],
    STEEL_LIGHT: [115, 128, 142],

    RADAR_GREEN: [45, 255, 140],
    CYAN: [0, 230, 255],
    AMBER: [255, 185, 40],
    ORANGE_PLUME: [255, 130, 35],
    RED_ALERT: [255, 55, 68],
    MAGENTA: [215, 80, 255],
    WHITE: [245, 248, 252],

    PANEL_BG: [20, 24, 30],
    PANEL_DARK: [12, 15, 20],
    PANEL_BORDER: [58, 70, 86],
    TEXT_DIM: [130, 145, 165]
  });

  function clamp(val, low, high) {
    return Math.max(low, Math.min(high, val));
  }

  function clampColor(c) {
    return [
      Math.floor(Math.max(0, Math.min(255, c[0]))),
      Math.floor(Math.max(0, Math.min(255, c[1]))),
      Math.floor(Math.max(0, Math.min(255, c[2])))
    ];
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function lerpColor(c1, c2, t) {
    const k = clamp(t, 0.0, 1.0);
    return [
      Math.floor(c1[0] + (c2[0] - c1[0]) * k),
      Math.floor(c1[1] + (c2[1] - c1[1]) * k),
      Math.floor(c1[2] + (c2[2] - c1[2]) * k)
    ];
  }

  function rgb(c) {
    return `rgb(${c[0]},${c[1]},${c[2]})`;
  }

  function rgba(c, a) {
    return `rgba(${c[0]},${c[1]},${c[2]},${a})`;
  }

  function randRange(min, max) {
    return min + Math.random() * (max - min);
  }

  function randInt(min, max) {
    return Math.floor(min + Math.random() * (max - min + 1));
  }

  function randChoice(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
  }

  class Vec2 {
    constructor(x = 0, y = 0) {
      this.x = x;
      this.y = y;
    }
    clone() {
      return new Vec2(this.x, this.y);
    }
    add(v) {
      return new Vec2(this.x + v.x, this.y + v.y);
    }
    sub(v) {
      return new Vec2(this.x - v.x, this.y - v.y);
    }
    mul(s) {
      return new Vec2(this.x * s, this.y * s);
    }
    lengthSq() {
      return this.x * this.x + this.y * this.y;
    }
    length() {
      return Math.hypot(this.x, this.y);
    }
    normalize() {
      const magSq = this.lengthSq();
      if (magSq < 1e-9) return new Vec2(0.0, -1.0);
      const inv = 1.0 / Math.sqrt(magSq);
      return new Vec2(this.x * inv, this.y * inv);
    }
    distanceTo(v) {
      return Math.hypot(this.x - v.x, this.y - v.y);
    }
    rotateRad(rad) {
      const c = Math.cos(rad);
      const s = Math.sin(rad);
      return new Vec2(this.x * c - this.y * s, this.x * s + this.y * c);
    }
  }

  class GlowCache {
    static _cache = new Map();

    static draw(targetCtx, color, pos, radius, alpha = 95) {
      const r = Math.floor(radius);
      if (r <= 2) return;
      const qr = Math.max(4, Math.floor(r / 4) * 4);
      const ck0 = Math.floor(color[0] / 8) * 8;
      const ck1 = Math.floor(color[1] / 8) * 8;
      const ck2 = Math.floor(color[2] / 8) * 8;
      const ak = Math.floor(alpha / 10) * 10;
      const key = `${ck0},${ck1},${ck2}|${qr}|${ak}`;

      let surf = this._cache.get(key);
      if (!surf) {
        if (this._cache.size > 400) this._cache.clear();
        surf = document.createElement("canvas");
        surf.width = qr * 2;
        surf.height = qr * 2;
        const sctx = surf.getContext("2d");
        for (let i = 4; i >= 1; i--) {
          const frac = i / 4.0;
          const cr = Math.max(1, Math.floor(qr * frac));
          const ca = clamp(Math.floor(ak * (1.0 - frac * 0.62) * 0.5), 0, 255) / 255;
          sctx.fillStyle = `rgba(${ck0},${ck1},${ck2},${ca.toFixed(3)})`;
          sctx.beginPath();
          sctx.arc(qr, qr, cr, 0, Math.PI * 2);
          sctx.fill();
        }
        this._cache.set(key, surf);
      }

      targetCtx.save();
      targetCtx.globalCompositeOperation = "lighter";
      targetCtx.drawImage(surf, Math.floor(pos.x - qr), Math.floor(pos.y - qr));
      targetCtx.restore();
    }
  }

  // ============================================================================
  // 2. PROCEDURAL MILITARY DSP AUDIO SYNTHESIZER (WEB AUDIO API)
  // ============================================================================
  class THAADAudio {
    constructor() {
      this.enabled = true;
      this.muted = false;
      this.ctx = null;
      this.buffers = {};
      this.initialized = false;
    }

    unlock() {
      if (!this.enabled) return;
      try {
        if (!this.ctx) {
          const AudioCtx = window.AudioContext || window.webkitAudioContext;
          if (!AudioCtx) {
            this.enabled = false;
            return;
          }
          this.ctx = new AudioCtx();
          this._buildAllBuffers();
          this.initialized = true;
        }
        if (this.ctx && this.ctx.state === "suspended") {
          this.ctx.resume();
        }
      } catch (e) {
        this.enabled = false;
      }
    }

    _buildAllBuffers() {
      this.buffers.click = this._makeClick();
      this.buffers.power_link = this._makeChirp(160, 560, 0.22, 0.24);
      this.buffers.hydraulic_hum = this._makeHydraulic();
      this.buffers.batt_charge = this._makeChirp(220, 420, 0.06, 0.14);
      this.buffers.radar_lock = this._makeChirp(1420, 1880, 0.09, 0.22);
      this.buffers.cap_blow = this._makeNoise(0.16, 0.34, 0.32, 2.6);
      this.buffers.thaad_roar = this._makeRoar();
      this.buffers.lsam_roar = this._makeChirp(110, 340, 0.38, 0.24);
      this.buffers.pac3_roar = this._makeNoise(0.45, 0.32, 0.26, 1.9);
      this.buffers.stage_sep = this._makeNoise(0.18, 0.26, 0.35, 2.5);
      this.buffers.dacs_puff = this._makeNoise(0.05, 0.14, 0.55, 3.0);
      this.buffers.kinetic_hit = this._makeKineticBoom();
      this.buffers.ground_impact = this._makeNoise(0.95, 0.48, 0.06, 1.3);
      this.buffers.alarm = this._makeChirp(760, 520, 0.18, 0.22);
    }

    _makeClick() {
      const sr = 22050;
      const n = Math.floor(sr * 0.025);
      const buf = this.ctx.createBuffer(1, n, sr);
      const data = buf.getChannelData(0);
      for (let i = 0; i < n; i++) {
        const env = Math.pow(1.0 - i / n, 2.4);
        data[i] = 0.28 * env * (Math.floor(i / 4) % 2 === 0 ? 1.0 : -1.0);
      }
      return buf;
    }

    _makeHydraulic() {
      const sr = 22050;
      const n = Math.floor(sr * 0.12);
      const buf = this.ctx.createBuffer(1, n, sr);
      const data = buf.getChannelData(0);
      for (let i = 0; i < n; i++) {
        const t = i / sr;
        const env = Math.sin(Math.PI * (i / n));
        const wave = Math.sin(2 * Math.PI * 135 * t) * 0.6 + Math.sin(2 * Math.PI * 270 * t) * 0.4;
        data[i] = 0.12 * env * wave;
      }
      return buf;
    }

    _makeChirp(f0, f1, dur, vol) {
      const sr = 22050;
      const n = Math.floor(sr * dur);
      const buf = this.ctx.createBuffer(1, n, sr);
      const data = buf.getChannelData(0);
      let ph = 0.0;
      for (let i = 0; i < n; i++) {
        const frac = i / n;
        const env = Math.sin(Math.PI * frac);
        const f = f0 + (f1 - f0) * frac;
        ph += (2 * Math.PI * f) / sr;
        data[i] = vol * env * Math.sin(ph);
      }
      return buf;
    }

    _makeNoise(dur, vol, cutoff = 0.2, decay = 1.6) {
      const sr = 22050;
      const n = Math.floor(sr * dur);
      const buf = this.ctx.createBuffer(1, n, sr);
      const data = buf.getChannelData(0);
      let lp = 0.0;
      for (let i = 0; i < n; i++) {
        const frac = i / n;
        const env = Math.pow(1.0 - frac, decay);
        const w = randRange(-1.0, 1.0);
        lp += cutoff * (w - lp);
        data[i] = clamp(vol * 2.8 * env * lp, -1.0, 1.0);
      }
      return buf;
    }

    _makeRoar() {
      const sr = 22050;
      const n = Math.floor(sr * 1.15);
      const buf = this.ctx.createBuffer(1, n, sr);
      const data = buf.getChannelData(0);
      let lp1 = 0.0;
      let lp2 = 0.0;
      for (let i = 0; i < n; i++) {
        const frac = i / n;
        const attack = Math.min(1.0, frac * 18.0);
        const env = attack * Math.pow(1.0 - frac, 1.05);
        const w = randRange(-1.0, 1.0);
        lp1 += 0.24 * (w - lp1);
        lp2 += 0.12 * (lp1 - lp2);
        const sub = 0.45 * Math.sin(2 * Math.PI * (52.0 + 28.0 * (1.0 - frac)) * (i / sr));
        const crackle = 0.25 * w * Math.max(0.0, 1.0 - frac * 2.5);
        data[i] = clamp(0.42 * env * (lp2 * 2.8 + sub + crackle), -1.0, 1.0);
      }
      return buf;
    }

    _makeKineticBoom() {
      const sr = 22050;
      const n = Math.floor(sr * 0.65);
      const buf = this.ctx.createBuffer(1, n, sr);
      const data = buf.getChannelData(0);
      let lp = 0.0;
      for (let i = 0; i < n; i++) {
        const frac = i / n;
        const env = Math.pow(1.0 - frac, 1.8);
        const w = randRange(-1.0, 1.0);
        lp += 0.14 * (w - lp);
        const snap = Math.sin(2 * Math.PI * 1200 * (i / sr)) * Math.pow(1.0 - frac, 12.0);
        data[i] = clamp(0.44 * (env * lp * 2.6 + snap * 0.8), -1.0, 1.0);
      }
      return buf;
    }

    play(name) {
      if (!this.enabled || this.muted) return;
      if (!this.initialized) this.unlock();
      if (!this.ctx || !this.buffers[name]) return;
      try {
        const src = this.ctx.createBufferSource();
        src.buffer = this.buffers[name];
        src.connect(this.ctx.destination);
        src.start(0);
      } catch (e) {
        // iPad 오디오 정책 예외 무시
      }
    }
  }

  const SFX = new THAADAudio();

  // ============================================================================
  // 3. PARTICLES, GROUND-HUGGING EXHAUST PLUMES & DYNAMIC LIGHTS
  // ============================================================================
  class ExhaustSmokeCloud {
    constructor(pos, vel, radius = 6.0, life = 75, color = [225, 228, 232], growth = 0.28, groundInteract = true) {
      this.pos = pos.clone();
      this.vel = vel.clone();
      this.radius = radius;
      this.life = life;
      this.maxLife = life;
      this.color = color;
      this.growth = growth;
      this.groundInteract = groundInteract;
    }

    update(windX) {
      this.vel = this.vel.mul(0.93);
      this.vel.x += windX * 0.02;
      this.pos = this.pos.add(this.vel);
      this.radius += this.growth;
      this.life -= 1;

      if (this.groundInteract && this.pos.y >= GROUND_Y - 4) {
        this.pos.y = GROUND_Y - 4;
        const impactEnergy = Math.abs(this.vel.y);
        this.vel.y = -impactEnergy * 0.12;
        const spreadDir = this.vel.x <= 0 ? -1.0 : 1.0;
        this.vel.x += spreadDir * impactEnergy * 0.45;
        this.growth *= 1.03;
      }
    }

    draw(targetCtx, lights) {
      if (this.life <= 0) return;
      const ratio = this.life / this.maxLife;
      const alpha = (145 * ratio * ratio) / 255;
      const r = Math.floor(this.radius);
      if (r < 2 || alpha <= 0.01) return;

      let cr = this.color[0];
      let cg = this.color[1];
      let cb = this.color[2];
      for (let i = 0; i < lights.length; i++) {
        const lt = lights[i];
        const d = Math.hypot(lt.pos.x - this.pos.x, lt.pos.y - this.pos.y);
        if (d < lt.radius) {
          const inf = Math.pow(1.0 - d / lt.radius, 1.5) * lt.strength * 0.75;
          cr = Math.min(255, cr + lt.color[0] * inf);
          cg = Math.min(255, cg + lt.color[1] * inf);
          cb = Math.min(255, cb + lt.color[2] * inf);
        }
      }

      targetCtx.fillStyle = `rgba(${Math.floor(cr)},${Math.floor(cg)},${Math.floor(cb)},${alpha.toFixed(3)})`;
      targetCtx.beginPath();
      targetCtx.arc(Math.floor(this.pos.x), Math.floor(this.pos.y), r, 0, Math.PI * 2);
      targetCtx.fill();
    }
  }

  class PlumeFireParticle {
    constructor(pos, vel, radius = 7.0, life = 16) {
      this.pos = pos.clone();
      this.vel = vel.clone();
      this.radius = radius;
      this.life = life;
      this.maxLife = life;
    }

    update() {
      this.vel = this.vel.mul(0.9);
      this.pos = this.pos.add(this.vel);
      this.radius *= 0.94;
      this.life -= 1;
      if (this.pos.y >= GROUND_Y - 2) {
        this.pos.y = GROUND_Y - 2;
        this.vel.y = 0;
        this.vel.x *= 1.15;
      }
    }

    draw(targetCtx) {
      if (this.life <= 0) return;
      const ratio = this.life / this.maxLife;
      const col = lerpColor(Palette.RED_ALERT, Palette.WHITE, ratio * ratio);
      GlowCache.draw(targetCtx, col, this.pos, this.radius * 2.2, Math.floor(180 * ratio));
      targetCtx.fillStyle = rgb(col);
      targetCtx.beginPath();
      targetCtx.arc(Math.floor(this.pos.x), Math.floor(this.pos.y), Math.max(1, Math.floor(this.radius)), 0, Math.PI * 2);
      targetCtx.fill();
    }
  }

  class SparkStreak {
    constructor(pos, vel, color, life = 28, gravity = 0.09, width = 2) {
      this.pos = pos.clone();
      this.vel = vel.clone();
      this.color = color;
      this.life = life;
      this.maxLife = life;
      this.gravity = gravity;
      this.width = width;
    }

    update() {
      this.vel = this.vel.mul(0.965);
      this.vel.y += this.gravity;
      this.pos = this.pos.add(this.vel);
      this.life -= 1;
    }

    draw(targetCtx) {
      if (this.life <= 0) return;
      const ratio = this.life / this.maxLife;
      const c = clampColor([this.color[0] * ratio, this.color[1] * ratio, this.color[2] * ratio]);
      const tail = this.pos.sub(this.vel.mul(1.7));
      targetCtx.strokeStyle = rgb(c);
      targetCtx.lineWidth = this.width;
      targetCtx.beginPath();
      targetCtx.moveTo(this.pos.x, this.pos.y);
      targetCtx.lineTo(tail.x, tail.y);
      targetCtx.stroke();
    }
  }

  class TumblingDebris {
    constructor(pos, vel, length = 10, width = 4, color = [150, 160, 170], life = 140, smokeTrail = false) {
      this.pos = pos.clone();
      this.vel = vel.clone();
      this.angle = randRange(0, Math.PI * 2);
      this.angVel = randRange(-0.25, 0.25);
      this.length = length;
      this.width = width;
      this.color = color;
      this.life = life;
      this.smokeTrail = smokeTrail;
    }

    update(smokeList) {
      this.vel.x *= 0.992;
      this.vel.y += 0.14;
      this.pos = this.pos.add(this.vel);
      this.angle += this.angVel;
      this.life -= 1;

      if (this.smokeTrail && this.life > 35 && Math.random() < 0.45) {
        smokeList.push(new ExhaustSmokeCloud(
          this.pos,
          new Vec2(randRange(-0.3, 0.3), randRange(-0.3, 0.3)),
          2.5, 24, [165, 170, 178], 0.09, false
        ));
      }

      if (this.pos.y >= GROUND_Y) {
        this.pos.y = GROUND_Y;
        this.vel.y *= -0.35;
        this.vel.x *= 0.65;
        this.angVel *= 0.4;
        this.smokeTrail = false;
      }
    }

    draw(targetCtx) {
      if (this.life <= 0) return;
      const fade = Math.min(1.0, this.life / 25.0);
      const c = clampColor([this.color[0] * fade, this.color[1] * fade, this.color[2] * fade]);
      const fwd = new Vec2(Math.cos(this.angle), Math.sin(this.angle)).mul(this.length * 0.5);
      let right = new Vec2(-fwd.y, fwd.x);
      if (right.lengthSq() > 0) right = right.normalize().mul(this.width * 0.5);

      const p0 = this.pos.add(fwd).add(right);
      const p1 = this.pos.add(fwd).sub(right);
      const p2 = this.pos.sub(fwd).sub(right);
      const p3 = this.pos.sub(fwd).add(right);

      targetCtx.fillStyle = rgb(c);
      targetCtx.beginPath();
      targetCtx.moveTo(p0.x, p0.y);
      targetCtx.lineTo(p1.x, p1.y);
      targetCtx.lineTo(p2.x, p2.y);
      targetCtx.lineTo(p3.x, p3.y);
      targetCtx.closePath();
      targetCtx.fill();
    }
  }

  class ShockwaveRing {
    constructor(pos, maxR, color = Palette.CYAN, duration = 26, width = 3) {
      this.pos = pos.clone();
      this.maxR = maxR;
      this.curR = 4.0;
      this.color = color;
      this.life = duration;
      this.maxLife = duration;
      this.width = width;
    }

    update() {
      this.life -= 1;
      const t = 1.0 - this.life / this.maxLife;
      this.curR = 4.0 + (this.maxR - 4.0) * (1.0 - Math.pow(1.0 - t, 3.0));
    }

    draw(targetCtx) {
      if (this.life <= 0) return;
      const ratio = this.life / this.maxLife;
      const r = Math.floor(this.curR);
      if (r <= 2) return;
      GlowCache.draw(targetCtx, this.color, this.pos, r * 1.4, Math.floor(120 * ratio));

      targetCtx.save();
      targetCtx.globalCompositeOperation = "lighter";
      targetCtx.strokeStyle = rgba(this.color, (240 * ratio) / 255);
      targetCtx.lineWidth = this.width;
      targetCtx.beginPath();
      targetCtx.arc(this.pos.x, this.pos.y, r, 0, Math.PI * 2);
      targetCtx.stroke();

      if (r > 10) {
        targetCtx.fillStyle = rgba(Palette.WHITE, (170 * ratio * ratio) / 255);
        targetCtx.beginPath();
        targetCtx.arc(this.pos.x, this.pos.y, Math.floor(r * 0.55), 0, Math.PI * 2);
        targetCtx.fill();
      }
      targetCtx.restore();
    }
  }

  class DynamicLight {
    constructor(pos, color, intensity = 1.0, radius = 280, life = 24) {
      this.pos = pos.clone();
      this.color = color;
      this.intensity = intensity;
      this.radius = radius;
      this.life = life;
      this.maxLife = life;
    }

    update() {
      this.life -= 1;
    }

    get strength() {
      if (this.life <= 0) return 0.0;
      return this.intensity * Math.pow(this.life / this.maxLife, 1.4);
    }
  }

  class FloatingCallout {
    constructor(pos, text, color = Palette.WHITE, life = 65) {
      this.pos = pos.clone();
      this.text = text;
      this.color = color;
      this.life = life;
      this.maxLife = life;
    }

    update() {
      this.pos.y -= 0.65;
      this.life -= 1;
    }

    draw(targetCtx) {
      if (this.life <= 0) return;
      const alpha = Math.min(1.0, (this.life / this.maxLife) * 1.5);
      targetCtx.save();
      targetCtx.globalAlpha = alpha;
      targetCtx.font = FONT_SM;
      targetCtx.textAlign = "center";
      targetCtx.textBaseline = "top";
      targetCtx.fillStyle = rgb(this.color);
      targetCtx.fillText(this.text, Math.floor(this.pos.x), Math.floor(this.pos.y));
      targetCtx.restore();
    }
  }

  // ============================================================================
  // 4. BATTERY POWER TRUCK, MULTI-LAYER LAUNCHERS & DUAL AN/TPY-2 RADARS
  // ============================================================================
  class BatterySupplyTruck {
    /** 사드/방공포대 전용 이동식 전력공급차량 (EPP-01: Electrical Power Plant) */
    constructor(xPos) {
      this.x = xPos;
      this.y = GROUND_Y;
      this.connected = false;
      this.cableProgress = 0.0;
      this.pulsePhase = 0.0;
    }

    toggleConnection() {
      this.connected = !this.connected;
      return this.connected;
    }

    update() {
      this.pulsePhase += 0.14;
      if (this.connected) {
        this.cableProgress = Math.min(1.0, this.cableProgress + 0.075);
      } else {
        this.cableProgress = Math.max(0.0, this.cableProgress - 0.09);
      }
    }

    getPowerBusOrigin() {
      return new Vec2(this.x + 38, this.y - 14);
    }

    drawPowerCables(targetCtx, targetPorts) {
      if (this.cableProgress <= 0.01) return;
      const origin = this.getPowerBusOrigin();

      targetCtx.save();
      for (let i = 0; i < targetPorts.length; i++) {
        const port = targetPorts[i];
        const curEndX = lerp(origin.x, port.x, this.cableProgress);
        const curEndY = lerp(origin.y, port.y, this.cableProgress);

        targetCtx.strokeStyle = "rgb(20,26,34)";
        targetCtx.lineWidth = 4;
        targetCtx.beginPath();
        targetCtx.moveTo(origin.x, origin.y);
        targetCtx.lineTo(origin.x + 8, GROUND_Y - 2);
        targetCtx.lineTo(curEndX - 6, GROUND_Y - 2);
        targetCtx.lineTo(curEndX, curEndY);
        targetCtx.stroke();

        const pulseAlpha = this.connected ? (0.55 + 0.35 * Math.sin(this.pulsePhase - i * 0.7)) : 0.25;
        targetCtx.strokeStyle = `rgba(0,230,255,${pulseAlpha.toFixed(3)})`;
        targetCtx.lineWidth = 1.6;
        targetCtx.beginPath();
        targetCtx.moveTo(origin.x, origin.y);
        targetCtx.lineTo(origin.x + 8, GROUND_Y - 2);
        targetCtx.lineTo(curEndX - 6, GROUND_Y - 2);
        targetCtx.lineTo(curEndX, curEndY);
        targetCtx.stroke();

        if (this.cableProgress >= 0.98) {
          targetCtx.fillStyle = rgb(Palette.CYAN);
          targetCtx.beginPath();
          targetCtx.arc(port.x, port.y, 3, 0, Math.PI * 2);
          targetCtx.fill();
        }
      }
      targetCtx.restore();
    }

    draw(targetCtx) {
      const x = Math.floor(this.x);
      const y = Math.floor(this.y);

      targetCtx.fillStyle = rgb(Palette.OLIVE_DRAB);
      targetCtx.fillRect(x - 42, y - 20, 84, 9);
      targetCtx.strokeStyle = rgb(Palette.STEEL_DARK);
      targetCtx.lineWidth = 1;
      targetCtx.strokeRect(x - 42, y - 20, 84, 9);

      targetCtx.fillStyle = rgb(Palette.OLIVE_LIGHT);
      targetCtx.fillRect(x - 40, y - 40, 56, 20);
      targetCtx.strokeStyle = rgb(this.connected ? Palette.CYAN : Palette.STEEL_DARK);
      targetCtx.lineWidth = 1.5;
      targetCtx.strokeRect(x - 40, y - 40, 56, 20);

      for (let gx = x - 34; gx <= x - 6; gx += 14) {
        targetCtx.fillStyle = rgb(Palette.STEEL_DARK);
        targetCtx.fillRect(gx, y - 36, 9, 12);
      }
      const ledCol = this.connected ? Palette.CYAN : Palette.RED_ALERT;
      targetCtx.fillStyle = rgb(ledCol);
      targetCtx.beginPath();
      targetCtx.arc(x + 9, y - 34, 3, 0, Math.PI * 2);
      targetCtx.fill();
      if (this.connected) {
        GlowCache.draw(targetCtx, Palette.CYAN, new Vec2(x + 9, y - 34), 16, 150);
      }

      targetCtx.fillStyle = rgb(Palette.OLIVE_LIGHT);
      targetCtx.beginPath();
      targetCtx.moveTo(x + 18, y - 20);
      targetCtx.lineTo(x + 42, y - 20);
      targetCtx.lineTo(x + 44, y - 30);
      targetCtx.lineTo(x + 33, y - 37);
      targetCtx.lineTo(x + 18, y - 37);
      targetCtx.closePath();
      targetCtx.fill();
      targetCtx.strokeStyle = rgb(Palette.STEEL_DARK);
      targetCtx.lineWidth = 1;
      targetCtx.stroke();

      targetCtx.fillStyle = "rgb(35,58,76)";
      targetCtx.beginPath();
      targetCtx.moveTo(x + 31, y - 35);
      targetCtx.lineTo(x + 40, y - 29);
      targetCtx.lineTo(x + 31, y - 29);
      targetCtx.closePath();
      targetCtx.fill();

      [x - 30, x - 12, x + 28].forEach((wx) => {
        targetCtx.fillStyle = "rgb(18,20,24)";
        targetCtx.beginPath();
        targetCtx.arc(wx, y - 6, 6.5, 0, Math.PI * 2);
        targetCtx.fill();
        targetCtx.fillStyle = "rgb(75,82,90)";
        targetCtx.beginPath();
        targetCtx.arc(wx, y - 6, 2.5, 0, Math.PI * 2);
        targetCtx.fill();
      });

      targetCtx.font = FONT_XS;
      targetCtx.textAlign = "center";
      targetCtx.textBaseline = "top";
      targetCtx.fillStyle = rgb(this.connected ? Palette.CYAN : Palette.AMBER);
      targetCtx.fillText(this.connected ? "EPP-01 [PWR ON]" : "EPP-01 [OFFLINE]", x, y + 5);
    }
  }

  class THAADLauncherTruck {
    /** M1120 HEMTT 8x8 기반 사드(THAAD) 6연장 이동식 발사대 차량 */
    constructor(idx, xPos) {
      this.idx = idx;
      this.x = xPos;
      this.y = GROUND_Y;

      this.outriggerDeploy = 0.0;
      this.elevationDeg = 0.0;
      this.targetErected = false;

      this.thermalBatt = 65.0;
      this.cellsLoaded = new Array(6).fill(true); // 사드 방어미사일 6발 장착
      this.reloadTimer = 0.0;
      this.blastFlash = 0;
    }

    get isErected() {
      return this.elevationDeg >= 72.0;
    }

    get readyCells() {
      let count = 0;
      for (let i = 0; i < this.cellsLoaded.length; i++) {
        if (this.cellsLoaded[i]) count++;
      }
      return count;
    }

    isReadyToFire(powerConnected) {
      return powerConnected && this.isErected && this.thermalBatt >= 80.0 && this.readyCells > 0;
    }

    getPowerPort() {
      return new Vec2(this.x - 44, this.y - 14);
    }

    getPivotPos() {
      return new Vec2(this.x - 36, this.y - 22);
    }

    getMuzzleAndBreech() {
      const pivot = this.getPivotPos();
      const rad = -(this.elevationDeg * Math.PI) / 180.0;
      const dirVec = new Vec2(Math.cos(rad), Math.sin(rad));
      const muzzle = pivot.add(dirVec.mul(84.0));
      const breech = pivot.sub(dirVec.mul(12.0));
      return { muzzle, breech, dirVec };
    }

    update(powerConnected, hydraulicMult = 1.0, reloadMult = 1.0) {
      if (this.blastFlash > 0) this.blastFlash -= 1;

      if (!powerConnected) return;

      if (this.targetErected) {
        if (this.outriggerDeploy < 1.0) {
          this.outriggerDeploy = Math.min(1.0, this.outriggerDeploy + 0.065 * hydraulicMult);
        } else if (this.elevationDeg < 74.0) {
          this.elevationDeg = Math.min(74.0, this.elevationDeg + 1.25 * hydraulicMult);
        }
      } else {
        if (this.elevationDeg > 0.0) {
          this.elevationDeg = Math.max(0.0, this.elevationDeg - 1.3 * hydraulicMult);
        } else if (this.outriggerDeploy > 0.0) {
          this.outriggerDeploy = Math.max(0.0, this.outriggerDeploy - 0.065 * hydraulicMult);
        }
      }

      if (this.readyCells === 0) {
        this.reloadTimer += 0.008 * reloadMult;
        if (this.reloadTimer >= 1.0) {
          this.reloadTimer = 0.0;
          this.cellsLoaded.fill(true);
          this.thermalBatt = 70.0;
        }
      }
    }

    fireOneCell(powerConnected, smokeList, fireList, debrisList, lightsList) {
      if (!this.isReadyToFire(powerConnected)) return null;

      const cellIdx = this.cellsLoaded.findIndex(Boolean);
      this.cellsLoaded[cellIdx] = false;
      const usedBatt = this.thermalBatt;
      this.thermalBatt = Math.max(0.0, this.thermalBatt - 18.0);
      this.blastFlash = 20;

      const { muzzle, breech, dirVec } = this.getMuzzleAndBreech();
      const perp = new Vec2(-dirVec.y, dirVec.x);
      const rowOffset = ((cellIdx % 3) - 1.0) * 4.5;
      const spawnMuzzle = muzzle.add(perp.mul(rowOffset));
      const spawnBreech = breech.add(perp.mul(rowOffset));

      debrisList.push(new TumblingDebris(
        spawnMuzzle,
        dirVec.mul(randRange(5.0, 8.0)).add(perp.mul(randRange(-2.0, 2.0))),
        9, 3, [185, 190, 195], 110
      ));
      debrisList.push(new TumblingDebris(
        spawnBreech,
        dirVec.mul(-randRange(6.0, 9.5)).add(perp.mul(randRange(-2.0, 2.0))),
        9, 3, [150, 155, 160], 110
      ));

      lightsList.push(new DynamicLight(spawnBreech, Palette.ORANGE_PLUME, 1.5, 310, 26));
      lightsList.push(new DynamicLight(spawnMuzzle, Palette.AMBER, 1.1, 220, 18));

      const smokeCols = [
        [235, 236, 240],
        [215, 218, 224],
        [195, 198, 205]
      ];
      for (let i = 0; i < 24; i++) {
        const spread = randRange(-0.38, 0.38);
        const blastDir = dirVec.mul(-1).rotateRad(spread);
        const spd = randRange(4.5, 12.5);
        smokeList.push(new ExhaustSmokeCloud(
          spawnBreech,
          blastDir.mul(spd),
          randRange(6.5, 11.5),
          randInt(65, 105),
          randChoice(smokeCols),
          randRange(0.28, 0.44),
          true
        ));
      }

      for (let i = 0; i < 16; i++) {
        const spread = randRange(-0.28, 0.28);
        const blastDir = dirVec.mul(-1).rotateRad(spread);
        const spd = randRange(5.0, 13.0);
        fireList.push(new PlumeFireParticle(
          spawnBreech,
          blastDir.mul(spd),
          randRange(6.0, 10.5),
          randInt(12, 22)
        ));
      }

      for (let i = 0; i < 10; i++) {
        fireList.push(new PlumeFireParticle(
          spawnMuzzle,
          dirVec.mul(randRange(2.0, 6.0)).add(perp.mul(randRange(-1.5, 1.5))),
          randRange(4.0, 7.0),
          randInt(8, 14)
        ));
      }

      return { muzzlePos: spawnMuzzle, dirVec, usedBatt };
    }

    draw(targetCtx, isSelected, powerConnected) {
      const x = Math.floor(this.x);
      const y = Math.floor(this.y);

      const jackDrop = Math.floor(this.outriggerDeploy * 10);
      [x - 40, x + 20].forEach((jx) => {
        targetCtx.strokeStyle = rgb(Palette.STEEL_LIGHT);
        targetCtx.lineWidth = 3;
        targetCtx.beginPath();
        targetCtx.moveTo(jx, y - 14);
        targetCtx.lineTo(jx, y - 10 + jackDrop);
        targetCtx.stroke();

        targetCtx.fillStyle = rgb(this.outriggerDeploy >= 1.0 ? Palette.AMBER : Palette.STEEL_DARK);
        targetCtx.fillRect(jx - 5, y - 11 + jackDrop, 10, 3);
      });

      targetCtx.fillStyle = rgb(Palette.OLIVE_DRAB);
      targetCtx.fillRect(x - 46, y - 20, 92, 9);
      targetCtx.strokeStyle = rgb(Palette.STEEL_DARK);
      targetCtx.lineWidth = 1;
      targetCtx.strokeRect(x - 46, y - 20, 92, 9);

      targetCtx.fillStyle = rgb(Palette.OLIVE_LIGHT);
      targetCtx.beginPath();
      targetCtx.moveTo(x + 22, y - 20);
      targetCtx.lineTo(x + 48, y - 20);
      targetCtx.lineTo(x + 50, y - 31);
      targetCtx.lineTo(x + 38, y - 39);
      targetCtx.lineTo(x + 22, y - 39);
      targetCtx.closePath();
      targetCtx.fill();
      targetCtx.strokeStyle = rgb(Palette.STEEL_DARK);
      targetCtx.lineWidth = 1;
      targetCtx.stroke();

      targetCtx.fillStyle = "rgb(35,58,76)";
      targetCtx.beginPath();
      targetCtx.moveTo(x + 36, y - 37);
      targetCtx.lineTo(x + 46, y - 30);
      targetCtx.lineTo(x + 36, y - 30);
      targetCtx.closePath();
      targetCtx.fill();

      [x - 36, x - 18, x + 18, x + 36].forEach((wx) => {
        targetCtx.fillStyle = "rgb(18,20,24)";
        targetCtx.beginPath();
        targetCtx.arc(wx, y - 6, 6.5, 0, Math.PI * 2);
        targetCtx.fill();

        targetCtx.fillStyle = "rgb(75,82,90)";
        targetCtx.beginPath();
        targetCtx.arc(wx, y - 6, 2.5, 0, Math.PI * 2);
        targetCtx.fill();
      });

      const pivot = this.getPivotPos();
      const rad = -(this.elevationDeg * Math.PI) / 180.0;
      const dirV = new Vec2(Math.cos(rad), Math.sin(rad));
      const perpV = new Vec2(-dirV.y, dirV.x);

      if (this.elevationDeg > 1.0) {
        const cylBase = new Vec2(x - 4, y - 20);
        const cylAttach = pivot.add(dirV.mul(38)).sub(perpV.mul(6));
        targetCtx.strokeStyle = rgb(Palette.STEEL_LIGHT);
        targetCtx.lineWidth = 3;
        targetCtx.beginPath();
        targetCtx.moveTo(cylBase.x, cylBase.y);
        targetCtx.lineTo(cylAttach.x, cylAttach.y);
        targetCtx.stroke();
      }

      const pRear = pivot.sub(dirV.mul(10));
      const pFront = pivot.add(dirV.mul(82));
      const c0 = pRear.add(perpV.mul(7));
      const c1 = pFront.add(perpV.mul(7));
      const c2 = pFront.sub(perpV.mul(7));
      const c3 = pRear.sub(perpV.mul(7));

      targetCtx.fillStyle = rgb(Palette.OLIVE_DRAB);
      targetCtx.beginPath();
      targetCtx.moveTo(c0.x, c0.y);
      targetCtx.lineTo(c1.x, c1.y);
      targetCtx.lineTo(c2.x, c2.y);
      targetCtx.lineTo(c3.x, c3.y);
      targetCtx.closePath();
      targetCtx.fill();

      targetCtx.strokeStyle = rgb(isSelected ? Palette.RADAR_GREEN : (powerConnected ? Palette.OLIVE_LIGHT : Palette.STEEL_DARK));
      targetCtx.lineWidth = isSelected ? 1.5 : 1;
      targetCtx.stroke();

      [0.25, 0.55, 0.85].forEach((frac) => {
        const bandC = pivot.add(dirV.mul(82 * frac));
        const b1 = bandC.add(perpV.mul(7));
        const b2 = bandC.sub(perpV.mul(7));
        targetCtx.strokeStyle = rgb(Palette.STEEL_DARK);
        targetCtx.lineWidth = 2;
        targetCtx.beginPath();
        targetCtx.moveTo(b1.x, b1.y);
        targetCtx.lineTo(b2.x, b2.y);
        targetCtx.stroke();
      });

      if (this.blastFlash > 0) {
        GlowCache.draw(targetCtx, Palette.ORANGE_PLUME, pRear, 34, Math.floor(180 * (this.blastFlash / 20.0)));
      }

      const tagCol = !powerConnected ? Palette.RED_ALERT : (isSelected ? Palette.RADAR_GREEN : Palette.TEXT_DIM);
      targetCtx.font = FONT_XS;
      targetCtx.textAlign = "center";
      targetCtx.textBaseline = "top";
      targetCtx.fillStyle = rgb(tagCol);
      targetCtx.fillText(`TEL-0${this.idx + 1} [${this.readyCells}/6]`, x, y + 5);
    }
  }

  class ANTPY2RadarTrailer {
    /** 포대 1기당 1대씩 배치되는 AN/TPY-2 X-밴드 위상배열 레이더 차량 */
    constructor(idx, xPos, sectorBiasDeg) {
      this.idx = idx;
      this.x = xPos;
      this.y = GROUND_Y;
      this.sectorBiasDeg = sectorBiasDeg;
      this.dishAngleDeg = sectorBiasDeg;
    }

    getPowerPort() {
      return new Vec2(this.x - 36, this.y - 12);
    }

    update(primaryTarget, powerConnected) {
      if (!powerConnected) {
        this.dishAngleDeg = lerp(this.dishAngleDeg, 10.0, 0.06);
        return;
      }
      if (primaryTarget) {
        const dx = primaryTarget.pos.x - this.x;
        const dy = (this.y - 34) - primaryTarget.pos.y;
        const desiredDeg = clamp((Math.atan2(dy, Math.max(40.0, dx)) * 180.0) / Math.PI, 12.0, 68.0);
        this.dishAngleDeg = lerp(this.dishAngleDeg, desiredDeg, 0.09);
      } else {
        const sweep = this.sectorBiasDeg + Math.sin(performance.now() * 0.0022 + this.idx * 1.4) * 14.0;
        this.dishAngleDeg = lerp(this.dishAngleDeg, sweep, 0.05);
      }
    }

    draw(targetCtx, hasLock, powerConnected) {
      const x = Math.floor(this.x);
      const y = Math.floor(this.y);

      targetCtx.fillStyle = rgb(Palette.OLIVE_DRAB);
      targetCtx.fillRect(x - 36, y - 18, 72, 9);

      [x - 32, x + 32].forEach((jx) => {
        targetCtx.strokeStyle = rgb(Palette.STEEL_LIGHT);
        targetCtx.lineWidth = 2.5;
        targetCtx.beginPath();
        targetCtx.moveTo(jx, y - 11);
        targetCtx.lineTo(jx, y);
        targetCtx.stroke();
      });

      [x - 20, x - 8, x + 18].forEach((wx) => {
        targetCtx.fillStyle = "rgb(18,20,24)";
        targetCtx.beginPath();
        targetCtx.arc(wx, y - 5.5, 5.5, 0, Math.PI * 2);
        targetCtx.fill();
      });

      targetCtx.fillStyle = rgb(Palette.OLIVE_LIGHT);
      targetCtx.fillRect(x - 33, y - 31, 22, 13);
      targetCtx.strokeStyle = rgb(Palette.STEEL_DARK);
      targetCtx.lineWidth = 1;
      targetCtx.strokeRect(x - 33, y - 31, 22, 13);

      const pivot = new Vec2(x + 8, y - 20);
      const beamRad = -(this.dishAngleDeg * Math.PI) / 180.0;
      const beamDir = new Vec2(Math.cos(beamRad), Math.sin(beamRad));
      const faceDir = new Vec2(-beamDir.y, beamDir.x);

      const pBot = pivot.sub(faceDir.mul(5));
      const pTop = pivot.add(faceDir.mul(23));
      const backVec = beamDir.mul(-10);

      const d0 = pBot;
      const d1 = pTop;
      const d2 = pTop.add(backVec);
      const d3 = pBot.add(backVec);

      targetCtx.fillStyle = rgb(Palette.OLIVE_LIGHT);
      targetCtx.beginPath();
      targetCtx.moveTo(d0.x, d0.y);
      targetCtx.lineTo(d1.x, d1.y);
      targetCtx.lineTo(d2.x, d2.y);
      targetCtx.lineTo(d3.x, d3.y);
      targetCtx.closePath();
      targetCtx.fill();

      targetCtx.strokeStyle = rgb(powerConnected ? Palette.CYAN : Palette.STEEL_DARK);
      targetCtx.lineWidth = 1;
      targetCtx.stroke();

      targetCtx.strokeStyle = rgb(!powerConnected ? Palette.STEEL_DARK : (hasLock ? Palette.RADAR_GREEN : Palette.CYAN));
      targetCtx.lineWidth = 2;
      targetCtx.beginPath();
      targetCtx.moveTo(pBot.x, pBot.y);
      targetCtx.lineTo(pTop.x, pTop.y);
      targetCtx.stroke();

      if (powerConnected) {
        const beamLen = 780;
        const spread = hasLock ? 0.055 : 0.115;
        const centerOrigin = pBot.add(pTop).mul(0.5);
        const bLeft = centerOrigin.add(beamDir.rotateRad(-spread).mul(beamLen));
        const bRight = centerOrigin.add(beamDir.rotateRad(spread).mul(beamLen));

        targetCtx.save();
        targetCtx.globalCompositeOperation = "lighter";
        targetCtx.fillStyle = hasLock ? "rgba(45,255,140,0.085)" : "rgba(0,210,255,0.055)";
        targetCtx.beginPath();
        targetCtx.moveTo(centerOrigin.x, centerOrigin.y);
        targetCtx.lineTo(bLeft.x, bLeft.y);
        targetCtx.lineTo(bRight.x, bRight.y);
        targetCtx.closePath();
        targetCtx.fill();
        targetCtx.restore();
      }

      targetCtx.font = FONT_XS;
      targetCtx.textAlign = "center";
      targetCtx.textBaseline = "top";
      targetCtx.fillStyle = rgb(powerConnected ? Palette.CYAN : Palette.TEXT_DIM);
      targetCtx.fillText(`TPY2-0${this.idx + 1}`, x, y + 5);
    }
  }

  class LSAMLauncherUnit {
    /** 최외곽 초고고도 자동 요격 포대 (L-SAM VLS 4연장 수직발사기, 자동발사/낮은 명중률) */
    constructor(xPos) {
      this.x = xPos;
      this.y = GROUND_Y;
      this.elevationDeg = 0.0;
      this.cellsLoaded = new Array(4).fill(true);
      this.fireCooldown = 0;
      this.reloadTimer = 0.0;
      this.blastFlash = 0;
    }

    get readyCells() {
      return this.cellsLoaded.filter(Boolean).length;
    }

    getPowerPort() {
      return new Vec2(this.x - 32, this.y - 12);
    }

    update(powerConnected, autoEnabled, threats, interceptors, smokeList, fireList, lightsList) {
      if (this.blastFlash > 0) this.blastFlash -= 1;
      if (this.fireCooldown > 0) this.fireCooldown -= 1;

      if (!powerConnected) {
        this.elevationDeg = Math.max(0.0, this.elevationDeg - 1.5);
        return null;
      }

      if (this.elevationDeg < 90.0) {
        this.elevationDeg = Math.min(90.0, this.elevationDeg + 1.8);
      }

      if (this.readyCells === 0) {
        this.reloadTimer += 0.0055;
        if (this.reloadTimer >= 1.0) {
          this.reloadTimer = 0.0;
          this.cellsLoaded.fill(true);
        }
        return null;
      }

      if (autoEnabled && this.elevationDeg >= 88.0 && this.fireCooldown <= 0 && threats.length > 0) {
        const candidates = threats.filter((t) => {
          if (!t.alive || t.pos.y > 330) return false;
          const alreadyTargeted = interceptors.some((m) => m.active && m.target === t && m.layer === "LSAM");
          return !alreadyTargeted;
        });

        if (candidates.length > 0) {
          candidates.sort((a, b) => a.pos.y - b.pos.y);
          const target = candidates[0];
          const cellIdx = this.cellsLoaded.findIndex(Boolean);
          this.cellsLoaded[cellIdx] = false;
          this.fireCooldown = 125;
          this.blastFlash = 16;

          const muzzle = new Vec2(this.x + (cellIdx - 1.5) * 6, this.y - 58);
          const launchDir = new Vec2(0.18, -1.0).normalize();

          lightsList.push(new DynamicLight(muzzle, Palette.MAGENTA, 1.0, 220, 18));
          for (let i = 0; i < 12; i++) {
            smokeList.push(new ExhaustSmokeCloud(
              new Vec2(this.x, GROUND_Y - 6),
              new Vec2(randRange(-3.5, 3.5), randRange(-1.8, -0.3)),
              randRange(5, 9),
              randInt(45, 70),
              [210, 200, 225],
              0.22,
              true
            ));
            fireList.push(new PlumeFireParticle(muzzle, new Vec2(randRange(-1.2, 1.2), randRange(-4, -1)), 5, 10));
          }

          SFX.play("lsam_roar");
          return new LSAMInterceptor(muzzle, launchDir, target);
        }
      }
      return null;
    }

    draw(targetCtx, powerConnected, autoEnabled) {
      const x = Math.floor(this.x);
      const y = Math.floor(this.y);

      targetCtx.fillStyle = rgb(Palette.OLIVE_DRAB);
      targetCtx.fillRect(x - 34, y - 18, 68, 9);
      [x - 24, x - 8, x + 22].forEach((wx) => {
        targetCtx.fillStyle = "rgb(18,20,24)";
        targetCtx.beginPath();
        targetCtx.arc(wx, y - 5.5, 5.5, 0, Math.PI * 2);
        targetCtx.fill();
      });

      const pivot = new Vec2(x - 16, y - 20);
      const rad = -(this.elevationDeg * Math.PI) / 180.0;
      const dirV = new Vec2(Math.cos(rad), Math.sin(rad));
      const perpV = new Vec2(-dirV.y, dirV.x);
      const top = pivot.add(dirV.mul(44));

      const p0 = pivot.add(perpV.mul(11));
      const p1 = top.add(perpV.mul(11));
      const p2 = top.sub(perpV.mul(11));
      const p3 = pivot.sub(perpV.mul(11));

      targetCtx.fillStyle = rgb(Palette.STEEL_DARK);
      targetCtx.beginPath();
      targetCtx.moveTo(p0.x, p0.y);
      targetCtx.lineTo(p1.x, p1.y);
      targetCtx.lineTo(p2.x, p2.y);
      targetCtx.lineTo(p3.x, p3.y);
      targetCtx.closePath();
      targetCtx.fill();

      targetCtx.strokeStyle = rgb(powerConnected && autoEnabled ? Palette.MAGENTA : Palette.STEEL_LIGHT);
      targetCtx.lineWidth = 1.5;
      targetCtx.stroke();

      if (this.blastFlash > 0) {
        GlowCache.draw(targetCtx, Palette.MAGENTA, top, 28, Math.floor(170 * (this.blastFlash / 16.0)));
      }

      targetCtx.font = FONT_XS;
      targetCtx.textAlign = "center";
      targetCtx.textBaseline = "top";
      targetCtx.fillStyle = rgb(powerConnected ? Palette.MAGENTA : Palette.TEXT_DIM);
      targetCtx.fillText(`L-SAM [${this.readyCells}/4]`, x, y + 5);
    }
  }

  class PAC3LauncherUnit {
    /** 하층 종말 수동 요격 포대 (PAC-3 MSE 8연장 경사발사기) */
    constructor(xPos) {
      this.x = xPos;
      this.y = GROUND_Y;
      this.elevationDeg = 0.0;
      this.cellsLoaded = new Array(8).fill(true);
      this.reloadTimer = 0.0;
      this.blastFlash = 0;
    }

    get readyCells() {
      return this.cellsLoaded.filter(Boolean).length;
    }

    getPowerPort() {
      return new Vec2(this.x - 32, this.y - 12);
    }

    isReadyToFire(powerConnected) {
      return powerConnected && this.elevationDeg >= 55.0 && this.readyCells > 0;
    }

    update(powerConnected) {
      if (this.blastFlash > 0) this.blastFlash -= 1;

      if (!powerConnected) {
        this.elevationDeg = Math.max(0.0, this.elevationDeg - 1.5);
        return;
      }

      if (this.elevationDeg < 58.0) {
        this.elevationDeg = Math.min(58.0, this.elevationDeg + 1.6);
      }

      if (this.readyCells === 0) {
        this.reloadTimer += 0.0085;
        if (this.reloadTimer >= 1.0) {
          this.reloadTimer = 0.0;
          this.cellsLoaded.fill(true);
        }
      }
    }

    fireOneCell(powerConnected, target, smokeList, fireList, lightsList) {
      if (!this.isReadyToFire(powerConnected) || !target) return null;

      const cellIdx = this.cellsLoaded.findIndex(Boolean);
      this.cellsLoaded[cellIdx] = false;
      this.blastFlash = 14;

      const rad = -(this.elevationDeg * Math.PI) / 180.0;
      const dirV = new Vec2(Math.cos(rad), Math.sin(rad));
      const perpV = new Vec2(-dirV.y, dirV.x);
      const pivot = new Vec2(this.x - 16, yOffset(this.y));
      const muzzle = pivot.add(dirV.mul(52)).add(perpV.mul(((cellIdx % 4) - 1.5) * 3.0));
      const breech = pivot.sub(dirV.mul(8));

      lightsList.push(new DynamicLight(breech, Palette.AMBER, 1.0, 190, 16));
      for (let i = 0; i < 12; i++) {
        smokeList.push(new ExhaustSmokeCloud(
          breech,
          dirV.mul(-randRange(3.5, 8.0)).rotateRad(randRange(-0.35, 0.35)),
          randRange(4.5, 8.0),
          randInt(40, 65),
          [220, 225, 230],
          0.22,
          true
        ));
        fireList.push(new PlumeFireParticle(muzzle, dirV.mul(randRange(2, 5)), 4, 9));
      }

      SFX.play("pac3_roar");
      return new PAC3Interceptor(muzzle, dirV, target);
    }

    draw(targetCtx, powerConnected) {
      const x = Math.floor(this.x);
      const y = Math.floor(this.y);

      targetCtx.fillStyle = rgb(Palette.OLIVE_DRAB);
      targetCtx.fillRect(x - 34, y - 16, 68, 8);
      [x - 24, x - 8, x + 22].forEach((wx) => {
        targetCtx.fillStyle = "rgb(18,20,24)";
        targetCtx.beginPath();
        targetCtx.arc(wx, y - 5, 5, 0, Math.PI * 2);
        targetCtx.fill();
      });

      const pivot = new Vec2(x - 16, y - 18);
      const rad = -(this.elevationDeg * Math.PI) / 180.0;
      const dirV = new Vec2(Math.cos(rad), Math.sin(rad));
      const perpV = new Vec2(-dirV.y, dirV.x);
      const front = pivot.add(dirV.mul(50));

      const c0 = pivot.add(perpV.mul(8));
      const c1 = front.add(perpV.mul(8));
      const c2 = front.sub(perpV.mul(8));
      const c3 = pivot.sub(perpV.mul(8));

      targetCtx.fillStyle = rgb(Palette.OLIVE_LIGHT);
      targetCtx.beginPath();
      targetCtx.moveTo(c0.x, c0.y);
      targetCtx.lineTo(c1.x, c1.y);
      targetCtx.lineTo(c2.x, c2.y);
      targetCtx.lineTo(c3.x, c3.y);
      targetCtx.closePath();
      targetCtx.fill();

      targetCtx.strokeStyle = rgb(powerConnected ? Palette.AMBER : Palette.STEEL_DARK);
      targetCtx.lineWidth = 1.5;
      targetCtx.stroke();

      if (this.blastFlash > 0) {
        GlowCache.draw(targetCtx, Palette.AMBER, front, 22, Math.floor(160 * (this.blastFlash / 14.0)));
      }

      targetCtx.font = FONT_XS;
      targetCtx.textAlign = "center";
      targetCtx.textBaseline = "top";
      targetCtx.fillStyle = rgb(powerConnected ? Palette.AMBER : Palette.TEXT_DIM);
      targetCtx.fillText(`PAC-3 [${this.readyCells}/8]`, x, y + 5);
    }
  }

  function yOffset(groundY) {
    return groundY - 18;
  }

  // ============================================================================
  // 5. INTERCEPTORS (L-SAM OUTER AUTO, THAAD UPPER MANUAL, PAC-3 LOWER MANUAL)
  // ============================================================================
  class LSAMInterceptor {
    /** 최외곽 초고고도 자동 요격탄 (낮은 요격률 ~45%로 1차 저지선 역할) */
    constructor(startPos, launchDir, target) {
      this.layer = "LSAM";
      this.pos = startPos.clone();
      this.vel = launchDir.normalize().mul(7.0);
      this.target = target;
      this.fuel = 115.0;
      this.maxSpeed = 17.5;
      this.accel = 0.62;
      this.willHit = Math.random() < 0.45;
      this.missOffset = new Vec2(randRange(-36, 36), randRange(-26, 26));
      this.active = true;
      this.hitSuccess = false;
    }

    update(smokeList, fireList) {
      if (!this.active) return;

      if (this.fuel > 0) {
        this.fuel -= 0.65;
        const spd = Math.min(this.maxSpeed, this.vel.length() + this.accel);
        this.vel = this.vel.normalize().mul(spd);

        const backDir = this.vel.normalize().mul(-1);
        const nozzle = this.pos.add(backDir.mul(12));
        smokeList.push(new ExhaustSmokeCloud(
          nozzle,
          backDir.mul(1.1),
          3.4, 34, [215, 185, 245], 0.09, false
        ));
        if (Math.random() < 0.6) {
          fireList.push(new PlumeFireParticle(nozzle, backDir.mul(2.0), 3.5, 6));
        }
      } else {
        this.active = false;
        return;
      }

      if (this.target && this.target.alive) {
        const aimPos = this.willHit ? this.target.pos : this.target.pos.add(this.missOffset);
        const r = aimPos.sub(this.pos);
        const dist = r.length();

        if (this.willHit && dist <= 22.0) {
          this.hitSuccess = true;
          this.active = false;
          return;
        }

        if (dist > 1e-3) {
          const desiredDir = r.normalize();
          const curDir = this.vel.normalize();
          const blended = curDir.mul(0.86).add(desiredDir.mul(0.14)).normalize();
          this.vel = blended.mul(this.vel.length());
        }
      } else {
        this.active = false;
        return;
      }

      this.pos = this.pos.add(this.vel);
      if (this.pos.x < -50 || this.pos.x > SCREEN_WIDTH + 60 || this.pos.y < -80 || this.pos.y >= GROUND_Y) {
        this.active = false;
      }
    }

    draw(targetCtx) {
      if (!this.active) return;
      const angle = Math.atan2(this.vel.y, this.vel.x);
      const fwd = new Vec2(Math.cos(angle), Math.sin(angle));
      const right = new Vec2(-fwd.y, fwd.x);
      const tail = this.pos.sub(fwd.mul(13));
      const nose = this.pos.add(fwd.mul(9));

      GlowCache.draw(targetCtx, Palette.MAGENTA, tail, 14, 150);
      targetCtx.strokeStyle = rgb(Palette.MAGENTA);
      targetCtx.lineWidth = 3.5;
      targetCtx.beginPath();
      targetCtx.moveTo(tail.x, tail.y);
      targetCtx.lineTo(nose.x, nose.y);
      targetCtx.stroke();

      targetCtx.fillStyle = rgb(Palette.WHITE);
      targetCtx.beginPath();
      targetCtx.moveTo(nose.x, nose.y);
      targetCtx.lineTo(this.pos.add(fwd.mul(4)).add(right.mul(2.5)).x, this.pos.add(fwd.mul(4)).add(right.mul(2.5)).y);
      targetCtx.lineTo(this.pos.add(fwd.mul(4)).sub(right.mul(2.5)).x, this.pos.add(fwd.mul(4)).sub(right.mul(2.5)).y);
      targetCtx.closePath();
      targetCtx.fill();
    }
  }

  class PAC3Interceptor {
    /** 하층 종말 수동 요격탄 (PAC-3 MSE 고기동 직격 요격체) */
    constructor(startPos, launchDir, target) {
      this.layer = "PAC3";
      this.pos = startPos.clone();
      this.vel = launchDir.normalize().mul(8.5);
      this.target = target;
      this.fuel = 95.0;
      this.maxSpeed = 19.0;
      this.accel = 0.78;
      this.active = true;
      this.hitSuccess = false;
    }

    update(smokeList, fireList) {
      if (!this.active) return;

      if (this.fuel > 0) {
        this.fuel -= 0.72;
        const spd = Math.min(this.maxSpeed, this.vel.length() + this.accel);
        this.vel = this.vel.normalize().mul(spd);

        const backDir = this.vel.normalize().mul(-1);
        const nozzle = this.pos.add(backDir.mul(10));
        smokeList.push(new ExhaustSmokeCloud(
          nozzle,
          backDir.mul(0.9),
          2.8, 28, [245, 225, 175], 0.08, false
        ));
        if (Math.random() < 0.7) {
          fireList.push(new PlumeFireParticle(nozzle, backDir.mul(1.8), 3.0, 5));
        }
      } else {
        this.active = false;
        return;
      }

      if (this.target && this.target.alive) {
        const r = this.target.pos.sub(this.pos);
        const dist = r.length();
        if (dist <= 22.0) {
          this.hitSuccess = true;
          this.active = false;
          return;
        }
        if (dist > 1e-3) {
          const vRel = this.target.vel.sub(this.vel);
          const losRate = (r.x * vRel.y - r.y * vRel.x) / (dist * dist);
          const turnCmd = clamp(4.8 * losRate, -0.19, 0.19);
          this.vel = this.vel.rotateRad(turnCmd);
        }
      } else {
        this.active = false;
        return;
      }

      this.pos = this.pos.add(this.vel);
      if (this.pos.x < -50 || this.pos.x > SCREEN_WIDTH + 60 || this.pos.y < -50 || this.pos.y >= GROUND_Y) {
        this.active = false;
      }
    }

    draw(targetCtx) {
      if (!this.active) return;
      const angle = Math.atan2(this.vel.y, this.vel.x);
      const fwd = new Vec2(Math.cos(angle), Math.sin(angle));
      const right = new Vec2(-fwd.y, fwd.x);
      const tail = this.pos.sub(fwd.mul(11));
      const nose = this.pos.add(fwd.mul(8));

      GlowCache.draw(targetCtx, Palette.AMBER, tail, 12, 160);
      targetCtx.strokeStyle = rgb(Palette.WHITE);
      targetCtx.lineWidth = 3;
      targetCtx.beginPath();
      targetCtx.moveTo(tail.x, tail.y);
      targetCtx.lineTo(nose.x, nose.y);
      targetCtx.stroke();

      targetCtx.fillStyle = rgb(Palette.AMBER);
      targetCtx.beginPath();
      targetCtx.moveTo(nose.x, nose.y);
      targetCtx.lineTo(this.pos.add(fwd.mul(3)).add(right.mul(2.2)).x, this.pos.add(fwd.mul(3)).add(right.mul(2.2)).y);
      targetCtx.lineTo(this.pos.add(fwd.mul(3)).sub(right.mul(2.2)).x, this.pos.add(fwd.mul(3)).sub(right.mul(2.2)).y);
      targetCtx.closePath();
      targetCtx.fill();
    }
  }

  class THAADMissile {
    /** 상층·외기권 직격 요격미사일 (1단 부스터 분리 + DACS 측면 추력기 직격) */
    constructor(startPos, launchDir, target, battCharge, thrustMult = 1.0) {
      this.layer = "THAAD";
      this.pos = startPos.clone();
      this.vel = launchDir.normalize().mul(6.5);
      this.target = target;

      this.phase = "RAIL_CLEAR";
      this.phaseTimer = 14;
      this.boosterAttached = true;

      const overcharged = battCharge >= 98.0;
      const mult = thrustMult * (overcharged ? 1.15 : 1.0);
      this.fuel = 105.0;
      this.maxSpeed = 17.5 * mult;
      this.accel = 0.62 * mult;
      this.navGain = 4.4;
      this.maxTurn = 0.15;

      this.active = true;
      this.hitSuccess = false;
      this.prevDist = target ? this.pos.distanceTo(target.pos) : 9999.0;
      this.dacsPuffs = [];
    }

    update(smokeList, fireList, sparksList, debrisList) {
      if (!this.active) return;

      this.dacsPuffs = this.dacsPuffs
        .map((item) => ({ pos: item.pos, dir: item.dir, life: item.life - 1 }))
        .filter((item) => item.life > 0);

      if (this.phase === "RAIL_CLEAR") {
        this.phaseTimer -= 1;
        this.vel = this.vel.normalize().mul(Math.min(this.maxSpeed, this.vel.length() + 0.65));
        this.pos = this.pos.add(this.vel);
        this._emitPlume(smokeList, fireList, true);
        if (this.phaseTimer <= 0) {
          this.phase = "BOOST_PITCH";
        }
        return;
      }

      if (this.phase === "BOOST_PITCH") {
        this.fuel -= 0.68;
        const spd = Math.min(this.maxSpeed * 0.9, this.vel.length() + this.accel);
        this.vel = this.vel.normalize().mul(spd);
        this._emitPlume(smokeList, fireList, true);

        if (this.fuel <= 44.0) {
          this.phase = "KV_TERMINAL";
          this.boosterAttached = false;
          SFX.play("stage_sep");
          const backDir = this.vel.normalize().mul(-1);
          debrisList.push(new TumblingDebris(
            this.pos.add(backDir.mul(12)),
            this.vel.mul(0.42).add(new Vec2(randRange(-1.0, 1.0), 1.4)),
            15, 5, [175, 182, 190], 150, true
          ));
          for (let i = 0; i < 12; i++) {
            sparksList.push(new SparkStreak(
              this.pos.add(backDir.mul(10)),
              new Vec2(randRange(-2.5, 2.5), randRange(-2.5, 2.5)),
              Palette.CYAN,
              16
            ));
          }
        }
      } else if (this.phase === "KV_TERMINAL") {
        if (this.fuel > 0) {
          this.fuel -= 0.38;
          const spd = Math.min(this.maxSpeed, this.vel.length() + this.accel * 0.78);
          this.vel = this.vel.normalize().mul(spd);
          this._emitPlume(smokeList, fireList, false);
        } else {
          this.phase = "COAST";
          this.vel = this.vel.mul(0.994);
          this.vel.y += 0.04;
        }
      }

      if (this.target && this.target.alive) {
        const r = this.target.pos.sub(this.pos);
        const dist = r.length();

        if (dist <= 24.0 || (dist < 34.0 && dist > this.prevDist)) {
          this.hitSuccess = true;
          this.active = false;
          return;
        }
        this.prevDist = dist;

        if (dist > 1e-3 && this.vel.length() > 0.1) {
          const vRel = this.target.vel.sub(this.vel);
          const losRate = (r.x * vRel.y - r.y * vRel.x) / (dist * dist);
          const turnLimit = this.maxTurn * (this.phase === "KV_TERMINAL" ? 1.28 : 1.0);
          const turnCmd = clamp(this.navGain * losRate, -turnLimit, turnLimit);
          this.vel = this.vel.rotateRad(turnCmd);

          if (this.phase === "KV_TERMINAL" && Math.abs(turnCmd) > 0.025 && Math.random() < 0.65) {
            const fwd = this.vel.normalize();
            const side = new Vec2(-fwd.y, fwd.x).mul(turnCmd > 0 ? -1.0 : 1.0);
            this.dacsPuffs.push({ pos: this.pos.clone(), dir: side, life: 5 });
            if (Math.random() < 0.25) SFX.play("dacs_puff");
          }
        }
      } else {
        if (this.phase === "COAST" || this.pos.y < 15 || this.pos.x > SCREEN_WIDTH + 40) {
          this.active = false;
          return;
        }
      }

      this.pos = this.pos.add(this.vel);
      if (this.pos.x < -50 || this.pos.x > SCREEN_WIDTH + 60 || this.pos.y < -50 || this.pos.y >= GROUND_Y) {
        this.active = false;
      }
    }

    _emitPlume(smokeList, fireList, heavy = true) {
      const backDir = this.vel.normalize().mul(-1);
      const nozzle = this.pos.add(backDir.mul(this.boosterAttached ? 16 : 9));

      if (heavy) {
        smokeList.push(new ExhaustSmokeCloud(
          nozzle,
          backDir.mul(1.4).add(new Vec2(randRange(-0.35, 0.35), randRange(-0.35, 0.35))),
          5.2, 68, [232, 236, 242], 0.14, false
        ));
        if (Math.random() < 0.7) {
          fireList.push(new PlumeFireParticle(nozzle, backDir.mul(2.5), 4.5, 8));
        }
      } else {
        smokeList.push(new ExhaustSmokeCloud(
          nozzle,
          backDir.mul(0.8),
          2.2, 26, [180, 225, 250], 0.06, false
        ));
      }
    }

    draw(targetCtx) {
      if (!this.active) return;

      const angle = Math.atan2(this.vel.y, this.vel.x);
      const fwd = new Vec2(Math.cos(angle), Math.sin(angle));
      const right = new Vec2(-fwd.y, fwd.x);

      for (let i = 0; i < this.dacsPuffs.length; i++) {
        const puff = this.dacsPuffs[i];
        const jetEnd = puff.pos.add(puff.dir.mul(14 * (puff.life / 5.0)));
        targetCtx.strokeStyle = rgb(Palette.CYAN);
        targetCtx.lineWidth = 2;
        targetCtx.beginPath();
        targetCtx.moveTo(puff.pos.x, puff.pos.y);
        targetCtx.lineTo(jetEnd.x, jetEnd.y);
        targetCtx.stroke();
        GlowCache.draw(targetCtx, Palette.CYAN, puff.pos, 10, 140);
      }

      if (this.fuel > 0) {
        const isBoost = this.boosterAttached;
        const fCol = isBoost ? Palette.ORANGE_PLUME : Palette.CYAN;
        const fLen = isBoost ? randRange(22, 34) : randRange(10, 16);
        const nozzle = this.pos.sub(fwd.mul(isBoost ? 16 : 8));
        const tip = nozzle.sub(fwd.mul(fLen));
        GlowCache.draw(targetCtx, fCol, nozzle, isBoost ? 20 : 12, 170);

        const pA = nozzle.add(right.mul(3.2));
        const pB = nozzle.sub(right.mul(3.2));
        targetCtx.fillStyle = rgb(fCol);
        targetCtx.beginPath();
        targetCtx.moveTo(pA.x, pA.y);
        targetCtx.lineTo(pB.x, pB.y);
        targetCtx.lineTo(tip.x, tip.y);
        targetCtx.closePath();
        targetCtx.fill();

        const coreEnd = nozzle.sub(fwd.mul(fLen * 0.6));
        targetCtx.strokeStyle = rgb(Palette.WHITE);
        targetCtx.lineWidth = 2;
        targetCtx.beginPath();
        targetCtx.moveTo(nozzle.x, nozzle.y);
        targetCtx.lineTo(coreEnd.x, coreEnd.y);
        targetCtx.stroke();
      }

      if (this.boosterAttached) {
        const bTail = this.pos.sub(fwd.mul(16));
        const bJoint = this.pos.sub(fwd.mul(3));
        targetCtx.strokeStyle = "rgb(195,202,212)";
        targetCtx.lineWidth = 5;
        targetCtx.beginPath();
        targetCtx.moveTo(bTail.x, bTail.y);
        targetCtx.lineTo(bJoint.x, bJoint.y);
        targetCtx.stroke();

        const f0 = bTail.add(fwd.mul(4));
        const f1 = bTail.sub(fwd.mul(2)).add(right.mul(6));
        const f2 = bTail.sub(fwd.mul(2)).sub(right.mul(6));
        targetCtx.fillStyle = "rgb(95,108,122)";
        targetCtx.beginPath();
        targetCtx.moveTo(f0.x, f0.y);
        targetCtx.lineTo(f1.x, f1.y);
        targetCtx.lineTo(f2.x, f2.y);
        targetCtx.closePath();
        targetCtx.fill();
      }

      const kvTail = this.pos.sub(fwd.mul(4));
      const kvMid = this.pos.add(fwd.mul(5));
      const kvNose = this.pos.add(fwd.mul(11));

      targetCtx.strokeStyle = rgb(Palette.WHITE);
      targetCtx.lineWidth = 4;
      targetCtx.beginPath();
      targetCtx.moveTo(kvTail.x, kvTail.y);
      targetCtx.lineTo(kvMid.x, kvMid.y);
      targetCtx.stroke();

      const k0 = kvNose;
      const k1 = kvMid.add(right.mul(2.2));
      const k2 = kvMid.sub(right.mul(2.2));
      targetCtx.fillStyle = rgb(Palette.CYAN);
      targetCtx.beginPath();
      targetCtx.moveTo(k0.x, k0.y);
      targetCtx.lineTo(k1.x, k1.y);
      targetCtx.lineTo(k2.x, k2.y);
      targetCtx.closePath();
      targetCtx.fill();
    }
  }

  // ============================================================================
  // 6. INCOMING BALLISTIC MISSILE THREATS (SRBM, MRBM, MIRV, HGV, MARV)
  // ============================================================================
  class BallisticThreat {
    static _idSeq = 200;

    constructor(startPos, targetX, speed, threatType) {
      BallisticThreat._idSeq += 1;
      this.uid = `BM-${BallisticThreat._idSeq}`;
      this.pos = startPos.clone();
      this.targetPos = new Vec2(targetX, GROUND_Y);
      this.threatType = threatType;
      this.alive = true;
      this.trail = [];
      this.phase = randRange(0, Math.PI * 2);
      this.evadeCooldown = 0;
      this.apogeeReached = false;

      const dx = this.targetPos.x - this.pos.x;
      const dy = this.targetPos.y - this.pos.y;
      const dist = Math.max(60.0, Math.hypot(dx, dy));

      if (threatType === ThreatType.DECOY) {
        this.gravity = 0.009;
        this.dragCoeff = 0.0085;
        const flightT = Math.max(210.0, dist / (speed * 0.92));
        const vx = dx / flightT;
        const vy = (dy - 0.5 * this.gravity * (flightT * flightT)) / flightT;
        this.vel = new Vec2(vx, vy);
      } else if (
        threatType === ThreatType.SRBM ||
        threatType === ThreatType.MRBM ||
        threatType === ThreatType.MIRV ||
        threatType === ThreatType.MARV
      ) {
        this.gravity = threatType === ThreatType.MRBM ? 0.017 : 0.0135;
        this.dragCoeff = threatType === ThreatType.MRBM ? 0.0014 : 0.0018;
        const flightT = Math.max(185.0, dist / speed);
        const vx = dx / flightT;
        const vy = (dy - 0.5 * this.gravity * (flightT * flightT)) / flightT;
        this.vel = new Vec2(vx, vy);
      } else {
        this.gravity = 0.004;
        this.dragCoeff = 0.0012;
        this.vel = new Vec2(dx, dy).normalize().mul(speed * 1.25);
      }

      this.splitY = threatType === ThreatType.MIRV ? randInt(195, 285) : null;
      this.hasSplit = false;
    }

    getAirDensityFactor() {
      const altRatio = clamp((GROUND_Y - this.pos.y) / GROUND_Y, 0.0, 1.0);
      return Math.pow(1.0 - altRatio, 1.6);
    }

      this.splitY = threatType === ThreatType.MIRV ? randInt(195, 285) : null;
      this.hasSplit = false;
    }

    getMach() {
      return (this.vel.length() * 1.65).toFixed(1);
    }

    getAltitudeKm() {
      return Math.max(0.0, (GROUND_Y - this.pos.y) * 0.085).toFixed(1);
    }

    getColor() {
      switch (this.threatType) {
        case ThreatType.SRBM:
          return Palette.RED_ALERT;
        case ThreatType.MRBM:
          return Palette.ORANGE_PLUME;
        case ThreatType.MIRV:
          return Palette.MAGENTA;
        case ThreatType.MARV:
          return Palette.CYAN;
        default:
          return Palette.AMBER;
      }
    }

    update(smokeList, interceptors) {
      this.trail.push(this.pos.clone());
      if (this.trail.length > 36) this.trail.shift();

      this.phase += 0.09;
      if (this.evadeCooldown > 0) this.evadeCooldown -= 1;
      if (!this.apogeeReached && this.vel.y > 0) {
        this.apogeeReached = true;
      }

      const airDensity = this.getAirDensityFactor();

      if (this.threatType === ThreatType.HGV) {
        const perp = new Vec2(-this.vel.y, this.vel.x);
        if (perp.lengthSq() > 0) {
          this.pos = this.pos.add(perp.normalize().mul(Math.sin(this.phase * 1.35) * (1.1 + airDensity * 1.1)));
        }
      } else if (this.threatType === ThreatType.MARV && this.evadeCooldown <= 0) {
        for (let i = 0; i < interceptors.length; i++) {
          const m = interceptors[i];
          if (m.active && m.target === this && this.pos.distanceTo(m.pos) < 140) {
            const turnGain = 0.08 + airDensity * 0.11;
            this.vel = this.vel.rotateRad(randChoice([-turnGain, turnGain]));
            this.evadeCooldown = 44;
            break;
          }
        }
      }

      const spd = this.vel.length();
      if (spd > 0.05 && this.dragCoeff > 0) {
        const dragAccel = this.dragCoeff * spd * spd * (0.25 + airDensity * 1.35);
        const newSpd = Math.max(0.85, spd - dragAccel);
        this.vel = this.vel.normalize().mul(newSpd);
      }

      const terminalBoost = this.apogeeReached && this.threatType !== ThreatType.DECOY ? (1.0 + airDensity * 0.22) : 1.0;
      this.vel.y += this.gravity * terminalBoost;
      this.pos = this.pos.add(this.vel);

      if (Math.random() < 0.55) {
        smokeList.push(new ExhaustSmokeCloud(
          this.pos,
          new Vec2(-this.vel.x * 0.05, -this.vel.y * 0.05),
          2.6, 24, this.getColor(), 0.07, false
        ));
      }
    }

    draw(targetCtx) {
      const col = this.getColor();
      for (let i = 1; i < this.trail.length; i++) {
        const ratio = i / this.trail.length;
        const c = clampColor([col[0] * ratio, col[1] * ratio, col[2] * ratio]);
        targetCtx.strokeStyle = rgb(c);
        targetCtx.lineWidth = Math.max(1, Math.floor(3.2 * ratio));
        targetCtx.beginPath();
        targetCtx.moveTo(this.trail[i - 1].x, this.trail[i - 1].y);
        targetCtx.lineTo(this.trail[i].x, this.trail[i].y);
        targetCtx.stroke();
      }

      GlowCache.draw(targetCtx, col, this.pos, 18, 155);
      const angle = Math.atan2(this.vel.y, this.vel.x);
      const fwd = new Vec2(Math.cos(angle), Math.sin(angle));
      const right = new Vec2(-fwd.y, fwd.x);
      const w0 = this.pos.add(fwd.mul(10));
      const w1 = this.pos.sub(fwd.mul(6)).add(right.mul(4));
      const w2 = this.pos.sub(fwd.mul(6)).sub(right.mul(4));

      targetCtx.fillStyle = rgb(Palette.WHITE);
      targetCtx.beginPath();
      targetCtx.moveTo(w0.x, w0.y);
      targetCtx.lineTo(w1.x, w1.y);
      targetCtx.lineTo(w2.x, w2.y);
      targetCtx.closePath();
      targetCtx.fill();
    }
  }

  // ============================================================================
  // 7. TFCC TACTICAL CONSOLE SWITCH
  // ============================================================================
  class ConsoleSwitch {
    constructor(x, y, w, h, title, sub, hotkey, accent) {
      this.x = x;
      this.y = y;
      this.w = w;
      this.h = h;
      this.title = title;
      this.sub = sub;
      this.hotkey = hotkey;
      this.accent = accent;
    }

    contains(pt) {
      return pt.x >= this.x && pt.x <= this.x + this.w && pt.y >= this.y && pt.y <= this.y + this.h;
    }

    draw(targetCtx, hovered, active, overrideTitle = null, overrideSub = null, pulseGuide = false) {
      let bg = !active ? [28, 35, 45] : clampColor([this.accent[0] * 0.25, this.accent[1] * 0.25, this.accent[2] * 0.25]);
      if (hovered) bg = clampColor([bg[0] + 12, bg[1] + 12, bg[2] + 12]);

      targetCtx.fillStyle = rgb(bg);
      targetCtx.beginPath();
      targetCtx.roundRect(this.x, this.y, this.w, this.h, 6);
      targetCtx.fill();

      targetCtx.strokeStyle = rgb(active || hovered ? this.accent : Palette.PANEL_BORDER);
      targetCtx.lineWidth = 2;
      targetCtx.stroke();

      if (pulseGuide) {
        const pulse = 0.45 + 0.45 * Math.sin(performance.now() * 0.008);
        targetCtx.save();
        targetCtx.strokeStyle = `rgba(255, 225, 90, ${pulse.toFixed(3)})`;
        targetCtx.lineWidth = 3.5;
        targetCtx.beginPath();
        targetCtx.roundRect(this.x - 2, this.y - 2, this.w + 4, this.h + 4, 8);
        targetCtx.stroke();
        targetCtx.restore();
      }

      const ledX = this.x + 11;
      const ledY = this.y + 11;
      targetCtx.fillStyle = rgb(active ? this.accent : [55, 65, 76]);
      targetCtx.beginPath();
      targetCtx.arc(ledX, ledY, 4, 0, Math.PI * 2);
      targetCtx.fill();
      if (active) {
        GlowCache.draw(targetCtx, this.accent, new Vec2(ledX, ledY), 10, 130);
      }

      targetCtx.font = FONT_XS;
      targetCtx.textAlign = "right";
      targetCtx.textBaseline = "top";
      targetCtx.fillStyle = "rgb(155,172,192)";
      targetCtx.fillText(`[${this.hotkey}]`, this.x + this.w - 7, this.y + 6);

      const tStr = overrideTitle !== null ? overrideTitle : this.title;
      const sStr = overrideSub !== null ? overrideSub : this.sub;

      targetCtx.font = FONT_MD;
      targetCtx.textAlign = "center";
      targetCtx.textBaseline = "top";
      targetCtx.fillStyle = rgb(active ? Palette.WHITE : [195, 205, 218]);
      targetCtx.fillText(tStr, this.x + this.w / 2, this.y + 20);

      targetCtx.font = FONT_XS;
      targetCtx.fillStyle = rgb(active ? this.accent : Palette.TEXT_DIM);
      targetCtx.fillText(sStr, this.x + this.w / 2, this.y + 41);
    }
  }

  // ============================================================================
  // 8. MAIN THAAD & MULTI-LAYER BMD SIMULATION CONTROLLER
  // ============================================================================
  class THAADCommandSim {
    constructor() {
      this.skySurf = this._buildSky();
      this.stars = [];
      for (let i = 0; i < 120; i++) {
        this.stars.push({
          x: randInt(0, SCREEN_WIDTH - 1),
          y: randInt(8, BATTLE_HEIGHT - 160),
          b: randInt(100, 230)
        });
      }
      this.ridgeFar = this._makeRidge(95, 38, 0.006);
      this.ridgeNear = this._makeRidge(55, 22, 0.011);

      // 하단 사격통제 콘솔 버튼 배치 (3열 구성, 겹침 없이 정렬)
      this.btnPower = new ConsoleSwitch(280, CONSOLE_TOP + 48, 152, 60, "POWER LINK", "EPP-01 CABLE", "C", Palette.CYAN);
      this.btnErect = new ConsoleSwitch(280, CONSOLE_TOP + 114, 152, 60, "ERECT TEL", "RAISE TO 74°", "E", Palette.CYAN);
      this.btnBatt = new ConsoleSwitch(280, CONSOLE_TOP + 180, 152, 60, "THERMAL BATT", "HOLD CHARGE", "F", Palette.AMBER);

      this.btnAutoprep = new ConsoleSwitch(440, CONSOLE_TOP + 48, 146, 60, "AUTO-PREP", "ERECT & CHG", "T", Palette.RADAR_GREEN);
      this.btnLock = new ConsoleSwitch(440, CONSOLE_TOP + 114, 146, 60, "TPY-2 LOCK", "CYCLE TARGET", "TAB", Palette.RADAR_GREEN);
      this.btnLsamAuto = new ConsoleSwitch(440, CONSOLE_TOP + 180, 146, 60, "L-SAM: AUTO", "OUTER (~45%)", "L", Palette.MAGENTA);

      this.btnArm = new ConsoleSwitch(1238, CONSOLE_TOP + 48, 182, 60, "SAFE", "MASTER ARM", "A", Palette.RED_ALERT);
      this.btnFire = new ConsoleSwitch(1238, CONSOLE_TOP + 114, 182, 60, "LAUNCH THAAD", "UPPER LAYER", "SPACE", Palette.RED_ALERT);
      this.btnFirePac3 = new ConsoleSwitch(1238, CONSOLE_TOP + 180, 182, 60, "FIRE PAC-3", "LOWER LAYER", "X", Palette.AMBER);

      this.battleCanvas = document.createElement("canvas");
      this.battleCanvas.width = SCREEN_WIDTH;
      this.battleCanvas.height = BATTLE_HEIGHT;
      this.battleCtx = this.battleCanvas.getContext("2d");

      this.keys = {};
      this.pointerPos = new Vec2(SCREEN_WIDTH / 2, BATTLE_HEIGHT / 2);
      this.holdingBattButton = false;

      this.reset();
      this._bindEvents();
    }

    _buildSky() {
      const s = document.createElement("canvas");
      s.width = SCREEN_WIDTH;
      s.height = BATTLE_HEIGHT;
      const sctx = s.getContext("2d");

      for (let y = 0; y < BATTLE_HEIGHT; y++) {
        const t = y / BATTLE_HEIGHT;
        let c;
        if (t < 0.62) {
          c = lerpColor(Palette.SKY_TOP, Palette.SKY_MID, t / 0.62);
        } else if (t < 0.9) {
          c = lerpColor(Palette.SKY_MID, Palette.SKY_LOW, (t - 0.62) / 0.28);
        } else {
          c = lerpColor(Palette.SKY_LOW, Palette.HORIZON_DUST, (t - 0.9) / 0.1);
        }
        sctx.fillStyle = rgb(c);
        sctx.fillRect(0, y, SCREEN_WIDTH, 1);
      }

      const exoY = 185;
      sctx.strokeStyle = "rgb(30,56,82)";
      sctx.lineWidth = 1;
      for (let x = 0; x < SCREEN_WIDTH; x += 24) {
        sctx.beginPath();
        sctx.moveTo(x, exoY);
        sctx.lineTo(x + 12, exoY);
        sctx.stroke();
      }
      sctx.font = FONT_XS;
      sctx.textAlign = "left";
      sctx.textBaseline = "top";
      sctx.fillStyle = "rgb(52,92,128)";
      sctx.fillText("OUTER L-SAM & EXO-ATMOSPHERIC THAAD LAYER (ALT 45KM+)", 16, exoY - 15);
      return s;
    }

    _makeRidge(baseH, amp, freq) {
      const pts = [];
      const off = randRange(0, 50);
      for (let x = 0; x <= SCREEN_WIDTH + 24; x += 24) {
        const h = baseH + Math.sin(x * freq + off) * amp + Math.cos(x * freq * 2.4) * (amp * 0.4);
        pts.push({ x, y: GROUND_Y - Math.max(10, h) });
      }
      return pts;
    }

    reset() {
      // 좌측에서 우측으로 다층 방공포대 전개:
      // EPP-01(전력차량) -> L-SAM(최외곽 자동) -> TEL-01 & TPY2-01 -> TEL-02 & TPY2-02 -> PAC-3(하층 수동)
      this.powerTruck = new BatterySupplyTruck(70);
      this.lsamLauncher = new LSAMLauncherUnit(175);
      this.tels = [
        new THAADLauncherTruck(0, 305),
        new THAADLauncherTruck(1, 545)
      ];
      this.radars = [
        new ANTPY2RadarTrailer(0, 425, 28.0),
        new ANTPY2RadarTrailer(1, 665, 44.0)
      ];
      this.pac3Launcher = new PAC3LauncherUnit(785);
      this.selectedTel = 0;

      // 우측 방어 대상 전략 기지 (3개 구역)
      this.bases = [
        { name: "AIRBASE ALPHA", x: 995, hp: 150, maxHp: 150, alive: true },
        { name: "COMMAND HUB", x: 1155, hp: 150, maxHp: 150, alive: true },
        { name: "METRO SECTOR", x: 1315, hp: 150, maxHp: 150, alive: true }
      ];

      this.threats = [];
      this.interceptors = [];
      this.smoke = [];
      this.fire = [];
      this.sparks = [];
      this.debris = [];
      this.shockwaves = [];
      this.lights = [];
      this.callouts = [];

      this.masterArmed = false;
      this.autoPrep = false;
      this.lsamAutoEnabled = true;
      this.lockedTarget = null;
      this.lockProgress = 0.0;

      this.score = 0;
      this.intercepts = 0;
      this.wave = 1;
      this.toSpawn = 4;
      this.spawnTimer = 95;
      this.waveCooldown = 0;
      this.shake = 0.0;
      this.hitstop = 0;
      this.humTimer = 0;
      this.statusMsg = "1. TAP [POWER LINK] (OR EPP-01 TRUCK) TO ENERGIZE MULTI-LAYER BMD BATTERY";
      this.statusCol = Palette.CYAN;
      this.gameOver = false;
    }

    setStatus(msg, col = Palette.CYAN) {
      this.statusMsg = msg;
      this.statusCol = col;
    }

    togglePowerLink() {
      const linked = this.powerTruck.toggleConnection();
      SFX.play(linked ? "power_link" : "click");
      if (linked) {
        this.setStatus("EPP-01 POWER ONLINE! L-SAM AUTO-ACTIVE // PRESS [E] TO ERECT THAAD LAUNCHERS", Palette.RADAR_GREEN);
      } else {
        this.lockProgress = 0.0;
        this.setStatus("EPP-01 POWER DISCONNECTED! ALL LAUNCHERS & RADARS OFFLINE", Palette.RED_ALERT);
      }
    }

    acquireTarget(threat) {
      if (!this.powerTruck.connected) {
        SFX.play("alarm");
        this.setStatus("DUAL AN/TPY-2 RADARS OFFLINE! CONNECT EPP-01 POWER FIRST [C]", Palette.RED_ALERT);
        return;
      }
      if (threat && threat.alive && threat !== this.lockedTarget) {
        this.lockedTarget = threat;
        this.lockProgress = 0.0;
        SFX.play("radar_lock");
        this.setStatus(`DUAL AN/TPY-2 TRACKING ${threat.uid} [${threat.threatType}]...`, Palette.RADAR_GREEN);
      }
    }

    cycleTarget() {
      if (!this.powerTruck.connected) {
        SFX.play("alarm");
        this.setStatus("RADARS OFFLINE: CONNECT EPP-01 POWER [C]", Palette.RED_ALERT);
        return;
      }
      if (this.threats.length === 0) {
        this.setStatus("NO BALLISTIC TARGETS ON DUAL AN/TPY-2 RADARS", Palette.AMBER);
        return;
      }
      const ordered = [...this.threats].sort((a, b) => b.pos.y - a.pos.y);
      const curIdx = ordered.indexOf(this.lockedTarget);
      if (curIdx !== -1) {
        const nxt = ordered[(curIdx + 1) % ordered.length];
        this.acquireTarget(nxt);
      } else {
        this.acquireTarget(ordered[0]);
      }
    }

    attemptLaunchThaad() {
      if (this.gameOver) return;
      if (!this.powerTruck.connected) {
        SFX.play("alarm");
        this.setStatus("INTERLOCK BLOCKED: CONNECT EPP-01 POWER FIRST! TAP [POWER LINK]", Palette.RED_ALERT);
        return;
      }
      if (!this.masterArmed) {
        SFX.play("alarm");
        this.setStatus("INTERLOCK BLOCKED: MASTER ARM IS [SAFE]! TAP [SAFE -> ARMED]", Palette.RED_ALERT);
        return;
      }
      if (!this.lockedTarget || !this.threats.includes(this.lockedTarget)) {
        if (this.threats.length > 0) {
          this.acquireTarget([...this.threats].sort((a, b) => b.pos.y - a.pos.y)[0]);
        } else {
          SFX.play("alarm");
          this.setStatus("NO INCOMING TARGETS TO ENGAGE", Palette.AMBER);
          return;
        }
      }
      if (this.lockProgress < 1.0) {
        this.lockProgress = 1.0;
      }

      const order = [this.tels[this.selectedTel], ...this.tels.filter((t) => t.idx !== this.selectedTel)];
      const readyTel = order.find((t) => t.isReadyToFire(this.powerTruck.connected));

      if (!readyTel) {
        SFX.play("alarm");
        if (!this.tels.some((t) => t.isErected)) {
          this.setStatus("INTERLOCK BLOCKED: THAAD STOWED! TAP [ERECT TEL]", Palette.RED_ALERT);
        } else if (this.tels.every((t) => t.readyCells === 0)) {
          this.setStatus("INTERLOCK BLOCKED: ALL 12 THAAD CELLS REARMING!", Palette.AMBER);
        } else {
          this.setStatus("INTERLOCK BLOCKED: THERMAL BATT <80%! HOLD [THERMAL BATT]", Palette.RED_ALERT);
        }
        return;
      }

      const launchData = readyTel.fireOneCell(
        this.powerTruck.connected,
        this.smoke,
        this.fire,
        this.debris,
        this.lights
      );
      if (launchData) {
        const missile = new THAADMissile(
          launchData.muzzlePos,
          launchData.dirVec,
          this.lockedTarget,
          launchData.usedBatt
        );
        this.interceptors.push(missile);
        this.selectedTel = (readyTel.idx + 1) % this.tels.length;
        this.shake = 12.5;
        SFX.play("thaad_roar");
        this.setStatus(
          `THAAD AWAY! TEL-0${readyTel.idx + 1} (${readyTel.readyCells}/6 LEFT) -> ${this.lockedTarget.uid}`,
          Palette.RADAR_GREEN
        );
      }
    }

    attemptLaunchPac3() {
      if (this.gameOver) return;
      if (!this.powerTruck.connected) {
        SFX.play("alarm");
        this.setStatus("PAC-3 OFFLINE: CONNECT EPP-01 POWER FIRST! TAP [POWER LINK]", Palette.RED_ALERT);
        return;
      }
      if (!this.masterArmed) {
        SFX.play("alarm");
        this.setStatus("PAC-3 BLOCKED: MASTER ARM IS [SAFE]! TAP [SAFE -> ARMED]", Palette.RED_ALERT);
        return;
      }

      let tgt = (this.lockedTarget && this.threats.includes(this.lockedTarget)) ? this.lockedTarget : null;
      if (!tgt && this.threats.length > 0) {
        tgt = [...this.threats].sort((a, b) => b.pos.y - a.pos.y)[0];
        this.acquireTarget(tgt);
      }
      if (!tgt) {
        SFX.play("alarm");
        this.setStatus("PAC-3 STANDBY: NO INCOMING WARHEADS", Palette.AMBER);
        return;
      }

      const pac3 = this.pac3Launcher.fireOneCell(
        this.powerTruck.connected,
        tgt,
        this.smoke,
        this.fire,
        this.lights
      );
      if (pac3) {
        this.interceptors.push(pac3);
        this.shake = 7.5;
        this.setStatus(
          `PAC-3 MSE LAUNCHED! (${this.pac3Launcher.readyCells}/8 LEFT) -> ${tgt.uid}`,
          Palette.AMBER
        );
      } else {
        SFX.play("alarm");
        this.setStatus("PAC-3 LAUNCHER ELEVATING OR RELOADING...", Palette.AMBER);
      }
    }

    spawnThreat() {
      const aliveBases = this.bases.filter((b) => b.alive);
      if (aliveBases.length === 0) return;
      const targetB = randChoice(aliveBases);
      const targetX = targetB.x + randInt(-28, 28);

      const startX = randInt(890, SCREEN_WIDTH - 35);
      const startY = -15;
      const spd = 1.28 + this.wave * 0.12;

      const r = Math.random();
      let tt = ThreatType.SRBM;
      if (this.wave >= 3 && r < 0.22) tt = ThreatType.MARV;
      else if (this.wave >= 2 && r < 0.42) tt = ThreatType.HGV;
      else if (this.wave >= 2 && r < 0.66) tt = ThreatType.MIRV;
      else if (r < 0.45) tt = ThreatType.MRBM;

      const threat = new BallisticThreat(new Vec2(startX, startY), targetX, spd, tt);
      this.threats.push(threat);
      if (!this.lockedTarget && this.powerTruck.connected) {
        this.acquireTarget(threat);
      }
    }

    predictPip(tel, target) {
      if (!target || !target.alive) return null;
      const { muzzle } = tel.getMuzzleAndBreech();
      const dist = muzzle.distanceTo(target.pos);
      const tEst = dist / 15.0;
      return target.pos.add(target.vel.mul(tEst)).add(new Vec2(0, 0.5 * target.gravity * (tEst * tEst)));
    }

    _toCanvasCoords(clientX, clientY) {
      const rect = canvas.getBoundingClientRect();
      const scaleX = SCREEN_WIDTH / rect.width;
      const scaleY = SCREEN_HEIGHT / rect.height;
      return new Vec2((clientX - rect.left) * scaleX, (clientY - rect.top) * scaleY);
    }

    _handlePointerDown(pt) {
      SFX.unlock();

      if (this.gameOver) {
        this.reset();
        return;
      }

      if (pt.y < BATTLE_HEIGHT) {
        // 전장 좌측 EPP-01 전력공급차량 터치 시 전원 연결 토글
        if (Math.abs(pt.x - this.powerTruck.x) < 48 && Math.abs(pt.y - (GROUND_Y - 22)) < 35) {
          this.togglePowerLink();
          return;
        }
        // 전장 내 THAAD TEL 차량 터치 시 선택 전환
        for (let i = 0; i < this.tels.length; i++) {
          if (Math.abs(pt.x - this.tels[i].x) < 52 && Math.abs(pt.y - (GROUND_Y - 25)) < 45) {
            this.selectedTel = i;
            SFX.play("click");
            this.setStatus(`SELECTED THAAD HEMTT TEL-0${i + 1}`, Palette.CYAN);
            return;
          }
        }
        // 상공 탄도미사일 터치 시 락온
        if (this.threats.length > 0) {
          let nearest = this.threats[0];
          let minD = nearest.pos.distanceTo(pt);
          for (let i = 1; i < this.threats.length; i++) {
            const d = this.threats[i].pos.distanceTo(pt);
            if (d < minD) {
              minD = d;
              nearest = this.threats[i];
            }
          }
          if (minD < 115) {
            this.acquireTarget(nearest);
          }
        }
      } else {
        if (this.btnPower.contains(pt)) {
          this.togglePowerLink();
        } else if (this.btnErect.contains(pt)) {
          if (!this.powerTruck.connected) {
            SFX.play("alarm");
            this.setStatus("HYDRAULIC PUMP NO POWER: CONNECT EPP-01 FIRST [C]", Palette.RED_ALERT);
            return;
          }
          const newState = !this.tels.some((t) => t.targetErected);
          this.tels.forEach((t) => {
            t.targetErected = newState;
          });
          SFX.play("click");
          this.setStatus(
            newState ? "DEPLOYING OUTRIGGERS & ERECTING 6-CELL LAUNCHERS TO 74°..." : "STOWING LAUNCHER CANISTERS...",
            Palette.CYAN
          );
        } else if (this.btnBatt.contains(pt)) {
          if (!this.powerTruck.connected) {
            SFX.play("alarm");
            this.setStatus("BATTERY CHARGER NO POWER: CONNECT EPP-01 FIRST [C]", Palette.RED_ALERT);
          } else {
            this.holdingBattButton = true;
          }
        } else if (this.btnAutoprep.contains(pt)) {
          this.autoPrep = !this.autoPrep;
          if (this.autoPrep && this.powerTruck.connected) {
            this.tels.forEach((t) => {
              t.targetErected = true;
            });
          }
          SFX.play("click");
        } else if (this.btnLock.contains(pt)) {
          this.cycleTarget();
        } else if (this.btnLsamAuto.contains(pt)) {
          this.lsamAutoEnabled = !this.lsamAutoEnabled;
          SFX.play("click");
          this.setStatus(
            this.lsamAutoEnabled ? "L-SAM OUTER LAYER: AUTOMATIC ENGAGEMENT ENABLED" : "L-SAM OUTER LAYER: WEAPONS HOLD",
            Palette.MAGENTA
          );
        } else if (this.btnArm.contains(pt)) {
          this.masterArmed = !this.masterArmed;
          SFX.play("click");
          this.setStatus(
            this.masterArmed ? "MASTER ARM: LIVE [WEAPONS FREE — THAAD & PAC-3 READY]" : "MASTER ARM: SAFE",
            this.masterArmed ? Palette.RED_ALERT : Palette.CYAN
          );
        } else if (this.btnFire.contains(pt)) {
          this.attemptLaunchThaad();
        } else if (this.btnFirePac3.contains(pt)) {
          this.attemptLaunchPac3();
        } else {
          for (let idx = 0; idx < 2; idx++) {
            const bx = 596 + idx * 224;
            const by = CONSOLE_TOP + 48;
            if (pt.x >= bx && pt.x <= bx + 216 && pt.y >= by && pt.y <= by + 192) {
              this.selectedTel = idx;
              SFX.play("click");
            }
          }
        }
      }
    }

    _bindEvents() {
      window.addEventListener("keydown", (e) => {
        SFX.unlock();
        this.keys[e.code] = true;

        if (["Space", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Tab"].includes(e.code)) {
          e.preventDefault();
        }

        if (e.code === "KeyR" && this.gameOver) {
          this.reset();
        } else if (!this.gameOver) {
          if (e.code === "KeyC") {
            this.togglePowerLink();
          } else if (e.code === "KeyE") {
            if (!this.powerTruck.connected) {
              SFX.play("alarm");
              this.setStatus("HYDRAULIC PUMP NO POWER: CONNECT EPP-01 FIRST [C]", Palette.RED_ALERT);
              return;
            }
            const newState = !this.tels.some((t) => t.targetErected);
            this.tels.forEach((t) => {
              t.targetErected = newState;
            });
            SFX.play("click");
            this.setStatus(
              newState ? "DEPLOYING OUTRIGGERS & ERECTING 6-CELL LAUNCHERS TO 74°..." : "STOWING LAUNCHER CANISTERS...",
              Palette.CYAN
            );
          } else if (e.code === "KeyT") {
            this.autoPrep = !this.autoPrep;
            if (this.autoPrep && this.powerTruck.connected) {
              this.tels.forEach((t) => {
                t.targetErected = true;
              });
            }
            SFX.play("click");
          } else if (e.code === "KeyL") {
            this.lsamAutoEnabled = !this.lsamAutoEnabled;
            SFX.play("click");
          } else if (e.code === "KeyA") {
            this.masterArmed = !this.masterArmed;
            SFX.play("click");
            this.setStatus(
              this.masterArmed ? "MASTER ARM: LIVE [WEAPONS FREE]" : "MASTER ARM: SAFE",
              this.masterArmed ? Palette.RED_ALERT : Palette.CYAN
            );
          } else if (e.code === "Tab") {
            this.cycleTarget();
          } else if (e.code === "Space") {
            this.attemptLaunchThaad();
          } else if (e.code === "KeyX") {
            this.attemptLaunchPac3();
          } else if (e.code === "Digit1" || e.code === "Digit2") {
            this.selectedTel = e.code === "Digit1" ? 0 : 1;
            SFX.play("click");
          } else if (e.code === "KeyM") {
            SFX.muted = !SFX.muted;
          }
        }
      });

      window.addEventListener("keyup", (e) => {
        this.keys[e.code] = false;
      });

      canvas.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        this.pointerPos = this._toCanvasCoords(e.clientX, e.clientY);
        this._handlePointerDown(this.pointerPos);
      });

      canvas.addEventListener("pointermove", (e) => {
        e.preventDefault();
        this.pointerPos = this._toCanvasCoords(e.clientX, e.clientY);
      });

      const releaseHold = () => {
        this.holdingBattButton = false;
      };
      canvas.addEventListener("pointerup", releaseHold);
      canvas.addEventListener("pointercancel", releaseHold);
      canvas.addEventListener("pointerleave", releaseHold);
    }

    update() {
      if (this.gameOver) return;

      if (this.hitstop > 0) {
        this.hitstop -= 1;
        return;
      }

      this.shake *= 0.87;
      this.powerTruck.update();
      const pwrReady = this.powerTruck.connected;

      const manualCharge = Boolean((this.keys["KeyF"] || this.holdingBattButton) && pwrReady);
      if (manualCharge || (this.autoPrep && pwrReady)) {
        const rate = manualCharge ? 1.65 : 0.85;
        let chargedAny = false;
        this.tels.forEach((t) => {
          if (t.readyCells > 0 && t.thermalBatt < 100.0) {
            t.thermalBatt = Math.min(100.0, t.thermalBatt + rate);
            chargedAny = true;
          }
        });
        if (manualCharge && chargedAny) {
          this.humTimer += 1;
          if (this.humTimer % 7 === 0) SFX.play("batt_charge");
        }
      }

      if (pwrReady && this.tels.some((t) => t.elevationDeg > 0.5 && t.elevationDeg < 73.5)) {
        this.humTimer += 1;
        if (this.humTimer % 9 === 0) SFX.play("hydraulic_hum");
      }

      this.tels.forEach((t) => t.update(pwrReady));
      this.pac3Launcher.update(pwrReady);

      const autoLsamMissile = this.lsamLauncher.update(
        pwrReady,
        this.lsamAutoEnabled,
        this.threats,
        this.interceptors,
        this.smoke,
        this.fire,
        this.lights
      );
      if (autoLsamMissile) {
        this.interceptors.push(autoLsamMissile);
        this.setStatus(`L-SAM OUTER AUTO-FIRE -> ${autoLsamMissile.target.uid} (LOW PK)`, Palette.MAGENTA);
      }

      const activeTgt = this.threats.includes(this.lockedTarget) ? this.lockedTarget : null;
      this.radars.forEach((r) => r.update(activeTgt, pwrReady));

      // 초반 전원 연결 전까지 1웨이브 스폰 대기
      if (this.wave === 1 && !pwrReady && this.intercepts === 0) {
        this.spawnTimer = 90;
      } else if (this.toSpawn > 0) {
        this.spawnTimer -= 1;
        if (this.spawnTimer <= 0) {
          this.spawnThreat();
          this.toSpawn -= 1;
          this.spawnTimer = Math.max(58, 155 - this.wave * 10);
        }
      } else if (this.threats.length === 0) {
        this.waveCooldown += 1;
        if (this.waveCooldown === 1) {
          const aliveCnt = this.bases.filter((b) => b.alive).length;
          const bonus = aliveCnt * 350;
          this.score += bonus;
          this.setStatus(`WAVE ${this.wave} INTERCEPTED! DEFENSE BONUS +${bonus}`, Palette.RADAR_GREEN);
        }
        if (this.waveCooldown > 180) {
          this.wave += 1;
          this.toSpawn = 4 + this.wave * 2;
          this.waveCooldown = 0;
          this.setStatus(`EARLY WARNING: WAVE ${this.wave} (${this.toSpawn} WARHEADS) INBOUND!`, Palette.AMBER);
        }
      }

      if (pwrReady && this.threats.includes(this.lockedTarget)) {
        if (this.lockProgress < 1.0) {
          this.lockProgress = Math.min(1.0, this.lockProgress + 0.18);
        }
      } else {
        this.lockedTarget = null;
        this.lockProgress = 0.0;
        if (pwrReady && this.threats.length > 0) {
          this.acquireTarget([...this.threats].sort((a, b) => b.pos.y - a.pos.y)[0]);
        }
      }

      for (let i = this.threats.length - 1; i >= 0; i--) {
        const th = this.threats[i];
        th.update(this.smoke, this.interceptors);

        if (th.threatType === ThreatType.MIRV && !th.hasSplit && th.pos.y >= th.splitY) {
          th.hasSplit = true;
          th.alive = false;
          this.threats.splice(i, 1);
          this.shockwaves.push(new ShockwaveRing(th.pos, 38, Palette.MAGENTA, 20, 2));
          const aliveBases = this.bases.filter((b) => b.alive);
          if (aliveBases.length > 0) {
            for (let k = 0; k < 3; k++) {
              const tb = randChoice(aliveBases);
              const sub = new BallisticThreat(
                th.pos,
                tb.x + randInt(-25, 25),
                th.vel.length() * 1.08,
                ThreatType.SRBM
              );
              this.threats.push(sub);
            }
            this.setStatus("WARNING: MIRV BUS DEPLOYED 3 RE-ENTRY WARHEADS!", Palette.RED_ALERT);
          }
          continue;
        }

        if (th.pos.y >= GROUND_Y) {
          th.alive = false;
          this.threats.splice(i, 1);
          SFX.play("ground_impact");
          this.shake = 22.0;
          this.shockwaves.push(new ShockwaveRing(th.pos, 105, Palette.RED_ALERT, 40, 4));
          this.lights.push(new DynamicLight(th.pos, Palette.RED_ALERT, 1.5, 360, 34));
          for (let k = 0; k < 40; k++) {
            const ang = randRange(-Math.PI, 0);
            const spd = randRange(2.0, 9.5);
            this.sparks.push(new SparkStreak(
              th.pos,
              new Vec2(Math.cos(ang) * spd, Math.sin(ang) * spd),
              Palette.RED_ALERT,
              38
            ));
          }

          for (let bIdx = 0; bIdx < this.bases.length; bIdx++) {
            const b = this.bases[bIdx];
            if (b.alive && Math.abs(b.x - th.pos.x) < 75) {
              b.hp = Math.max(0, b.hp - 35);
              if (b.hp === 0) {
                b.alive = false;
                this.setStatus(`CRITICAL: ${b.name} DESTROYED BY BALLISTIC IMPACT!`, Palette.RED_ALERT);
              } else {
                const pct = Math.ceil((b.hp / b.maxHp) * 100);
                this.setStatus(`IMPACT ALERT: ${b.name} DAMAGED (${pct}% HP)`, Palette.AMBER);
              }
            }
          }
        }
      }

      if (!this.bases.some((b) => b.alive)) {
        this.gameOver = true;
      }

      for (let i = this.interceptors.length - 1; i >= 0; i--) {
        const m = this.interceptors[i];
        if (m.layer === "THAAD") {
          m.update(this.smoke, this.fire, this.sparks, this.debris);
        } else {
          m.update(this.smoke, this.fire);
        }

        if (m.hitSuccess) {
          SFX.play("kinetic_hit");
          this.hitstop = m.layer === "THAAD" ? 3 : 1;
          this.shake = m.layer === "THAAD" ? 15.0 : 9.0;
          const ringCol = m.layer === "LSAM" ? Palette.MAGENTA : (m.layer === "PAC3" ? Palette.AMBER : Palette.CYAN);
          this.shockwaves.push(new ShockwaveRing(m.pos, 72, ringCol, 28, 4));
          this.shockwaves.push(new ShockwaveRing(m.pos, 42, Palette.WHITE, 18, 2));
          this.lights.push(new DynamicLight(m.pos, ringCol, 1.4, 320, 26));

          const sparkCols = [ringCol, Palette.WHITE, Palette.AMBER];
          for (let k = 0; k < 34; k++) {
            const ang = randRange(0, Math.PI * 2);
            const spd = randRange(2.0, 10.5);
            this.sparks.push(new SparkStreak(
              m.pos,
              new Vec2(Math.cos(ang) * spd, Math.sin(ang) * spd),
              randChoice(sparkCols),
              32
            ));
          }
          for (let k = 0; k < 6; k++) {
            this.debris.push(new TumblingDebris(
              m.pos,
              new Vec2(randRange(-4.0, 4.0), randRange(-4.5, 1.5)),
              randInt(7, 13),
              3,
              [210, 220, 230],
              120
            ));
          }

          const tIdx = this.threats.indexOf(m.target);
          if (tIdx !== -1) {
            const t = this.threats[tIdx];
            t.alive = false;
            this.threats.splice(tIdx, 1);
            const ptsMap = {
              [ThreatType.SRBM]: 200,
              [ThreatType.MRBM]: 280,
              [ThreatType.MIRV]: 400,
              [ThreatType.HGV]: 500,
              [ThreatType.MARV]: 550
            };
            const pts = ptsMap[t.threatType] || 250;
            this.score += pts;
            this.intercepts += 1;
            this.callouts.push(new FloatingCallout(m.pos, `${m.layer} KILL! ${t.uid} (+${pts})`, Palette.RADAR_GREEN));
            this.setStatus(`${m.layer} INTERCEPT! ${t.uid} DESTROYED AT ${t.getAltitudeKm()}KM`, Palette.RADAR_GREEN);
          }
        }

        if (!m.active) {
          this.interceptors.splice(i, 1);
        }
      }

      if (this.smoke.length > 550) {
        this.smoke.splice(0, this.smoke.length - 550);
      }
      for (let i = this.smoke.length - 1; i >= 0; i--) {
        this.smoke[i].update(0.28);
        if (this.smoke[i].life <= 0) this.smoke.splice(i, 1);
      }
      for (let i = this.fire.length - 1; i >= 0; i--) {
        this.fire[i].update();
        if (this.fire[i].life <= 0) this.fire.splice(i, 1);
      }
      for (let i = this.sparks.length - 1; i >= 0; i--) {
        this.sparks[i].update();
        if (this.sparks[i].life <= 0) this.sparks.splice(i, 1);
      }
      for (let i = this.debris.length - 1; i >= 0; i--) {
        this.debris[i].update(this.smoke);
        if (this.debris[i].life <= 0) this.debris.splice(i, 1);
      }
      for (let i = this.shockwaves.length - 1; i >= 0; i--) {
        this.shockwaves[i].update();
        if (this.shockwaves[i].life <= 0) this.shockwaves.splice(i, 1);
      }
      for (let i = this.lights.length - 1; i >= 0; i--) {
        this.lights[i].update();
        if (this.lights[i].life <= 0) this.lights.splice(i, 1);
      }
      for (let i = this.callouts.length - 1; i >= 0; i--) {
        this.callouts[i].update();
        if (this.callouts[i].life <= 0) this.callouts.splice(i, 1);
      }
    }

    renderBattlefield(bctx) {
      bctx.drawImage(this.skySurf, 0, 0);

      for (let i = 0; i < this.stars.length; i++) {
        const st = this.stars[i];
        bctx.fillStyle = `rgb(${st.b},${st.b},${Math.min(255, st.b + 15)})`;
        bctx.fillRect(st.x, st.y, 1, 1);
      }

      const ridges = [
        { pts: this.ridgeFar, baseC: [14, 21, 34], rimC: [28, 42, 62] },
        { pts: this.ridgeNear, baseC: [22, 30, 42], rimC: [42, 56, 74] }
      ];

      for (let rIdx = 0; rIdx < ridges.length; rIdx++) {
        const { pts, baseC, rimC } = ridges[rIdx];
        bctx.fillStyle = rgb(baseC);
        bctx.beginPath();
        bctx.moveTo(0, GROUND_Y);
        for (let i = 0; i < pts.length; i++) {
          bctx.lineTo(pts[i].x, pts[i].y);
        }
        bctx.lineTo(SCREEN_WIDTH, GROUND_Y);
        bctx.closePath();
        bctx.fill();

        bctx.lineWidth = 2;
        for (let i = 0; i < pts.length - 1; i++) {
          const p1 = pts[i];
          const p2 = pts[i + 1];
          const mx = (p1.x + p2.x) * 0.5;
          const my = (p1.y + p2.y) * 0.5;
          let r = rimC[0];
          let g = rimC[1];
          let b = rimC[2];
          for (let l = 0; l < this.lights.length; l++) {
            const lt = this.lights[l];
            const d = Math.hypot(lt.pos.x - mx, lt.pos.y - my);
            if (d < lt.radius) {
              const f = Math.pow(1.0 - d / lt.radius, 1.6) * lt.strength * 0.8;
              r += lt.color[0] * f;
              g += lt.color[1] * f;
              b += lt.color[2] * f;
            }
          }
          bctx.strokeStyle = rgb(clampColor([r, g, b]));
          bctx.beginPath();
          bctx.moveTo(p1.x, p1.y);
          bctx.lineTo(p2.x, p2.y);
          bctx.stroke();
        }
      }

      bctx.fillStyle = rgb(Palette.DESERT_MID);
      bctx.fillRect(0, GROUND_Y, SCREEN_WIDTH, BATTLE_HEIGHT - GROUND_Y);
      bctx.strokeStyle = "rgb(88,92,98)";
      bctx.lineWidth = 2;
      bctx.beginPath();
      bctx.moveTo(0, GROUND_Y);
      bctx.lineTo(SCREEN_WIDTH, GROUND_Y);
      bctx.stroke();

      for (let i = 0; i < this.lights.length; i++) {
        const lt = this.lights[i];
        if (lt.pos.y > GROUND_Y - 120) {
          GlowCache.draw(bctx, lt.color, new Vec2(lt.pos.x, GROUND_Y), lt.radius * 0.75, Math.floor(130 * lt.strength));
        }
      }

      bctx.font = FONT_XS;
      bctx.textAlign = "center";
      bctx.textBaseline = "top";
      for (let i = 0; i < this.bases.length; i++) {
        const b = this.bases[i];
        const bx = b.x;
        if (!b.alive) {
          bctx.fillStyle = "rgb(45,34,36)";
          bctx.fillRect(bx - 38, GROUND_Y - 8, 76, 8);
          bctx.fillStyle = rgb(Palette.RED_ALERT);
          bctx.fillText("DESTROYED", bx, GROUND_Y + 5);
          continue;
        }
        const rx = bx - 36;
        const ry = GROUND_Y - 36;
        const hpPct = Math.ceil((b.hp / b.maxHp) * 100);
        const col = hpPct > 50 ? Palette.CYAN : Palette.AMBER;
        bctx.fillStyle = "rgb(26,38,56)";
        bctx.beginPath();
        bctx.roundRect(rx, ry, 72, 36, [3, 3, 0, 0]);
        bctx.fill();
        bctx.strokeStyle = rgb(col);
        bctx.lineWidth = 1;
        bctx.stroke();

        bctx.fillStyle = "rgb(135,220,255)";
        for (let wx = rx + 8; wx < rx + 64; wx += 12) {
          for (let wy = ry + 8; wy < ry + 30; wy += 10) {
            bctx.fillRect(wx, wy, 5, 4);
          }
        }
        bctx.fillStyle = rgb(col);
        bctx.fillText(`${b.name} (${hpPct}%)`, bx, GROUND_Y + 5);
      }

      const pwrReady = this.powerTruck.connected;
      this.powerTruck.drawPowerCables(bctx, [
        this.lsamLauncher.getPowerPort(),
        this.tels[0].getPowerPort(),
        this.radars[0].getPowerPort(),
        this.tels[1].getPowerPort(),
        this.radars[1].getPowerPort(),
        this.pac3Launcher.getPowerPort()
      ]);

      this.powerTruck.draw(bctx);
      this.lsamLauncher.draw(bctx, pwrReady, this.lsamAutoEnabled);
      for (let i = 0; i < this.radars.length; i++) {
        this.radars[i].draw(bctx, pwrReady && this.lockProgress >= 1.0, pwrReady);
      }
      for (let i = 0; i < this.tels.length; i++) {
        this.tels[i].draw(bctx, i === this.selectedTel, pwrReady);
      }
      this.pac3Launcher.draw(bctx, pwrReady);

      for (let i = 0; i < this.smoke.length; i++) this.smoke[i].draw(bctx, this.lights);
      for (let i = 0; i < this.debris.length; i++) this.debris[i].draw(bctx);
      for (let i = 0; i < this.threats.length; i++) this.threats[i].draw(bctx);
      for (let i = 0; i < this.interceptors.length; i++) this.interceptors[i].draw(bctx);
      for (let i = 0; i < this.fire.length; i++) this.fire[i].draw(bctx);
      for (let i = 0; i < this.shockwaves.length; i++) this.shockwaves[i].draw(bctx);
      for (let i = 0; i < this.sparks.length; i++) this.sparks[i].draw(bctx);

      const lt = this.lockedTarget;
      if (pwrReady && lt && this.threats.includes(lt)) {
        const locked = this.lockProgress >= 1.0;
        const col = locked ? Palette.RADAR_GREEN : Palette.AMBER;
        const br = Math.floor(28 - this.lockProgress * 12);
        const cx = Math.floor(lt.pos.x);
        const cy = Math.floor(lt.pos.y);

        bctx.strokeStyle = rgb(col);
        bctx.lineWidth = 2;
        bctx.strokeRect(cx - br, cy - br, br * 2, br * 2);

        const tag = `${lt.uid} [${lt.threatType}] | M${lt.getMach()} | ${lt.getAltitudeKm()}KM`;
        bctx.font = FONT_XS;
        bctx.textAlign = "left";
        bctx.textBaseline = "top";
        bctx.fillStyle = rgb(col);
        bctx.fillText(tag, cx + br + 6, cy - 10);

        if (locked) {
          const pip = this.predictPip(this.tels[this.selectedTel], lt);
          if (pip) {
            const px = Math.floor(pip.x);
            const py = Math.floor(pip.y);
            bctx.strokeStyle = "rgb(38,120,88)";
            bctx.lineWidth = 1;
            bctx.beginPath();
            bctx.moveTo(lt.pos.x, lt.pos.y);
            bctx.lineTo(pip.x, pip.y);
            bctx.stroke();

            bctx.strokeStyle = rgb(Palette.CYAN);
            bctx.beginPath();
            bctx.arc(px, py, 8, 0, Math.PI * 2);
            bctx.stroke();

            bctx.beginPath();
            bctx.moveTo(px - 11, py);
            bctx.lineTo(px + 11, py);
            bctx.moveTo(px, py - 11);
            bctx.lineTo(px, py + 11);
            bctx.stroke();
          }
        }
      }

      for (let i = 0; i < this.callouts.length; i++) this.callouts[i].draw(bctx);

      bctx.fillStyle = "rgba(8,12,20,0.8)";
      bctx.fillRect(0, 0, SCREEN_WIDTH, 30);

      bctx.font = FONT_MD;
      bctx.textAlign = "left";
      bctx.textBaseline = "top";
      bctx.fillStyle = rgb(Palette.WHITE);
      bctx.fillText(`SCORE: ${String(this.score).padStart(6, "0")}`, 18, 7);

      bctx.fillStyle = rgb(Palette.RADAR_GREEN);
      bctx.fillText(`INTERCEPTS: ${this.intercepts}`, 185, 7);

      bctx.fillStyle = rgb(Palette.CYAN);
      bctx.fillText(`WAVE: ${String(this.wave).padStart(2, "0")}`, 355, 7);

      bctx.font = FONT_XS;
      bctx.fillStyle = "rgb(155,180,205)";
      const guide = "[C] POWER  |  [E] ERECT THAAD  |  [F] CHARGE BATT  |  [A] ARM  |  [SPACE] THAAD  |  [X] PAC-3  |  L-SAM: AUTO";
      bctx.fillText(guide, 480, 9);
    }

    renderConsole() {
      ctx.fillStyle = rgb(Palette.PANEL_BG);
      ctx.fillRect(0, CONSOLE_TOP, SCREEN_WIDTH, CONSOLE_HEIGHT);

      ctx.strokeStyle = "rgb(85,105,130)";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(0, CONSOLE_TOP);
      ctx.lineTo(SCREEN_WIDTH, CONSOLE_TOP);
      ctx.stroke();

      // 상태 메시지 티커
      const tx = 20;
      const ty = CONSOLE_TOP + 10;
      const tw = SCREEN_WIDTH - 40;
      const th = 30;
      ctx.fillStyle = rgb(Palette.PANEL_DARK);
      ctx.beginPath();
      ctx.roundRect(tx, ty, tw, th, 5);
      ctx.fill();
      ctx.strokeStyle = rgb(Palette.PANEL_BORDER);
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.font = FONT_MD;
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillStyle = rgb(this.statusCol);
      ctx.fillText(`>> ${this.statusMsg}`, tx + 12, ty + 7);

      // 좌측: 다층 방공 통합 고각 섹터 레이더 스코프
      const sx = 20;
      const sy = CONSOLE_TOP + 48;
      const sw = 250;
      const sh = 192;
      ctx.fillStyle = "rgb(9,17,16)";
      ctx.beginPath();
      ctx.roundRect(sx, sy, sw, sh, 6);
      ctx.fill();
      ctx.strokeStyle = rgb(Palette.PANEL_BORDER);
      ctx.lineWidth = 1;
      ctx.stroke();

      const ox = sx + 22;
      const oy = sy + sh - 16;
      const layerRings = [
        { r: 70, col: "rgba(255,185,40,0.28)" },
        { r: 140, col: "rgba(0,230,255,0.28)" },
        { r: 205, col: "rgba(215,80,255,0.28)" }
      ];
      layerRings.forEach((lr) => {
        ctx.strokeStyle = lr.col;
        ctx.beginPath();
        ctx.arc(ox, oy, lr.r, -Math.PI * 0.5, 0);
        ctx.stroke();
      });

      ctx.strokeStyle = "rgb(24,80,56)";
      ctx.beginPath();
      ctx.moveTo(ox, oy);
      ctx.lineTo(sx + sw - 10, oy);
      ctx.moveTo(ox, oy);
      ctx.lineTo(ox, sy + 12);
      ctx.stroke();

      if (this.powerTruck.connected) {
        for (let i = 0; i < this.threats.length; i++) {
          const th = this.threats[i];
          const px = Math.floor(ox + (th.pos.x / SCREEN_WIDTH) * 212);
          const py = Math.floor(oy - ((GROUND_Y - th.pos.y) / GROUND_Y) * 155);
          if (px >= sx && px <= sx + sw && py >= sy && py <= sy + sh) {
            ctx.fillStyle = rgb(Palette.RED_ALERT);
            ctx.beginPath();
            ctx.arc(px, py, 3, 0, Math.PI * 2);
            ctx.fill();
            if (th === this.lockedTarget) {
              ctx.strokeStyle = rgb(Palette.RADAR_GREEN);
              ctx.beginPath();
              ctx.arc(px, py, 6, 0, Math.PI * 2);
              ctx.stroke();
            }
          }
        }
        for (let i = 0; i < this.interceptors.length; i++) {
          const m = this.interceptors[i];
          const px = Math.floor(ox + (m.pos.x / SCREEN_WIDTH) * 212);
          const py = Math.floor(oy - ((GROUND_Y - m.pos.y) / GROUND_Y) * 155);
          if (px >= sx && px <= sx + sw && py >= sy && py <= sy + sh) {
            ctx.fillStyle = rgb(m.layer === "LSAM" ? Palette.MAGENTA : (m.layer === "PAC3" ? Palette.AMBER : Palette.CYAN));
            ctx.beginPath();
            ctx.arc(px, py, 2.2, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }

      ctx.font = FONT_XS;
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillStyle = rgb(this.powerTruck.connected ? Palette.RADAR_GREEN : Palette.RED_ALERT);
      ctx.fillText(this.powerTruck.connected ? "MULTI-LAYER BMD SCOPE" : "RADARS OFFLINE [NO PWR]", sx + 10, sy + 8);

      // 중앙 제어 스위치들 (다음 필요한 조작 단계에 황금색 가이드 테두리 표시)
      let nextStep = null;
      if (!this.powerTruck.connected) {
        nextStep = "POWER";
      } else if (!this.tels.some((t) => t.isErected)) {
        nextStep = "ERECT";
      } else if (!this.tels.some((t) => t.thermalBatt >= 80.0 && t.readyCells > 0)) {
        nextStep = "BATT";
      } else if (!this.masterArmed) {
        nextStep = "ARM";
      } else if (this.threats.length > 0 && this.lockProgress >= 1.0) {
        nextStep = "FIRE";
      }

      this.btnPower.draw(
        ctx,
        this.btnPower.contains(this.pointerPos),
        this.powerTruck.connected,
        this.powerTruck.connected ? "PWR: LINKED" : "POWER LINK",
        this.powerTruck.connected ? "ALL UNITS ON" : "1. TAP TO CONNECT",
        nextStep === "POWER"
      );

      const anyErecting = this.tels.some((t) => t.targetErected);
      this.btnErect.draw(
        ctx,
        this.btnErect.contains(this.pointerPos),
        anyErecting && this.powerTruck.connected,
        anyErecting ? "STOW TEL" : "ERECT TEL",
        `ANGLE: ${Math.floor(this.tels[this.selectedTel].elevationDeg)}° / 74°`,
        nextStep === "ERECT"
      );

      const charging = Boolean((this.keys["KeyF"] || this.holdingBattButton) && this.powerTruck.connected);
      this.btnBatt.draw(
        ctx,
        this.btnBatt.contains(this.pointerPos),
        charging,
        null,
        null,
        nextStep === "BATT"
      );

      this.btnAutoprep.draw(
        ctx,
        this.btnAutoprep.contains(this.pointerPos),
        this.autoPrep && this.powerTruck.connected,
        `AUTO: ${this.autoPrep ? "ON" : "OFF"}`
      );
      this.btnLock.draw(ctx, this.btnLock.contains(this.pointerPos), this.lockProgress >= 1.0);
      this.btnLsamAuto.draw(
        ctx,
        this.btnLsamAuto.contains(this.pointerPos),
        this.lsamAutoEnabled && this.powerTruck.connected,
        this.lsamAutoEnabled ? "L-SAM: AUTO" : "L-SAM: HOLD",
        `OUTER (${this.lsamLauncher.readyCells}/4)`
      );

      // 중앙 우측: THAAD TEL-01 & TEL-02 6연장 발사관 셀 매트릭스 (3x2)
      for (let idx = 0; idx < this.tels.length; idx++) {
        const tel = this.tels[idx];
        const bx = 596 + idx * 224;
        const by = CONSOLE_TOP + 48;
        const bw = 216;
        const bh = 192;
        const sel = idx === this.selectedTel;

        ctx.fillStyle = rgb(Palette.PANEL_DARK);
        ctx.beginPath();
        ctx.roundRect(bx, by, bw, bh, 6);
        ctx.fill();

        ctx.strokeStyle = rgb(sel ? Palette.RADAR_GREEN : Palette.PANEL_BORDER);
        ctx.lineWidth = sel ? 2 : 1;
        ctx.stroke();

        ctx.font = FONT_SM;
        ctx.textAlign = "left";
        ctx.textBaseline = "top";
        ctx.fillStyle = rgb(sel ? Palette.RADAR_GREEN : Palette.WHITE);
        ctx.fillText(`THAAD TEL-0${idx + 1}`, bx + 10, by + 8);

        ctx.font = FONT_XS;
        ctx.textAlign = "right";
        ctx.fillStyle = rgb(tel.isErected ? Palette.CYAN : Palette.AMBER);
        ctx.fillText(`EL:${tel.elevationDeg.toFixed(0)}°`, bx + bw - 10, by + 10);

        for (let cI = 0; cI < 6; cI++) {
          const loaded = tel.cellsLoaded[cI];
          const cx = bx + 12 + (cI % 3) * 66;
          const cy = by + 34 + Math.floor(cI / 3) * 32;
          const cw = 60;
          const ch = 26;
          const cCol = loaded ? Palette.RADAR_GREEN : [45, 50, 58];

          ctx.fillStyle = loaded ? "rgb(22,32,30)" : "rgb(18,20,24)";
          ctx.beginPath();
          ctx.roundRect(cx, cy, cw, ch, 3);
          ctx.fill();
          ctx.strokeStyle = rgb(cCol);
          ctx.lineWidth = 1;
          ctx.stroke();

          ctx.font = FONT_XS;
          ctx.textAlign = "center";
          ctx.textBaseline = "top";
          ctx.fillStyle = rgb(cCol);
          ctx.fillText(loaded ? `MSL-0${cI + 1}` : "EMPTY", cx + cw / 2, cy + 7);
        }

        const barX = bx + 12;
        const barY = by + 108;
        const barW = bw - 24;
        const barH = 26;
        ctx.fillStyle = "rgb(22,28,36)";
        ctx.beginPath();
        ctx.roundRect(barX, barY, barW, barH, 3);
        ctx.fill();

        const fw = Math.floor(barW * (tel.thermalBatt / 100.0));
        if (fw > 0) {
          const fc = tel.thermalBatt >= 98 ? Palette.CYAN : (tel.thermalBatt >= 80 ? Palette.RADAR_GREEN : Palette.AMBER);
          ctx.fillStyle = rgb(fc);
          ctx.beginPath();
          ctx.roundRect(barX, barY, fw, barH, 3);
          ctx.fill();
        }

        const minX = barX + Math.floor(barW * 0.8);
        ctx.strokeStyle = rgb(Palette.RED_ALERT);
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(minX, barY);
        ctx.lineTo(minX, barY + barH);
        ctx.stroke();

        ctx.strokeStyle = rgb(Palette.PANEL_BORDER);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(barX, barY, barW, barH, 3);
        ctx.stroke();

        ctx.font = FONT_XS;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = rgb(Palette.WHITE);
        ctx.fillText(`THERMAL BATT: ${Math.floor(tel.thermalBatt)}%`, barX + barW / 2, barY + 7);

        let stStr;
        let stCol;
        if (!this.powerTruck.connected) {
          stStr = "OFFLINE — LINK EPP-01";
          stCol = Palette.RED_ALERT;
        } else if (tel.readyCells === 0) {
          stStr = `REARMING (${Math.floor(tel.reloadTimer * 100)}%)`;
          stCol = Palette.AMBER;
        } else if (!tel.isErected) {
          stStr = "STOWED — TAP [ERECT TEL]";
          stCol = Palette.AMBER;
        } else if (tel.thermalBatt < 80.0) {
          stStr = "LOW BATT — HOLD [F]";
          stCol = Palette.AMBER;
        } else {
          stStr = "READY FOR INTERCEPT";
          stCol = Palette.RADAR_GREEN;
        }
        ctx.fillStyle = rgb(stCol);
        ctx.fillText(stStr, bx + bw / 2, by + bh - 26);
      }

      // 보조 방공망 상태 패널: 최외곽 L-SAM (자동) & 하층 PAC-3 MSE (수동)
      const auxX = 1044;
      const auxW = 186;
      const lsamY = CONSOLE_TOP + 48;
      const lsamH = 92;

      ctx.fillStyle = rgb(Palette.PANEL_DARK);
      ctx.beginPath();
      ctx.roundRect(auxX, lsamY, auxW, lsamH, 6);
      ctx.fill();
      ctx.strokeStyle = rgb(Palette.MAGENTA);
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.font = FONT_XS;
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillStyle = rgb(Palette.MAGENTA);
      ctx.fillText("L-SAM-01 [OUTER AUTO]", auxX + 10, lsamY + 8);

      for (let i = 0; i < 4; i++) {
        const loaded = this.lsamLauncher.cellsLoaded[i];
        const cx = auxX + 12 + i * 42;
        const cy = lsamY + 30;
        ctx.fillStyle = loaded ? "rgba(215,80,255,0.22)" : "rgb(20,22,28)";
        ctx.fillRect(cx, cy, 36, 22);
        ctx.strokeStyle = rgb(loaded ? Palette.MAGENTA : [50, 56, 65]);
        ctx.strokeRect(cx, cy, 36, 22);
      }
      ctx.textAlign = "center";
      const lsamSt = !this.powerTruck.connected
        ? "OFFLINE"
        : (this.lsamLauncher.readyCells === 0 ? `RELOAD ${Math.floor(this.lsamLauncher.reloadTimer * 100)}%` : "AUTO-FIRE (~45% PK)");
      ctx.fillStyle = rgb(this.powerTruck.connected ? Palette.RADAR_GREEN : Palette.RED_ALERT);
      ctx.fillText(lsamSt, auxX + auxW / 2, lsamY + 62);

      // 하층 PAC-3 MSE 패널
      const pacY = CONSOLE_TOP + 148;
      const pacH = 92;
      ctx.fillStyle = rgb(Palette.PANEL_DARK);
      ctx.beginPath();
      ctx.roundRect(auxX, pacY, auxW, pacH, 6);
      ctx.fill();
      ctx.strokeStyle = rgb(Palette.AMBER);
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.textAlign = "left";
      ctx.fillStyle = rgb(Palette.AMBER);
      ctx.fillText("PAC-3 MSE [MANUAL X]", auxX + 10, pacY + 8);

      for (let i = 0; i < 8; i++) {
        const loaded = this.pac3Launcher.cellsLoaded[i];
        const cx = auxX + 12 + i * 21;
        const cy = pacY + 30;
        ctx.fillStyle = loaded ? "rgba(255,185,40,0.28)" : "rgb(20,22,28)";
        ctx.fillRect(cx, cy, 17, 22);
        ctx.strokeStyle = rgb(loaded ? Palette.AMBER : [50, 56, 65]);
        ctx.strokeRect(cx, cy, 17, 22);
      }
      ctx.textAlign = "center";
      const pacSt = !this.powerTruck.connected
        ? "OFFLINE"
        : (this.pac3Launcher.readyCells === 0 ? `RELOAD ${Math.floor(this.pac3Launcher.reloadTimer * 100)}%` : "READY — TAP [FIRE PAC-3]");
      ctx.fillStyle = rgb(this.powerTruck.connected ? Palette.AMBER : Palette.RED_ALERT);
      ctx.fillText(pacSt, auxX + auxW / 2, pacY + 62);

      // 우측 끝: Master Arm + THAAD 발사 + PAC-3 발사 스위치
      this.btnArm.draw(
        ctx,
        this.btnArm.contains(this.pointerPos),
        this.masterArmed,
        this.masterArmed ? "ARMED" : "SAFE",
        null,
        nextStep === "ARM"
      );
      const canFireThaad =
        this.powerTruck.connected &&
        this.masterArmed &&
        this.lockProgress >= 1.0 &&
        this.tels.some((t) => t.isReadyToFire(this.powerTruck.connected));
      this.btnFire.draw(
        ctx,
        this.btnFire.contains(this.pointerPos),
        canFireThaad,
        null,
        null,
        nextStep === "FIRE" && canFireThaad
      );

      const canFirePac3 =
        this.powerTruck.connected &&
        this.masterArmed &&
        this.pac3Launcher.isReadyToFire(this.powerTruck.connected) &&
        this.threats.length > 0;
      this.btnFirePac3.draw(
        ctx,
        this.btnFirePac3.contains(this.pointerPos),
        canFirePac3,
        null,
        null,
        nextStep === "FIRE" && !canFireThaad && canFirePac3
      );
    }

    render() {
      this.renderBattlefield(this.battleCtx);

      const sx = this.shake > 0.5 ? randRange(-this.shake, this.shake) : 0.0;
      const sy = this.shake > 0.5 ? randRange(-this.shake, this.shake) : 0.0;

      ctx.fillStyle = "#000";
      ctx.fillRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT);
      ctx.drawImage(this.battleCanvas, Math.floor(sx), Math.floor(sy));

      this.renderConsole();

      if (this.gameOver) {
        ctx.fillStyle = "rgba(6,8,14,0.8)";
        ctx.fillRect(0, 0, SCREEN_WIDTH, BATTLE_HEIGHT);

        ctx.textAlign = "center";
        ctx.textBaseline = "top";

        ctx.font = FONT_XL;
        ctx.fillStyle = rgb(Palette.RED_ALERT);
        ctx.fillText("DEFENDED SECTOR OVERRUN", SCREEN_WIDTH / 2, BATTLE_HEIGHT / 2 - 70);

        ctx.font = FONT_LG;
        ctx.fillStyle = rgb(Palette.WHITE);
        ctx.fillText(
          `FINAL SCORE: ${this.score}   |   TOTAL INTERCEPTS: ${this.intercepts}`,
          SCREEN_WIDTH / 2,
          BATTLE_HEIGHT / 2 - 5
        );

        ctx.font = FONT_MD;
        ctx.fillStyle = rgb(Palette.CYAN);
        ctx.fillText("TAP SCREEN OR PRESS [R] TO REDEPLOY BMD BATTERY", SCREEN_WIDTH / 2, BATTLE_HEIGHT / 2 + 48);
      }
    }

    start() {
      let lastTime = performance.now();
      let accumulator = 0;

      const loop = (now) => {
        const dt = Math.min(now - lastTime, 100);
        lastTime = now;
        accumulator += dt;

        while (accumulator >= FRAME_MS) {
          this.update();
          accumulator -= FRAME_MS;
        }

        this.render();
        requestAnimationFrame(loop);
      };

      requestAnimationFrame(loop);
    }
  }

  window.addEventListener("load", () => {
    const sim = new THAADCommandSim();
    sim.start();
  });
})();
</script>
</body>
</html>