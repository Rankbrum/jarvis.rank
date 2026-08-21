const TYPE_COLORS = {
  project: "#43c7f4", lead: "#36d17c", task: "#ffb21c", concept: "#a98cff",
  proposal: "#ff7a45", invoice: "#ef6ca5", note: "#d9e1eb", person: "#a98cff",
};
const MIN_SCALE = 0.25;
const MAX_SCALE = 3.5;
const MAX_COORDINATE = 100000;
const MAX_ACCELERATION = 1.25;
const MAX_VELOCITY = 12;
const MAX_REPULSION = 0.55;
const MAX_SPRING = 0.8;

export class SpatialGrid {
  constructor(cellSize = 140) {
    this.cellSize = cellSize;
    this.cells = new Map();
  }

  rebuild(nodes) {
    this.cells.clear();
    for (const node of nodes) {
      const key = `${Math.floor(node.x / this.cellSize)},${Math.floor(node.y / this.cellSize)}`;
      const cell = this.cells.get(key) || [];
      cell.push(node);
      this.cells.set(key, cell);
    }
  }

  nearby(node) {
    const cx = Math.floor(node.x / this.cellSize);
    const cy = Math.floor(node.y / this.cellSize);
    const result = [];
    for (let offsetX = -1; offsetX <= 1; offsetX += 1) {
      for (let offsetY = -1; offsetY <= 1; offsetY += 1) result.push(...(this.cells.get(`${cx + offsetX},${cy + offsetY}`) || []));
    }
    return result;
  }
}

export function shortestPath(nodes, edges, start, end) {
  if (!start || !end) return [];
  const adjacency = new Map(nodes.map((node) => [node.id, []]));
  if (!adjacency.has(start) || !adjacency.has(end)) return [];
  for (const edge of edges) {
    adjacency.get(edge.source)?.push(edge.target);
    adjacency.get(edge.target)?.push(edge.source);
  }
  const queue = [start];
  const parent = new Map([[start, null]]);
  for (let cursor = 0; cursor < queue.length; cursor += 1) {
    const current = queue[cursor];
    if (current === end) {
      const path = [];
      for (let id = current; id !== null; id = parent.get(id)) path.push(id);
      return path.reverse();
    }
    for (const next of adjacency.get(current) || []) {
      if (!parent.has(next)) { parent.set(next, current); queue.push(next); }
    }
  }
  return [];
}

export function resolveLabelCollisions(candidates) {
  const accepted = [];
  for (const candidate of [...candidates].sort((left, right) => right.importance - left.importance || String(left.id).localeCompare(String(right.id)))) {
    const overlaps = accepted.some((other) => !(candidate.right < other.left || candidate.left > other.right || candidate.bottom < other.top || candidate.top > other.bottom));
    if (!overlaps) accepted.push(candidate);
  }
  return accepted;
}

function seededPosition(id, spread) {
  let hash = 2166136261;
  for (const character of String(id)) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
  return { x: ((hash >>> 0) % spread) - spread / 2, y: (((hash >>> 11) % spread) - spread / 2) };
}

function nodeDegree(node) {
  return Number(node.degree ?? node.connections?.length ?? ((node.incoming?.length || 0) + (node.outgoing?.length || 0)) ?? 1) || 1;
}

function isSafeNumber(value) {
  return Number.isFinite(value) && Math.abs(value) <= MAX_COORDINATE;
}

function capVector(x, y, maximum) {
  const magnitude = Math.hypot(x, y);
  if (!Number.isFinite(magnitude)) return { x: 0, y: 0 };
  if (magnitude <= maximum) return { x, y };
  const scale = maximum / magnitude;
  return { x: x * scale, y: y * scale };
}

