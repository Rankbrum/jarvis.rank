import assert from "node:assert/strict";

let moduleSerial = 0;

class FakeElement {
  constructor(tagName = "div") {
    this.tagName = tagName.toUpperCase();
    this.children = [];
    this.dataset = {};
    this.attributes = {};
    this.listeners = new Map();
    this.style = { setProperty: () => {} };
    this.className = "";
    this.disabled = false;
    this.value = "";
    this.placeholder = "";
    this.parentElement = null;
    this._text = "";
  }

  set textContent(value) {
    this._text = String(value);
    this.children = [];
  }

  get textContent() {
    return this._text + this.children.map((child) => child.textContent).join("");
  }

  append(...nodes) {
    this._text = "";
    for (const node of nodes) {
      node.parentElement = this;
      this.children.push(node);
    }
  }

  replaceChildren(...nodes) {
    this.children = [];
    this._text = "";
    this.append(...nodes);
  }

  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  removeAttribute(name) { delete this.attributes[name]; }
  addEventListener(type, handler) { this.listeners.set(type, [...(this.listeners.get(type) || []), handler]); }
  removeEventListener(type, handler) {
    const remaining = (this.listeners.get(type) || []).filter((candidate) => candidate !== handler);
    if (remaining.length) this.listeners.set(type, remaining); else this.listeners.delete(type);
  }
  dispatchEvent(event) {
    event.target ||= this;
    for (const handler of this.listeners.get(event.type) || []) handler(event);
    return true;
  }
  click() {
    if (this.disabled) return;
    this.focus();
    this.dispatchEvent({ type: "click", target: this, preventDefault() {} });
  }
  focus() { this.ownerDocument.activeElement = this; }
  contains(node) { return node === this || this.children.some((child) => child.contains(node)); }
  matches(selector) {
    if (selector === "button") return this.tagName === "BUTTON";
    if (selector === ".type-filter") return this.className.split(/\s+/).includes("type-filter");
    if (selector.startsWith("#")) return this.attributes.id === selector.slice(1);
    return false;
  }
  closest(selector) {
    let current = this;
    while (current) {
      if (current.matches(selector)) return current;
      current = current.parentElement;
    }
    return null;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  querySelectorAll(selector) {
    const found = [];
    const walk = (node) => {
      for (const child of node.children) {
        if (child.matches(selector) || (selector === "[data-reactor-label]" && "reactorLabel" in child.dataset)) found.push(child);
        walk(child);
      }
    };
    walk(this);
    return found;
  }
}

class FakeCanvas extends FakeElement {
  constructor() { super("canvas"); this.width = 0; this.height = 0; this.context = { transforms: [], setTransform(...values) { this.transforms.push(values); }, clearRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}, arc() {}, fill() {}, fillText() {}, measureText(text) { return { width: String(text).length * 7 }; } }; }
  getContext() { return this.context; }
  getBoundingClientRect() { return { left: 0, top: 0, width: 640, height: 420 }; }
  setPointerCapture() {}
  releasePointerCapture() {}
}

class FakeDocument {
  constructor() {
    this.documentElement = new FakeElement("html");
    this.body = new FakeElement("body");
    this.documentElement.append(this.body);
    this.bySelector = new Map();
    this.groups = new Map();
    this.listeners = new Map();
    this.activeElement = this.body;
    this.register("body", this.body);
    this.register("html", this.documentElement);
  }

  register(selector, element, group) {
    element.ownerDocument = this;
    this.bySelector.set(selector, element);
    if (group) this.groups.set(group, [...(this.groups.get(group) || []), element]);
    return element;
  }

  createElement(tagName) {
    const element = new FakeElement(tagName);
    element.ownerDocument = this;
    return element;
  }

  querySelector(selector) {
    if (selector.startsWith("#")) return this.bySelector.get(selector) || null;
    if (selector.startsWith("[data-panel-toggle=") || selector.startsWith("[data-panel-open=")) return this.querySelectorAll(selector)[0] || null;
    return this.bySelector.get(selector) || null;
  }

  querySelectorAll(selector) {
    if (selector === "[data-action]") return this.groups.get("actions") || [];
    if (selector === "[data-panel-toggle], [data-panel-open]") return this.groups.get("panels") || [];
    if (selector === "[data-graph-action]") return this.groups.get("graphActions") || [];
    if (selector === "[data-graph-keyboard-action]") return this.groups.get("graphKeyboardActions") || [];
    const matches = [...selector.matchAll(/data-panel-(?:toggle|open)="([^"]+)"/g)].map((match) => match[1]);
    if (matches.length) return (this.groups.get("panels") || []).filter((element) => matches.includes(element.dataset.panelToggle || element.dataset.panelOpen));
    return [];
  }

