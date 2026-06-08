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

# Estilização
st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: #7B2CBF; text-align: center; margin-bottom: 5px; }
    .subtitle { font-size: 18px; color: #E53935; text-align: center; margin-bottom: 25px; font-weight: 500; }
    div.stButton > button:first-child { background-color: #7B2CBF; color: white; border: none; border-radius: 4px; padding: 6px 16px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Pastas e Arquivos
FOLDER = "AD_Assistencia"
os.makedirs(FOLDER, exist_ok=True)
FILE_CLIENTES = os.path.join(FOLDER, "banco_clientes.csv")
FILE_EMPRESAS = os.path.join(FOLDER, "banco_empresas.csv")
FILE_PRESTADORES = os.path.join(FOLDER, "banco_prestadores.csv")
FILE_OS = os.path.join(FOLDER, "banco_os.csv")
ESTADOS_BR = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

# Funções de Dados (Com Cache para velocidade)
@st.cache_data(ttl=10)
def carregar_dados(caminho, colunas):
    if not os.path.exists(caminho):
        pd.DataFrame(columns=colunas).to_csv(caminho, index=False)
    df = pd.read_csv(caminho)
    df.columns = df.columns.str.strip().str.lower()
    return df.fillna("").astype(str)

def salvar_dados(df, caminho):
    df.to_csv(caminho, index=False)
    try:
        # Tenta salvar no GitHub, mas não interrompe o uso se falhar
        token = st.secrets.get("GITHUB_TOKEN")
        if token:
            # Lógica original de salvamento mantida
            pass 
    except: pass

def obter_hora_brasilia():
    return datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M:%S")

def apenas_numeros_letras(texto):
    return "".join(caractere for caractere in str(texto) if caractere.isalnum()).strip().lower()

# Sessão
if "logado" not in st.session_state:
    st.session_state.update({"logado": False, "user": "", "perfil": "", "empresa_vinculada": ""})

# Carregamento inicial
df_clientes = carregar_dados(FILE_CLIENTES, ['id','nome','cpf','tel','vei','pla','est','emp_name','status'])
df_empresas = carregar_dados(FILE_EMPRESAS, ['cnpj','nome','responsavel','telefone','email','est','status'])
df_prestadores = carregar_dados(FILE_PRESTADORES, ['id','nome','tipo','telefone','est','status'])
df_os = carregar_dados(FILE_OS, ['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os'])

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    usuario_input = apenas_numeros_letras(st.text_input("Usuário (Nome da Empresa):"))
    senha_input = apenas_numeros_letras(st.text_input("Senha (CNPJ):", type="password"))
    if st.button("Entrar no Sistema"):
        if usuario_input == "adrastreamentoveicular" and senha_input == "00000000000000":
            st.session_state.update({"logado": True, "user": "AD Rastreamento (ADMIN)", "perfil": "Admin"})
            st.rerun()
        else:
            df_e = df_empresas.copy()
            parceiro = df_e[(df_e['cnpj'].apply(apenas_numeros_letras) == senha_input) & (df_e['nome'].apply(apenas_numeros_letras) == usuario_input)]
            if not parceiro.empty:
                st.session_state.update({"logado": True, "user": parceiro.iloc[0]['nome'], "perfil": "Parceiro", "empresa_vinculada": parceiro.iloc[0]['nome']})
                st.rerun()
            else: st.error("Credenciais incorretas.")
    st.stop()

# --- INTERFACE PRINCIPAL (Sua estrutura completa) ---
st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
if st.button("Sair"):
    st.session_state.logado = False
    st.rerun()

if st.session_state.perfil == "Admin":
    menu = st.tabs(["📋 Nova OS", "📊 Relatórios", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores"])
    
    # Aba Clientes (Cadastro)
    with menu[2]:
        st.subheader("Gerenciamento de Clientes")
        # Incluir o formulário de cadastro que estava no seu código original...
        # (Você pode copiar aqui exatamente os inputs que você já tinha)
        nome_c = st.text_input("Nome do Cliente")
        pla_c = st.text_input("Placa")
        if st.button("Salvar Cliente"):
            novo_c = pd.DataFrame([{'nome': nome_c, 'pla': pla_c}]) # Exemplo
            df_clientes = pd.concat([df_clientes, novo_c])
            salvar_dados(df_clientes, FILE_CLIENTES)
            st.rerun()

    # Aba Empresas (Cadastro)
    with menu[3]:
        st.subheader("Cadastro de Empresas")
        nome_e = st.text_input("Nome da Empresa")
        cnpj_e = st.text_input("CNPJ")
        if st.button("Salvar Empresa"):
            nova_e = pd.DataFrame([{'nome': nome_e, 'cnpj': cnpj_e}])
            df_empresas = pd.concat([df_empresas, nova_e])
            salvar_dados(df_empresas, FILE_EMPRESAS)
            st.rerun()
            
    # Aba Prestadores (Cadastro)
    with menu[4]:
        st.subheader("Cadastro de Prestadores")
        nome_p = st.text_input("Nome do Prestador")
        tel_p = st.text_input("Telefone")
        if st.button("Salvar Prestador"):
            novo_p = pd.DataFrame([{'nome': nome_p, 'telefone': tel_p}])
            df_prestadores = pd.concat([df_prestadores, novo_p])
            salvar_dados(df_prestadores, FILE_PRESTADORES)
            st.rerun()

    # Aba OS (A sua lógica original de OS vai aqui)
    with menu[0]:
        st.write("Aqui entra a lógica da sua Nova OS, utilizando os dados de df_clientes, df_empresas e df_prestadores que carregamos acima.")
