// ═══════════════════════════════════════════════
//  N E X U S  —  Terminal UI
// ═══════════════════════════════════════════════

let ws = null;
let streaming = false;
let currentBlock = null;
let rawText = '';
let history = [];
let historyIdx = -1;

const $ = (s) => document.querySelector(s);
const output = () => $('#output');
const input = () => $('#input');
const terminal = () => $('#terminal');

// ── Boot ──
async function boot() {
  const el = $('#boot-text');
  const lines = [
    '██████╗  NEXUS SYSTEM v1.0',
    '██╔══██╗ Neural Execution & Unified System',
    '██║  ██║ ────────────────────────────────',
    '██║  ██║ Connecting to Claude Code...',
    '██████╔╝ All systems operational.',
    '',
    '███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗',
    '████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝',
    '██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗',
    '██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║',
    '██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║',
    '╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝',
    '',
    'Ready.',
  ];

  for (const line of lines) {
    el.textContent += line + '\n';
    await sleep(50 + Math.random() * 40);
  }

  await sleep(500);
  $('#boot').classList.add('hidden');
  setTimeout(() => $('#boot').remove(), 400);

  // Print welcome in terminal
  appendSystem('');
  appendBanner();
  appendSystem('');
  appendSystem('Type a command. Ctrl+C to abort. "clear" to reset.\n');
  input().focus();
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── WebSocket ──
function connect() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${proto}//${location.host}/ws`);

  ws.onopen = () => setStatus('ready');
  ws.onclose = () => {
    setStatus('error', 'DISCONNECTED');
    setTimeout(connect, 3000);
  };
  ws.onerror = () => setStatus('error', 'ERROR');
  ws.onmessage = (e) => handle(JSON.parse(e.data));
}

function setStatus(state, text) {
  const dot = $('#status-dot');
  const lbl = $('#status-text');
  dot.className = 'tb-dot' + (state === 'thinking' ? ' thinking' : state === 'error' ? ' error' : '');
  lbl.textContent = text || (state === 'ready' ? 'READY' : state === 'thinking' ? 'WORKING' : 'ERROR');
}

// ── Handle messages ──
function handle(data) {
  switch (data.type) {
    case 'stream_start':
      streaming = true;
      rawText = '';
      setStatus('thinking');
      currentBlock = document.createElement('div');
      currentBlock.className = 'line-response cursor-blink';
      output().appendChild(currentBlock);
      scroll();
      break;

    case 'stream_chunk':
      rawText += data.content;
      if (currentBlock) {
        currentBlock.innerHTML = renderMd(rawText);
        scroll();
      }
      break;

    case 'tool_use':
      const tool = document.createElement('div');
      tool.className = 'line-tool';
      tool.textContent = `  ⚡ ${data.tool}${data.content ? ': ' + data.content.slice(0, 120) : ''}`;
      // Insert before current response block
      if (currentBlock) {
        output().insertBefore(tool, currentBlock);
      } else {
        output().appendChild(tool);
      }
      scroll();
      break;

    case 'stream_end':
      streaming = false;
      setStatus('ready');
      if (currentBlock) {
        currentBlock.classList.remove('cursor-blink');
        // Final render
        if (rawText) currentBlock.innerHTML = renderMd(rawText);
      }
      currentBlock = null;
      bumpMsgCount();
      appendBreak();
      enableInput();
      scroll();
      break;

    case 'error':
      streaming = false;
      setStatus('ready');
      if (currentBlock) currentBlock.classList.remove('cursor-blink');
      currentBlock = null;
      appendError(data.content);
      appendBreak();
      enableInput();
      break;

    case 'status':
      break;

    case 'model_changed':
      updateModelDisplay(data.model);
      break;
  }
}

// ── Output helpers ──
function appendSystem(text) {
  const el = document.createElement('div');
  el.className = 'line-system';
  el.textContent = text;
  output().appendChild(el);
  scroll();
}

function appendPrompt(cmd) {
  const el = document.createElement('div');
  el.className = 'line-prompt';
  el.innerHTML = `nexus <span style="color:var(--green)">❯</span> <span class="cmd">${escHtml(cmd)}</span>`;
  output().appendChild(el);
  scroll();
}

function appendError(text) {
  const el = document.createElement('div');
  el.className = 'line-error';
  el.textContent = '✗ ' + text;
  output().appendChild(el);
  scroll();
}

function appendBreak() {
  const el = document.createElement('div');
  el.className = 'line-break';
  output().appendChild(el);
}

