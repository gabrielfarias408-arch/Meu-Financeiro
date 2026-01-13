import streamlit as st
import json
import os

# =============================
# CONFIGURAÇÃO INICIAL
# =============================

st.set_page_config(page_title="My Finance Pro", layout="centered")

ARQUIVO_USUARIOS = "usuarios.json"

# =============================
# FUNÇÕES AUXILIARES
# =============================

def carregar_usuarios():
    if os.path.exists(ARQUIVO_USUARIOS):
        with open(ARQUIVO_USUARIOS, "r") as f:
            return json.load(f)
    else:
        return {
            "admin": {
                "senha": "admin123",
                "aprovado": True,
                "admin": True
            }
        }

def salvar_usuarios(usuarios):
    with open(ARQUIVO_USUARIOS, "w") as f:
        json.dump(usuarios, f, indent=4)

usuarios = carregar_usuarios()

# =============================
# CONTROLE DE SESSÃO
# =============================

if "logado" not in st.session_state:
    st.session_state.logado = False

if "usuario" not in st.session_state:
    st.session_state.usuario = ""

# =============================
# TELA DE LOGIN
# =============================

if not st.session_state.logado:
    st.title("🔐 Login - My Finance Pro")

    email = st.text_input("E-mail")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if email in usuarios:
            if usuarios[email]["senha"] == senha:
                if usuarios[email]["aprovado"]:
                    st.session_state.logado = True
                    st.session_state.usuario = email
                    st.rerun()
                else:
                    st.error("Usuário ainda não aprovado pelo administrador.")
            else:
                st.error("Senha incorreta.")
        else:
            st.error("Usuário não encontrado.")

    st.markdown("---")
    st.subheader("📩 Novo usuário? Cadastre-se")

    novo_email = st.text_input("Novo e-mail")
    nova_senha = st.text_input("Nova senha", type="password")

    if st.button("Cadastrar"):
        if novo_email in usuarios:
            st.warning("Usuário já existe.")
        else:
            usuarios[novo_email] = {
                "senha": nova_senha,
                "aprovado": False,
                "admin": False
            }
            salvar_usuarios(usuarios)
            st.success("Cadastro realizado! Aguarde aprovação do administrador.")

    st.stop()

# =============================
# APP PRINCIPAL
# =============================

st.sidebar.success(f"Logado como: {st.session_state.usuario}")

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.session_state.usuario = ""
    st.rerun()

# =============================
# TELA ADMIN
# =============================

if usuarios[st.session_state.usuario]["admin"]:
    st.title("🛠 Painel do Administrador")

    st.subheader("Usuários cadastrados")

    for email, dados in usuarios.items():
        if email == "admin":
            continue

        col1, col2, col3 = st.columns(3)

        col1.write(email)
        col2.write("Aprovado" if dados["aprovado"] else "Pendente")

        if not dados["aprovado"]:
            if col3.button("Aprovar", key=email):
                usuarios[email]["aprovado"] = True
                salvar_usuarios(usuarios)
                st.rerun()

else:
    # =============================
    # TELA USUÁRIO COMUM
    # =============================

    st.title("📊 My Finance Pro")
    st.write("Bem-vindo ao aplicativo financeiro.")
    st.info("Seu acesso já foi aprovado pelo administrador.")
