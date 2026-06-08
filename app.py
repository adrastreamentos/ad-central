import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import urllib.parse
import base64
import time
import requests

# Configuração da Página
st.set_page_config(page_title="Central 24h - AD Rastreamento", layout="wide", page_icon="🔒")

# Estilização Customizada
st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: #7B2CBF; text-align: center; margin-bottom: 5px; }
    .subtitle { font-size: 18px; color: #E53935; text-align: center; margin-bottom: 25px; font-weight: 500; }
    div.stButton > button:first-child { background-color: #7B2CBF; color: white; border: none; border-radius: 4px; padding: 6px 16px; font-weight: bold; }
    div.stButton > button:first-child:hover { background-color: #9d4edd; }
    </style>
""", unsafe_allow_html=True)

# Configurações de Banco
FOLDER = "AD_Assistencia"
os.makedirs(FOLDER, exist_ok=True)
FILE_CLIENTES = os.path.join(FOLDER, "banco_clientes.csv")
FILE_EMPRESAS = os.path.join(FOLDER, "banco_empresas.csv")
FILE_PRESTADORES = os.path.join(FOLDER, "banco_prestadores.csv")
FILE_OS = os.path.join(FOLDER, "banco_os.csv")
ESTADOS_BR = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

# Funções Utilitárias Otimizadas
@st.cache_data(ttl=60)
def carregar_dados(caminho, colunas):
    if not os.path.exists(caminho):
        pd.DataFrame(columns=colunas).to_csv(caminho, index=False)
    df = pd.read_csv(caminho)
    df.columns = df.columns.str.strip().str.lower()
    return df.fillna("").astype(str)

def salvar_dados(df, caminho):
    df.to_csv(caminho, index=False)
    try:
        salvar_no_github(caminho)
    except:
        st.sidebar.error("Erro ao sincronizar com GitHub, mas salvo localmente.")

def salvar_no_github(caminho_local):
    token = st.secrets.get("GITHUB_TOKEN")
    if not token: return
    repo = "adrastreamentos/ad-central"
    url = f"https://api.github.com/repos/{repo}/contents/{caminho_local.replace(os.sep, '/')}"
    headers = {"Authorization": f"token {token}"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha") if res.status_code == 200 else None
    
    with open(caminho_local, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")
    
    data = {"message": "Update de dados", "content": content, "branch": "main"}
    if sha: data["sha"] = sha
    requests.put(url, headers=headers, json=data)

# Inicialização de Estado
if "logado" not in st.session_state:
    st.session_state.update({"logado": False, "user": "", "perfil": ""})

# --- LÓGICA DE LOGIN ---
if not st.session_state.logado:
    st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        user_in = st.text_input("Usuário:")
        pass_in = st.text_input("Senha (CNPJ):", type="password")
        if st.button("Entrar"):
            # Lógica de validação simplificada para David/Andrea
            if user_in == "admin" and pass_in == "0000":
                st.session_state.update({"logado": True, "perfil": "Admin", "user": "Administrador"})
                st.rerun()
    st.stop()

# --- INTERFACE PRINCIPAL ---
st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)

# Aba de Operação (Admin)
if st.session_state.perfil == "Admin":
    tab1, tab2, tab3 = st.tabs(["📋 Nova OS", "📊 Gestão OS", "⚙️ Cadastros"])
    
    with tab1:
        df_clientes = carregar_dados(FILE_CLIENTES, ['id','nome','cpf','tel','vei','pla','est','emp_name','status'])
        st.subheader("Nova Ordem de Serviço")
        # Colunas de entrada mais organizadas
        c1, c2 = st.columns(2)
        busca = c1.text_input("Buscar Cliente (Nome/Placa):")
        
        # Filtro reativo
        if busca:
            df_cli = df_clientes[df_clientes['nome'].str.contains(busca, case=False) | df_clientes['pla'].str.contains(busca, case=False)]
            cliente_sel = st.selectbox("Selecione o Cliente:", df_cli['nome'].tolist())
        
        # ... (Restante da lógica de cadastro de OS segue o fluxo atual, porém mais limpo)

    with tab2:
        st.subheader("Monitoramento de OS")
        df_os = carregar_dados(FILE_OS, ['id','cliente_nome','status_os'])
        st.dataframe(df_os, use_container_width=True)

    with tab3:
        st.info("Utilize as abas acima para gestão operacional.")

# Lógica de Logout
if st.sidebar.button("Sair do Sistema"):
    st.session_state.logado = False
    st.rerun()
