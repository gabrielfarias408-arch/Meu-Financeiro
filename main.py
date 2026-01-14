import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import date
import hashlib

# ================== CONFIGURAÇÃO ==================
st.set_page_config(page_title="My Finance Pro", layout="wide")

USUARIOS_ARQ = "usuarios.csv"
FINANCAS_ARQ = "financas.csv"

# ================== FUNÇÕES ==================
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def inicializar_usuarios():
    if not os.path.exists(USUARIOS_ARQ):
        admin = pd.DataFrame([{
            "email": "admin@admin.com",
            "senha": hash_senha("admin123"),
            "perfil": "admin",
            "aprovado": True
        }])
        admin.to_csv(USUARIOS_ARQ, index=False)

def carregar_usuarios():
    inicializar_usuarios()
    return pd.read_csv(USUARIOS_ARQ)

def salvar_usuarios(df):
    df.to_csv(USUARIOS_ARQ, index=False)

def carregar_financas(usuario):
    if os.path.exists(FINANCAS_ARQ):
        df = pd.read_csv(FINANCAS_ARQ)
        df["Data"] = pd.to_datetime(df["Data"]).dt.date
        return df[df["Usuario"] == usuario]
    return pd.DataFrame(columns=["Usuario", "Data", "Tipo", "Descricao", "Categoria", "Valor"])

def salvar_financas(df):
    df.to_csv(FINANCAS_ARQ, index=False)

def formatar_moeda(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ================== SESSION ==================
if "logado" not in st.session_state:
    st.session_state.logado = False
if "usuario" not in st.session_state:
    st.session_state.usuario = None
if "perfil" not in st.session_state:
    st.session_state.perfil = None

# ================== LOGIN ==================
if not st.session_state.logado:
    st.title("🔐 My Finance Pro")

    aba_login, aba_cadastro = st.tabs(["Login", "Cadastro"])

    with aba_login:
        email = st.text_input("Email")
        senha = st.text_input("Senha", type="password")

        if st.button("Entrar"):
            usuarios = carregar_usuarios()
            senha_hash = hash_senha(senha)

            user = usuarios[
                (usuarios["email"] == email) &
                (usuarios["senha"] == senha_hash) &
                (usuarios["aprovado"] == True)
            ]

            if not user.empty:
                st.session_state.logado = True
                st.session_state.usuario = email
                st.session_state.perfil = user.iloc[0]["perfil"]
                st.rerun()
            else:
                st.error("Login inválido ou usuário não aprovado.")

    with aba_cadastro:
        novo_email = st.text_input("Email novo")
        nova_senha = st.text_input("Senha nova", type="password")

        if st.button("Cadastrar"):
            usuarios = carregar_usuarios()
            if novo_email in usuarios["email"].values:
                st.error("Usuário já existe.")
            else:
                novo = pd.DataFrame([{
                    "email": novo_email,
                    "senha": hash_senha(nova_senha),
                    "perfil": "usuario",
                    "aprovado": False
                }])
                salvar_usuarios(pd.concat([usuarios, novo], ignore_index=True))
                st.success("Cadastro enviado. Aguarde aprovação do admin.")

    st.stop()

# ================== ADMIN ==================
if st.session_state.perfil == "admin":
    st.sidebar.header("👑 Administração")
    usuarios = carregar_usuarios()

    for i, row in usuarios.iterrows():
        col1, col2, col3 = st.sidebar.columns([3, 1, 1])
        col1.write(row["email"])

        if not row["aprovado"]:
            if col2.button("Aprovar", key=f"a{i}"):
                usuarios.loc[i, "aprovado"] = True
                salvar_usuarios(usuarios)
                st.rerun()

        if col3.button("❌", key=f"d{i}"):
            usuarios = usuarios.drop(i)
            salvar_usuarios(usuarios)
            st.rerun()

# ================== APLICATIVO ==================
st.sidebar.success(f"Logado como: {st.session_state.usuario}")

dados = carregar_financas(st.session_state.usuario)

# ---------- Lançamentos ----------
st.header("📝 Lançamentos")

col1, col2, col3 = st.columns(3)
tipo = col1.selectbox("Tipo", ["Entrada", "Saída", "Investimento"])
descricao = col2.text_input("Descrição")
categoria = col3.text_input("Categoria")
valor = st.number_input("Valor", min_value=0.0)
data = st.date_input("Data", value=date.today())

if st.button("Salvar lançamento"):
    novo = pd.DataFrame([{
        "Usuario": st.session_state.usuario,
        "Data": data,
        "Tipo": tipo,
        "Descricao": descricao,
        "Categoria": categoria,
        "Valor": valor if tipo == "Entrada" else -valor
    }])

    if os.path.exists(FINANCAS_ARQ):
        base = pd.read_csv(FINANCAS_ARQ)
        salvar_financas(pd.concat([base, novo], ignore_index=True))
    else:
        salvar_financas(novo)

    st.success("Lançamento salvo!")
    st.rerun()

# ---------- Tabela ----------
st.subheader("📄 Movimentações")
st.dataframe(dados, use_container_width=True)

# ---------- Gráficos ----------
st.subheader("📊 Dashboard")

df_saida = dados[dados["Tipo"] == "Saída"]

if not df_saida.empty:
    fig1 = px.pie(
        df_saida,
        values=df_saida["Valor"].abs(),
        names="Categoria",
        title="Distribuição de Gastos"
    )
    st.plotly_chart(fig1, use_container_width=True)

df_tipo = dados.groupby("Tipo")["Valor"].sum().abs().reset_index()

if not df_tipo.empty:
    fig2 = px.bar(
        df_tipo,
        x="Tipo",
        y="Valor",
        title="Resumo Financeiro",
        text="Valor"
    )
    fig2.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
    st.plotly_chart(fig2, use_container_width=True)

# ---------- Logout ----------
if st.sidebar.button("Sair"):
    st.session_state.clear()
    st.rerun()



