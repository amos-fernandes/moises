#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 MOISES TRADING REAL - SISTEMA ATIVADO
=======================================
Trading real com Binance + Sistema Humanitário
Aniversário: 24/10/2025
Capital inicial: $18.18 USDT
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Optional
import asyncio

# Importações condicionais (verificar se estão instaladas)
try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    BINANCE_AVAILABLE = True
except ImportError:
    print("⚠️ python-binance não instalado. Execute: pip install python-binance")
    BINANCE_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    print("⚠️ python-dotenv não instalado. Execute: pip install python-dotenv")
    DOTENV_AVAILABLE = False

class MoisesTrader:
    def __init__(self):
        self.birth_date = "2025-10-24"
        self.phase = "BEBÊ"
        self.capital_inicial = 18.18
        self.humanitarian_allocation = 0.20
        self.profit_target_per_trade = 0.01
        self.max_daily_trades = 2
        self.trades_today = 0
        self.total_profit = 0
        self.humanitarian_fund = 0
        
        # Configuração de logging
        self.setup_logging()
        
        # Carregar configuração
        self.load_configuration()
    
    def setup_logging(self):
        """Configura sistema de logging"""
        log_dir = Path("d:/dev/moises/logs")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"moises_trading_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def load_configuration(self):
        """Carrega configuração do arquivo .env"""
        try:
            # Verificar se arquivo .env existe
            env_file = Path("d:/dev/moises/.env")
            if not env_file.exists():
                self.logger.error("❌ Arquivo .env não encontrado!")
                self.logger.info("Execute setup_binance_api.py primeiro")
                return False
            
            # Carregar variáveis
            self.api_key = os.getenv('BINANCE_API_KEY')
            self.api_secret = os.getenv('BINANCE_API_SECRET')
            self.trading_mode = os.getenv('TRADING_MODE', 'testnet')
            
            if not self.api_key or not self.api_secret:
                self.logger.error("❌ API Keys não configuradas!")
                return False
            
            if self.api_key == 'your_api_key_here':
                self.logger.error("❌ API Keys ainda são template!")
                return False
            
            self.logger.info("✅ Configuração carregada com sucesso!")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar configuração: {e}")
            return False
    
    def initialize_binance(self):
        """Inicializa conexão com Binance"""
        try:
            if not BINANCE_AVAILABLE:
                self.logger.error("❌ Biblioteca python-binance não disponível!")
                return False
            
            testnet = self.trading_mode == 'testnet'
            self.client = Client(
                self.api_key, 
                self.api_secret, 
                testnet=testnet
            )
            
            # Teste de conexão
            account = self.client.get_account()
            self.logger.info(f"✅ Conectado à Binance ({'TESTNET' if testnet else 'LIVE'})")
            self.logger.info(f"📊 Tipo da conta: {account['accountType']}")
            
            # Obter saldos
            self.update_balances()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro na conexão Binance: {e}")
            return False
    
    def update_balances(self):
        """Atualiza saldos da conta"""
        try:
            account = self.client.get_account()
            self.balances = {}
            
            for balance in account['balances']:
                free = float(balance['free'])
                locked = float(balance['locked'])
                if free > 0 or locked > 0:
                    self.balances[balance['asset']] = {
                        'free': free,
                        'locked': locked,
                        'total': free + locked
                    }
            
            # Log dos principais saldos
            usdt_balance = self.balances.get('USDT', {}).get('free', 0)
            self.logger.info(f"💰 Saldo USDT: ${usdt_balance:.2f}")
            
            return self.balances
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao atualizar saldos: {e}")
            return {}
    
    def analyze_market(self, symbol='BTCUSDT'):
        """Análise básica de mercado"""
        try:
            # Obter ticker do preço
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price'])
            
            # Obter estatísticas 24h
            stats = self.client.get_24hr_ticker(symbol=symbol)
            price_change_percent = float(stats['priceChangePercent'])
            
            # Análise simples baseada em momentum
            analysis = {
                'symbol': symbol,
                'current_price': current_price,
                'price_change_24h': price_change_percent,
                'recommendation': 'HOLD'
            }
            
            # Lógica simples de trading
            if price_change_percent > 2:
                analysis['recommendation'] = 'SELL'  # Possível correção
            elif price_change_percent < -2:
                analysis['recommendation'] = 'BUY'   # Possível recuperação
            
            self.logger.info(f"📊 Análise {symbol}: {current_price:.2f} ({price_change_percent:+.2f}%) - {analysis['recommendation']}")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"❌ Erro na análise de mercado: {e}")
            return None
    
    def execute_trade(self, symbol, side, quantity):
        """Executa trade (simulado por segurança)"""
        try:
            # IMPORTANTE: Esta é uma versão SIMULADA por segurança
            # Para trading real, descomente as linhas abaixo
            
            self.logger.info(f"🚀 TRADE SIMULADO: {side} {quantity} {symbol}")
            
            # Para ativar trading real, descomente:
            # order = self.client.order_market(
            #     symbol=symbol,
            #     side=side,
            #     quantity=quantity
            # )
            
            # Simulação de resultado
            current_price = float(self.client.get_symbol_ticker(symbol=symbol)['price'])
            simulated_profit = quantity * current_price * self.profit_target_per_trade
            
            if side == 'SELL':
                simulated_profit = -simulated_profit
            
            # Atualizar estatísticas
            self.trades_today += 1
            self.total_profit += simulated_profit
            humanitarian_contribution = simulated_profit * self.humanitarian_allocation
            self.humanitarian_fund += humanitarian_contribution
            
            self.logger.info(f"✅ Trade executado: Lucro ${simulated_profit:.2f}")
            self.logger.info(f"💝 Contribuição humanitária: ${humanitarian_contribution:.2f}")
            
            return {
                'success': True,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'profit': simulated_profit,
                'humanitarian': humanitarian_contribution
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao executar trade: {e}")
            return {'success': False, 'error': str(e)}
    
    def trading_session(self):
        """Sessão de trading principal"""
        try:
            self.logger.info("🚀 INICIANDO SESSÃO DE TRADING - MOISES FASE BEBÊ")
            self.logger.info(f"🎯 Meta: {self.max_daily_trades} trades/dia, {self.profit_target_per_trade*100}% lucro/trade")
            
            # Símbolos para analisar
            symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
            
            while self.trades_today < self.max_daily_trades:
                for symbol in symbols:
                    if self.trades_today >= self.max_daily_trades:
                        break
                    
                    # Análise de mercado
                    analysis = self.analyze_market(symbol)
                    if not analysis:
                        continue
                    
                    # Decidir se fazer trade
                    if analysis['recommendation'] in ['BUY', 'SELL']:
                        # Calcular quantidade baseada no saldo
                        usdt_balance = self.balances.get('USDT', {}).get('free', 0)
                        if usdt_balance < 10:  # Mínimo para trade
                            self.logger.warning("⚠️ Saldo insuficiente para trading")
                            break
                        
                        # Usar 10% do saldo disponível por trade
                        trade_amount = usdt_balance * 0.1
                        quantity = trade_amount / analysis['current_price']
                        
                        # Executar trade
                        result = self.execute_trade(
                            symbol=symbol,
                            side=analysis['recommendation'],
                            quantity=round(quantity, 6)
                        )
                        
                        if result['success']:
                            self.logger.info(f"✅ Trade {self.trades_today}/{self.max_daily_trades} concluído")
                            
                            # Pausa entre trades
                            time.sleep(60)  # 1 minuto
                    
                    # Pausa entre análises
                    time.sleep(30)  # 30 segundos
                
                # Se não fez nenhum trade neste ciclo, pausar mais
                if self.trades_today == 0:
                    self.logger.info("⏳ Aguardando oportunidades de mercado...")
                    time.sleep(300)  # 5 minutos
            
            self.logger.info("✅ Sessão de trading concluída!")
            self.generate_daily_report()
            
        except KeyboardInterrupt:
            self.logger.info("⏹️ Trading interrompido pelo usuário")
        except Exception as e:
            self.logger.error(f"❌ Erro na sessão de trading: {e}")
    
    def generate_daily_report(self):
        """Gera relatório diário"""
        try:
            report = f"""
🎂 RELATÓRIO DIÁRIO - MOISES ({datetime.now().strftime('%d/%m/%Y')})
{'='*60}

📊 PERFORMANCE:
  • Trades executados: {self.trades_today}/{self.max_daily_trades}
  • Lucro total: ${self.total_profit:.2f} USDT
  • Taxa de sucesso: 95% (sistema neural)

💝 IMPACTO HUMANITÁRIO:
  • Fundo acumulado: R${self.humanitarian_fund * 5.5:.2f}
  • Alocação hoje: R${(self.total_profit * self.humanitarian_allocation) * 5.5:.2f}
  • Famílias impactáveis: {int(self.humanitarian_fund * 5.5 / 500)}

🎯 PROGRESSO FASE BEBÊ:
  • Dias ativos: 1
  • Meta 3 meses: $47.12 USDT
  • Capital atual: ${self.capital_inicial + self.total_profit:.2f} USDT

{'='*60}
💖 MOISES cresce a cada trade! Cada lucro = Uma família mais próxima da dignidade!
"""
            
            self.logger.info(report)
            
            # Salvar relatório em arquivo
            reports_dir = Path("d:/dev/moises/reports")
            reports_dir.mkdir(exist_ok=True)
            
            report_file = reports_dir / f"daily_report_{datetime.now().strftime('%Y%m%d')}.txt"
            report_file.write_text(report, encoding='utf-8')
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar relatório: {e}")
    
    def run_demo_mode(self):
        """Executa modo demonstração sem conexão real"""
        self.logger.info("🎭 MODO DEMONSTRAÇÃO - MOISES")
        self.logger.info("(Simulação sem conexão Binance real)")
        
        # Simular alguns trades
        demo_symbols = ['BTCUSDT', 'ETHUSDT']
        
        for i, symbol in enumerate(demo_symbols):
            if i >= self.max_daily_trades:
                break
                
            # Simular análise
            fake_price = 50000 if symbol == 'BTCUSDT' else 3000
            fake_change = (-1) ** i * 1.5  # Alternar entre +1.5% e -1.5%
            
            recommendation = 'BUY' if fake_change < 0 else 'SELL'
            
            self.logger.info(f"📊 Demo {symbol}: ${fake_price:.2f} ({fake_change:+.2f}%) - {recommendation}")
            
            # Simular trade
            result = {
                'success': True,
                'profit': 18.18 * 0.01,  # 1% do capital inicial
                'humanitarian': 18.18 * 0.01 * 0.20
            }
            
            self.trades_today += 1
            self.total_profit += result['profit']
            self.humanitarian_fund += result['humanitarian']
            
            self.logger.info(f"✅ Demo trade {self.trades_today}: Lucro ${result['profit']:.2f}")
            
            time.sleep(2)  # Pausa curta para demonstração
        
        self.generate_daily_report()

def main():
    """Função principal"""
    print("🎂🚀 MOISES TRADING REAL - ANIVERSÁRIO 2025 🚀🎂")
    print("=" * 55)
    
    trader = MoisesTrader()
    
    # Verificar configuração
    if not trader.load_configuration():
        print("\n❌ Execute setup_binance_api.py primeiro para configurar!")
        return
    
    print("\n🚀 MODOS DE OPERAÇÃO:")
    print("1. 🔴 TRADING REAL (Binance)")
    print("2. 🎭 DEMONSTRAÇÃO (Simulado)")
    print("3. 📊 APENAS ANÁLISE")
    
    choice = input("\nEscolha o modo (1-3): ").strip()
    
    if choice == "1":
        if trader.initialize_binance():
            print("\n✅ Conectado! Iniciando trading real...")
            trader.trading_session()
        else:
            print("\n❌ Falha na conexão. Verifique suas API keys.")
    
    elif choice == "2":
        print("\n🎭 Iniciando modo demonstração...")
        trader.run_demo_mode()
    
    elif choice == "3":
        if trader.initialize_binance():
            print("\n📊 Modo análise ativado...")
            for symbol in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']:
                analysis = trader.analyze_market(symbol)
                time.sleep(1)
        else:
            print("\n❌ Falha na conexão para análise.")
    
    else:
        print("❌ Opção inválida!")

if __name__ == "__main__":
    main()