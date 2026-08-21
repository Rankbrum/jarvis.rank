import { ASSISTANT_STATES, getAssistantState, setAssistantState } from "./reactor.js";
import { KnowledgeGraph } from "./graph.js";

const CATEGORY_COLORS = ["#43c7f4", "#f6b83f", "#a48bff", "#44cf86", "#ef78ad", "#fa9947", "#d8e0e8"];
const messagesElement = document.querySelector("#messages");
const cardElement = document.querySelector("#response-card");
const detectedTextElement = document.querySelector("#detected-text");
const form = document.querySelector("#ask-form");
const input = document.querySelector("#ask-input");
let memoryMode = false;
let pendingMemory = null;
let recoveryTimer = null;
let stateGeneration = 0;
const panelOpeners = new Map();
let graphView = null;
let inspectorGeneration = 0;
let inspectorController = null;

export async function api(path, options = {}) {
  const response = await fetch(path, options);
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw requestError("INVALID_RESPONSE", "O servidor devolveu uma resposta inválida.");
  }
  if (!response.ok || !payload.ok) {
    throw requestError(payload?.error?.code || "REQUEST_FAILED", payload?.error?.message || "A solicitação não pôde ser concluída.");
  }
  return payload.data;
}

function requestError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}

function addMessage(role, text) {
  const message = document.createElement("article");
  message.className = `message message-${role}`;
  const label = document.createElement("span");
  label.className = "message-role";
  label.textContent = role === "user" ? "VOCÊ" : "JARVIS";
  const content = document.createElement("span");
  content.textContent = text;
  message.append(label, content);
  messagesElement.append(message);
  messagesElement.scrollTop = messagesElement.scrollHeight;
}

function showError(code, message) {
  detectedTextElement.textContent = `${code}: ${message} Tente novamente.`;
  detectedTextElement.dataset.error = "true";
}

function clearError() {
  detectedTextElement.textContent = "Texto é processado localmente.";
  delete detectedTextElement.dataset.error;
}

function setState(nextState) {
  stateGeneration += 1;
  if (recoveryTimer !== null) {
    window.clearTimeout(recoveryTimer);
    recoveryTimer = null;
  }
  setAssistantState(nextState);
  return stateGeneration;
}

function presentError(code, message) {
  showError(code, message);
  const errorGeneration = setState(ASSISTANT_STATES.ERROR);
  recoveryTimer = window.setTimeout(() => {
    recoveryTimer = null;
    if (stateGeneration === errorGeneration && getAssistantState() === ASSISTANT_STATES.ERROR) {
      setState(ASSISTANT_STATES.IDLE);
    }
  }, 1800);
}

export function renderCard(card) {
  cardElement.replaceChildren();
  if (!card || typeof card !== "object") return;
  const panel = document.createElement("section");
  panel.className = "response-card";
  const title = document.createElement("h3");
  title.textContent = String(card.type || "response").replaceAll("_", " ").toUpperCase();
  panel.append(title);
  const items = Array.isArray(card.items) ? card.items : [];
  if (items.length) {
    const list = document.createElement("ul");
    for (const item of items.slice(0, 5)) {
      const entry = document.createElement("li");
      entry.textContent = String(item?.title || item?.filename || item?.path || "Item disponível");
      list.append(entry);
    }
    panel.append(list);
  } else {
    const body = document.createElement("p");
    body.textContent = card.text || card.fact || card.path || describeCard(card);
    panel.append(body);
  }
  cardElement.append(panel);
}

function describeCard(card) {
  if (Array.isArray(card.available_tools)) return `Disponível: ${card.available_tools.join(", ")}.`;
  if (card.item?.title) return String(card.item.title);
  return "Resposta estruturada disponível.";
}

