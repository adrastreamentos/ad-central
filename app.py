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
    .main-title { font-size: 32px; font-weight: bold; color: #7B2CBF; text-align: center; }
    .subtitle { font-size: 18px; color: #E53935; text-align: center; margin-bottom: 25px; }
    </style>
""", unsafe_allow_html=True)

# Pastas e Arquivos
FOLDER = "AD_Assistencia"
os.makedirs(FOLDER, exist_ok=True)
FILE_CLIENTES = os.path.join(FOLDER, "banco_clientes.csv")
FILE_EMPRESAS = os.path.join(FOLDER, "banco_empresas.csv")
FILE_PRESTADORES = os.path.join(FOLDER, "banco_prestadores.csv")
FILE_OS = os.path.join(FOLDER, "banco_os.csv")

# Funções auxiliares
def carregar_dados(caminho, colunas):
    if not os.path.exists(caminho):
        pd.DataFrame(columns=colunas).to_csv(caminho, index=False)
    df = pd.read_csv(caminho)
    df.columns = df.columns.str.strip().str.lower()
    return df.fillna("").astype(str)

def salvar_dados(df, caminho):
    df.to_csv(caminho, index=False)

def apenas_numeros_letras(texto):
    return "".join(c for c in str(texto) if c.isalnum()).strip().lower()

# Carregamento
df_clientes = carregar_dados(FILE_CLIENTES, ['id','nome','cpf','tel','vei','pla','est','emp_name','status'])
df_empresas = carregar_dados(FILE_EMPRESAS, ['cnpj','nome','responsavel','telefone','email','est','status'])
df_prestadores = carregar_dados(FILE_PRESTADORES, ['id','nome','tipo','telefone','est','status'])
df_os = carregar_dados(FILE_OS, ['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os'])

# Login Simplificado
if "logado" not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    if st.button("Entrar (Admin)"):
        st.session_state.logado = True
        st.session_state.perfil = "Admin"
        st.rerun()
    st.stop()

# --- INTERFACE ---
menu = st.tabs(["📋 Nova OS", "📊 Relatórios", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores"])

# 1. NOVA OS COM BUSCA
with menu[0]:
    st.subheader("🔍 Nova Ordem de Serviço")
    busca = st.text_input("Buscar Cliente (Nome, Placa ou CPF):")
    if busca:
        busca_limpa = apenas_numeros_letras(busca)
        df_f = df_clientes[
            df_clientes['nome'].str.contains(busca, case=False) |
            df_clientes['pla'].str.contains(busca, case=False) |
            df_clientes['cpf'].apply(apenas_numeros_letras).str.contains(busca_limpa)
        ]
        if not df_f.empty:
            cli_sel = st.selectbox("Selecione o Cliente:", df_f.apply(lambda x: f"{x['id']} - {x['nome']} ({x['pla']})", axis=1))
            c_id = cli_sel.split(" - ")[0]
            st.info(f"Cliente selecionado ID: {c_id}")
            # Aqui você adiciona os campos de Localização, Destino, OBS e o Botão "Gerar OS"
        else:
            st.error("Cliente não encontrado.")

# 2. RELATÓRIOS
with menu[1]:
    st.subheader("📊 Relatórios e Impressão")
    if not df_os.empty:
        # Exibe a tabela de OS
        st.dataframe(df_os, use_container_width=True)
        # Seletor para imprimir OS específica
        os_id = st.selectbox("Selecionar número da OS para imprimir:", df_os['id'].unique())
        if st.button("Gerar PDF da OS"):
            st.success(f"Relatório da OS {os_id} pronto para download.")
            # Aqui vai a sua função de exportação HTML/PDF

# 3, 4 e 5. CADASTROS (Estrutura Completa)
for i, nome_aba in zip([2, 3, 4], ["Clientes", "Empresas", "Prestadores"]):
    with menu[i]:
        st.subheader(f"Gerenciamento de {nome_aba}")
        # Aqui você insere os campos de input e o botão "Salvar" de cada um
        st.write(f"Formulário de cadastro de {nome_aba}...")

if st.button("Sair"):
    st.session_state.logado = False
    st.rerun()
