// =============================================================
// 🐋 Whalescope — Electron Main Process (DEV + DMG READY)
// =============================================================
const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");

let backendProcess = null;

// =============================================================
// 🌍 Entorno & Rutas Base (DEV vs DMG)
// =============================================================
const isDev = !app.isPackaged;

// 🔹 Dev: raíz del repo (whalescopebrainw/)
// 🔹 Prod: Resources/python dentro del .app
const repoRoot = path.resolve(__dirname, "..");

const pythonRoot = isDev
  ? repoRoot                                  // DEV: whalescopebrainw/
  : path.join(process.resourcesPath, "python"); // PROD: Contents/Resources/python/

// Scripts Python (backend + exporters)
const scriptsRoot = isDev
  ? path.join(repoRoot, "python", "whalescope_scripts")
  : path.join(pythonRoot, "whalescope_scripts");

// Ejecutable de Python
const pythonExec = isDev
  ? path.join(repoRoot, ".venv", "bin", "python3") // DEV: .venv/bin/python3
  : path.join(pythonRoot, "bin", "python3");       // PROD: python/bin/python3

// API keys (siempre en userData)
const apiKeysPath = path.join(app.getPath("userData"), "api_keys.json");

// =============================================================
// 🧭 Ruta de scripts Python
// =============================================================
function getScriptPath(scriptName) {
  return path.join(scriptsRoot, scriptName);
}

