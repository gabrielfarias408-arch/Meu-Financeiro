import streamlit as st
import pandas as pd
import plotly.express as px
import os
import hashlib
import calendar
from datetime import datetime, date

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="My Finance Pro", layout="wide", page_icon="💰")

# --- FUNÇÕES DE SEGURANÇA ---
def gerar_hash(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

def verificar_login(email_input, senha_input):
    if os.path.exists("usuarios.csv"):
        df_users = pd.read_csv("usuarios.csv")
        user_row = df_users[df_users['email'] == email_input]
        if not user_row.empty:
            if gerar_hash(senha_input) == user_row.iloc[0]['senha']:
                if user_row.iloc[0]['aprovado']:
                    return True, "Sucesso"
                return False, "Usuário aguardando aprovação."
            return False, "Senha incorreta."
    return False, "E-mail não encontrado ou erro no arquivo."

# --- FUNÇÕES DE DADOS ---
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
        "Entrada": ["Selecione...", "Salário", "Pró-labore", "Rendimento"],
        "Saída": ["Selecione...", "Alimentação", "Aluguel", "Internet", "Lazer", "Saúde"],
        "Investimento": ["Selecione...", "Ações", "FIIs", "Reserva de Emergência"]
    }

def salvar_dados(df):
    df.drop(columns=['_orig_index'], errors='ignore').to_csv("financas.csv", index=False)

def salvar_categorias(dic):
    max_len = max(len(v) for v in dic.values())
    dic_pad = {k: v + [None]*(max_len - len(v)) for k, v in dic.items()}
    pd.DataFrame(dic_pad).to_csv("categorias.csv", index=False)

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'edit_index' not in st.session_state: st.session_state['edit_index'] = None
if 'form_id' not in st.session_state: st.session_state['form_id'] = 0

# --- TELA DE LOGIN ---
if not st.session_state['logado']:
    st.title("🔒 My Finance Pro - Acesso")
    col_l, _ = st.columns([1, 2])
    with col_l:
        email_log = st.text_input("E-mail")
        senha_log = st.text_input("Senha", type="password")
        if st.button("Acessar Sistema", use_container_width=True):
            sucesso, msg = verificar_login(email_log, senha_log)
            if sucesso:
                st.session_state['logado'] = True
                st.session_state['usuario_atual'] = email_log
                st.rerun()
            else:
                st.error(msg)
