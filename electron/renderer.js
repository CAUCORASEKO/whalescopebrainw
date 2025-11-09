// =========================================================
// WhaleScope - Electron Renderer (Final Full Version)
// =========================================================

console.log('[Renderer] Loaded');


// =========================================================
// SECTION HANDLER – Mostrar layout antes y ocultar loader al final
// =========================================================
document.addEventListener('sectionChange', async (e) => {
  const { section } = e.detail;
  console.log(`[Renderer] Section change to: ${section}`);

  // 🔹 Mostrar el layout de esa sección
  const currentSection = document.getElementById(`${section}-section`);
  if (!currentSection) {
    console.error(`[Renderer] ❌ Section not found: ${section}-section`);
    return;
  }

  // 🔹 Mostrar spinner mientras carga
  const loadingEl = currentSection.querySelector('.loading');
  if (loadingEl) loadingEl.style.display = 'block';

  try {
    // 🔹 Llamar a la función que carga los datos (BITCOIN REMOVIDO)
    if (section === 'eth') await loadEth();
    if (section === 'binance_polar') await loadBinancePolar();
    if (section === 'marketbrain') {
      console.log("[Renderer] MarketBrain opened (waiting for subtab load)");
}
  } catch (err) {
    console.error(`[Renderer] Error loading section ${section}:`, err);
  } finally {
    // 🔹 Siempre ocultar el spinner al terminar (éxito o error)
    if (loadingEl) loadingEl.style.display = 'none';
  }
});


// =========================================================
// DOM READY
// =========================================================
document.addEventListener('DOMContentLoaded', async () => {
  const form = document.getElementById('config-form');
  const configSection = document.getElementById('config-section');
  const mainApp = document.getElementById('main-app');

  // ---------- Default Dates ----------
  const today = new Date();
  const monthAgo = new Date();
  monthAgo.setDate(today.getDate() - 30);
  const formatDate = (d) => d.toISOString().split('T')[0];

  function setDefaultDates(prefix = '') {
    const start = document.getElementById(`${prefix}startDate`) || document.getElementById(`${prefix}start-date`);
    const end = document.getElementById(`${prefix}endDate`) || document.getElementById(`${prefix}end-date`);
    if (start && end && !start.value && !end.value) {
      start.value = formatDate(monthAgo);
      end.value = formatDate(today);
    }
  }
  setDefaultDates('');
  setDefaultDates('eth-');

  // ---------- Restore Config ----------
const saved = localStorage.getItem('whalescopeConfig');
if (saved) {
  const parsed = JSON.parse(saved);
  if (parsed.BINANCE_API_KEY && parsed.BINANCE_API_SECRET) {
    console.log('[Renderer] Restored API keys');
    await window.electronAPI.saveApiKeys(parsed);
    configSection.style.display = 'none';
    mainApp.style.display = 'block';
    window.showSection('marketbrain'); // ✅ dejamos esto
  } else {
    localStorage.removeItem('whalescopeConfig');
  }
}

  // ---------- Save New Config ----------
if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const cfg = {
      BINANCE_API_KEY: document.getElementById('apiKey').value.trim(),
      BINANCE_API_SECRET: document.getElementById('apiSecret').value.trim(),
      ARKHAM_API_KEY: document.getElementById('arkhamKey').value.trim(),
      CMC_API_KEY: document.getElementById('cmcKey').value.trim(),
      ALLIUM_API_KEY: document.getElementById('alliumKey').value.trim(),
      OPENAI_API_KEY: document.getElementById('openaiKey').value.trim(),
      COINGECKO_API_KEY: document.getElementById('coingeckoKey')?.value.trim() || ''
    };

    if (!cfg.BINANCE_API_KEY || !cfg.BINANCE_API_SECRET) {
      alert('Please enter Binance API keys');
      return;
    }

    // Save config
    localStorage.setItem('whalescopeConfig', JSON.stringify(cfg));
    await window.electronAPI.saveApiKeys(cfg);

    // Show app
    configSection.style.display = 'none';
    mainApp.style.display = 'block';

    // ✅ Directo a MarketBrain (sin loadBitcoin)
    window.showSection('marketbrain');
  });
}

  // ---------- Refresh Buttons ----------
  const btcRefresh = document.getElementById('refreshBtn');
  if (btcRefresh) btcRefresh.addEventListener('click', loadBitcoin);

  const ethRefresh = document.getElementById('eth-refreshBtn');
  if (ethRefresh) ethRefresh.addEventListener('click', loadEth);
});



// =========================================================
// DATA LOADERS
// =========================================================

async function loadEth() {
  try {
    const start = document.getElementById('eth-startDate').value;
    const end = document.getElementById('eth-endDate').value;
    const params = { section: 'eth', startDate: start, endDate: end };
    const data = await window.electronAPI.loadData(params);
    renderEth(data);
  } catch (err) { console.error('[Renderer] ETH error:', err); }
}

async function loadBinancePolar() {
  try {
    console.log("[Renderer] Fetching Binance Polar from backend...");
    const res = await fetch("http://127.0.0.1:5001/api/binance_polar");
    const data = await res.json();
    renderBinancePolar(data);
  } catch (err) {
    console.error("[Renderer] Binance Polar error:", err);
  }
}

async function loadMarketBrain() {
  console.log("[Renderer] Opening MarketBrain…");

  // ✅ Mostrar Allium por defecto
  const viewAllium = document.getElementById("marketbrain-allium-view");
  const viewBinance = document.getElementById("marketbrain-binance-market");
  const viewPolar = document.getElementById("marketbrain-binance-polar");

  if (viewAllium) viewAllium.style.display = "block";
  if (viewBinance) viewBinance.style.display = "none";
  if (viewPolar) viewPolar.style.display = "none";

  // ✅ No cargar Binance aquí
  // Nos quedamos esperando a que el usuario haga clic en "Binance Market"
  console.log("[Renderer] ✅ Waiting for subtab selection");
}

