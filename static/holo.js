// ═══════════════════════════════════════════════
//  N E X U S  —  3D Wireframe Globe
//  Red & Gold theme
// ═══════════════════════════════════════════════

(function () {
  const canvas = document.getElementById('globe-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  let W, H, cx, cy, radius;
  let rotY = 0;
  let mouseOffsetX = 0;

  function resize() {
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    W = rect.width;
    H = rect.height;
    cx = W / 2;
    cy = H / 2;
    radius = Math.min(W, H) * 0.36;
  }

  window.addEventListener('resize', resize);

  canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    mouseOffsetX = ((e.clientX - rect.left) / W - 0.5) * 2;
  });

  // Project 3D point to 2D
  function project(lat, lon, r) {
    const latRad = (lat * Math.PI) / 180;
    const lonRad = (lon * Math.PI) / 180;

    const x = r * Math.cos(latRad) * Math.sin(lonRad);
    const y = -r * Math.sin(latRad);
    const z = r * Math.cos(latRad) * Math.cos(lonRad);

    // Rotate around Y
    const cosR = Math.cos(rotY);
    const sinR = Math.sin(rotY);
    const rx = x * cosR - z * sinR;
    const rz = x * sinR + z * cosR;

    // Tilt slightly
    const tilt = 0.3;
    const cosT = Math.cos(tilt);
    const sinT = Math.sin(tilt);
    const ry = y * cosT - rz * sinT;
    const rz2 = y * sinT + rz * cosT;

    // Perspective
    const perspective = 600;
    const scale = perspective / (perspective + rz2);

    return {
      x: cx + rx * scale,
      y: cy + ry * scale,
      z: rz2,
      scale: scale,
    };
  }

  // ── Draw latitude lines ──
  function drawLatLines() {
    for (let lat = -75; lat <= 75; lat += 15) {
      ctx.beginPath();
      let started = false;

      for (let lon = 0; lon <= 360; lon += 3) {
        const p = project(lat, lon, radius);

        if (p.z < -radius * 0.1) {
          started = false;
          continue;
        }

        const alpha = 0.1 + (p.z / radius) * 0.15;
        ctx.strokeStyle = `rgba(255, 26, 26, ${Math.max(0.03, alpha)})`;

        if (!started) {
          ctx.moveTo(p.x, p.y);
          started = true;
        } else {
          ctx.lineTo(p.x, p.y);
        }
      }
      ctx.lineWidth = 0.8;
      ctx.stroke();
    }
  }

  // ── Draw longitude lines ──
  function drawLonLines() {
    for (let lon = 0; lon < 360; lon += 20) {
      ctx.beginPath();
      let started = false;

      for (let lat = -90; lat <= 90; lat += 3) {
        const p = project(lat, lon, radius);

        if (p.z < -radius * 0.1) {
          started = false;
          continue;
        }

        const alpha = 0.1 + (p.z / radius) * 0.15;
        ctx.strokeStyle = `rgba(255, 26, 26, ${Math.max(0.03, alpha)})`;

        if (!started) {
          ctx.moveTo(p.x, p.y);
          started = true;
        } else {
          ctx.lineTo(p.x, p.y);
        }
      }
      ctx.lineWidth = 0.8;
      ctx.stroke();
    }
  }

  // ── Draw dots at intersections ──
  function drawNodes() {
    for (let lat = -60; lat <= 60; lat += 30) {
      for (let lon = 0; lon < 360; lon += 40) {
        const p = project(lat, lon, radius);
        if (p.z < 0) continue;

        const alpha = 0.3 + (p.z / radius) * 0.4;
        const size = 1.5 * p.scale;

        ctx.beginPath();
        ctx.arc(p.x, p.y, size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 215, 0, ${alpha})`;
        ctx.fill();
      }
    }
  }

  // ── Draw orbiting ring ──
  function drawOrbitRing(r, speed, color, width) {
    ctx.beginPath();
    let started = false;

    for (let a = 0; a <= 360; a += 2) {
      const p = project(0, a + speed, r);

      if (p.z < -r * 0.05) {
        started = false;
        continue;
      }

      if (!started) {
        ctx.moveTo(p.x, p.y);
        started = true;
      } else {
        ctx.lineTo(p.x, p.y);
      }
    }

    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.stroke();
  }

  // ── Draw data points orbiting ──
  function drawSatellites(t) {
    const count = 4;
    for (let i = 0; i < count; i++) {
      const angle = (i * 360 / count) + t * 40;
      const lat = Math.sin((t + i) * 0.5) * 30;
      const p = project(lat, angle, radius + 12);
      if (p.z < 0) continue;

      // Glow
      ctx.beginPath();
      ctx.arc(p.x, p.y, 4 * p.scale, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255, 215, 0, 0.15)`;
      ctx.fill();

      // Core
      ctx.beginPath();
      ctx.arc(p.x, p.y, 2 * p.scale, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255, 215, 0, 0.8)`;
      ctx.fill();
    }
  }

  // ── Outer rings (arc reactor style) ──
  function drawReactorRings(t) {
    const outerR = radius + 20;
    const segments = 8;

    for (let i = 0; i < segments; i++) {
      const startAngle = (i * Math.PI * 2) / segments + t * 0.4 + 0.08;
      const endAngle = ((i + 1) * Math.PI * 2) / segments + t * 0.4 - 0.08;

      ctx.beginPath();
      ctx.arc(cx, cy, outerR, startAngle, endAngle);
      ctx.strokeStyle = `rgba(255, 26, 26, ${0.12 + Math.sin(t * 2 + i) * 0.06})`;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // Inner counter-rotating ring
    const innerR = radius + 10;
    for (let i = 0; i < 12; i++) {
      const startAngle = (i * Math.PI * 2) / 12 - t * 0.3 + 0.04;
      const endAngle = ((i + 1) * Math.PI * 2) / 12 - t * 0.3 - 0.04;

      ctx.beginPath();
      ctx.arc(cx, cy, innerR, startAngle, endAngle);
      ctx.strokeStyle = `rgba(255, 215, 0, 0.08)`;
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Tick marks
    for (let i = 0; i < 72; i++) {
      const angle = (i * Math.PI * 2) / 72 + t * 0.1;
      const inner = outerR + 3;
      const outer = outerR + (i % 6 === 0 ? 10 : 5);
      const alpha = i % 6 === 0 ? 0.12 : 0.04;

      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(angle) * inner, cy + Math.sin(angle) * inner);
      ctx.lineTo(cx + Math.cos(angle) * outer, cy + Math.sin(angle) * outer);
      ctx.strokeStyle = `rgba(255, 26, 26, ${alpha})`;
      ctx.lineWidth = 0.6;
      ctx.stroke();
    }
  }

  // ── Main loop ──
  let t = 0;

  function frame() {
    ctx.clearRect(0, 0, W * window.devicePixelRatio, H * window.devicePixelRatio);
    ctx.save();
    t += 0.016;

    // Auto rotate + mouse influence
    rotY += 0.005 + mouseOffsetX * 0.01;

    // Draw elements back to front
    drawReactorRings(t);
    drawLatLines();
    drawLonLines();
    drawNodes();
    drawSatellites(t);

    // Equator ring (gold)
    drawOrbitRing(radius + 2, 0, 'rgba(255, 215, 0, 0.1)', 1);

    ctx.restore();
    requestAnimationFrame(frame);
  }

  resize();
  frame();
})();
