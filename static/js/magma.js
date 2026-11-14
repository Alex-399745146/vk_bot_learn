(() => {
  "use strict";

  const canvas = document.getElementById("magma-particles");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  // Уважаем настройку «уменьшить движение».
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const DPR = Math.min(window.devicePixelRatio || 1, 2);
  const MAX_PARTICLES = 85;

  let width = 0;
  let height = 0;
  let particles = [];
  let rafId = 0;
  let lastTime = 0;

  const sprite = createSprite();

  function createSprite() {
    const size = 64;
    const surface = document.createElement("canvas");
    surface.width = size;
    surface.height = size;

    const brush = surface.getContext("2d");
    const gradient = brush.createRadialGradient(
      size / 2, size * 0.72, 0,
      size / 2, size * 0.5, size / 2,
    );
    gradient.addColorStop(0.0, "rgba(255, 255, 235, 1)");
    gradient.addColorStop(0.18, "rgba(255, 224, 130, .95)");
    gradient.addColorStop(0.45, "rgba(255, 120, 20, .55)");
    gradient.addColorStop(1.0, "rgba(255, 60, 0, 0)");

    brush.fillStyle = gradient;
    brush.fillRect(0, 0, size, size);
    return surface;
  }

  function particleCount() {
    return Math.max(18, Math.min(MAX_PARTICLES, Math.round((width * height) / 28000)));
  }

  function resetParticle(particle, initial = false) {
    particle.x = Math.random() * width;
    particle.y = initial
      ? Math.random() * height
      : height + Math.random() * height * 0.15;
    particle.size = 1.2 + Math.random() * 3.2;
    particle.speed = 14 + Math.random() * 44;
    particle.alpha = 0.25 + Math.random() * 0.55;
    particle.phase = Math.random() * Math.PI * 2;
    particle.frequency = 0.4 + Math.random() * 0.9;
    particle.drift = 6 + Math.random() * 18;
    return particle;
  }

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;

    canvas.width = Math.round(width * DPR);
    canvas.height = Math.round(height * DPR);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);

    particles = Array.from({ length: particleCount() }, () => resetParticle({}, true));
  }

  function frame(now) {
    rafId = 0;
    if (document.hidden) return;

    if (!lastTime) lastTime = now;
    const delta = Math.min((now - lastTime) / 1000, 0.05);
    lastTime = now;

    ctx.clearRect(0, 0, width, height);
    ctx.globalCompositeOperation = "lighter";

    for (const particle of particles) {
      particle.y -= particle.speed * delta;
      particle.phase += particle.frequency * delta;

      if (particle.y < -30) {
        resetParticle(particle);
        continue;
      }

      const x = particle.x + Math.sin(particle.phase) * particle.drift * 0.35;
      const flicker = 0.65 + Math.sin(particle.phase * 2.1) * 0.25;

      ctx.globalAlpha = particle.alpha * flicker;
      const particleWidth = particle.size * 2.4;
      const particleHeight = particle.size * 4.8;
      ctx.drawImage(
        sprite,
        x - particleWidth / 2,
        particle.y - particleHeight / 2,
        particleWidth,
        particleHeight,
      );
    }

    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
    rafId = requestAnimationFrame(frame);
  }

  function start() {
    if (!rafId) {
      lastTime = 0;
      rafId = requestAnimationFrame(frame);
    }
  }

  function stop() {
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = 0;
    }
  }

  resize();
  start();

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
    else start();
  });

  let resizeTimer = 0;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      stop();
      resize();
      start();
    }, 200);
  });
})();