// =========================================================
// RENDERERS
// =========================================================



// =========================================================
// 🧠 Ethereum Renderer (limpio, sin Allium ni staking)
// =========================================================
function renderEth(data) {
  console.log('[Renderer] renderEth:', data);

  // === Activar sección ETH ===
  const section = document.getElementById('eth-section');
  if (section) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    section.classList.add('active');
  }

  // === Ocultar spinner ===
  const loading = document.getElementById('eth-loading');
  if (loading) loading.style.display = 'none';

  // =========================================================
  // 📊 Market Stats
  // =========================================================
  const statsBody = document.getElementById('eth-marketStatsTableBody');
  if (statsBody) {
    statsBody.innerHTML = '';
    Object.entries(data?.markets || {}).forEach(([k, v]) => {
      statsBody.innerHTML += `<tr><td>${k}</td><td>${v}</td></tr>`;
    });
  }

  // =========================================================
  // 📈 Performance
  // =========================================================
  const perfBody = document.getElementById('eth-performanceTableBody');
  if (perfBody) {
    perfBody.innerHTML = '';
    if (data?.yields) {
      perfBody.innerHTML += `<tr><td>24h</td><td>${data.yields.percent_change_24h ?? '—'}%</td></tr>`;
      perfBody.innerHTML += `<tr><td>7d</td><td>${data.yields.percent_change_7d ?? '—'}%</td></tr>`;
      perfBody.innerHTML += `<tr><td>30d</td><td>${data.yields.percent_change_30d ?? '—'}%</td></tr>`;
    }
  }

  // =========================================================
  // 💰 ETH Price Trend (Candlestick)
  // =========================================================
  if (data.price_history) {
    const trace = {
      x: data.price_history.dates,
      open: data.price_history.open,
      high: data.price_history.high,
      low: data.price_history.low,
      close: data.price_history.close,
      type: 'candlestick'
    };

    Plotly.newPlot('eth-priceTrendChart', [trace], {
      title: 'ETH Price (OHLC)',
      paper_bgcolor: '#1a1a1a',
      plot_bgcolor: '#1a1a1a',
      font: { color: '#eee' },
      xaxis: { title: 'Date' },
      yaxis: { title: 'Price (USD)', tickformat: ',.0f' }
    });
  }

  // =========================================================
  // 🐋 Whale Activity (Top Flows)
  // =========================================================
  const ethFlowsBody = document.getElementById('eth-topFlowsTableBody');
  if (ethFlowsBody) {
    ethFlowsBody.innerHTML = '';
    if (data.top_flows?.length) {
      data.top_flows.slice(-30).forEach(f => {
        const color =
          f.status?.toLowerCase().includes('sell') ? '#ff5252' :
          f.status?.toLowerCase().includes('buy') ? '#00e676' :
          '#aaa';
        ethFlowsBody.innerHTML += `
          <tr>
            <td>${f.timestamp || '-'}</td>
            <td>${(f.input_usd || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
            <td>${(f.output_usd || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
            <td style="color:${color};font-weight:600">${f.status || 'N/A'}</td>
          </tr>`;
      });
    } else {
      ethFlowsBody.innerHTML = `<tr><td colspan="4" class="centered-cell">No whale flow data available</td></tr>`;
    }
  }

  // =========================================================
  // 🟩🟥 Whale Net Flows Chart (Dual Bars + Line)
  // =========================================================
  const ethWhaleChartDiv = document.getElementById('ethWhaleFlowsChart');
  if (ethWhaleChartDiv && data.top_flows?.length) {
    const topFlows = data.top_flows.slice(-30);
    const dates = topFlows.map(f => f.timestamp);
    const inflows = topFlows.map(f => f.input_usd || 0);
    const outflows = topFlows.map(f => f.output_usd || 0);
    const netFlows = topFlows.map(f => (f.input_usd || 0) - (f.output_usd || 0));

    const traceIn = {
      x: dates, y: inflows,
      name: 'Inflows',
      type: 'bar',
      marker: { color: '#00e676', opacity: 0.85 }
    };
    const traceOut = {
      x: dates, y: outflows.map(v => -v),
      name: 'Outflows',
      type: 'bar',
      marker: { color: '#ff5252', opacity: 0.85 }
    };
    const traceNet = {
      x: dates, y: netFlows,
      name: 'Net Flow',
      type: 'scatter',
      mode: 'lines+markers',
      line: { color: '#ffffff', width: 2 },
      marker: { size: 6 }
    };

    Plotly.newPlot(ethWhaleChartDiv, [traceIn, traceOut, traceNet], {
      title: '🐋 ETH Whale Net Flows (USD)',
      barmode: 'relative',
      paper_bgcolor: '#111',
      plot_bgcolor: '#111',
      font: { color: '#eee' },
      margin: { t: 60, l: 100, r: 40, b: 70 },
      xaxis: { title: 'Date', tickangle: -25 },
      yaxis: { title: 'Flow (USD)', tickformat: ',.0f', gridcolor: '#222' },
      legend: { orientation: 'h', y: -0.3, x: 0.25 }
    });
  } else if (ethWhaleChartDiv) {
    ethWhaleChartDiv.innerHTML = '<p style="color:#888;text-align:center;">No whale data available</p>';
  }

  // =========================================================
  // 📥📤 Exchange Health Gauge
  // =========================================================
  const exchGaugeDiv = document.getElementById('eth-exchangeHealthGauge');
  if (exchGaugeDiv) {
    const inflow = data?.inflows || 0;
    const outflow = data?.outflows || 0;
    const ratio = inflow + outflow > 0 ? (inflow / (inflow + outflow)) * 100 : 0;

    Plotly.newPlot(exchGaugeDiv, [{
      type: 'indicator',
      mode: 'gauge+number',
      value: ratio,
      title: { text: 'Exchange Health (%)', font: { size: 18, color: '#eee' } },
      gauge: {
        axis: { range: [0, 100], tickwidth: 1, tickcolor: '#eee' },
        bar: { color: ratio > 50 ? '#00e676' : '#ff5252' },
        bgcolor: '#111',
        borderwidth: 1, bordercolor: '#333',
        steps: [
          { range: [0, 50], color: '#4d0000' },
          { range: [50, 100], color: '#003300' }
        ]
      }
    }], {
      paper_bgcolor: '#111', font: { color: '#eee' }
    });
  }

  // =========================================================
  // 💸 Transaction Fees Chart
  // =========================================================
  if (data?.fees) {
    Plotly.newPlot('eth-feesChart', [{
      x: data.fees.dates,
      y: data.fees.values,
      mode: 'lines',
      line: { color: '#f0c542' },
      name: 'Transaction Fees'
    }], {
      title: '💸 ETH Transaction Fees',
      paper_bgcolor: '#111', plot_bgcolor: '#111',
      font: { color: '#eee' },
      yaxis: { type: 'log', title: 'Fees (log scale)' }
    });
  }

  // =========================================================
  // 🤖 Insights & Analysis
  // =========================================================
  const insightsDiv = document.getElementById('ethInsights');
  if (insightsDiv) {
    insightsDiv.innerHTML = data.insights?.insight
      ? `<div class="insights-text">${marked.parse(data.insights.insight)}</div>`
      : `<i>No insights available</i>`;
  }

  const analysisDiv = document.getElementById('eth-marketAnalysis');
  const conclusionDiv = document.getElementById('eth-marketConclusion');
  if (analysisDiv) analysisDiv.textContent = data.analysis || 'No advice available';
  if (conclusionDiv) conclusionDiv.textContent = data.conclusion || 'N/A';
}

