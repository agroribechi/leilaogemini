const names = { dashboard: 'Visão geral', auctions: 'Leilões', quality: 'Qualidade OCR', subscribers: 'Assinantes', settings: 'Configurações' };
function getApiUrl() {
  if (window.API_URL) return window.API_URL;
  const host = window.location.hostname;
  const proto = window.location.protocol;
  const saved = localStorage.getItem('ARREMATE_API_URL');
  if (saved && !saved.includes('127.0.0.1') && !saved.includes('localhost')) return saved;
  if (host === 'localhost' || host === '127.0.0.1') return 'http://127.0.0.1:8000';
  if (host.includes('-admin.') || host.includes('-mobile.')) {
    return `${proto}//${host.replace('-admin.', '-api.').replace('-mobile.', '-api.')}`;
  }
  return `${proto}//${host}`;
}
const API_URL = getApiUrl();
let activeAuctionId = 'remate-elite-nelore-2026';
let activeReading = null;
let currentAuction = null;
let auctionsList = [];

function showPage(page) {
  document.querySelectorAll('.page').forEach((item) => {
    item.classList.toggle('active', item.dataset.page === page);
  });
  document.querySelectorAll('.side-link').forEach((item) => {
    item.classList.toggle('active', item.dataset.page === page);
  });
  const title = document.querySelector('#page-title');
  if (title) title.textContent = names[page] || page;
  window.scrollTo(0, 0);
}

