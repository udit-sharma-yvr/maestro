const runBtn = document.getElementById("run");
const promptEl = document.getElementById("prompt");
const timeline = document.getElementById("timeline");
const costEl = document.getElementById("cost");
const statusEl = document.getElementById("status");

runBtn.addEventListener("click", async () => {
  const prompt = promptEl.value.trim();
  if (!prompt) return;
  runBtn.disabled = true;
  timeline.innerHTML = "";
  costEl.textContent = "$0.000000";
  statusEl.textContent = "starting…";

  let res;
  try {
    res = await fetch("/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
  } catch (e) {
    statusEl.textContent = "request failed";
    runBtn.disabled = false;
    return;
  }

  const { task_id, error } = await res.json();
  if (error) {
    statusEl.textContent = error;
    runBtn.disabled = false;
    return;
  }

  const scheme = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${scheme}://${location.host}/stream/${task_id}`);
  ws.onmessage = (e) => render(JSON.parse(e.data));
  ws.onclose = () => {
    runBtn.disabled = false;
  };
  ws.onerror = () => {
    statusEl.textContent = "stream error";
    runBtn.disabled = false;
  };
});

function render(ev) {
  // Cost events update the header counter; no timeline row.
  if (ev.type === "cost") {
    const t = ev.total;
    costEl.textContent = `$${t.total_cost.toFixed(6)}  (${t.input_tokens}↑ / ${t.output_tokens}↓)`;
    return;
  }

  const row = document.createElement("div");
  row.className = `event ${ev.type.replace(/[.]/g, "-")}`;

  switch (ev.type) {
    case "task.start":
      row.innerHTML = `<b>Task</b> — ${escapeHtml(ev.prompt)}`;
      statusEl.textContent = "running";
      break;
    case "route":
      row.innerHTML = `<b>Route</b> → ${ev.decision} <span class="muted">(${ev.model})</span>`;
      break;
    case "agent.message": {
      const calls = ev.tool_calls?.length
        ? `<ul class="calls">${ev.tool_calls
            .map((t) => `<li>🔧 ${escapeHtml(t.name)}(${escapeHtml(JSON.stringify(t.args))})</li>`)
            .join("")}</ul>`
        : "";
      row.innerHTML =
        `<b>Agent</b> <span class="muted">(${ev.model})</span>` +
        `<pre>${escapeHtml(ev.content || "(calling tools)")}</pre>${calls}`;
      break;
    }
    case "tool.result":
      row.innerHTML = `<b>Tool result</b> · ${escapeHtml(ev.name)}<pre>${escapeHtml(ev.result)}</pre>`;
      break;
    case "answer":
      row.innerHTML = `<b>Answer</b><pre class="answer">${escapeHtml(ev.content)}</pre>`;
      statusEl.textContent = "done";
      break;
    case "task.end":
      row.innerHTML = `<b class="muted">Done</b>`;
      break;
    case "error":
      row.innerHTML = `<b>Error</b> ${escapeHtml(ev.message)}`;
      statusEl.textContent = "error";
      break;
    default:
      row.innerHTML = `<b>${escapeHtml(ev.type)}</b>`;
  }

  timeline.appendChild(row);
  timeline.scrollTop = timeline.scrollHeight;
}

function escapeHtml(s) {
  return (s ?? "").toString().replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}
