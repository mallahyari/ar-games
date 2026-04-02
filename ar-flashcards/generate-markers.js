// Generates ArUco DICT_4X4 markers in the browser and displays them
// 4x4 markers: 6x6 grid total (1px border each side + 4x4 bits + 1px border each side)

// 4x4_50 dictionary — first 5 marker bit patterns
// Each marker is a 4x4 bit matrix (row-major)
const DICT_4X4 = [
  // ID 0
  [0,0,0,1,
   0,1,1,1,
   1,0,0,1,
   1,0,1,1],
  // ID 1
  [0,0,1,0,
   1,1,0,1,
   0,0,0,1,
   0,1,0,0],
  // ID 2
  [0,0,1,1,
   1,0,0,0,
   0,1,1,0,
   1,1,0,1],
  // ID 3
  [0,1,0,0,
   0,0,1,1,
   1,1,0,0,
   1,0,1,1],
  // ID 4
  [0,1,0,1,
   1,1,1,0,
   0,1,0,0,
   0,0,1,0],
];

function drawMarker(canvas, id, size = 160) {
  const ctx = canvas.getContext('2d');
  canvas.width = size;
  canvas.height = size;

  const bits = DICT_4X4[id];
  const gridSize = 6; // 4 data bits + 2 border cells
  const cellSize = size / gridSize;

  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, size, size);

  for (let row = 0; row < gridSize; row++) {
    for (let col = 0; col < gridSize; col++) {
      const isBorder = row === 0 || row === gridSize - 1 || col === 0 || col === gridSize - 1;
      let black;
      if (isBorder) {
        black = true; // border is always black
      } else {
        const bitRow = row - 1;
        const bitCol = col - 1;
        black = bits[bitRow * 4 + bitCol] === 1;
      }
      ctx.fillStyle = black ? '#000' : '#fff';
      ctx.fillRect(col * cellSize, row * cellSize, cellSize, cellSize);
    }
  }
}

async function loadCards() {
  const res = await fetch('cards.json');
  return res.json();
}

async function init() {
  const cards = await loadCards();
  const grid = document.getElementById('grid');

  for (let id = 0; id < DICT_4X4.length; id++) {
    const card = cards[String(id)];
    if (!card) continue;

    const div = document.createElement('div');
    div.className = 'card';

    const canvas = document.createElement('canvas');
    drawMarker(canvas, id, 160);

    const label = document.createElement('div');
    label.className = 'label';
    label.textContent = `Marker #${id}`;

    const question = document.createElement('div');
    question.className = 'question';
    question.textContent = card.question;

    div.appendChild(canvas);
    div.appendChild(label);
    div.appendChild(question);
    grid.appendChild(div);
  }
}

init();
