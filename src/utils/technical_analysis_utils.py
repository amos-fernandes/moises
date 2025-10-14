import os
import ccxt.async_support as ccxt
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd


# from .utils.logger import get_logger 
# logger = get_logger()
# Ou logger passado como argumento para as funções

# Variáveis de ambiente lidas uma vez no início ou passadas para funções
CCXT_EXCHANGE_ID_ENV = os.environ.get("CCXT_EXCHANGE_ID", "binance")
CCXT_API_KEY_ENV = os.environ.get("CCXT_API_KEY")
CCXT_API_SECRET_ENV = os.environ.get("CCXT_API_SECRET")
CCXT_API_PASSWORD_ENV = os.environ.get("CCXT_API_PASSWORD")
CCXT_SANDBOX_MODE_ENV = os.environ.get("CCXT_SANDBOX_MODE", "false").lower() == "true"


async def get_ccxt_exchange(logger_instance) -> Optional[ccxt.Exchange]:
    """
    Inicializa e retorna uma instância da exchange ccxt.
    Retorna None se a configuração estiver ausente ou a inicialização falhar.
    """
    if not CCXT_API_KEY_ENV or not CCXT_API_SECRET_ENV:
        logger_instance.warning("CCXT_API_KEY ou CCXT_API_SECRET não configurados. Não é possível inicializar a exchange.")
        return None

    try:
        exchange_class = getattr(ccxt, CCXT_EXCHANGE_ID_ENV)
        config = {
            'apiKey': CCXT_API_KEY_ENV,
            'secret': CCXT_API_SECRET_ENV,
            'enableRateLimit': True,
        }
        if CCXT_API_PASSWORD_ENV:
            config['password'] = CCXT_API_PASSWORD_ENV
        
        exchange = exchange_class(config)

        if CCXT_SANDBOX_MODE_ENV:
            # Configurar sandbox/testnet
            
            # Método set_sandbox_mode (preferível)
            if hasattr(exchange, 'set_sandbox_mode') and callable(exchange.set_sandbox_mode):
                try:
                    exchange.set_sandbox_mode(True)
                    logger_instance.info(f"CCXT: Modo SANDBOX ativado para {CCXT_EXCHANGE_ID_ENV} via set_sandbox_mode.")
                except Exception as e_sandbox:
                    logger_instance.warning(f"CCXT: Tentativa de set_sandbox_mode para {CCXT_EXCHANGE_ID_ENV} falhou: {e_sandbox}. Tentando URL de teste.")
                    # Tentar fallback para URL de teste se set_sandbox_mode falhar
                    if 'test' in exchange.urls:
                        exchange.urls['api'] = exchange.urls['test']
                        logger_instance.info(f"CCXT: URLs alteradas para TESTNET para {CCXT_EXCHANGE_ID_ENV} (fallback).")
                    else:
                         logger_instance.warning(f"CCXT: Nenhuma URL de teste encontrada para {CCXT_EXCHANGE_ID_ENV} como fallback.")
            # Alterar URLs diretamente (se set_sandbox_mode não estiver disponível)
            elif 'test' in exchange.urls:
                exchange.urls['api'] = exchange.urls['test']
                logger_instance.info(f"CCXT: URLs alteradas para TESTNET para {CCXT_EXCHANGE_ID_ENV} (método direto).")
            else:
                logger_instance.warning(f"CCXT: Modo SANDBOX solicitado, mas não há método set_sandbox_mode nem URL de teste para {CCXT_EXCHANGE_ID_ENV}.")
        
        # Carregar mercados, útil para todas as operações
        # await exchange.load_markets()
        # logger_instance.info(f"CCXT: Mercados carregados para {CCXT_EXCHANGE_ID_ENV}.")
        return exchange

    except AttributeError:
        logger_instance.error(f"CCXT: Exchange ID '{CCXT_EXCHANGE_ID_ENV}' inválida ou não suportada.")
        return None
    except Exception as e:
        logger_instance.error(f"CCXT: Erro ao inicializar exchange {CCXT_EXCHANGE_ID_ENV}: {str(e)}", exc_info=True)
        return None


