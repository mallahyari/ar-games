const { lineCircleIntersects, checkSwipeSlices } = require('../collision.js');

let passed = 0, failed = 0;
function assert(condition, msg) {
    if (condition) { console.log(`  PASS: ${msg}`); passed++; }
    else { console.error(`  FAIL: ${msg}`); failed++; }
}

console.log('lineCircleIntersects:');
assert(lineCircleIntersects(0, 0, 100, 0, 50, 0, 10),   'line through center hits');
assert(lineCircleIntersects(0, 0, 100, 0, 50, 5, 10),   'line grazes circle hits');
assert(!lineCircleIntersects(0, 0, 100, 0, 50, 20, 10), 'line above circle misses');
assert(!lineCircleIntersects(0, 0, 10, 0, 50, 0, 10),   'segment ends before circle misses');
assert(lineCircleIntersects(0, 0, 200, 0, 50, 0, 10),   'circle mid-segment hits');
assert(!lineCircleIntersects(0, 0, 0, 0, 50, 50, 10),   'zero-length segment misses');

console.log('\ncheckSwipeSlices:');
const objects = [
    { x: 500, y: 240, radius: 40, sliced: false },
    { x: 100, y: 240, radius: 40, sliced: false },
    { x: 500, y: 240, radius: 40, sliced: true  },
];
const swipe = { x1: 0.45, y1: 0.5, x2: 0.55, y2: 0.5 };
const result = checkSwipeSlices(swipe, 1000, 480, objects);
assert(result.includes(0),  'slices object in path');
assert(!result.includes(1), 'does not slice object outside path');
assert(!result.includes(2), 'does not re-slice already-sliced object');

if (failed > 0) { console.error(`\n${passed} passed, ${failed} failed`); process.exit(1); }
else console.log(`\n${passed} passed, 0 failed`);
