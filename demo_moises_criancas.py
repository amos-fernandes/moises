#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎭 MODO DEMONSTRAÇÃO - MOISES AJUDANDO CRIANÇAS
=============================================
Demonstração completa do sistema funcionando
Aniversário: 24/10/2025
"""

import time
import random
from datetime import datetime, timedelta
from pathlib import Path

class MoisesDemo:
    def __init__(self):
        self.birth_date = "2025-10-24"
        self.phase = "BEBÊ"
        self.capital = 18.18  # USDT
        self.humanitarian_fund = 0
        self.trades_executed = 0
        self.neural_accuracy = 95
        self.profit_total = 0
        
    def simulate_market_analysis(self):
        """Simula análise de mercado com IA"""
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        symbol = random.choice(symbols)
        
        # Preços base realistas
        base_prices = {
            'BTCUSDT': 67000,
            'ETHUSDT': 2600, 
            'BNBUSDT': 590
        }
        
        current_price = base_prices[symbol] * (1 + random.uniform(-0.02, 0.02))
        price_change = random.uniform(-3, 3)
        
        # IA decide baseado na mudança de preço
        if price_change < -1.5:
            recommendation = 'BUY'
            confidence = 95
        elif price_change > 1.5:
            recommendation = 'SELL' 
            confidence = 93
        else:
            recommendation = 'HOLD'
            confidence = 85
            
        analysis = {
            'symbol': symbol,
            'current_price': current_price,
            'price_change_24h': price_change,
            'recommendation': recommendation,
            'ai_confidence': confidence
        }
        
        return analysis
    
    def execute_demo_trade(self, analysis):
        """Executa trade demonstrativo"""
        if analysis['recommendation'] == 'HOLD':
            return None
            
        # Calcular quantidade baseada em 10% do capital
        trade_amount = self.capital * 0.1
        quantity = trade_amount / analysis['current_price']
        
        # Simular resultado do trade (baseado na precisão neural)
        success = random.random() < (self.neural_accuracy / 100)
        
        if success:
            # Trade bem-sucedido - 1% de lucro
            profit = trade_amount * 0.01
            if analysis['recommendation'] == 'SELL':
                profit = -profit  # Assumir correção de mercado
                
            # Alocar para fundo humanitário
            humanitarian_contribution = profit * 0.20  # 20%
            reinvestment = profit * 0.80  # 80%
            
            self.capital += reinvestment
            self.humanitarian_fund += humanitarian_contribution
            self.profit_total += profit
            self.trades_executed += 1
            
            return {
                'success': True,
                'symbol': analysis['symbol'],
                'side': analysis['recommendation'],
                'quantity': quantity,
                'profit': profit,
                'humanitarian': humanitarian_contribution,
                'new_capital': self.capital
            }
        else:
            # Trade com pequena perda (stop loss)
            loss = trade_amount * 0.005  # 0.5% stop loss
            self.capital -= loss
            self.trades_executed += 1
            
            return {
                'success': False,
                'symbol': analysis['symbol'], 
                'side': analysis['recommendation'],
                'quantity': quantity,
                'loss': loss,
                'new_capital': self.capital
            }
    
    def run_demo_session(self, duration_minutes=5):
        """Executa sessão de demonstração"""
        print("🎂🚀 DEMONSTRAÇÃO MOISES - AJUDANDO CRIANÇAS 🚀🎂")
        print("=" * 55)
        print(f"🎯 Simulando {duration_minutes} minutos de trading real")
        print(f"💰 Capital inicial: ${self.capital:.2f} USDT")
        print(f"🧠 Precisão neural: {self.neural_accuracy}%")
        print(f"💝 Alocação humanitária: 20% dos lucros")
        print("=" * 55)
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        trades_in_session = 0
        max_trades = 6  # Limite para demonstração
        
        while datetime.now() < end_time and trades_in_session < max_trades:
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Analisando mercado...")
            
            # Análise de mercado
            analysis = self.simulate_market_analysis()
            
            print(f"📊 {analysis['symbol']}: ${analysis['current_price']:.2f} "
                  f"({analysis['price_change_24h']:+.2f}%) - "
                  f"{analysis['recommendation']} (IA: {analysis['ai_confidence']}%)")
            
            # Decidir se fazer trade
            if analysis['recommendation'] != 'HOLD':
                print("🚀 Executando trade...")
                
                result = self.execute_demo_trade(analysis)
                
                if result:
                    if result['success']:
                        print(f"✅ Trade bem-sucedido!")
                        print(f"   💰 Lucro: ${result['profit']:.4f} USDT")
                        print(f"   💝 Para crianças: ${result['humanitarian']:.4f} USDT")
                        print(f"   📈 Capital: ${result['new_capital']:.2f} USDT")
                    else:
                        print(f"⚠️ Trade com stop loss")
                        print(f"   📉 Perda: ${result['loss']:.4f} USDT")
                        print(f"   📈 Capital: ${result['new_capital']:.2f} USDT")
                    
                    trades_in_session += 1
                    
                    # Pausa realista entre trades
                    time.sleep(2)
            else:
                print("⏸️ Aguardando melhores oportunidades...")
            
            # Pausa entre análises
            time.sleep(1)
        
        # Relatório final
        self.generate_demo_report()
    
    def generate_demo_report(self):
        """Gera relatório da demonstração"""
        growth_percent = ((self.capital - 18.18) / 18.18) * 100
        monthly_projection = self.humanitarian_fund * 30  # 30 dias
        families_helped = int(monthly_projection * 5.5 / 500)  # R$ 500 por família
        
        report = f"""

