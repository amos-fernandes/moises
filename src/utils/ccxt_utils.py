# src/utils/ccxt_utils.py

import ccxt.async_support as ccxt
import asyncio
from typing import Any, Dict, List, Optional, Tuple
import logging
import os
import aiohttp

# Importar configurações de um local centralizado  ---/home/verticalagent/dev/ai-nina/nina-cry/src/config/config.py
# Supondo que config.py está em src/config/config.py
CCXT_EXCHANGE_ID = os.environ.get("CCXT_EXCHANGE_ID", "binance")
CCXT_API_KEY = os.environ.get("CCXT_API_KEY")
CCXT_API_SECRET = os.environ.get("CCXT_API_SECRET")
CCXT_API_PASSWORD = os.environ.get("CCXT_API_PASSWORD")
CCXT_SANDBOX_MODE = os.environ.get("CCXT_SANDBOX_MODE", "false").lower() == "true"

from src.config.config import MULTI_ASSET_SYMBOLS


# === Função Principal ===
async def get_ccxt_exchange(logger_instance: Optional[logging.Logger] = None):
    """
    Cria e retorna uma instância da exchange configurada (ex: Binance).
    Usa credenciais do ambiente.
    """
    # Usa o logger fornecido ou cria um padrão
    logger = logger_instance or logging.getLogger("CCXT-Utils")

    logger.info(f"Inicializando exchange: {CCXT_EXCHANGE_ID}")
    
    exchange_class = getattr(ccxt, CCXT_EXCHANGE_ID)
    exchange = exchange_class({
        'apiKey': CCXT_API_KEY,
        'secret': CCXT_API_SECRET,
        'password': CCXT_API_PASSWORD,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot'  # ou 'future' se for usar alavancagem
        }
    })

    try:
        # Testa a conexão
        await exchange.fetch_time()
        logger.info(f"✅ Conexão com {CCXT_EXCHANGE_ID} estabelecida com sucesso.")
        return exchange
    except ccxt.AuthenticationError as e:
        logger.critical(f"❌ Autenticação falhou: chaves inválidas ou sem permissão. Erro: {e}")
        await exchange.close()
        return None
    except ccxt.NetworkError as e:
        logger.error(f"⚠️  Erro de rede ao conectar com {CCXT_EXCHANGE_ID}: {e}")
        await exchange.close()
        return None
    except Exception as e:
        logger.critical(f"❌ Erro inesperado ao conectar com {CCXT_EXCHANGE_ID}: {e}", exc_info=True)
        if hasattr(exchange, 'close'):
            await exchange.close()
        return None

async def get_current_portfolio(exchange: ccxt.Exchange, logger: logging.Logger) -> Optional[Dict[str, Dict[str, float]]]:
    """
    Busca o portfólio atual (balanços e valor em USD) da exchange.
    Retorna um dicionário com informações do portfólio ou None em caso de erro.
    Ex: {'total_value_usd': 10000.0, 'assets': {'BTC': {'free': 0.1, 'value_usd': 5000.0}, ...}}
    """
    try:
        # 1. Buscar balanços
        balances = await exchange.fetch_balance()
        
        # 2. Isolar apenas os ativos que temos saldo e que estão no nosso universo de negociação
        asset_symbols = [symbol.split('/')[0] for symbol in MULTI_ASSET_SYMBOLS.values()] # Ex: ['ETH', 'BTC', 'ADA', 'SOL']
        # Adicionar a moeda de cotação (ex: USDT)
        quote_currency = 'USDT' # Assumindo USDT, pegue do config se for variável
        asset_symbols.append(quote_currency)
        
        current_positions = {
            asset: {'free': balances.get(asset, {}).get('free', 0.0)}
            for asset in asset_symbols
            if balances.get(asset, {}).get('free', 0.0) > 0
        }

        # 3. Buscar os preços atuais para converter para USD
        total_value_usd = current_positions.get(quote_currency, {'free': 0.0})['free']
        symbols_to_fetch_price = [f"{asset}/{quote_currency}" for asset in current_positions if asset != quote_currency]
        
        if symbols_to_fetch_price:
            tickers = await exchange.fetch_tickers(symbols_to_fetch_price)
            for asset, position_info in current_positions.items():
                if asset == quote_currency:
                    position_info['value_usd'] = position_info['free']
                    continue
                
                ticker_symbol = f"{asset}/{quote_currency}"
                if ticker_symbol in tickers:
                    price = tickers[ticker_symbol].get('last') or tickers[ticker_symbol].get('bid')
                    if price:
                        value_usd = position_info['free'] * price
                        position_info['value_usd'] = value_usd
                        total_value_usd += value_usd
                    else:
                        logger.warning(f"Não foi possível obter o preço para {ticker_symbol} para calcular o valor do portfólio.")
                        position_info['value_usd'] = 0.0
                else:
                    logger.warning(f"Ticker para {ticker_symbol} não encontrado.")
                    position_info['value_usd'] = 0.0

        return {
            'total_value_usd': total_value_usd,
            'assets': current_positions
        }

    except Exception as e:
        logger.error(f"Erro ao buscar o portfólio atual da exchange: {e}", exc_info=True)
        return None


