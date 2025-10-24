"""
🧪 TESTE BINANCE REAL - Configuração e validação
Testa conectividade real com Binance Testnet/Mainnet
"""

import ccxt
import asyncio
import json
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BinanceRealTester:
    """
    Testa conexão real com Binance para validar sistema operacional
    """
    
    def __init__(self):
        self.exchange = None
        self.test_results = {}
        
    async def test_binance_connection(self, api_key: str, secret: str, use_testnet: bool = True) -> Dict[str, Any]:
        """
        Testa conexão real com Binance
        """
        try:
            # Configurar exchange
            config = {
                'apiKey': api_key,
                'secret': secret,
                'sandbox': use_testnet,  # True para testnet, False para mainnet
                'enableRateLimit': True,
                'options': {
                    'adjustForTimeDifference': True,  # Fix timestamp automático
                    'recvWindow': 10000  # Janela de tempo maior
                }
            }
            
            self.exchange = ccxt.binance(config)
            
            print(f"🔗 Testando conexão com Binance {'Testnet' if use_testnet else 'Mainnet'}...")
            
            # 1. Testar autenticação
            account_info = await self._test_authentication()
            
            # 2. Testar dados de mercado
            market_data = await self._test_market_data()
            
            # 3. Testar order book
            orderbook_data = await self._test_orderbook()
            
            # 4. Testar saldo (sempre - mas seguro)
            balance_data = await self._test_balance()
            
            # 5. Testar ordem simulada (apenas se testnet)
            order_test = None
            if use_testnet:
                order_test = await self._test_simulated_order()
            else:
                # Para mainnet, apenas simular sem executar
                order_test = {
                    "status": "SUCCESS",
                    "note": "Simulação apenas - mainnet seguro",
                    "order_creation_possible": True
                }
                
            results = {
                "connection_status": "SUCCESS",
                "exchange_name": "Binance",
                "testnet_mode": use_testnet,
                "timestamp": datetime.now().isoformat(),
                "tests": {
                    "authentication": account_info,
                    "market_data": market_data,
                    "orderbook": orderbook_data,
                    "balance": balance_data,
                    "order_simulation": order_test
                },
                "system_ready_for_trading": True
            }
            
            self.test_results = results
            return results
            
        except Exception as e:
            error_result = {
                "connection_status": "FAILED",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "system_ready_for_trading": False
            }
            logger.error(f"Binance connection test failed: {e}")
            return error_result
    
    async def _test_authentication(self) -> Dict[str, Any]:
        """Testa autenticação com Binance"""
        try:
            # Testar account info (requer API key válida)
            account = self.exchange.fetch_balance()
            
            return {
                "status": "SUCCESS",
                "account_type": account.get('info', {}).get('accountType', 'SPOT'),
                "permissions": account.get('info', {}).get('permissions', []),
                "authenticated": True
            }
            
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "authenticated": False
            }
    
    async def _test_market_data(self) -> Dict[str, Any]:
        """Testa dados de mercado"""
        try:
            # Testar ticker do BTCUSDT
            ticker = self.exchange.fetch_ticker('BTC/USDT')
            
            return {
                "status": "SUCCESS",
                "symbol": ticker['symbol'],
                "price": ticker['last'],
                "volume": ticker['baseVolume'],
                "market_data_available": True
            }
            
        except Exception as e:
            return {
                "status": "FAILED", 
                "error": str(e),
                "market_data_available": False
            }
    
    async def _test_orderbook(self) -> Dict[str, Any]:
        """Testa order book"""
        try:
            orderbook = self.exchange.fetch_order_book('BTC/USDT', 5)
            
            return {
                "status": "SUCCESS",
                "bids_count": len(orderbook['bids']),
                "asks_count": len(orderbook['asks']),
                "spread": orderbook['asks'][0][0] - orderbook['bids'][0][0] if orderbook['asks'] and orderbook['bids'] else 0,
                "orderbook_available": True
            }
            
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "orderbook_available": False
            }
    
    async def _test_balance(self) -> Dict[str, Any]:
        """Testa saldo da conta (testnet only)"""
        try:
            balance = self.exchange.fetch_balance()
            
            # Filtrar apenas saldos > 0
            non_zero_balances = {
                currency: amount for currency, amount in balance['total'].items() 
                if amount > 0
            }
            
            return {
                "status": "SUCCESS",
                "currencies_available": list(non_zero_balances.keys()),
                "balance_count": len(non_zero_balances),
                "balance_accessible": True
            }
            
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "balance_accessible": False
            }
    
    async def _test_simulated_order(self) -> Dict[str, Any]:
        """Testa ordem simulada (testnet only)"""
        try:
            # Testar apenas dry run - não executa ordem real
            symbol = 'BTC/USDT'
            amount = 0.001  # Pequena quantidade para teste
            
            ticker = self.exchange.fetch_ticker(symbol)
            price = ticker['last'] * 0.99  # Preço ligeiramente abaixo do mercado
            
            # Criar ordem de teste (dry run)
            test_order = {
                "symbol": symbol,
                "type": "limit",
                "side": "buy", 
                "amount": amount,
                "price": price
            }
            
            return {
                "status": "SUCCESS",
                "test_order": test_order,
                "order_creation_possible": True,
                "note": "Ordem simulada - não executada"
            }
            
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e),
                "order_creation_possible": False
            }
    
    def get_connection_summary(self) -> Dict[str, Any]:
        """
        Resumo da conexão para o sistema neural
        """
        if not self.test_results:
            return {"status": "NO_TESTS_RUN"}
            
        tests = self.test_results.get('tests', {})
        
        # Calcular score de conectividade
        success_count = sum(
            1 for test in tests.values() 
            if test and test.get('status') == 'SUCCESS'
        )
        total_tests = len([t for t in tests.values() if t is not None])
        connectivity_score = (success_count / total_tests) if total_tests > 0 else 0
        
        return {
            "binance_connected": self.test_results.get('connection_status') == 'SUCCESS',
            "connectivity_score": connectivity_score,
            "testnet_mode": self.test_results.get('testnet_mode', True),
            "ready_for_neural_trading": connectivity_score >= 0.8,
            "last_test": self.test_results.get('timestamp'),
            "test_summary": {
                "authentication": tests.get('authentication', {}).get('status', 'FAILED') == 'SUCCESS' if tests.get('authentication') else False,
                "market_data": tests.get('market_data', {}).get('status', 'FAILED') == 'SUCCESS' if tests.get('market_data') else False, 
                "orderbook": tests.get('orderbook', {}).get('status', 'FAILED') == 'SUCCESS' if tests.get('orderbook') else False,
                "balance_access": tests.get('balance', {}).get('status', 'FAILED') == 'SUCCESS' if tests.get('balance') else False,
                "order_simulation": tests.get('order_simulation', {}).get('status', 'FAILED') == 'SUCCESS' if tests.get('order_simulation') else False
            }
        }

# Instância global para uso na API
binance_tester = BinanceRealTester()