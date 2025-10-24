"""
Sistema de Treinamento Contínuo
Treina a rede neural em tempo real com dados do mercado
Aprende das estratégias Equilibrada_Pro e US Market System
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from datetime import datetime, timezone, timedelta
import time
import json
from threading import Thread, Lock
import schedule

# Imports do sistema
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.ml.neural_learning_agent import NeuralTradingAgent, TradingExperience
from src.data.alpha_vantage_loader import USMarketDataManager
from src.config.multi_asset_config import OPTIMIZED_ASSET_CONFIGS
from new_rede_a.config import US_MARKET_FOCUS_CONFIG

logger = logging.getLogger(__name__)

class ContinuousLearningSystem:
    """
    Sistema de aprendizado contínuo para rede neural
    - Coleta dados em tempo real
    - Treina com experiências dos experts
    - Melhora performance continuamente
    - Monitora assertividade e ajusta parâmetros
    """
    
    def __init__(self, target_accuracy: float = 0.60):
        self.target_accuracy = target_accuracy
        self.current_accuracy = 0.0
        self.learning_active = False
        self.data_lock = Lock()
        
        # Componentes principais
        self.neural_agent = NeuralTradingAgent(
            state_size=50,
            action_size=3,
            learning_rate=0.001,
            epsilon=0.8  # Começa com alta exploration
        )
        
        self.data_manager = USMarketDataManager()
        
        # Configuração de símbolos focados
        self.focus_symbols = [
            symbol for symbol, config in OPTIMIZED_ASSET_CONFIGS['STOCKS'].items()
            if config.get('market') == 'US' and config.get('priority') == 1
        ]
        
        # Métricas de aprendizado
        self.learning_metrics = {
            'total_experiences': 0,
            'training_sessions': 0,
            'accuracy_history': [],
            'reward_history': [],
            'learning_rate_adjustments': 0,
            'expert_vs_neural_comparison': []
        }
        
        # Cache de dados
        self.market_data_cache = {}
        self.last_data_update = None
        
        logger.info("🎓 Sistema de Aprendizado Contínuo inicializado")
        logger.info(f"🎯 Target accuracy: {target_accuracy:.0%}")
        logger.info(f"📊 Símbolos foco: {self.focus_symbols}")
    
    def start_continuous_learning(self):
        """Inicia o sistema de aprendizado contínuo"""
        self.learning_active = True
        
        logger.info("🚀 Iniciando aprendizado contínuo...")
        
        # Agenda tarefas
        schedule.every(15).minutes.do(self._collect_market_data)
        schedule.every(30).minutes.do(self._training_session)
        schedule.every(2).hours.do(self._evaluate_and_adjust)
        schedule.every(12).hours.do(self._save_progress)
        schedule.every().day.at("09:00").do(self._daily_performance_report)
        
        # Thread principal de execução
        learning_thread = Thread(target=self._learning_loop, daemon=True)
        learning_thread.start()
        
        logger.info("✅ Sistema de aprendizado ativo")
        
        return learning_thread
    
    def stop_learning(self):
        """Para o sistema de aprendizado"""
        self.learning_active = False
        logger.info("🛑 Sistema de aprendizado parado")
    
    def _learning_loop(self):
        """Loop principal de aprendizado"""
        while self.learning_active:
            try:
                schedule.run_pending()
                time.sleep(60)  # Verifica a cada minuto
                
            except Exception as e:
                logger.error(f"❌ Erro no loop de aprendizado: {e}")
                time.sleep(300)  # Espera 5 min em caso de erro
    
    def _collect_market_data(self):
        """Coleta dados de mercado em tempo real"""
        logger.info("📡 Coletando dados de mercado...")
        
        try:
            # Carrega dados dos símbolos foco
            new_data = self.data_manager.load_us_market_data(
                symbols=self.focus_symbols,
                interval="60min"
            )
            
            if new_data:
                with self.data_lock:
                    self.market_data_cache.update(new_data)
                    self.last_data_update = datetime.now(timezone.utc)
                
                logger.info(f"✅ Dados atualizados: {len(new_data)} símbolos")
                
                # Processa experiências para cada símbolo
                self._process_new_experiences(new_data)
            
        except Exception as e:
            logger.error(f"❌ Erro coletando dados: {e}")
    
    def _process_new_experiences(self, market_data: Dict[str, pd.DataFrame]):
        """Processa novos dados e cria experiências de aprendizado"""
        for symbol, df in market_data.items():
            try:
                if len(df) < 50:  # Dados insuficientes
                    continue
                
                # Processa múltiplos pontos no tempo
                for i in range(len(df) - 20, len(df) - 1):  # Últimos 20 pontos
                    current_data = df.iloc[:i+1]
                    next_data = df.iloc[:i+2]
                    
                    if len(current_data) < 30:  # Mínimo para indicadores
                        continue
                    
                    # Estado atual
                    current_state = self.neural_agent.preprocess_market_data(current_data)
                    next_state = self.neural_agent.preprocess_market_data(next_data)
                    
                    # Ação do expert
                    expert_action, expert_confidence, strategy_used = \
                        self.neural_agent.get_expert_action(symbol, current_data)
                    
                    # Calcula recompensa baseada no resultado real
                    current_price = current_data['close'].iloc[-1]
                    next_price = next_data['close'].iloc[-1]
                    price_change = (next_price - current_price) / current_price
                    
                    reward = self.neural_agent.calculate_reward(
                        expert_action, price_change, expert_confidence
                    )
                    
                    # Determina condições de mercado
                    volatility = current_data['close'].rolling(10).std().iloc[-1]
                    trend = (current_data['close'].iloc[-1] / current_data['close'].iloc[-10] - 1)
                    
                    if trend > 0.02:
                        market_condition = 'bull'
                    elif trend < -0.02:
                        market_condition = 'bear'
                    else:
                        market_condition = 'sideways'
                    
                    # Cria experiência
                    experience = TradingExperience(
                        symbol=symbol,
                        state=current_state,
                        action=expert_action,
                        reward=reward,
                        next_state=next_state,
                        done=False,
                        confidence=expert_confidence,
                        strategy_used=strategy_used,
                        timestamp=current_data.index[-1] if hasattr(current_data.index[-1], 'to_pydatetime') 
                                 else datetime.now(timezone.utc),
                        market_conditions=market_condition
                    )
                    
                    # Armazena experiência
                    self.neural_agent.remember(experience)
                    self.learning_metrics['total_experiences'] += 1
                
                logger.info(f"📈 Experiências processadas para {symbol}: {len(df) - 20}")
                
            except Exception as e:
                logger.error(f"❌ Erro processando {symbol}: {e}")
    
    def _training_session(self):
        """Sessão de treinamento da rede neural"""
        logger.info("🎓 Iniciando sessão de treinamento...")
        
        try:
            # Treina com experiências recentes
            if len(self.neural_agent.memory) >= 32:
                
                # Imitation Learning (aprende dos experts)
                imitation_loss = self.neural_agent.imitation_learning(batch_size=64)
                
                # Reinforcement Learning (melhora com experiência)
                rl_loss = self.neural_agent.replay_training(batch_size=32)
                
                # Atualiza target network periodicamente
                if self.learning_metrics['training_sessions'] % 10 == 0:
                    self.neural_agent.update_target_network()
                
                self.learning_metrics['training_sessions'] += 1
                
                logger.info(f"✅ Treinamento concluído")
                logger.info(f"📊 Imitation loss: {imitation_loss:.4f}")
                logger.info(f"📊 RL loss: {rl_loss:.4f}")
                logger.info(f"🎯 Exploration rate: {self.neural_agent.epsilon:.3f}")
            
            else:
                logger.info("⏳ Aguardando mais experiências para treinar...")
        
        except Exception as e:
            logger.error(f"❌ Erro no treinamento: {e}")
    
    def _evaluate_and_adjust(self):
        """Avalia performance e ajusta parâmetros"""
        logger.info("📊 Avaliando performance e ajustando parâmetros...")
        
        try:
            # Avalia performance atual
            performance = self.neural_agent.evaluate_performance()
            
            if performance.get('insufficient_data'):
                logger.info("📊 Dados insuficientes para avaliação")
                return
            
            self.current_accuracy = performance['accuracy']
            
            logger.info(f"📈 Accuracy atual: {self.current_accuracy:.1%}")
            logger.info(f"🎯 Target accuracy: {self.target_accuracy:.1%}")
            logger.info(f"💰 Avg reward: {performance['avg_reward']:.3f}")
            logger.info(f"📊 Profit factor: {performance['profit_factor']:.2f}")
            
            # Ajustes adaptativos
            self._adaptive_parameter_adjustment(performance)
            
            # Armazena métricas
            self.learning_metrics['accuracy_history'].append(self.current_accuracy)
            self.learning_metrics['reward_history'].append(performance['avg_reward'])
            
            # Compara com experts
            self._compare_with_experts()
            
        except Exception as e:
            logger.error(f"❌ Erro na avaliação: {e}")
    
    def _adaptive_parameter_adjustment(self, performance: Dict):
        """Ajusta parâmetros baseado na performance"""
        accuracy = performance['accuracy']
        avg_reward = performance['avg_reward']
        
        # Ajusta learning rate
        if accuracy < self.target_accuracy - 0.1:  # 10% abaixo do target
            # Performance ruim: aumenta learning rate
            current_lr = float(self.neural_agent.q_network.optimizer.learning_rate.numpy())
            new_lr = min(current_lr * 1.1, 0.01)
            self.neural_agent.q_network.optimizer.learning_rate.assign(new_lr)
            
            logger.info(f"📈 Learning rate aumentado: {current_lr:.6f} → {new_lr:.6f}")
            self.learning_metrics['learning_rate_adjustments'] += 1
            
        elif accuracy > self.target_accuracy + 0.05:  # 5% acima do target
            # Performance boa: diminui learning rate para estabilidade
            current_lr = float(self.neural_agent.q_network.optimizer.learning_rate.numpy())
            new_lr = max(current_lr * 0.95, 0.0001)
            self.neural_agent.q_network.optimizer.learning_rate.assign(new_lr)
            
            logger.info(f"📉 Learning rate diminuído: {current_lr:.6f} → {new_lr:.6f}")
        
        # Ajusta exploration rate
        if accuracy < self.target_accuracy:
            # Precisa explorar mais
            self.neural_agent.epsilon = max(
                self.neural_agent.epsilon, 
                0.3 - (accuracy / self.target_accuracy) * 0.2
            )
        else:
            # Pode reduzir exploration
            self.neural_agent.epsilon = max(
                self.neural_agent.epsilon * 0.99, 
                0.05
            )
        
        logger.info(f"🔄 Exploration rate ajustado: {self.neural_agent.epsilon:.3f}")
    
    def _compare_with_experts(self):
        """Compara performance da rede neural com experts"""
        if len(self.market_data_cache) == 0:
            return
        
        try:
            neural_correct = 0
            expert_correct = 0
            total_comparisons = 0
            
            # Testa em dados recentes
            for symbol, df in self.market_data_cache.items():
                if len(df) < 30:
                    continue
                
                # Última observação
                test_data = df.iloc[:-1]  # Todos menos o último
                actual_price_change = (df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]
                
                # Ação do expert
                expert_action, expert_conf, _ = self.neural_agent.get_expert_action(symbol, test_data)
                
                # Ação da rede neural
                state = self.neural_agent.preprocess_market_data(test_data)
                neural_action, neural_conf = self.neural_agent.act(state, use_expert=False)
                
                # Verifica acertos
                if expert_action == 1 and actual_price_change > 0.005:  # Buy e subiu
                    expert_correct += 1
                elif expert_action == 2 and actual_price_change < -0.005:  # Sell e desceu
                    expert_correct += 1
                elif expert_action == 0 and abs(actual_price_change) < 0.005:  # Hold e lateral
                    expert_correct += 1
                
                if neural_action == 1 and actual_price_change > 0.005:
                    neural_correct += 1
                elif neural_action == 2 and actual_price_change < -0.005:
                    neural_correct += 1
                elif neural_action == 0 and abs(actual_price_change) < 0.005:
                    neural_correct += 1
                
                total_comparisons += 1
            
            if total_comparisons > 0:
                expert_accuracy = expert_correct / total_comparisons
                neural_accuracy = neural_correct / total_comparisons
                
                comparison = {
                    'timestamp': datetime.now(timezone.utc),
                    'expert_accuracy': expert_accuracy,
                    'neural_accuracy': neural_accuracy,
                    'neural_improvement': neural_accuracy - expert_accuracy,
                    'total_tests': total_comparisons
                }
                
                self.learning_metrics['expert_vs_neural_comparison'].append(comparison)
                
                logger.info(f"🏆 Expert accuracy: {expert_accuracy:.1%}")
                logger.info(f"🧠 Neural accuracy: {neural_accuracy:.1%}")
                logger.info(f"📈 Neural improvement: {comparison['neural_improvement']:+.1%}")
        
        except Exception as e:
            logger.error(f"❌ Erro na comparação: {e}")
    
    def _save_progress(self):
        """Salva progresso do modelo e métricas"""
        logger.info("💾 Salvando progresso...")
        
        try:
            # Salva modelo da rede neural
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            model_path = f"neural_trading_agent_{timestamp}.h5"
            self.neural_agent.save_model(model_path)
            
            # Salva métricas detalhadas
            metrics_path = f"learning_metrics_{timestamp}.json"
            with open(metrics_path, 'w') as f:
                json.dump(self.learning_metrics, f, indent=2, default=str)
            
            logger.info(f"✅ Progresso salvo: {model_path}")
            
        except Exception as e:
            logger.error(f"❌ Erro salvando progresso: {e}")
    
    def _daily_performance_report(self):
        """Relatório diário de performance"""
        logger.info("📋 Gerando relatório diário...")
        
        try:
            performance = self.neural_agent.evaluate_performance()
            
            if performance.get('insufficient_data'):
                logger.info("📊 Dados insuficientes para relatório")
                return
            
            report = f"""