  addEventListener(type, handler) { this.listeners.set(type, [...(this.listeners.get(type) || []), handler]); }
  removeEventListener(type, handler) {
    const remaining = (this.listeners.get(type) || []).filter((candidate) => candidate !== handler);
    if (remaining.length) this.listeners.set(type, remaining); else this.listeners.delete(type);
  }
  dispatchEvent(event) {
    for (const handler of this.listeners.get(event.type) || []) handler(event);
    return true;
  }
}

class FakeWindow {
  constructor() {
    this.listeners = new Map();
    this.timers = [];
    this.nextTimer = 1;
  }

  addEventListener(type, handler) { this.listeners.set(type, [...(this.listeners.get(type) || []), handler]); }
  dispatchEvent(event) {
    for (const handler of this.listeners.get(event.type) || []) handler(event);
    return true;
  }
  setTimeout(callback) {
    const timer = { id: this.nextTimer++, callback, cancelled: false };
    this.timers.push(timer);
    return timer.id;
  }
  clearTimeout(id) {
    const timer = this.timers.find((candidate) => candidate.id === id);
    if (timer) timer.cancelled = true;
  }
  runTimers() {
    const timers = this.timers.splice(0);
    for (const timer of timers) if (!timer.cancelled) timer.callback();
  }
}

class FakeCustomEvent {
  constructor(type, init = {}) { this.type = type; this.detail = init.detail; }
}

function response(data) {
  return { ok: true, json: async () => ({ ok: true, data }) };
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((nextResolve, nextReject) => { resolve = nextResolve; reject = nextReject; });
  return { promise, resolve, reject };
}

function buildEnvironment() {
  const document = new FakeDocument();
  const element = (selector, tagName = "div") => document.register(selector, document.createElement(tagName));
  const messages = element("#messages");
  const card = element("#response-card");
  const detected = element("#detected-text", "p");
  const form = element("#ask-form", "form");
  const input = element("#ask-input", "input");
  const reactor = element("#reactor", "section");
  const canvas = document.register("#graph-canvas", new FakeCanvas());
  canvas.ownerDocument = document;
  const reactorLabel = document.createElement("strong");
  reactorLabel.dataset.reactorLabel = "";
  reactor.append(reactorLabel);
  const inspector = element("#inspector", "aside");
  const filters = element("#filters", "aside");
  for (const selector of ["#mode-badge", "[data-status]", "[data-status-data]", "[data-status-model]", "[data-status-voice]", "[data-graph-count]", "[data-type-filters]", "[data-top-hubs]", "[data-inspector-content]", "#graph-node-select", "#graph-feedback"]) element(selector);
  document.body.append(messages, card, detected, form, input, reactor, canvas, inspector, filters);

  for (const action of ["brief", "plan", "memory"]) {
    const button = document.createElement("button");
    button.dataset.action = action;
    document.register(`[data-action=${action}]`, button, "actions");
  }
  for (const panelId of ["inspector", "filters"]) {
    const opener = document.createElement("button");
    opener.dataset.panelOpen = panelId;
    opener.setAttribute("aria-expanded", "false");
    document.register(`[data-panel-open=${panelId}]`, opener, "panels");
    const closer = document.createElement("button");
    closer.dataset.panelToggle = panelId;
    closer.setAttribute("aria-expanded", "false");
    document.register(`[data-panel-toggle=${panelId}]`, closer, "panels");
    (panelId === "inspector" ? inspector : filters).append(closer);
  }
  const graphAction = document.createElement("button");
  graphAction.dataset.graphAction = "fit";
  document.register("[data-graph-action=fit]", graphAction, "graphActions");
  for (const action of ["focus", "path"]) {
    const button = document.createElement("button");
    button.dataset.graphKeyboardAction = action;
    document.register(`[data-graph-keyboard-action=${action}]`, button, "graphKeyboardActions");
  }
  const window = new FakeWindow();
  return { document, window, elements: { messages, card, detected, form, input, reactor, inspector, filters, canvas } };
}

async function flush() {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}

