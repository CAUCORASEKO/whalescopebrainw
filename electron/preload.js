// preload.js — WhaleScope Electron Preload
const { contextBridge, ipcRenderer } = require('electron');

/**
 * @typedef {Object} LoadDataParams
 * @property {string} section - Section identifier ("bitcoin", "eth", "marketbrain", "binance_polar")
 * @property {string} [startDate] - Optional start date (YYYY-MM-DD), used for BTC/ETH
 * @property {string} [endDate] - Optional end date (YYYY-MM-DD), used for BTC/ETH
 * @property {Object} [filters] - Optional filters (e.g., { symbols: "BTC", exchanges: ["binance"] })
 */

/**
 * @typedef {Object} MarketbrainExportParams
 * @property {string} symbol - Crypto symbol (e.g., "BTC", "ETH")
 * @property {string} [startDate] - Optional start date (legacy only)
 * @property {string} [endDate] - Optional end date (legacy only)
 */

/**
 * @typedef {Object} MarketbrainExportResult
 * @property {boolean} canceled - Whether the save dialog was canceled
 * @property {string} [filePath] - Path to the saved file (if not canceled)
 */

/**
 * API exposed to the renderer via `window.electronAPI`
 * @typedef {Object} ElectronAPI
 * @property {(params: LoadDataParams) => Promise<any>} loadData
 * @property {(params: MarketbrainExportParams) => Promise<MarketbrainExportResult>} exportMarketbrainCsv
 * @property {(params: Object) => Promise<MarketbrainExportResult>} exportPDF
 * @property {(keys: Object) => Promise<void>} saveApiKeys
 * @property {() => Promise<any>} getLidoData
 * @property {(scriptPath: string) => Promise<any>} runPython
 */

/** @type {ElectronAPI} */
const api = {

  // ✅ Usado para cualquier llamada genérica (incluye BINANCE CSV)
  invoke: (channel, data) => ipcRenderer.invoke(channel, data),

  // 🔹 Carga de datos general
  loadData: (params) => ipcRenderer.invoke('loadData', params),

  // 🔹 Exportar CSV MarketBrain
  exportMarketbrainCsv: (params) => ipcRenderer.invoke('marketbrain:exportCsv', params),
  // 🔹 Exportar CSV Binance Market
  exportBinanceMarketCsv: (params) => ipcRenderer.invoke('binance_market:exportCsv', params),

    // 🔹 Exportar PDF (Allium / MarketBrain / etc)
  exportPDF: (params) => ipcRenderer.invoke('exportPDF', params),

  // 🔹 Abrir archivos después de exportar (abrir PDF sin ventana blanca)
  openPath: (filePath) => ipcRenderer.invoke('openPath', filePath),

  // 🔹 Guardar claves API
  saveApiKeys: (keys) => ipcRenderer.invoke('saveApiKeys', keys),

  // 🔹 Ejecutar scripts python directos
  runPython: (scriptPath) => ipcRenderer.invoke('runPython', scriptPath),

  // 🔹 Obtener datos de Lido staking
  getLidoData: () => ipcRenderer.invoke('getLidoData')
};

// Exponer la API al renderer (segura)
contextBridge.exposeInMainWorld('electronAPI', api);