// =============================================================
// 🐋 Whalescope — Electron Main Process
// =============================================================
const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");
let backendProcess = null; // 🔹 Guardará la referencia al proceso Flask

// =============================================================
// 📁 Rutas base
// =============================================================

const isDev = !app.isPackaged;
const apiKeysPath = path.join(app.getPath("userData"), "api_keys.json");
const projectRoot = isDev
  ? path.resolve(__dirname, "..")
  : process.resourcesPath;

const pythonPath = isDev
  ? path.join(projectRoot, ".venv/bin/python3")   // ✅ desarrollo
  : path.join(process.resourcesPath, "pyapp/bin/python3"); // ✅ prod

console.log("[Main] 🐍 Using Python:", pythonPath);

// =============================================================
// ⚙️ Helpers — Ejecutar scripts Python (Dev vs App Instalada) ✅
// =============================================================
function runPythonScript(scriptPath, args = []) {
  return new Promise((resolve, reject) => {
    const isDev = !app.isPackaged;

    // ✅ En desarrollo usamos el script original desde el proyecto
    // ✅ En la app instalada el script está dentro de "Resources/python/whalescope_scripts"
    const realScriptPath = isDev
      ? scriptPath
      : path.join(
          process.resourcesPath,
          "python/whalescope_scripts",
          path.basename(scriptPath) // ✅ evita rutas incorrectas internas
        );

    console.log(`[Main] 🐍 Running Python script: ${realScriptPath}`);

    // ✅ Usamos pythonPath correcto (ya redefinido antes según Dev/Prod)
    const proc = spawn(pythonPath, [realScriptPath, ...args], {
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data) => (stdout += data.toString()));
    proc.stderr.on("data", (data) => (stderr += data.toString()));

    proc.on("close", (code) => {
      if (code === 0) {
        resolve(stdout.trim());
      } else {
        reject(new Error(stderr || `Python exited with code ${code}`));
      }
    });
  });
}
// =============================================================
// 💾 IPC — Guardar / Cargar API Keys
// =============================================================
ipcMain.handle("saveApiKeys", async (event, keys) => {
  try {
    fs.writeFileSync(apiKeysPath, JSON.stringify(keys, null, 2));
    console.log(`[Main] ✅ API keys saved to ${apiKeysPath}`);
    return { success: true };
  } catch (err) {
    console.error("[Main] ❌ Error saving API keys:", err);
    return { success: false, error: err.message };
  }
});

ipcMain.handle("loadApiKeys", async () => {
  try {
    if (fs.existsSync(apiKeysPath)) {
      const keys = JSON.parse(fs.readFileSync(apiKeysPath, "utf8"));
      console.log("[Main] ✅ API keys loaded:", keys);
      return { success: true, keys };
    }
    return { success: false, keys: {} };
  } catch (err) {
    console.error("[Main] ❌ Error loading API keys:", err);
    return { success: false, error: err.message };
  }
});

// =============================================================
// 📡 IPC — Carga de datos (desde Flask backend)
// =============================================================
ipcMain.handle("loadData", async (event, params) => {
  let endpoint = "";

  // ✅ Binance Polar → endpoint fijo sin query
  if (params.section === "binance_polar") {
    endpoint = `http://127.0.0.1:5001/api/binance_polar`;
  } 
  
  // ✅ Todo lo demás → pero SIN el campo section en el query
  else {
    const q = { ...params };
    delete q.section; // 🔥 Clave: no mandar 'section' en el query

    const query = new URLSearchParams(q).toString();
    endpoint = `http://127.0.0.1:5001/api/${params.section}?${query}`;
  }

  console.log(`[Main] 🌐 Fetching from backend: ${endpoint}`);

  try {
    const res = await fetch(endpoint);
    return await res.json();
  } catch (err) {
    console.error("[Main] ❌ Error loading data:", err);
    return { error: err.message };
  }
});

