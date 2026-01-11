import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# 1. CONFIGURAÇÃO DE PÁGINA INTELIGENTE
st.set_page_config(
    page_title="My Finance Pro", 
    layout="wide", 
    page_icon="💰",
    initial_sidebar_state="collapsed" # Melhora a experiência no celular ao abrir
)

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
        "Entrada": ["Salário", "Pró-labore", "Rendimento", "Outros"],
        "Saída": ["Alimentação", "Aluguel", "Internet", "Transporte", "Lazer", "Saúde", "Outros"],
        "Investimento": ["Criptomoedas", "Tesouro Direto", "Ações", "FIIs", "Reserva de Emergência"]
    }

def salvar_dados(df):
    df_save = df.drop(columns=['_orig_index'], errors='ignore')
    df_save.to_csv("financas.csv", index=False)

def formatar_moeda(valor):
    return f"R$ {abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- INICIALIZAÇÃO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'edit_index' not in st.session_state: st.session_state['edit_index'] = None

# --- SISTEMA DE SEGURANÇA (SENHA) ---
if not st.session_state['logado']:
    st.title("🔒 Acesso Restrito")
    try:
        senha_mestra = st.secrets["password"] # Busca P@nambi2026 no cofre
    except:
        senha_mestra = "1234" # Segurança para teste local
    
    senha_digitada = st.text_input("Senha do Sistema:", type="password")
    if st.button("Acessar App", use_container_width=True):
        if senha_digitada == senha_mestra:
            st.session_state['logado'] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
