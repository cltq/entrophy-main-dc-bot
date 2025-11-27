function animateValue(el, start, end, duration){
  const startTime = performance.now();
  function step(now){
    const t = Math.min(1, (now - startTime) / duration);
    const val = Math.round(start + (end - start) * t);
    el.textContent = val;
    if(t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function applyStatus(data){
  updateTextSmooth(document.getElementById('bot-name'), data.name || 'Bot');
  updateTextSmooth(document.getElementById('bot-id'), 'ID: ' + (data.id || '-'));
  const uptimeEl = document.getElementById('uptime');
  updateTextSmooth(uptimeEl, data.uptime || '-');
  const guildCountEl = document.getElementById('guild-count');
  const current = parseInt(guildCountEl.textContent) || 0;
  animateValue(guildCountEl, current, data.guild_count, 700);

  const rl = document.getElementById('recent-logs');
  rl.innerHTML = '';
  for(const ln of data.recent_logs){
    const div = document.createElement('div');
    div.className = 'logline';
    div.textContent = ln;
    rl.appendChild(div);
  }

}

function updateTextSmooth(el, text){
  if(!el) return;
  el.style.transition = 'opacity .18s ease, transform .18s ease';
  el.style.opacity = '0';
  el.style.transform = 'translateY(-4px)';
  setTimeout(()=>{
    el.textContent = text;
    el.style.opacity = '1';
    el.style.transform = 'none';
  }, 180);
}

/* Toast & button helper */
(function(){
  if(!document.getElementById('toast-root')){
    const t = document.createElement('div');
    t.id = 'toast-root';
    t.style.position = 'fixed';
    t.style.right = '20px';
    t.style.bottom = '24px';
    t.style.zIndex = 9999;
    document.body.appendChild(t);
  }

  window.showToast = function(msg, opts={}){
    const root = document.getElementById('toast-root');
    const el = document.createElement('div');
    el.className = 'toast';
    el.textContent = msg;
    root.appendChild(el);
    setTimeout(()=> el.classList.add('visible'), 10);
    setTimeout(()=>{
      el.classList.remove('visible');
      setTimeout(()=> el.remove(), 300);
    }, opts.duration || 4000);
  }

  window.setButtonLoading = function(btn, loading){
    if(!btn) return;
    if(loading){
      btn.dataset._old = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> ' + (btn.dataset._old || btn.textContent);
      btn.classList.add('loading');
    }else{
      btn.disabled = false;
      if(btn.dataset._old) btn.innerHTML = btn.dataset._old;
      btn.classList.remove('loading');
    }
  }
})();
// Modal utility: create modal element if not present
(function ensureModal(){
  if(document.getElementById('confirm-modal')) return;
  const modalHtml = `
  <div id="confirm-modal" class="modal" role="dialog" aria-hidden="true">
    <div class="modal-backdrop"></div>
    <div class="modal-panel">
      <div class="modal-header">
        <div class="modal-title">Confirm</div>
      </div>
      <div class="modal-body">
        <div class="modal-text">Are you sure?</div>
        <label class="modal-label">Dashboard token (if set)</label>
        <input id="modal-token" class="modal-input" placeholder="token (optional)" />
      </div>
      <div class="modal-actions">
        <button class="btn modal-cancel">Cancel</button>
        <button class="btn modal-confirm danger">Confirm</button>
      </div>
    </div>
  </div>`;
  document.body.insertAdjacentHTML('beforeend', modalHtml);
})();

// Prefer SSE for smooth updates
if(typeof(EventSource) !== 'undefined'){
  const es = new EventSource('/api/stream');
  es.onmessage = (e) => {
    try{
      const data = JSON.parse(e.data);
      applyStatus(data);
    }catch(err){console.warn('sse parse', err)}
  };
  es.onerror = (e) => { console.warn('sse error', e); es.close(); };
} else {
  // fallback polling
  async function refreshStatus(){
    try{
      const res = await fetch('/api/status');
      const data = await res.json();
      applyStatus(data);
    }catch(e){console.warn('Failed to refresh', e);}
  }
  refreshStatus();
  setInterval(refreshStatus, 1000);
}
