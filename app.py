import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import urllib.parse
import time

# Configuração da Página
st.set_page_config(page_title="Central 24h - AD Rastreamento", layout="wide", page_icon="🔒")

# Estilização
st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: #7B2CBF; text-align: center; margin-bottom: 5px; }
    .subtitle { font-size: 18px; color: #E53935; text-align: center; margin-bottom: 25px; font-weight: 500; }
    </style>
""", unsafe_allow_html=True)

# Definições
ESTADOS_BR = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
FOLDER = "AD_Assistencia"
os.makedirs(FOLDER, exist_ok=True)
FILE_CLIENTES, FILE_EMPRESAS, FILE_PRESTADORES, FILE_OS = [os.path.join(FOLDER, f) for f in ["banco_clientes.csv", "banco_empresas.csv", "banco_prestadores.csv", "banco_os.csv"]]

def carregar_dados(caminho, colunas):
    if not os.path.exists(caminho): return pd.DataFrame(columns=colunas)
    df = pd.read_csv(caminho)
    return df

df_clientes = carregar_dados(FILE_CLIENTES, ['id','nome','cpf','tel','vei','pla','est','emp_name','status'])
df_empresas = carregar_dados(FILE_EMPRESAS, ['cnpj','nome','responsavel','telefone','email','est','status'])
df_prestadores = carregar_dados(FILE_PRESTADORES, ['id','nome','tipo','telefone','est','status'])
df_os = carregar_dados(FILE_OS, ['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os','zap_enviado'])

if "logado" not in st.session_state: st.session_state.logado = False

# LOGIN
if not st.session_state.logado:
    st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    user = st.text_input("Usuário:", key="login_user")
    pwd = st.text_input("Senha:", type="password", key="login_pwd")
    if st.button("Entrar"):
        if user == "adrastreamentoveicular" and pwd == "00000000000000":
            st.session_state.logado = True
            st.session_state.perfil = "Admin"
            st.rerun()
        else: st.error("Erro")
    st.stop()

# INTERFACE
if st.button("Sair"): st.session_state.logado = False; st.rerun()

menu = st.tabs(["📋 Nova OS", "📊 Relatórios", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores"])
with menu[0]:
    st.subheader("Nova OS")
    busca = st.text_input("Buscar Cliente:", key="busca_os")
    if busca:
        filtro = df_clientes[df_clientes['nome'].str.contains(busca, case=False, na=False)]
        if not filtro.empty:
            sel = st.selectbox("Selecione:", [f"{r['id']} - {r['nome']}" for _, r in filtro.iterrows()], key="sel_cli_os")
            c_id = sel.split(" - ")[0]
            cliente = df_clientes[df_clientes['id'].astype(str) == c_id].iloc[0]
            servico = st.selectbox("Serviço:", ["Guincho", "Pane Seca", "Pane Elétrica", "Borraceiro", "Chaveiro"], key="serv_os")
            motivo = st.selectbox("Motivo:", ["Acidente", "Furto", "Roubo", "Outros"], key="mot_os")
            prestador = st.text_input("Prestador:", key="prest_os")
            loc = st.text_input("Origem:", key="loc_os")
            dest = st.text_input("Destino:", key="dest_os")
            obs = st.text_area("Obs:", key="obs_os")
            if st.button("Gerar OS"):
                nova_id = int(df_os['id'].max() + 1) if not df_os.empty else 1
                nova_os = pd.DataFrame([{'id': nova_id, 'data_hora': datetime.now().strftime("%d/%m/%Y %H:%M"), 'cliente_id': c_id, 'cliente_nome': cliente['nome'], 'empresa': cliente['emp_name'], 'tipo_servico': servico, 'motivo': motivo, 'prestador': prestador, 'localizacao': loc, 'destino': dest, 'obs': obs, 'status_os': "EM ATENDIMENTO", 'zap_enviado': "NÃO"}])
                df_os = pd.concat([df_os, nova_os], ignore_index=True)
                df_os.to_csv(FILE_OS, index=False)
                st.success("OS Gerada com sucesso!")
                st.rerun()

with menu[1]:
    st.subheader("Relatórios & Despacho")
    for idx, row in df_os.sort_values(by='id', ascending=False).iterrows():
        if str(row['status_os']) == "EM ATENDIMENTO":
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"OS {row['id']} | {row['cliente_nome']} | {row['prestador']}")
            with col2:
                tel = "".join(filter(str.isdigit, str(row['prestador'])))
                link = f"https://api.whatsapp.com/send?phone=55{tel}&text=OS%20{row['id']}%20-%20Servico:%20{row['tipo_servico']}"
                st.markdown(f'<a href="{link}" target="_blank">📲 Despachar</a>', unsafe_allow_html=True)
                if st.button("Encerrar", key=f"enc_{row['id']}"):
                    df_os.loc[idx, 'status_os'] = "ENCERRADO"
                    df_os.to_csv(FILE_OS, index=False)
                    st.rerun()
            st.markdown("---")
        else:
            st.write(f"OS {row['id']} - ENCERRADA")

with menu[2]:
    st.subheader("Clientes")
    nome = st.text_input("Nome:", key="c_nome_novo")
    if st.button("Salvar Cliente"):
        novo = pd.DataFrame([{'id': int(df_clientes['id'].max()+1) if not df_clientes.empty else 1, 'nome': nome.upper(), 'cpf': '', 'tel': '', 'vei': '', 'pla': '', 'est': 'RN', 'emp_name': 'AD RASTREAMENTO VEICULAR', 'status': 'Ativo'}])
        df_clientes = pd.concat([df_clientes, novo], ignore_index=True)
        df_clientes.to_csv(FILE_CLIENTES, index=False)
        st.success("Salvo!")
