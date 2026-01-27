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
            if gerar_hash(senha_input) == str(user_row.iloc[0]['senha']):
                if user_row.iloc[0]['aprovado']:
                    return True, "Sucesso"
                return False, "Usuário aguardando aprovação."
            return False, "Senha incorreta."
    return False, "Usuário não encontrado."

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
        "Entrada": ["Selecione...", "Salário", "Rendimento", "Outros"],
        "Saída": ["Selecione...", "Alimentação", "Aluguel", "Lazer", "Saúde", "Transporte"],
        "Investimento": ["Selecione...", "Ações", "FIIs", "Cripto", "Reserva de Emergência"]
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
            suc, msg = verificar_login(email_log, senha_log)
            if suc:
                st.session_state['logado'], st.session_state['usuario_atual'] = True, email_log
                st.rerun()
            else: st.error(msg)
else:
    # --- ÁREA LOGADA ---
    dados_total = carregar_dados()
    cats = carregar_categorias()

    # Barra Lateral
    st.sidebar.title("💰 Finance Pro")
    st.sidebar.write(f"Usuário: **{st.session_state['usuario_atual']}**")
    if st.sidebar.button("Sair"):
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

    # Filtro de dados
    dados_total['_orig_index'] = dados_total.index
    dados_mes = dados_total[(pd.to_datetime(dados_total['Data']).dt.month == mes_sel_idx) & (pd.to_datetime(dados_total['Data']).dt.year == ano_sel)].copy()

    # --- REATIVAÇÃO DAS 3 ABAS ---
    aba_reg, aba_dash, aba_meta = st.tabs(["📝 Lançamentos", "📊 Dashboard", "🎯 Metas"])

    with aba_reg:
        # Cards de Resumo
        t_ent = dados_mes[dados_mes['Tipo'] == "Entrada"]['Valor'].sum()
        t_sai = abs(dados_mes[dados_mes['Tipo'] == "Saída"]['Valor'].sum())
        t_inv = abs(dados_mes[dados_mes['Tipo'] == "Investimento"]['Valor'].sum())
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Receitas", formatar_moeda(t_ent))
        c2.metric("Despesas", formatar_moeda(t_sai), delta_color="inverse")
        c3.metric("Investido", formatar_moeda(t_inv))
        c4.metric("Saldo Líquido", formatar_moeda(t_ent - t_sai - t_inv))
        
        st.divider()

        # PREPARAÇÃO DOS DADOS PARA EDIÇÃO
        if st.session_state['edit_index'] is not None:
            try:
                row = dados_total.loc[st.session_state['edit_index']]
                v_tipo, v_desc, v_valor, v_data, v_cat = row['Tipo'], row['Item'], abs(float(row['Valor'])), row['Data'], row['Categoria']
                st.warning(f"🔧 Editando: {v_desc}")
                if st.button("Cancelar Edição"):
                    st.session_state['edit_index'] = None
                    st.rerun()
            except: st.session_state['edit_index'] = None; st.rerun()
        else:
            v_tipo, v_desc, v_valor, v_data, v_cat = "---", "", 0.0, date(ano_sel, mes_sel_idx, 1), "Selecione..."

        # FORMULÁRIO DE LANÇAMENTO
        with st.container(border=True):
            f1, f2, f3, f4 = st.columns([1.2, 2, 1, 1])
            tipos = ["---", "Saída", "Entrada", "Investimento"]
            tipo_s = f1.selectbox("Tipo", tipos, index=tipos.index(v_tipo) if v_tipo in tipos else 0, key=f"t_{st.session_state['form_id']}")
            item_s = f2.text_input("Descrição", value=v_desc, key=f"i_{st.session_state['form_id']}")
            valor_num = f3.number_input("Valor (R$)", min_value=0.0, value=v_valor, format="%.2f", key=f"v_{st.session_state['form_id']}")
            u_dia = calendar.monthrange(ano_sel, mes_sel_idx)[1]
            data_s = f4.date_input("Data", value=v_data, min_value=date(ano_sel, mes_sel_idx, 1), max_value=date(ano_sel, mes_sel_idx, u_dia), key=f"d_{st.session_state['form_id']}")
            
            col_c, col_nc = st.columns([3, 1])
            lista_c = cats.get(tipo_s, ["Selecione..."])
            cat_s = col_c.selectbox("Categoria", lista_c, index=lista_c.index(v_cat) if v_cat in lista_c else 0, key=f"c_{st.session_state['form_id']}")
            nova_c = col_nc.text_input("Nova Cat.", key=f"nc_{st.session_state['form_id']}")

            if st.button("💾 Salvar Registro", use_container_width=True, type="primary"):
                if tipo_s != "---" and item_s != "" and valor_num > 0:
                    v_f = -valor_num if tipo_s in ["Saída", "Investimento"] else valor_num
                    c_f = nova_c if nova_c else cat_s
                    if st.session_state['edit_index'] is not None:
                        dados_total.loc[st.session_state['edit_index'], ["Data", "Tipo", "Item", "Categoria", "Valor"]] = [data_s, tipo_s, item_s, c_f, v_f]
                        st.session_state['edit_index'] = None
                    else:
                        dados_total = pd.concat([dados_total, pd.DataFrame([{"Data": data_s, "Tipo": tipo_s, "Item": item_s, "Categoria": c_f, "Valor": v_f}])], ignore_index=True)
                    if nova_c and nova_c not in cats.get(tipo_s, []):
                        cats[tipo_s].append(nova_c); salvar_categorias(cats)
                    salvar_dados(dados_total); st.session_state['form_id'] += 1; st.rerun()
                else: st.error("Preencha todos os campos!")

        # LISTAGEM DE MOVIMENTAÇÕES
        st.subheader("📋 Detalhamento")
        if not dados_mes.empty:
            for _, r in dados_mes.sort_values(by='Data', ascending=False).iterrows():
                idx_orig = r['_orig_index']
                with st.container(border=False):
                    col = st.columns([1, 1, 3, 2, 1.5, 0.8])
                    col[0].write(f"**{r['Data'].strftime('%d/%m')}**")
                    col[1].caption(r['Tipo'])
                    col[2].write(r['Item'])
                    col[3].write(f"🏷️ {r['Categoria']}")
                    cor = "green" if r['Valor'] > 0 else "red"
                    col[4].markdown(f":{cor}[**{formatar_moeda(r['Valor'])}**]")
                    be, bd = col[5].columns(2)
                    if be.button("✏️", key=f"ed_{idx_orig}_{st.session_state['form_id']}"):
                        st.session_state['edit_index'] = idx_orig; st.rerun()
                    if bd.button("🗑️", key=f"de_{idx_orig}_{st.session_state['form_id']}"):
                        dados_total = dados_total.drop(index=idx_orig).reset_index(drop=True); salvar_dados(dados_total); st.rerun()
                st.divider()

    # --- ABA 2: DASHBOARD (REATIVADA) ---
    with aba_dash:
        st.header(f"📊 Análise de {mes_sel_nome}")
        if not dados_mes.empty:
            col_d1, col_d2 = st.columns(2)
            
            # Gráfico de Pizza (Gastos)
            df_gastos = dados_mes[dados_mes['Tipo'] == "Saída"]
            if not df_gastos.empty:
                fig_pizza = px.pie(df_gastos, values=abs(df_gastos['Valor']), names='Categoria', 
                                  title="Distribuição de Despesas", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                col_d1.plotly_chart(fig_pizza, use_container_width=True)
            else:
                col_d1.info("Sem despesas para mostrar no gráfico.")

            # Gráfico de Barras (Comparativo)
            df_comp = dados_mes.groupby('Tipo')['Valor'].sum().abs().reset_index()
            fig_bar = px.bar(df_comp, x='Tipo', y='Valor', color='Tipo', title="Entradas vs Saídas", text_auto='.2f')
            col_d2.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Lance dados para visualizar os gráficos.")

    # --- ABA 3: METAS / RESERVA (REATIVADA) ---
    with aba_meta:
        st.header("🎯 Metas e Reserva de Emergência")
        # Filtra tudo que foi categorizado como Reserva de Emergência no histórico todo
        reserva_atual = abs(dados_total[dados_total['Categoria'] == "Reserva de Emergência"]['Valor'].sum())
        meta_objetivo = 30000.0  # Você pode alterar esse valor
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Total em Reserva", formatar_moeda(reserva_atual))
            st.write(f"Sua meta atual é de: **{formatar_moeda(meta_objetivo)}**")
        
        with col_m2:
            progresso = min(reserva_atual / meta_objetivo, 1.0)
            st.write(f"Progresso da Meta: **{progresso:.1%}**")
            st.progress(progresso)
        
        st.divider()
        st.caption("Dica: Para alimentar sua reserva, faça lançamentos com o Tipo 'Investimento' e a Categoria 'Reserva de Emergência'.")


