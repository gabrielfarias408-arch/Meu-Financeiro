import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# 1. Configuração de Página Otimizada
st.set_page_config(page_title="My Finance Pro", layout="wide", page_icon="💰", initial_sidebar_state="collapsed")

# --- FUNÇÕES DE ARQUIVO E DADOS (Mantendo sua lógica original) ---
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
    return f"R$ {abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- INICIALIZAÇÃO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'edit_index' not in st.session_state: st.session_state['edit_index'] = None
if 'form_id' not in st.session_state: st.session_state['form_id'] = 0

# --- SEGURANÇA INTELIGENTE ---
if not st.session_state['logado']:
    st.title("🔒 My Finance Pro - Acesso")
    try:
        senha_mestra = st.secrets["password"]
    except:
        senha_mestra = "1234" # Fallback para PC
    
    col_l, _ = st.columns([1, 2])
    senha = col_l.text_input("Senha do Sistema:", type="password")
    if col_l.button("Acessar", use_container_width=True):
        if senha == senha_mestra:
            st.session_state['logado'] = True
            st.rerun()
        else: st.error("Senha incorreta.")
else:
    dados_total = carregar_dados()
    cats = carregar_categorias()

    # --- BARRA LATERAL (Filtros) ---
    st.sidebar.header("📅 Período")
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

    # ABAS (Aba Inv renomeada para Metas)
    aba_reg, aba_dash, aba_inv = st.tabs(["📝 Lançar", "📊 Dashboard", "🎯 Metas"])

    # --- ABA 1: LANÇAMENTOS (Mobile Friendly) ---
    with aba_reg:
        st.subheader(f"Movimentos de {mes_sel_nome}/{ano_sel}")
        
        with st.expander("➕ Novo Lançamento / Editar", expanded=st.session_state['edit_index'] is not None):
            if st.session_state['edit_index'] is not None and st.session_state['edit_index'] in dados_total.index:
                row = dados_total.loc[st.session_state['edit_index']]
                v_tipo, v_desc, v_valor, v_data, v_cat = row['Tipo'], row['Item'], f"{abs(float(row['Valor'])):.2f}".replace(".", ","), row['Data'], row['Categoria']
                st.info(f"🔧 Editando: {v_desc}")
            else:
                try: d_padrao = date(ano_sel, mes_sel_idx, hoje.day if ano_sel == hoje.year and mes_sel_idx == hoje.month else 1)
                except: d_padrao = date(ano_sel, mes_sel_idx, 1)
                v_tipo, v_desc, v_valor, v_data, v_cat = "---", "", "", d_padrao, "Selecione..."

            # Formulario ajustado para colunas que empilham no celular
            with st.container():
                c1, c2 = st.columns(2)
                tipo_s = c1.selectbox("Tipo", ["---", "Saída", "Entrada", "Investimento"], index=["---", "Saída", "Entrada", "Investimento"].index(v_tipo), key=f"t_{st.session_state['form_id']}")
                data_s = c2.date_input("Data", value=v_data, format="DD/MM/YYYY", key=f"d_{st.session_state['form_id']}")
                
                item_s = st.text_input("Descrição", value=v_desc, key=f"i_{st.session_state['form_id']}")
                valor_s = st.text_input("Valor (R$)", value=v_valor, key=f"v_{st.session_state['form_id']}", placeholder="0,00")
                
                c3, c4 = st.columns([2, 1])
                opcoes_cat = cats.get(tipo_s, ["Selecione..."])
                cat_s = c3.selectbox("Categoria", opcoes_cat, index=opcoes_cat.index(v_cat) if v_cat in opcoes_cat else 0, key=f"c_{st.session_state['form_id']}")
                n_cat_in = c4.text_input("Nova Cat.", key=f"nc_{st.session_state['form_id']}")

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
                        
                        if n_cat_in and n_cat_in not in cats.get(tipo_s, []):
                            if tipo_s != "---":
                                cats[tipo_s].append(n_cat_in)
                                salvar_categorias(cats)
                        
                        salvar_dados(dados_total)
                        st.session_state['form_id'] += 1
                        st.rerun()
                    except: st.error("Por favor, insira um valor válido.")

        st.divider()
        # EXIBIÇÃO EM CARDS (Inteligência para Celular)
        if not dados_mes.empty:
            for _, r in dados_mes.sort_values(by='Data', ascending=False).iterrows():
                idx = r['_orig_index']
                with st.container(border=True):
                    col_txt, col_btn = st.columns([4, 1])
                    cor = "green" if r['Valor'] > 0 else "red"
                    
                    col_txt.markdown(f"**{r['Data'].strftime('%d/%m')} - {r['Item']}**")
                    col_txt.caption(f"{r['Categoria']} | {r['Tipo']}")
                    col_txt.markdown(f":{cor}[**{formatar_moeda(r['Valor'])}**]")
                    
                    # Botões de ação em colunas dentro do card
                    b_ed, b_del = col_btn.columns(2)
                    if b_ed.button("✏️", key=f"e_{idx}_{st.session_state['form_id']}"):
                        st.session_state['edit_index'] = idx
                        st.rerun()
                    if b_del.button("🗑️", key=f"d_{idx}_{st.session_state['form_id']}"):
                        dados_total = dados_total.drop(index=idx).reset_index(drop=True)
                        salvar_dados(dados_total)
                        st.rerun()
        else:
            st.info("Nenhum registro para este período.")

    # --- ABA 2: DASHBOARD (Com Rankings e Barras Ordenadas) ---
    with aba_dash:
        c_t, c_f = st.columns([2, 1])
        c_t.header("📊 Dashboard Analítico")
        modo_v = c_f.radio("Visão:", ["Mensal", "Acumulado Ano"], horizontal=True)

        if modo_v == "Mensal":
            df_dash = dados_mes.copy()
            txt_p = f"em {mes_sel_nome}"
        else:
            df_dash = dados_total[(pd.to_datetime(dados_total['Data']).dt.year == ano_sel) & (pd.to_datetime(dados_total['Data']).dt.month <= mes_sel_idx)].copy()
            txt_p = f"Acumulado {ano_sel}"

        if not df_dash.empty:
            # Métricas rápidas
            m1, m2, m3 = st.columns(3)
            ganhos = df_dash[df_dash['Tipo'] == "Entrada"]['Valor'].sum()
            gastos = abs(df_dash[df_dash['Tipo'] == "Saída"]['Valor'].sum())
            m1.metric("Ganhos", formatar_moeda(ganhos))
            m2.metric("Gastos", formatar_moeda(gastos))
            m3.metric("Saldo", formatar_moeda(ganhos - gastos))

            st.divider()
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                df_sai = df_dash[df_dash['Tipo'] == "Saída"]
                if not df_sai.empty:
                    fig_pie = px.pie(df_sai, values=abs(df_sai['Valor']), names='Categoria', title=f"Onde você gastou {txt_p}", hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)

            with col_g2:
                # Barras Ordenadas por Valor
                df_tipo = df_dash.groupby('Tipo')['Valor'].sum().abs().reset_index()
                df_tipo = df_tipo.sort_values(by='Valor', ascending=False)
                fig_tipo = px.bar(df_tipo, x='Tipo', y='Valor', color='Tipo', text_auto='.2s', title=f"Entradas vs Saídas {txt_p}")
                fig_tipo.update_layout(xaxis={'categoryorder':'total descending'})
                st.plotly_chart(fig_tipo, use_container_width=True, config={'displayModeBar': False})

            # Top 5 Categorias que mais consumiram
            st.divider()
            df_rank_cat = df_dash[df_dash['Tipo'] == "Saída"]
            if not df_rank_cat.empty:
                df_rank = df_rank_cat.groupby('Categoria')['Valor'].sum().abs().reset_index()
                df_rank = df_rank.sort_values(by='Valor', ascending=False).head(5)
                fig_rank = px.bar(df_rank, x='Valor', y='Categoria', orientation='h', title="🏆 Top 5 Maiores Gastos", color='Categoria', text_auto='.2s')
                fig_rank.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_rank, use_container_width=True)
        else:
            st.info("Sem dados para análise neste período.")

    # --- ABA 3: METAS (Sua lógica original de Reserva) ---
    with aba_inv:
        st.header("🎯 Reserva de Emergência")
        total_r = abs(dados_total[dados_total['Categoria'] == "Reserva de Emergência"]['Valor'].sum())
        meta_valor = 30000.0
        progresso = min(total_r/meta_valor, 1.0)
        
        st.progress(progresso)
        st.markdown(f"### Saldo: **{formatar_moeda(total_r)}** de {formatar_moeda(meta_valor)}")
        st.caption(f"Você já atingiu {progresso*100:.1f}% da sua meta de reserva.")