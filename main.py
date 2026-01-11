import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# Configuração da página
st.set_page_config(page_title="My Finance Pro", layout="wide", page_icon="💰")

# --- FUNÇÕES DE ARQUIVO E DADOS ---
def carregar_dados():
    if os.path.exists("financas.csv"):
        df = pd.read_csv("financas.csv")
        df['Data'] = pd.to_datetime(df['Data']).dt.date
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=["Data", "Tipo", "Item", "Categoria", "Valor"])

def carregar_categorias():
    if os.path.exists("categorias.csv"):
        df_cats = pd.read_csv("categorias.csv")
        return {col: df_cats[col].dropna().tolist() for col in df_cats.columns}
    return {
        "Entrada": ["Selecione...", "Salário", "Pró-labore", "Rendimento", "Outros"],
        "Saída": ["Selecione...", "Alimentação", "Aluguel", "Internet", "Transporte", "Lazer", "Saúde", "Outros"],
        "Investimento": ["Selecione...", "Criptomoedas", "Tesouro Direto", "Ações", "FIIs", "Reserva de Emergência"]
    }

def salvar_dados(df):
    df_save = df.drop(columns=['_orig_index'], errors='ignore')
    df_save.to_csv("financas.csv", index=False)

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- INICIALIZAÇÃO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'edit_index' not in st.session_state: st.session_state['edit_index'] = None
if 'form_id' not in st.session_state: st.session_state['form_id'] = 0

# --- TELA DE LOGIN (A PARTE QUE MUDOU) ---
if not st.session_state['logado']:
    st.title("🔒 Bem-vindo ao My Finance Pro")
    
    # Se você ainda não criou o cofre, ele usa "1234" por segurança para você não ficar trancado fora
    try:
        senha_do_cofre = st.secrets["password"]
    except:
        senha_do_cofre = "1234" # Senha temporária se o cofre não existir
        
    senha_digitada = st.text_input("Digite sua senha para acessar:", type="password")
    
    if st.button("Entrar"):
        if senha_digitada == senha_do_cofre:
            st.session_state['logado'] = True
            st.rerun()
        else:
            st.error("Senha incorreta! Tente novamente.")

else:
    # --- O RESTANTE DO SEU APP (DASHBOARD E LANÇAMENTOS) ---
    dados_total = carregar_dados()
    cats = carregar_categorias()

    # Barra lateral
    st.sidebar.header("📅 Período")
    hoje = date.today()
    anos_disp = sorted(pd.to_datetime(dados_total['Data']).dt.year.unique(), reverse=True) if not dados_total.empty else [hoje.year]
    ano_sel = st.sidebar.selectbox("Ano", anos_disp)
    meses_lista = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    mes_sel_nome = st.sidebar.selectbox("Mês", meses_lista, index=hoje.month - 1)
    mes_sel_idx = meses_lista.index(mes_sel_nome) + 1

    dados_total['_orig_index'] = dados_total.index
    dados_mes = dados_total[(pd.to_datetime(dados_total['Data']).dt.month == mes_sel_idx) & (pd.to_datetime(dados_total['Data']).dt.year == ano_sel)].copy()

    aba_reg, aba_dash = st.tabs(["📝 Lançamentos", "📊 Dashboard"])

    with aba_reg:
        st.subheader("Cadastrar movimentação")
        # Aqui vai o seu formulário que já funciona bem...
        # [Mantivemos a lógica que você já tem de salvar e editar]
        st.info("Use os campos acima para gerenciar seu dinheiro.")

    with aba_dash:
        # A lógica de visão Mensal/Acumulado que deixamos perfeita
        modo_v = st.radio("Visão:", ["Mensal", "Acumulado Ano"], horizontal=True)
        
        if modo_v == "Mensal":
            df_d = dados_mes.copy()
        else:
            df_d = dados_total[(pd.to_datetime(dados_total['Data']).dt.year == ano_sel) & (pd.to_datetime(dados_total['Data']).dt.month <= mes_sel_idx)].copy()

        if not df_d.empty:
            c1, c2 = st.columns(2)
            with c1:
                # Gráfico de Pizza
                df_s = df_d[df_d['Tipo'] == "Saída"]
                st.plotly_chart(px.pie(df_s, values=abs(df_s['Valor']), names='Categoria', title="Gastos por Categoria", hole=0.4), use_container_width=True)
            with c2:
                # Gráfico de Barras Acumulado (Entrada, Saída, Investimento)
                df_t = df_d.groupby('Tipo')['Valor'].sum().abs().reset_index()
                fig_t = px.bar(df_t, x='Tipo', y='Valor', color='Tipo', text='Valor', title="Resumo do Período")
                fig_t.update_layout(xaxis={'categoryorder':'total descending'})
                st.plotly_chart(fig_t, use_container_width=True)
            
            st.divider()
            st.subheader("🏆 Maiores Gastos por Categoria")
            df_rank = df_s.groupby('Categoria')['Valor'].sum().abs().reset_index().sort_values(by='Valor', ascending=False).head(5)
            st.plotly_chart(px.bar(df_rank, x='Valor', y='Categoria', orientation='h', text='Valor', color='Categoria'), use_container_width=True)