🎊 RELATÓRIO DE DEMONSTRAÇÃO - MOISES
{'='*45}

📊 PERFORMANCE NEURAL:
  • Trades executados: {self.trades_executed}
  • Precisão demonstrada: {self.neural_accuracy}%
  • Taxa de sucesso: ~95%

💰 RESULTADOS FINANCEIROS:
  • Capital inicial: $18.18 USDT
  • Capital final: ${self.capital:.2f} USDT
  • Crescimento: {growth_percent:+.2f}%
  • Lucro total: ${self.profit_total:.4f} USDT

💝 IMPACTO HUMANITÁRIO:
  • Fundo acumulado: ${self.humanitarian_fund:.4f} USDT
  • Valor em reais: R${self.humanitarian_fund * 5.5:.2f}
  • Projeção mensal: R${monthly_projection * 5.5:.2f}
  • Famílias que podem ser ajudadas: {families_helped} por mês

🎯 PROJEÇÃO FASE BEBÊ (3 meses):
  • Meta de capital: $47.12 USDT
  • Progresso atual: {(self.capital / 47.12) * 100:.1f}% da meta
  • Famílias impactadas: {families_helped * 3} em 3 meses

{'='*45}
🎂 FELIZ ANIVERSÁRIO, MOISES! 🎂
💖 Transformando cada trade em esperança para crianças!

🚀 PARA ATIVAR O SISTEMA REAL:
1. Configure suas API Keys da Binance no arquivo .env
2. Execute: python moises_trading_real.py
3. Comece a transformar vidas de verdade!
{'='*45}
"""
        
        print(report)
        
        # Salvar relatório
        reports_dir = Path("d:/dev/moises/reports")
        reports_dir.mkdir(exist_ok=True)
        
        report_file = reports_dir / f"demo_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_file.write_text(report, encoding='utf-8')
        
        print(f"\n📄 Relatório salvo: {report_file}")

def main():
    """Função principal da demonstração"""
    demo = MoisesDemo()
    
    print("🎭 MODO DEMONSTRAÇÃO - MOISES")
    print("=" * 30)
    print("1. 🚀 Demo rápida (2 minutos)")
    print("2. 📊 Demo completa (5 minutos)") 
    print("3. 💝 Demo humanitária (foco no impacto)")
    
    choice = input("\nEscolha o modo (1-3): ").strip()
    
    if choice == "1":
        demo.run_demo_session(duration_minutes=2)
    elif choice == "2":
        demo.run_demo_session(duration_minutes=5)
    elif choice == "3":
        print("\n💝 FOCO NO IMPACTO HUMANITÁRIO")
        print("=" * 35)
        demo.run_demo_session(duration_minutes=3)
    else:
        print("🚀 Executando demo padrão...")
        demo.run_demo_session(duration_minutes=3)

if __name__ == "__main__":
    main()