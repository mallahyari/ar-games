const WS_URL = 'ws://localhost:8765';
const RECONNECT_DELAY = 2000;

const FRUIT_CONFIG = {
    apple:      { emoji: '🍎', color: '#e74c3c' },
    watermelon: { emoji: '🍉', color: '#27ae60' },
    orange:     { emoji: '🍊', color: '#e67e22' },
    bomb:       { emoji: '💣', color: '#2c3e50' },
};
const SPAWN_TYPES = ['apple', 'watermelon', 'orange', 'orange', 'apple', 'bomb'];

let canvas, ctx;
let state = {};

function initState() {
    state = {
        objects: [], score: 0, lives: 3,
        maxObjects: 3, speed: 3, spawnInterval: 2000,
        lastSpawnTime: 0, difficultyTimer: 0,
        gameOver: false, running: false,
        ws: null, wsConnected: false,
        trails: [],
        devMode: new URLSearchParams(window.location.search).has('dev'),
        mouseStart: null, lastTime: null,
    };
}

function spawnObject() {
    const type = SPAWN_TYPES[Math.floor(Math.random() * SPAWN_TYPES.length)];
    const edge = Math.floor(Math.random() * 4); // 0=top 1=right 2=bottom 3=left
    const r = 40;
    let x, y;
    switch (edge) {
        case 0: x = Math.random() * canvas.width;  y = -r; break;
        case 1: x = canvas.width + r;               y = Math.random() * canvas.height; break;
        case 2: x = Math.random() * canvas.width;  y = canvas.height + r; break;
        default: x = -r;                            y = Math.random() * canvas.height;
    }
    const targetX = canvas.width  * (0.2 + Math.random() * 0.6);
    const targetY = canvas.height * (0.2 + Math.random() * 0.6);
    const angle  = Math.atan2(targetY - y, targetX - x);
    const spread = (Math.random() - 0.5) * 0.8;
    return {
        id: Date.now() + Math.random(),
        x, y,
        vx: Math.cos(angle + spread) * state.speed,
        vy: Math.sin(angle + spread) * state.speed,
        radius: r, type, sliced: false, sliceEffect: null,
    };
}

function applySwipe(swipe) {
    if (state.gameOver) return;
    state.trails.push({
        x1: swipe.x1 * canvas.width,  y1: swipe.y1 * canvas.height,
        x2: swipe.x2 * canvas.width,  y2: swipe.y2 * canvas.height,
        alpha: 1.0,
    });
    const indices = checkSwipeSlices(swipe, canvas.width, canvas.height, state.objects);
    if (!indices.length) return;
    const combo = indices.length >= 2;
    for (const i of indices) {
        const obj = state.objects[i];
        obj.sliced = true;
        obj.sliceEffect = { alpha: 1.0, offsetX: 0, offsetY: 0 };
        if (obj.type === 'bomb') {
            state.lives = Math.max(0, state.lives - 1);
            if (state.lives === 0) triggerGameOver();
        } else {
            state.score += combo ? 3 : 1;
        }
    }
}

function update(dt) {
    if (state.gameOver) return;

    state.difficultyTimer += dt;
    if (state.difficultyTimer >= 15000) {
        state.difficultyTimer = 0;
        state.maxObjects    = Math.min(state.maxObjects + 1, 10);
        state.speed         = Math.min(state.speed * 1.05, 10);
        state.spawnInterval = Math.max(state.spawnInterval * 0.95, 800);
    }

    const activeCount = state.objects.filter(o => !o.sliced).length;
    const now = performance.now();
    if (activeCount < state.maxObjects && now - state.lastSpawnTime > state.spawnInterval) {
        state.objects.push(spawnObject());
        state.lastSpawnTime = now;
    }

    const margin = 80;
    for (let i = state.objects.length - 1; i >= 0; i--) {
        const obj = state.objects[i];
        if (obj.sliced) {
            obj.sliceEffect.alpha    -= 0.04;
            obj.sliceEffect.offsetX  += obj.vx * 0.5;
            obj.sliceEffect.offsetY  += obj.vy * 0.5;
            if (obj.sliceEffect.alpha <= 0) state.objects.splice(i, 1);
            continue;
        }
        obj.x += obj.vx;
        obj.y += obj.vy;
        const off = obj.x < -margin || obj.x > canvas.width + margin ||
                    obj.y < -margin || obj.y > canvas.height + margin;
        if (off) {
            state.objects.splice(i, 1);
            if (obj.type !== 'bomb') {
                state.lives = Math.max(0, state.lives - 1);
                if (state.lives === 0) triggerGameOver();
            }
        }
    }

    for (let i = state.trails.length - 1; i >= 0; i--) {
        state.trails[i].alpha -= 0.05;
        if (state.trails[i].alpha <= 0) state.trails.splice(i, 1);
    }
}

