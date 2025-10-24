# src/utils/market_data_utils.py

import aiohttp
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def fetch_btc_dominance() -> float:
    """
    Busca a dominância de mercado do Bitcoin (BTC) da API pública da CoinGecko.
    """
    url = "https://api.coingecko.com/api/v3/global"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()
                btc_dominance = data.get("data", {}).get("market_cap_percentage", {}).get("btc")
                
                if btc_dominance is not None:
                    logger.info(f"Dominância do BTC obtida com sucesso: {btc_dominance:.2f}%")
                    return float(btc_dominance)
                else:
                    logger.error("Campo de dominância do BTC não encontrado na resposta da API.")
                    return 0.0
                    
    except Exception as e:
        logger.error(f"Falha ao buscar a dominância do BTC da CoinGecko: {e}", exc_info=True)
        return 0.0

async def get_market_sentiment() -> Dict[str, Any]:
    """
    Busca o Índice de Medo e Ganância (Fear & Greed Index) da API alternative.me.
    """
    url = "https://api.alternative.me/fng/?limit=1"
    default_sentiment = {'value': 50, 'classification': 'Unknown'}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()
                
                if 'data' in data and len(data['data']) > 0:
                    sentiment_data = data['data'][0]
                    result = {
                        'value': int(sentiment_data.get('value', 50)),
                        'classification': sentiment_data.get('value_classification', 'Unknown')
                    }
                    logger.info(f"Sentimento de mercado obtido: {result['classification']} ({result['value']})")
                    return result
                else:
                    logger.warning("Resposta da API de sentimento não continha dados válidos.")
                    return default_sentiment

    except Exception as e:
        logger.error(f"Falha ao buscar o Índice de Medo e Ganância: {e}", exc_info=True)
        return default_sentiment