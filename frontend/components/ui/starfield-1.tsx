"use client";

import React, { useEffect, useRef } from "react";

interface StarfieldProps {
  starColor?: string;
  bgColor?: string;
  mouseAdjust?: boolean;
  easing?: number;
  speed?: number;
  quantity?: number;
  opacity?: number;
  hyperspace?: boolean;
  warpFactor?: number;
}

interface SD {
  w: number;
  h: number;
  ctx: CanvasRenderingContext2D | null;
  cw: number;
  ch: number;
  x: number;
  y: number;
  z: number;
  star: { colorRatio: number; arr: number[][] };
  prevTime: number;
}

export function Starfield({
  starColor  = "rgba(255,255,255,1)",
  bgColor    = "rgba(0,0,0,1)",
  mouseAdjust = false,
  easing     = 1,
  speed      = 1,
  quantity   = 512,
  opacity    = 0.1,
  hyperspace = false,
  warpFactor = 10,
}: StarfieldProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const mouse  = { x: 0, y: 0 };
    const cursor = { x: 0, y: 0 };
    let raf: number;

    const compSpeed = hyperspace ? speed * warpFactor : speed;
    const fillColor = hyperspace ? `rgba(0,0,0,${opacity})` : bgColor;
    const ratio     = quantity / 2;

    const sd: SD = {
      w: 0, h: 0, ctx: null, cw: 0, ch: 0,
      x: 0, y: 0, z: 0,
      star: { colorRatio: 0, arr: [] },
      prevTime: 0,
    };

    const measure = () => {
      const el = canvas.parentElement;
      if (!el) return;
      sd.w = el.clientWidth;
      sd.h = el.clientHeight;
      sd.x = Math.round(sd.w / 2);
      sd.y = Math.round(sd.h / 2);
      sd.z = (sd.w + sd.h) / 2;
      sd.star.colorRatio = 1 / sd.z;
      if (!cursor.x && !cursor.y) { cursor.x = sd.x; cursor.y = sd.y; }
      if (!mouse.x && !mouse.y)   { mouse.x = cursor.x - sd.x; mouse.y = cursor.y - sd.y; }
    };

    const setupCanvas = () => {
      measure();
      sd.ctx = canvas.getContext("2d");
      canvas.width  = sd.w;
      canvas.height = sd.h;
      if (sd.ctx) {
        sd.ctx.fillStyle   = fillColor;
        sd.ctx.strokeStyle = starColor;
      }
    };

    const bigBang = () => {
      sd.star.arr = Array.from({ length: quantity }, () => [
        Math.random() * sd.w * 2 - sd.x * 2,
        Math.random() * sd.h * 2 - sd.y * 2,
        Math.round(Math.random() * sd.z),
        0, 0, 0, 0, 1,
      ]);
    };

    const resize = () => {
      const el = canvas.parentElement;
      if (!el) return;
      const newW = el.clientWidth;
      const newH = el.clientHeight;
      if (sd.cw === newW && sd.ch === newH) return;
      const rw = newW / (sd.cw || newW);
      const rh = newH / (sd.ch || newH);
      sd.cw = sd.w = newW;
      sd.ch = sd.h = newH;
      sd.x = Math.round(sd.w / 2);
      sd.y = Math.round(sd.h / 2);
      sd.z = (sd.w + sd.h) / 2;
      sd.star.colorRatio = 1 / sd.z;
      canvas.width  = sd.w;
      canvas.height = sd.h;
      sd.star.arr = sd.star.arr.map((s) => {
        const n = [...s];
        n[0] = s[0] * rw;
        n[1] = s[1] * rh;
        n[3] = sd.x + (n[0] / n[2]) * ratio;
        n[4] = sd.y + (n[1] / n[2]) * ratio;
        return n;
      });
      if (sd.ctx) {
        sd.ctx.fillStyle   = fillColor;
        sd.ctx.strokeStyle = starColor;
      }
    };

    const update = () => {
      mouse.x = (cursor.x - sd.x) / easing;
      mouse.y = (cursor.y - sd.y) / easing;
      sd.star.arr = sd.star.arr.map((s) => {
        const n = [...s];
        n[7] = 1;
        n[5] = n[3]; n[6] = n[4];
        n[0] += mouse.x >> 4;
        if (n[0] > sd.x << 1)  { n[0] -= sd.w << 1; n[7] = 0; }
        if (n[0] < -(sd.x << 1)) { n[0] += sd.w << 1; n[7] = 0; }
        n[1] += mouse.y >> 4;
        if (n[1] > sd.y << 1)  { n[1] -= sd.h << 1; n[7] = 0; }
        if (n[1] < -(sd.y << 1)) { n[1] += sd.h << 1; n[7] = 0; }
        n[2] -= compSpeed;
        if (n[2] > sd.z) { n[2] -= sd.z; n[7] = 0; }
        if (n[2] < 0)    { n[2] += sd.z; n[7] = 0; }
        n[3] = sd.x + (n[0] / n[2]) * ratio;
        n[4] = sd.y + (n[1] / n[2]) * ratio;
        return n;
      });
    };

    const draw = () => {
      const ctx = sd.ctx;
      if (!ctx) return;
      ctx.fillStyle = fillColor;
      ctx.fillRect(0, 0, sd.w, sd.h);
      ctx.strokeStyle = starColor;
      for (const s of sd.star.arr) {
        if (s[5] > 0 && s[5] < sd.w && s[6] > 0 && s[6] < sd.h && s[7]) {
          ctx.lineWidth = (1 - sd.star.colorRatio * s[2]) * 2;
          ctx.beginPath();
          ctx.moveTo(s[5], s[6]);
          ctx.lineTo(s[3], s[4]);
          ctx.stroke();
          ctx.closePath();
        }
      }
    };

    const animate = () => {
      resize();
      update();
      draw();
      raf = requestAnimationFrame(animate);
    };

    const onMouseMove = (e: MouseEvent) => {
      const el = canvas.parentElement;
      if (!el) return;
      cursor.x = e.pageX || e.clientX + el.scrollLeft - el.clientLeft;
      cursor.y = e.pageY || e.clientY + el.scrollTop  - el.clientTop;
    };

    setupCanvas();
    bigBang();
    animate();
    if (mouseAdjust) canvas.parentElement?.addEventListener("mousemove", onMouseMove);

    return () => {
      cancelAnimationFrame(raf);
      if (mouseAdjust) canvas.parentElement?.removeEventListener("mousemove", onMouseMove);
    };
  }, [starColor, bgColor, mouseAdjust, easing, speed, quantity, opacity, hyperspace, warpFactor]);

  return (
    <div style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
      <canvas ref={canvasRef} style={{ display: "block", width: "100%", height: "100%" }} />
    </div>
  );
}