else:
    # --- ÁREA LOGADA ---
    dados_total = carregar_dados()
    cats = carregar_categorias()

    # Barra Lateral
    st.sidebar.title("💰 My Finance Pro")
    st.sidebar.write(f"Conectado: **{st.session_state['usuario_atual']}**")
    if st.sidebar.button("🚪 Sair"):
        st.session_state['logado'] = False
        st.rerun()

    st.sidebar.divider()
    hoje = date.today()
    anos_disp = sorted(pd.to_datetime(dados_total['Data']).dt.year.unique(), reverse=True) if not dados_total.empty else [hoje.year]
    if hoje.year not in anos_disp: anos_disp.insert(0, hoje.year)
    
    ano_sel = st.sidebar.selectbox("Ano", anos_disp)
    meses_lista = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    mes_sel_nome = st.sidebar.selectbox("Mês", meses_lista, index=hoje.month - 1)
    mes_sel_idx = meses_lista.index(mes_sel_nome) + 1

    # Filtragem de Dados
    dados_total['_orig_index'] = dados_total.index
    dados_mes = dados_total[
        (pd.to_datetime(dados_total['Data']).dt.month == mes_sel_idx) & 
        (pd.to_datetime(dados_total['Data']).dt.year == ano_sel)
    ].copy()

    aba_reg, aba_dash, aba_inv = st.tabs(["📝 Lançamentos", "📊 Dashboard", "🎯 Metas"])

    with aba_reg:
        # --- MELHORIA 2: CARDS DE RESUMO VISUAL ---
        total_entradas = dados_mes[dados_mes['Tipo'] == "Entrada"]['Valor'].sum()
        total_saidas = abs(dados_mes[dados_mes['Tipo'] == "Saída"]['Valor'].sum())
        total_invest = abs(dados_mes[dados_mes['Tipo'] == "Investimento"]['Valor'].sum())
        saldo_liq = total_entradas - total_saidas - total_invest

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Receitas", formatar_moeda(total_entradas))
        c2.metric("Despesas", formatar_moeda(total_saidas), delta_color="inverse")
        c3.metric("Investido", formatar_moeda(total_invest))
        c4.metric("Saldo Líquido", formatar_moeda(saldo_liq), delta=saldo_liq)
        
        st.divider()

        # --- FORMULÁRIO DE LANÇAMENTO ---
        if st.session_state['edit_index'] is not None:
            row = dados_total.loc[st.session_state['edit_index']]
            v_tipo, v_desc, v_valor, v_data, v_cat = row['Tipo'], row['Item'], abs(float(row['Valor'])), row['Data'], row['Categoria']
            st.warning(f"🔧 Editando: {v_desc}")
        else:
            v_tipo, v_desc, v_valor, v_data, v_cat = "---", "", 0.0, date(ano_sel, mes_sel_idx, 1), "Selecione..."

        with st.container(border=True):
            f1, f2, f3, f4 = st.columns([1.2, 2, 1.2, 1.2])
            tipo_s = f1.selectbox("Tipo", ["---", "Saída", "Entrada", "Investimento"], index=["---", "Saída", "Entrada", "Investimento"].index(v_tipo), key=f"t_{st.session_state['form_id']}")
            item_s = f2.text_input("Descrição", value=v_desc, placeholder="Ex: Aluguel", key=f"i_{st.session_state['form_id']}")
            
            # --- MELHORIA 1: INPUT DE VALOR NUMÉRICO ---
            valor_num = f3.number_input("Valor (R$)", min_value=0.0, value=v_valor, format="%.2f", step=10.0, key=f"v_{st.session_state['form_id']}")
            
            # --- MELHORIA 4: DATA TRAVADA NO MÊS ---
            u_dia = calendar.monthrange(ano_sel, mes_sel_idx)[1]
            data_s = f4.date_input("Data", value=v_data, min_value=date(ano_sel, mes_sel_idx, 1), max_value=date(ano_sel, mes_sel_idx, u_dia), format="DD/MM/YYYY", key=f"d_{st.session_state['form_id']}")
            
            col_cat, col_ncat = st.columns([3, 1])
            op_cat = cats.get(tipo_s, ["Selecione..."])
            cat_s = col_cat.selectbox("Categoria", op_cat, index=op_cat.index(v_cat) if v_cat in op_cat else 0, key=f"c_{st.session_state['form_id']}")
            n_cat_in = col_ncat.text_input("Nova Cat.", key=f"nc_{st.session_state['form_id']}")

            if st.button("💾 Salvar Registro", use_container_width=True):
                if tipo_s != "---" and item_s != "" and valor_num > 0:
                    v_final = -valor_num if tipo_s in ["Saída", "Investimento"] else valor_num
                    c_final = n_cat_in if n_cat_in else cat_s
                    
                    if st.session_state['edit_index'] is not None:
                        dados_total.loc[st.session_state['edit_index'], ["Data", "Tipo", "Item", "Categoria", "Valor"]] = [data_s, tipo_s, item_s, c_final, v_final]
                        st.session_state['edit_index'] = None
                    else:
                        dados_total = pd.concat([dados_total, pd.DataFrame([{"Data": data_s, "Tipo": tipo_s, "Item": item_s, "Categoria": c_final, "Valor": v_final}])], ignore_index=True)
                    
                    if n_cat_in and n_cat_in not in cats.get(tipo_s, []):
                        cats[tipo_s].append(n_cat_in); salvar_categorias(cats)
                    
                    salvar_dados(dados_total); st.session_state['form_id'] += 1; st.rerun()
                else:
                    st.error("Preencha Tipo, Descrição e Valor.")

        # --- MELHORIA 3: ESTÉTICA DA TABELA ---
        st.subheader("📋 Detalhamento")
        if not dados_mes.empty:
            for _, r in dados_mes.sort_values(by='Data', ascending=False).iterrows():
                with st.container(border=False):
                    col = st.columns([1, 1, 2.5, 2, 1.5, 0.8])
                    col[0].write(f"**{r['Data'].strftime('%d/%m')}**")
                    col[1].caption(r['Tipo'])
                    col[2].write(r['Item'])
                    col[3].write(f"🏷️ {r['Categoria']}")
                    cor = "green" if r['Valor'] > 0 else "red"
                    col[4].markdown(f":{cor}[**{formatar_moeda(r['Valor'])}**]")
                    
                    be, bd = col[5].columns(2)
                    if be.button("✏️", key=f"e_{r['_orig_index']}_{st.session_state['form_id']}"):
                        st.session_state['edit_index'] = r['_orig_index']; st.rerun()
                    if bd.button("🗑️", key=f"d_{r['_orig_index']}_{st.session_state['form_id']}"):
                        dados_total = dados_total.drop(index=r['_orig_index']).reset_index(drop=True); salvar_dados(dados_total); st.rerun()
                st.divider()
        else:
            st.info("Nenhum lançamento encontrado neste período.")

    with aba_dash:
        if not dados_mes.empty:
            col_g1, col_g2 = st.columns(2)
            df_sai = dados_mes[dados_mes['Tipo'] == "Saída"]
            if not df_sai.empty:
                fig_pie = px.pie(df_sai, values=abs(df_sai['Valor']), names='Categoria', title="Gastos por Categoria", hole=0.4)
                col_g1.plotly_chart(fig_pie, use_container_width=True)
            
            df_tipo = dados_mes.groupby('Tipo')['Valor'].sum().abs().reset_index()
            fig_bar = px.bar(df_tipo, x='Tipo', y='Valor', color='Tipo', title="Entradas vs Saídas", text_auto='.2f')
            col_g2.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Dados insuficientes para gráficos.")

    with aba_inv:
        st.header("📈 Metas e Reserva")
        reserva = abs(dados_total[dados_total['Categoria'] == "Reserva de Emergência"]['Valor'].sum())
        meta = 30000.0
        st.write(f"Reserva de Emergência: **{formatar_moeda(reserva)}**")
        st.progress(min(reserva/meta, 1.0))
        st.caption(f"Meta de R$ 30.000,00 (Alcançado: {reserva/meta:.1%})")



