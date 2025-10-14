# src/utils/ccxt_utils.py

"""
Módulo utilitário para interações com exchanges de criptomoedas usando a biblioteca CCXT.
Fornece funcionalidades para:
- Conectar à exchange.
- Buscar dados de mercado (preços, OHLCV).
- Gerenciar portfólio (buscar saldos, rebalancear).
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import ccxt.async_support as ccxt
from ccxt.base.errors import AuthenticationError, NetworkError

# --- CONFIGURAÇÃO CENTRALIZADA ---
# Carrega as configurações a partir de variáveis de ambiente.
# Em um projeto maior, considere usar uma biblioteca como Pydantic para validação.
logger = logging.getLogger("CCXT-Utils")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class ExchangeConfig:
    """Estrutura para as configurações da exchange."""
    ID = os.environ.get("CCXT_EXCHANGE_ID", "binance")
    API_KEY = os.environ.get("CCXT_API_KEY")
    API_SECRET = os.environ.get("CCXT_API_SECRET")
    API_PASSWORD = os.environ.get("CCXT_API_PASSWORD")  # Para exchanges como Coinbase Pro
    SANDBOX_MODE = os.environ.get("CCXT_SANDBOX_MODE", "false").lower() == "true"
    DEFAULT_TYPE = 'spot'  # 'spot' ou 'future'

# --- FUNÇÕES DE CONEXÃO E SETUP ---

async def get_ccxt_exchange(config: ExchangeConfig) -> Optional[ccxt.Exchange]:
    """
    Cria, configura e testa uma instância da exchange CCXT.

    Args:
        config (ExchangeConfig): Objeto de configuração com credenciais e detalhes da exchange.

    Returns:
        Optional[ccxt.Exchange]: Uma instância da exchange pronta para uso ou None em caso de falha.
    """
    logger.info(f"Inicializando exchange '{config.ID}' (Sandbox: {config.SANDBOX_MODE})...")
    
    if not hasattr(ccxt, config.ID):
        logger.critical(f"❌ Exchange ID '{config.ID}' não é válida ou suportada pela CCXT.")
        return None

    exchange_class = getattr(ccxt, config.ID)
    exchange = exchange_class({
        'apiKey': config.API_KEY,
        'secret': config.API_SECRET,
        'password': config.API_PASSWORD,
        'enableRateLimit': True,
        'options': {'defaultType': config.DEFAULT_TYPE},
    })

    if config.SANDBOX_MODE:
        logger.warning("MODO SANDBOX ATIVADO. Operações não serão executadas com dinheiro real.")
        exchange.set_sandbox_mode(True)

    try:
        await exchange.load_markets()
        await exchange.fetch_time()
        logger.info(f"✅ Conexão com '{config.ID}' estabelecida com sucesso.")
        return exchange
    except AuthenticationError as e:
        logger.critical(f"❌ Autenticação falhou: Chaves de API inválidas ou sem permissão. Erro: {e}")
    except NetworkError as e:
        logger.error(f"⚠️ Erro de rede ao conectar com '{config.ID}': {e}")
    except Exception as e:
        logger.critical(f"❌ Erro inesperado ao conectar com '{config.ID}': {e}", exc_info=True)
    
    # Se qualquer exceção ocorrer, fecha a conexão e retorna None
    await exchange.close()
    return None

# --- FUNÇÕES DE GERENCIAMENTO DE PORTFÓLIO ---

async def get_current_portfolio(
    exchange: ccxt.Exchange,
    assets_to_track: List[str],
    quote_currency: str
) -> Optional[Dict[str, Any]]:
    """
    Busca o portfólio atual (saldos e valor em USD/USDT) da exchange.

    Args:
        exchange (ccxt.Exchange): Instância da exchange conectada.
        assets_to_track (List[str]): Lista de símbolos de ativos a serem monitorados (ex: ['BTC', 'ETH']).
        quote_currency (str): A moeda de cotação para calcular o valor (ex: 'USDT').

    Returns:
        Optional[Dict[str, Any]]: Dicionário com o estado do portfólio ou None em caso de erro.
        Ex: {'total_value_quote': 10000.0, 'assets': {'BTC': {'free': 0.1, 'value_quote': 5000.0}, ...}}
    """
    try:
        balances = await exchange.fetch_balance()
        assets_with_quote = assets_to_track + [quote_currency]

        # Filtra apenas os ativos que nos interessam e que possuem saldo
        current_positions = {
            asset: {'free': balances.get(asset, {}).get('free', 0.0)}
            for asset in assets_with_quote
            if balances.get(asset, {}).get('total', 0.0) > 0
        }

        # Calcula o valor total na moeda de cotação
        total_value_quote = current_positions.get(quote_currency, {'free': 0.0})['free']
        
        symbols_to_fetch_price = [
            f"{asset}/{quote_currency}" for asset in current_positions 
            if asset != quote_currency and f"{asset}/{quote_currency}" in exchange.markets
        ]
        
        if not symbols_to_fetch_price:
            logger.info("Nenhum ativo (além da moeda de cotação) para precificar no portfólio.")
            return {
                'total_value_quote': total_value_quote,
                'assets': current_positions
            }

        tickers = await exchange.fetch_tickers(symbols_to_fetch_price)
        for symbol_pair, ticker_data in tickers.items():
            asset, _ = symbol_pair.split('/')
            price = ticker_data.get('last') or ticker_data.get('bid')
            
            if price and asset in current_positions:
                value_quote = current_positions[asset]['free'] * price
                current_positions[asset]['value_quote'] = value_quote
                total_value_quote += value_quote
            else:
                logger.warning(f"Não foi possível obter preço para '{symbol_pair}'.")
                current_positions[asset]['value_quote'] = 0.0
        
        # Garante que a própria moeda de cotação tenha seu valor registrado
        if quote_currency in current_positions:
            current_positions[quote_currency]['value_quote'] = current_positions[quote_currency]['free']

        return {'total_value_quote': total_value_quote, 'assets': current_positions}

    except Exception as e:
        logger.error(f"Erro ao buscar o portfólio atual da exchange: {e}", exc_info=True)
        return None


async def execute_portfolio_rebalance(
    exchange: ccxt.Exchange, 
    target_weights: Dict[str, float],
    all_asset_symbols: List[str],
    quote_currency: str,
    min_trade_diff_usd: float = 1.0
) -> Dict[str, Any]:
    """
    Executa ordens de mercado para rebalancear o portfólio para os pesos alvo.

    Args:
        exchange (ccxt.Exchange): Instância da exchange.
        target_weights (Dict[str, float]): Pesos alvo para cada ativo (ex: {'BTC': 0.5, 'ETH': 0.5}).
        all_asset_symbols (List[str]): Lista de todos os ativos considerados no universo de negociação.
        quote_currency (str): Moeda de cotação (ex: 'USDT').
        min_trade_diff_usd (float): A diferença mínima em USD para acionar uma negociação.

    Returns:
        Dict[str, Any]: Um resumo das operações, incluindo status, ordens e erros.
    """
    logger.info("--- INICIANDO CICLO DE REBALANCEAMENTO DE PORTFÓLIO ---")
    logger.info(f"Pesos Alvo da IA: {target_weights}")
    results = {"status": "pending", "executed_orders": [], "errors": []}

    try:
        # 1. Obter estado atual e valor total do portfólio
        portfolio_state = await get_current_portfolio(exchange, all_asset_symbols, quote_currency)
        if not portfolio_state:
            raise ValueError("Falha ao obter o estado atual do portfólio.")

        total_value_quote = portfolio_state['total_value_quote']
        current_positions = portfolio_state['assets']
        logger.info(f"Valor Total Atual do Portfólio: ${total_value_quote:,.2f} {quote_currency}")

        # 2. Calcular plano de negociação
        trade_plan = []
        for asset, target_weight in target_weights.items():
            target_value = total_value_quote * target_weight
            current_value = current_positions.get(asset, {}).get('value_quote', 0.0)
            trade_diff = target_value - current_value
            
            if abs(trade_diff) > min_trade_diff_usd:
                trade_plan.append({'symbol': asset, 'diff_quote': trade_diff})
        
        logger.info(f"Plano de Negociação (Diferença em {quote_currency}): {trade_plan}")
        
        # 3. Executar VENDAS primeiro para liberar capital
        sells = sorted([t for t in trade_plan if t['diff_quote'] < 0], key=lambda x: x['diff_quote'])
        for trade in sells:
            symbol = trade['symbol']
            amount_to_sell_quote = abs(trade['diff_quote'])
            market_symbol = f"{symbol}/{quote_currency}"
            
            try:
                # Converter valor para quantidade do ativo
                ticker = await exchange.fetch_ticker(market_symbol)
                price = ticker['bid'] # Preço de venda (bid)
                if not price: raise ValueError(f"Preço BID indisponível para {market_symbol}")
                
                amount_to_sell = amount_to_sell_quote / price
                market_info = exchange.markets[market_symbol]
                
                # Validar limites
                if exchange.amount_to_precision(market_symbol, amount_to_sell) < market_info.get('limits', {}).get('amount', {}).get('min', 0):
                    logger.warning(f"Ordem de venda para {symbol} abaixo do mínimo. Pulando.")
                    continue
                
                logger.info(f"Executando Market Sell: {amount_to_sell:.6f} de {market_symbol}")
                order = await exchange.create_market_sell_order(market_symbol, amount_to_sell)
                results['executed_orders'].append(order)

            except Exception as e_sell:
                error_msg = f"Erro na ordem de VENDA para {symbol}: {e_sell}"
                logger.error(error_msg, exc_info=True)
                results['errors'].append({"symbol": symbol, "error": str(e_sell)})

        # Pausa para garantir que o saldo seja atualizado na exchange
        if sells:
            logger.info("Aguardando 5s para atualização de saldo após vendas...")
            await asyncio.sleep(5)

        # 4. Executar COMPRAS com o capital disponível
        buys = sorted([t for t in trade_plan if t['diff_quote'] > 0], key=lambda x: x['diff_quote'], reverse=True)
        if buys:
            # Obter saldo atualizado da moeda de cotação
            updated_balances = await exchange.fetch_balance()
            available_quote = updated_balances.get(quote_currency, {}).get('free', 0.0)
            logger.info(f"Saldo {quote_currency} disponível para compras: ${available_quote:,.2f}")
            
            total_needed_for_buys = sum(t['diff_quote'] for t in buys)
            allocation_factor = min(1.0, available_quote / total_needed_for_buys if total_needed_for_buys > 0 else 1.0)
            if allocation_factor < 1.0:
                logger.warning(f"Capital insuficiente. Compras serão escaladas por um fator de {allocation_factor:.2f}.")

            for trade in buys:
                symbol = trade['symbol']
                cost_to_buy = trade['diff_quote'] * allocation_factor
                market_symbol = f"{symbol}/{quote_currency}"
                
                try:
                    market_info = exchange.markets[market_symbol]
                    if cost_to_buy < market_info.get('limits', {}).get('cost', {}).get('min', 0):
                        logger.warning(f"Ordem de compra para {symbol} (custo ${cost_to_buy:,.2f}) abaixo do mínimo. Pulando.")
                        continue
                        
                    logger.info(f"Executando Market Buy: ${cost_to_buy:,.2f} de {market_symbol}")
                    # A compra por 'cost' (quoteOrderQty) é específica de algumas exchanges como a Binance.
                    params = {'quoteOrderQty': cost_to_buy}
                    order = await exchange.create_market_buy_order(market_symbol, None, params)
                    results['executed_orders'].append(order)
                    
                except Exception as e_buy:
                    error_msg = f"Erro na ordem de COMPRA para {symbol}: {e_buy}"
                    logger.error(error_msg, exc_info=True)
                    results['errors'].append({"symbol": symbol, "error": str(e_buy)})

        results['status'] = "completed_with_errors" if results['errors'] else "completed"
    
    except Exception as e:
        error_msg = f"Falha crítica no processo de rebalanceamento: {e}"
        logger.critical(error_msg, exc_info=True)
        results['status'] = "failed"
        results['errors'].append({"symbol": "general", "error": error_msg})

    logger.info(f"--- CICLO DE REBALANCEAMENTO CONCLUÍDO (Status: {results['status']}) ---")
    return results

# --- BLOCO DE TESTE ---

async def main_test():
    """Função para testar as funcionalidades do módulo de forma isolada."""
    logger.info("--- INICIANDO TESTE DO MÓDULO CCXT UTILS ---")
    
    # 1. Carregar configuração e conectar
    config = ExchangeConfig()
    # Forçar sandbox para o teste, por segurança
    config.SANDBOX_MODE = True 
    
    exchange = await get_ccxt_exchange(config)
    if not exchange:
        logger.error("Não foi possível conectar à exchange. Abortando teste.")
        return

    try:
        # 2. Definir universo de negociação
        # Em um app real, isso viria do seu config principal
        QUOTE_CURRENCY = 'USDT'
        ASSET_UNIVERSE = ['BTC', 'ETH', 'SOL', 'ADA']

        # 3. Testar a busca de portfólio
        logger.info("\n--- Testando get_current_portfolio ---")
        portfolio = await get_current_portfolio(exchange, ASSET_UNIVERSE, QUOTE_CURRENCY)
        if portfolio:
            logger.info(f"Portfólio atual: Total ${portfolio['total_value_quote']:.2f} {QUOTE_CURRENCY}")
            logger.info(f"Ativos: {portfolio['assets']}")
        else:
            logger.error("Falha ao buscar portfólio.")

        # 4. Testar o rebalanceamento
        logger.info("\n--- Testando execute_portfolio_rebalance ---")
        # Exemplo de pesos alvo (soma deve ser 1.0)
        target_weights = {
            'BTC': 0.50,
            'ETH': 0.30,
            'SOL': 0.20,
            'ADA': 0.0, # Zerando a posição em ADA
        }
        
        rebalance_result = await execute_portfolio_rebalance(
            exchange, 
            target_weights, 
            ASSET_UNIVERSE, 
            QUOTE_CURRENCY
        )
        logger.info(f"Resultado do rebalanceamento: {rebalance_result}")

    finally:
        # 5. Fechar a conexão
        if exchange:
            logger.info("Fechando conexão com a exchange.")
            await exchange.close()

if __name__ == "__main__":
    # Para executar este teste:
    # 1. Defina as variáveis de ambiente: CCXT_EXCHANGE_ID, CCXT_API_KEY, CCXT_API_SECRET
    # 2. Rode o script: python src/utils/ccxt_utils.py
    asyncio.run(main_test())