export class KnowledgeGraph {
  constructor(canvas, callbacks = {}) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d");
    this.callbacks = callbacks;
    this.nodes = [];
    this.edges = [];
    this.visibleNodes = [];
    this.visibleEdges = [];
    this.nodeById = new Map();
    this.relatedById = new Map();
    this.enabledTypes = new Set();
    this.grid = new SpatialGrid();
    this.transform = { x: 0, y: 0, scale: 1 };
    this.focusedId = null;
    this.hoveredId = null;
    this.pathIds = new Set();
    this.relatedIds = new Set();
    this.drag = null;
    this.destroyed = false;
    this.suspended = false;
    this.labelsVisible = true;
    this.physicsUntil = 0;
    this.settledFrames = 0;
    this.frameId = null;
    this.hasFitted = false;
    this.reducedMotion = Boolean(globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
    this.onWheel = this.onWheel.bind(this);
    this.onPointerDown = this.onPointerDown.bind(this);
    this.onPointerMove = this.onPointerMove.bind(this);
    this.onPointerUp = this.onPointerUp.bind(this);
    this.onVisibilityChange = this.onVisibilityChange.bind(this);
    this.resize = this.resize.bind(this);
    this.resizeObserver = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(this.resize);
    this.resizeObserver?.observe(canvas);
    canvas.addEventListener("wheel", this.onWheel, { passive: false });
    canvas.addEventListener("pointerdown", this.onPointerDown);
    canvas.addEventListener("pointermove", this.onPointerMove);
    canvas.addEventListener("pointerup", this.onPointerUp);
    canvas.addEventListener("pointercancel", this.onPointerUp);
    globalThis.document?.addEventListener("visibilitychange", this.onVisibilityChange);
    this.resize();
  }

  setData(graph = {}) {
    const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
    const edges = Array.isArray(graph.edges) ? graph.edges : [];
    this.nodes = nodes.map((node) => {
      const position = seededPosition(node.id, Math.max(900, Math.sqrt(nodes.length) * 130));
      const degree = nodeDegree(node);
      return { ...node, ...position, vx: 0, vy: 0, degree, radius: 5 + Math.min(18, Math.sqrt(degree) * 3), dragged: false };
    });
    this.nodeById = new Map(this.nodes.map((node) => [node.id, node]));
    this.edges = edges.filter((edge) => this.nodeById.has(edge.source) && this.nodeById.has(edge.target)).map((edge) => ({ ...edge }));
    this.enabledTypes = new Set(this.nodes.map((node) => node.type));
    this.focusedId = null;
    this.hoveredId = null;
    this.pathIds.clear();
    this.rebuildGraphCaches();
    this.hasFitted = false;
    this.fitToView();
    this.wake(950);
  }

  setTypeFilter(type, enabled) {
    if (enabled) this.enabledTypes.add(type); else this.enabledTypes.delete(type);
    this.rebuildVisible();
    this.updateRelated();
    this.wake(420);
  }

  focusNode(id) {
    const node = this.nodeById.get(id) || null;
    this.focusedId = node?.id || null;
    this.pathIds.clear();
    this.updateRelated();
    this.callbacks.onFocus?.(node);
    this.wake(260);
  }

  selectPathTo(id) {
    if (!this.focusedId || !this.nodeById.has(id) || id === this.focusedId) return [];
    const path = shortestPath(this.nodes, this.edges, this.focusedId, id);
    this.pathIds = new Set(path);
    this.updateRelated();
    this.callbacks.onPath?.(path);
    this.requestFrame();
    return path;
  }

  centerOnNode(id) {
    const node = this.nodeById.get(id);
    if (!node) return false;
    const rect = this.canvas.getBoundingClientRect();
    this.transform.x = rect.width / 2 - node.x * this.transform.scale;
    this.transform.y = rect.height / 2 - node.y * this.transform.scale;
    this.focusNode(id);
    this.requestFrame();
    return true;
  }

  panBy(x, y) {
    this.transform.x += x;
    this.transform.y += y;
    this.requestFrame();
  }

