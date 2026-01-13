import streamlit as st
import pandas as pd
import os
import hashlib

# ==============================
# CONFIGURAÇÃO DA PÁGINA
# ==============================
st.set_page_config(
    page_title="My Finance Pro",
    page_icon="💰",
    layout="wide"
)

# ==============================
# FUNÇÃO PARA CRIPTOGRAFAR SENHA
# ==============================
def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# ==============================
# USUÁRIOS - CSV
# ==============================
def carregar_usuarios():
    if os.path.exists("usuarios.csv"):
        return pd.read_csv("usuarios.csv")
    else:
        df = pd.DataFrame(columns=["email", "senha", "perfil", "status"])
        df.to_csv("usuarios.csv", index=False)
        return df

def salvar_usuarios(df):
    df.to_csv("usuarios.csv", index=False)

usuarios = carregar_usuarios()

# ==============================
# CRIA ADMIN PADRÃO (SE NÃO EXISTIR)
# ==============================
if "admin@admin.com" not in usuarios["email"].values:
    admin = {
        "email": "admin@admin.com",
        "senha": criptografar_senha("1234"),
        "perfil": "admin",
        "status": "ativo"
    }
    usuarios = pd.concat([usuarios, pd.DataFrame([admin])], ignore_index=True)
    salvar_usuarios(usuarios)

# ==============================
# SESSION STATE
# ==============================
if "logado" not in st.session_state:
    st.session_state.logado = False

if "usuario" not in st.session_state:
    st.session_state.usuario = None

# ==============================
# LOGIN / CADASTRO
# ==============================
if not st.session_state.logado:
    st.title("🔐 My Finance Pro")

    aba_login, aba_cadastro = st.tabs(["Login", "Cadastro"])

    # -------- LOGIN --------
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

    # -------- CADASTRO --------
    with aba_cadastro:
        novo_email = st.text_input("Novo e-mail")
        nova_senha = st.text_input("Nova senha", type="password")

        if st.button("Solicitar Cadastro"):
            if novo_email in usuarios["email"].values:
                st.error("E-mail já cadastrado.")
            elif novo_email == "" or nova_senha == "":
                st.error("Preencha todos os campos.")
            else:
                novo_usuario = {
                    "email": novo_email,
                    "senha": criptografar_senha(nova_senha),
                    "perfil": "user",
                    "status": "pendente"
                }
                usuarios = pd.concat(
                    [usuarios, pd.DataFrame([novo_usuario])],
                    ignore_index=True
                )
                salvar_usuarios(usuarios)
                st.success("Cadastro enviado. Aguarde aprovação do administrador.")

    st.stop()

# ==============================
# USUÁRIO LOGADO
# ==============================
user = st.session_state.usuario

st.sidebar.success(f"Logado como: {user['email']}")

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.session_state.usuario = None
    st.rerun()

# ==============================
# PAINEL ADMIN
# ==============================
if user["perfil"] == "admin":
    st.title("🛠️ Painel do Administrador")

    usuarios = carregar_usuarios()

    st.subheader("Usuários cadastrados")
    st.dataframe(usuarios[["email", "perfil", "status"]])

    st.divider()

    st.subheader("Gerenciar Usuários")

    email_sel = st.selectbox(
        "Selecionar usuário",
        usuarios["email"].tolist()
    )

    col1, col2 = st.columns(2)

    if col1.button("Aprovar Usuário"):
        usuarios.loc[usuarios["email"] == email_sel, "status"] = "ativo"
        salvar_usuarios(usuarios)
        st.success("Usuário aprovado.")
        st.rerun()

    if col2.button("Resetar Senha"):
        nova_senha = "123456"
        usuarios.loc[
            usuarios["email"] == email_sel, "senha"
        ] = criptografar_senha(nova_senha)
        salvar_usuarios(usuarios)
        st.warning("Senha resetada para: 123456")

    st.stop()

# ==============================
# APP DO USUÁRIO
# ==============================
st.title("💰 My Finance Pro")

st.info("""
Aqui entra o seu aplicativo financeiro.

Você pode colar abaixo o código de lançamentos,
dashboard e gráficos sem mexer na parte de login.
""")

st.success("Usuário autenticado com sucesso.")
