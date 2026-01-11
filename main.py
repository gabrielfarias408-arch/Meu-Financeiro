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

def salvar_categorias(dic):
    max_len = max(len(v) for v in dic.values())
    dic_pad = {k: v + [None]*(max_len - len(v)) for k, v in dic.items()}
    pd.DataFrame(dic_pad).to_csv("categorias.csv", index=False)

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- INICIALIZAÇÃO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'edit_index' not in st.session_state: st.session_state['edit_index'] = None
if 'form_id' not in st.session_state: st.session_state['form_id'] = 0

# --- TELA DE LOGIN SEGURA ---
if not st.session_state['logado']:
    st.title("🔒 My Finance Pro - Acesso")
    col_l, _ = st.columns([1, 2])
    
    # Busca a senha no Secrets do Streamlit, usa "1234" se não estiver configurado
    try:
        senha_mestra = st.secrets["password"]
    except:
        senha_mestra = "1234"
        
    senha_digitada = col_l.text_input("Senha do Sistema:", type="password")
    if col_l.button("Acessar"):
        if senha_digitada == senha_mestra:
            st.session_state['logado'] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
else:
    # --- APP PRINCIPAL ---
    dados_total = carregar_dados()
    cats = carregar_categorias()

    # --- BARRA LATERAL ---
    st.sidebar.header("📅 Período de Referência")
    hoje = date.today()
    anos_disp = sorted(pd.to_datetime(dados_total['Data']).dt.year.unique(), reverse=True) if not dados_total.empty else [hoje.year]
    if hoje.year not in anos_disp: anos_disp.insert(0, hoje.year)
    
    ano_sel = st.sidebar.selectbox("Ano", anos_disp)
    meses_lista = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    mes_sel_nome = st.sidebar.selectbox("Mês", meses_lista, index=hoje.month - 1)
    mes_sel_idx = meses_lista.index(mes_sel_nome) + 1

    dados_total['_orig_index'] = dados_total.index
    dados_mes = dados_total[
        (pd.to_datetime(dados_total['Data']).dt.month == mes_sel_idx) & 
        (pd.to_datetime(dados_total['Data']).dt.year == ano_sel)
    ].copy()

    aba_reg, aba_dash, aba_inv = st.tabs(["📝 Lançamentos", "📊 Dashboard Analítico", "🎯 Metas"])

    # --- ABA 1: LANÇAMENTOS ---
    with aba_reg:
        st.subheader(f"Movimentações de {mes_sel_nome}/{ano_sel}")
        if st.session_state['edit_index'] is not None and st.session_state['edit_index'] in dados_total.index:
            row = dados_total.loc[st.session_state['edit_index']]
            v_tipo, v_desc, v_valor, v_data, v_cat = row['Tipo'], row['Item'], f"{abs(float(row['Valor'])):.2f}".replace(".", ","), row['Data'], row['Categoria']
            st.warning(f"🔧 Editando: {v_desc}")
        else:
            st.session_state['edit_index'] = None
            try: d_padrao = date(ano_sel, mes_sel_idx, hoje.day if ano_sel == hoje.year and mes_sel_idx == hoje.month else 1)
            except: d_padrao = date(ano_sel, mes_sel_idx, 1)
            v_tipo, v_desc, v_valor, v_data, v_cat = "---", "", "", d_padrao, "Selecione..."

        with st.container(border=True):
            f1, f2, f3, f4 = st.columns([1, 2, 1, 1])
            tipo_s = f1.selectbox("Tipo", ["---", "Saída", "Entrada", "Investimento"], index=["---", "Saída", "Entrada", "Investimento"].index(v_tipo), key=f"t_{st.session_state['form_id']}")
            item_s = f2.text_input("Descrição", value=v_desc, key=f"i_{st.session_state['form_id']}")
            valor_s = f3.text_input("Valor (R$)", value=v_valor, key=f"v_{st.session_state['form_id']}")
            data_s = f4.date_input("Data", value=v_data, format="DD/MM/YYYY", key=f"d_{st.session_state['form_id']}")
            col_cat, col_ncat = st.columns([3, 1])
            opcoes_cat = cats.get(tipo_s, ["Selecione..."])
            cat_s = col_cat.selectbox("Categoria", opcoes_cat, index=opcoes_cat.index(v_cat) if v_cat in opcoes_cat else 0, key=f"c_{st.session_state['form_id']}")
            n_cat_in = col_ncat.text_input("Nova Cat.", key=f"nc_{st.session_state['form_id']}")

            if st.button("💾 Salvar Registro", use_container_width=True, key=f"sv_{st.session_state['form_id']}"):
                try:
                    v_num = float(valor_s.replace(".", "").replace(",", "."))
                    v_f = -v_num if tipo_s in ["Saída", "Investimento"] else v_num
                    cat_f = n_cat_in if n_cat_in else cat_s
                    if st.session_state['edit_index'] is not None:
                        dados_total.loc[st.session_state['edit_index'], ["Data", "Tipo", "Item", "Categoria", "Valor"]] = [data_s, tipo_s, item_s, cat_f, v_f]
                        st.session_state['edit_index'] = None
                    else:
                        dados_total = pd.concat([dados_total, pd.DataFrame([{"Data": data_s, "Tipo": tipo_s, "Item": item_s, "Categoria": cat_f, "Valor": v_f}])], ignore_index=True)
                    if n_cat_in and tipo_s != "---":
                        if n_cat_in not in cats[tipo_s]:
                            cats[tipo_s].append(n_cat_in); salvar_categorias(cats)
                    salvar_dados(dados_total); st.session_state['form_id'] += 1; st.rerun()
                except: st.error("Erro no valor. Use apenas números e vírgula.")

        st.divider()
        if not dados_mes.empty:
            for _, r in dados_mes.sort_values(by='Data', ascending=False).iterrows():
                idx = r['_orig_index']
                col = st.columns([1.2, 1, 2.5, 2, 1.5, 0.8])
                col[0].write(r['Data'].strftime('%d/%m/%Y'))
                col[1].write(r['Tipo']); col[2].write(r['Item']); col[3].write(r['Categoria'])
                cor = "green" if r['Valor'] > 0 else "red"
                col[4].markdown(f":{cor}[{formatar_moeda(r['Valor'])}]")
                be, bd = col[5].columns(2)
                if be.button("✏️", key=f"e_{idx}_{st.session_state['form_id']}"): st.session_state['edit_index'] = idx; st.rerun()
                if bd.button("🗑️", key=f"d_{idx}_{st.session_state['form_id']}"): 
                    dados_total = dados_total.drop(index=idx).reset_index(drop=True); salvar_dados(dados_total); st.rerun()

    # --- ABA 2: DASHBOARD ANALÍTICO ---
    with aba_dash:
        c_t, c_f = st.columns([3, 1])
        c_t.header("📊 Análise de Performance")
        modo_v = c_f.radio("Visão:", ["Mensal", "Acumulado Ano"], horizontal=True, key="v_global")

        if modo_v == "Mensal":
            df_dash = dados_mes.copy()
            txt_p = f"em {mes_sel_nome}"
        else:
            df_dash = dados_total[(pd.to_datetime(dados_total['Data']).dt.year == ano_sel) & (pd.to_datetime(dados_total['Data']).dt.month <= mes_sel_idx)].copy()
            txt_p = f"Acumulado até {mes_sel_nome}"

        if not df_dash.empty:
            st.divider()
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                df_sai = df_dash[df_dash['Tipo'] == "Saída"]
                if not df_sai.empty:
                    st.plotly_chart(px.pie(df_sai, values=abs(df_sai['Valor']), names='Categoria', title=f"Distribuição de Gastos ({modo_v})", hole=0.4), use_container_width=True)

            with col_g2:
                df_tipo = df_dash.groupby('Tipo')['Valor'].sum().abs().reset_index()
                df_tipo.columns = ['Tipo de Movimentação', 'Total Financeiro']
                df_tipo = df_tipo.sort_values(by='Total Financeiro', ascending=False)

                fig_tipo = px.bar(df_tipo, x='Tipo de Movimentação', y='Total Financeiro', color='Tipo de Movimentação', text='Total Financeiro', title=f"Expressão Financeira {txt_p}")
                fig_tipo.update_layout(xaxis={'categoryorder':'total descending'})
                fig_tipo.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
                st.plotly_chart(fig_tipo, use_container_width=True)

            st.divider()
            st.subheader(f"🏆 Top 5 Categorias de Gastos ({txt_p})")
            df_rank_cat = df_dash[df_dash['Tipo'] == "Saída"].copy()
            if not df_rank_cat.empty:
                df_rank = df_rank_cat.groupby('Categoria')['Valor'].sum().abs().reset_index()
                df_rank = df_rank.sort_values(by='Valor', ascending=False).head(5)
                fig_rank = px.bar(df_rank, x='Valor', y='Categoria', orientation='h', text='Valor', color='Categoria')
                fig_rank.update_layout(yaxis={'categoryorder':'total ascending'})
                fig_rank.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
                st.plotly_chart(fig_rank, use_container_width=True)
            else: st.info("Nenhuma saída registrada para gerar o ranking.")
        else:
            st.info("Nenhum dado encontrado para este período.")

    # --- ABA 3: METAS ---
    with aba_inv:
        st.header("🎯 Reserva de Emergência")
        total_r = abs(dados_total[dados_total['Categoria'] == "Reserva de Emergência"]['Valor'].sum())
        meta = 30000
        progresso = min(total_r/meta, 1.0)
        st.progress(progresso)
        st.write(f"**Progresso:** {progresso*100:.1f}%")
        st.caption(f"Saldo atual: {formatar_moeda(total_r)} de {formatar_moeda(meta)}")
