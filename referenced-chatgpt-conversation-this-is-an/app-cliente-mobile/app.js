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
  if (name === 'favorites') renderFavorites();
  if (name === 'history') loadHistory();
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
  
  // Evita que polling atrasado sobrescreva dados em tempo real mais recentes
  if (window.currentReading && window.currentReading.captured_at && data.captured_at) {
    const newTime = new Date(data.captured_at).getTime();
    const curTime = new Date(window.currentReading.captured_at).getTime();
    if (!isNaN(newTime) && !isNaN(curTime) && newTime < curTime) {
      return;
    }
  }

  window.currentReading = data;
  const lotEl = document.querySelector('#lot-number');
  const priceEl = document.querySelector('#price');
  const descEl = document.querySelector('#description');
  const homeCardLot = document.querySelector('#home-card-lot');

  if (lotEl && data.lot !== undefined && data.lot !== null) lotEl.textContent = String(data.lot).padStart(3, '0');
  if (homeCardLot && data.lot !== undefined && data.lot !== null) homeCardLot.textContent = `Lote ${String(data.lot).padStart(3, '0')}`;
  if (priceEl && data.price_cents !== undefined && data.price_cents !== null) priceEl.textContent = formatCurrency(data.price_cents);
  if (descEl && data.description) descEl.textContent = data.description;

  const imageUrl = data.image_url || (data.payload && data.payload.image_url);
  if (imageUrl) {
    document.querySelectorAll('.cattle-image').forEach(el => {
      el.style.backgroundImage = `linear-gradient(0deg, rgba(25, 36, 21, 0.5), rgba(196, 169, 106, 0.1)), url('${imageUrl}')`;
      el.style.backgroundSize = 'cover';
      el.style.backgroundPosition = 'center';
    });
  }

  updateSaveButtonState();

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
    const list = document.querySelector('#full-history-list') || document.querySelector('.history-list');
    if (!list) return;

    const targetId = activeAuctionId || 'remate-elite-nelore-2026';
    const res = await fetch(`${API_URL}/api/auctions/${targetId}/readings?limit=50&distinct_by_lot=true`);
    if (!res.ok) return;

    const readings = await res.json();
    if (Array.isArray(readings) && readings.length > 0) {
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
        const imgUrl = r.image_url || (r.payload && r.payload.image_url);
        const imgTag = imgUrl ? `<img src="${imgUrl}" style="width:40px; height:40px; object-fit:cover; border-radius:6px; margin-right:10px; border:1px solid #343d34;" />` : '';
        const article = document.createElement('article');
        article.style.marginBottom = '8px';
        article.innerHTML = `<span class="${lotChipCls}">${r.lot != null ? String(r.lot).padStart(3, '0') : '--'}</span><div style="display:flex; align-items:center; flex:1;">${imgTag}<div><strong>${r.description || 'Lote do Leilão'}</strong><small>${timeStatus}</small></div></div><b>${formatCurrency(r.price_cents)}</b>`;
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

function getSavedLots() {
  try {
    return JSON.parse(localStorage.getItem('arremate_saved_lots') || '[]');
  } catch (_) {
    return [];
  }
}

function isLotSaved(lotNumber) {
  if (lotNumber == null) return false;
  const saved = getSavedLots();
  return saved.some(item => String(item.lot) === String(lotNumber));
}

function getCurrentReadingToSave() {
  if (window.currentReading && window.currentReading.lot != null) {
    return window.currentReading;
  }
  const lotText = document.querySelector('#lot-number')?.textContent || '';
  const priceText = document.querySelector('#price')?.textContent || '';
  const descText = document.querySelector('#description')?.textContent || '';
  
  const lotNum = parseInt(lotText.replace(/\D/g, ''), 10) || null;
  let cents = null;
  if (priceText) {
    const digits = priceText.replace(/\D/g, '');
    if (digits) cents = parseInt(digits, 10);
  }
  return {
    lot: lotNum,
    price_cents: cents,
    description: descText || 'Lote do Leilão',
    image_url: ''
  };
}

function toggleSaveCurrentLot() {
  const reading = getCurrentReadingToSave();
  if (!reading || reading.lot == null) {
    notify('Nenhum lote ativo no momento');
    return;
  }

  let saved = getSavedLots();
  const lotStr = String(reading.lot);
  const existsIndex = saved.findIndex(item => String(item.lot) === lotStr);

  const favHeart = document.querySelector('.favorite');
  const saveBtn = document.querySelector('#save-button');

  if (existsIndex >= 0) {
    saved.splice(existsIndex, 1);
    localStorage.setItem('arremate_saved_lots', JSON.stringify(saved));
    notify(`Lote ${lotStr} removido dos salvos`);
    if (favHeart) favHeart.textContent = '♡';
    if (saveBtn) {
      saveBtn.textContent = 'Salvar lote';
      saveBtn.classList.remove('outline-button');
      saveBtn.classList.add('gold-button');
    }
  } else {
    const imageUrl = reading.image_url || (reading.payload && reading.payload.image_url) || '';
    saved.push({
      lot: reading.lot,
      price_cents: reading.price_cents,
      description: reading.description || 'Lote do Leilão',
      image_url: imageUrl,
      saved_at: new Date().toISOString()
    });
    localStorage.setItem('arremate_saved_lots', JSON.stringify(saved));
    notify(`⭐ Lote ${lotStr} salvo nos favoritos!`);
    if (favHeart) favHeart.textContent = '♥';
    if (saveBtn) {
      saveBtn.textContent = '✓ Lote Salvo';
      saveBtn.classList.remove('gold-button');
      saveBtn.classList.add('outline-button');
    }
  }
  renderFavorites();
}

function updateSaveButtonState() {
  const reading = window.currentReading;
  if (!reading || reading.lot == null) return;
  const saved = isLotSaved(reading.lot);
  const favHeart = document.querySelector('.favorite');
  const saveBtn = document.querySelector('#save-button');

  if (favHeart) favHeart.textContent = saved ? '♥' : '♡';
  if (saveBtn) {
    if (saved) {
      saveBtn.textContent = '✓ Lote Salvo';
      saveBtn.classList.remove('gold-button');
      saveBtn.classList.add('outline-button');
    } else {
      saveBtn.textContent = 'Salvar lote';
      saveBtn.classList.remove('outline-button');
      saveBtn.classList.add('gold-button');
    }
  }
}

function renderFavorites() {
  const listEl = document.querySelector('#favorites-list');
  if (!listEl) return;

  const saved = getSavedLots();
  if (saved.length === 0) {
    listEl.innerHTML = '<div class="empty-note">Nenhum lote salvo nos seus favoritos ainda. Clique em "Salvar lote" durante o leilão para monitorar.</div>';
    return;
  }

  listEl.innerHTML = saved.map(item => {
    const lotStr = item.lot != null ? String(item.lot).padStart(3, '0') : '--';
    const priceStr = formatCurrency(item.price_cents);
    const imgStyle = item.image_url ? `background: url('${item.image_url}') center/cover;` : '';
    return `
      <article class="saved-card" style="margin-bottom:10px;">
        <div class="saved-image cattle-image" style="${imgStyle}"></div>
        <div style="flex:1;">
          <span class="live-badge" style="background:var(--gold); color:#151a15;">⭐ FAVORITO</span>
          <h3 style="margin:6px 0 4px;">Lote ${lotStr}</h3>
          <p style="margin:0 0 6px;">${item.description || 'Lote do Leilão'}</p>
          <strong style="display:block; font-size:15px; color:var(--gold);">${priceStr}</strong>
          <button type="button" class="remove-fav-btn" data-lot="${item.lot}" style="color:var(--soft); font-size:11px; margin-top:8px; padding:0; cursor:pointer;">✕ Remover dos salvos</button>
        </div>
      </article>
    `;
  }).join('');

  listEl.querySelectorAll('.remove-fav-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const lotToRemove = btn.dataset.lot;
      let savedList = getSavedLots().filter(i => String(i.lot) !== String(lotToRemove));
      localStorage.setItem('arremate_saved_lots', JSON.stringify(savedList));
      notify(`Lote ${lotToRemove} removido dos salvos`);
      updateSaveButtonState();
      renderFavorites();
    });
  });
}