// =============================================================
// ⚙️ Ejecutar script Python (exportadores, etc.)
// =============================================================
function runPythonScript(scriptName, args = []) {
  const scriptPath = getScriptPath(scriptName);

  console.log(`[Main] 🐍 Python: ${pythonExec}`);
  console.log(`[Main] 📄 Script: ${scriptPath}`);

  return new Promise((resolve, reject) => {
    const proc = spawn(pythonExec, [scriptPath, ...args], {
      cwd: isDev ? repoRoot : pythonRoot,
      env: { ...process.env },
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (d) => (stdout += d.toString()));
    proc.stderr.on("data", (d) => (stderr += d.toString()));

    proc.on("close", (code) => {
      if (code === 0) resolve(stdout.trim());
      else reject(new Error(stderr || `Python exited with code ${code}`));
    });
  });
}

// =============================================================
// 💾 API KEYS — Guardar / Cargar
// =============================================================
ipcMain.handle("saveApiKeys", async (_, keys) => {
  fs.writeFileSync(apiKeysPath, JSON.stringify(keys, null, 2));
  return { success: true };
});

ipcMain.handle("loadApiKeys", async () => {
  if (fs.existsSync(apiKeysPath)) {
    return {
      success: true,
      keys: JSON.parse(fs.readFileSync(apiKeysPath, "utf8")),
    };
  }
  return { success: false, keys: {} };
});

// =============================================================
// 📡 IPC — Carga de datos desde Flask Backend (REST)
// =============================================================
ipcMain.handle("loadData", async (event, params) => {
  let endpoint = "";

  if (params.section === "binance_polar") {
    endpoint = `http://127.0.0.1:5001/api/binance_polar`;
  } else {
    const q = { ...params };
    delete q.section;
    const query = new URLSearchParams(q).toString();
    endpoint = `http://127.0.0.1:5001/api/${params.section}?${query}`;
  }

  console.log(`[Main] 🌐 Fetching → ${endpoint}`);

  try {
    const res = await fetch(endpoint);
    return await res.json();
  } catch (err) {
    console.error("[Main] ❌ loadData error:", err);
    return { error: err.message };
  }
});

// =============================================================
// 📁 Export CSV — MarketBrain
// =============================================================
ipcMain.handle(
  "marketbrain:exportCsv",
  async (event, { symbols, startDate, endDate }) => {
    const saveDialog = await dialog.showSaveDialog({
      title: `Export MarketBrain CSV`,
      defaultPath: `MarketBrain_${symbols}_${startDate}_${endDate}.csv`,
      filters: [{ name: "CSV Files", extensions: ["csv"] }],
    });

    if (saveDialog.canceled) return { canceled: true };

    try {
      console.log("[Main] 🧾 Exporting MarketBrain CSV...");

      const tempCsvPath = await runPythonScript("export_marketbrain_csv.py", [
        symbols,
        startDate,
        endDate,
      ]);

      fs.copyFileSync(tempCsvPath.trim(), saveDialog.filePath);
      require("electron").shell.openPath(saveDialog.filePath);

      return { success: true, filePath: saveDialog.filePath };
    } catch (err) {
      console.error("[Main] ❌ MarketBrain CSV Export Error:", err);
      return { success: false, error: err.message };
    }
  }
);

// =============================================================
// 📄 Export CSV — Binance Market
// =============================================================
ipcMain.handle(
  "binance_market:exportCsv",
  async (_, { symbol, startDate, endDate }) => {
    const saveDialog = await dialog.showSaveDialog({
      defaultPath: `WhaleScope_${symbol}_${startDate}_${endDate}.csv`,
      filters: [{ name: "CSV Files", extensions: ["csv"] }],
    });
    if (saveDialog.canceled) return;

    const tempCsvPath = await runPythonScript("export_binance_market_csv.py", [
      symbol.toUpperCase(),
      "--start-date",
      startDate,
      "--end-date",
      endDate,
    ]);

    fs.copyFileSync(tempCsvPath, saveDialog.filePath);
    require("electron").shell.openPath(saveDialog.filePath);
    return { success: true };
  }
);

// =============================================================
// 📄 Export PDF — Allium & Binance Market
// =============================================================
ipcMain.handle(
  "exportPDF",
  async (_, { section, symbols, startDate, endDate, chartImageBase64 }) => {
    const saveDialog = await dialog.showSaveDialog({
      defaultPath: `WhaleScope_${section}_${symbols}_${startDate}_${endDate}.pdf`,
      filters: [{ name: "PDF Files", extensions: ["pdf"] }],
    });
    if (saveDialog.canceled) return;

    let scriptName;
    let args = [];

    if (section === "allium") {
      scriptName = "export_pdf_allium.py";

      let chartPath = "";
      if (chartImageBase64) {
        chartPath = path.join(
          app.getPath("temp"),
          `allium_chart_${Date.now()}.png`
        );
        fs.writeFileSync(
          chartPath,
          chartImageBase64.replace(/^data:image\/png;base64,/, ""),
          "base64"
        );
        args.push(chartPath);
      }

      args.unshift(symbols.toUpperCase(), startDate, endDate);
    } else if (section === "binance_market") {
      scriptName = "export_pdf_binance_market.py";
      args = [
        symbols.toUpperCase(),
        "--start-date",
        startDate,
        "--end-date",
        endDate,
      ];
    } else {
      return { success: false, error: "Export not supported here." };
    }

    const pdfTmpPath = await runPythonScript(scriptName, args);
    fs.copyFileSync(pdfTmpPath, saveDialog.filePath);
    require("electron").shell.openPath(saveDialog.filePath);

    return { success: true };
  }
);

// =============================================================
// 🚀 Flask Backend + Window
// =============================================================
function startPythonBackend() {
  const backendScript = getScriptPath("backend_ultra_pro.py");

  console.log("[Main] 🐍 Starting Backend:");
  console.log(" → Python:", pythonExec);
  console.log(" → Script:", backendScript);

  backendProcess = spawn(pythonExec, [backendScript], {
    cwd: isDev ? repoRoot : pythonRoot,
    env: { ...process.env },
    stdio: "inherit",
  });

  backendProcess.on("error", (err) => {
    console.error("[Main] ❌ Backend failed to start:", err);
  });

  backendProcess.on("close", (code) => {
    console.log(`[Main] 🧩 Backend closed with code ${code}`);
  });
}

function createWindow() {
  new BrowserWindow({
    width: 1280,
    height: 860,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  }).loadFile("index.html");
}

app.whenReady().then(() => {
  startPythonBackend();
  setTimeout(createWindow, 1500); // pequeño margen para que Flask arranque
});