async function loadApp(fetchImpl) {
  const environment = buildEnvironment();
  globalThis.document = environment.document;
  globalThis.window = environment.window;
  globalThis.CustomEvent = FakeCustomEvent;
  globalThis.fetch = fetchImpl;
  const url = new URL(`../ui/app.js?runtime=${moduleSerial++}`, import.meta.url);
  const app = await import(url.href);
  await flush();
  return { ...environment, app };
}

function standardFetch(extra = {}) {
  const defaults = {
    "/api/status": () => response({ assistant_mode: "limited", model_connected: false, voice_configured: false, data_source: "demo", indexed_documents: 2 }),
    "/api/graph": () => response({ nodes: [] }),
  };
  return async (path, options) => {
    const handler = extra[path] || defaults[path];
    if (!handler) throw new Error(`Unexpected request: ${path}`);
    return handler(options);
  };
}

async function testReactorEventDetail() {
  const document = new FakeDocument();
  const reactor = document.register("#reactor", document.createElement("section"));
  const label = document.createElement("strong"); label.dataset.reactorLabel = ""; reactor.append(label);
  document.body.append(reactor);
  const window = new FakeWindow();
  globalThis.document = document;
  globalThis.window = window;
  globalThis.CustomEvent = FakeCustomEvent;
  const reactorModule = await import(new URL("../ui/reactor.js", import.meta.url).href);
  let detail;
  window.addEventListener("jarvis:state", (event) => { detail = event.detail; });
  reactorModule.setAssistantState(reactorModule.ASSISTANT_STATES.LISTENING);
  assert.deepEqual(detail, { state: "LISTENING" });
  assert.equal(reactor.dataset.state, "LISTENING");
  assert.equal(label.textContent, "LISTENING");
}

async function testStaleRecoveryDoesNotResetNewRequest() {
  const secondChat = deferred();
  let chats = 0;
  const { app, window, elements } = await loadApp(standardFetch({
    "/api/chat": () => (++chats === 1 ? Promise.reject(Object.assign(new Error("offline"), { code: "OFFLINE" })) : secondChat.promise),
  }));
  await assert.rejects(app.submitText("primeira"), /offline/);
  const second = app.submitText("segunda");
  assert.equal(elements.reactor.dataset.state, "THINKING");
  window.runTimers();
  assert.equal(elements.reactor.dataset.state, "THINKING", "an earlier recovery timer must not reset a newer request");
  secondChat.resolve(response({ spoken: "feito", card: { type: "conversation", text: "feito" } }));
  await second;
  assert.equal(elements.reactor.dataset.state, "IDLE");
}

async function testMemoryConfirmationIsOneShot() {
  const memoryRequest = deferred();
  let requests = 0;
  const { document, elements } = await loadApp(standardFetch({
    "/api/remember": () => { requests += 1; return memoryRequest.promise; },
  }));
  document.querySelectorAll("[data-action]").find((button) => button.dataset.action === "memory").click();
  elements.input.value = "Priorizar vendas";
  elements.form.dispatchEvent({ type: "submit", preventDefault() {}, target: elements.form });
  const [confirm] = elements.card.querySelectorAll("button");
  confirm.click();
  confirm.click();
  assert.equal(requests, 1, "double click must not create duplicate memory writes");
  assert.equal(confirm.disabled, true, "confirmation controls are disabled immediately");
  memoryRequest.resolve(response({ spoken: "Salvei.", card: { type: "memory", fact: "Priorizar vendas" } }));
  await flush();
  assert.equal(elements.reactor.dataset.state, "IDLE");
}

async function testFailedMemorySaveRestoresRetryAndCancel() {
  const retryRequest = deferred();
  let requests = 0;
  const { document, elements } = await loadApp(standardFetch({
    "/api/remember": () => {
      requests += 1;
      return requests === 1
        ? Promise.reject(Object.assign(new Error("disk unavailable"), { code: "MEMORY_UNAVAILABLE" }))
        : retryRequest.promise;
    },
  }));
  document.querySelectorAll("[data-action]").find((button) => button.dataset.action === "memory").click();
  elements.input.value = "Priorizar vendas";
  elements.form.dispatchEvent({ type: "submit", preventDefault() {}, target: elements.form });
  const [confirm, cancel] = elements.card.querySelectorAll("button");
  confirm.click();
  await flush();
  assert.equal(requests, 1);
  assert.equal(confirm.disabled, false, "a failed save restores the retry control");
  assert.equal(cancel.disabled, false, "a failed save restores the cancel control");
  assert.match(elements.card.textContent, /Priorizar vendas/, "the pending fact remains visible for retry");
  confirm.click();
  assert.equal(requests, 2, "retry sends exactly one new write");
  retryRequest.resolve(response({ spoken: "Salvei.", card: { type: "memory", fact: "Priorizar vendas" } }));
  await flush();
  assert.equal(elements.reactor.dataset.state, "IDLE");
}

