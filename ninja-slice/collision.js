function lineCircleIntersects(x1, y1, x2, y2, cx, cy, r) {
    const dx = x2 - x1, dy = y2 - y1;
    const fx = x1 - cx, fy = y1 - cy;
    const a = dx * dx + dy * dy;
    if (a === 0) return false;
    const b = 2 * (fx * dx + fy * dy);
    const c = fx * fx + fy * fy - r * r;
    const disc = b * b - 4 * a * c;
    if (disc < 0) return false;
    const sqrtD = Math.sqrt(disc);
    const t1 = (-b - sqrtD) / (2 * a);
    const t2 = (-b + sqrtD) / (2 * a);
    return (t1 >= 0 && t1 <= 1) || (t2 >= 0 && t2 <= 1);
}

function checkSwipeSlices(swipe, cw, ch, objects) {
    const sx1 = swipe.x1 * cw, sy1 = swipe.y1 * ch;
    const sx2 = swipe.x2 * cw, sy2 = swipe.y2 * ch;
    const result = [];
    for (let i = 0; i < objects.length; i++) {
        const obj = objects[i];
        if (obj.sliced) continue;
        if (lineCircleIntersects(sx1, sy1, sx2, sy2, obj.x, obj.y, obj.radius)) {
            result.push(i);
        }
    }
    return result;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { lineCircleIntersects, checkSwipeSlices };
}
