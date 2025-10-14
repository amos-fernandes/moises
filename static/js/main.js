

// Simulação de Monte Carlo (Plotly)
function plotMonteCarlo() {
  const mean = 1000;
  const std = 150;
  const samples = Array.from({length: 5000}, () => {
    return mean + Math.random() * std * (Math.random() > 0.5 ? 1 : -1);
  });

  const hist = {
    x: samples,
    type: 'histogram',
    nbinsx: 50,
    marker: { color: '#00ccff' },
    name: 'Distribuição de Retornos'
  };

  const layout = {
    title: 'Simulação Monte Carlo - Distribuição de Retornos (5000 simulações)',
    xaxis: { title: 'Valor Final do Portfólio (USD)' },
    yaxis: { title: 'Frequência' },
    bargap: 0.1,
    paper_bgcolor: '#0f1620',
    plot_bgcolor: '#1a2430',
    font: { color: '#e0e0e0' }
  };

  Plotly.newPlot('monte-carlo-plot', [hist], layout);
}

// Carregar operações do backend
async function loadTrades() {
  try {
    const response = await fetch('/api/transactions/recent');
    const trades = await response.json();
    const tbody = document.querySelector('#trades-table tbody');
    tbody.innerHTML = '';

    trades.forEach(t => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${t.rnn_transaction_id.slice(0,8)}...</td>
        <td>${t.client_id}</td>
        <td>${t.rnn_decisions?.[0]?.asset_id || 'N/A'}</td>
        <td>$${t.initial_amount}</td>
        <td>$${t.final_calculated_amount}</td>
        <td style="color: ${t.profit_loss >= 0 ? '#00ff88' : '#ff3860'}">
          $${t.profit_loss}
        </td>
        <td><span class="status ${t.status}">${t.status}</span></td>
        <td><a href="https://polygonscan.com/tx/${t.blockchain_tx_hash}" target="_blank">Ver NFT</a></td>
      `;
      tbody.appendChild(row);
    });
  } catch (e) {
    console.error("Erro ao carregar operações:", e);
  }
}

// Conectar Web3 e carregar NFTs
async function connectWeb3() {
  if (window.ethereum) {
    const web3 = new Web3(window.ethereum);
    document.getElementById('web3-status').textContent = '✅ Conectado';
    await window.ethereum.request({ method: 'eth_requestAccounts' });

    // Simular busca de NFTs (em produção: use The Graph ou API do contrato)
    const nftContainer = document.getElementById('nft-container');
    nftContainer.innerHTML = `
      <div class="nft-item">
        <img src="https://via.placeholder.com/200/00ccff/ffffff?text=AINFT" alt="NFT"/>
        <h4>Operação #abc123</h4>
        <a href="https://mumbai.polygonscan.com/tx/0x..." target="_blank">Ver na Blockchain</a>
      </div>
    `;
  } else {
    document.getElementById('web3-status').textContent = '❌ Sem MetaMask';
  }
}

// Inicializar
document.addEventListener('DOMContentLoaded', () => {
  plotMonteCarlo();
  loadTrades();
  connectWeb3();
});