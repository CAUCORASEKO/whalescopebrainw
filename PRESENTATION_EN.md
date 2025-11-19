# 🎤 WhaleScope Desktop — Internship Presentation (Aalto University)

**Author:** Claudio Valenzuela (CAUCO)  
**Study Program:** Tieto- ja viestintätekniikka (TVT), RASEKO — Turku, Finland  
**Internship Host:** Aalto University — Department of Economics and Commerce  
**Project:** WhaleScope Desktop Analytics Application  

---

## 1. Introduction

Hello, my name is **Claudio Valenzuela**, and this is the summary of my internship project at Aalto University.  
I developed **WhaleScope**, a desktop analytics application integrating market data, on-chain intelligence, whale flows, and automated report generation.

The project required combining:
- Desktop development (Electron)
- Python backend engineering
- Data analytics & APIs
- UX for financial dashboards

---

## 2. Project Goal

The goal of WhaleScope was to build a **professional standalone macOS tool** for:

- Visualizing crypto market trends  
- Analyzing on-chain flows  
- Detecting “whale” activity  
- Exporting PDF/CSV reports  
- Supporting academic research & market analysis  

Aalto required a system that:
- Runs offline  
- Has an embedded Python environment  
- Has a clean UI  
- Is easy to distribute as a `.dmg`  
- Stores API keys securely  

---

## 3. Technology Stack

### 🟦 Electron (Frontend)
- Electron 37  
- HTML / CSS / JavaScript  
- Plotly + Chart.js visualizations  
- IPC communication

### 🐍 Python Backend
- Flask REST API  
- Pandas, NumPy  
- Requests for API integrations  
- SQLite `marketbrain.db`  
- Embedded Python 3.11 inside the macOS app

### 🔗 APIs Used
- Binance API  
- Arkham Intelligence  
- Allium Analytics  
- Coingecko & CMC (optional)  

---

## 4. Application Features

### 🧠 MarketBrain Engine
- Token flows  
- Net inflow/outflow calculations  
- Intensity scoring  
- Historical data aggregation  

### 🐋 Whale Detector
- Identifies unusual transactions  
- Scores large movements  
- Tracks behavior across chains  

### 📊 Visualization Dashboards
- Market overview  
- Polar charts  
- Whale activity charts  
- Detailed metrics  

### 📄 Reporting Tools
- PDF generation (with charts)  
- CSV export  
- Auto-open on macOS  

### 🔐 Secure Environment
- API keys saved only in  
  `~/Library/Application Support/WhaleScope/api_keys.json`

---

## 5. Technical Challenges & Solutions

### ✔ Embedding Python inside Electron
Created a custom packaged Python environment under:



### ✔ Dev vs Production Path Resolution
Different logic for:
- `electron .` (dev)
- `.app` file (production)

### ✔ Multi-process communication
- Electron main → Python Flask backend
- Spawned processes for scripts
- JSON responses for all analytics

### ✔ Database Automation
- Automated saving of staking/whale data
- Clean schema design for academic use

---

## 6. Results for Aalto University

The final output is a **fully working macOS .dmg** application that:

- Requires no Python installation  
- Runs offline  
- Is stable and production-ready  
- Provides dashboards, analytics, and reporting  
- Can be used for teaching and research  

Aalto has confirmed the application works correctly.

---

## 7. Skills Learned

### Technical
- Full-stack architecture  
- Electron app development  
- Python data engineering  
- API integration  
- macOS packaging  
- Debugging multi-environment apps  

### Professional
- Documentation (English & Finnish)  
- Software delivery  
- Working with a university stakeholder  
- Task planning & version control  

---

## 8. Conclusion

This internship allowed me to combine:
- Software development  
- Data analytics  
- Blockchain intelligence  
- Desktop engineering

WhaleScope is now a complete, professional-grade tool delivered to Aalto University.

---