function notify(message) {
  const toast = document.querySelector('.toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2600);
}

function currency(cents) {
  return cents == null ? '—' : `R$ ${(cents / 100).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
}

let reconnectTimer = null;
let activeSocket = null;

function setConnectionStatus(connected, text) {
  const conn = document.querySelector('.connection');
  if (!conn) return;
  if (connected) {
    conn.innerHTML = '<i></i> Sistema conectado';
    const dot = conn.querySelector('i');
    if (dot) dot.style.background = '#25D366';
  } else {
    conn.innerHTML = `<i></i> ${text || 'Aguardando API local'}`;
    const dot = conn.querySelector('i');
    if (dot) dot.style.background = '#d58a4d';
  }
}

function addRecentEvent(reading) {
  const list = document.querySelector('#recent-events-list');
  if (!list) return;
  const timeStr = new Date(reading.captured_at || Date.now()).toLocaleTimeString('pt-BR');
  const lotStr = reading.lot != null ? `Lote ${String(reading.lot).padStart(3, '0')}` : 'Sem lote';
  const priceStr = currency(reading.price_cents);
  const li = document.createElement('li');
  li.innerHTML = `<time>${timeStr}</time><div><strong>${priceStr}</strong><span>Leitura OCR · ${lotStr}</span></div><em>Publicado</em>`;
  list.insertBefore(li, list.firstChild);
  if (list.children.length > 10) list.removeChild(list.lastChild);
}

function applyReading(reading) {
  activeReading = reading;
  const lotEl = document.querySelector('#current-lot');
  const priceEl = document.querySelector('#current-price');
  const descEl = document.querySelector('#current-description');
  const metricLot = document.querySelector('#metric-lot');
  const metricDesc = document.querySelector('#metric-desc');
  const metricPrice = document.querySelector('#metric-price');

  const lotText = reading.lot != null ? String(reading.lot).padStart(3, '0') : '—';
  const priceText = currency(reading.price_cents);
  const descText = reading.description || 'Descrição não identificada';

  if (lotEl) lotEl.textContent = lotText;
  if (priceEl) priceEl.textContent = priceText;
  if (descEl) descEl.textContent = descText;

  if (metricLot) metricLot.textContent = lotText;
  if (metricDesc) metricDesc.textContent = descText;
  if (metricPrice) metricPrice.textContent = priceText.replace('R$ ', '');

  document.querySelectorAll('#price').forEach((element) => { element.textContent = priceText; });
  document.querySelectorAll('#lot-number').forEach((element) => { element.textContent = lotText; });
}

function updateAuctionDisplay(auction) {
  currentAuction = auction;
  const nameEl = document.querySelector('#active-auction-name');
  const locEl = document.querySelector('#active-auction-location');
  if (nameEl && auction.name) nameEl.textContent = auction.name;
  if (locEl && auction.location) locEl.textContent = `${auction.location} · ${auction.status === 'live' ? 'Ao vivo' : 'Agendado'}`;
}

function renderAuctionsTable() {
  const tbody = document.querySelector('#auctions-tbody');
  if (!tbody) return;
  if (!auctionsList || auctionsList.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color:#888;">Nenhum leilão cadastrado no momento.</td></tr>';
    return;
  }
  tbody.innerHTML = auctionsList.map((a) => {
    const isCurrent = a.id === activeAuctionId;
    return `
      <tr style="${isCurrent ? 'background: #1e281b;' : ''}">
        <td><strong>${a.name}</strong>${isCurrent ? ' <span style="background:#89aa61;color:#111;font-size:9px;padding:2px 6px;border-radius:4px;font-weight:800;margin-left:6px;">EM OPERAÇÃO</span>' : ''}</td>
        <td>${a.location}</td>
        <td><span class="status ${a.status === 'live' ? 'live' : 'ready'}"><i></i> ${a.status === 'live' ? 'Ao vivo' : 'Agendado'}</span></td>
        <td>${a.youtube_url ? '<span style="color:#89aa61; font-weight:600;">✓ YouTube Configurado</span>' : '<span style="color:#888;">Sem transmissão</span>'}${a.whatsapp_number ? `<a href="https://wa.me/${a.whatsapp_number.replace(/\D/g, '')}" target="_blank" style="margin-left: 10px; color: #25D366;"><small>💬 ${a.whatsapp_number}</small></a>` : ''}</td>
        <td style="display:flex; gap:8px;">
          <button class="review" data-action="edit" data-id="${a.id}">⚙ Editar</button>
          ${!isCurrent ? `<button class="review" style="background:#89aa61; color:#111; font-weight:700;" data-action="select" data-id="${a.id}">Operar</button>` : ''}
        </td>
      </tr>
    `;
  }).join('');
}

async function loadInitialData() {
  try {
    const res = await fetch(`${API_URL}/api/auctions`);
    if (!res.ok) throw new Error('API offline');
    auctionsList = await res.json();
    const live = auctionsList.find((auction) => auction.status === 'live') || auctionsList[0];
    if (live) {
      activeAuctionId = live.id;
      updateAuctionDisplay(live);
    }
    renderAuctionsTable();

    const readingsRes = await fetch(`${API_URL}/api/auctions/${activeAuctionId}/readings?limit=5`);
    if (readingsRes.ok) {
      const readings = await readingsRes.json();
      if (readings && readings.length > 0) {
        applyReading(readings[0]);
        const list = document.querySelector('#recent-events-list');
        if (list) {
          list.innerHTML = readings.map(r => {
            const timeStr = new Date(r.captured_at || Date.now()).toLocaleTimeString('pt-BR');
            const lotStr = r.lot != null ? `Lote ${String(r.lot).padStart(3, '0')}` : 'Sem lote';
            return `<li><time>${timeStr}</time><div><strong>${currency(r.price_cents)}</strong><span>Leitura OCR · ${lotStr}</span></div><em>Publicado</em></li>`;
          }).join('');
        }
      }
    }
    setConnectionStatus(true);
    connectRealtime();
  } catch (_) {
    setConnectionStatus(false, 'Conectando à API local...');
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(loadInitialData, 3000);
  }
}

function openModal(id) {
  const modal = document.querySelector(`#${id}`);
  if (modal) modal.classList.add('active');
}

function closeModal(id) {
  const modal = document.querySelector(`#${id}`);
  if (modal) modal.classList.remove('active');
}

function openEditAuction(id) {
  const auction = auctionsList.find(a => a.id === id) || currentAuction;
  if (!auction) return;
  document.querySelector('#edit-auction-id').value = auction.id;
  document.querySelector('#edit-name').value = auction.name;
  document.querySelector('#edit-location').value = auction.location;
  document.querySelector('#edit-status').value = auction.status || 'scheduled';
  document.querySelector('#edit-youtube').value = auction.youtube_url || '';
  document.querySelector('#edit-whatsapp').value = auction.whatsapp_number || '';
  openModal('edit-auction-modal');
}

function selectAuction(id) {
  activeAuctionId = id;
  const selected = auctionsList.find(a => a.id === id);
  if (selected) {
    updateAuctionDisplay(selected);
    renderAuctionsTable();
    showPage('dashboard');
    notify(`Leilão '${selected.name}' selecionado para operação!`);
    connectRealtime();
  }
}

function connectRealtime() {
  if (activeSocket) {
    try { activeSocket.close(); } catch (_) {}
  }
  const wsUrl = `${API_URL.replace('http', 'ws')}/ws/auctions/${activeAuctionId}`;
  activeSocket = new WebSocket(wsUrl);

  activeSocket.onopen = () => {
    setConnectionStatus(true);
  };

  activeSocket.onmessage = (message) => {
    try {
      const event = JSON.parse(message.data);
      if (event.type === 'reading.created') {
        applyReading(event.data);
        addRecentEvent(event.data);
        notify(`Nova leitura do Lote ${event.data.lot ?? '—'} recebida!`);
      }
      if (event.type === 'reading.corrected') {
        applyReading({ ...activeReading, ...event.data });
        notify('Correção publicada');
      }
      if (event.type === 'auction.updated') {
        const idx = auctionsList.findIndex(a => a.id === event.data.id);
        if (idx !== -1) auctionsList[idx] = event.data;
        if (event.data.id === activeAuctionId) updateAuctionDisplay(event.data);
        renderAuctionsTable();
        notify('Dados do leilão e transmissão atualizados!');
      }
    } catch (_) {}
  };

  activeSocket.onerror = () => {
    setConnectionStatus(false, 'Conexão perdida com a API');
  };

  activeSocket.onclose = () => {
    setConnectionStatus(false, 'Tentando reconectar...');
    setTimeout(connectRealtime, 3000);
  };
}

// Delegação global de cliques
document.addEventListener('click', (e) => {
  // 1. Fechar modais (prioridade máxima)
  const closeBtn = e.target.closest('[data-close]');
  if (closeBtn) {
    closeModal(closeBtn.dataset.close);
    return;
  }

  // Fechar ao clicar fora do modal-box
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('active');
    return;
  }

  // 2. Botões específicos (ANTES de [data-page] pois estão dentro de section[data-page])
  if (e.target.closest('#manage-auctions-btn')) {
    showPage('auctions');
    return;
  }

  if (e.target.closest('#edit-auction-btn')) {
    openEditAuction(activeAuctionId);
    return;
  }

  if (e.target.closest('#new-auction') || e.target.closest('#new-auction-alt')) {
    openModal('new-auction-modal');
    return;
  }

  // 3. Ações da tabela de leilões
  const actionBtn = e.target.closest('[data-action]');
  if (actionBtn) {
    const action = actionBtn.dataset.action;
    const id = actionBtn.dataset.id;
    if (action === 'edit') openEditAuction(id);
    if (action === 'select') selectAuction(id);
    return;
  }

  // 4. Navegação de abas (sidebar e text-buttons com data-page)
  // Verificar APENAS side-links e text-buttons, NÃO sections .page
  const pageBtn = e.target.closest('.side-link[data-page], .text-button[data-page]');
  if (pageBtn) {
    showPage(pageBtn.dataset.page);
    return;
  }
});