function render() {
    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (const obj of state.objects) {
        obj.sliced ? drawSliced(obj) : drawObject(obj);
    }

    for (const t of state.trails) {
        ctx.save();
        ctx.strokeStyle = `rgba(255,255,200,${t.alpha})`;
        ctx.lineWidth = 4; ctx.lineCap = 'round';
        ctx.beginPath(); ctx.moveTo(t.x1, t.y1); ctx.lineTo(t.x2, t.y2);
        ctx.stroke(); ctx.restore();
    }

    drawHUD();
    if (state.gameOver) drawGameOver();
    if (!state.wsConnected && !state.devMode) drawReconnecting();
}

function drawObject(obj) {
    const cfg = FRUIT_CONFIG[obj.type];
    ctx.save();
    ctx.beginPath();
    ctx.arc(obj.x, obj.y, obj.radius, 0, Math.PI * 2);
    ctx.fillStyle = cfg.color; ctx.fill();
    ctx.font = `${obj.radius}px serif`;
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(cfg.emoji, obj.x, obj.y);
    ctx.restore();
}

function drawSliced(obj) {
    const cfg = FRUIT_CONFIG[obj.type];
    const eff = obj.sliceEffect;
    ctx.save();
    ctx.globalAlpha = Math.max(0, eff.alpha);
    for (let half = 0; half < 2; half++) {
        const dx = eff.offsetX + (half === 0 ? -15 : 15) * (1 - eff.alpha);
        const dy = eff.offsetY + 10 * (1 - eff.alpha);
        ctx.save();
        ctx.beginPath();
        ctx.arc(obj.x + dx, obj.y + dy, obj.radius, half * Math.PI, (half + 1) * Math.PI);
        ctx.closePath();
        ctx.fillStyle = cfg.color; ctx.fill();
        ctx.restore();
    }
    ctx.restore();
}

function drawHUD() {
    ctx.save();
    ctx.fillStyle = '#fff'; ctx.font = 'bold 36px monospace';
    ctx.textAlign = 'left';  ctx.textBaseline = 'top';
    ctx.fillText(`Score: ${state.score}`, 20, 20);
    ctx.textAlign = 'right';
    ctx.fillText('❤️'.repeat(state.lives), canvas.width - 20, 20);
    ctx.restore();
}

function drawGameOver() {
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.75)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#fff'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.font = 'bold 80px monospace';
    ctx.fillText('GAME OVER', canvas.width / 2, canvas.height / 2 - 70);
    ctx.font = 'bold 48px monospace';
    ctx.fillText(`Score: ${state.score}`, canvas.width / 2, canvas.height / 2 + 10);
    ctx.font = '28px monospace'; ctx.fillStyle = '#aaa';
    ctx.fillText('Click to restart', canvas.width / 2, canvas.height / 2 + 80);
    ctx.restore();
}

function drawReconnecting() {
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.6)'; ctx.fillRect(0, 0, canvas.width, 56);
    ctx.fillStyle = '#f39c12'; ctx.font = '22px monospace';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('Connecting to camera server...', canvas.width / 2, 28);
    ctx.restore();
}

function gameLoop(timestamp) {
    if (state.lastTime === null) state.lastTime = timestamp;
    update(timestamp - state.lastTime);
    state.lastTime = timestamp;
    render();
    requestAnimationFrame(gameLoop);
}

function triggerGameOver() {
    state.gameOver = true;
    state.running  = false;
}

function startGame() {
    initState();
    state.running = true;
    connectWebSocket();
    if (state.devMode) setupDevMode();
    requestAnimationFrame(gameLoop);
}

function restartGame() {
    if (state.ws) { state.ws.onclose = null; state.ws.close(); }
    startGame();
}

function connectWebSocket() {
    if (state.devMode) return;
    let ws;
    try { ws = new WebSocket(WS_URL); }
    catch (e) { setTimeout(connectWebSocket, RECONNECT_DELAY); return; }
    state.ws = ws;
    ws.onopen    = () => { state.wsConnected = true; };
    ws.onmessage = (e) => {
        try { const msg = JSON.parse(e.data); if (msg.type === 'swipe') applySwipe(msg); }
        catch (_) {}
    };
    ws.onclose = () => { state.wsConnected = false; setTimeout(connectWebSocket, RECONNECT_DELAY); };
    ws.onerror = () => ws.close();
}

function setupDevMode() {
    state.wsConnected = true;
    canvas.addEventListener('mousedown', (e) => {
        const r = canvas.getBoundingClientRect();
        state.mouseStart = {
            x: (e.clientX - r.left) / canvas.width,
            y: (e.clientY - r.top)  / canvas.height,
        };
    });
    canvas.addEventListener('mouseup', (e) => {
        if (!state.mouseStart) return;
        const r = canvas.getBoundingClientRect();
        applySwipe({
            type: 'swipe',
            x1: state.mouseStart.x, y1: state.mouseStart.y,
            x2: (e.clientX - r.left) / canvas.width,
            y2: (e.clientY - r.top)  / canvas.height,
        });
        state.mouseStart = null;
    });
}

window.addEventListener('DOMContentLoaded', () => {
    canvas = document.getElementById('game');
    ctx    = canvas.getContext('2d');

    function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
    resize();
    window.addEventListener('resize', resize);
    canvas.addEventListener('click', () => { if (state.gameOver) restartGame(); });
    startGame();
});
