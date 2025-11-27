/** @format */

const canvas = document.getElementById("mainCanvas");
const ctx = canvas.getContext("2d");

const state = {
  running: false,
  temperature: 25,
  particles: [],
};

function drawScene() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Vẽ background
  ctx.fillStyle = "#1e3a8a";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Vẽ particles
  state.particles.forEach(p => {
    ctx.fillStyle = "red";
    ctx.beginPath();
    ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
    ctx.fill();
  });
}

function updatePhysics() {
  if (!state.running) return;

  state.particles.forEach(p => {
    p.x += p.vx;
    p.y += p.vy;

    // Bounce
    if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
    if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
  });

  drawScene();
  requestAnimationFrame(updatePhysics);
}

function init() {
  // Tạo particles
  for (let i = 0; i < 10; i++) {
    state.particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 2,
      vy: (Math.random() - 0.5) * 2,
    });
  }

  // Event listeners
  document.getElementById("btnStart").onclick = () => {
    state.running = true;
    updatePhysics();
  };

  document.getElementById("btnReset").onclick = () => {
    state.running = false;
    state.particles = [];
    init();
  };

  drawScene();
}

init();