else:
    # --- APP PRINCIPAL ---
    dados_total = carregar_dados()
    cats = carregar_categorias()

    # Barra Lateral (Filtros de Data)
    st.sidebar.header("📅 Período")
    hoje = date.today()
    ano_sel = st.sidebar.selectbox("Ano", [2024, 2025, 2026], index=1)
    meses_n = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    mes_sel_nome = st.sidebar.selectbox("Mês", meses_n, index=hoje.month - 1)
    mes_sel_idx = meses_n.index(mes_sel_nome) + 1

    # ABAS (Nomes curtos para mobile)
    aba_reg, aba_dash, aba_meta = st.tabs(["📝 Lançar", "📊 Dashboard", "🎯 Metas"])

    with aba_reg:
        # FORMULÁRIO INTELIGENTE
        # O expander ajuda a economizar tela no celular
        titulo_form = "🔧 Editando Lançamento" if st.session_state['edit_index'] is not None else "➕ Novo Lançamento"
        with st.expander(titulo_form, expanded=(st.session_state['edit_index'] is not None)):
            if st.session_state['edit_index'] is not None:
                row = dados_total.loc[st.session_state['edit_index']]
                v_tipo, v_desc, v_valor, v_data, v_cat = row['Tipo'], row['Item'], abs(row['Valor']), row['Data'], row['Categoria']
            else:
                v_tipo, v_desc, v_valor, v_data, v_cat = "Saída", "", 0.0, hoje, "Alimentação"

            with st.form("form_financeiro"):
                # No celular, as colunas 1,1 se empilham perfeitamente
                col1, col2 = st.columns(2)
                tipo_f = col1.selectbox("Tipo", ["Saída", "Entrada", "Investimento"], index=["Saída", "Entrada", "Investimento"].index(v_tipo))
                data_f = col2.date_input("Data", v_data)
                
                desc_f = st.text_input("Descrição", value=v_desc)
                
                col3, col4 = st.columns(2)
                valor_f = col3.number_input("Valor (R$)", value=float(v_valor), step=0.01)
                lista_cat = cats.get(tipo_f, ["Outros"])
                cat_f = col4.selectbox("Categoria", lista_cat, index=lista_cat.index(v_cat) if v_cat in lista_cat else 0)

                if st.form_submit_button("Salvar Movimentação", use_container_width=True):
                    valor_final = -valor_f if tipo_f in ["Saída", "Investimento"] else valor_f
                    if st.session_state['edit_index'] is not None:
                        dados_total.loc[st.session_state['edit_index'], ["Data", "Tipo", "Item", "Categoria", "Valor"]] = [data_f, tipo_f, desc_f, cat_f, valor_final]
                        st.session_state['edit_index'] = None
                    else:
                        novo = pd.DataFrame([{"Data": data_f, "Tipo": tipo_f, "Item": desc_f, "Categoria": cat_f, "Valor": valor_final}])
                        dados_total = pd.concat([dados_total, novo], ignore_index=True)
                    salvar_dados(dados_total)
                    st.success("Salvo com sucesso!")
                    st.rerun()

        st.divider()
        # EXIBIÇÃO EM CARDS (Muito melhor para celular que tabelas)
        st.subheader("Registros Recentes")
        dados_total['_orig_index'] = dados_total.index
        df_mes = dados_total[
            (pd.to_datetime(dados_total['Data']).dt.month == mes_sel_idx) & 
            (pd.to_datetime(dados_total['Data']).dt.year == ano_sel)
        ].sort_values(by="Data", ascending=False)

        if df_mes.empty:
            st.info("Nenhum registro encontrado para este mês.")
        else:
            for i, r in df_mes.iterrows():
                with st.container(border=True): # Cria um "card"
                    c_info, c_acoes = st.columns([4, 1])
                    cor = "red" if r['Valor'] < 0 else "green"
                    c_info.markdown(f"**{r['Data'].strftime('%d/%m')} - {r['Item']}**")
                    c_info.caption(f"{r['Categoria']} | {r['Tipo']}")
                    c_info.markdown(f":{cor}[**{formatar_moeda(r['Valor'])}**]")
                    
                    # Botões de ação adaptados
                    idx = r['_orig_index']
                    b1, b2 = c_acoes.columns(2)
                    if b1.button("✏️", key=f"ed_{idx}"):
                        st.session_state['edit_index'] = idx
                        st.rerun()
                    if b2.button("🗑️", key=f"del_{idx}"):
                        dados_total = dados_total.drop(index=idx)
                        salvar_dados(dados_total)
                        st.rerun()

    with aba_dash:
        st.subheader("📊 Performance Financeira")
        modo = st.radio("Filtro do Dashboard:", ["Mensal", "Acumulado Ano"], horizontal=True)
        
        if modo == "Mensal":
            df_dash = df_mes.copy()
        else:
            df_dash = dados_total[pd.to_datetime(dados_total['Data']).dt.year == ano_sel]

        if not df_dash.empty:
            # MÉTRICAS RÁPIDAS (Lado a lado no PC, uma sob a outra no Celular)
            m1, m2, m3 = st.columns(3)
            ganhos = df_dash[df_dash['Tipo'] == "Entrada"]['Valor'].sum()
            gastos = abs(df_dash[df_dash['Tipo'] == "Saída"]['Valor'].sum())
            m1.metric("Ganhos", formatar_moeda(ganhos))
            m2.metric("Gastos", formatar_moeda(gastos))
            m3.metric("Saldo", formatar_moeda(ganhos - gastos))

            # GRÁFICOS RESPONSIVOS
            col_graf1, col_graf2 = st.columns([1, 1])
            
            with col_graf1:
                # Barras de Entradas vs Saídas
                resumo = df_dash.groupby('Tipo')['Valor'].sum().abs().reset_index()
                fig_bar = px.bar(resumo, x='Tipo', y='Valor', color='Tipo', title="Entradas vs Saídas", text_auto='.2s')
                st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})
            
            with col_graf2:
                # Pizza de Gastos
                df_sai = df_dash[df_dash['Tipo'] == "Saída"]
                if not df_sai.empty:
                    fig_pie = px.pie(df_sai, values=abs(df_sai['Valor']), names='Categoria', title="Divisão de Gastos", hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Adicione dados para ver os gráficos.")

    with aba_meta:
        st.subheader("🎯 Metas e Reservas")
        reserva = abs(dados_total[dados_total['Categoria'] == "Reserva de Emergência"]['Valor'].sum())
        meta_valor = 30000.0
        progresso = min(reserva / meta_valor, 1.0)
        
        st.write(f"**Reserva de Emergência**")
        st.progress(progresso)
        st.write(f"{progresso*100:.1f}% concluído ({formatar_moeda(reserva)} de {formatar_moeda(meta_valor)})")
