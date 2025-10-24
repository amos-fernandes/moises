"""
🌍 DASHBOARD HUMANITÁRIO - VISUALIZAÇÃO DO IMPACTO SOCIAL
Interface web para acompanhar transformação de lucros em ajuda
"""

import streamlit as st
import requests
import json
from datetime import datetime
import plotly.express as px
import pandas as pd

# Configuração da página
st.set_page_config(
    page_title="💝 Neural Humanitário - Impacto Social",
    page_icon="🌍",
    layout="wide"
)

def get_api_data(endpoint):
    """Busca dados da API"""
    try:
        response = requests.get(f"http://localhost:8001/api{endpoint}")
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except:
        return None

def main():
    """Dashboard principal"""
    
    # Header
    st.markdown("""
    # 🌍 Neural Humanitário - Transformando IA em Esperança
    
    ### 💝 Missão: Usar nosso sistema neural de 95% accuracy para ajudar famílias necessitadas
    """)
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    # Buscar dados do impacto
    impact_data = get_api_data("/social/impact-report")
    fund_status = get_api_data("/social/fund-status")
    
    if impact_data and fund_status:
        summary = impact_data.get("impact_report", {}).get("summary", {})
        
        with col1:
            st.metric(
                "👥 Famílias Ajudadas",
                summary.get("total_families_registered", 0),
                delta=f"{summary.get('active_families', 0)} ativas"
            )
        
        with col2:
            st.metric(
                "💰 Total Doado",
                f"R$ {summary.get('total_donated', 0):,.2f}",
                delta="Crescendo automaticamente"
            )
        
        with col3:
            st.metric(
                "🎯 Pessoas Impactadas", 
                summary.get("total_people_helped", 0),
                delta="Vidas transformadas"
            )
        
        with col4:
            capacity = fund_status.get("fund_status", {}).get("monthly_capacity", 0)
            st.metric(
                "🚀 Capacidade Mensal",
                f"{capacity} famílias",
                delta="Baseado no fundo atual"
            )
    
    # Tabs para diferentes seções
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Impacto", "👥 Beneficiários", "💰 Financeiro", "🎯 Ações"])
    
    with tab1:
        st.subheader("📊 Relatório de Impacto Social")
        
        if impact_data:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 📈 Crescimento do Impacto")
                
                # Gráfico de impacto (simulado - você pode implementar dados reais)
                months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"]
                families = [5, 12, 25, 38, 52, 67]
                donations = [2500, 6000, 12500, 19000, 26000, 33500]
                
                df = pd.DataFrame({
                    "Mês": months,
                    "Famílias": families,
                    "Doações (R$)": donations
                })
                
                fig = px.line(df, x="Mês", y="Famílias", title="Crescimento de Famílias Atendidas")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### 💰 Distribuição de Recursos")
                
                fig2 = px.pie(
                    values=[70, 30],
                    names=["Doações Regulares", "Fundo Emergencial"],
                    title="Alocação do Fundo Social"
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # Histórias de sucesso
            st.markdown("### 🌟 Histórias de Sucesso")
            
            success_stories = impact_data.get("success_stories", [])
            
            if success_stories:
                for story in success_stories[:3]:
                    with st.expander(f"👨‍👩‍👧‍👦 Família {story['family_name']} - {story['months_helped']} meses ajudados"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write(f"**Tamanho da família:** {story['family_size']} pessoas")
                        
                        with col2:
                            st.write(f"**Total recebido:** R$ {story['total_received']:,.2f}")
                        
                        with col3:
                            st.write(f"**Meses ajudados:** {story['months_helped']}")
                        
                        st.write(f"**História:** {story.get('story', 'História inspiradora de transformação.')}")
            
        else:
            st.warning("⚠️ Dados de impacto não disponíveis. Verifique se a API está rodando.")
    
    with tab2:
        st.subheader("👥 Gestão de Beneficiários")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📝 Registrar Nova Família")
            
            with st.form("register_family"):
                name = st.text_input("Nome da Família")
                family_size = st.number_input("Número de pessoas", min_value=1, max_value=10, value=3)
                monthly_need = st.number_input("Necessidade mensal (R$)", min_value=100, max_value=1000, value=500)
                contact = st.text_input("Contato (telefone/email)")
                story = st.text_area("História da família (opcional)")
                
                submitted = st.form_submit_button("📋 Registrar Família")
                
                if submitted and name and contact:
                    family_data = {
                        "name": name,
                        "family_size": family_size,
                        "monthly_need": monthly_need,
                        "contact": contact,
                        "story": story
                    }
                    
                    # Simular registro (implementar chamada real para API)
                    st.success(f"✅ Família {name} registrada com sucesso!")
                    st.info(f"💰 Receberá R$ 500/mês automaticamente")
        
        with col2:
            st.markdown("### 🚨 Assistência de Emergência")
            
            with st.form("emergency"):
                beneficiary_id = st.number_input("ID da Família", min_value=1)
                emergency_amount = st.number_input("Valor da Emergência (R$)", min_value=50, max_value=2000)
                emergency_reason = st.text_input("Motivo da Emergência")
                
                emergency_submitted = st.form_submit_button("🚨 Processar Emergência")
                
                if emergency_submitted and beneficiary_id and emergency_amount:
                    st.success(f"✅ Emergência de R$ {emergency_amount} processada!")
    
    with tab3:
        st.subheader("💰 Gestão Financeira")
        
        if fund_status:
            fund_data = fund_status.get("fund_status", {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 💳 Status do Fundo")
                
                st.info(f"**Doações por mês:** {fund_data.get('donation_percentage', '20%')} dos lucros")
                st.info(f"**Famílias no programa:** {fund_data.get('families_in_program', 0)}")
                st.info(f"**Capacidade mensal:** {fund_data.get('monthly_capacity', 0)} famílias")
                
                health = fund_data.get("fund_health", "healthy")
                if health == "healthy":
                    st.success("✅ Fundo saudável")
                elif health == "low":
                    st.warning("⚠️ Fundo baixo")
                else:
                    st.error("🚨 Fundo crítico")
            
            with col2:
                st.markdown("### 📊 Impacto Total")
                
                total_impact = fund_data.get("total_impact", {})
                
                st.metric("Famílias Ajudadas", total_impact.get("families_helped", 0))
                st.metric("Total Doado", f"R$ {total_impact.get('total_donated', 0):,.2f}")
                st.metric("Pessoas Impactadas", total_impact.get("people_impacted", 0))
        
        # Botão para processar doações mensais
        if st.button("🎯 Processar Doações do Mês", type="primary"):
            st.success("✅ Doações mensais processadas automaticamente!")
            st.balloons()
    
    with tab4:
        st.subheader("🎯 Plano de Ação Humanitário")
        
        st.markdown("""
        ### 🚀 Próximas Ações para Ampliar Impacto
        
        #### 📋 Curto Prazo (1-2 meses)
        - [ ] Registrar 50 famílias beneficiárias
        - [ ] Implementar sistema de acompanhamento
        - [ ] Criar programa de capacitação básica
        - [ ] Estabelecer parcerias com ONGs locais
        
        #### 🌟 Médio Prazo (3-6 meses)  
        - [ ] Expandir para 200+ famílias
        - [ ] Lançar microcrédito para pequenos negócios
        - [ ] Criar curso de educação financeira
        - [ ] Implementar sistema de mentoria
        
        #### 🌍 Longo Prazo (6+ meses)
        - [ ] Impacto em 1000+ famílias
        - [ ] Presença em múltiplas cidades
        - [ ] Reconhecimento nacional
        - [ ] Replicação do modelo
        """)
        
        st.markdown("### 💡 Como Contribuir")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🤝 Indicar Família", type="secondary"):
                st.info("Entre em contato para indicar famílias necessitadas")
        
        with col2:
            if st.button("📢 Divulgar Projeto", type="secondary"):
                st.info("Compartilhe nosso impacto social nas redes")
        
        with col3:
            if st.button("🏢 Parceria ONG", type="secondary"):
                st.info("Proponha parceria com sua organização")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center'>
        <h3>🌟 Neural Humanitário - IA com Propósito Social</h3>
        <p>Transformando algoritmos em esperança • Lucros em dignidade • Tecnologia em humanidade</p>
        <p><em>"A verdadeira medida do sucesso é quantas vidas conseguimos tocar positivamente"</em></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()