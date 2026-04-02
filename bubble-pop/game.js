const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');

const BUBBLE_COLORS = [
  '#ff6b9d', '#c44dff', '#4dc8ff', '#4dffb4',
  '#ffdd4d', '#ff8c4d', '#4d79ff', '#ff4d4d',
];

const MIN_RADIUS = 30;
const MAX_RADIUS = 70;
const MIN_SPEED = 40;   // px/s
const MAX_SPEED = 100;
const SPAWN_INTERVAL = 1200; // ms
const MAX_BUBBLES = 12;

let state;
let ws;
let hands = [];
const devMode = new URLSearchParams(location.search).has('dev');

function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
}

function initState() {
  return {
    bubbles: [],
    pops: [],         // pop animations
    score: 0,
    lives: 5,
    gameOver: false,
    lastSpawn: 0,
    lastTime: null,
    animFrameId: null,
    wsConnected: devMode,
    reconnecting: false,
  };
}

function spawnBubble(now) {
  const r = MIN_RADIUS + Math.random() * (MAX_RADIUS - MIN_RADIUS);
  const x = r + Math.random() * (canvas.width - 2 * r);
  const speed = MIN_SPEED + Math.random() * (MAX_SPEED - MIN_SPEED);
  const color = BUBBLE_COLORS[Math.floor(Math.random() * BUBBLE_COLORS.length)];
  return { x, y: canvas.height + r, r, speed, color, popped: false, opacity: 1 };
}

function popBubble(bubble) {
  bubble.popped = true;
  state.pops.push({
    x: bubble.x, y: bubble.y, r: bubble.r,
    color: bubble.color,
    scale: 1, opacity: 1,
  });
}

function checkHandCollisions() {
  if (!hands.length) return;
  for (const bubble of state.bubbles) {
    if (bubble.popped) continue;
    for (const hand of hands) {
      const hx = hand.x * canvas.width;
      const hy = hand.y * canvas.height;
      const hr = hand.radius * canvas.width;
      const dist = Math.hypot(hx - bubble.x, hy - bubble.y);
      if (dist < hr + bubble.r) {
        popBubble(bubble);
        state.score++;
        break;
      }
    }
  }
}

function update(now) {
  if (state.lastTime === null) { state.lastTime = now; }
  const dt = Math.min((now - state.lastTime) / 1000, 0.1);
  state.lastTime = now;

  if (state.gameOver) return;

  // Spawn
  if (state.bubbles.filter(b => !b.popped).length < MAX_BUBBLES &&
      now - state.lastSpawn > SPAWN_INTERVAL) {
    state.bubbles.push(spawnBubble(now));
    state.lastSpawn = now;
  }

  // Move bubbles
  for (const b of state.bubbles) {
    if (b.popped) continue;
    b.y -= b.speed * dt;
    if (b.y + b.r < 0) {
      b.popped = true;
      state.lives--;
      if (state.lives <= 0) state.gameOver = true;
    }
  }

  // Check collisions
  checkHandCollisions();

  // Trim old bubbles
  state.bubbles = state.bubbles.filter(b => !b.popped || false);
  // Keep popped ones briefly for the pop animation; actual removal in pop update below

  // Update pop animations
  for (const p of state.pops) {
    p.scale += dt * 4;
    p.opacity -= dt * 3;
  }
  state.pops = state.pops.filter(p => p.opacity > 0);
}

function drawBubble(b) {
  ctx.save();
  ctx.globalAlpha = b.opacity;
  ctx.beginPath();
  ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2);
  ctx.strokeStyle = b.color;
  ctx.lineWidth = 3;
  ctx.stroke();

  // Shiny highlight
  const grad = ctx.createRadialGradient(
    b.x - b.r * 0.3, b.y - b.r * 0.3, b.r * 0.05,
    b.x, b.y, b.r
  );
  grad.addColorStop(0, 'rgba(255,255,255,0.35)');
  grad.addColorStop(0.4, b.color + '55');
  grad.addColorStop(1, b.color + '22');
  ctx.fillStyle = grad;
  ctx.fill();
  ctx.restore();
}