export async function submitText(text) {
  const message = String(text || "").trim();
  if (!message) return null;
  setState(ASSISTANT_STATES.THINKING);
  clearError();
  addMessage("user", message);
  try {
    const data = await api("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: message }) });
    addMessage("assistant", data.spoken);
    renderCard(data.card);
    setState(ASSISTANT_STATES.IDLE);
    return data;
  } catch (error) {
    presentError(error.code || "REQUEST_FAILED", error.message);
    throw error;
  }
}

async function submitAction(label, path) {
  setState(ASSISTANT_STATES.THINKING);
  clearError();
  addMessage("user", label);
  try {
    const data = await api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    addMessage("assistant", data.spoken);
    renderCard(data.card);
    setState(ASSISTANT_STATES.IDLE);
  } catch (error) {
    presentError(error.code || "REQUEST_FAILED", error.message);
  }
}

function stageMemoryConfirmation(text) {
  const fact = String(text || "").trim();
  if (!fact) {
    input.focus();
    return;
  }
  memoryMode = false;
  pendingMemory = { fact, submitting: false };
  input.placeholder = "Pergunte ao JARVIS";
  detectedTextElement.textContent = "Revise e confirme antes de gravar a memória.";
  cardElement.replaceChildren();
  const panel = document.createElement("section");
  panel.className = "response-card";
  const title = document.createElement("h3");
  title.textContent = "CONFIRMAR MEMÓRIA";
  const body = document.createElement("p");
  body.textContent = fact;
  const confirm = document.createElement("button");
  confirm.type = "button";
  confirm.textContent = "Confirmar e salvar";
  confirm.addEventListener("click", () => void submitMemory());
  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.textContent = "Cancelar";
  cancel.addEventListener("click", () => {
    pendingMemory = null;
    cardElement.replaceChildren();
    detectedTextElement.textContent = "Memória descartada.";
  });
  panel.append(title, body, confirm, cancel);
  cardElement.append(panel);
}

async function submitMemory() {
  if (!pendingMemory || pendingMemory.submitting) return;
  pendingMemory.submitting = true;
  const { fact } = pendingMemory;
  cardElement.querySelectorAll("button").forEach((button) => { button.disabled = true; });
  setState(ASSISTANT_STATES.THINKING);
  clearError();
  addMessage("user", `Salvar memória: ${fact}`);
  try {
    const data = await api("/api/remember", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ fact, confirmed: true }) });
    addMessage("assistant", data.spoken);
    renderCard(data.card);
    pendingMemory = null;
    setState(ASSISTANT_STATES.IDLE);
  } catch (error) {
    pendingMemory.submitting = false;
    cardElement.querySelectorAll("button").forEach((button) => { button.disabled = false; });
    const [retry] = cardElement.querySelectorAll("button");
    if (retry) retry.textContent = "Tentar salvar";
    presentError(error.code || "REQUEST_FAILED", error.message);
  }
}

function renderStatus(status) {
  const mode = status.assistant_mode === "connected" ? "CONNECTED" : "LIMITED MODE";
  const badge = document.querySelector("#mode-badge");
  badge.textContent = mode;
  badge.dataset.mode = status.assistant_mode || "limited";
  document.querySelector("[data-status]").textContent = status.model_connected ? "Modelo conectado · operações locais" : "LIMITED MODE — MODEL NOT CONNECTED";
  document.querySelector("[data-status-data]").textContent = `${String(status.data_source || "local").toUpperCase()} · ${status.indexed_documents || 0}`;
  document.querySelector("[data-status-model]").textContent = status.model_connected ? "CONNECTED" : "LIMITED";
  document.querySelector("[data-status-voice]").textContent = status.voice_configured ? "READY" : "OFFLINE";
}

function renderStatusUnavailable() {
  const badge = document.querySelector("#mode-badge");
  badge.textContent = "STATUS UNAVAILABLE";
  badge.dataset.mode = "limited";
  document.querySelector("[data-status]").textContent = "Não foi possível verificar o sistema local. Verifique o servidor e recarregue a página.";
  document.querySelector("[data-status-data]").textContent = "UNAVAILABLE";
  document.querySelector("[data-status-model]").textContent = "UNKNOWN";
  document.querySelector("[data-status-voice]").textContent = "UNKNOWN";
}

