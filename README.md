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

## 📄 License
MIT License © 2025 Claudio Valenzuela (CAUCO)
