// scripts.js

console.log('[Index] Script loaded');

// Mapa de fuentes de datos y las claves API requeridas
const dataSourceApiKeys = {
  'Binance': [
    { id: 'binanceApiKey', label: 'Clave API de Binance', placeholder: 'Ingresa tu clave API de Binance' },
    { id: 'binanceApiSecret', label: 'Secreto API de Binance', placeholder: 'Ingresa tu secreto API de Binance' }
  ],
  'Ethereum Mainnet': [
    { id: 'etherscanApiKey', label: 'Clave API de Etherscan', placeholder: 'Ingresa tu clave API de Etherscan' }
  ],
  'Polygon Mainnet': [
    { id: 'polygonscanApiKey', label: 'Clave API de PolygonScan', placeholder: 'Ingresa tu clave API de PolygonScan' }
  ],
  'Kraken': [
    { id: 'krakenApiKey', label: 'Clave API de Kraken', placeholder: 'Ingresa tu clave API de Kraken' },
    { id: 'krakenApiSecret', label: 'Secreto API de Kraken', placeholder: 'Ingresa tu secreto API de Kraken' }
  ],
  'Coinbase': [
    { id: 'coinbaseApiKey', label: 'Clave API de Coinbase', placeholder: 'Ingresa tu clave API de Coinbase' },
    { id: 'coinbaseApiSecret', label: 'Secreto API de Coinbase', placeholder: 'Ingresa tu secreto API de Coinbase' }
  ]
};

window.showSection = function(section) {
  console.log(`[Index] showSection called with: ${section}`);
  try {
    const buttons = document.querySelectorAll('.navBtn');
    const sections = document.querySelectorAll('.section');

    console.log(`[Index] Found ${buttons.length} buttons`);
    console.log(`[Index] Found ${sections.length} sections`);

    buttons.forEach(btn => btn.classList.remove('active'));
    sections.forEach(sec => sec.classList.remove('active'));

    const btn = document.querySelector(`.navBtn[data-section="${section}-section"]`);
    const sec = document.getElementById(`${section}-section`);
    console.log('[Index] Selected button:', btn ? btn.outerHTML : 'null');
    console.log('[Index] Selected section:', sec ? sec.id : 'null');

    if (btn && sec) {
      btn.classList.add('active');
      sec.classList.add('active');
      console.log('[Index] Added active class to button and section');

      const event = new CustomEvent('sectionChange', { 
        detail: { section: section },
        bubbles: true,
        cancelable: true
      });
      console.log(`[Index] Dispatching sectionChange event for: ${section}`, event);
      document.dispatchEvent(event);
    } else {
      console.error(`[Index] Button or section not found for: ${section}`);
    }
  } catch (error) {
    console.error('[Index] Error in showSection:', error.message, error.stack);
  }
};

document.addEventListener('DOMContentLoaded', () => {
  console.log('[Index] DOM content loaded');

  // Actualizar los campos de API keys dinámicamente según la fuente de datos
  const dataSourceInput = document.getElementById('dataSource');
  const apiKeysSection = document.getElementById('apiKeysSection');

  function updateApiKeysFields() {
    const dataSource = dataSourceInput.value.trim();
    console.log(`[Index] Data Source changed to: ${dataSource}`);
    apiKeysSection.innerHTML = ''; // Limpiar campos previos

    const requiredKeys = dataSourceApiKeys[dataSource] || [];
    if (requiredKeys.length === 0) {
      apiKeysSection.innerHTML = '<p>No se requieren claves API para esta fuente de datos.</p>';
      return;
    }

    const flexRow = document.createElement('div');
    flexRow.className = 'flex-row';
    requiredKeys.forEach(key => {
      const formGroup = document.createElement('div');
      formGroup.className = 'form-group';
      formGroup.innerHTML = `
        <label for="${key.id}">${key.label}:</label>
        <input id="${key.id}" type="text" placeholder="${key.placeholder}" />
      `;
      flexRow.appendChild(formGroup);
    });
    apiKeysSection.appendChild(flexRow);
  }

  dataSourceInput.addEventListener('input', updateApiKeysFields);
  dataSourceInput.addEventListener('change', updateApiKeysFields);
  updateApiKeysFields(); // Llamada inicial

  // Handle Analyze Button
  const analyzeBtn = document.getElementById('analyzeBtn');
  if (analyzeBtn) {
    analyzeBtn.addEventListener('click', () => {
      console.log('[Index] Analyze button clicked');
      const toAnalyze = document.getElementById('toAnalyze').value;
      const dataSource = document.getElementById('dataSource').value.trim();
      const startDate = document.getElementById('startDate').value;
      const endDate = document.getElementById('endDate').value;
      const usdcContract = document.getElementById('usdcContract').value;
      const contractAddress = document.getElementById('contractAddress').value;
      const btcWallets = document.getElementById('btcWallets').value.split('\n').filter(w => w.trim());
      const ethWallets = document.getElementById('ethWallets').value.split('\n').filter(w => w.trim());

      // Recolectar dinámicamente las claves API según la fuente de datos
      const requiredKeys = dataSourceApiKeys[dataSource] || [];
      const apiKeys = {};
      for (const key of requiredKeys) {
        const input = document.getElementById(key.id);
        if (input) {
          apiKeys[key.id] = input.value;
          if (!input.value && dataSource in dataSourceApiKeys) {
            alert(`Por favor, ingresa la ${key.label} para la fuente de datos ${dataSource}.`);
            return;
          }
        }
      }

      // Validar fechas
      if (!startDate || !endDate) {
        alert('Por favor, selecciona las fechas de inicio y fin.');
        return;
      }

      // Ocultar la pantalla de entrada y mostrar la pantalla de resultados
      document.getElementById('inputScreen').style.display = 'none';
      document.getElementById('resultsScreen').style.display = 'block';

      // Mostrar la sección correspondiente
      window.showSection(toAnalyze);

      // Trigger data loading with user inputs
      const event = new CustomEvent('sectionChange', {
        detail: {
          section: toAnalyze,
          startDate,
          endDate,
          inputs: {
            dataSource,
            ...apiKeys,
            usdcContract,
            contractAddress,
            btcWallets,
            ethWallets
          }
        },
        bubbles: true,
        cancelable: true
      });
      document.dispatchEvent(event);
    });
  }
});