// =========================================================
// Binance Polar Renderer (LuxAlgo-style + Rotation Analysis)
// =========================================================

let currentPolarData = null;
let currentTimeframe = 'daily';
let currentOrder = 'none';

// 🎨 Colores asignados por símbolo
const POLAR_COLORS = {
  'BTC/USDT': 'gold',
  'ETH/USDT': 'aqua',
  'XRP/USDT': 'blue',
  'BNB/USDT': 'fuchsia',
  'SOL/USDT': 'green',
  'DOGE/USDT': 'lime',
  'ADA/USDT': 'maroon',
  'TRX/USDT': 'silver',
  'LINK/USDT': 'olive',
  'AVAX/USDT': 'orange'
};

// =========================================================
// 🔄 Capital Rotation Detection (Weekly → Daily momentum)
// =========================================================
function getPolarRotation(data) {
  if (!data?.results?.daily?.data || !data?.results?.weekly?.data) {
    return "Not enough data to analyze rotation.";
  }

  const daily = data.results.daily.data;
  const weekly = data.results.weekly.data;

  const dailyMap = Object.fromEntries(daily.map(d => [d.symbol, d.percent]));
  const weeklyMap = Object.fromEntries(weekly.map(d => [d.symbol, d.percent]));

  const momentum = [];

  for (const symbol in dailyMap) {
    if (weeklyMap[symbol] !== undefined) {
      momentum.push({
        symbol,
        change: weeklyMap[symbol] - dailyMap[symbol]
      });
    }
  }

  momentum.sort((a, b) => b.change - a.change);

  return `🔄 Capital Rotation (Weekly → Daily): ${momentum.map(m => m.symbol).join(" → ")}`;
}

// =========================================================
// Render principal
// =========================================================
function renderBinancePolar(data) {
  console.log('[Renderer] renderBinancePolar:', data);

  if (!data || !data.results) {
    console.warn('[Renderer] No polar data received');
    return;
  }

  currentPolarData = data;

  const timeframes = ['daily', 'weekly', 'monthly', 'yearly'];
  timeframes.forEach(tf => {
    const btn = document.getElementById(`binance_polar-${tf}`);
    if (btn && !btn.dataset.bound) {
      btn.addEventListener('click', () => {
        drawBinancePolar(tf, currentOrder);
        highlightActiveButton(tf);
      });
      btn.dataset.bound = 'true';
    }
  });

  const orderSelector = document.getElementById('binance_polar-order');
  if (orderSelector && !orderSelector.dataset.bound) {
    orderSelector.addEventListener('change', (e) => {
      drawBinancePolar(currentTimeframe, e.target.value);
    });
    orderSelector.dataset.bound = 'true';
  }

  drawBinancePolar(currentTimeframe, currentOrder);
  highlightActiveButton(currentTimeframe);
}

// =========================================================
function highlightActiveButton(tf) {
  ['daily', 'weekly', 'monthly', 'yearly'].forEach(t => {
    const btn = document.getElementById(`binance_polar-${t}`);
    if (btn) btn.classList.toggle('active', t === tf);
  });
}

