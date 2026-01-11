import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# 1. Layout Fluido
st.set_page_config(page_title="My Finance Pro", layout="wide", page_icon="💰")

# --- FUNÇÕES DE NÚCLEO ---
def carregar_dados():
    if os.path.exists("financas.csv"):
        # Lendo com tratamento de erro para evitar crash se o arquivo estiver aberto
        df = pd.read_csv("financas.csv")
        df['Data'] = pd.to_datetime(df['Data']).dt.date
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
        return df
    return pd.DataFrame(columns=["Data", "Tipo", "Item", "Categoria", "Valor"])

def salvar_dados(df):
    # Remove colunas temporárias antes de salvar
    df_save = df.drop(columns=['_orig_index'], errors='ignore')
    df_save.to_csv("financas.csv", index=False)

def formatar_moeda(valor):
    return f"R$ {abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- SEGURANÇA ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'edit_index' not in st.session_state: st.session_state['edit_index'] = None

if not st.session_state['logado']:
    st.title("🔒 Login")
    try:
        senha_mestra = st.secrets["password"]
    except:
        senha_mestra = "1234"
    
    senha_digitada = st.text_input("Senha:", type="password")
    if st.button("Entrar", use_container_width=True):
        if senha_digitada == senha_mestra:
            st.session_state['logado'] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
else:
    # --- APP PRINCIPAL ---
    # Recarrega os dados para garantir sincronia
    df = carregar_dados()

    # Filtros na Lateral (recolhidos por padrão no mobile)
    st.sidebar.header("📅 Período")
    ano_sel = st.sidebar.selectbox("Ano", [2024, 2025, 2026], index=2) # 2026 como padrão
    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    mes_sel_nome = st.sidebar.selectbox("Mês", meses, index=date.today().month - 1)
    mes_idx = meses.index(mes_sel_nome) + 1

    aba1, aba2 = st.tabs(["📝 Lançamentos", "📊 Dashboard"])

    with aba1:
        # TÍTULO E FORMULÁRIO
        if st.session_state['edit_index'] is not None:
            st.warning("🔧 Modo de Edição Ativo")
            idx_ed = st.session_state['edit_index']
            # Garante que o index existe
            if idx_ed in df.index:
                r_ed = df.loc[idx_ed]
                v_tipo, v_item, v_val, v_data, v_cat = r_ed['Tipo'], r_ed['Item'], abs(float(r_ed['Valor'])), r_ed['Data'], r_ed['Categoria']
            else:
                st.session_state['edit_index'] = None
                st.rerun()
        else:
            v_tipo, v_item, v_val, v_data, v_cat = "Saída", "", 0.0, date.today(), "Outros"

        with st.form("form_lancar", clear_on_submit=True):
            tipo = st.selectbox("O que é?", ["Saída", "Entrada", "Investimento"], index=["Saída", "Entrada", "Investimento"].index(v_tipo))
            item = st.text_input("Descrição", value=v_item, placeholder="Ex: Combustível")
            
            c1, c2 = st.columns(2)
            # O number_input é melhor para mobile pois abre teclado numérico
            valor = c1.number_input("Valor R$", min_value=0.0, value=v_val, step=0.01, format="%.2f")
            dt = c2.date_input("Data", value=v_data)
            
            cats = ["Alimentação", "Aluguel", "Lazer", "Transporte", "Saúde", "Educação", "Salário", "Investimento", "Outros"]
            categoria = st.selectbox("Categoria", cats, index=cats.index(v_cat) if v_cat in cats else 8)

            btn_label = "Atualizar" if st.session_state['edit_index'] is not None else "Salvar Lançamento"
            if st.form_submit_button(btn_label, use_container_width=True):
                valor_final = -valor if tipo in ["Saída", "Investimento"] else valor
                
                if st.session_state['edit_index'] is not None:
                    df.loc[st.session_state['edit_index'], ["Data", "Tipo", "Item", "Categoria", "Valor"]] = [dt, tipo, item, categoria, valor_final]
                    st.session_state['edit_index'] = None
                else:
                    novo_registro = pd.DataFrame([{"Data": dt, "Tipo": tipo, "Item": item, "Categoria": categoria, "Valor": valor_final}])
                    df = pd.concat([df, novo_registro], ignore_index=True)
                
                salvar_dados(df)
                st.success("Concluído!")
                st.rerun()
        
        if st.session_state['edit_index'] is not None:
            if st.button("Cancelar Edição", use_container_width=True):
                st.session_state['edit_index'] = None
                st.rerun()

        st.divider()
        # LISTAGEM EM CARDS (Melhor para Celular)
        df['_orig_index'] = df.index
        df_mes = df[(pd.to_datetime(df['Data']).dt.month == mes_idx) & (pd.to_datetime(df['Data']).dt.year == ano_sel)]
        
        for i, row in df_mes.sort_values(by="Data", ascending=False).iterrows():
            with st.container(border=True):
                col_txt, col_btn = st.columns([3, 1])
                cor = "red" if row['Valor'] < 0 else "green"
                col_txt.markdown(f"**{row['Item']}**")
                col_txt.caption(f"{row['Data'].strftime('%d/%m')} • {row['Categoria']}")
                col_txt.markdown(f":{cor}[{formatar_moeda(row['Valor'])}]")
                
                # Botões de ação empilhados para facilitar o toque
                if col_btn.button("✏️", key=f"ed{i}", use_container_width=True):
                    st.session_state['edit_index'] = row['_orig_index']
                    st.rerun()
                if col_btn.button("🗑️", key=f"del{i}", use_container_width=True):
                    df = df.drop(index=row['_orig_index'])
                    salvar_dados(df)
                    st.rerun()

    with aba2:
        st.subheader(f"Resumo de {mes_sel_nome}")
        df_dash = df[pd.to_datetime(df['Data']).dt.year == ano_sel]
        
        if not df_dash.empty:
            # Métricas
            ent = df_dash[df_dash['Tipo'] == "Entrada"]['Valor'].sum()
            sai = abs(df_dash[df_dash['Tipo'] == "Saída"]['Valor'].sum())
            
            c1, c2 = st.columns(2)
            c1.metric("Ganhos", formatar_moeda(ent))
            c2.metric("Gastos", formatar_moeda(sai))

            # Gráficos adaptados
            fig_bar = px.bar(df_dash.groupby('Tipo')['Valor'].sum().abs().reset_index(), 
                             x='Tipo', y='Valor', color='Tipo', title="Entradas vs Saídas")
            st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})
            
            df_pie = df_dash[df_dash['Tipo'] == "Saída"]
            if not df_pie.empty:
                fig_pie = px.pie(df_pie, values=abs(df_pie['Valor']), names='Categoria', title="Gastos por Categoria")
                st.plotly_chart(fig_pie, use_container_width=True)