function drawPop(p) {
  ctx.save();
  ctx.globalAlpha = Math.max(0, p.opacity);
  ctx.translate(p.x, p.y);
  ctx.scale(p.scale, p.scale);

  // Burst lines
  const lines = 8;
  ctx.strokeStyle = p.color;
  ctx.lineWidth = 2;
  for (let i = 0; i < lines; i++) {
    const angle = (i / lines) * Math.PI * 2;
    const inner = p.r * 0.6;
    const outer = p.r * 1.2;
    ctx.beginPath();
    ctx.moveTo(Math.cos(angle) * inner, Math.sin(angle) * inner);
    ctx.lineTo(Math.cos(angle) * outer, Math.sin(angle) * outer);
    ctx.stroke();
  }
  ctx.restore();
}

function drawHands() {
  for (const hand of hands) {
    const hx = hand.x * canvas.width;
    const hy = hand.y * canvas.height;
    const hr = hand.radius * canvas.width;
    ctx.save();
    ctx.beginPath();
    ctx.arc(hx, hy, Math.max(hr, 20), 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,255,255,0.4)';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.restore();
  }
}

function drawHUD() {
  ctx.save();
  ctx.font = 'bold 36px Arial';
  ctx.fillStyle = '#fff';
  ctx.textAlign = 'left';
  ctx.fillText(`Score: ${state.score}`, 20, 50);
  ctx.textAlign = 'right';
  ctx.fillText('❤️'.repeat(state.lives), canvas.width - 20, 50);
  ctx.restore();
}

function drawGameOver() {
  ctx.save();
  ctx.fillStyle = 'rgba(0,0,0,0.7)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#fff';
  ctx.font = 'bold 80px Arial';
  ctx.textAlign = 'center';
  ctx.fillText('Game Over', canvas.width / 2, canvas.height / 2 - 40);
  ctx.font = '40px Arial';
  ctx.fillText(`Score: ${state.score}`, canvas.width / 2, canvas.height / 2 + 30);
  ctx.font = '28px Arial';
  ctx.fillStyle = '#aaa';
  ctx.fillText('Tap to play again', canvas.width / 2, canvas.height / 2 + 90);
  ctx.restore();
}

function drawReconnecting() {
  ctx.save();
  ctx.fillStyle = 'rgba(255,100,0,0.85)';
  ctx.font = '22px Arial';
  ctx.textAlign = 'center';
  ctx.fillText('Connecting to camera server...', canvas.width / 2, canvas.height - 30);
  ctx.restore();
}

function render() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Background gradient
  const bg = ctx.createLinearGradient(0, 0, 0, canvas.height);
  bg.addColorStop(0, '#0d0221');
  bg.addColorStop(1, '#0a1628');
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  for (const b of state.bubbles) {
    if (!b.popped) drawBubble(b);
  }
  for (const p of state.pops) drawPop(p);
  drawHands();
  drawHUD();

  if (state.gameOver) drawGameOver();
  if (!state.wsConnected && !devMode) drawReconnecting();
}

function gameLoop(now) {
  update(now);
  render();
  state.animFrameId = requestAnimationFrame(gameLoop);
}

function startGame() {
  if (state && state.animFrameId) cancelAnimationFrame(state.animFrameId);
  state = initState();
  state.animFrameId = requestAnimationFrame(gameLoop);
}

function connectWebSocket() {
  ws = new WebSocket('ws://localhost:8765');

  ws.onopen = () => {
    console.log('WS connected');
    if (state) state.wsConnected = true;
  };

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'hands') {
      hands = msg.hands;
    }
  };

  ws.onclose = () => {
    if (state) state.wsConnected = false;
    hands = [];
    setTimeout(connectWebSocket, 2000);
  };

  ws.onerror = () => ws.close();
}

function setupDevMode() {
  // Mouse simulates a single hand
  canvas.addEventListener('mousemove', (e) => {
    const r = canvas.getBoundingClientRect();
    hands = [{
      type: 'hand',
      x: (e.clientX - r.left) / canvas.width,
      y: (e.clientY - r.top) / canvas.height,
      radius: 0.06,
    }];
  });
  canvas.addEventListener('mouseleave', () => { hands = []; });
}

window.addEventListener('resize', resize);

document.addEventListener('DOMContentLoaded', () => {
  resize();

  document.addEventListener('click', () => {
    if (state && state.gameOver) startGame();
  });

  startGame();

  if (devMode) {
    setupDevMode();
  } else {
    connectWebSocket();
  }
});
