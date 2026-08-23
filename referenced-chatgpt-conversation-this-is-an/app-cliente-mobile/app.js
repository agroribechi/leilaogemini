const buttons = document.querySelectorAll('[data-go]');
const screens = document.querySelectorAll('.screen');
const navItems = document.querySelectorAll('.nav-item');
const toast = document.querySelector('.toast');
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
window.currentAuction = null;
window.currentReading = null;

function goTo(name) {
  screens.forEach((screen) => screen.classList.toggle('active', screen.dataset.screen === name));
  navItems.forEach((item) => item.classList.toggle('active', item.dataset.go === name));
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function notify(message) {
  toast.textContent = message;
  toast.classList.add('show');
  window.setTimeout(() => toast.classList.remove('show'), 2600);
}

function formatCurrency(cents) {
  if (cents == null) return '—';
  return `R$ ${(cents / 100).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
}

function updateLiveView(data) {
  if (!data) return;
  window.currentReading = data;
  const lotEl = document.querySelector('#lot-number');
  const priceEl = document.querySelector('#price');
  const descEl = document.querySelector('#description');
  const homeCardLot = document.querySelector('#home-card-lot');

  if (lotEl && data.lot !== undefined && data.lot !== null) lotEl.textContent = String(data.lot);
  if (homeCardLot && data.lot !== undefined && data.lot !== null) homeCardLot.textContent = `Lote ${String(data.lot).padStart(3, '0')}`;
  if (priceEl && data.price_cents !== undefined && data.price_cents !== null) priceEl.textContent = formatCurrency(data.price_cents);
  if (descEl && data.description) descEl.textContent = data.description;

  // Atualiza timeline de lances se for um novo lance
  const timeline = document.querySelector('.timeline');
  if (timeline && data.price_cents && data.id !== window.lastTimelineReadingId) {
    window.lastTimelineReadingId = data.id;
    const timeStr = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const li = document.createElement('li');
    li.innerHTML = `<span class="time">${timeStr}</span><div><strong>${formatCurrency(data.price_cents)}</strong><small>${data.description ? data.description : 'Atualização de lance'}</small></div>`;
    timeline.insertBefore(li, timeline.firstChild);
  }
}

function parseVideoEmbedUrl(url) {
  if (!url || typeof url !== 'string' || url.trim() === '') return null;
  const clean = url.trim();

  // YouTube match: watch?v=, youtu.be/, /live/, /v/, /shorts/
  const ytMatch = clean.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|embed\/|v\/|live\/|shorts\/))([a-zA-Z0-9_-]{11})/);
  if (ytMatch && ytMatch[1]) {
    return `https://www.youtube.com/embed/${ytMatch[1]}`;
  }

  // Se já for um embed genérico
  if (clean.includes('/embed/')) {
    return clean;
  }

  // Vimeo
  const vimeoMatch = clean.match(/vimeo\.com\/(?:video\/)?([0-9]+)/);
  if (vimeoMatch && vimeoMatch[1]) {
    return `https://player.vimeo.com/video/${vimeoMatch[1]}`;
  }

  if (clean.startsWith('http')) return clean;

  return null;
}

function setVideo(embedUrl) {
  const iframe = document.querySelector('#youtube-player');
  const placeholder = document.querySelector('#video-placeholder');

  if (!iframe) return;

  if (embedUrl) {
    if (iframe.src !== embedUrl) iframe.src = embedUrl;
    iframe.style.display = 'block';
    if (placeholder) placeholder.style.display = 'none';
  } else {
    iframe.src = '';
    iframe.style.display = 'none';
    if (placeholder) {
      placeholder.textContent = 'Nenhuma transmissão configurada. Aguarde o leiloeiro iniciar.';
      placeholder.style.display = 'flex';
    }
  }
}

