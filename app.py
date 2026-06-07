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
    </style>
""", unsafe_allow_html=True)

# Configurações e Carregamento de dados (Mantendo estrutura intacta)
ESTADOS_BR = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
SERVICOS_DISPONIVEIS = ["Guincho", "Pane Seca", "Pane Elétrica", "Borraceiro", "Chaveiro"]
FOLDER = "AD_Assistencia"
os.makedirs(FOLDER, exist_ok=True)
FILE_CLIENTES = os.path.join(FOLDER, "banco_clientes.csv")
FILE_EMPRESAS = os.path.join(FOLDER, "banco_empresas.csv")
FILE_PRESTADORES = os.path.join(FOLDER, "banco_prestadores.csv")
FILE_OS = os.path.join(FOLDER, "banco_os.csv")

def obter_hora_brasilia(): return datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M:%S")
def apenas_numeros_letras(texto): return "".join(c for c in str(texto) if c.isalnum()).strip().lower()

def carregar_dados(caminho, colunas):
    if not os.path.exists(caminho): return pd.DataFrame(columns=colunas)
    df = pd.read_csv(caminho)
    df.columns = df.columns.str.lower()
    return df

def salvar_dados(df, caminho): df.to_csv(caminho, index=False)

df_clientes = carregar_dados(FILE_CLIENTES, ['id','nome','cpf','tel','vei','pla','est','emp_name','status'])
df_empresas = carregar_dados(FILE_EMPRESAS, ['cnpj','nome','responsavel','telefone','email','est','status'])
df_prestadores = carregar_dados(FILE_PRESTADORES, ['id','nome','tipo','telefone','est','status'])
df_os = carregar_dados(FILE_OS, ['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os','zap_enviado'])

if "logado" not in st.session_state: st.session_state.logado = False

# LOGIN
if not st.session_state.logado:
    st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    user = st.text_input("Usuário:")
    pwd = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        if user == "adrastreamentoveicular" and pwd == "00000000000000":
            st.session_state.logado = True
            st.session_state.perfil = "Admin"
            st.rerun()
        else:
            df_e = df_empresas[df_empresas['nome'].str.lower() == user.lower()]
            if not df_e.empty and str(df_e.iloc[0]['cnpj']) == pwd:
                st.session_state.logado = True
                st.session_state.perfil = "Parceiro"
                st.session_state.empresa_vinculada = df_e.iloc[0]['nome']
                st.rerun()
            else: st.error("Erro no login")
    st.stop()

# INTERFACE INTERNA (ADM/PARCEIRO)
if st.button("Sair"):
    st.session_state.logado = False
    st.rerun()

if st.session_state.perfil == "Admin":
    menu = st.tabs(["📋 Nova OS", "📊 Relatórios", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores"])
    with menu[0]:
        busca = st.text_input("Buscar Cliente:")
        if busca:
            filtro = df_clientes[df_clientes['nome'].str.contains(busca, case=False)]
            if not filtro.empty:
                sel = st.selectbox("Selecione:", [f"{r['id']} - {r['nome']}" for _, r in filtro.iterrows()])
                c_id = sel.split(" - ")[0]
                cliente = df_clientes[df_clientes['id'].astype(str) == c_id].iloc[0]
                servico = st.selectbox("Serviço:", SERVICOS_DISPONIVEIS)
                motivo = st.selectbox("Motivo:", ["Acidente", "Furto", "Roubo", "Outros"])
                prestador = st.text_input("Prestador:")
                loc = st.text_input("Origem:")
                dest = st.text_input("Destino:")
                obs = st.text_area("Obs:")
                if st.button("Gerar OS"):
                    nova_id = int(df_os['id'].max() + 1) if not df_os.empty else 1
                    novo_chamado = pd.DataFrame([{'id': nova_id, 'data_hora': obter_hora_brasilia(), 'cliente_id': c_id, 'cliente_nome': cliente['nome'], 'empresa': cliente['emp_name'], 'tipo_servico': servico, 'motivo': motivo, 'prestador': prestador, 'localizacao': loc, 'destino': dest, 'obs': obs, 'status_os': "EM ATENDIMENTO", 'zap_enviado': "NÃO"}])
                    df_os = pd.concat([df_os, novo_chamado], ignore_index=True)
                    salvar_dados(df_os, FILE_OS)
                    st.success("OS Gerada!")
                    st.rerun()

    with menu[2]:
        modo = st.checkbox("Editar cliente existente")
        dados_ant = None
        if modo and not df_clientes.empty:
            sel = st.selectbox("Selecione:", [f"{r['id']} - {r['nome']}" for _, r in df_clientes.iterrows()])
            dados_ant = df_clientes[df_clientes['id'].astype(str) == sel.split(" - ")[0]].iloc[0]
        
        nome = st.text_input("Nome:", value=dados_ant['nome'] if dados_ant is not None else "")
        cpf = st.text_input("CPF:", value=dados_ant['cpf'] if dados_ant is not None else "")
        tel = st.text_input("Tel:", value=dados_ant['tel'] if dados_ant is not None else "")
        vei = st.text_input("Veículo:", value=dados_ant['vei'] if dados_ant is not None else "")
        pla = st.text_input("Placa:", value=dados_ant['pla'] if dados_ant is not None else "")
        est = st.selectbox("UF:", ESTADOS_BR, index=ESTADOS_BR.index(dados_ant['est']) if dados_ant is not None and dados_ant['est'] in ESTADOS_BR else 19)
        emp = st.selectbox("Empresa:", ["AD RASTREAMENTO VEICULAR"] + list(df_empresas['nome'].unique()))
        
        if st.button("Salvar"):
            if not modo:
                novo = pd.DataFrame([{'id': int(df_clientes['id'].max() + 1) if not df_clientes.empty else 1, 'nome': nome.upper(), 'cpf': cpf, 'tel': tel, 'vei': vei.upper(), 'pla': pla.upper(), 'est': est, 'emp_name': emp.upper(), 'status': 'Ativo'}])
                df_clientes = pd.concat([df_clientes, novo], ignore_index=True)
            else:
                df_clientes.loc[df_clientes['id'].astype(str) == str(dados_ant['id']), ['nome','cpf','tel','vei','pla','est','emp_name']] = [nome.upper(), cpf, tel, vei.upper(), pla.upper(), est, emp.upper()]
            salvar_dados(df_clientes, FILE_CLIENTES)
            st.success("Salvo!")
            st.rerun()

    with menu[3]:
        modo_e = st.checkbox("Editar empresa existente")
        dados_e_ant = None
        if modo_e and not df_empresas.empty:
            sel_e = st.selectbox("Selecione:", [f"{r['cnpj']} - {r['nome']}" for _, r in df_empresas.iterrows()])
            dados_e_ant = df_empresas[df_empresas['cnpj'].astype(str) == sel_e.split(" - ")[0]].iloc[0]
            
        cnpj = st.text_input("CNPJ:", value=str(dados_e_ant['cnpj']) if dados_e_ant is not None else "")
        nome_e = st.text_input("Nome:", value=str(dados_e_ant['nome']) if dados_e_ant is not None else "")
        resp = st.text_input("Responsável:", value=str(dados_e_ant['responsavel']) if dados_e_ant is not None else "")
        tel_e = st.text_input("Telefone:", value=str(dados_e_ant['telefone']) if dados_e_ant is not None else "")
        mail = st.text_input("E-mail:", value=str(dados_e_ant['email']) if dados_e_ant is not None else "")
        est_e = st.selectbox("UF:", ESTADOS_BR, index=ESTADOS_BR.index(dados_e_ant['est']) if dados_e_ant is not None and dados_e_ant['est'] in ESTADOS_BR else 19)
        
        if st.button("Salvar Empresa"):
            if not modo_e:
                novo = pd.DataFrame([{'cnpj': cnpj, 'nome': nome_e.upper(), 'responsavel': resp.upper(), 'telefone': tel_e, 'email': mail, 'est': est_e, 'status': 'Ativo'}])
                df_empresas = pd.concat([df_empresas, novo], ignore_index=True)
            else:
                df_empresas.loc[df_empresas['cnpj'].astype(str) == str(dados_e_ant['cnpj']), ['nome', 'responsavel', 'telefone', 'email', 'est']] = [nome_e.upper(), resp.upper(), tel_e, mail, est_e]
            salvar_dados(df_empresas, FILE_EMPRESAS)
            st.success("Salvo!")
            st.rerun()