function appendBanner() {
  const banner = `
  ██╗  ██╗███████╗██╗     ██╗      ██████╗
  ██║  ██║██╔════╝██║     ██║     ██╔═══██╗
  ███████║█████╗  ██║     ██║     ██║   ██║
  ██╔══██║██╔══╝  ██║     ██║     ██║   ██║
  ██║  ██║███████╗███████╗███████╗╚██████╔╝
  ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝ ╚═════╝

  ███╗   ███╗██████╗    ███╗   ███╗██╗   ██╗██╗  ██╗ █████╗ ███╗   ███╗███╗   ███╗ █████╗ ██████╗
  ████╗ ████║██╔══██╗   ████╗ ████║██║   ██║██║  ██║██╔══██╗████╗ ████║████╗ ████║██╔══██╗██╔══██╗
  ██╔████╔██║██████╔╝   ██╔████╔██║██║   ██║███████║███████║██╔████╔██║██╔████╔██║███████║██║  ██║
  ██║╚██╔╝██║██╔══██╗   ██║╚██╔╝██║██║   ██║██╔══██║██╔══██║██║╚██╔╝██║██║╚██╔╝██║██╔══██║██║  ██║
  ██║ ╚═╝ ██║██║  ██║██╗██║ ╚═╝ ██║╚██████╔╝██║  ██║██║  ██║██║ ╚═╝ ██║██║ ╚═╝ ██║██║  ██║██████╔╝
  ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═════╝

  ██████╗  █████╗ ███████╗██╗  ██╗██╗██████╗
  ██╔══██╗██╔══██╗██╔════╝██║  ██║██║██╔══██╗
  ██████╔╝███████║███████╗███████║██║██║  ██║
  ██╔══██╗██╔══██║╚════██║██╔══██║██║██║  ██║
  ██║  ██║██║  ██║███████║██║  ██║██║██████╔╝
  ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝╚═════╝
`.trimEnd();

  const el = document.createElement('pre');
  el.style.cssText = 'color: var(--cyan); font-size: 10px; line-height: 1.2; text-shadow: 0 0 12px rgba(255,26,26,0.5); margin: 8px 0;';
  el.textContent = banner;
  output().appendChild(el);
  scroll();
}

function scroll() {
  terminal().scrollTop = terminal().scrollHeight;
}

// ── Input ──
function send() {
  const el = input();
  const text = el.value.trim();
  if (!text || streaming) return;

  // Local commands
  if (text === 'clear') {
    output().innerHTML = '';
    appendSystem('Terminal cleared.\n');
    el.value = '';
    autosize(el);
    return;
  }

  if (text === 'exit' || text === 'quit') {
    appendSystem('Closing NEXUS...');
    setTimeout(() => window.close(), 500);
    el.value = '';
    return;
  }

  // Save to history
  history.unshift(text);
  if (history.length > 200) history.pop();
  historyIdx = -1;

  // Echo the command
  appendPrompt(text);
  bumpMsgCount();

  // Disable input
  disableInput();

  // Send to server
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'prompt', content: text }));
  }

  el.value = '';
  autosize(el);
}

function disableInput() {
  input().classList.add('disabled');
  input().disabled = true;
}

function enableInput() {
  const el = input();
  el.classList.remove('disabled');
  el.disabled = false;
  el.focus();
}

function autosize(el) {
  el.style.height = 'auto';
  el.style.height = el.scrollHeight + 'px';
}