// =========================================================
function drawBinancePolar(timeframe, order = 'none') {
  if (!currentPolarData) return;

  const dataset = [...(currentPolarData.results[timeframe]?.data || [])];
  if (!dataset.length) return;

  currentTimeframe = timeframe;
  currentOrder = order;

  if (order === 'ascending') dataset.sort((a, b) => a.percent - b.percent);
  if (order === 'descending') dataset.sort((a, b) => b.percent - a.percent);

  const symbols = dataset.map(d => d.symbol);
  const dominance = dataset.map(d => d.percent);

  const traces = dataset.map((d) => ({
    type: 'scatterpolar',
    r: [d.percent],
    theta: [d.symbol],
    mode: 'markers+text',
    text: `${d.symbol}<br>${d.percent.toFixed(2)}%`,
    textposition: 'top center',
    marker: { size: 12, color: POLAR_COLORS[d.symbol] || 'gray' },
    hovertext: `${d.symbol}<br>Vol: ${d.cum_vol.toFixed(0)} USD<br>Δ: ${(d.cum_delta * 100).toFixed(2)}%`,
    hoverinfo: 'text'
  }));

  const meanVal = dominance.reduce((a, b) => a + b, 0) / dominance.length;
  traces.push({
    type: 'scatterpolar',
    r: Array(symbols.length).fill(meanVal),
    theta: symbols,
    mode: 'lines',
    line: { dash: 'dot', color: 'gray' },
    hoverinfo: 'skip'
  });

  Plotly.newPlot('binancePolarChart', traces, {
    polar: { radialaxis: { visible: true, title: '% Dominance' } },
    showlegend: false,
    margin: { t: 40, l: 40, r: 40, b: 40 }
  });

  // 📝 Tabla
  const tableBody = document.getElementById('binance_polar-tableBody');
  tableBody.innerHTML = dataset.map(d => `
    <tr>
      <td>${d.symbol}</td>
      <td>${d.percent.toFixed(2)}%</td>
      <td>${d.cum_vol.toFixed(0)}</td>
      <td>${(d.cum_delta * 100).toFixed(2)}%</td>
    </tr>
  `).join('');

  // 🤖 Insights + Rotación
  const insightsDiv = document.getElementById('binance_polar-insights');
  if (insightsDiv) {
    const rotation = getPolarRotation(currentPolarData);
    const insights = (currentPolarData.results[timeframe].insights || []).map(line => `<p>${line}</p>`).join('');
    insightsDiv.innerHTML = `<p><strong>${rotation}</strong></p><hr>${insights}`;
  }
}

// =========================================================
// Timeframe Buttons (bind once DOM loaded)
// =========================================================
document.addEventListener('DOMContentLoaded', () => {
  ['daily','weekly','monthly','yearly'].forEach(tf => {
    const btn = document.getElementById(`binance_polar-${tf}`);
    if (btn) {
      btn.addEventListener('click', () => {
        drawBinancePolar(tf);
      });
    }
  });
});

// =========================================================
// EXPORTS (versión limpia sin staking)
// =========================================================

