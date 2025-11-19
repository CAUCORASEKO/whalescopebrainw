# 🎤 WhaleScope Desktop — Harjoittelun Esittely (Aalto-yliopisto)

**Tekijä:** Claudio Valenzuela (CAUCO)  
**Koulutus:** Tieto- ja viestintätekniikka (TVT), RASEKO — Turku  
**Harjoittelupaikka:** Aalto-yliopisto, Taloustieteen ja Kaupan laitos  
**Projekti:** WhaleScope Desktop -analytiikkasovellus  

---

## 1. Johdanto

Hei, olen **Claudio Valenzuela**, ja tämä on yhteenveto harjoitteluprojektistani Aalto-yliopistolle.  
Kehitin **WhaleScope**-sovelluksen, joka yhdistää markkinadatan, on-chain-analytiikan, whale-virrat ja automaattiset raportit.

Projekti yhdisti:
- Työpöytäsovelluksen kehityksen  
- Python-backendin  
- Data-analytiikan  
- Talousvisualisoinnin  

---

## 2. Projektin Tavoite

Tavoitteena oli rakentaa **ammattitasoinen macOS-sovellus**, joka:

- Visualisoi kryptomarkkinoiden trendit  
- Analysoi on-chain-dataa  
- Tunnistaa “whale”-liikkeitä  
- Luo PDF/CSV-raportteja  
- Tukee tutkimusta ja opetusta

Aalto tarvitsi sovelluksen, joka:
- Toimii offline  
- Sisältää upotetun Pythonin  
- On helppo jakaa `.dmg`-tiedostona  
- Tallentaa API-avaimet turvallisesti  

---

## 3. Teknologiat

### 🟦 Electron (käyttöliittymä)
- Electron 37  
- HTML / CSS / JavaScript  
- Plotly ja Chart.js  
- IPC-viestintä

### 🐍 Python Backend
- Flask REST API  
- Pandas, NumPy  
- Binance / Arkham / Allium API  
- SQLite-tietokanta  
- Upotettu Python 3.11 sovelluksen sisällä

---

## 4. Sovelluksen Ominaisuudet

### 🧠 MarketBrain
- Token-virrat  
- Nettoinflow/Outflow  
- Intensiteettipisteytys  
- Historiallinen analytiikka  

### 🐋 Whale Detector
- Suurten siirtojen tunnistus  
- Käyttäytymisanalyysi  
- Moniketjuinen seuranta  

### 📊 Dashboardit
- Markkinakatsaus  
- Polar-kaaviot  
- Whale-aktiviteetti  

### 📄 Raportointi
- PDF-vienti (sisältäen kaaviot)  
- CSV-vienti  
- Automaattinen avaus macOS:ssa  

### 🔐 Turvallisuus
API-avaimet tallennetaan vain tähän polkuun:



---

## 5. Haasteet ja Ratkaisut

### ✔ Pythonin upottaminen Electroniin  
Mukautettu Python-ympäristö kansiossa `Resources/pyapp/`.

### ✔ Kehitysympäristö vs. tuotantoversio  
Erot Electronin ja .app-tiedoston poluissa ratkaistu koodissa.

### ✔ Prosessien välinen kommunikointi  
Electron ↔ Flask  
JSON-pohjainen integraatio.

### ✔ Tietokanta  
Automaattinen tietojen tallennus ja siivous.

---

## 6. Lopputulos Aalto-yliopistolle

Lopullinen tuotos on täysin toimiva **macOS .dmg -sovellus**, joka:

- Ei vaadi Pythonin asennusta  
- Toimii offline  
- On vakaa ja helppokäyttöinen  
- Sisältää analytiikan, visualisoinnit ja raportoinnin  

Aalto on vahvistanut sovelluksen toimivuuden.

---

## 7. Opitut Taidot

### Tekniset
- Full-stack-kehitys  
- Python-analytiikka  
- Electron-sovellukset  
- API-integraatiot  
- macOS-paketointi  

### Ammatilliset
- Dokumentointi (EN & FI)  
- Projektinhallinta  
- Kommunikointi sidosryhmien kanssa  
- Versionhallinta (Git)

---

## 8. Yhteenveto

Projektin avulla yhdistin:
- Ohjelmistokehityksen  
- Data-analytiikan  
- Blockchain-teknologian  
- Työpöytäkehityksen  

WhaleScope on nyt valmis työkalu Aallon käyttöön.

---