  zoomBy(factor) {
    const rect = this.canvas.getBoundingClientRect();
    const cursor = { x: rect.width / 2, y: rect.height / 2 };
    const world = { x: (cursor.x - this.transform.x) / this.transform.scale, y: (cursor.y - this.transform.y) / this.transform.scale };
    const nextScale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, this.transform.scale * factor));
    this.transform.x = cursor.x - world.x * nextScale;
    this.transform.y = cursor.y - world.y * nextScale;
    this.transform.scale = nextScale;
    this.requestFrame();
  }

  setLabelsVisible(visible) {
    this.labelsVisible = Boolean(visible);
    this.requestFrame();
  }

  fitToView() {
    if (!this.visibleNodes.length) return;
    const rect = this.canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const bounds = this.visibleNodes.reduce((result, node) => ({
      left: Math.min(result.left, node.x - node.radius), right: Math.max(result.right, node.x + node.radius),
      top: Math.min(result.top, node.y - node.radius), bottom: Math.max(result.bottom, node.y + node.radius),
    }), { left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity });
    const padding = 46;
    const width = Math.max(1, bounds.right - bounds.left + padding * 2);
    const height = Math.max(1, bounds.bottom - bounds.top + padding * 2);
    const scale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, Math.min(rect.width / width, rect.height / height, 1.25)));
    this.transform.scale = scale;
    this.transform.x = rect.width / 2 - ((bounds.left + bounds.right) / 2) * scale;
    this.transform.y = rect.height / 2 - ((bounds.top + bounds.bottom) / 2) * scale;
    this.hasFitted = true;
    this.requestFrame();
  }

  rebuildGraphCaches() {
    this.relatedById = new Map(this.nodes.map((node) => [node.id, new Set()]));
    for (const edge of this.edges) {
      this.relatedById.get(edge.source)?.add(edge.target);
      this.relatedById.get(edge.target)?.add(edge.source);
    }
    this.rebuildVisible();
    this.updateRelated();
  }

  rebuildVisible() {
    this.visibleNodes = this.nodes.filter((node) => this.enabledTypes.has(node.type));
    const visibleIds = new Set(this.visibleNodes.map((node) => node.id));
    this.visibleEdges = this.edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target));
  }

  updateRelated() {
    const active = [this.hoveredId, this.focusedId, ...this.pathIds].filter(Boolean);
    this.relatedIds = new Set(active);
    for (const id of active) for (const relatedId of this.relatedById.get(id) || []) this.relatedIds.add(relatedId);
  }

  tick() {
    if (!this.visibleNodes.length) return;
    for (let index = 0; index < this.visibleNodes.length; index += 1) this.recoverNode(this.visibleNodes[index], index);
    this.grid.rebuild(this.visibleNodes);
    for (const node of this.visibleNodes) {
      node.ax = 0;
      node.ay = 0;
    }
    for (const node of this.visibleNodes) {
      for (const other of this.grid.nearby(node)) {
        if (node === other || String(node.id) >= String(other.id)) continue;
        const dx = node.x - other.x;
        const dy = node.y - other.y;
        const distance2 = Math.max(64, dx * dx + dy * dy);
        if (distance2 > 19600) continue;
        const distance = Math.sqrt(distance2);
        const force = Math.min(MAX_REPULSION, 180 / distance2);
        const xForce = (dx / distance) * force;
        const yForce = (dy / distance) * force;
        node.ax += xForce; node.ay += yForce;
        other.ax -= xForce; other.ay -= yForce;
      }
    }
    for (const edge of this.visibleEdges) {
      const source = this.nodeById.get(edge.source);
      const target = this.nodeById.get(edge.target);
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const distance = Math.max(1, Math.hypot(dx, dy));
      const force = Math.max(-MAX_SPRING, Math.min(MAX_SPRING, (distance - 90) * 0.004));
      const xForce = (dx / distance) * force;
      const yForce = (dy / distance) * force;
      source.ax += xForce; source.ay += yForce;
      target.ax -= xForce; target.ay -= yForce;
    }
    let energy = 0;
    for (let index = 0; index < this.visibleNodes.length; index += 1) {
      const node = this.visibleNodes[index];
      const acceleration = capVector(node.ax - node.x * 0.00012, node.ay - node.y * 0.00012, MAX_ACCELERATION);
      const velocity = capVector((node.vx + acceleration.x) * 0.88, (node.vy + acceleration.y) * 0.88, MAX_VELOCITY);
      node.vx = velocity.x;
      node.vy = velocity.y;
      if (!node.dragged) { node.x += node.vx; node.y += node.vy; }
      this.recoverNode(node, index);
      energy += Math.abs(node.vx) + Math.abs(node.vy);
    }
    this.settledFrames = energy / this.visibleNodes.length < 0.075 ? this.settledFrames + 1 : 0;
  }

  recoverNode(node, index) {
    if (isSafeNumber(node.x) && isSafeNumber(node.y) && Number.isFinite(node.vx) && Number.isFinite(node.vy)) return;
    const position = seededPosition(node.id || index, Math.max(900, Math.sqrt(Math.max(1, this.nodes.length)) * 130));
    node.x = position.x;
    node.y = position.y;
    node.vx = 0;
    node.vy = 0;
    node.ax = 0;
    node.ay = 0;
  }

  wake(duration = 300) {
    if (this.destroyed) return;
    if (this.reducedMotion) {
      this.requestFrame();
      return;
    }
    this.physicsUntil = Math.max(this.physicsUntil, performance.now() + duration);
    this.settledFrames = 0;
    this.requestFrame();
  }

  requestFrame() {
    if (this.destroyed || this.suspended || this.frameId !== null || globalThis.document?.hidden) return;
    const raf = globalThis.requestAnimationFrame;
    if (typeof raf === "function") this.frameId = raf((time) => this.frame(time));
    else this.draw(performance.now());
  }

  frame(time) {
    this.frameId = null;
    if (this.destroyed || this.suspended || globalThis.document?.hidden) return;
    if (time < this.physicsUntil && this.settledFrames < 45) this.tick();
    this.draw(time);
    if (time < this.physicsUntil && this.settledFrames < 45) this.requestFrame();
  }

  resize() {
    if (this.destroyed) return;
    const rect = this.canvas.getBoundingClientRect();
    const ratio = globalThis.devicePixelRatio || globalThis.window?.devicePixelRatio || 1;
    this.pixelRatio = ratio;
    this.canvas.width = Math.max(1, Math.floor(rect.width * ratio));
    this.canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    if (this.visibleNodes.length && !this.hasFitted) this.fitToView();
    else this.requestFrame();
  }

  toWorld(event) {
    const rect = this.canvas.getBoundingClientRect();
    return { x: (event.clientX - rect.left - this.transform.x) / this.transform.scale, y: (event.clientY - rect.top - this.transform.y) / this.transform.scale };
  }

  hitTest(event) {
    const point = this.toWorld(event);
    for (let index = this.visibleNodes.length - 1; index >= 0; index -= 1) {
      const node = this.visibleNodes[index];
      if (Math.hypot(point.x - node.x, point.y - node.y) <= node.radius + 5) return node;
    }
    return null;
  }

  onWheel(event) {
    event.preventDefault();
    const rect = this.canvas.getBoundingClientRect();
    const cursor = { x: event.clientX - rect.left, y: event.clientY - rect.top };
    const world = { x: (cursor.x - this.transform.x) / this.transform.scale, y: (cursor.y - this.transform.y) / this.transform.scale };
    const nextScale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, this.transform.scale * Math.exp(-event.deltaY * 0.001)));
    this.transform.x = cursor.x - world.x * nextScale;
    this.transform.y = cursor.y - world.y * nextScale;
    this.transform.scale = nextScale;
    this.requestFrame();
  }

  onPointerDown(event) {
    this.canvas.setPointerCapture?.(event.pointerId);
    const node = this.hitTest(event);
    if (node && event.shiftKey && this.focusedId && node.id !== this.focusedId) {
      this.selectPathTo(node.id);
      return;
    }
    if (node) {
      this.focusNode(node.id);
      node.dragged = true;
      this.drag = { kind: "node", node };
      this.canvas.style.cursor = "grabbing";
    } else this.drag = { kind: "pan", x: event.clientX, y: event.clientY, originX: this.transform.x, originY: this.transform.y };
    this.wake(520);
  }

  onPointerMove(event) {
    const node = this.hitTest(event);
    const hoveredId = node?.id || null;
    if (hoveredId !== this.hoveredId) {
      this.hoveredId = hoveredId;
      this.updateRelated();
      this.callbacks.onHover?.(node);
    }
    if (this.drag?.kind === "node") {
      const point = this.toWorld(event);
      Object.assign(this.drag.node, { x: point.x, y: point.y, vx: 0, vy: 0 });
      this.wake(160);
    } else if (this.drag?.kind === "pan") {
      this.transform.x = this.drag.originX + event.clientX - this.drag.x;
      this.transform.y = this.drag.originY + event.clientY - this.drag.y;
      this.requestFrame();
    } else {
      this.canvas.style.cursor = node ? "pointer" : "grab";
      this.requestFrame();
    }
  }

  onPointerUp(event) {
    if (this.drag?.kind === "node") this.drag.node.dragged = false;
    this.drag = null;
    this.canvas.style.cursor = this.hoveredId ? "pointer" : "grab";
    this.canvas.releasePointerCapture?.(event.pointerId);
    this.wake(220);
  }

  onVisibilityChange() {
    if (globalThis.document?.hidden) this.suspend();
    else this.resume();
  }

  suspend() {
    this.suspended = true;
    if (this.frameId !== null && typeof globalThis.cancelAnimationFrame === "function") globalThis.cancelAnimationFrame(this.frameId);
    this.frameId = null;
  }

  resume() {
    if (this.destroyed) return;
    this.suspended = false;
    this.resize();
  }

  draw() {
    const ctx = this.context;
    const ratio = this.pixelRatio || 1;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.setTransform(ratio * this.transform.scale, 0, 0, ratio * this.transform.scale, ratio * this.transform.x, ratio * this.transform.y);
    const hasRelated = this.relatedIds.size > 0;
    ctx.lineWidth = 1 / this.transform.scale;
    for (const edge of this.visibleEdges) {
      const source = this.nodeById.get(edge.source);
      const target = this.nodeById.get(edge.target);
      const highlighted = this.pathIds.has(source.id) && this.pathIds.has(target.id);
      ctx.globalAlpha = highlighted ? 0.9 : (!hasRelated || this.relatedIds.has(source.id) || this.relatedIds.has(target.id) ? 0.34 : 0.1);
      ctx.strokeStyle = highlighted ? "#43c7f4" : "#516072";
      ctx.beginPath(); ctx.moveTo(source.x, source.y); ctx.lineTo(target.x, target.y); ctx.stroke();
    }
    for (const node of this.visibleNodes) {
      ctx.globalAlpha = !hasRelated || this.relatedIds.has(node.id) ? 1 : 0.1;
      ctx.fillStyle = TYPE_COLORS[node.type] || "#d9e1eb";
      ctx.beginPath(); ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2); ctx.fill();
    }
    if (this.labelsVisible) this.drawLabels(ctx);
    ctx.globalAlpha = 1;
  }

  drawLabels(ctx) {
    const fontSize = 12 / this.transform.scale;
    ctx.font = `${fontSize}px ui-monospace, SFMono-Regular, Consolas, monospace`;
    const candidates = this.visibleNodes.slice().sort((left, right) => right.degree - left.degree).slice(0, 120).map((node) => {
      const width = ctx.measureText(String(node.title || node.id)).width;
      return { id: node.id, node, importance: node.degree, left: node.x + node.radius + 4 / this.transform.scale, right: node.x + node.radius + width + 8 / this.transform.scale, top: node.y - fontSize * 0.7, bottom: node.y + fontSize * 0.7 };
    });
    ctx.fillStyle = "#d9e1eb";
    for (const label of resolveLabelCollisions(candidates)) {
      ctx.globalAlpha = this.relatedIds.size && !this.relatedIds.has(label.node.id) ? 0.1 : 1;
      ctx.fillText(String(label.node.title || label.node.id), label.left, label.node.y + fontSize * 0.35);
    }
  }

  destroy() {
    if (this.destroyed) return;
    this.destroyed = true;
    this.suspend();
    this.resizeObserver?.disconnect();
    this.canvas.removeEventListener("wheel", this.onWheel);
    this.canvas.removeEventListener("pointerdown", this.onPointerDown);
    this.canvas.removeEventListener("pointermove", this.onPointerMove);
    this.canvas.removeEventListener("pointerup", this.onPointerUp);
    this.canvas.removeEventListener("pointercancel", this.onPointerUp);
    globalThis.document?.removeEventListener("visibilitychange", this.onVisibilityChange);
  }
}
