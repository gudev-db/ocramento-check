import streamlit as st
import pandas as pd
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(
    page_title="Monitor de Orçamento - Plataformas de Ads",
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
</style>
""", unsafe_allow_html=True)

class MonitorOrcamento:
    def __init__(self):
        self.plataformas_suportadas = ['Google Ads', 'Meta Ads', 'TikTok Ads', 'LinkedIn Ads']
        self.config_email = {}
        self.dados_planejamento = None
        
    def carregar_configuracoes_email(self):
        """Carrega as configurações de email do usuário"""
        st.sidebar.header("📧 Configurações de Email")
        
        self.config_email = {
            'smtp_server': st.sidebar.text_input("Servidor SMTP", "smtp.gmail.com"),
            'smtp_port': st.sidebar.number_input("Porta SMTP", 587, 2525, 587),
            'email_remetente': st.sidebar.text_input("Email Remetente"),
            'senha': st.sidebar.text_input("Senha do Email", type="password"),
            'email_destinatario': st.sidebar.text_input("Email Destinatário"),
            'assunto_padrao': st.sidebar.text_input("Assunto do Email", "ALERTA: Discrepância de Orçamento Detectada")
        }
        
        # Salvar configurações na sessão
        if st.sidebar.button("💾 Salvar Configurações"):
            st.session_state.config_email = self.config_email
            st.sidebar.success("Configurações salvas!")
    
    def carregar_planilha_planejamento(self):
        """Interface para carregar a planilha de planejamento"""
        st.header("📊 Carregar Planilha de Planejamento")
        
        uploaded_file = st.file_uploader(
            "Faça upload da planilha de planejamento (Excel ou CSV)",
            type=['xlsx', 'xls', 'csv'],
            key="planilha_planejamento"
        )
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    self.dados_planejamento = pd.read_csv(uploaded_file)
                else:
                    self.dados_planejamento = pd.read_excel(uploaded_file)
                
                st.success(f"✅ Planilha carregada com sucesso! {len(self.dados_planejamento)} registros encontrados.")
                
                # Mostrar preview dos dados
                with st.expander("👀 Visualizar dados da planilha"):
                    st.dataframe(self.dados_planejamento.head(10))
                    
                return True
            except Exception as e:
                st.error(f"❌ Erro ao carregar planilha: {str(e)}")
                return False
        return False
    
    def processar_dados_plataforma(self, plataforma, arquivo):
        """Processa os dados de cada plataforma"""
        try:
            if arquivo.name.endswith('.csv'):
                df = pd.read_csv(arquivo)
            else:
                df = pd.read_excel(arquivo)
            
            # Mapeamento de colunas por plataforma
            mapeamento_colunas = {
                'Google Ads': {
                    'campanha': ['Campaign', 'Campanha', 'Campaign name'],
                    'orcamento_planejado': ['Budget', 'Orçamento', 'Budget amount'],
                    'gasto_atual': ['Cost', 'Custo', 'Spend', 'Gasto'],
                    'status': ['Status', 'Campaign status']
                },
                'Meta Ads': {
                    'campanha': ['Campaign name', 'Campanha', 'Campaign'],
                    'orcamento_planejado': ['Budget', 'Orçamento', 'Amount spent'],
                    'gasto_atual': ['Amount spent', 'Spend', 'Gasto', 'Cost'],
                    'status': ['Status', 'Campaign status']
                },
                'TikTok Ads': {
                    'campanha': ['Campaign name', 'Campanha'],
                    'orcamento_planejado': ['Budget', 'Orçamento'],
                    'gasto_atual': ['Spend', 'Gasto', 'Cost'],
                    'status': ['Status', 'Campaign status']
                },
                'LinkedIn Ads': {
                    'campanha': ['Campaign name', 'Campanha'],
                    'orcamento_planejado': ['Budget', 'Orçamento'],
                    'gasto_atual': ['Spend', 'Gasto', 'Cost'],
                    'status': ['Status', 'Campaign status']
                }
            }
            
            # Encontrar colunas correspondentes
            colunas_mapeadas = {}
            for col_alvo, possiveis_nomes in mapeamento_colunas[plataforma].items():
                for nome in possiveis_nomes:
                    if nome in df.columns:
                        colunas_mapeadas[col_alvo] = nome
                        break
            
            if not colunas_mapeadas:
                st.warning(f"⚠️ Não foi possível mapear as colunas para {plataforma}")
                return None
            
            # Criar DataFrame padronizado
            df_processado = df[list(colunas_mapeadas.values())].copy()
            df_processado.columns = list(colunas_mapeadas.keys())
            df_processado['plataforma'] = plataforma
            
            # Converter colunas numéricas
            colunas_numericas = ['orcamento_planejado', 'gasto_atual']
            for col in colunas_numericas:
                if col in df_processado.columns:
                    df_processado[col] = pd.to_numeric(df_processado[col], errors='coerce')
            
            return df_processado
            
        except Exception as e:
            st.error(f"❌ Erro ao processar {plataforma}: {str(e)}")
            return None
    
    def comparar_orcamentos(self, dados_plataformas):
        """Compara os orçamentos planejados com os gastos atuais"""
        alertas = []
        
        for plataforma, df in dados_plataformas.items():
            if df is None or df.empty:
                continue
                
            for _, row in df.iterrows():
                campanha = row.get('campanha', 'N/A')
                orcamento_planejado = row.get('orcamento_planejado', 0)
                gasto_atual = row.get('gasto_atual', 0)
                status = row.get('status', 'Ativa')
                
                # Ignorar campanhas pausadas ou inativas
                if status and isinstance(status, str) and any(palavra in status.lower() for palavra in ['pausada', 'inativa', 'paused', 'inactive']):
                    continue
                
                if pd.isna(orcamento_planejado) or pd.isna(gasto_atual):
                    continue
                
                # Verificar discrepâncias
                if orcamento_planejado > 0:
                    percentual_gasto = (gasto_atual / orcamento_planejado) * 100
                    
                    # Alertas baseados em thresholds
                    if percentual_gasto > 110:  # Gastou mais de 110% do orçamento
                        alertas.append({
                            'tipo': 'CRÍTICO',
                            'plataforma': plataforma,
                            'campanha': campanha,
                            'orcamento_planejado': orcamento_planejado,
                            'gasto_atual': gasto_atual,
                            'percentual': percentual_gasto,
                            'mensagem': f'GASTO EXCEDIDO: {percentual_gasto:.1f}% do orçamento'
                        })
                    elif percentual_gasto > 95:  # Próximo do limite
                        alertas.append({
                            'tipo': 'ALERTA',
                            'plataforma': plataforma,
                            'campanha': campanha,
                            'orcamento_planejado': orcamento_planejado,
                            'gasto_atual': gasto_atual,
                            'percentual': percentual_gasto,
                            'mensagem': f'PRÓXIMO DO LIMITE: {percentual_gasto:.1f}% do orçamento'
                        })
                    elif percentual_gasto < 50 and gasto_atual > 0:  # Baixo gasto
                        alertas.append({
                            'tipo': 'BAIXO_GASTO',
                            'plataforma': plataforma,
                            'campanha': campanha,
                            'orcamento_planejado': orcamento_planejado,
                            'gasto_atual': gasto_atual,
                            'percentual': percentual_gasto,
                            'mensagem': f'BAIXO GASTO: Apenas {percentual_gasto:.1f}% do orçamento utilizado'
                        })
        
        return alertas
    
    def enviar_email_alerta(self, alertas):
        """Envia email de alerta"""
        if not self.config_email or not alertas:
            return False
        
        try:
            # Configurar servidor SMTP
            server = smtplib.SMTP(self.config_email['smtp_server'], self.config_email['smtp_port'])
            server.starttls()
            server.login(self.config_email['email_remetente'], self.config_email['senha'])
            
            # Criar mensagem
            msg = MIMEMultipart()
            msg['From'] = self.config_email['email_remetente']
            msg['To'] = self.config_email['email_destinatario']
            msg['Subject'] = self.config_email['assunto_padrao']
            
            # Corpo do email
            corpo_email = """
            <h2>🚨 Alertas de Orçamento - Plataformas de Ads</h2>
            <p>Foram detectadas discrepâncias nos orçamentos das campanhas:</p>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f2f2f2;">
                    <th>Plataforma</th>
                    <th>Campanha</th>
                    <th>Orçamento Planejado</th>
                    <th>Gasto Atual</th>
                    <th>Percentual</th>
                    <th>Status</th>
                </tr>
            """
            
            for alerta in alertas:
                cor_status = "#ff4444" if alerta['tipo'] == 'CRÍTICO' else "#ff8800" if alerta['tipo'] == 'ALERTA' else "#ffbb33"
                corpo_email += f"""
                <tr>
                    <td>{alerta['plataforma']}</td>
                    <td>{alerta['campanha']}</td>
                    <td>R$ {alerta['orcamento_planejado']:,.2f}</td>
                    <td>R$ {alerta['gasto_atual']:,.2f}</td>
                    <td>{alerta['percentual']:.1f}%</td>
                    <td style="color: {cor_status}; font-weight: bold;">{alerta['mensagem']}</td>
                </tr>
                """
            
            corpo_email += f"""
            </table>
            <br>
            <p><strong>Total de alertas:</strong> {len(alertas)}</p>
            <p><em>Este é um alerta automático do Sistema de Monitoramento de Orçamento.</em></p>
            """
            
            msg.attach(MIMEText(corpo_email, 'html'))
            
            # Enviar email
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            st.error(f"❌ Erro ao enviar email: {str(e)}")
            return False
    
    def mostrar_dashboard(self, dados_plataformas, alertas):
        """Mostra o dashboard com métricas e alertas"""
        st.header("📈 Dashboard de Monitoramento")
        
        # Métricas gerais
        col1, col2, col3, col4 = st.columns(4)
        
        total_campanhas = sum(len(df) for df in dados_plataformas.values() if df is not None)
        total_alertas = len(alertas)
        alertas_criticos = len([a for a in alertas if a['tipo'] == 'CRÍTICO'])
        plataformas_ativas = len([p for p, df in dados_plataformas.items() if df is not None and not df.empty])
        
        with col1:
            st.metric("Total de Campanhas", total_campanhas)
        with col2:
            st.metric("Alertas Totais", total_alertas)
        with col3:
            st.metric("Alertas Críticos", alertas_criticos, delta=f"-{alertas_criticos}" if alertas_criticos > 0 else None)
        with col4:
            st.metric("Plataformas Ativas", plataformas_ativas)
        
        # Mostrar alertas
        if alertas:
            st.header("🚨 Alertas Detectados")
            
            # Filtrar alertas por tipo
            tab1, tab2, tab3 = st.tabs(["🔴 Críticos", "🟡 Alertas", "🔵 Baixo Gasto"])
            
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
                    st.info("✅ Nenhum alerta crítico detectado")
            
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
                    st.info("✅ Nenhum alerta de proximidade detectado")
            
            with tab3:
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
                    st.info("✅ Nenhum caso de baixo gasto detectado")
            
            # Botão para enviar alertas por email
            if self.config_email.get('email_remetente') and self.config_email.get('email_destinatario'):
                if st.button("📧 Enviar Alertas por Email", type="primary"):
                    if self.enviar_email_alerta(alertas):
                        st.success("✅ Email enviado com sucesso!")
                    else:
                        st.error("❌ Falha ao enviar email")
        else:
            st.markdown("""
            <div class="success-box">
                <h3>✅ Tudo sob controle!</h3>
                <p>Nenhuma discrepância de orçamento foi detectada nas plataformas monitoradas.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Mostrar dados por plataforma
        st.header("📋 Dados por Plataforma")
        
        for plataforma, df in dados_plataformas.items():
            if df is not None and not df.empty:
                with st.expander(f"{plataforma} ({len(df)} campanhas)"):
                    st.dataframe(df, use_container_width=True)
    
    def executar_monitoramento(self):
        """Executa o processo completo de monitoramento"""
        st.markdown('<div class="main-header">💰 Monitor de Orçamento - Plataformas de Ads</div>', unsafe_allow_html=True)
        
        # Carregar configurações
        self.carregar_configuracoes_email()
        
        # Carregar planilha de planejamento
        if not self.carregar_planilha_planejamento():
            return
        
        st.header("🔄 Carregar Dados das Plataformas")
        
        dados_plataformas = {}
        
        # Interface para cada plataforma
        tabs = st.tabs(self.plataformas_suportadas)
        
        for i, plataforma in enumerate(self.plataformas_suportadas):
            with tabs[i]:
                st.subheader(f"Dados da {plataforma}")
                
                uploaded_file = st.file_uploader(
                    f"Faça upload do relatório da {plataforma}",
                    type=['xlsx', 'xls', 'csv'],
                    key=f"upload_{plataforma}"
                )
                
                if uploaded_file is not None:
                    with st.spinner(f"Processando {plataforma}..."):
                        df_processado = self.processar_dados_plataforma(plataforma, uploaded_file)
                        
                        if df_processado is not None:
                            dados_plataformas[plataforma] = df_processado
                            st.success(f"✅ {plataforma} processada: {len(df_processado)} campanhas")
                            
                            # Mostrar preview
                            with st.expander(f"Visualizar dados da {plataforma}"):
                                st.dataframe(df_processado.head(), use_container_width=True)
                        else:
                            st.error(f"❌ Falha ao processar {plataforma}")
        
        # Executar comparação se houver dados
        if dados_plataformas:
            st.header("🔍 Executar Análise")
            
            if st.button("🔄 Executar Verificação de Orçamentos", type="primary"):
                with st.spinner("Analisando orçamentos..."):
                    alertas = self.comparar_orcamentos(dados_plataformas)
                    self.mostrar_dashboard(dados_plataformas, alertas)
                    
                    # Salvar resultados na sessão
                    st.session_state.ultima_analise = {
                        'dados_plataformas': dados_plataformas,
                        'alertas': alertas,
                        'timestamp': datetime.now()
                    }
        else:
            st.warning("⚠️ Carregue pelo menos uma plataforma para executar a análise")

def main():
    # Inicializar o monitor
    monitor = MonitorOrcamento()
    
    # Sidebar com informações
    st.sidebar.header("ℹ️ Sobre o Sistema")
    st.sidebar.info("""
    Este sistema monitora automaticamente os orçamentos das campanhas 
    em diferentes plataformas de ads e alerta sobre discrepâncias.
    
    **Funcionalidades:**
    - ✅ Comparação com planilha de planejamento
    - 📧 Alertas automáticos por email
    - 📊 Dashboard interativo
    - 🔄 Suporte a múltiplas plataformas
    """)
    
    # Executar o monitoramento
    monitor.executar_monitoramento()

if __name__ == "__main__":
    main()
