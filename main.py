import streamlit as st
import pandas as pd
import plotly.express as px
import os
import hashlib
from datetime import date

# =====================================================
# CONFIGURAÇÃO DA PÁGINA
# =====================================================
st.set_page_config(
    page_title="My Finance Pro",
    page_icon="💰",
    layout="wide"
)

# =====================================================
# FUNÇÕES DE SEGURANÇA
# =====================================================
def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# =====================================================
# USUÁRIOS
# =====================================================
def carregar_usuarios():
    if os.path.exists("usuarios.csv"):
        return pd.read_csv("usuarios.csv")
    df = pd.DataFrame(columns=["email", "senha", "perfil", "status"])
    df.to_csv("usuarios.csv", index=False)
    return df

def salvar_usuarios(df):
    df.to_csv("usuarios.csv", index=False)

usuarios = carregar_usuarios()

# ADMIN PADRÃO
if "admin@admin.com" not in usuarios["email"].values:
    admin = {
        "email": "admin@admin.com",
        "senha": criptografar_senha("1234"),
        "perfil": "admin",
        "status": "ativo"
    }
    usuarios = pd.concat([usuarios, pd.DataFrame([admin])], ignore_index=True)
    salvar_usuarios(usuarios)

# =====================================================
# SESSION STATE
# =====================================================
if "logado" not in st.session_state:
    st.session_state.logado = False
if "usuario" not in st.session_state:
    st.session_state.usuario = None
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None
if "form_id" not in st.session_state:
    st.session_state.form_id = 0

# =====================================================
# LOGIN / CADASTRO
# =====================================================
if not st.session_state.logado:
    st.title("🔐 My Finance Pro")

    aba_login, aba_cadastro = st.tabs(["Login", "Cadastro"])

    with aba_login:
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")

        if st.button("Entrar"):
            senha_cripto = criptografar_senha(senha)
            user = usuarios[
                (usuarios["email"] == email) &
                (usuarios["senha"] == senha_cripto)
            ]

            if not user.empty:
                if user.iloc[0]["status"] != "ativo":
                    st.error("Usuário aguardando aprovação do administrador.")
                else:
                    st.session_state.logado = True
                    st.session_state.usuario = user.iloc[0].to_dict()
                    st.rerun()
            else:
                st.error("E-mail ou senha incorretos.")

    with aba_cadastro:
        novo_email = st.text_input("Novo e-mail")
        nova_senha = st.text_input("Nova senha", type="password")

        if st.button("Solicitar Cadastro"):
            if novo_email in usuarios["email"].values:
                st.error("E-mail já cadastrado.")
            elif novo_email == "" or nova_senha == "":
                st.error("Preencha todos os campos.")
            else:
                novo = {
                    "email": novo_email,
                    "senha": criptografar_senha(nova_senha),
                    "perfil": "user",
                    "status": "pendente"
                }
                usuarios = pd.concat([usuarios, pd.DataFrame([novo])], ignore_index=True)
                salvar_usuarios(usuarios)
                st.success("Cadastro enviado. Aguarde aprovação do administrador.")

    st.stop()

# =====================================================
# USUÁRIO LOGADO
# =====================================================
user = st.session_state.usuario
email_usuario = user["email"]

st.sidebar.success(f"Logado como: {email_usuario}")

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.session_state.usuario = None
    st.rerun()

# =====================================================
# PAINEL ADMIN
# =====================================================
if user["perfil"] == "admin":
    st.title("🛠️ Painel do Administrador")

    usuarios = carregar_usuarios()
    st.dataframe(usuarios[["email", "perfil", "status"]])

    email_sel = st.selectbox("Selecionar usuário", usuarios["email"])

    col1, col2 = st.columns(2)

    if col1.button("Aprovar Usuário"):
        usuarios.loc[usuarios["email"] == email_sel, "status"] = "ativo"
        salvar_usuarios(usuarios)
        st.success("Usuário aprovado.")
        st.rerun()

    if col2.button("Resetar Senha"):
        nova = "123456"
        usuarios.loc[usuarios["email"] == email_sel, "senha"] = criptografar_senha(nova)
        salvar_usuarios(usuarios)
        st.warning("Senha resetada para: 123456")

    st.stop()

# =====================================================
# FUNÇÕES FINANCEIRAS (MULTIUSUÁRIO)
# =====================================================
def carregar_dados(usuario):
    if os.path.exists("financas.csv"):
        df = pd.read_csv("financas.csv")
        df["Data"] = pd.to_datetime(df["Data"]).dt.date
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
        return df[df["Usuario"] == usuario]
    return pd.DataFrame(columns=["Usuario", "Data", "Tipo", "Item", "Categoria", "Valor"])

def salvar_dados(df):
    df.to_csv("financas.csv", index=False)

def carregar_categorias():
    if os.path.exists("categorias.csv"):
        df = pd.read_csv("categorias.csv")
        return {c: df[c].dropna().tolist() for c in df.columns}
    return {
        "Entrada": ["Salário", "Outros"],
        "Saída": ["Alimentação", "Aluguel", "Lazer", "Outros"],
        "Investimento": ["Reserva de Emergência", "Outros"]
    }

def formatar_moeda(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# =====================================================
# APP FINANCEIRO
# =====================================================
dados_total = carregar_dados(email_usuario)
cats = carregar_categorias()
hoje = date.today()

st.title("💰 My Finance Pro")

aba_reg, aba_dash, aba_meta = st.tabs(["📝 Lançamentos", "📊 Dashboard", "🎯 Metas"])

# ---------------- LANÇAMENTOS ----------------
with aba_reg:
    tipo = st.selectbox("Tipo", ["Entrada", "Saída", "Investimento"])
    item = st.text_input("Descrição")
    valor = st.number_input("Valor", min_value=0.0)
    data = st.date_input("Data", hoje)
    categoria = st.selectbox("Categoria", cats[tipo])

    if st.button("Salvar"):
        novo = pd.DataFrame([{
            "Usuario": email_usuario,
            "Data": data,
            "Tipo": tipo,
            "Item": item,
            "Categoria": categoria,
            "Valor": valor if tipo == "Entrada" else -valor
        }])
        salvar_dados(pd.concat([dados_total, novo], ignore_index=True))
        st.success("Lançamento salvo.")
        st.rerun()

    st.dataframe(dados_total)

# ---------------- DASHBOARD ----------------
with aba_dash:
    ganhos = dados_total[dados_total["Tipo"] == "Entrada"]["Valor"].sum()
    gastos = abs(dados_total[dados_total["Tipo"] == "Saída"]["Valor"].sum())

    st.metric("Ganhos", formatar_moeda(ganhos))
    st.metric("Gastos", formatar_moeda(gastos))
    st.metric("Saldo", formatar_moeda(ganhos - gastos))

    if not dados_total.empty:
        fig = px.pie(
            dados_total[dados_total["Tipo"] == "Saída"],
            values=abs(dados_total["Valor"]),
            names="Categoria"
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------------- METAS ----------------
with aba_meta:
    total = abs(
        dados_total[dados_total["Categoria"] == "Reserva de Emergência"]["Valor"].sum()
    )
    meta = 30000
    st.progress(min(total / meta, 1.0))
    st.write(f"Reserva: {formatar_moeda(total)} de {formatar_moeda(meta)}")