// =============================================================
// 📁 IPC — Exportar CSV (MarketBrain / Allium) — FIX ✅
// =============================================================
ipcMain.handle("marketbrain:exportCsv", async (event, { symbols, startDate, endDate }) => {
  const saveDialog = await dialog.showSaveDialog({
    title: `Export ${symbols} CSV`,
    defaultPath: `MarketBrain_${symbols}_${startDate}_${endDate}.csv`,
    filters: [{ name: "CSV Files", extensions: ["csv"] }],
  });

  if (saveDialog.canceled) return { canceled: true };

  const scriptPath = isDev
    ? path.join(projectRoot, "python/whalescope_scripts/export_marketbrain_csv.py")
    : path.join(process.resourcesPath, "python/whalescope_scripts/export_marketbrain_csv.py");

  try {
    console.log("[Main] 🧾 Running CSV export script...");

    const tempCsvPath = (await runPythonScript(scriptPath, [
      symbols,
      startDate,
      endDate
    ])).trim();

    fs.copyFileSync(tempCsvPath, saveDialog.filePath);

    require("electron").shell.openPath(saveDialog.filePath);
    return { canceled: false, filePath: saveDialog.filePath };

  } catch (err) {
    console.error("[Main] ❌ CSV Export Error:", err);
    return { canceled: false, error: err.message };
  }
});


// =============================================================
// 📁 IPC — Exportar CSV (Binance Market) — FIX ✅
// =============================================================
ipcMain.handle("binance_market:exportCsv", async (event, { symbol, startDate, endDate }) => {
  const saveDialog = await dialog.showSaveDialog({
    title: `Export ${symbol} Binance Market CSV`,
    defaultPath: `WhaleScope_${symbol}_${startDate}_${endDate}.csv`,
    filters: [{ name: "CSV Files", extensions: ["csv"] }],
  });

  if (saveDialog.canceled) return { canceled: true };

  const scriptPath = isDev
    ? path.join(projectRoot, "python/whalescope_scripts/export_binance_market_csv.py")
    : path.join(process.resourcesPath, "python/whalescope_scripts/export_binance_market_csv.py");

  try {
    console.log("[Main] 🧾 Running Binance Market CSV export script...");

    const tempCsvPath = (await runPythonScript(scriptPath, [
      symbol.toUpperCase(),
      "--start-date", startDate,
      "--end-date", endDate,
    ])).trim();

    fs.copyFileSync(tempCsvPath, saveDialog.filePath);

    require("electron").shell.openPath(saveDialog.filePath);
    return { canceled: false, filePath: saveDialog.filePath };

  } catch (err) {
    console.error("[Main] ❌ Binance CSV Export Error:", err);
    return { canceled: false, error: err.message };
  }
});




// =============================================================
// 📄 IPC — Exportar PDF (Allium / Binance Market) ✅
// =============================================================
ipcMain.handle("exportPDF", async (event, { section, symbols, startDate, endDate, chartImageBase64 }) => {
  try {
    const saveDialog = await dialog.showSaveDialog({
      title: `Export ${symbols} Report (PDF)`,
      defaultPath: `WhaleScope_${section}_${symbols}_${startDate}_${endDate}.pdf`,
      filters: [{ name: "PDF Files", extensions: ["pdf"] }],
    });

    if (saveDialog.canceled) return { success: false };

    let scriptPath;
    let args = [];

    // =========================================================
    // 🟡 ALLIUM (con gráfico opcional)
    // =========================================================
    if (section === "allium") {
      scriptPath = path.join(projectRoot, "python/whalescope_scripts/export_pdf_allium.py");

      // Guardamos el gráfico solo si existe
      let chartPath = "";
      if (chartImageBase64) {
        chartPath = path.join(app.getPath("temp"), `allium_chart_${Date.now()}.png`);
        fs.writeFileSync(chartPath, chartImageBase64.replace(/^data:image\/png;base64,/, ""), "base64");
      }

      args = [symbols.toUpperCase(), startDate, endDate];
      if (chartPath) args.push(chartPath);
    }

    // =========================================================
    // 🟦 BINANCE MARKET (sin gráfico)
    // =========================================================
    else if (section === "binance_market") {
      scriptPath = path.join(projectRoot, "python/whalescope_scripts/export_pdf_binance_market.py");
      args = [
        symbols.toUpperCase(),
        "--start-date", startDate,
        "--end-date", endDate
      ];
    }

    // =========================================================
    // 🚫 BINANCE POLAR — EXPORT DISABLED
    // =========================================================
    else if (section === "binance_polar") {
      console.warn("[Main] ❌ Export PDF blocked for Binance Polar");
      return { success: false, error: "Export is disabled for Binance Polar." };
    }

    // =========================================================
    // ❌ Cualquier otra sección desconocida
    // =========================================================
    else {
      throw new Error(`Unknown PDF export section: ${section}`);
    }

    console.log("[Main] 🧾 Running PDF script:", scriptPath, "ARGS:", args);

    const pdfTmpPath = (await runPythonScript(scriptPath, args)).trim();

    fs.copyFileSync(pdfTmpPath, saveDialog.filePath);

    const { shell } = require("electron");
    shell.openPath(saveDialog.filePath);

    console.log(`[Main] ✅ PDF exported → ${saveDialog.filePath}`);
    return { success: true, filePath: saveDialog.filePath };

  } catch (err) {
    console.error("[Main] ❌ PDF Export Error:", err);
    return { success: false, error: err.message };
  }
});
// =============================================================
// 📂 IPC — Abrir archivo sin crear ventana en blanco ✅
// =============================================================
ipcMain.handle("openPath", async (event, filePath) => {
  const { shell } = require("electron");
  shell.openPath(filePath); // ✅ Abre el archivo en Preview / Acrobat sin ventana extra
});




