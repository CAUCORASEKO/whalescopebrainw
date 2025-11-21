// =============================================================
// 🐋 Whalescope — Electron Main Process (DEV + DMG READY)
// =============================================================
const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");
let backendProcess = null;

// =============================================================
// 🌍 Entorno & Rutas Base (clave para DEV + .DMG)
// =============================================================
const isDev = !app.isPackaged;

const apiKeysPath = path.join(app.getPath("userData"), "api_keys.json");

// 🟡 DEV → carpeta del proyecto
// 🔵 DMG → pyapp dentro del .app
const projectRoot = isDev
  ? path.resolve(__dirname, "..", "pyapp")   // ← 💯 correcto
  : path.join(process.resourcesPath, "python"); 

// 🐍 Python interpreter
const pythonPath = isDev
  ? path.join(projectRoot, "..", ".venv/bin/python3") // ✅ DEV use .venv
  : path.join(projectRoot, "bin/python3");            // ✅ PROD uses embedded python

// =============================================================
// 🧭 Obtener ruta de script Python según entorno
// =============================================================
function getScriptPath(scriptName) {
  
    return path.join(projectRoot, "whalescope_scripts", scriptName);
    
}

// =============================================================
// ⚙️ Ejecutar script Python
// =============================================================
function runPythonScript(scriptName, args = []) {
  const scriptPath = getScriptPath(scriptName);

  console.log(`[Main] 🐍 Python: ${pythonPath}`);
  console.log(`[Main] 📄 Script: ${scriptPath}`);

  return new Promise((resolve, reject) => {
    const proc = spawn(pythonPath, [scriptPath, ...args], {
      cwd: projectRoot,
      env: { ...process.env },
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", d => stdout += d.toString());
    proc.stderr.on("data", d => stderr += d.toString());

    proc.on("close", code => {
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
  if (fs.existsSync(apiKeysPath))
    return { success: true, keys: JSON.parse(fs.readFileSync(apiKeysPath, "utf8")) };
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
ipcMain.handle("marketbrain:exportCsv", async (event, { symbols, startDate, endDate }) => {
  const saveDialog = await dialog.showSaveDialog({
    title: `Export MarketBrain CSV`,
    defaultPath: `MarketBrain_${symbols}_${startDate}_${endDate}.csv`,
    filters: [{ name: "CSV Files", extensions: ["csv"] }]
  });

  if (saveDialog.canceled) return { canceled: true };

  try {
    console.log("[Main] 🧾 Exporting MarketBrain CSV...");

    const tempCsvPath = await runPythonScript("export_marketbrain_csv.py", [
      symbols,
      startDate,
      endDate
    ]);

    fs.copyFileSync(tempCsvPath.trim(), saveDialog.filePath);
    require("electron").shell.openPath(saveDialog.filePath);

    return { success: true, filePath: saveDialog.filePath };
  } catch (err) {
    console.error("[Main] ❌ MarketBrain CSV Export Error:", err);
    return { success: false, error: err.message };
  }
});


// =============================================================
// 📄 Export CSV — Binance Market ✅
// =============================================================
ipcMain.handle("binance_market:exportCsv", async (_, { symbol, startDate, endDate }) => {
  const saveDialog = await dialog.showSaveDialog({
    defaultPath: `WhaleScope_${symbol}_${startDate}_${endDate}.csv`,
    filters: [{ name: "CSV Files", extensions: ["csv"] }],
  });
  if (saveDialog.canceled) return;

  const tempCsvPath = await runPythonScript("export_binance_market_csv.py", [
    symbol.toUpperCase(),
    "--start-date", startDate,
    "--end-date", endDate
  ]);

  fs.copyFileSync(tempCsvPath, saveDialog.filePath);
  require("electron").shell.openPath(saveDialog.filePath);
  return { success: true };
});

// =============================================================
// 📄 Export PDF — Allium & Binance Market ✅
// =============================================================
ipcMain.handle("exportPDF", async (_, { section, symbols, startDate, endDate, chartImageBase64 }) => {
  const saveDialog = await dialog.showSaveDialog({
    defaultPath: `WhaleScope_${section}_${symbols}_${startDate}_${endDate}.pdf`,
    filters: [{ name: "PDF Files", extensions: ["pdf"] }],
  });
  if (saveDialog.canceled) return;

  let scriptName, args = [];

  if (section === "allium") {
    scriptName = "export_pdf_allium.py";

    let chartPath = "";
    if (chartImageBase64) {
      chartPath = path.join(app.getPath("temp"), `allium_chart_${Date.now()}.png`);
      fs.writeFileSync(chartPath, chartImageBase64.replace(/^data:image\/png;base64,/, ""), "base64");
      args.push(chartPath);
    }

    args.unshift(symbols.toUpperCase(), startDate, endDate);
  }

  else if (section === "binance_market") {
    scriptName = "export_pdf_binance_market.py";
    args = [
      symbols.toUpperCase(),
      "--start-date", startDate,
      "--end-date", endDate
    ];
  }

  else return { success: false, error: "Export not supported here." };

  const pdfTmpPath = await runPythonScript(scriptName, args);
  fs.copyFileSync(pdfTmpPath, saveDialog.filePath);
  require("electron").shell.openPath(saveDialog.filePath);

  return { success: true };
});

// =============================================================
// 🚀 Flask Backend + Window
// =============================================================


function startPythonBackend() {
  const pythonExec = isDev
    ? path.join(projectRoot, "..", ".venv/bin/python3")
    : path.join(process.resourcesPath, "python", "bin", "python3");

  const backendScript = isDev
    ? path.join(projectRoot, "whalescope_scripts", "backend_ultra_pro.py")
    : path.join(process.resourcesPath, "python", "whalescope_scripts", "backend_ultra_pro.py");

  console.log("[Main] 🐍 Starting Backend:");
  console.log(" → Python:", pythonExec);
  console.log(" → Script:", backendScript);

  backendProcess = spawn(pythonExec, [backendScript], {
    cwd: isDev
      ? path.join(projectRoot, "..")
      : path.join(process.resourcesPath, "python"), // ✅ FIX AQUÍ
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
  setTimeout(createWindow, 1500); // ⏳ darle tiempo a Flask para arrancar
});
