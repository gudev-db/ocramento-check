import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(
    page_title="Monitor de Orçamento - Campanhas",
    page_icon="💰",
    layout="wide"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .alert-box {
        background-color: #ffebee;
        border-left: 5px solid #f44336;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .success-box {
        background-color: #e8f5e8;
        border-left: 5px solid #4caf50;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .warning-box {
        background-color: #fff3e0;
        border-left: 5px solid #ff9800;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #dee2e6;
        text-align: center;
    }
    .config-section {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

class MonitorOrcamento:
    def __init__(self):
        self.dados_campanhas = None
        
    def carregar_planilha_campanhas(self):
        """Interface para carregar a planilha de campanhas"""
        st.header("📊 Carregar Planilha de Campanhas")
        
        uploaded_file = st.file_uploader(
            "Faça upload da planilha com os dados das campanhas (Excel ou CSV)",
            type=['xlsx', 'xls', 'csv'],
            key="planilha_campanhas"
        )
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    self.dados_campanhas = pd.read_csv(uploaded_file)
                else:
                    self.dados_campanhas = pd.read_excel(uploaded_file)
                
                st.success(f"✅ Planilha carregada com sucesso! {len(self.dados_campanhas)} campanhas encontradas.")
                
                # Mostrar preview dos dados
                with st.expander("👀 Visualizar dados da planilha"):
                    st.dataframe(self.dados_campanhas.head(10))
                    
                return True
            except Exception as e:
                st.error(f"❌ Erro ao carregar planilha: {str(e)}")
                return False
        return False
    
    def configurar_orcamentos(self):
        """Interface para configurar os orçamentos por plataforma/campanha"""
        st.header("⚙️ Configurar Orçamentos")
        
        if self.dados_campanhas is None:
            st.warning("⚠️ Carregue primeiro a planilha de campanhas")
            return {}
        
        # Detectar colunas possíveis para plataforma e campanha
        colunas_disponiveis = self.dados_campanhas.columns.tolist()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔍 Identificar Colunas")
            coluna_plataforma = st.selectbox(
                "Selecione a coluna que identifica a plataforma:",
                options=colunas_disponiveis,
                index=0
            )
            
            coluna_campanha = st.selectbox(
                "Selecione a coluna que identifica a campanha:",
                options=colunas_disponiveis,
                index=1 if len(colunas_disponiveis) > 1 else 0
            )
            
            coluna_gasto = st.selectbox(
                "Selecione a coluna que mostra o gasto atual:",
                options=colunas_disponiveis,
                index=2 if len(colunas_disponiveis) > 2 else 0
            )
        
        with col2:
            st.subheader("💰 Definir Orçamentos")
            
            # Orçamento global padrão
            orcamento_global = st.number_input(
                "Orçamento padrão para todas as campanhas:",
                min_value=0.0,
                value=1000.0,
                step=100.0
            )
            
            # Orçamentos específicos por plataforma
            st.subheader("🎯 Orçamentos por Plataforma")
            
            if coluna_plataforma in self.dados_campanhas.columns:
                plataformas = self.dados_campanhas[coluna_plataforma].unique()
                orcamentos_plataforma = {}
                
                for plataforma in plataformas[:10]:  # Limitar a 10 para não ficar muito longo
                    orcamento = st.number_input(
                        f"Orçamento para {plataforma}:",
                        min_value=0.0,
                        value=orcamento_global,
                        step=100.0,
                        key=f"orc_{plataforma}"
                    )
                    orcamentos_plataforma[plataforma] = orcamento
            
            # Orçamentos específicos por campanha
            st.subheader("🎯 Orçamentos por Campanha (Opcional)")
            orcamentos_campanha = {}
            
            if st.checkbox("Definir orçamentos individuais por campanha"):
                campanhas_sample = self.dados_campanhas[coluna_campanha].head(5).tolist()
                for campanha in campanhas_sample:
                    orcamento = st.number_input(
                        f"Orçamento para '{campanha}':",
                        min_value=0.0,
                        value=orcamento_global,
                        step=100.0,
                        key=f"camp_{campanha}"
                    )
                    orcamentos_campanha[campanha] = orcamento
        
        return {
            'coluna_plataforma': coluna_plataforma,
            'coluna_campanha': coluna_campanha,
            'coluna_gasto': coluna_gasto,
            'orcamento_global': orcamento_global,
            'orcamentos_plataforma': orcamentos_plataforma,
            'orcamentos_campanha': orcamentos_campanha
        }
    
    def analisar_campanhas(self, config):
        """Analisa as campanhas e identifica as que fogem do orçamento"""
        if self.dados_campanhas is None:
            return []
        
        alertas = []
        df = self.dados_campanhas.copy()
        
        # Converter coluna de gasto para numérico
        if config['coluna_gasto'] in df.columns:
            df[config['coluna_gasto']] = pd.to_numeric(df[config['coluna_gasto']], errors='coerce')
        
        for _, row in df.iterrows():
            campanha = row.get(config['coluna_campanha'], 'N/A')
            plataforma = row.get(config['coluna_plataforma'], 'N/A')
            gasto_atual = row.get(config['coluna_gasto'], 0)
            
            if pd.isna(gasto_atual):
                continue
            
            # Determinar orçamento alvo
            orcamento_alvo = config['orcamento_global']  # Padrão global
            
            # Verificar se tem orçamento específico por campanha
            if campanha in config['orcamentos_campanha']:
                orcamento_alvo = config['orcamentos_campanha'][campanha]
            # Verificar se tem orçamento específico por plataforma
            elif plataforma in config['orcamentos_plataforma']:
                orcamento_alvo = config['orcamentos_plataforma'][plataforma]
            
            # Calcular percentual de gasto
            if orcamento_alvo > 0:
                percentual_gasto = (gasto_atual / orcamento_alvo) * 100
                
                # Identificar problemas
                if percentual_gasto > 110:  # Gastou mais de 110%
                    alertas.append({
                        'tipo': 'CRÍTICO',
                        'plataforma': plataforma,
                        'campanha': campanha,
                        'orcamento_planejado': orcamento_alvo,
                        'gasto_atual': gasto_atual,
                        'percentual': percentual_gasto,
                        'mensagem': f'GASTO EXCEDIDO: {percentual_gasto:.1f}% do orçamento'
                    })
                elif percentual_gasto > 100:  # Passou do orçamento
                    alertas.append({
                        'tipo': 'ALERTA',
                        'plataforma': plataforma,
                        'campanha': campanha,
                        'orcamento_planejado': orcamento_alvo,
                        'gasto_atual': gasto_atual,
                        'percentual': percentual_gasto,
                        'mensagem': f'ORÇAMENTO ULTRAPASSADO: {percentual_gasto:.1f}%'
                    })
                elif percentual_gasto > 90:  # Próximo do limite
                    alertas.append({
                        'tipo': 'ATENÇÃO',
                        'plataforma': plataforma,
                        'campanha': campanha,
                        'orcamento_planejado': orcamento_alvo,
                        'gasto_atual': gasto_atual,
                        'percentual': percentual_gasto,
                        'mensagem': f'PRÓXIMO DO LIMITE: {percentual_gasto:.1f}%'
                    })
                elif percentual_gasto < 30 and gasto_atual > 0:  # Baixo gasto
                    alertas.append({
                        'tipo': 'BAIXO_GASTO',
                        'plataforma': plataforma,
                        'campanha': campanha,
                        'orcamento_planejado': orcamento_alvo,
                        'gasto_atual': gasto_atual,
                        'percentual': percentual_gasto,
                        'mensagem': f'BAIXO GASTO: {percentual_gasto:.1f}% utilizado'
                    })
        
        return alertas
    
    def mostrar_resultados(self, alertas, config):
        """Mostra os resultados da análise"""
        st.header("📈 Resultados da Análise")
        
        # Métricas gerais
        col1, col2, col3, col4 = st.columns(4)
        
        total_campanhas = len(self.dados_campanhas)
        total_alertas = len(alertas)
        alertas_criticos = len([a for a in alertas if a['tipo'] == 'CRÍTICO'])
        plataformas_analisadas = len(self.dados_campanhas[config['coluna_plataforma']].unique())
        
        with col1:
            st.metric("Total de Campanhas", total_campanhas)
        with col2:
            st.metric("Alertas Totais", total_alertas)
        with col3:
            st.metric("Alertas Críticos", alertas_criticos)
        with col4:
            st.metric("Plataformas", plataformas_analisadas)
        
        # Mostrar alertas
        if alertas:
            st.header("🚨 Campanhas com Discrepâncias")
            
            # Filtrar alertas por tipo
            tab1, tab2, tab3, tab4 = st.tabs(["🔴 Críticos", "🟡 Alertas", "🟠 Atenção", "🔵 Baixo Gasto"])
            
            with tab1:
                criticos = [a for a in alertas if a['tipo'] == 'CRÍTICO']
                if criticos:
                    for alerta in criticos:
                        st.markdown(f"""
                        <div class="alert-box">
                            <strong>{alerta['plataforma']} - {alerta['campanha']}</strong><br>
                            Orçamento: R$ {alerta['orcamento_planejado']:,.2f} | 
                            Gasto: R$ {alerta['gasto_atual']:,.2f} | 
                            <strong>{alerta['percentual']:.1f}%</strong><br>
                            {alerta['mensagem']}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("✅ Nenhum alerta crítico")
            
            with tab2:
                alertas_medio = [a for a in alertas if a['tipo'] == 'ALERTA']
                if alertas_medio:
                    for alerta in alertas_medio:
                        st.markdown(f"""
                        <div class="warning-box">
                            <strong>{alerta['plataforma']} - {alerta['campanha']}</strong><br>
                            Orçamento: R$ {alerta['orcamento_planejado']:,.2f} | 
                            Gasto: R$ {alerta['gasto_atual']:,.2f} | 
                            <strong>{alerta['percentual']:.1f}%</strong><br>
                            {alerta['mensagem']}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("✅ Nenhum orçamento ultrapassado")
            
            with tab3:
                atencao = [a for a in alertas if a['tipo'] == 'ATENÇÃO']
                if atencao:
                    for alerta in atencao:
                        st.markdown(f"""
                        <div class="warning-box">
                            <strong>{alerta['plataforma']} - {alerta['campanha']}</strong><br>
                            Orçamento: R$ {alerta['orcamento_planejado']:,.2f} | 
                            Gasto: R$ {alerta['gasto_atual']:,.2f} | 
                            <strong>{alerta['percentual']:.1f}%</strong><br>
                            {alerta['mensagem']}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("✅ Nenhuma campanha próxima do limite")
            
            with tab4:
                baixo_gasto = [a for a in alertas if a['tipo'] == 'BAIXO_GASTO']
                if baixo_gasto:
                    for alerta in baixo_gasto:
                        st.markdown(f"""
                        <div class="warning-box">
                            <strong>{alerta['plataforma']} - {alerta['campanha']}</strong><br>
                            Orçamento: R$ {alerta['orcamento_planejado']:,.2f} | 
                            Gasto: R$ {alerta['gasto_atual']:,.2f} | 
                            <strong>{alerta['percentual']:.1f}%</strong><br>
                            {alerta['mensagem']}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("✅ Nenhum caso de baixo gasto")
            
            # Resumo em tabela
            st.subheader("📋 Resumo em Tabela")
            df_alertas = pd.DataFrame(alertas)
            st.dataframe(df_alertas, use_container_width=True)
            
        else:
            st.markdown("""
            <div class="success-box">
                <h3>✅ Todas as campanhas dentro do orçamento!</h3>
                <p>Nenhuma discrepância foi encontrada nas campanhas analisadas.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Mostrar dados completos
        st.header("📊 Dados Completos das Campanhas")
        st.dataframe(self.dados_campanhas, use_container_width=True)
    
    def executar_monitoramento(self):
        """Executa o processo completo de monitoramento"""
        st.markdown('<div class="main-header">💰 Monitor de Orçamento - Campanhas</div>', unsafe_allow_html=True)
        
        # Carregar planilha de campanhas
        if not self.carregar_planilha_campanhas():
            return
        
        # Configurar orçamentos
        config = self.configurar_orcamentos()
        
        # Botão para executar análise
        st.header("🔍 Executar Análise")
        
        if st.button("🔄 Analisar Campanhas", type="primary", use_container_width=True):
            with st.spinner("Analisando campanhas..."):
                alertas = self.analisar_campanhas(config)
                self.mostrar_resultados(alertas, config)

def main():
    # Inicializar o monitor
    monitor = MonitorOrcamento()
    
    # Sidebar com informações
    st.sidebar.header("ℹ️ Sobre o Sistema")
    st.sidebar.info("""
    **Monitor de Orçamento de Campanhas**
    
    **Como usar:**
    1. 📊 Carregue a planilha com os dados das campanhas
    2. ⚙️ Configure os orçamentos desejados
    3. 🔄 Execute a análise
    4. 🚨 Veja as campanhas com discrepâncias
    
    **Tipos de alerta:**
    - 🔴 Crítico: >110% do orçamento
    - 🟡 Alerta: >100% do orçamento  
    - 🟠 Atenção: >90% do orçamento
    - 🔵 Baixo gasto: <30% do orçamento
    """)
    
    # Executar o monitoramento
    monitor.executar_monitoramento()

if __name__ == "__main__":
    main()