═══════════════════════════════════════
📊 RELATÓRIO DIÁRIO - {datetime.now().strftime('%Y-%m-%d')}
═══════════════════════════════════════

🎯 PERFORMANCE ATUAL:
   Accuracy: {self.current_accuracy:.1%} (Target: {self.target_accuracy:.1%})
   Avg Reward: {performance['avg_reward']:.3f}
   Profit Factor: {performance['profit_factor']:.2f}
   
🧠 APRENDIZADO:
   Total Experiências: {self.learning_metrics['total_experiences']:,}
   Sessões de Treino: {self.learning_metrics['training_sessions']:,}
   Ajustes LR: {self.learning_metrics['learning_rate_adjustments']}
   
🎛️ PARÂMETROS:
   Exploration Rate: {self.neural_agent.epsilon:.3f}
   Learning Rate: {float(self.neural_agent.q_network.optimizer.learning_rate.numpy()):.6f}
   
📈 EVOLUÇÃO (últimos 7 dias):
   Accuracy Trend: {np.mean(self.learning_metrics['accuracy_history'][-7:]) if len(self.learning_metrics['accuracy_history']) >= 7 else 'N/A'}
   Reward Trend: {np.mean(self.learning_metrics['reward_history'][-7:]) if len(self.learning_metrics['reward_history']) >= 7 else 'N/A'}