// ── Markdown renderer ──
function renderMd(text) {
  if (!text) return '';
  let h = escHtml(text);

  // Code blocks
  h = h.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code>${code.trim()}</code></pre>`);

  // Inline code
  h = h.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Bold
  h = h.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  // Italic
  h = h.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');

  // Headers
  h = h.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  h = h.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  h = h.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // Blockquote
  h = h.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

  // Lists
  h = h.replace(/^- (.+)$/gm, '<li>$1</li>');
  h = h.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>');

  // HR
  h = h.replace(/^---$/gm, '<hr>');

  // Links
  h = h.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

  // Newlines
  h = h.replace(/\n/g, '<br>');

  return h;
}

function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// ── Clock & Uptime ──
let msgCount = 0;
const startTime = Date.now();

function tick() {
  $('#clock').textContent = new Date().toLocaleTimeString('en-US', { hour12: false });

  // Uptime
  const elapsed = Math.floor((Date.now() - startTime) / 1000);
  const h = String(Math.floor(elapsed / 3600)).padStart(2, '0');
  const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
  const s = String(elapsed % 60).padStart(2, '0');
  const uptimeEl = document.getElementById('uptime');
  if (uptimeEl) uptimeEl.textContent = `${h}:${m}:${s}`;
}

function bumpMsgCount() {
  msgCount++;
  const el = document.getElementById('msg-count');
  if (el) el.textContent = msgCount;
}

// ── Models ──
let allModels = [];
let configuredKeys = [];

function loadModels() {
  fetch('/api/info').then(r => r.json()).then(d => {
    if (d.cwd) {
      let p = d.cwd.replace(/^\/Users\/[^/]+/, '~');
      $('#cwd-label').textContent = p;
    }

    allModels = d.models || [];
    configuredKeys = d.configured_keys || [];
    const selected = d.selected_model || 'claude-opus';

    // Populate dropdown grouped by provider
    const dropdown = $('#model-dropdown');
    dropdown.innerHTML = '';

    const providers = {};
    for (const m of allModels) {
      if (!providers[m.provider]) providers[m.provider] = [];
      providers[m.provider].push(m);
    }

    const providerLabels = {
      claude: 'ANTHROPIC',
      openai: 'OPENAI',
      google: 'GOOGLE',
      xai: 'xAI (GROK)',
      deepseek: 'DEEPSEEK',
      mistral: 'MISTRAL',
      together: 'META / TOGETHER',
      groq: 'GROQ',
    };

    for (const [prov, models] of Object.entries(providers)) {
      const group = document.createElement('optgroup');
      group.label = providerLabels[prov] || prov.toUpperCase();
      for (const m of models) {
        const opt = document.createElement('option');
        opt.value = m.id;
        opt.textContent = m.name;
        if (m.id === selected) opt.selected = true;
        group.appendChild(opt);
      }
      dropdown.appendChild(group);
    }

    updateModelDisplay(selected);
  }).catch(() => {});
}

function updateModelDisplay(modelId) {
  const model = allModels.find(m => m.id === modelId);
  const el = document.getElementById('current-model');
  if (el && model) {
    el.textContent = model.name.toUpperCase();
  }
}

// ── API Keys Modal ──
function showKeysModal() {
  const providers = [
    { id: 'openai', name: 'OpenAI', placeholder: 'sk-...' },
    { id: 'google', name: 'Google (Gemini)', placeholder: 'AIza...' },
    { id: 'xai', name: 'xAI (Grok)', placeholder: 'xai-...' },
    { id: 'deepseek', name: 'DeepSeek', placeholder: 'sk-...' },
    { id: 'mistral', name: 'Mistral', placeholder: '' },
    { id: 'together', name: 'Together AI', placeholder: '' },
    { id: 'groq', name: 'Groq', placeholder: 'gsk_...' },
  ];

  const rows = providers.map(p => {
    const configured = configuredKeys.includes(p.id);
    return `
      <div class="modal-row">
        <label>${p.name}</label>
        <input type="password" id="key-${p.id}" placeholder="${p.placeholder || 'API key...'}"
               class="${configured ? 'has-key' : ''}">
        <div class="key-status ${configured ? 'configured' : 'missing'}">
          ${configured ? '● Configured' : '○ Not set'}
        </div>
      </div>
    `;
  }).join('');

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal">
      <h2>API KEYS</h2>
      <div style="font-size:10px; color:var(--muted); margin-bottom:14px;">
        Claude uses your existing CLI auth. Other providers need API keys.
      </div>
      ${rows}
      <div class="modal-actions">
        <button class="modal-btn" id="modal-cancel">CANCEL</button>
        <button class="modal-btn primary" id="modal-save">SAVE KEYS</button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  overlay.querySelector('#modal-cancel').onclick = () => overlay.remove();
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) overlay.remove();
  });

  overlay.querySelector('#modal-save').onclick = async () => {
    for (const p of providers) {
      const input = overlay.querySelector(`#key-${p.id}`);
      const val = input.value.trim();
      if (val) {
        await fetch('/api/key', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider: p.id, key: val }),
        });
      }
    }
    overlay.remove();
    loadModels(); // Refresh configured status
    appendSystem('API keys updated.');
  };
}

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  boot();
  connect();
  tick();
  setInterval(tick, 1000);

  loadModels();

  const el = input();

  el.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }

    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (history.length && historyIdx < history.length - 1) {
        historyIdx++;
        el.value = history[historyIdx];
        autosize(el);
      }
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIdx > 0) {
        historyIdx--;
        el.value = history[historyIdx];
      } else {
        historyIdx = -1;
        el.value = '';
      }
      autosize(el);
    }
  });

  el.addEventListener('input', () => autosize(el));

  // Ctrl+C to abort
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'c' && streaming) {
      e.preventDefault();
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'abort' }));
      }
    }
  });

  // Click terminal to focus input
  terminal().addEventListener('click', (e) => {
    if (!window.getSelection().toString()) {
      el.focus();
    }
  });

  // Command list clicks
  document.querySelectorAll('.cmd-item').forEach(item => {
    item.addEventListener('click', () => {
      const cmd = item.dataset.cmd;
      if (cmd) {
        const inp = input();
        inp.value = cmd;
        inp.focus();
        send();
      }
    });
  });

  // Model dropdown change
  const dropdown = document.getElementById('model-dropdown');
  if (dropdown) {
    dropdown.addEventListener('change', () => {
      const modelId = dropdown.value;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'set_model', model: modelId }));
      }
      updateModelDisplay(modelId);
      appendSystem(`Model switched to: ${modelId}`);
    });
  }

  // API Keys button
  const keysBtn = document.getElementById('btn-keys');
  if (keysBtn) {
    keysBtn.addEventListener('click', showKeysModal);
  }
});
