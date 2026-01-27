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
    """Criptografa a senha para comparar com o CSV."""
    return hashlib.sha256(str.encode(senha)).hexdigest()

def verificar_login(email_input, senha_input):
    """Valida as credenciais no arquivo usuarios.csv."""
    if os.path.exists("usuarios.csv"):
        df_users = pd.read_csv("usuarios.csv")
        user_row = df_users[df_users['email'] == email_input]
        if not user_row.empty:
            if gerar_hash(senha_input) == user_row.iloc[0]['senha']:
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
        "Entrada": ["Selecione...", "Salário", "Pró-labore", "Rendimento", "Outros"],
        "Saída": ["Selecione...", "Alimentação", "Aluguel", "Internet", "Transporte", "Lazer", "Saúde"],
        "Investimento": ["Selecione...", "Ações", "Cripto", "Tesouro", "Reserva de Emergência"]
    }

def salvar_dados(df):
    # Remove a coluna auxiliar de índice antes de salvar
    df.drop(columns=['_orig_index'], errors='ignore').to_csv("financas.csv", index=False)

def salvar_categorias(dic):
    max_len = max(len(v) for v in dic.values())
    dic_pad = {k: v + [None]*(max_len - len(v)) for k, v in dic.items()}
    pd.DataFrame(dic_pad).to_csv("categorias.csv", index=False)

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- INICIALIZAÇÃO DE ESTADO ---
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
    # --- INTERFACE PRINCIPAL (LOGADA) ---
    dados_total = carregar_dados()
    cats = carregar_categorias()

    # Barra Lateral
    st.sidebar.title("💰 My Finance Pro")
    st.sidebar.write(f"Usuário: **{st.session_state['usuario_atual']}**")
    if st.sidebar.button("🚪 Sair"):
        st.session_state['logado'] = False
        st.rerun()

    st.sidebar.divider()
    hoje = date.today()
    
    # Seleção de Período
    anos_disp = sorted(pd.to_datetime(dados_total['Data']).dt.year.unique(), reverse=True) if not dados_total.empty else [hoje.year]
    if hoje.year not in anos_disp: anos_disp.insert(0, hoje.year)
    ano_sel = st.sidebar.selectbox("Ano", anos_disp)
    
    meses_lista = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    mes_sel_nome = st.sidebar.selectbox("Mês", meses_lista, index=hoje.month - 1)
    mes_sel_idx = meses_lista.index(mes_sel_nome) + 1

    # Filtragem dos dados do mês
    dados_total['_orig_index'] = dados_total.index
    dados_mes = dados_total[
        (pd.to_datetime(dados_total['Data']).dt.month == mes_sel_idx) & 
        (pd.to_datetime(dados_total['Data']).dt.year == ano_sel)
    ].copy()

    aba_reg, aba_dash, aba_inv = st.tabs(["📝 Lançamentos", "📊 Dashboard Analítico", "🎯 Metas"])

    # --- ABA 1: LANÇAMENTOS ---
    with aba_reg:
        # 1. Cards de Resumo
        t_ent = dados_mes[dados_mes['Tipo'] == "Entrada"]['Valor'].sum()
        t_sai = abs(dados_mes[dados_mes['Tipo'] == "Saída"]['Valor'].sum())
        t_inv = abs(dados_mes[dados_mes['Tipo'] == "Investimento"]['Valor'].sum())
        saldo_mes = t_ent - t_sai - t_inv

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Receitas", formatar_moeda(t_ent))
        c2.metric("Despesas", formatar_moeda(t_sai), delta_color="inverse")
        c3.metric("Investido", formatar_moeda(t_inv))
        c4.metric("Saldo Líquido", formatar_moeda(saldo_mes), delta=saldo_mes)
        
        st.divider()

        # 2. Lógica de Edição (Pré-preenchimento)
        if st.session_state['edit_index'] is not None:
            try:
                item_edit = dados_total.loc[st.session_state['edit_index']]
                v_tipo, v_desc = item_edit['Tipo'], item_edit['Item']
                v_valor, v_data, v_cat = abs(float(item_edit['Valor'])), item_edit['Data'], item_edit['Categoria']
                st.warning(f"🔧 Editando: {v_desc}")
                if st.button("❌ Cancelar Edição"):
                    st.session_state['edit_index'] = None
                    st.rerun()
            except:
                st.session_state['edit_index'] = None
                st.rerun()
        else:
            v_tipo, v_desc, v_valor, v_cat = "---", "", 0.0, date(ano_sel, mes_sel_idx, 1)

        # 3. Formulário de Cadastro/Edição
        with st.container(border=True):
            f1, f2, f3, f4 = st.columns([1.2, 2, 1.2, 1.2])
            
            tipos_op = ["---", "Saída", "Entrada", "Investimento"]
            tipo_s = f1.selectbox("Tipo", tipos_op, index=tipos_op.index(v_tipo) if v_tipo in tipos_op else 0, key=f"t_{st.session_state['form_id']}")
            
            item_s = f2.text_input("Descrição", value=v_desc, placeholder="Ex: Mercado", key=f"i_{st.session_state['form_id']}")
            
            valor_num = f3.number_input("Valor (R$)", min_value=0.0, value=v_valor, format="%.2f", step=10.0, key=f"v_{st.session_state['form_id']}")
            
            # Calendário Travado no Mês Selecionado
            ultimo_dia_mes = calendar.monthrange(ano_sel, mes_sel_idx)[1]
            data_s = f4.date_input("Data", value=v_data, 
                                   min_value=date(ano_sel, mes_sel_idx, 1), 
                                   max_value=date(ano_sel, mes_sel_idx, ultimo_dia_mes), 
                                   format="DD/MM/YYYY", key=f"d_{st.session_state['form_id']}")
            
            col_cat, col_ncat = st.columns([3, 1])
            opcoes_cat = cats.get(tipo_s, ["Selecione..."])
            cat_s = col_cat.selectbox("Categoria", opcoes_cat, index=opcoes_cat.index(v_cat) if v_cat in opcoes_cat else 0, key=f"c_{st.session_state['form_id']}")
            n_cat_in = col_ncat.text_input("Nova Cat.", key=f"nc_{st.session_state['form_id']}")

            btn_label = "💾 Salvar Alterações" if st.session_state['edit_index'] is not None else "➕ Cadastrar Lançamento"
            if st.button(btn_label, use_container_width=True, type="primary"):
                if tipo_s != "---" and item_s != "" and valor_num > 0:
                    val_final = -valor_num if tipo_s in ["Saída", "Investimento"] else valor_num
                    cat_final = n_cat_in if n_cat_in else cat_s
                    
                    if st.session_state['edit_index'] is not None:
                        dados_total.loc[st.session_state['edit_index'], ["Data", "Tipo", "Item", "Categoria", "Valor"]] = [data_s, tipo_s, item_s, cat_final, val_final]
                        st.session_state['edit_index'] = None
                    else:
                        nova_linha = pd.DataFrame([{"Data": data_s, "Tipo": tipo_s, "Item": item_s, "Categoria": cat_final, "Valor": val_final}])
                        dados_total = pd.concat([dados_total, nova_linha], ignore_index=True)
                    
                    if n_cat_in and n_cat_in not in cats.get(tipo_s, []):
                        cats[tipo_s].append(n_cat_in); salvar_categorias(cats)
                    
                    salvar_dados(dados_total); st.session_state['form_id'] += 1; st.rerun()
                else:
                    st.error("Preencha todos os campos obrigatórios.")

        # 4. Tabela de Lançamentos
        st.subheader(f"📋 Movimentações de {mes_sel_nome}/{ano_sel}")
        if not dados_mes.empty:
            for _, r in dados_mes.sort_values(by='Data', ascending=False).iterrows():
                idx_orig = r['_orig_index']
                with st.container(border=False):
                    col_t = st.columns([1, 1, 2.5, 2, 1.5, 0.8])
                    col_t[0].write(f"**{r['Data'].strftime('%d/%m')}**")
                    col_t[1].caption(r['Tipo'])
                    col_t[2].write(r['Item'])
                    col_t[3].write(f"🏷️ {r['Categoria']}")
                    cor_valor = "green" if r['Valor'] > 0 else "red"
                    col_t[4].markdown(f":{cor_valor}[**{formatar_moeda(r['Valor'])}**]")
                    
                    b_edit, b_del = col_t[5].columns(2)
                    if b_edit.button("✏️", key=f"ed_{idx_orig}_{st.session_state['form_id']}"):
                        st.session_state['edit_index'] = idx_orig; st.rerun()
                    if b_del.button("🗑️", key=f"de_{idx_orig}_{st.session_state['form_id']}"):
                        dados_total = dados_total.drop(index=idx_orig).reset_index(drop=True)
                        salvar_dados(dados_total); st.rerun()
                st.divider()
        else:
            st.info("Nenhum lançamento neste mês.")

    # --- ABA 2: DASHBOARD ---
    with aba_dash:
        if not dados_mes.empty:
            col_d1, col_d2 = st.columns(2)
            df_gastos = dados_mes[dados_mes['Tipo'] == "Saída"]
            if not df_gastos.empty:
                col_d1.plotly_chart(px.pie(df_gastos, values=abs(df_gastos['Valor']), names='Categoria', title="Gastos por Categoria", hole=0.4), use_container_width=True)
            
            df_resumo = dados_mes.groupby('Tipo')['Valor'].sum().abs().reset_index()
            col_d2.plotly_chart(px.bar(df_resumo, x='Tipo', y='Valor', color='Tipo', title="Entradas vs Saídas", text_auto='.2f'), use_container_width=True)
        else:
            st.info("Lance dados para gerar os gráficos.")

    # --- ABA 3: METAS ---
    with aba_inv:
        st.header("🎯 Reserva de Emergência")
        total_reserva = abs(dados_total[dados_total['Categoria'] == "Reserva de Emergência"]['Valor'].sum())
        meta_reserva = 30000.0
        pct = min(total_reserva / meta_reserva, 1.0)
        st.write(f"Saldo Atual: **{formatar_moeda(total_reserva)}**")
        st.progress(pct)
        st.caption(f"Meta: {formatar_moeda(meta_reserva)} ({pct:.1%})")