function renderGraphSummary(graph) {
  const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
  document.querySelector("[data-graph-count]").textContent = `${nodes.length} NÓS EM MEMÓRIA`;
  document.body.dataset.graphReady = "true";
  const totals = new Map();
  for (const node of nodes) {
    const type = String(node?.type || "other");
    totals.set(type, (totals.get(type) || 0) + 1);
  }
  const filterRoot = document.querySelector("[data-type-filters]");
  filterRoot.replaceChildren(...[...totals.entries()].sort().map(([type, count], index) => typeFilter(type, count, index)));
  renderTopHubs(nodes);
  renderGraphNodeOptions(nodes);
}

function renderGraphNodeOptions(nodes) {
  const select = document.querySelector("#graph-node-select");
  if (!select) return;
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Escolha um nó";
  const options = [...nodes].sort((left, right) => String(left?.title || left?.id).localeCompare(String(right?.title || right?.id))).map((node) => {
    const option = document.createElement("option");
    option.value = String(node.id);
    option.textContent = `${node.title || node.id} · ${node.type || "item"}`;
    return option;
  });
  select.replaceChildren(placeholder, ...options);
}

function typeFilter(type, count, index) {
  const filter = document.createElement("button");
  filter.type = "button";
  filter.className = "type-filter";
  filter.dataset.type = type;
  filter.setAttribute("aria-pressed", "true");
  filter.style.setProperty("--category-color", CATEGORY_COLORS[index % CATEGORY_COLORS.length]);
  const dot = document.createElement("span"); dot.className = "filter-dot";
  const label = document.createElement("span"); label.textContent = type;
  const total = document.createElement("small"); total.textContent = count;
  filter.append(dot, label, total);
  return filter;
}

function renderTopHubs(nodes) {
  const ranked = [...nodes].sort((left, right) => Number(right?.connections?.length || 0) - Number(left?.connections?.length || 0)).slice(0, 6);
  const list = document.querySelector("[data-top-hubs]");
  list.replaceChildren(...ranked.map((node, index) => {
    const row = document.createElement("li");
    const dot = document.createElement("span"); dot.className = `hub-dot ${["cyan", "amber", "violet", "green"][index % 4]}`;
    const label = document.createElement("span"); label.textContent = String(node?.title || "Sem título");
    const count = document.createElement("b"); count.textContent = String(node?.connections?.length || 0);
    row.append(dot, label, count);
    return row;
  }));
}

function announceGraph(message) {
  const feedback = document.querySelector("#graph-feedback");
  if (feedback) feedback.textContent = message;
}

function graphNodeTitle(id) {
  const node = graphView?.nodeById.get(id);
  return node?.title || id || "nó selecionado";
}

