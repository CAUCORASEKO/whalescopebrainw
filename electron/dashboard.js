const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Conectar a la base de datos con ruta dinámica
const dbPath = path.join(__dirname, 'whalescope.db');
const db = new sqlite3.Database(dbPath, (err) => {
    if (err) {
        console.error('Error al conectar a la base de datos:', err.message);
    } else {
        console.log('Conexión a la base de datos establecida correctamente.');
    }
});

// Función para obtener datos de mercado de BTC
function getBtcMarketData(callback) {
    console.log('Ejecutando getBtcMarketData...');
    db.get(`
        SELECT price, volume_24h, market_cap, timestamp
        FROM btc_market_stats
        ORDER BY timestamp DESC
        LIMIT 1
    `, (err, row) => {
        if (err) {
            console.error('Error al leer btc_market_stats:', err.message);
            callback(null);
            return;
        }
        console.log('Datos obtenidos de btc_market_stats:', row);
        callback(row);
    });
}

// Función para obtener datos históricos de BTC (precios y volumen)
function getBtcData(callback) {
    console.log('Ejecutando getBtcData...');
    db.all("SELECT date, price_usd, volume_usd FROM btc_prices ORDER BY date", [], (err, rows) => {
        if (err) {
            console.error('Error al leer datos de btc_prices:', err.message);
            callback([]);
            return;
        }
        console.log('Datos obtenidos de btc_prices:', rows.slice(0, 5));
        callback(rows);
    });
}

// Función para obtener datos de billeteras ETH
function getEthData(callback) {
    console.log('Ejecutando getEthData...');
    db.all(`
        SELECT address, token, balance, balance_usd, timestamp, category
        FROM eth_wallets
    `, (err, rows) => {
        if (err) {
            console.error('Error al leer eth_wallets:', err.message);
            callback([]);
            return;
        }
        console.log('Datos obtenidos de eth_wallets:', rows);
        callback(rows);
    });
}

// Función para obtener datos de billeteras BTC (detallados)
function getBtcWalletData(callback) {
    console.log('Ejecutando getBtcWalletData...');
    db.all(`
        SELECT w.address, w.balance_btc, w.balance_usd, w.category,
               t.tx_hash, t.value_btc as tx_value_btc, t.value_usd as tx_value_usd,
               t.date, t.source_address, t.destination_addresses, t.tx_type, t.fee_btc, t.confirmed
        FROM btc_wallets w
        LEFT JOIN btc_transactions t ON w.address = t.address
    `, (err, rows) => {
        if (err) {
            console.error('Error al leer btc_wallets y btc_transactions:', err.message);
            callback([]);
            return;
        }
        console.log('Datos obtenidos de btc_wallets y btc_transactions:', rows.slice(0, 5));
        callback(rows);
    });
}

// Función para obtener datos de BlackRock (billeteras BTC simplificadas para gráfico)
function getBlackrockData(callback) {
    console.log('Ejecutando getBlackrockData...');
    db.all("SELECT address, balance_btc, timestamp FROM btc_wallets LIMIT 10", [], (err, rows) => {
        if (err) {
            console.error('Error al leer datos de btc_wallets:', err.message);
            callback([]);
            return;
        }
        console.log('Datos obtenidos de btc_wallets:', rows);
        callback(rows);
    });
}

// Función para obtener eventos macroeconómicos (noticias de la FED)
function getFedNews(callback) {
    console.log('Ejecutando getFedNews...');
    db.all("SELECT date, title, description, source, timestamp FROM macro_events ORDER BY date DESC LIMIT 10", [], (err, rows) => {
        if (err) {
            console.error('Error al leer datos de macro_events:', err.message);
            callback([]);
            return;
        }
        console.log('Datos obtenidos de macro_events:', rows);
        callback(rows);
    });
}

// Función para obtener datos de Lido
function getLidoData(callback) {
    console.log('Ejecutando getLidoData...');
    const query = `
        SELECT pool_name, total_eth_deposited, eth_staked, eth_unstaked, staking_rewards, timestamp
        FROM liquid_staking_pools
        WHERE pool_name = 'Lido'
        LIMIT 1
    `;
    db.get(query, (err, row) => {
        if (err) {
            console.error('Error al leer liquid_staking_pools:', err.message);
            callback(null);
            return;
        }
        console.log('Datos obtenidos de liquid_staking_pools:', row);
        callback(row);
    });
}