function applyAuctionData(auction) {
  if (!auction) return;
  window.currentAuction = auction;

  const wpBtn = document.getElementById('whatsapp-bid-btn');
  if (wpBtn) {
    wpBtn.style.display = auction.whatsapp_number ? 'flex' : 'none';
  }

  if (auction.youtube_url && auction.youtube_url.trim() !== '') {
    const embed = parseVideoEmbedUrl(auction.youtube_url);
    if (embed) {
      setVideo(embed);
    } else {
      setVideo(null);
    }
  } else {
    const savedUrl = localStorage.getItem('arremate_custom_youtube');
    if (savedUrl) {
      const embed = parseVideoEmbedUrl(savedUrl);
      if (embed) setVideo(embed);
      else setVideo(null);
    } else {
      setVideo(null);
    }
  }
}

let mobileReconnectTimer = null;

async function loadLiveAuction() {
  try {
    const res = await fetch(`${API_URL}/api/auctions`);
    if (!res.ok) throw new Error('API offline');
    const auctions = await res.json();
    if (auctions && auctions.length > 0) {
      const live = auctions.find(a => a.status === 'live') || auctions[0];
      activeAuctionId = live.id;
      applyAuctionData(live);
    }

    const readingsRes = await fetch(`${API_URL}/api/auctions/${activeAuctionId}/readings?limit=1`);
    if (readingsRes.ok) {
      const readings = await readingsRes.json();
      if (readings && readings[0]) {
        updateLiveView(readings[0]);
      }
    }
    connectRealtime();
  } catch (err) {
    clearTimeout(mobileReconnectTimer);
    mobileReconnectTimer = setTimeout(loadLiveAuction, 3000);
  }
}

let mobileSocket = null;

function connectRealtime() {
  if (mobileSocket) {
    try { mobileSocket.close(); } catch (_) {}
  }
  const wsUrl = `${API_URL.replace('http', 'ws')}/ws/auctions/${activeAuctionId}`;
  mobileSocket = new WebSocket(wsUrl);

  mobileSocket.onmessage = (message) => {
    try {
      const event = JSON.parse(message.data);
      if (event.type === 'reading.created' || event.type === 'reading.corrected') {
        updateLiveView(event.data);
        notify(event.type === 'reading.corrected' ? 'Lance corrigido pela mesa' : 'Novo lance em tempo real!');
      }
      if (event.type === 'auction.updated') {
        if (event.data.id === activeAuctionId || !activeAuctionId) {
          applyAuctionData(event.data);
          notify('Transmissão ao vivo sincronizada!');
        }
      }
    } catch (_) {}
  };

  mobileSocket.onclose = () => {
    setTimeout(connectRealtime, 3000);
  };
}

async function loadHistory() {
  try {
    const readings = await fetch(`${API_URL}/api/auctions/${activeAuctionId}/readings?limit=50&distinct_by_lot=true`).then(res => res.json());
    const list = document.querySelector('.history-list');
    if (list && readings && readings.length > 0) {
      list.innerHTML = '';
      
      const seenLots = new Set();
      const uniqueReadings = [];
      for (const r of readings) {
        const lotKey = r.lot != null ? String(r.lot) : null;
        if (lotKey && !seenLots.has(lotKey)) {
          seenLots.add(lotKey);
          uniqueReadings.push(r);
        } else if (!lotKey) {
          uniqueReadings.push(r);
        }
      }

      uniqueReadings.forEach((r, idx) => {
        const isCurrent = idx === 0;
        const lotChipCls = isCurrent ? 'lot-chip' : 'lot-chip muted';
        const timeStatus = isCurrent ? 'Em andamento' : `${new Date(r.captured_at).toLocaleTimeString('pt-BR', {hour:'2-digit', minute:'2-digit'})} · lido`;
        const article = document.createElement('article');
        article.innerHTML = `<span class="${lotChipCls}">${r.lot != null ? String(r.lot).padStart(3, '0') : '--'}</span><div><strong>${r.description || 'Lote do Leilão'}</strong><small>${timeStatus}</small></div><b>${formatCurrency(r.price_cents)}</b>`;
        list.appendChild(article);
      });
    }
  } catch (e) {
    console.error('Failed to load history', e);
  }
}