function initialiseGraph() {
  const canvas = document.querySelector("#graph-canvas");
  if (!canvas) return;
  graphView = new KnowledgeGraph(canvas, {
    onFocus: (node) => {
      if (!node) {
        announceGraph("Não foi possível focar o nó selecionado.");
        return;
      }
      announceGraph(`Foco em ${node.title || node.id}.`);
      window.dispatchEvent(new CustomEvent("jarvis:node", { detail: { id: node.id } }));
    },
    onPath: (path, targetId, status) => {
      if (!path.length) {
        if (status === "missing-focus") announceGraph("Selecione primeiro um nó para traçar um caminho.");
        else announceGraph(`Sem caminho entre ${graphNodeTitle(graphView?.focusedId)} e ${graphNodeTitle(targetId)}.`);
        return;
      }
      const route = path.map((id) => graphNodeTitle(id)).join(" → ");
      announceGraph(`Caminho com ${path.length} nós: ${route}.`);
      window.dispatchEvent(new CustomEvent("jarvis:node", { detail: { id: targetId } }));
    },
  });
  window.addEventListener("jarvis:graph", (event) => graphView?.setData(event.detail || {}));
  window.addEventListener("jarvis:filter", (event) => {
    const { type, enabled } = event.detail || {};
    if (type) graphView?.setTypeFilter(type, enabled);
  });
  window.addEventListener("jarvis:graph-action", (event) => {
    if (event.detail?.action === "fit") graphView?.fitToView();
    if (event.detail?.action === "labels") {
      const control = document.querySelector('[data-graph-action="labels"]');
      const visible = control?.getAttribute("aria-pressed") !== "false";
      graphView?.setLabelsVisible(visible);
    }
  });
  canvas.addEventListener("keydown", (event) => {
    const pan = 48;
    if (event.key === "ArrowLeft") graphView?.panBy(pan, 0);
    else if (event.key === "ArrowRight") graphView?.panBy(-pan, 0);
    else if (event.key === "ArrowUp") graphView?.panBy(0, pan);
    else if (event.key === "ArrowDown") graphView?.panBy(0, -pan);
    else if (event.key === "+" || event.key === "=") graphView?.zoomBy(1.18);
    else if (event.key === "-") graphView?.zoomBy(1 / 1.18);
    else if (event.key === "Home") graphView?.fitToView();
    else return;
    event.preventDefault();
  });
  window.addEventListener("pagehide", (event) => {
    if (event.persisted) graphView?.suspend();
    else graphView?.destroy();
  });
  window.addEventListener("pageshow", (event) => { if (event.persisted) graphView?.resume(); });
}

async function loadInspector(nodeId) {
  inspectorGeneration += 1;
  const generation = inspectorGeneration;
  inspectorController?.abort();
  inspectorController = typeof AbortController === "undefined" ? null : new AbortController();
  try {
    const node = await api(`/api/node/${encodeURIComponent(nodeId)}`, inspectorController ? { signal: inspectorController.signal } : {});
    if (generation !== inspectorGeneration) return;
    const root = document.querySelector("[data-inspector-content]");
    root.replaceChildren();
    const title = document.createElement("p");
    title.className = "panel-hint";
    title.textContent = `${node.title || "Nó"} · ${node.type || "item"}`;
    root.append(title);
  } catch (error) {
    if (generation !== inspectorGeneration || error?.name === "AbortError") return;
    presentError(error.code || "NODE_UNAVAILABLE", error.message);
  }
}

function panelControls(panelId) {
  return document.querySelectorAll(`[data-panel-toggle="${panelId}"], [data-panel-open="${panelId}"]`);
}

function setPanelOpen(panelId, isOpen, { opener = null, restoreFocus = true } = {}) {
  const panel = document.querySelector(`#${panelId}`);
  if (!panel) return;
  if (isOpen) {
    for (const otherId of ["inspector", "filters"]) {
      if (otherId !== panelId) setPanelOpen(otherId, false, { restoreFocus: false });
    }
    panelOpeners.set(panelId, opener || document.activeElement);
  }
  panel.dataset.open = String(isOpen);
  panelControls(panelId).forEach((control) => {
    control.setAttribute("aria-expanded", String(isOpen));
    if (control.dataset.panelToggle) control.textContent = isOpen ? "Fechar" : "Abrir";
  });
  if (!isOpen && restoreFocus) {
    const panelOpener = panelOpeners.get(panelId);
    if (panelOpener) panelOpener.focus();
  }
}

