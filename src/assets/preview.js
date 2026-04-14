async function loadEpisode() {
  try {
    const res = await fetch('episode.json?t=' + Date.now());
    if (!res.ok) throw new Error('episode.json が見つかりません');
    const data = await res.json();
    renderEpisode(data);
  } catch (err) {
    document.getElementById('content').innerHTML = `
      <div class="error">
        ❌ ${err.message}<br><br>
        ローカルサーバーで開いてください:<br>
        <code>python3 -m http.server 8000</code>
      </div>
    `;
  }
}

function renderEpisode(data) {
  let html = `
    <h1>${data.title || 'タイトル未設定'}</h1>
    <div class="subtitle">${data.plot_twist_type || ''}</div>
    <div class="plot-twist">${data.plot_twist_description || ''}</div>
    <div class="panels-grid">
  `;
  
  (data.panels || []).forEach(panel => {
    let dialoguesHtml = '';
    (panel.dialogue || []).forEach(d => {
      let text = d.text || '';
      if (d.highlight) {
        text = text.replace(d.highlight, `<span class="highlight">${d.highlight}</span>`);
      }
      dialoguesHtml += `
        <div class="dialogue dialogue-${d.type || 'normal'}">
          <div class="dialogue-char">${d.character || '?'} [${d.type || 'normal'}]</div>
          <div class="dialogue-text">${text}</div>
          <div class="dialogue-meta">位置: ${d.bubble_position || '自動'}</div>
        </div>
      `;
    });
    
    html += `
      <div class="panel">
        <div class="panel-header">
          <div class="panel-number">${panel.number}</div>
          <div class="panel-name">${panel.name || ''}</div>
        </div>
        <div class="panel-desc">${panel.description || ''}</div>
        <div class="background-info">🎨 ${panel.background || ''}</div>
        <div class="characters">👤 ${(panel.characters || []).join(', ')}</div>
        <div class="dialogue-list">${dialoguesHtml}</div>
      </div>
    `;
  });
  
  html += `</div>`;
  
  if (data.instagram_hook) {
    html += `<div class="instagram-hook">${data.instagram_hook}</div>`;
  }
  
  document.getElementById('content').innerHTML = html;
  document.title = data.title + ' - プレビュー';
}

// 初回読み込み
loadEpisode();