// Función para obtener datos de colas de staking
function getStakingQueues(callback) {
    console.log('Ejecutando getStakingQueues...');
    db.all("SELECT queue_type, eth_amount, avg_wait_time, timestamp FROM eth_staking_queues", [], (err, rows) => {
        if (err) {
            console.error('Error al leer eth_staking_queues:', err.message);
            callback([]);
            return;
        }
        console.log('Datos obtenidos de eth_staking_queues:', rows);
        callback(rows);
    });
}

// Función para obtener el staking ratio
function getStakingRatio(callback) {
    console.log('Ejecutando getStakingRatio...');
    db.get("SELECT date, staking_ratio, avg_rewards, timestamp FROM eth_staking_ratio ORDER BY date DESC LIMIT 1", [], (err, row) => {
        if (err) {
            console.error('Error al leer eth_staking_ratio:', err.message);
            callback(null);
            return;
        }
        console.log('Datos obtenidos de eth_staking_ratio:', row);
        callback(row);
    });
}

// Función para renderizar todos los datos
function renderAllData() {
    getBtcMarketData((row) => {
        const btcMarketDataDiv = document.getElementById('btcMarketData');
        if (row) {
            btcMarketDataDiv.innerHTML = `
                <p>Precio: $${row.price.toFixed(2)}</p>
                <p>Volumen (24h): $${row.volume_24h.toLocaleString()}</p>
                <p>Capitalización de Mercado: $${row.market_cap.toLocaleString()}</p>
                <p>Última Actualización: ${row.timestamp}</p>
            `;
        } else {
            btcMarketDataDiv.innerHTML = 'No se encontraron datos de mercado de BTC.';
        }
    });

    getBtcData((rows) => {
        if (rows.length === 0) {
            console.warn('No se encontraron datos para el gráfico de precios de BTC.');
            return;
        }
        const dates = rows.map(row => row.date);
        const prices = rows.map(row => row.price_usd);
        const trace = {
            x: dates,
            y: prices,
            type: 'scatter',
            mode: 'lines',
            name: 'Precio de BTC (USD)'
        };
        const layout = {
            title: 'Precio de Bitcoin (USD)',
            xaxis: { title: 'Fecha' },
            yaxis: { title: 'Precio (USD)' },
            margin: { t: 30, b: 50, l: 50, r: 50 }
        };
        Plotly.newPlot('btc-price', [trace], layout);
    });

    getBtcData((rows) => {
        if (rows.length === 0) {
            console.warn('No se encontraron datos para el gráfico de volumen de BTC.');
            return;
        }
        const dates = rows.map(row => row.date);
        const volumes = rows.map(row => row.volume_usd);
        const trace = {
            x: dates,
            y: volumes,
            type: 'bar',
            name: 'Volumen de BTC (USD)'
        };
        const layout = {
            title: 'Volumen de Bitcoin (USD)',
            xaxis: { title: 'Fecha' },
            yaxis: { title: 'Volumen (USD)' },
            margin: { t: 30, b: 50, l: 50, r: 50 }
        };
        Plotly.newPlot('btc-volume', [trace], layout);
    });

    getEthData((rows) => {
        const ethDataDiv = document.getElementById('ethData');
        if (rows.length === 0) {
            ethDataDiv.innerHTML = 'No se encontraron datos de billeteras ETH.';
            return;
        }
        let html = `
            <table>
                <thead>
                    <tr>
                        <th>Dirección</th>
                        <th>Token</th>
                        <th>Balance</th>
                        <th>Balance (USD)</th>
                        <th>Categoría</th>
                        <th>Última Actualización</th>
                    </tr>
                </thead>
                <tbody>
        `;
        rows.forEach(row => {
            html += `
                <tr>
                    <td>${row.address}</td>
                    <td>${row.token}</td>
                    <td>${row.balance}</td>
                    <td>$${row.balance_usd.toFixed(2)}</td>
                    <td>${row.category}</td>
                    <td>${row.timestamp}</td>
                </tr>
            `;
        });
        html += `
                </tbody>
            </table>
        `;
        ethDataDiv.innerHTML = html;
    });

    getBtcWalletData((rows) => {
        const btcDataDiv = document.getElementById('btcData');
        if (rows.length === 0) {
            btcDataDiv.innerHTML = 'No se encontraron datos de billeteras BTC.';
            return;
        }
        const wallets = {};
        rows.forEach(row => {
            if (!wallets[row.address]) {
                wallets[row.address] = {
                    balance_btc: row.balance_btc,
                    balance_usd: row.balance_usd,
                    category: row.category,
                    transactions: []
                };
            }
            if (row.tx_hash) {
                wallets[row.address].transactions.push({
                    tx_hash: row.tx_hash,
                    value_btc: row.tx_value_btc,
                    value_usd: row.tx_value_usd,
                    date: row.date,
                    source_address: row.source_address,
                    destination_addresses: JSON.parse(row.destination_addresses),
                    tx_type: row.tx_type,
                    fee_btc: row.fee_btc,
                    confirmed: row.confirmed
                });
            }
        });

        let html = '';
        for (const [address, wallet] of Object.entries(wallets)) {
            html += `
                <h3>Billetera: ${address} (${wallet.category})</h3>
                <p>Balance: ${wallet.balance_btc} BTC ($${wallet.balance_usd.toFixed(2)} USD)</p>
                <table>
                    <thead>
                        <tr>
                            <th>Hash</th>
                            <th>Valor (BTC)</th>
                            <th>Valor (USD)</th>
                            <th>Fecha</th>
                            <th>Origen</th>
                            <th>Destinos</th>
                            <th>Tipo</th>
                            <th>Tarifa (BTC)</th>
                            <th>Confirmada</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            wallet.transactions.forEach(tx => {
                html += `
                    <tr>
                        <td>${tx.tx_hash}</td>
                        <td>${tx.value_btc}</td>
                        <td>$${tx.value_usd.toFixed(2)}</td>
                        <td>${tx.date}</td>
                        <td>${tx.source_address}</td>
                        <td>${tx.destination_addresses.join(', ')}</td>
                        <td>${tx.tx_type}</td>
                        <td>${tx.fee_btc}</td>
                        <td>${tx.confirmed ? 'Sí' : 'No'}</td>
                    </tr>
                `;
            });
            html += `
                    </tbody>
                </table>
            `;
        }
        btcDataDiv.innerHTML = html;
    });

    getBlackrockData((rows) => {
        if (rows.length === 0) {
            console.warn('No se encontraron datos para el gráfico de BlackRock.');
            return;
        }
        const addresses = rows.map(row => row.address);
        const balances = rows.map(row => row.balance_btc);
        const trace = {
            x: addresses,
            y: balances,
            type: 'bar',
            name: 'Saldo (BTC)'
        };
        const layout = {
            title: 'Saldos de Billeteras de BlackRock',
            xaxis: { title: 'Dirección', tickangle: 45 },
            yaxis: { title: 'Saldo (BTC)' },
            margin: { t: 30, b: 100, l: 50, r: 50 }
        };
        Plotly.newPlot('blackrock', [trace], layout);
    });

    getFedNews((rows) => {
        const newsDiv = document.getElementById('fed-news-content');
        if (rows.length === 0) {
            newsDiv.innerHTML = '<p>No se encontraron eventos de la FED.</p>';
            return;
        }
        let html = '<ul>';
        rows.forEach(row => {
            html += `<li><strong>${row.date}</strong>: ${row.title} - ${row.description}</li>`;
        });
        html += '</ul>';
        newsDiv.innerHTML = html;
    });

    getLidoData((row) => {
        const lidoDataDiv = document.getElementById('lidoData');
        if (!row) {
            lidoDataDiv.innerHTML = 'No se encontraron datos de Lido.';
            return;
        }
        lidoDataDiv.innerHTML = `
            <h3>Lido Staking Pool</h3>
            <table>
                <thead>
                    <tr>
                        <th>Métrica</th>
                        <th>Valor</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>Pool Name</td><td>${row.pool_name}</td></tr>
                    <tr><td>Total ETH Deposited</td><td>${row.total_eth_deposited.toLocaleString()}</td></tr>
                    <tr><td>ETH Staked</td><td>${row.eth_staked.toLocaleString()}</td></tr>
                    <tr><td>ETH Unstaked</td><td>${row.eth_unstaked.toLocaleString()}</td></tr>
                    <tr><td>Staking Rewards (ETH)</td><td>${row.staking_rewards.toLocaleString()}</td></tr>
                    <tr><td>Last Updated</td><td>${row.timestamp}</td></tr>
                </tbody>
            </table>
        `;
    });

    getStakingQueues((rows) => {
        const stakingQueuesDiv = document.getElementById('stakingQueues');
        if (rows.length === 0) {
            stakingQueuesDiv.innerHTML = 'No se encontraron datos de colas de staking.';
            return;
        }
        let html = `
            <h3>Staking Queues</h3>
            <table>
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>ETH Amount</th>
                        <th>Avg Wait Time (Days)</th>
                        <th>Last Updated</th>
                    </tr>
                </thead>
                <tbody>
        `;
        rows.forEach(row => {
            html += `
                <tr>
                    <td>${row.queue_type}</td>
                    <td>${row.eth_amount.toLocaleString()}</td>
                    <td>${(row.avg_wait_time / (24 * 60 * 60)).toFixed(2)}</td>
                    <td>${row.timestamp}</td>
                </tr>
            `;
        });
        html += `
                </tbody>
            </table>
        `;
        stakingQueuesDiv.innerHTML = html;
    });

    getStakingRatio((row) => {
        const stakingRatioDiv = document.getElementById('stakingRatio');
        if (!row) {
            stakingRatioDiv.innerHTML = 'No se encontraron datos de staking ratio.';
            return;
        }
        stakingRatioDiv.innerHTML = `
            <h3>Staking Ratio</h3>
            <table>
                <thead>
                    <tr>
                        <th>Métrica</th>
                        <th>Valor</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>Date</td><td>${row.date}</td></tr>
                    <tr><td>Staking Ratio</td><td>${(row.staking_ratio * 100).toFixed(2)}%</td></tr>
                    <tr><td>Average Rewards (APR)</td><td>${(row.avg_rewards * 100).toFixed(2)}%</td></tr>
                    <tr><td>Last Updated</td><td>${row.timestamp}</td></tr>
                </tbody>
            </table>
        `;
    });
}

// Funciones para ampliar y cerrar gráficos
function enlargeChart(chartId) {
    const modal = document.getElementById('chartModal');
    const enlargedChartDiv = document.getElementById('enlarged-chart');
    modal.style.display = 'block';

    if (chartId === 'btc-price') {
        getBtcData((rows) => {
            const dates = rows.map(row => row.date);
            const prices = rows.map(row => row.price_usd);
            const trace = {
                x: dates,
                y: prices,
                type: 'scatter',
                mode: 'lines',
                name: 'Precio de BTC (USD)'
            };
            const layout = {
                title: 'Precio de Bitcoin (USD) - Detalle',
                xaxis: { title: 'Fecha' },
                yaxis: { title: 'Precio (USD)' }
            };
            Plotly.newPlot('enlarged-chart', [trace], layout);
        });
    } else if (chartId === 'btc-volume') {
        getBtcData((rows) => {
            const dates = rows.map(row => row.date);
            const volumes = rows.map(row => row.volume_usd);
            const trace = {
                x: dates,
                y: volumes,
                type: 'bar',
                name: 'Volumen de BTC (USD)'
            };
            const layout = {
                title: 'Volumen de Bitcoin (USD) - Detalle',
                xaxis: { title: 'Fecha' },
                yaxis: { title: 'Volumen (USD)' }
            };
            Plotly.newPlot('enlarged-chart', [trace], layout);
        });
    } else if (chartId === 'blackrock') {
        getBlackrockData((rows) => {
            const addresses = rows.map(row => row.address);
            const balances = rows.map(row => row.balance_btc);
            const trace = {
                x: addresses,
                y: balances,
                type: 'bar',
                name: 'Saldo (BTC)'
            };
            const layout = {
                title: 'Saldos de Billeteras de BlackRock - Detalle',
                xaxis: { title: 'Dirección', tickangle: 45 },
                yaxis: { title: 'Saldo (BTC)' }
            };
            Plotly.newPlot('enlarged-chart', [trace], layout);
        });
    }
}

function closeModal() {
    const modal = document.getElementById('chartModal');
    modal.style.display = 'none';
}

window.onclick = function(event) {
    const modal = document.getElementById('chartModal');
    if (event.target == modal) {
        modal.style.display = 'none';
    }
};