function initWhatsAppButton() {
  const btn = document.getElementById('whatsapp-bid-btn');
  if (!btn) return;
  
  btn.addEventListener('click', () => {
    if (!window.currentAuction || !window.currentAuction.whatsapp_number) {
      alert("Número de WhatsApp do leilão não configurado.");
      return;
    }
    
    const auc = window.currentAuction;
    const read = window.currentReading;
    
    const lotStr = read && read.lot ? read.lot : '--';
    const priceStr = read && read.price_cents ? formatCurrency(read.price_cents) : '--';
    
    const message = `Olá! Gostaria de dar um lance no Leilão *${auc.name}*.\n\n*Lote atual:* ${lotStr}\n*Preço atual na tela:* ${priceStr}\n\n*Meu lance é: R$ ______*`;
    
    const number = auc.whatsapp_number.replace(/\\D/g, '');
    const url = `https://wa.me/${number}?text=${encodeURIComponent(message)}`;
    
    window.open(url, '_blank');
  });
}

function initVideoPlayer() {
  const changeBtn = document.querySelector('#change-video-btn');
  if (changeBtn) {
    changeBtn.addEventListener('click', () => {
      const current = localStorage.getItem('arremate_custom_youtube') || '';
      const input = prompt('Cole o link do YouTube da transmissao do leilao (ex: https://youtube.com/watch?v=... ou /live/...):', current);
      if (input !== null && input.trim() !== '') {
        const embedUrl = parseVideoEmbedUrl(input.trim());
        if (embedUrl) {
          localStorage.setItem('arremate_custom_youtube', input.trim());
          setVideo(embedUrl);
          notify('Video do leilao atualizado com sucesso!');
        } else {
          alert('Link do YouTube invalido. Certifique-se de colar uma URL completa do YouTube.');
        }
      }
    });
  }

  // Tenta carregar URL salva localmente (enquanto aguarda API)
  const savedUrl = localStorage.getItem('arremate_custom_youtube');
  if (savedUrl) {
    const embed = parseVideoEmbedUrl(savedUrl);
    if (embed) setVideo(embed);
  }
}

buttons.forEach((button) => button.addEventListener('click', () => goTo(button.dataset.go)));
document.querySelector('.favorite').addEventListener('click', (event) => {
  event.currentTarget.textContent = event.currentTarget.textContent === '\u2661' ? '\u2665' : '\u2661';
  notify(event.currentTarget.textContent === '\u2665' ? 'Lote adicionado aos salvos' : 'Lote removido dos salvos');
});
const saveBtn = document.querySelector('#save-button');
if (saveBtn) {
  saveBtn.addEventListener('click', () => notify('Lote salvo nos seus favoritos!'));
}

const alertBtn = document.querySelector('#alert-button');
if (alertBtn) {
  alertBtn.addEventListener('click', () => {
    const lotNum = window.currentReading?.lot ? `Lote ${window.currentReading.lot}` : 'lotes deste leilão';
    const currentPhone = localStorage.getItem('arremate_user_phone') || '';
    const phone = prompt(`Digite seu WhatsApp (com DDD) para receber alertas automáticos quando houver novidades para o ${lotNum}:`, currentPhone);
    if (phone && phone.trim() !== '') {
      localStorage.setItem('arremate_user_phone', phone.trim());
      notify(`🔔 Alerta ativado no WhatsApp para ${phone.trim()}!`);
    }
  });
}

document.querySelectorAll('.filter').forEach((filter) => filter.addEventListener('click', () => {
  document.querySelectorAll('.filter').forEach((item) => item.classList.remove('active-filter'));
  filter.classList.add('active-filter');
  notify(`Filtro selecionado: ${filter.textContent}`);
}));

initVideoPlayer();
initWhatsAppButton();
loadLiveAuction().then(loadHistory);

// Fallback de polling HTTP para dispositivos móveis
setInterval(async () => {
  if (activeAuctionId) {
    try {
      const res = await fetch(`${API_URL}/api/auctions/${activeAuctionId}/readings?limit=1`);
      if (res.ok) {
        const readings = await res.json();
        if (readings && readings[0]) updateLiveView(readings[0]);
      }
    } catch (_) {}
  }
}, 3000);
