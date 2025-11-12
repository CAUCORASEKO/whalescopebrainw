# 🐋 WhaleScope — Markkina- ja lohkoketjuanalytiikan työkalu

[🌍 Read this in English](README.md)

**WhaleScope** on monialustainen työpöytäsovellus, joka yhdistää lohkoketju- ja markkinadataa.  
Sovellus kehitettiin osana harjoittelua **Aalto-yliopiston talous- ja kauppatieteiden laitoksella**  
(Opiskelija: Tieto- ja viestintätekniikka (TVT), RASEKO, Turku)

---

## 🚀 Ominaisuudet
- Reaaliaikainen Binance-markkinadatan analytiikka  
- Visualisointipaneelit (Electron + Chart.js / Plotly)  
- Python-backend Flaskilla ja Pandas-kirjastolla  
- Raporttien vienti PDF- ja CSV-muotoon  
- Upotettu Python-tulkin tuki (ei erillistä asennusta)

---

## 🧠 Arkkitehtuuri

Electron (käyttöliittymä)
│
├── IPC / spawn()
│
└── Python Flask-backend
├── whalescope_scripts/
├── SQLite3-tietokanta
└── REST API (localhost:5001)


---

## 🖼️ Kuvakaappaukset

| Hallintapaneeli | MarketBrain | Binance Polar |
|-----------------|--------------|---------------|
| ![Dashboard](docs/screenshot_dashboard.png) | ![MarketBrain](docs/screenshot_marketbrain.png) | ![Polar](docs/screenshot_polar.png) |

---

## 🧑‍💻 Kehittäjä
**Claudio Valenzuela (CAUCO)**  
- RASEKO – Tieto- ja viestintätekniikka (TVT), Turku  
- Harjoittelu Aalto-yliopistossa, Talous- ja kauppatieteiden laitos  
- Toiminimi (Tmi) Ohjelmistokehittäjä ja Data-analyytikko  
- [LinkedIn](#) • [GitHub](#)

---

## 📄 Lisenssi
MIT-lisenssi © 2025 Claudio Valenzuela (CAUCO)