async def execute_portfolio_rebalance(
    exchange: ccxt.Exchange, 
    target_weights: Dict[str, float], # Ex: {'eth': 0.5, 'btc': 0.5, ...}
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    Lógica de execução de ordens para rebalancear o portfólio para os pesos alvo.
    Retorna um resumo das operações.
    """
    logger.info("--- INICIANDO CICLO DE REBALANCEAMENTO DE PORTFÓLIO ---")
    logger.info(f"Pesos Alvo da IA: {target_weights}")

    results = {"status": "pending", "orders": [], "errors": []}
    
    try:
        # 1. Obter o estado atual do portfólio
        portfolio_state = await get_current_portfolio(exchange, logger)
        if not portfolio_state:
            raise ValueError("Não foi possível obter o estado atual do portfólio da exchange.")

        total_value_usd = portfolio_state['total_value_usd']
        current_positions = portfolio_state['assets']
        logger.info(f"Valor Total Atual do Portfólio: ${total_value_usd:,.2f}")
        
        # 2. Calcular o valor alvo de cada ativo
        quote_currency = 'USDT' # Assumir USDT como moeda base
        asset_keys = list(target_weights.keys()) # ['eth', 'btc', 'ada', 'sol']
        asset_symbols = [MULTI_ASSET_SYMBOLS[key].split('/')[0] for key in asset_keys] # Ex: ['ETH', 'BTC', 'ADA', 'SOL']

        # Mapeamento reverso para encontrar a chave (eth) a partir do símbolo (ETH)
        key_from_symbol = {MULTI_ASSET_SYMBOLS[k].split('/')[0]: k for k in asset_keys}
        
        trade_plan = []
        for symbol in asset_symbols:
            key = key_from_symbol[symbol]
            target_weight = target_weights.get(key, 0.0)
            target_value_usd = total_value_usd * target_weight
            
            current_value_usd = current_positions.get(symbol, {}).get('value_usd', 0.0)
            
            trade_diff_usd = target_value_usd - current_value_usd
            trade_plan.append({'symbol': symbol, 'diff_usd': trade_diff_usd})
            
        logger.info(f"Plano de Negociação (Diferença em USD): {trade_plan}")
        
        # 3. Executar Ordens de Venda Primeiro para liberar capital
        orders_to_sell = [trade for trade in trade_plan if trade['diff_usd'] < 0]
        for trade in sorted(orders_to_sell, key=lambda x: x['diff_usd']): # Vende os maiores primeiro
            symbol_to_sell = trade['symbol']
            usd_to_sell = abs(trade['diff_usd'])
            market_symbol = f"{symbol_to_sell}/{quote_currency}"
            
            try:
                # Converter valor em USD para quantidade do ativo
                price = (await exchange.fetch_ticker(market_symbol))['bid'] # Usar preço de venda (bid)
                if not price: raise ValueError(f"Preço de BID indisponível para {market_symbol}")
                
                amount_to_sell = usd_to_sell / price
                
                # Checar se a quantidade a vender não excede o saldo
                available_to_sell = current_positions.get(symbol_to_sell, {}).get('free', 0.0)
                if amount_to_sell > available_to_sell:
                    logger.warning(f"Tentando vender {amount_to_sell:.6f} {symbol_to_sell}, mas apenas {available_to_sell:.6f} disponível. Ajustando ordem.")
                    amount_to_sell = available_to_sell

                # Checar se a ordem atende ao mínimo da exchange
                market_info = exchange.markets[market_symbol]
                min_amount = market_info.get('limits', {}).get('amount', {}).get('min')
                if min_amount and amount_to_sell < min_amount:
                    logger.info(f"Ordem de venda para {symbol_to_sell} ({amount_to_sell:.6f}) abaixo do mínimo ({min_amount}). Pulando.")
                    continue

                logger.info(f"Executando Market Sell: {amount_to_sell:.6f} {market_symbol}")
                order = await exchange.create_market_sell_order(market_symbol, amount_to_sell)
                results['orders'].append(order)
                
            except Exception as e_sell:
                error_msg = f"Erro ao executar ordem de VENDA para {symbol_to_sell}: {e}"
                logger.error(error_msg, exc_info=True)
                results['errors'].append(error_msg)

        # Dar um tempo para as ordens de venda serem processadas e o saldo USDT ser atualizado
        await asyncio.sleep(5) # 5 segundos de espera

        # 4. Executar Ordens de Compra
        orders_to_buy = [trade for trade in trade_plan if trade['diff_usd'] > 0]
        # Obter saldo USDT atualizado
        updated_balances = await exchange.fetch_balance()
        available_usd = updated_balances.get(quote_currency, {}).get('free', 0.0)
        logger.info(f"Saldo USDT disponível para compras: ${available_usd:,.2f}")
        
        total_usd_to_buy = sum(trade['diff_usd'] for trade in orders_to_buy)
        allocation_factor = 1.0
        if total_usd_to_buy > available_usd:
            logger.warning(f"Capital necessário para compras (${total_usd_to_buy:,.2f}) excede o saldo disponível (${available_usd:,.2f}). As ordens serão escaladas.")
            allocation_factor = available_usd / total_usd_to_buy

        for trade in sorted(orders_to_buy, key=lambda x: x['diff_usd'], reverse=True): # Compra os maiores primeiro
            symbol_to_buy = trade['symbol']
            usd_to_buy = trade['diff_usd'] * allocation_factor
            market_symbol = f"{symbol_to_buy}/{quote_currency}"
            
            try:
                # Checar se a ordem atende ao custo mínimo da exchange
                market_info = exchange.markets[market_symbol]
                min_cost = market_info.get('limits', {}).get('cost', {}).get('min')
                if min_cost and usd_to_buy < min_cost:
                    logger.info(f"Ordem de compra para {symbol_to_buy} (custo ${usd_to_buy:,.2f}) abaixo do mínimo (${min_cost}). Pulando.")
                    continue
                
                logger.info(f"Executando Market Buy: ${usd_to_buy:,.2f} de {market_symbol}")
                # CCXT v2+ usa `amount` para market buy orders, mas algumas exchanges usam `cost`
                # Para market buy com valor em USD, precisamos especificar o `cost`
                # `create_market_buy_order_with_cost` ou params
                params = {'quoteOrderQty': usd_to_buy} # Para Binance, comprar com USDT
                order = await exchange.create_market_buy_order(market_symbol, None, params)
                results['orders'].append(order)
                
            except Exception as e_buy:
                error_msg = f"Erro ao executar ordem de COMPRA para {symbol_to_buy}: {e}"
                logger.error(error_msg, exc_info=True)
                results['errors'].append(error_msg)

        results['status'] = "completed_with_errors" if results['errors'] else "completed"
        logger.info("--- CICLO DE REBALANCEAMENTO DE PORTFÓLIO CONCLUÍDO ---")
        return results

    except Exception as e:
        error_msg = f"Falha crítica no processo de rebalanceamento: {e}"
        logger.critical(error_msg, exc_info=True)
        results['status'] = "failed"
        results['errors'].append(error_msg)
        return results





# === Função: Coleta de Dados de Cripto ===
async def fetch_crypto_data(
    exchange: ccxt.Exchange,
    pairs: List[str],
    logger_instance: Optional[logging.Logger] = None
) -> Tuple[Dict[str, Any], bool, str]:
    """
    Coleta dados de mercado para uma lista de pares.
    Retorna (dados, sucesso, mensagem de erro).
    """
    logger = logger_instance or logging.getLogger("CCXT-Utils")
    collected_data: Dict[str, Any] = {}
    fetch_successful = True
    error_message = ""

    logger.info(f"Coletando dados para pares: {pairs}")

    for pair_symbol in pairs:
        pair_data_key = pair_symbol.replace("/", "_")
        current_pair_data = {}

        try:
            # Ticker
            if exchange.has['fetchTicker']:
                ticker = await exchange.fetch_ticker(pair_symbol)
                current_pair_data['ticker'] = {
                    'last': ticker.get('last'),
                    'bid': ticker.get('bid'),
                    'ask': ticker.get('ask'),
                    'volume': ticker.get('baseVolume'),
                    'timestamp': ticker.get('timestamp')
                }

            # OHLCV (1h, 168 candles = 1 semana)
            ohlcv = await exchange.fetch_ohlcv(pair_symbol, timeframe='1h', limit=168)
            current_pair_data['ohlcv_1h'] = ohlcv

            # Order book (opcional)
            if exchange.has['fetchOrderBook']:
                orderbook = await exchange.fetch_order_book(pair_symbol, limit=10)
                current_pair_data['orderbook'] = {
                    'bids': orderbook['bids'][:5],
                    'asks': orderbook['asks'][:5],
                    'timestamp': orderbook['timestamp']
                }

            collected_data[pair_data_key] = current_pair_data
            logger.debug(f"✅ Dados coletados para {pair_symbol}")

        except Exception as e:
            error_msg = f"Falha ao coletar dados para {pair_symbol}: {str(e)}"
            logger.error(error_msg)
            collected_data[pair_data_key] = {"error": str(e)}
            error_message += f"{error_msg}; "
            fetch_successful = False

    return collected_data, fetch_successful, error_message



