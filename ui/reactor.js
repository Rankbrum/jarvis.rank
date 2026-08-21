export const ASSISTANT_STATES = Object.freeze({
  IDLE: "IDLE",
  LISTENING: "LISTENING",
  THINKING: "THINKING",
  SPEAKING: "SPEAKING",
  ERROR: "ERROR",
});

let currentState = ASSISTANT_STATES.IDLE;

export function setAssistantState(nextState) {
  if (!Object.values(ASSISTANT_STATES).includes(nextState)) {
    throw new Error(`Unknown assistant state: ${nextState}`);
  }

  currentState = nextState;
  document.documentElement.dataset.assistantState = nextState.toLowerCase();

  const reactor = document.querySelector("#reactor");
  if (reactor) {
    reactor.dataset.state = nextState;
    const label = reactor.querySelector("[data-reactor-label]");
    if (label) label.textContent = nextState;
  }

  window.dispatchEvent(new CustomEvent("jarvis:state", { detail: { state: nextState } }));
}

export function getAssistantState() {
  return currentState;
}