🏆 vs EXPERTS (última comparação):
"""
            
            if self.learning_metrics['expert_vs_neural_comparison']:
                last_comparison = self.learning_metrics['expert_vs_neural_comparison'][-1]
                report += f"   Neural: {last_comparison['neural_accuracy']:.1%}\n"
                report += f"   Expert: {last_comparison['expert_accuracy']:.1%}\n"
                report += f"   Melhoria: {last_comparison['neural_improvement']:+.1%}\n"
            
            report += "\n═══════════════════════════════════════"
            
            logger.info(report)
            
            # Salva relatório em arquivo
            report_path = f"daily_report_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
        except Exception as e:
            logger.error(f"❌ Erro gerando relatório: {e}")
    
    def get_current_status(self) -> Dict:
        """Retorna status atual do sistema"""
        return {
            "learning_active": self.learning_active,
            "current_accuracy": self.current_accuracy,
            "target_accuracy": self.target_accuracy,
            "total_experiences": self.learning_metrics['total_experiences'],
            "training_sessions": self.learning_metrics['training_sessions'],
            "exploration_rate": self.neural_agent.epsilon,
            "last_data_update": self.last_data_update,
            "symbols_tracked": len(self.market_data_cache),
            "focus_symbols": self.focus_symbols
        }

# Exemplo de uso
if __name__ == "__main__":
    print("🎓 Sistema de Treinamento Contínuo")
    print("🧠 Rede neural aprende das estratégias existentes")
    print("📈 Melhora continuamente para 60% assertividade")
    
    # Inicializa sistema
    learning_system = ContinuousLearningSystem(target_accuracy=0.60)
    
    print(f"✅ Sistema inicializado")
    print(f"🎯 Target: {learning_system.target_accuracy:.0%}")
    print(f"📊 Símbolos foco: {learning_system.focus_symbols}")
    
    # Inicia aprendizado
    learning_thread = learning_system.start_continuous_learning()
    
    try:
        # Monitora por um tempo
        print("\n🚀 Sistema ativo - Pressione Ctrl+C para parar")
        learning_thread.join()
        
    except KeyboardInterrupt:
        print("\n🛑 Parando sistema...")
        learning_system.stop_learning()
        print("✅ Sistema parado")