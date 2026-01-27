import streamlit as st
import pandas as pd
import plotly.express as px
import os
import hashlib
from datetime import datetime, date

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="My Finance Pro", layout="wide", page_icon="💰")

# --- FUNÇÕES DE SEGURANÇA ---
def gerar_hash(senha):
    """Transforma a senha em um código seguro (Hash SHA-256)."""
    return hashlib.sha256(str.encode(senha)).hexdigest()

def verificar_login(email_input, senha_input):
    """Verifica se o usuário existe e se a senha está correta."""
    if os.path.exists("usuarios.csv"):
        df_users = pd.read_csv("usuarios.csv")
        # Filtra pelo email
        user_row = df_users[df_users['email'] == email_input]
        
        if not user_row.empty:
            hash_digitado = gerar_hash(senha_input)
            hash_armazenado = user_row.iloc[0]['senha']
            aprovado = user_row.iloc[0]['aprovado']
            
            if hash_digitado == hash_armazenado:
                if aprovado:
                    return True, "Sucesso"
                else:
                    return False, "Usuário aguardando aprovação."
            else:
                return False, "Senha incorreta."
        return False, "E-mail não encontrado."
    return False, "Arquivo de usuários não encontrado."

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

# --- INICIALIZAÇÃO DE ESTADO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'edit_index' not in st.session_state: st.session_state['edit_index'] = None
if 'form_id' not in st.session_state: st.session_state['form_id'] = 0

# --- TELA DE ACESSO ---
if not st.session_state['logado']:
    st.title("🔒 My Finance Pro - Acesso")
    col_l, _ = st.columns([1, 2])
    with col_l:
        email_log = st.text_input("E-mail")
        senha_log = st.text_input("Senha", type="password")
        if st.button("Acessar Sistema"):
            sucesso, mensagem = verificar_login(email_log, senha_log)
            if sucesso:
                st.session_state['logado'] = True
                st.session_state['usuario_atual'] = email_log
                st.rerun()
            else:
                st.error(mensagem)
else:
    # --- ÁREA LOGADA DO SISTEMA ---
    dados_total = carregar_dados()
    cats = carregar_categorias()

    # Barra Lateral
    st.sidebar.header(f"👤 {st.session_state['usuario_atual']}")
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

    dados_total['_orig_index'] = dados_total.index
    dados_mes = dados_total[
        (pd.to_datetime(dados_total['Data']).dt.month == mes_sel_idx) & 
        (pd.to_datetime(dados_total['Data']).dt.year == ano_sel)
    ].copy()

    aba_reg, aba_dash, aba_inv = st.tabs(["📝 Lançamentos", "📊 Dashboard", "📈 Metas"])

    with aba_reg:
        st.subheader(f"Movimentações de {mes_sel_nome}/{ano_sel}")
        # Lógica de edição
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
                    
                    if n_cat_in and n_cat_in not in cats[tipo_s]:
                        cats[tipo_s].append(n_cat_in); salvar_categorias(cats)
                    
                    salvar_dados(dados_total); st.session_state['form_id'] += 1; st.rerun()
                except: st.error("Erro no formato do valor.")

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

    with aba_dash:
        # Lógica de dashboard resumida
        if not dados_mes.empty:
            total_entradas = dados_mes[dados_mes['Tipo'] == "Entrada"]['Valor'].sum()
            total_saidas = abs(dados_mes[dados_mes['Tipo'] == "Saída"]['Valor'].sum())
            saldo = total_entradas - total_saidas
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Entradas", formatar_moeda(total_entradas))
            c2.metric("Saídas", formatar_moeda(total_saidas))
            c3.metric("Saldo Mensal", formatar_moeda(saldo))
            
            st.divider()
            col_g1, col_g2 = st.columns(2)
            df_sai = dados_mes[dados_mes['Tipo'] == "Saída"]
            if not df_sai.empty:
                col_g1.plotly_chart(px.pie(df_sai, values=abs(df_sai['Valor']), names='Categoria', title="Gastos por Categoria"), use_container_width=True)
            
            df_tipo = dados_mes.groupby('Tipo')['Valor'].sum().abs().reset_index()
            col_g2.plotly_chart(px.bar(df_tipo, x='Tipo', y='Valor', color='Tipo', title="Resumo Financeiro"), use_container_width=True)
        else:
            st.info("Lance dados para ver o dashboard.")

    with aba_inv:
        st.header("🎯 Reserva de Emergência")
        total_r = abs(dados_total[dados_total['Categoria'] == "Reserva de Emergência"]['Valor'].sum())
        meta = 30000.0
        progresso = min(total_r / meta, 1.0)
        st.progress(progresso)
        st.caption(f"Saldo: {formatar_moeda(total_r)} de {formatar_moeda(meta)}")