function initialiseInteractions() {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = input.value;
    input.value = "";
    if (memoryMode) {
      stageMemoryConfirmation(text);
      return;
    }
    try { await submitText(text); } catch { input.value = text; input.focus(); }
  });
  document.querySelectorAll("[data-action]").forEach((button) => button.addEventListener("click", () => {
    if (button.dataset.action === "brief") void submitAction("Brief Me", "/api/brief");
    else if (button.dataset.action === "plan") void submitAction("Plan Day", "/api/plan");
    else { memoryMode = true; input.placeholder = "Fato que JARVIS deve lembrar"; detectedTextElement.textContent = "Descreva o fato; enviaremos uma confirmação antes de salvar."; input.focus(); }
  }));
  document.querySelectorAll("[data-panel-toggle], [data-panel-open]").forEach((button) => button.addEventListener("click", () => {
    const panelId = button.dataset.panelToggle || button.dataset.panelOpen;
    const panel = document.querySelector(`#${panelId}`);
    const willOpen = panel.dataset.open !== "true";
    setPanelOpen(panelId, willOpen, { opener: button.dataset.panelOpen ? button : null, restoreFocus: !willOpen });
  }));
  document.querySelector("[data-type-filters]").addEventListener("click", (event) => {
    const filter = event.target.closest(".type-filter");
    if (!filter) return;
    const enabled = filter.getAttribute("aria-pressed") !== "true";
    filter.setAttribute("aria-pressed", String(enabled));
    window.dispatchEvent(new CustomEvent("jarvis:filter", { detail: { type: filter.dataset.type, enabled } }));
  });
  document.querySelectorAll("[data-graph-action]").forEach((button) => button.addEventListener("click", () => {
    if (button.dataset.graphAction === "labels") button.setAttribute("aria-pressed", String(button.getAttribute("aria-pressed") !== "true"));
    window.dispatchEvent(new CustomEvent("jarvis:graph-action", { detail: { action: button.dataset.graphAction } }));
  }));
  document.querySelectorAll("[data-graph-keyboard-action]").forEach((button) => button.addEventListener("click", () => {
    const nodeId = document.querySelector("#graph-node-select")?.value;
    if (!nodeId) { announceGraph("Escolha um nó do grafo primeiro."); return; }
    if (button.dataset.graphKeyboardAction === "focus" && !graphView?.centerOnNode(nodeId)) announceGraph("Não foi possível focar o nó selecionado.");
    if (button.dataset.graphKeyboardAction === "path") graphView?.selectPathTo(nodeId);
  }));
  window.addEventListener("jarvis:node", (event) => { if (event.detail?.id) void loadInspector(event.detail.id); });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    for (const panelId of ["inspector", "filters"]) {
      const panel = document.querySelector(`#${panelId}`);
      if (panel?.dataset.open === "true") {
        event.preventDefault();
        setPanelOpen(panelId, false);
        break;
      }
    }
  });
}

async function initialise() {
  initialiseGraph();
  initialiseInteractions();
  setState(ASSISTANT_STATES.IDLE);
  const startupGeneration = stateGeneration;
  const [status, graph] = await Promise.allSettled([api("/api/status"), api("/api/graph")]);
  if (status.status === "fulfilled") renderStatus(status.value);
  else renderStatusUnavailable();
  if (graph.status === "fulfilled") {
    renderGraphSummary(graph.value);
    window.dispatchEvent(new CustomEvent("jarvis:graph", { detail: graph.value }));
  } else {
    document.querySelector("[data-graph-count]").textContent = "GRAFO INDISPONÍVEL";
  }
  if (stateGeneration !== startupGeneration) return;
  if (status.status === "rejected" && graph.status === "rejected") {
    presentError("STARTUP_UNAVAILABLE", "O sistema e o grafo local não responderam. Verifique o servidor e recarregue a página.");
  } else if (status.status === "rejected") {
    presentError("STATUS_UNAVAILABLE", "Não foi possível verificar o sistema local. Verifique o servidor e recarregue a página.");
  } else if (graph.status === "rejected") {
    presentError("GRAPH_UNAVAILABLE", "O grafo local não respondeu. Você pode tentar novamente recarregando a página.");
  }
}

void initialise();
