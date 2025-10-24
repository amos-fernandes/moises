"""
Sistema de Monitoramento de Performance Neural
Dashboard em tempo real para acompanhar aprendizado da IA
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
import time
import json
import numpy as np
from typing import Dict, List

# Configuração da página
st.set_page_config(
    page_title="Neural Trading Monitor",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# CONFIGURAÇÕES
# =====================================================

API_BASE_URL = "http://localhost:8001/api"
REFRESH_INTERVAL = 30  # segundos
US_STOCKS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA']

# =====================================================
# FUNÇÕES AUXILIARES
# =====================================================

@st.cache_data(ttl=60)
def get_neural_status():
    """Obtém status do sistema neural"""
    try:
        response = requests.get(f"{API_BASE_URL}/neural/status", timeout=5)
        return response.json() if response.status_code == 200 else None
    except:
        return None

@st.cache_data(ttl=30)
def get_neural_performance():
    """Obtém métricas de performance"""
    try:
        response = requests.get(f"{API_BASE_URL}/neural/performance", timeout=5)
        return response.json() if response.status_code == 200 else None
    except:
        return None

def get_prediction(symbol: str, use_neural: bool = True):
    """Obtém predição para um símbolo"""
    try:
        payload = {
            "symbol": symbol,
            "use_neural": use_neural,
            "confidence_threshold": 0.65
        }
        response = requests.post(f"{API_BASE_URL}/neural/predict", json=payload, timeout=10)
        return response.json() if response.status_code == 200 else None
    except:
        return None

def format_signal_badge(signal: str, confidence: float):
    """Formatar badge de sinal"""
    colors = {
        'BUY': '#28a745',
        'SELL': '#dc3545', 
        'HOLD': '#6c757d'
    }
    
    return f"""
    <div style="display: inline-block; background-color: {colors.get(signal, '#6c757d')}; 
                color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; margin: 2px;">
        {signal} ({confidence:.1%})
    </div>
    """

# =====================================================
# INTERFACE PRINCIPAL
# =====================================================

def main():
    # Header
    st.title("🧠 Neural Trading System - Monitor")
    st.markdown("**Sistema de IA com Aprendizado Contínuo | Meta: 60%+ Assertividade**")
    
    # Sidebar - Controles
    with st.sidebar:
        st.header("🎛️ Controles do Sistema")
        
        # Status Connection
        try:
            status = get_neural_status()
            if status:
                st.success("✅ Conectado ao Sistema")
            else:
                st.error("❌ Falha na Conexão")
        except:
            st.error("❌ Sistema Offline")
        
        # Controles
        st.subheader("Ações do Sistema")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Start", use_container_width=True):
                try:
                    requests.post(f"{API_BASE_URL}/neural/control?action=start", timeout=5)
                    st.success("Sistema iniciado!")
                except:
                    st.error("Erro ao iniciar")
        
        with col2:
            if st.button("⏹️ Stop", use_container_width=True):
                try:
                    requests.post(f"{API_BASE_URL}/neural/control?action=stop", timeout=5)
                    st.warning("Sistema parado!")
                except:
                    st.error("Erro ao parar")
        
        if st.button("💾 Salvar Modelo", use_container_width=True):
            try:
                requests.post(f"{API_BASE_URL}/neural/control?action=save", timeout=5)
                st.success("Modelo salvo!")
            except:
                st.error("Erro ao salvar")
        
        # Auto-refresh
        auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=True)
        
        if auto_refresh:
            time.sleep(0.1)  # Small delay
            st.rerun()
    
    # =====================================================
    # DASHBOARD PRINCIPAL
    # =====================================================
    
    # Métricas principais
    status = get_neural_status()
    performance = get_neural_performance()
    
    if status and performance:
        # KPIs principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            current_acc = performance.get('model_parameters', {}).get('current_accuracy', 0)
            st.metric(
                label="🎯 Assertividade Atual",
                value=f"{current_acc:.1%}",
                delta=f"Meta: 60%" if current_acc < 0.6 else "Meta atingida! 🎉"
            )
        
        with col2:
            exploration_rate = performance.get('model_parameters', {}).get('exploration_rate', 0)
            st.metric(
                label="🔍 Taxa Exploração",
                value=f"{exploration_rate:.2%}",
                delta="Aprendendo" if exploration_rate > 0.1 else "Explorando menos"
            )
        
        with col3:
            total_exp = performance.get('learning_evolution', {}).get('total_experiences', 0)
            st.metric(
                label="🧠 Total Experiências",
                value=f"{total_exp:,}",
                delta="+50/hora" if status.get('learning_status', {}).get('learning_active') else "Parado"
            )
        
        with col4:
            training_sessions = performance.get('learning_evolution', {}).get('training_sessions', 0)
            st.metric(
                label="🎓 Sessões Treino",
                value=f"{training_sessions}",
                delta="A cada 30min" if status.get('learning_status', {}).get('learning_active') else "Inativo"
            )
        
        # =====================================================
        # GRÁFICOS DE PERFORMANCE
        # =====================================================
        
        st.subheader("📈 Evolução da Performance")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de Assertividade
            acc_history = performance.get('learning_evolution', {}).get('accuracy_trend', [])
            if acc_history:
                fig_acc = go.Figure()
                fig_acc.add_trace(go.Scatter(
                    y=acc_history,
                    mode='lines+markers',
                    name='Assertividade',
                    line=dict(color='#007acc', width=3),
                    marker=dict(size=6)
                ))
                
                # Linha da meta
                fig_acc.add_hline(
                    y=0.6, 
                    line_dash="dash", 
                    line_color="red",
                    annotation_text="Meta 60%"
                )
                
                fig_acc.update_layout(
                    title="Evolução da Assertividade",
                    yaxis_title="Assertividade (%)",
                    yaxis=dict(tickformat='.1%'),
                    height=300
                )
                
                st.plotly_chart(fig_acc, use_container_width=True)
        
        with col2:
            # Gráfico de Recompensas
            reward_history = performance.get('learning_evolution', {}).get('reward_trend', [])
            if reward_history:
                fig_reward = go.Figure()
                fig_reward.add_trace(go.Scatter(
                    y=reward_history,
                    mode='lines+markers',
                    name='Recompensa Média',
                    line=dict(color='#28a745', width=3),
                    marker=dict(size=6)
                ))
                
                fig_reward.update_layout(
                    title="Evolução das Recompensas",
                    yaxis_title="Recompensa Média",
                    height=300
                )
                
                st.plotly_chart(fig_reward, use_container_width=True)
        
        # =====================================================
        # ANÁLISE EM TEMPO REAL
        # =====================================================
        
        st.subheader("🔍 Análise Neural vs Expert")
        
        # Seletor de símbolos
        selected_symbols = st.multiselect(
            "Escolha os símbolos para análise:",
            US_STOCKS,
            default=['AAPL', 'MSFT', 'NVDA']
        )
        
        if selected_symbols:
            # Análise dos símbolos selecionados
            analysis_results = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, symbol in enumerate(selected_symbols):
                status_text.text(f"Analisando {symbol}...")
                prediction = get_prediction(symbol)
                
                if prediction:
                    analysis_results.append(prediction)
                
                progress_bar.progress((i + 1) / len(selected_symbols))
            
            status_text.empty()
            progress_bar.empty()
            
            # Exibir resultados
            if analysis_results:
                st.subheader("📊 Resultados das Análises")
                
                # Tabela de resultados
                df_results = []
                for result in analysis_results:
                    df_results.append({
                        'Símbolo': result['symbol'],
                        'Expert Signal': result['expert_signal'],
                        'Expert Conf.': f"{result['expert_confidence']:.1%}",
                        'Neural Signal': result['neural_signal'],
                        'Neural Conf.': f"{result['neural_confidence']:.1%}",
                        'Decisão Final': result['final_recommendation'],
                        'Concordância': '✅' if result['expert_signal'] == result['neural_signal'] else '❌'
                    })
                
                df = pd.DataFrame(df_results)
                st.dataframe(df, use_container_width=True)
                
                # Gráfico de concordância
                concordance = [r['expert_signal'] == r['neural_signal'] for r in analysis_results]
                concordance_rate = sum(concordance) / len(concordance)
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Gráfico de confiança
                    symbols = [r['symbol'] for r in analysis_results]
                    expert_conf = [r['expert_confidence'] for r in analysis_results]
                    neural_conf = [r['neural_confidence'] for r in analysis_results]
                    
                    fig_conf = go.Figure()
                    fig_conf.add_trace(go.Bar(
                        x=symbols,
                        y=expert_conf,
                        name='Expert',
                        marker_color='#007acc'
                    ))
                    fig_conf.add_trace(go.Bar(
                        x=symbols,
                        y=neural_conf,
                        name='Neural',
                        marker_color='#28a745'
                    ))
                    
                    fig_conf.update_layout(
                        title="Confiança: Expert vs Neural",
                        yaxis_title="Confiança",
                        yaxis=dict(tickformat='.0%'),
                        barmode='group',
                        height=400
                    )
                    
                    st.plotly_chart(fig_conf, use_container_width=True)
                
                with col2:
                    st.metric(
                        label="🤝 Taxa de Concordância",
                        value=f"{concordance_rate:.1%}",
                        delta="Boa sincronização" if concordance_rate >= 0.7 else "Precisa melhorar"
                    )
                    
                    # Detalhes do último resultado
                    if analysis_results:
                        last_result = analysis_results[-1]
                        st.markdown("**Última Análise:**")
                        st.markdown(f"📊 {last_result['symbol']}")
                        
                        reasoning = last_result.get('reasoning', [])
                        for reason in reasoning[:2]:
                            st.markdown(f"• {reason}")
    
    else:
        st.error("❌ Não foi possível carregar os dados do sistema. Verifique se a API está rodando.")
        st.markdown("**Para iniciar o sistema:**")
        st.code("python app_neural_trading.py", language="bash")

# =====================================================
# EXECUÇÃO
# =====================================================

if __name__ == "__main__":
    # Auto-refresh configuration
    if 'refresh_counter' not in st.session_state:
        st.session_state.refresh_counter = 0
    
    # Executa dashboard
    main()
    
    # Footer
    st.markdown("---")
    st.markdown("🧠 **Neural Trading System** - Aprendizado contínuo para máxima assertividade")
    st.markdown(f"⏰ Última atualização: {datetime.now().strftime('%H:%M:%S')}")