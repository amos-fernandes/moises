"""
Sistema de Trading Real com Binance - Equilibrada_Pro
Configurado para operações reais com conversão BRL/USD
"""

import os
import sys
from pathlib import Path
import ccxt
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Adiciona paths
repo_root = str(Path(__file__).resolve().parents[1])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.trading.production_system import ProductionTradingSystem


class BinanceRealTrading:
    """Sistema de trading real na Binance com Equilibrada_Pro"""
    
    def __init__(self):
        self.trading_system = ProductionTradingSystem()
        
        # Configurações da Binance
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY')
        self.testnet = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
        
        # Configurações de trading
        self.trading_mode = os.getenv('TRADING_MODE', 'REAL')
        self.initial_balance_brl = float(os.getenv('INITIAL_BALANCE_BRL', 1000.0))
        self.max_position_size = float(os.getenv('MAX_POSITION_SIZE', 0.15))
        
        # Validações
        if not self.api_key or not self.secret_key:
            raise ValueError("❌ BINANCE_API_KEY e BINANCE_SECRET_KEY devem estar configuradas no .env")
        
        # Exchange
        self.exchange = None
        self.initialized = False
        
        print(f"🚀 Sistema inicializado:")
        print(f"   Mode: {self.trading_mode}")
        print(f"   Testnet: {self.testnet}")
        print(f"   Balance BRL: R$ {self.initial_balance_brl:,.2f}")
    
    async def initialize(self):
        """Inicializa conexão com Binance"""
        try:
            # Configura exchange
            exchange_config = {
                'apiKey': self.api_key,
                'secret': self.secret_key,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',  # Trading spot
                }
            }
            
            # Usa testnet se configurado
            if self.testnet:
                exchange_config['sandbox'] = True
                print("⚠️ MODO TESTNET ATIVO")
            else:
                print("🔴 MODO REAL ATIVO - CUIDADO!")
            
            self.exchange = ccxt.binance(exchange_config)
            
            # Testa conexão
            balance = await self.exchange.fetch_balance()
            print(f"✅ Conectado à Binance")
            print(f"💰 USDT disponível: ${balance.get('USDT', {}).get('free', 0):.2f}")
            
            # Verifica se tem BRL para conversão
            brl_balance = balance.get('BRL', {}).get('free', 0)
            if brl_balance > 0:
                print(f"💵 BRL disponível: R$ {brl_balance:.2f}")
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"❌ Erro ao conectar Binance: {e}")
            return False
    
    async def convert_brl_to_usd(self, amount_brl: float) -> float:
        """Converte BRL para USD via USDT"""
        try:
            if not self.initialized:
                await self.initialize()
            
            print(f"💱 Convertendo R$ {amount_brl:.2f} para USD...")
            
            # Busca taxa BRL/USDT
            ticker = await self.exchange.fetch_ticker('BRL/USDT')
            brl_usdt_rate = ticker['last']
            
            # Calcula quantidade de USDT
            usdt_amount = amount_brl / brl_usdt_rate
            
            print(f"📊 Taxa BRL/USDT: {brl_usdt_rate:.4f}")
            print(f"💰 Resultado: {usdt_amount:.2f} USDT ≈ ${usdt_amount:.2f}")
            
            return usdt_amount
            
        except Exception as e:
            print(f"❌ Erro na conversão BRL/USD: {e}")
            # Usa taxa aproximada se API falhar
            approximate_rate = 5.0  # Aproximadamente R$5.00 = $1.00
            return amount_brl / approximate_rate
    
    async def execute_real_trade(self, 
                               symbol: str, 
                               side: str, 
                               amount_usd: float,
                               signal_confidence: float) -> Dict[str, Any]:
        """Executa trade real na Binance"""
        try:
            if not self.initialized:
                await self.initialize()
            
            print(f"🎯 Executando trade real:")
            print(f"   Par: {symbol}")
            print(f"   Lado: {side}")
            print(f"   Valor: ${amount_usd:.2f}")
            print(f"   Confiança: {signal_confidence:.2%}")
            
            # Busca preço atual
            ticker = await self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # Calcula quantidade
            if side.upper() == 'BUY':
                quantity = amount_usd / current_price
            else:
                # Para venda, usa saldo disponível do ativo
                balance = await self.exchange.fetch_balance()
                asset = symbol.split('/')[0]  # Ex: ETH de ETH/USDT
                available = balance.get(asset, {}).get('free', 0)
                quantity = min(available, amount_usd / current_price)
            
            # Arredonda para precisão da exchange
            market = await self.exchange.fetch_market(symbol)
            precision = market['precision']['amount']
            quantity = round(quantity, precision)
            
            if quantity <= 0:
                return {
                    'success': False,
                    'error': 'Quantidade insuficiente para trade',
                    'quantity': quantity
                }
            
            # Executa ordem de mercado
            print(f"📈 Enviando ordem: {side} {quantity} {symbol} @ ${current_price:.2f}")
            
            order = await self.exchange.create_market_order(
                symbol=symbol,
                side=side.lower(),
                amount=quantity,
                price=None  # Ordem de mercado
            )
            
            print(f"✅ Ordem executada! ID: {order['id']}")
            
            # Calcula custo/receita
            filled_amount = order.get('filled', quantity)
            cost = filled_amount * current_price
            
            return {
                'success': True,
                'order_id': order['id'],
                'symbol': symbol,
                'side': side,
                'quantity': filled_amount,
                'price': current_price,
                'cost': cost,
                'timestamp': datetime.now().isoformat(),
                'confidence': signal_confidence
            }
            
        except Exception as e:
            print(f"❌ Erro ao executar trade: {e}")
            return {
                'success': False,
                'error': str(e),
                'symbol': symbol,
                'side': side,
                'amount_usd': amount_usd
            }
    
    async def run_equilibrada_strategy_real(self, 
                                          initial_amount_brl: float = None) -> Dict[str, Any]:
        """Executa estratégia Equilibrada_Pro com dinheiro real"""
        
        if initial_amount_brl is None:
            initial_amount_brl = self.initial_balance_brl
        
        print(f"\n🚀 INICIANDO TRADING REAL EQUILIBRADA_PRO")
        print(f"💰 Capital inicial: R$ {initial_amount_brl:.2f}")
        print(f"⚠️  ATENÇÃO: OPERAÇÕES COM DINHEIRO REAL!")
        
        results = {
            'start_time': datetime.now().isoformat(),
            'initial_amount_brl': initial_amount_brl,
            'trades': [],
            'total_pnl_usd': 0.0,
            'success': False
        }
        
        try:
            # Converte BRL para USD
            amount_usd = await self.convert_brl_to_usd(initial_amount_brl)
            results['initial_amount_usd'] = amount_usd
            
            # Ativos para análise
            symbols = ['ETH/USDT', 'BTC/USDT', 'SOL/USDT']
            
            for symbol in symbols:
                try:
                    print(f"\n📊 Analisando {symbol}...")
                    
                    # Busca dados OHLCV
                    ohlcv = await self.exchange.fetch_ohlcv(
                        symbol, 
                        timeframe='1h', 
                        limit=200
                    )
                    
                    # Converte para DataFrame
                    df = pd.DataFrame(
                        ohlcv, 
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    )
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    # Calcula indicadores
                    df_with_indicators = self.trading_system.calculate_indicators(df)
                    
                    # Gera sinal
                    last_index = len(df_with_indicators) - 1
                    signal, confidence, reason = self.trading_system.generate_signal(
                        df_with_indicators, 
                        last_index
                    )
                    
                    print(f"🎯 Sinal: {signal} | Confiança: {confidence:.2%} | {reason}")
                    
                    # Executa trade se sinal forte
                    if abs(signal) == 1 and confidence >= 0.6:
                        
                        # Determina valor do trade
                        trade_amount = amount_usd * self.max_position_size
                        
                        # Determina lado
                        side = 'BUY' if signal == 1 else 'SELL'
                        
                        # Executa trade real
                        trade_result = await self.execute_real_trade(
                            symbol, 
                            side, 
                            trade_amount, 
                            confidence
                        )
                        
                        results['trades'].append(trade_result)
                        
                        if trade_result['success']:
                            print(f"✅ Trade executado com sucesso!")
                        else:
                            print(f"❌ Falha no trade: {trade_result.get('error')}")
                    
                    else:
                        print(f"⏸️ Sinal insuficiente - aguardando melhor oportunidade")
                
                except Exception as e:
                    print(f"❌ Erro ao analisar {symbol}: {e}")
                    continue
            
            # Calcula resultado final
            successful_trades = [t for t in results['trades'] if t.get('success')]
            total_cost = sum(t.get('cost', 0) for t in successful_trades if t.get('side') == 'BUY')
            total_revenue = sum(t.get('cost', 0) for t in successful_trades if t.get('side') == 'SELL')
            
            results['total_pnl_usd'] = total_revenue - total_cost
            results['success'] = True
            results['end_time'] = datetime.now().isoformat()
            
            print(f"\n🏁 RESULTADO FINAL:")
            print(f"💹 Trades executados: {len(successful_trades)}")
            print(f"💰 P&L USD: ${results['total_pnl_usd']:+.2f}")
            
            return results
            
        except Exception as e:
            print(f"❌ Erro crítico na estratégia: {e}")
            results['error'] = str(e)
            return results
        
        finally:
            if self.exchange:
                await self.exchange.close()


