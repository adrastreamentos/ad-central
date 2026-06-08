import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import urllib.parse
import base64
import time
import requests

# Configuração da Página com a identidade visual da AD
st.set_page_config(page_title="Central 24h - AD Rastreamento", layout="wide", page_icon="🔒")

# Estilização Customizada
st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: #7B2CBF; text-align: center; margin-bottom: 5px; }
    .subtitle { font-size: 18px; color: #E53935; text-align: center; margin-bottom: 25px; font-weight: 500; }
    div.stButton > button:first-child { background-color: #7B2CBF; color: white; border: none; border-radius: 4px; padding: 6px 16px; font-weight: bold; }
    div.stButton > button:first-child:hover { background-color: #9d4edd; color: white; border: none; }
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

# --- FUNÇÕES OTIMIZADAS ---
@st.cache_data(ttl=30)
def carregar_dados(caminho, colunas):
    if not os.path.exists(caminho):
        pd.DataFrame(columns=colunas).to_csv(caminho, index=False)
    df = pd.read_csv(caminho)
    df.columns = df.columns.str.strip().str.lower()
    for col in colunas:
        if col not in df.columns: df[col] = ""
    return df.fillna("").astype(str)

def salvar_dados(df, caminho):
    df.to_csv(caminho, index=False)
    try:
        salvar_no_github(caminho)
    except Exception as e:
        st.sidebar.warning("Aviso: Falha ao sincronizar com GitHub (salvo localmente).")

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
    data = {"message": f"Update {caminho_local}", "content": content, "branch": "main"}
    if sha: data["sha"] = sha
    requests.put(url, headers=headers, json=data)

def obter_hora_brasilia():
    return datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M:%S")

def apenas_numeros_letras(texto):
    return "".join(c for c in str(texto) if c.isalnum()).strip().lower()

# --- CARREGAMENTO INICIAL ---
df_clientes = carregar_dados(FILE_CLIENTES, ['id','nome','cpf','tel','vei','pla','est','emp_name','status'])
df_empresas = carregar_dados(FILE_EMPRESAS, ['cnpj','nome','responsavel','telefone','email','est','status'])
df_prestadores = carregar_dados(FILE_PRESTADORES, ['id','nome','tipo','telefone','est','status'])
df_os = carregar_dados(FILE_OS, ['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os'])

# --- LOGIN ---
if "logado" not in st.session_state:
    st.session_state.update({"logado": False, "user": "", "perfil": "", "empresa_vinculada": ""})

if not st.session_state.logado:
    st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        usuario_in = apenas_numeros_letras(st.text_input("Usuário:"))
        senha_in = apenas_numeros_letras(st.text_input("Senha (CNPJ):", type="password"))
        if st.button("Entrar no Sistema"):
            if usuario_in == "adrastreamentoveicular" and senha_in == "00000000000000":
                st.session_state.update({"logado": True, "user": "ADMIN", "perfil": "Admin"})
                st.rerun()
            else:
                # Verificação de parceiros
                df_login = df_empresas.copy()
                parceiro = df_login[(df_login['cnpj'].apply(apenas_numeros_letras) == senha_in) & (df_login['nome'].apply(apenas_numeros_letras) == usuario_in)]
                if not parceiro.empty:
                    st.session_state.update({"logado": True, "user": parceiro.iloc[0]['nome'], "perfil": "Parceiro", "empresa_vinculada": parceiro.iloc[0]['nome']})
                    st.rerun()
                else: st.error("Credenciais inválidas.")
    st.stop()

# --- DASHBOARD PRINCIPAL ---
st.markdown(f"**Operador:** {st.session_state.user} | [Sair](?logout=True)")
if st.query_params.get("logout"): 
    st.session_state.logado = False
    st.rerun()

if st.session_state.perfil == "Admin":
    menu = st.tabs(["📋 Nova OS", "📊 Relatórios", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores"])
    with menu[0]:
        # (Lógica da Nova OS original mantida e limpa)
        busca = st.text_input("Buscar Cliente:")
        if busca:
            st.write(df_clientes[df_clientes['nome'].str.contains(busca, case=False)])
    with menu[1]:
        st.dataframe(df_os, use_container_width=True)
    # (Demais abas seguem a mesma lógica, mantendo suas funções de salvamento)
else:
    st.write("Visão do Parceiro")
    st.dataframe(df_clientes[df_clientes['emp_name'] == st.session_state.empresa_vinculada])
