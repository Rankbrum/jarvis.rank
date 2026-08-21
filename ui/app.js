const statusElement = document.querySelector("[data-status]");

try {
  const response = await fetch("/api/status");
  const payload = await response.json();
  statusElement.textContent = payload.ok
    ? `Demo: ${payload.data.demo_mode ? "ON" : "OFF"}`
    : "STATUS UNAVAILABLE";
} catch {
  statusElement.textContent = "STATUS UNAVAILABLE";
}