function exportToCSV(data, filename) {
  let rows = [];

  // --- Price History ---
  if (data.price_history?.dates) {
    rows.push("Date,Open,High,Low,Close,Volume");
    data.price_history.dates.forEach((d, i) => {
      rows.push([
        d,
        data.price_history.open?.[i] ?? '',
        data.price_history.high?.[i] ?? '',
        data.price_history.low?.[i] ?? '',
        data.price_history.close?.[i] ?? '',
        data.price_history.volume?.[i] ?? ''
      ].join(","));
    });
  }

  // --- Fees ---
  if (data.fees?.dates) {
    rows.push("\nDate,Fees");
    data.fees.dates.forEach((d, i) => {
      rows.push(`${d},${data.fees.values?.[i] ?? ''}`);
    });
  }

  // --- Exchange Flows ---
  rows.push("\nExchange Flows");
  rows.push(`Inflows,${data.inflows ?? 0}`);
  rows.push(`Outflows,${data.outflows ?? 0}`);
  rows.push(`Net Flow,${data.net_flow ?? 0}`);

  // --- Whale Flows ---
  if (data.top_flows?.length) {
    rows.push("\nWhale Flows");
    rows.push("Timestamp,Input USD,Output USD,Status");
    data.top_flows.forEach(f => {
      rows.push(`${f.timestamp},${f.input_usd},${f.output_usd},${f.status}`);
    });
  }

  // --- AI Analysis & Insights ---
  rows.push("\nAI Analysis");
  rows.push((data.insights?.insight || '⚠️ No analysis available').replace(/\n/g, " "));

  rows.push("\nConclusion");
  rows.push((data.conclusion || "N/A").replace(/\n/g, " "));

  // --- Export ---
  const blob = new Blob([rows.join("\n")], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.setAttribute("download", filename + ".csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// ============================================================
// Helper: multiline text con salto automático de página
// ============================================================
function addMultilineText(pdf, text, x, y, maxWidth, lineHeight = 6) {
  const pageHeight = pdf.internal.pageSize.height;
  const lines = pdf.splitTextToSize(String(text), maxWidth);
  for (let i = 0; i < lines.length; i++) {
    if (y > pageHeight - 20) {
      pdf.addPage();
      y = 20;
    }
    pdf.text(lines[i], x, y);
    y += lineHeight;
  }
  return y;
}

// ============================================================
// Export Report to PDF (versión limpia sin staking)
// ============================================================
async function exportReportToPDF(data, chartId, filename) {
  const { jsPDF } = window.jspdf;
  const pdf = new jsPDF();
  let y = 20;

  // --- Header ---
  pdf.setFontSize(18);
  pdf.text(`${filename} Report`, 14, y);
  y += 15;

  // --- Market Stats ---
  pdf.setFontSize(12);
  pdf.text("Market Stats:", 14, y);
  y += 6;
  Object.entries(data.markets || {}).forEach(([k, v]) => {
    y = addMultilineText(pdf, `${k}: ${v}`, 14, y, 180);
  });

  // --- Exchange Flows ---
  y += 6;
  pdf.text("Exchange Flows:", 14, y);
  y += 6;
  y = addMultilineText(pdf, `Inflows: ${data.inflows ?? 0}`, 14, y, 180);
  y = addMultilineText(pdf, `Outflows: ${data.outflows ?? 0}`, 14, y, 180);
  y = addMultilineText(pdf, `Net Flow: ${data.net_flow ?? 0}`, 14, y, 180);

  // --- AI Analysis ---
  y += 12;
  pdf.setFontSize(14);
  pdf.text("AI Analysis:", 14, y);
  y += 8;
  pdf.setFontSize(11);
  let insightText = data.insights?.insight || '⚠️ No analysis available';
  insightText = insightText
    .replace(/\*\*/g, '')
    .replace(/#{1,6}\s/g, '')
    .replace(/-\s/g, '• ')
    .replace(/\n{2,}/g, '\n');
  y = addMultilineText(pdf, insightText, 14, y, 180);

  // --- Conclusion ---
  y += 12;
  pdf.setFontSize(12);
  pdf.text("Conclusion:", 14, y);
  y += 8;
  y = addMultilineText(pdf, data.conclusion || 'N/A', 14, y, 180);

  // --- Main Price Chart ---
  const priceChartDiv = document.getElementById(chartId);
  if (priceChartDiv) {
    try {
      const img = await Plotly.toImage(priceChartDiv, { format: 'png', width: 800, height: 600 });
      if (y > pdf.internal.pageSize.height - 120) {
        pdf.addPage();
        y = 20;
      }
      pdf.addImage(img, 'PNG', 10, y, 180, 100);
      y += 110;
    } catch (err) {
      console.warn("Could not render price chart in PDF:", err);
    }
  }

  pdf.save(filename + '.pdf');
}


// ============================================================
// Binance Market → CSV Export (LOCAL DOWNLOAD, NO REPLACE) ✅
// ============================================================
function exportBinanceMarketCSV() {
  const table = document.getElementById("bm-topFlowsTableBody");
  if (!table || !table.children.length) {
    return alert("No Binance whale flow data available.");
  }

  const symbol = document.getElementById("marketbrain-symbols").value.trim().toUpperCase();
  const start  = document.getElementById("marketbrain-start").value || "";
  const end    = document.getElementById("marketbrain-end").value || "";

  let rows = ["Date,Input USD,Output USD,Status"];

  function cleanNumber(n) {
    n = Number(String(n).replace(/[^0-9.-]/g, ""));
    if (isNaN(n)) return "";
    if (Math.abs(n) >= 1_000_000_000) return (n / 1_000_000_000).toFixed(2) + "B";
    if (Math.abs(n) >= 1_000_000) return (n / 1_000_000).toFixed(2) + "M";
    return n.toFixed(0);
  }

  [...table.children].forEach(tr => {
    const date = tr.children[0].innerText;
    const input = cleanNumber(tr.children[1].innerText);
    const output = cleanNumber(tr.children[2].innerText);
    const status = tr.children[3].innerText;
    rows.push([date, input, output, status].join(","));
  });

  const blob = new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8;" });
  const filename = `binance_market_${symbol}_${start}_${end}.csv`;
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// ============================================================
// Binance Market → PDF Export with Chart
// ============================================================
async function exportBinanceMarketPDF() {
  const { jsPDF } = window.jspdf;
  const pdf = new jsPDF();
  let y = 20;

  pdf.setFontSize(18);
  pdf.text("Binance Market Report", 14, y);
  y += 12;

  // Whale table
  const table = document.getElementById("bm-topFlowsTableBody");
  if (table && table.children.length) {
    pdf.setFontSize(12);
    pdf.text("Top Whale Flows:", 14, y);
    y += 6;

    [...table.children].forEach(tr => {
      const row = [...tr.children].map(td => td.innerText).join("   ");
      pdf.text(row, 14, y);
      y += 6;
      if (y > 270) { pdf.addPage(); y = 20; }
    });
  }

  // Price Chart
  const chart = document.getElementById("bm-priceTrendChart");
  if (chart) {
    try {
      const img = await Plotly.toImage(chart, { format: "png", width: 900, height: 500 });
      if (y > 140) { pdf.addPage(); y = 20; }
      pdf.addImage(img, "PNG", 10, y, 190, 110);
      y += 120;
    } catch (err) {
      console.warn("Could not embed price chart:", err);
    }
  }

  pdf.save("binance_market_report.pdf");
}




// =========================================================
// 🧠 MarketBrain UI (Allium + Binance Market + Polar) — BLOQUE LIMPIO
// =========================================================

let activeSubtab = "allium";   // ÚNICA definición
let currentSymbol = "BTC";

// Estos se usan también fuera del DOMContentLoaded:
let inputSymbols, startInput, endInput, loadingDiv;

document.addEventListener("DOMContentLoaded", () => {
  const API_BASE = "http://127.0.0.1:5001";

  const loadBtn = document.getElementById("marketbrain-loadBtn");
  const refreshBtn = document.getElementById("marketbrain-refreshBtn");
  const exportCsvBtn = document.getElementById("marketbrain-exportCsvBtn");
  const exportPdfBtn = document.getElementById("marketbrain-exportPdfBtn");
  const exportBinanceCsvBtn = document.getElementById("bm-exportCsvBtn");
  if (exportBinanceCsvBtn) {
    exportBinanceCsvBtn.addEventListener("click", exportBinanceMarketCSV);
  }

  inputSymbols = document.getElementById("marketbrain-symbols");
  startInput = document.getElementById("marketbrain-start");
  endInput = document.getElementById("marketbrain-end");
  loadingDiv = document.getElementById("marketbrain-loading");

  // Fechas por defecto (últimos 30 días)
  const today = new Date();
  const start = new Date(today);
  start.setDate(today.getDate() - 30);
  const fmt = (d) => d.toISOString().slice(0, 10);

  if (!startInput.value) startInput.value = fmt(start);
  if (!endInput.value) endInput.value = fmt(today);
  if (!inputSymbols.value) inputSymbols.value = currentSymbol;

  // Tabs
  const btnAllium = document.getElementById("btnAlliumData");
  const btnBinance = document.getElementById("btnBinanceMarket");
  const btnPolar = document.getElementById("btnBinancePolar");

  const alliumView = document.getElementById("marketbrain-allium-view");
  const binanceView = document.getElementById("marketbrain-binance-market");
  const polarView = document.getElementById("marketbrain-binance-polar");

  function toggleDatePickers(show) {
    const container = document.getElementById("marketbrain-date-controls");
    if (container) container.style.display = show ? "" : "none";
  }

  function showSubtab(name) {
    activeSubtab = name;

    alliumView.style.display = "none";
    binanceView.style.display = "none";
    polarView.style.display = "none";

    if (name === "allium") alliumView.style.display = "block";
    if (name === "binance") binanceView.style.display = "block";
    if (name === "polar") polarView.style.display = "block";

    btnAllium.classList.toggle("active", name === "allium");
    btnBinance.classList.toggle("active", name === "binance");
    btnPolar.classList.toggle("active", name === "polar");

    // Date pickers sólo en Binance Market
    toggleDatePickers(name === "binance");

    // Ocultar/mostrar exportaciones globales en Binance Polar
    const gCsvBtn = document.getElementById("marketbrain-exportCsvBtn");
    const gPdfBtn = document.getElementById("marketbrain-exportPdfBtn");
    if (gCsvBtn && gPdfBtn) {
      if (name === "polar") {
        gCsvBtn.style.display = "none";
        gPdfBtn.style.display = "none";
      } else {
        gCsvBtn.style.display = "";
        gPdfBtn.style.display = "";
      }
    }
  }

  btnAllium.addEventListener("click", () => showSubtab("allium"));
  btnBinance.addEventListener("click", () => showSubtab("binance"));
  btnPolar.addEventListener("click", () => showSubtab("polar"));

  // Estado por defecto
  toggleDatePickers(false);
  showSubtab("allium");

  // ==============================
  // CSV EXPORT (Selector inteligente)
  // ==============================
  if (exportCsvBtn) exportCsvBtn.addEventListener("click", async () => {
    const symbol = inputSymbols.value.trim().toUpperCase();
    const start = startInput?.value || "";
    const end = endInput?.value || "";

    if (loadingDiv) loadingDiv.style.display = "block";
    try {
      if (activeSubtab === "allium") {
        console.log("📤 Exportando CSV desde Allium...");
        await window.electronAPI.exportMarketbrainCsv({
          symbols: symbol,
          startDate: start,
          endDate: end
        });
      } else if (activeSubtab === "binance") {
        console.log("📤 Exportando CSV desde Binance Market...");
        exportBinanceMarketCSV(); // genera CSV local de la vista
      } else {
        alert("⚠️ Esta pestaña no tiene exportación CSV disponible aún.");
      }
    } catch (err) {
      console.error("[Renderer] CSV Export Error:", err);
    } finally {
      if (loadingDiv) loadingDiv.style.display = "none";
    }
  });

  // ==============================
  // PDF EXPORT (con gráfico para Allium)
  // ==============================
  if (exportPdfBtn) exportPdfBtn.addEventListener("click", async () => {
    const symbol = inputSymbols.value.trim().toUpperCase();
    const start = startInput?.value || "";
    const end   = endInput?.value || "";

    let chartImageBase64 = null;

    // Solo capturar gráfico si estamos en ALLIUM
    if (activeSubtab === "allium") {
      const firstChart = document.querySelector("#marketbrain-charts .js-plotly-plot");
      if (firstChart) {
        try {
          chartImageBase64 = await Plotly.toImage(firstChart, { format: "png", width: 1200, height: 700 });
        } catch (err) {
          console.warn("⚠️ No se pudo capturar el gráfico:", err);
        }
      }
    }

    // Subtab → sección esperada por main.js
    const section =
      activeSubtab === "allium" ? "allium" :
      activeSubtab === "binance" ? "binance_market" :
      activeSubtab === "polar" ? "binance_polar" :
      null;

    if (!section) {
      alert("⚠️ Esta pestaña no tiene exportación PDF disponible.");
      return;
    }

    const result = await window.electronAPI.exportPDF({
      section,
      symbols: symbol,
      startDate: start,
      endDate: end,
      chartImageBase64
    });

    if (!result || result.canceled) return;
    console.log("[Renderer] ✅ PDF saved:", result.filePath);
  });

  // ==============================
  // LOAD & REFRESH
  // ==============================
  if (loadBtn) loadBtn.addEventListener("click", loadMarketBrainData);
  if (refreshBtn) refreshBtn.addEventListener("click", loadMarketBrainData);

  // Carga inicial
  loadMarketBrainData();
}); // <-- FIN de DOMContentLoaded (todas las llaves bien cerradas)


// =========================================================
// 📡 DATA LOADER
// =========================================================
async function loadMarketBrainData() {
  const symbol = inputSymbols?.value.trim().toUpperCase() || currentSymbol;
  const startDate = startInput?.value;
  const endDate = endInput?.value;

  if (loadingDiv) loadingDiv.style.display = "block";

  try {
    if (activeSubtab === "allium") {
      const data = await window.electronAPI.loadData({
        section: "marketbrain",
        symbols: symbol,
        startDate,
        endDate
      });
      renderMarketBrain(data);
    } else if (activeSubtab === "binance") {
      await loadBinanceMarketData(symbol, startDate, endDate);
    } else if (activeSubtab === "polar") {
      await loadBinancePolar();
    }
  } catch (err) {
    console.error("[Renderer] MarketBrain load error:", err);
  } finally {
    if (loadingDiv) loadingDiv.style.display = "none";
  }
}

// ==============================
// 🟡 Binance Market (fetch + render)
// ==============================
async function loadBinanceMarketData(symbol, startDate, endDate) {
  const status = document.getElementById("bm-status");
  const loading = document.getElementById("bm-loading");

  if (loading) loading.style.display = "block";
  if (status) status.textContent = `⏳ Loading Binance market data for ${symbol}...`;

  try {
    const params = new URLSearchParams({ symbol, startDate, endDate });
    const res = await fetch(`http://127.0.0.1:5001/api/binance_market?${params}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    setTimeout(() => renderBinanceMarket(data), 150);
    if (status) status.textContent = "";
  } catch (err) {
    console.error("[Renderer] ❌ Error loading Binance Market:", err);
    if (status) status.textContent = `⚠️ Failed to load Binance market data.`;
  } finally {
    if (loading) loading.style.display = "none";
  }
}

// =========================================================
// 🧠 MarketBrain Dashboard Renderer
// =========================================================
function renderMarketBrain(data) {
  console.log("[Renderer] 🧠 renderMarketBrain:", data);
  window.lastMarketBrain = data;

  const tbody = document.getElementById("marketbrain-tableBody");
  const insightsDiv = document.getElementById("marketbrain-insights");
  const chartsDiv = document.getElementById("marketbrain-charts");

  if (!tbody || !insightsDiv || !chartsDiv) return;

  tbody.innerHTML = "";
  chartsDiv.innerHTML = "";
  insightsDiv.innerHTML = `<p class="centered-cell">No insights yet.</p>`;

  if (!data || !data.results) {
    tbody.innerHTML = `<tr><td colspan="9" class="centered-cell">⚠️ No data available</td></tr>`;
    return;
  }

  const allRows = [];

  Object.entries(data.results).forEach(([symbol, result]) => {
    const rows = result?.staking_table || [];
    rows.forEach((r) => allRows.push({ symbol, ...r }));

    // KPIs Arkham
    if (result?.arkham_summary) {
      const a = result.arkham_summary;
      const setKpi = (id, v) => {
        const el = document.getElementById(id);
        if (el) el.textContent = v;
      };
      setKpi("kpi-inflow", `$${(a.total_inflow || 0).toLocaleString()}`);
      setKpi("kpi-outflow", `$${(a.total_outflow || 0).toLocaleString()}`);
      setKpi("kpi-netflow", `$${(a.netflow || 0).toLocaleString()}`);
      setKpi("kpi-txcount", a.tx_count?.toLocaleString() || 0);
    }

    // Insights
    if (result?.insights) {
      try {
        const raw = result.insights.toString();
        insightsDiv.innerHTML = insightsDiv.innerHTML.replace(
          `<p class="centered-cell">No insights yet.</p>`,
          ""
        ) + `<div class="insight-text">${
          typeof marked !== "undefined" ? marked.parse(raw) : raw
        }</div>`;
      } catch {
        insightsDiv.innerHTML += `<pre class="insight-text">${result.insights}</pre>`;
      }
    }
  });

  const safeNum = (x) => (isNaN(x) || x == null ? 0 : Number(x));

  // KPI Totales Dashboard
  const totalActiveStake = allRows.reduce((a, b) => a + safeNum(b.active_stake_usd_current), 0);
  const totalStake = allRows.reduce((a, b) => a + safeNum(b.total_stake_usd_current), 0);
  const avgPctActive = allRows.length
    ? allRows.reduce((a, b) => a + safeNum(b.pct_total_stake_active), 0) / allRows.length
    : 0;
  const avgPrice = allRows.length
    ? allRows.reduce((a, b) => a + safeNum(b.token_price_at_date), 0) / allRows.length
    : 0;

  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  set("kpi-active-stake", `$${totalActiveStake.toLocaleString()}`);
  set("kpi-total-stake", `$${totalStake.toLocaleString()}`);
  set("kpi-pct-active", `${avgPctActive.toFixed(2)}%`);
  set("kpi-price", `$${avgPrice.toFixed(2)}`);

  // Tabla
  allRows.forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${r.symbol}</td>
      <td>${r.activity_date || "-"}</td>
      <td>${safeNum(r.active_stake_usd_current).toLocaleString()}</td>
      <td>${safeNum(r.total_stake_usd_current).toLocaleString()}</td>
      <td>${safeNum(r.pct_total_stake_active).toFixed(2)}%</td>
      <td>${safeNum(r.pct_circulating_staked_est).toFixed(2)}%</td>
      <td>${safeNum(r.net_flow).toLocaleString()}</td>
      <td>${safeNum(r.deposits_est).toLocaleString()}</td>
      <td>${safeNum(r.withdrawals_est).toLocaleString()}</td>
    `;
    tbody.appendChild(tr);
  });

  // Gráficos por token
  const grouped = {};
  allRows.forEach((r) => {
    if (!grouped[r.symbol]) grouped[r.symbol] = [];
    grouped[r.symbol].push(r);
  });

  Object.entries(grouped).forEach(([symbol, series]) => {
    const div = document.createElement("div");
    div.id = `chart-${symbol}`;
    div.style.height = "420px";
    chartsDiv.appendChild(div);

    const dates = series.map((r) => r.activity_date);
    const pctActive = series.map((r) => safeNum(r.pct_total_stake_active));
    const pctCircStaked = series.map((r) => safeNum(r.pct_circulating_staked_est));
    const netFlowBillions = series.map((r) => safeNum(r.net_flow) / 1e9);

    Plotly.newPlot(div.id, [
      {
        x: dates, y: pctActive, name: "% Active Stake", type: "scatter", mode: "lines", line: { width: 2 }
      },
      {
        x: dates, y: pctCircStaked, name: "% Circulating Staked", type: "scatter", mode: "lines", line: { width: 2, dash: "dot" }
      },
      {
        x: dates, y: netFlowBillions, name: "Net Flow (USD, billions)", type: "bar", yaxis: "y2", opacity: 0.45
      }
    ], {
      title: `${symbol} — Staking Dynamics`,
      xaxis: { title: "Date" },
      yaxis: { title: "% Metrics" },
      yaxis2: { title: "Net Flow (USD, billions)", overlaying: "y", side: "right" },
      legend: { orientation: "h", y: -0.25 },
      margin: { t: 60, l: 70, r: 70, b: 60 },
      paper_bgcolor: "#1e1e1e",
      plot_bgcolor: "#1e1e1e",
      font: { color: "#eee" }
    });
  });

  console.log("[Renderer] ✅ MarketBrain dashboard rendered successfully.");
}

// ===============================
// 📊 Render Binance Market Panel
// ===============================
function renderBinanceMarket(data) {
  console.log("[Renderer] renderBinanceMarket:", data);

  const symbol = Object.keys(data?.results || {})[0];
  const result = data?.results?.[symbol];
  if (!result) return;

  // Price Chart
  const priceDiv = document.getElementById("bm-priceTrendChart");
  if (priceDiv && result.candles?.dates?.length) {
    Plotly.newPlot(
      priceDiv,
      [{
        x: result.candles.dates,
        open: result.candles.open,
        high: result.candles.high,
        low: result.candles.low,
        close: result.candles.close,
        type: "candlestick",
        name: `${symbol} Price`
      }],
      { paper_bgcolor: "#111", plot_bgcolor: "#111", font: { color: "#eee" }, title: `${symbol} Price (Binance)` }
    );
  }

  // Market Stats Table
  const statsTbody = document.getElementById("bm-marketStatsTableBody");
  if (statsTbody) {
    statsTbody.innerHTML = `
      <tr><td>Last Price</td><td>$${result.markets?.price?.toLocaleString() || "-"}</td></tr>
      <tr><td>24h Volume</td><td>${result.markets?.volume_24h?.toLocaleString() || "-"}</td></tr>
      <tr><td>Accumulation Score</td><td>${result.accumulation_score ?? "-"}</td></tr>
      <tr><td>Smart Money Phase</td><td>${result.smart_money_phase ?? "-"}</td></tr>
    `;
  }

  // Performance Table
  const perfTbody = document.getElementById("bm-performanceTableBody");
  if (perfTbody) {
    perfTbody.innerHTML = `
      <tr><td>24h Change</td><td>${result.performance?.percent_change_24h ?? "-"}%</td></tr>
      <tr><td>7d Change</td><td>${result.performance?.percent_change_7d ?? "-"}%</td></tr>
      <tr><td>30d Change</td><td>${result.performance?.percent_change_30d ?? "-"}%</td></tr>
    `;
  }

  // Netflow Chart
  const whaleDiv = document.getElementById("bm-whaleFlowsChart");
  if (whaleDiv && result.netflow?.dates?.length) {
    Plotly.newPlot(whaleDiv, [{
      x: result.netflow.dates,
      y: result.netflow.values,
      type: "bar",
      name: "Net Flow (USD)"
    }], {
      paper_bgcolor: "#111",
      plot_bgcolor: "#111",
      font: { color: "#eee" }
    });
  }

  // Fees Chart
  const feesDiv = document.getElementById("bm-feesChart");
  if (feesDiv && result.fees?.dates?.length) {
    Plotly.newPlot(feesDiv, [{
      x: result.fees.dates,
      y: result.fees.values,
      mode: "lines",
      line: { width: 2 },
      name: "Fees"
    }], {
      paper_bgcolor: "#111",
      plot_bgcolor: "#111",
      font: { color: "#eee" }
    });
  }

  // Whale Table
  const whalesTbody = document.getElementById("bm-topFlowsTableBody");
  if (whalesTbody) {
    const list = result.whales_table || [];

    whalesTbody.innerHTML = list.length
      ? list.map((w) => `
        <tr>
          <td>${w.date || "-"}</td>
          <td>${w.input_usd ? `$${w.input_usd.toLocaleString()}` : "-"}</td>
          <td>${w.output_usd ? `$${w.output_usd.toLocaleString()}` : "-"}</td>
          <td style="color:${w.status === "buy" ? "#00ffaa" : "#ff6464"}; font-weight:600;">${w.status}</td>
        </tr>`
      ).join("")
      : `<tr><td colspan="4" class="centered-cell">No whale activity detected</td></tr>`;
  }

  // Insights
  const insightsBox = document.getElementById("bm-insights");
  if (insightsBox) {
    insightsBox.innerHTML =
      result.insights && result.insights !== "No AI insights available."
        ? marked.parse(result.insights)
        : `<p class="centered-cell">No AI insights available for this asset yet.</p>`;
  }

  // Timestamp
  const ts = document.getElementById("bm-lastUpdated");
  if (ts) ts.textContent = `Last Updated: ${data.timestamp || "Unknown"}`;
}

// ====================================
// ✅ FIN DEL BLOQUE
// ====================================