async function testStartupFailuresAreVisibleAndRecover() {
  const { elements, window, app } = await loadApp(async () => { throw Object.assign(new Error("Servidor local indisponível"), { code: "LOCAL_OFFLINE" }); });
  assert.equal(elements.reactor.dataset.state, "ERROR");
  assert.match(elements.detected.textContent, /Tente novamente|recarregue/i);
  app.renderCard({ type: "limited_mode", available_tools: ["brief_me"] });
  assert.match(elements.card.textContent, /LIMITED MODE/);
  window.runTimers();
  assert.equal(elements.reactor.dataset.state, "IDLE");
}

async function testLateStartupFailureDoesNotClobberActiveChat() {
  const status = deferred();
  const graph = deferred();
  const chat = deferred();
  const { app, document, elements } = await loadApp(async (path) => {
    if (path === "/api/status") return status.promise;
    if (path === "/api/graph") return graph.promise;
    if (path === "/api/chat") return chat.promise;
    throw new Error(`Unexpected request: ${path}`);
  });
  const request = app.submitText("continuar");
  assert.equal(elements.reactor.dataset.state, "THINKING");
  status.reject(Object.assign(new Error("status offline"), { code: "LOCAL_OFFLINE" }));
  graph.resolve(response({ nodes: [] }));
  await flush();
  assert.equal(elements.reactor.dataset.state, "THINKING", "late bootstrap failures must not replace active chat state");
  assert.match(document.querySelector("[data-status]").textContent, /Não foi possível verificar o sistema local/, "late status failures still update the visible status region");
  assert.match(document.querySelector("#mode-badge").textContent, /STATUS UNAVAILABLE/);
  chat.resolve(response({ spoken: "pronto", card: { type: "conversation", text: "pronto" } }));
  await request;
}

async function testMobilePanelsAreExclusiveAndRestoreFocus() {
  const { document, elements } = await loadApp(standardFetch());
  const inspectorOpen = document.querySelectorAll("[data-panel-toggle], [data-panel-open]").find((button) => button.dataset.panelOpen === "inspector");
  const filtersOpen = document.querySelectorAll("[data-panel-toggle], [data-panel-open]").find((button) => button.dataset.panelOpen === "filters");
  const inspectorClose = document.querySelectorAll("[data-panel-toggle], [data-panel-open]").find((button) => button.dataset.panelToggle === "inspector");
  inspectorOpen.click();
  assert.equal(elements.inspector.dataset.open, "true");
  filtersOpen.click();
  assert.equal(elements.filters.dataset.open, "true");
  assert.equal(elements.inspector.dataset.open, "false", "opening a second panel closes the first");
  assert.equal(inspectorOpen.getAttribute("aria-expanded"), "false");
  inspectorOpen.click();
  inspectorClose.focus();
  inspectorClose.click();
  assert.equal(elements.inspector.dataset.open, "false");
  assert.equal(document.activeElement, inspectorOpen, "close returns focus to its opener");
  filtersOpen.click();
  document.dispatchEvent({ type: "keydown", key: "Escape", preventDefault() {} });
  assert.equal(elements.filters.dataset.open, "false");
  assert.equal(document.activeElement, filtersOpen, "Escape returns focus to the active panel opener");
}

async function testLatestInspectorResponseWins() {
  const first = deferred();
  const second = deferred();
  const { document, window } = await loadApp(standardFetch({
    "/api/node/first": () => first.promise,
    "/api/node/second": () => second.promise,
  }));
  window.dispatchEvent(new FakeCustomEvent("jarvis:node", { detail: { id: "first" } }));
  window.dispatchEvent(new FakeCustomEvent("jarvis:node", { detail: { id: "second" } }));
  second.resolve(response({ title: "Segundo", type: "task" }));
  await flush();
  first.resolve(response({ title: "Primeiro", type: "project" }));
  await flush();
  assert.match(document.querySelector("[data-inspector-content]").textContent, /Segundo/, "a stale inspector response cannot overwrite the latest selected node");
}