async def main():
    """Função principal para testes"""
    
    print("🔥 SISTEMA DE TRADING REAL EQUILIBRADA_PRO")
    print("=" * 50)
    
    # Cria instância do sistema
    trading_system = BinanceRealTrading()
    
    # Inicializa
    if await trading_system.initialize():
        print("✅ Sistema inicializado com sucesso")
        
        # Pergunta confirmação para trading real
        if trading_system.trading_mode == 'REAL' and not trading_system.testnet:
            print("\n⚠️  ATENÇÃO: VOCÊ ESTÁ PRESTES A FAZER TRADES REAIS!")
            print("💰 Isso usará seu dinheiro real na Binance")
            confirm = input("Digite 'CONFIRMO' para prosseguir: ")
            
            if confirm != 'CONFIRMO':
                print("❌ Operação cancelada pelo usuário")
                return
        
        # Executa estratégia
        result = await trading_system.run_equilibrada_strategy_real()
        
        print(f"\n📊 RESULTADO COMPLETO:")
        print(f"🎯 Sucesso: {result['success']}")
        print(f"💰 P&L: ${result.get('total_pnl_usd', 0):+.2f}")
        print(f"📈 Trades: {len(result.get('trades', []))}")
    
    else:
        print("❌ Falha na inicialização")


if __name__ == "__main__":
    asyncio.run(main())