buttons.forEach((button) => button.addEventListener('click', () => goTo(button.dataset.go)));
document.querySelector('.favorite')?.addEventListener('click', toggleSaveCurrentLot);
document.querySelector('#save-button')?.addEventListener('click', toggleSaveCurrentLot);

// Gerenciamento do Modal de Alerta
const alertModal = document.querySelector('#alert-modal');
const alertBtn = document.querySelector('#alert-button');
const closeModalBtn = document.querySelector('#close-modal-btn');
const confirmAlertBtn = document.querySelector('#confirm-alert-btn');
const keywordsInput = document.querySelector('#alert-keywords-input');
const phoneInput = document.querySelector('#alert-phone-input');

function openAlertModal() {
  if (!alertModal) return;
  const savedPhone = localStorage.getItem('arremate_user_phone') || '';
  if (phoneInput && savedPhone) phoneInput.value = savedPhone;
  alertModal.style.display = 'flex';
}

function closeAlertModal() {
  if (alertModal) alertModal.style.display = 'none';
}

document.querySelectorAll('#alert-button, .create-alert-btn').forEach(btn => {
  btn.addEventListener('click', openAlertModal);
});
if (closeModalBtn) closeModalBtn.addEventListener('click', closeAlertModal);
if (alertModal) {
  alertModal.addEventListener('click', (e) => {
    if (e.target === alertModal) closeAlertModal();
  });
}

// Chips interativos de categoria
document.querySelectorAll('.keyword-chips .chip').forEach(chip => {
  chip.addEventListener('click', () => {
    chip.classList.toggle('active');
    const activeChips = Array.from(document.querySelector('.keyword-chips').querySelectorAll('.chip.active')).map(c => c.dataset.kw);
    if (keywordsInput) keywordsInput.value = activeChips.join(', ');
  });
});

if (confirmAlertBtn) {
  confirmAlertBtn.addEventListener('click', async () => {
    const rawKw = keywordsInput ? keywordsInput.value.trim() : '';
    const phone = phoneInput ? phoneInput.value.trim() : '';
    if (!phone) {
      alert('Por favor, informe seu WhatsApp com DDD para receber o alerta.');
      return;
    }
    const keywordsList = rawKw ? rawKw.split(',').map(k => k.trim()).filter(Boolean) : ['Geral'];
    localStorage.setItem('arremate_user_phone', phone);
    
    try {
      await fetch(`${API_URL}/api/alerts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          auction_id: activeAuctionId,
          phone: phone,
          keywords: keywordsList
        })
      });
    } catch (_) {}

    closeAlertModal();
    notify(`🔔 Alerta de (${keywordsList.join(', ')}) ativado no WhatsApp!`);
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
  const activeScreen = document.querySelector('.screen.active');
  if (activeScreen && activeScreen.dataset.screen === 'history') {
    loadHistory();
  }
}, 3000);