async def fetch_crypto_data(
    exchange: ccxt.Exchange, 
    pairs: List[str], 
    logger_instance
) -> Tuple[Dict[str, Any], bool, str]:
    """
    Busca dados de mercado (ticker, OHLCV) para uma lista de pares de cripto.
    Retorna: (dados_coletados, sucesso, mensagem_de_erro_detalhada)
    """
    collected_data: Dict[str, Any] = {}
    fetch_successful = True
    error_message = ""

    logger_instance.info(f"CCXT: Iniciando coleta de dados para pares: {pairs}")

    for pair_symbol in pairs:
        pair_data_key = pair_symbol.replace("/", "_")
        current_pair_data = {}
        try:
            if exchange.has['fetchTicker']:
                ticker = await exchange.fetch_ticker(pair_symbol)
                current_pair_data['ticker'] = {
                    'last': ticker.get('last'), 'bid': ticker.get('bid'), 'ask': ticker.get('ask'),
                    'volume': ticker.get('baseVolume'), 'timestamp': ticker.get('timestamp')
                }
            
            if exchange.has['fetchOHLCV']:
                # Parametrizar timeframe e limit
                ohlcv = await exchange.fetch_ohlcv(pair_symbol, timeframe='1h', limit=72)
                current_pair_data['ohlcv_1h'] = ohlcv
            
            # Adicionar mais tipos de dados necessários (order book, trades)
            
            collected_data[pair_data_key] = current_pair_data
            logger_instance.info(f"CCXT: Dados coletados para {pair_symbol}: Ticker OK, OHLCV OK (len: {len(ohlcv if 'ohlcv' in current_pair_data else [])})")

        except ccxt.NetworkError as e_net:
            logger_instance.error(f"CCXT: Erro de REDE ao buscar dados para {pair_symbol}: {e_net}")
            error_message += f"NetworkError for {pair_symbol}: {e_net}; "
            fetch_successful = False # Flha parcial ou total
            break # Interrompe a coleta para todos
        except ccxt.ExchangeError as e_exc:
            logger_instance.error(f"CCXT: Erro da EXCHANGE ao buscar dados para {pair_symbol}: {e_exc}")
            error_message += f"ExchangeError for {pair_symbol}: {e_exc}; "
            fetch_successful = False
            # Algumas ExchangeErrors podem ser específicas do par (par não existe),
            # Continuar para outros pares. Outras podem ser fatais (API key inválida).
            # Considerar falha e parar para este par.
            collected_data[pair_data_key] = {"error": str(e_exc)} # Registra o erro para o par
        except Exception as e_gen:
            logger_instance.error(f"CCXT: Erro GERAL ao buscar dados para {pair_symbol}: {e_gen}", exc_info=True)
            error_message += f"General error for {pair_symbol}: {e_gen}; "
            fetch_successful = False
            collected_data[pair_data_key] = {"error": str(e_gen)}

    if not fetch_successful:
        logger_instance.warning(f"CCXT: Coleta de dados de cripto encontrou erros. Detalhes: {error_message}")
    else:
        logger_instance.info("CCXT: Coleta de dados de cripto concluída com sucesso.")
        
    return collected_data, fetch_successful, error_message

# Adicione aqui funções para executar ordens (CREATE_ORDER_PLACEHOLDER)
# async def create_crypto_order(...) -> Tuple[Optional[Dict], bool, str]:
# async def fetch_order_status(...)

# Adicionar funções para fechar posições, buscar balanços.import pandas as pd
from typing import Optional

"""
Módulo com funções para cálculo de indicadores de análise técnica.
Todas as funções aqui operam sobre DataFrames ou Séries do pandas.
"""

def calculate_rsi(price_series: pd.Series, window: int = 14) -> pd.Series:
    """
    Calcula o Índice de Força Relativa (RSI) para uma série de preços.

    O RSI é um oscilador de momentum que mede a velocidade e a mudança
    dos movimentos de preços. O RSI oscila entre 0 e 100.

    Args:
        price_series (pd.Series): Uma série pandas contendo os preços de fechamento ('Close').
        window (int): O período de tempo para o cálculo do RSI (padrão: 14).

    Returns:
        pd.Series: Uma série pandas com os valores de RSI calculados.
    """
    if not isinstance(price_series, pd.Series):
        raise TypeError("O input 'price_series' deve ser uma Série do pandas.")

    # Calcula a diferença de preço em relação ao período anterior.
    delta = price_series.diff(1)

    # Separa os ganhos (diferenças positivas) das perdas (diferenças negativas).
    # .clip(lower=0) garante que todos os valores negativos se tornem 0.
    gain = delta.clip(lower=0)
    
    # .abs() para tornar os valores de perda positivos.
    loss = -delta.clip(upper=0)

    # Calcula a média móvel exponencial dos ganhos e perdas.
    # O método ewm (Exponentially Weighted Moving) é a forma correta e eficiente
    # de calcular a média suavizada usada no RSI.
    # 'com' é o "center of mass", com = window - 1 é equivalente a alpha = 1 / window.
    # 'adjust=False' usa a fórmula recursiva que é padrão para o RSI.
    avg_gain = gain.ewm(com=window - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=window - 1, adjust=False).mean()

    # Calcula a Força Relativa (RS)
    # Adicionamos um valor pequeno (epsilon) para evitar divisão por zero se avg_loss for 0.
    epsilon = 1e-10
    rs = avg_gain / (avg_loss + epsilon)

    # Calcula o RSI final.
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


# --- Bloco de teste para demonstrar o uso ---
if __name__ == '__main__':
    # Cria um DataFrame de exemplo com dados de preço
    data = {
        'Open': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 110, 112, 111, 113, 115, 114, 112, 110, 111, 113],
        'High': [103, 104, 103, 105, 106, 106, 108, 109, 108, 111, 112, 113, 112, 115, 116, 115, 113, 111, 112, 114],
        'Low': [99, 101, 100, 102, 104, 103, 105, 107, 106, 108, 109, 110, 110, 112, 113, 112, 110, 109, 110, 111],
        'Close': [102, 103, 102, 104, 105, 105, 107, 108, 107, 110, 111, 112, 111, 114, 115, 113, 111, 110, 111, 112],
        'Volume': [1000, 1200, 1100, 1300, 1400, 1350, 1500, 1600, 1550, 1700, 1800, 1900, 1850, 2000, 2100, 2050, 1950, 1800, 1900, 2000]
    }
    hist = pd.DataFrame(data)

    print("--- DataFrame Original (Últimas 5 linhas) ---")
    print(hist.tail())
    
    # Calcula RSI e SMA
    hist['rsi_14'] = calculate_rsi(hist['Close'], window=14)
    hist['sma_20'] = hist['Close'].rolling(20).mean()

    print("\n--- DataFrame com Indicadores (Últimas 5 linhas) ---")
    print(hist.tail())

    # Você verá NaNs no início, o que é normal, pois os indicadores precisam
    # de um histórico mínimo (a 'janela') para serem calculados.
    print("\n--- DataFrame com Indicadores (Completo) ---")
    print(hist)