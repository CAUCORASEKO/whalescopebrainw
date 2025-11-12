# 🐋 WhaleScope — Market & Blockchain Analytics Platform

[🇫🇮 Lue tämä suomeksi](README_fi.md)

**WhaleScope** is a cross-platform desktop analytics tool integrating on-chain and market data.  
Developed as part of an academic internship at **Aalto University — Department of Economics and Commerce**  
(Student: Tieto- ja viestintätekniikka (TVT), RASEKO, Turku – Finland)

---

## 🚀 Features
- Real-time analytics for Binance Market data  
- Visualization dashboards (Electron + Chart.js / Plotly)  
- Python backend with Flask and Pandas  
- Export to PDF / CSV reports  
- Embedded Python runtime (no external Python installation required)

---

## 🧠 Architecture Overview
Electron (frontend)
│
├── IPC / spawn()
│
└── Python Flask backend
├── whalescope_scripts/
├── SQLite3 database
└── REST API (localhost:5001)


---

## 🖼️ Screenshots

| Dashboard | MarketBrain | Binance Polar |
|------------|--------------|---------------|
| ![Dashboard](docs/screenshot_dashboard.png) | ![MarketBrain](docs/screenshot_marketbrain.png) | ![Polar](docs/screenshot_polar.png) |

### 📄 PDF Export Example

![Export PDF](docs/screenshot_export_pdf.png)


---

## 🧰 Tech Stack

| Layer | Technologies |
|-------|---------------|
| Frontend | Electron, Node.js, Chart.js, Plotly |
| Backend | Python 3.11, Flask, Pandas, Matplotlib |
| Packaging | electron-builder, embedded Python |
| Platform | macOS (.dmg), cross-compatible |

---

## 🧑‍💻 Developer

**Claudio Valenzuela (CAUCO)**  
- 🇫🇮 Student — Tieto- ja viestintätekniikka (TVT), RASEKO, Turku  
- Internship — Aalto University, Dept. of Economics and Commerce  
- Toiminimi (Tmi) Developer | Data & Software Analytics  
- [LinkedIn](#) • [GitHub](#)

---

## ⚙️ Installation & Usage

### 1️⃣ Prerequisites
- macOS (tested on macOS Ventura / Sonoma)
- Node.js ≥ 18
- Python 3.11 (only required for development)

---

### 2️⃣ Clone the repository
```bash
git clone https://github.com/CAUCORASEKO/whalescope.git
cd whalescope/electron
```

---

### 3️⃣ Install dependencies
```bash
npm install
```

---

### 4️⃣ Run in development mode
This will start Electron and the Python backend using your local virtual environment (`.venv`):

```bash
npm start
```

You should see in the terminal:

```
[Main] 🐍 Starting Backend:
 → Python: .venv/bin/python3
 → Script: python/whalescope_scripts/backend_ultra_pro.py
 * Running on http://127.0.0.1:5001
```

Then the Electron app window will open automatically.

---

### 5️⃣ Build the production app (.dmg)
To package WhaleScope into a standalone macOS app with the embedded Python environment:

```bash
npm run dist:intel
```

The build output will appear in:

```
electron/dist/WhaleScope-1.0.0.dmg
```

You can distribute this `.dmg` directly — it runs on any Mac **without requiring Python installation**.

---

### 🧪 Troubleshooting

| Issue | Solution |
|--------|-----------|
| `Address already in use: 5001` | Close any previous backend process: `lsof -i :5001` → `kill -9 PID` |
| `"Empty output from script"` | Check that the `python/` folder was correctly copied inside `Resources/` |
| macOS blocks app (developer not verified) | Right-click → “Open” → confirm the first launch |


## 📄 License
MIT License © 2025 Claudio Valenzuela (CAUCO)