// Salvar Edição
document.querySelector('#save-edit-auction')?.addEventListener('click', async (event) => {
  event.preventDefault();
  const id = document.querySelector('#edit-auction-id').value;
  const name = document.querySelector('#edit-name').value.trim();
  const location = document.querySelector('#edit-location').value.trim();
  const status = document.querySelector('#edit-status').value;
  const youtubeUrl = document.querySelector('#edit-youtube').value.trim();
  const whatsappNumber = document.querySelector('#edit-whatsapp').value.trim();

  if (!name || !location) {
    notify('Preencha o nome e o local do leilão');
    return;
  }

  try {
    const res = await fetch(`${API_URL}/api/auctions/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, location, status, youtube_url: youtubeUrl, whatsapp_number: whatsappNumber })
    });
    if (res.ok) {
      closeModal('edit-auction-modal');
      notify('Leilão atualizado com sucesso!');
      loadInitialData();
    } else {
      notify('Erro ao salvar alterações');
    }
  } catch (_) {
    notify('Não foi possível conectar à API');
  }
});

// Criar Leilão
document.querySelector('#save-auction')?.addEventListener('click', async (event) => {
  event.preventDefault();
  const name = document.querySelector('#auction-name').value.trim();
  const location = document.querySelector('#auction-location').value.trim();
  const youtubeUrl = document.querySelector('#youtube_url')?.value.trim() || '';
  const whatsappNumber = document.querySelector('#whatsapp_number')?.value.trim() || '';

  if (!name || !location) {
    notify('Preencha o nome e o local do leilão');
    return;
  }

  try {
    const res = await fetch(`${API_URL}/api/auctions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, location, youtube_url: youtubeUrl, whatsapp_number: whatsappNumber })
    });
    if (res.ok) {
      closeModal('new-auction-modal');
      notify('Leilão criado com sucesso!');
      loadInitialData();
    }
  } catch (_) {
    notify('Não foi possível conectar à API local');
  }
});

// Inicialização
loadInitialData();
