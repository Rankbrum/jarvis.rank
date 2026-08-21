import assert from "node:assert/strict";

const graph = await import(new URL("../ui/graph.js", import.meta.url));

assert.deepEqual(
  graph.shortestPath(
    [{ id: "a" }, { id: "b" }, { id: "c" }, { id: "d" }],
    [{ source: "a", target: "b" }, { source: "b", target: "c" }, { source: "a", target: "d" }, { source: "d", target: "c" }],
    "a",
    "c",
  ),
  ["a", "b", "c"],
  "BFS chooses the shortest available path",
);
assert.deepEqual(graph.shortestPath([{ id: "a" }, { id: "b" }], [], "a", "b"), [], "disconnected nodes have no path");

const labels = graph.resolveLabelCollisions([
  { id: "low", importance: 1, left: 0, right: 20, top: 0, bottom: 12 },
  { id: "high", importance: 4, left: 4, right: 24, top: 0, bottom: 12 },
  { id: "free", importance: 2, left: 30, right: 50, top: 0, bottom: 12 },
]);
assert.deepEqual(labels.map((label) => label.id), ["high", "free"], "higher-priority overlapping labels win deterministically");

class FakeContext {
  setTransform() {} clearRect() {} beginPath() {} moveTo() {} lineTo() {} stroke() {} arc() {} fill() {} fillText() {}
  measureText(text) { return { width: String(text).length * 7 }; }
}

class FakeCanvas {
  constructor() { this.listeners = new Map(); this.style = {}; this.width = 0; this.height = 0; this.captures = []; }
  getContext() { return new FakeContext(); }
  getBoundingClientRect() { return { left: 10, top: 20, width: 400, height: 300 }; }
  addEventListener(type, handler) { this.listeners.set(type, handler); }
  removeEventListener(type) { this.listeners.delete(type); }
  setPointerCapture(id) { this.captures.push(id); }
  releasePointerCapture(id) { this.captures = this.captures.filter((capture) => capture !== id); }
}

const originalRaf = globalThis.requestAnimationFrame;
const originalCancelRaf = globalThis.cancelAnimationFrame;
const originalDpr = globalThis.devicePixelRatio;
const originalMatchMedia = globalThis.matchMedia;
const rafs = new Map();
let nextRaf = 1;
globalThis.devicePixelRatio = 2;
globalThis.requestAnimationFrame = (callback) => { const id = nextRaf++; rafs.set(id, callback); return id; };
globalThis.cancelAnimationFrame = (id) => rafs.delete(id);

const focused = [];
const canvas = new FakeCanvas();
const runtime = new graph.KnowledgeGraph(canvas, { onFocus: (node) => focused.push(node?.id) });
runtime.setData({
  nodes: [{ id: "a", title: "Alpha", type: "project", degree: 2 }, { id: "b", title: "Beta", type: "task", degree: 1 }, { id: "c", title: "Gamma", type: "lead", degree: 1 }],
  edges: [{ source: "a", target: "b" }, { source: "b", target: "c" }],
});
assert.equal(canvas.width, 800, "resize applies devicePixelRatio to Canvas width");
assert.equal(canvas.height, 600, "resize applies devicePixelRatio to Canvas height");
const initial = { ...runtime.transform };
runtime.onWheel({ clientX: 210, clientY: 170, deltaY: -100000, preventDefault() {} });
assert.equal(runtime.transform.scale, 3.5, "zoom is bounded at its maximum");
assert.notEqual(runtime.transform.x, initial.x, "zoom remains centered on the cursor");
runtime.setTypeFilter("task", false);
assert.equal(runtime.visibleNodes.some((node) => node.type === "task"), false, "type filters update visible nodes");
runtime.setTypeFilter("task", true);
const alpha = runtime.nodeById.get("a");
const alphaPointer = { clientX: 10 + runtime.transform.x + alpha.x * runtime.transform.scale, clientY: 20 + runtime.transform.y + alpha.y * runtime.transform.scale, pointerId: 7, shiftKey: false };
runtime.onPointerDown(alphaPointer);
assert.deepEqual(focused, ["a"], "pointer selection focuses a node and invokes the inspector callback");
runtime.onPointerUp(alphaPointer);
const panBefore = { ...runtime.transform };
runtime.onPointerDown({ clientX: 20, clientY: 30, pointerId: 8, shiftKey: false });
runtime.onPointerMove({ clientX: 55, clientY: 66, pointerId: 8 });
assert.equal(runtime.transform.x, panBefore.x + 35, "empty-space drag pans without moving nodes");
assert.equal(runtime.transform.y, panBefore.y + 36, "empty-space drag pans without moving nodes");
runtime.onPointerUp({ pointerId: 8 });
const alphaBeforeDrag = { x: alpha.x, y: alpha.y };
const dragStart = { clientX: 10 + runtime.transform.x + alpha.x * runtime.transform.scale, clientY: 20 + runtime.transform.y + alpha.y * runtime.transform.scale, pointerId: 9, shiftKey: false };
runtime.onPointerDown(dragStart);
runtime.onPointerMove({ ...dragStart, clientX: dragStart.clientX + 21, clientY: dragStart.clientY + 14, pointerId: 9 });
assert.notDeepEqual({ x: alpha.x, y: alpha.y }, alphaBeforeDrag, "node drag updates only the selected node position");
assert.equal(alpha.dragged, true, "node stays pinned during a pointer drag");
runtime.onPointerUp({ pointerId: 9 });
assert.equal(alpha.dragged, false, "releasing the pointer unpins the node");
runtime.destroy();
assert.equal(canvas.listeners.size, 0, "destroy removes Canvas listeners");
assert.equal(runtime.destroyed, true, "destroy marks the graph unusable");

globalThis.matchMedia = () => ({ matches: true });
const reduced = new graph.KnowledgeGraph(new FakeCanvas());
reduced.setData({ nodes: [{ id: "still", title: "Still", type: "note" }], edges: [] });
assert.equal(reduced.physicsUntil, 0, "reduced motion suppresses decorative force simulation");
reduced.destroy();

globalThis.requestAnimationFrame = originalRaf;
globalThis.cancelAnimationFrame = originalCancelRaf;
globalThis.devicePixelRatio = originalDpr;
globalThis.matchMedia = originalMatchMedia;

console.log("Graph algorithm tests passed");