// =============================================================
// 🐍 IPC — Ejecutar scripts Python directamente
// =============================================================
ipcMain.handle("runPython", async (event, scriptPath) => {
  try {
    const result = await runPythonScript(scriptPath);
    return { success: true, output: result };
  } catch (err) {
    console.error("[Main] ❌ Error running Python script:", err);
    return { success: false, error: err.message };
  }
});

// =============================================================
// 🦄 IPC — Obtener datos de Lido Staking
// =============================================================
ipcMain.handle("getLidoData", async () => {
  const scriptPath = path.join(projectRoot, "python/whalescope_scripts/lido_staking.py");
  try {
    const output = await runPythonScript(scriptPath);
    return JSON.parse(output);
  } catch (err) {
    console.error("[Main] ❌ Error fetching Lido data:", err);
    return { error: err.message };
  }
});

// =============================================================
// 🧠 Crear ventana principal
// =============================================================
function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 860,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.loadFile("index.html");
  return win;
}

// =============================================================
// 🚀 Iniciar backend Flask (Detecta Desarrollo vs App Instalada)
// =============================================================
function startPythonBackend() {
  const isDev = !app.isPackaged;

  const pythonPath = isDev
    ? path.join(projectRoot, ".venv/bin/python3") // DEV
    : path.join(process.resourcesPath, "pyapp/bin/python3"); // PROD ✅

  const backendScript = isDev
    ? path.join(projectRoot, "python/whalescope_scripts/backend_ultra_pro.py") // DEV
    : path.join(process.resourcesPath, "pyapp/whalescope_scripts/backend_ultra_pro.py"); // ✅ FIX

  console.log(`[Main] Starting backend with Python: ${pythonPath}`);
  console.log(`[Main] Using backend script: ${backendScript}`);

  backendProcess = spawn(pythonPath, [backendScript], {
    cwd: isDev ? projectRoot : path.join(process.resourcesPath, "pyapp"), // ✅ FIX: CWD correcto
    env: { ...process.env },
    stdio: "inherit",
  });

  backendProcess.on("close", (code) => {
    console.log(`[Main] 🧩 Flask backend exited with code ${code}`);
  });

  backendProcess.on("error", (err) => {
    console.error("[Main] ❌ Backend failed to start:", err);
  });
}

// =============================================================
// 🪩 App Lifecycle
// =============================================================
app.whenReady().then(() => {
  startPythonBackend();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

// =============================================================
// 🧹 Cerrar backend Flask cuando se cierre la app
// =============================================================
app.on("before-quit", () => {
  if (backendProcess) {
    console.log("[Main] 🧹 Stopping Flask backend...");
    backendProcess.kill("SIGTERM"); // 🔸 Detiene Flask limpiamente
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});