async function testKeyboardGraphControlsFocusTheSelectedNode() {
  const { document } = await loadApp(standardFetch({
    "/api/graph": () => response({ nodes: [{ id: "a", title: "Alpha", type: "project" }, { id: "b", title: "Beta", type: "task" }, { id: "c", title: "Gamma", type: "lead" }], edges: [{ source: "a", target: "b" }] }),
    "/api/node/a": () => response({ title: "Alpha", type: "project" }),
    "/api/node/b": () => response({ title: "Beta", type: "task" }),
  }));
  const select = document.querySelector("#graph-node-select");
  select.value = "a";
  document.querySelectorAll("[data-graph-keyboard-action]").find((button) => button.dataset.graphKeyboardAction === "focus").click();
  await flush();
  assert.match(document.querySelector("[data-inspector-content]").textContent, /Alpha/, "semantic keyboard focus chooses a graph node and synchronizes the inspector");
  select.value = "b";
  document.querySelectorAll("[data-graph-keyboard-action]").find((button) => button.dataset.graphKeyboardAction === "path").click();
  await flush();
  assert.match(document.querySelector("[data-inspector-content]").textContent, /Beta/, "semantic keyboard path selection synchronizes the inspector with its second node");
  assert.match(document.querySelector("#graph-feedback").textContent, /Caminho com 2 nós: Alpha → Beta/, "path feedback announces the complete titled route outside the Canvas");
  select.value = "c";
  document.querySelectorAll("[data-graph-keyboard-action]").find((button) => button.dataset.graphKeyboardAction === "path").click();
  assert.match(document.querySelector("#graph-feedback").textContent, /Sem caminho entre Alpha e Gamma/, "unreachable path feedback is announced outside the Canvas");
  select.value = "missing";
  document.querySelectorAll("[data-graph-keyboard-action]").find((button) => button.dataset.graphKeyboardAction === "focus").click();
  assert.match(document.querySelector("#graph-feedback").textContent, /Não foi possível focar/, "failed focus feedback is announced outside the Canvas");
  const canvas = document.querySelector("#graph-canvas");
  const pressCanvasKey = (key) => {
    let prevented = false;
    canvas.dispatchEvent({ type: "keydown", key, preventDefault() { prevented = true; } });
    assert.equal(prevented, true, `${key} is handled by the actual Canvas keyboard listener`);
    return canvas.context.transforms.at(-1);
  };
  const beforePan = canvas.context.transforms.at(-1);
  const afterPan = pressCanvasKey("ArrowLeft");
  assert.notDeepEqual(afterPan, beforePan, "Canvas ArrowLeft pans the rendered graph");
  const afterZoom = pressCanvasKey("+");
  assert.notEqual(afterZoom[0], afterPan[0], "Canvas plus key changes graph zoom");
  const afterFit = pressCanvasKey("Home");
  assert.notEqual(afterFit[0], afterZoom[0], "Canvas Home restores the fitted zoom");
}

async function testPersistedPagehidePreservesTheGraph() {
  const { window, elements } = await loadApp(standardFetch());
  const listenerCount = elements.canvas.listeners.size;
  window.dispatchEvent({ type: "pagehide", persisted: true });
  assert.equal(elements.canvas.listeners.size, listenerCount, "bfcache pagehide suspends rather than destroys the graph");
  window.dispatchEvent({ type: "pageshow", persisted: true });
  assert.equal(elements.canvas.listeners.size, listenerCount, "bfcache pageshow resumes without duplicate Canvas listeners");
  window.dispatchEvent({ type: "pagehide", persisted: false });
  assert.equal(elements.canvas.listeners.has("wheel"), false, "a non-persisted pagehide cleans up graph pointer listeners while preserving the app keyboard handler");
}

await testReactorEventDetail();
await testStaleRecoveryDoesNotResetNewRequest();
await testMemoryConfirmationIsOneShot();
await testFailedMemorySaveRestoresRetryAndCancel();
await testStartupFailuresAreVisibleAndRecover();
await testLateStartupFailureDoesNotClobberActiveChat();
await testMobilePanelsAreExclusiveAndRestoreFocus();
await testLatestInspectorResponseWins();
await testKeyboardGraphControlsFocusTheSelectedNode();
await testPersistedPagehidePreservesTheGraph();
console.log("UI runtime tests passed");
