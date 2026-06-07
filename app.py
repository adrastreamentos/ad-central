import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import urllib.parse
import base64
import time
import requests

st.set_page_config(page_title="Central 24h - AD Rastreamento", layout="wide", page_icon="🔒")

# Estilização
st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: #7B2CBF; text-align: center; margin-bottom: 5px; }
    .subtitle { font-size: 18px; color: #E53935; text-align: center; margin-bottom: 25px; font-weight: 500; }
    </style>
""", unsafe_allow_html=True)

ESTADOS_BR = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
SERVICOS_DISPONIVEIS = ["Guincho", "Pane Seca", "Pane Elétrica", "Borraceiro", "Chaveiro"]

FOLDER = "AD_Assistencia"
os.makedirs(FOLDER, exist_ok=True)
FILE_CLIENTES = os.path.join(FOLDER, "banco_clientes.csv")
FILE_EMPRESAS = os.path.join(FOLDER, "banco_empresas.csv")
FILE_PRESTADORES = os.path.join(FOLDER, "banco_prestadores.csv")
FILE_OS = os.path.join(FOLDER, "banco_os.csv")

def obter_hora_brasilia():
    return datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M:%S")

def apenas_numeros_letras(texto):
    return "".join(caractere for caractere in str(texto) if caractere.isalnum()).strip().lower()

def carregar_dados(caminho, colunas):
    if not os.path.exists(caminho): return pd.DataFrame(columns=colunas)
    df = pd.read_csv(caminho)
    df.columns = df.columns.str.lower()
    return df

def salvar_dados(df, caminho):
    df.to_csv(caminho, index=False)

def colorir_status(val):
    return 'color: green; font-weight: bold;' if val == 'Ativo' else 'color: red; font-weight: bold;'

# Carregamento
df_clientes = carregar_dados(FILE_CLIENTES, ['id','nome','cpf','tel','vei','pla','est','emp_name','status'])
df_empresas = carregar_dados(FILE_EMPRESAS, ['cnpj','nome','responsavel','telefone','email','est','status'])
df_prestadores = carregar_dados(FILE_PRESTADORES, ['id','nome','tipo','telefone','est','status'])
df_os = carregar_dados(FILE_OS, ['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os','zap_enviado'])

if "logado" not in st.session_state: st.session_state.logado = False

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
            else: st.error("Erro")
    st.stop()

if st.button("Sair"):
    st.session_state.logado = False
    st.rerun()

if st.session_state.perfil == "Admin":
    menu = st.tabs(["📋 Nova OS", "📊 Relatórios", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores"])
    with menu[0]:
        st.subheader("Nova OS")
        busca = st.text_input("Buscar Cliente (Nome/Placa/CPF):")
        if busca:
            filtro = df_clientes[df_clientes['nome'].str.contains(busca, case=False) | df_clientes['pla'].str.contains(busca, case=False)]
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
                    nova_os = pd.DataFrame([{'id': nova_id, 'data_hora': obter_hora_brasilia(), 'cliente_id': c_id, 'cliente_nome': cliente['nome'], 'empresa': cliente['emp_name'], 'tipo_servico': servico, 'motivo': motivo, 'prestador': prestador, 'localizacao': loc, 'destino': dest, 'obs': obs, 'status_os': "EM ATENDIMENTO", 'zap_enviado': "NÃO"}])
                    df_os = pd.concat([df_os, nova_os], ignore_index=True)
                    salvar_dados(df_os, FILE_OS)
                    st.success("OS Gerada!")
                    st.rerun()

    with menu[2]:
        st.subheader("Gerenciamento de Clientes")
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
        est = st.selectbox("UF:", ESTADOS_BR, index=ESTADOS_BR.index(dados_ant['est']) if dados_ant is not None else 19)
        emp = st.selectbox("Empresa:", ["AD RASTREAMENTO VEICULAR"] + list(df_empresas['nome'].unique()), index=0)
        
        if st.button("Salvar Cliente"):
            if not modo:
                prox = int(df_clientes['id'].max() + 1) if not df_clientes.empty else 1
                novo = pd.DataFrame([{'id': prox, 'nome': nome.upper(), 'cpf': cpf, 'tel': tel, 'vei': vei.upper(), 'pla': pla.upper(), 'est': est, 'emp_name': emp.upper(), 'status': 'Ativo'}])
                df_clientes = pd.concat([df_clientes, novo], ignore_index=True)
            else:
                df_clientes.loc[df_clientes['id'].astype(str) == str(dados_ant['id']), ['nome','cpf','tel','vei','pla','est','emp_name']] = [nome.upper(), cpf, tel, vei.upper(), pla.upper(), est, emp.upper()]
            salvar_dados(df_clientes, FILE_CLIENTES)
            st.success("Salvo!")
            st.rerun()

    with menu[3]:
        st.subheader("Empresas")
        modo_e = st.checkbox("Editar empresa existente")
        dados_e_ant = None
        if modo_e and not df_empresas.empty:
            sel_e = st.selectbox("Selecione:", [f"{r['cnpj']} - {r['nome']}" for _, r in df_empresas.iterrows()])
            dados_e_ant = df_empresas[df_empresas['cnpj'].astype(str) == sel_e.split(" - ")[0]].iloc[0]
            
        cnpj = st.text_input("CNPJ:", value=str(dados_e_ant['cnpj']) if dados_e_ant is not None else "")
        n_emp = st.text_input("Nome:", value=str(dados_e_ant['nome']) if dados_e_ant is not None else "")
        resp = st.text_input("Responsável:", value=str(dados_e_ant['responsavel']) if dados_e_ant is not None else "")
        telefone = st.text_input("Telefone:", value=str(dados_e_ant['telefone']) if dados_e_ant is not None else "")
        email = st.text_input("E-mail:", value=str(dados_e_ant['email']) if dados_e_ant is not None else "")
        est_e = st.selectbox("UF:", ESTADOS_BR, index=ESTADOS_BR.index(dados_e_ant['est']) if dados_e_ant is not None else 19)
        
        if st.button("Salvar Empresa"):
            if not modo_e:
                novo_e = pd.DataFrame([{'cnpj': cnpj, 'nome': n_emp.upper(), 'responsavel': resp.upper(), 'telefone': telefone, 'email': email, 'est': est_e, 'status': 'Ativo'}])
                df_empresas = pd.concat([df_empresas, novo_e], ignore_index=True)
            else:
                df_empresas.loc[df_empresas['cnpj'].astype(str) == str(dados_e_ant['cnpj']), ['cnpj', 'nome','responsavel','telefone','email','est']] = [cnpj, n_emp.upper(), resp.upper(), telefone, email, est_e]
            salvar_dados(df_empresas, FILE_EMPRESAS)
            st.success("Salvo!")
            st.rerun()

    with menu[4]:
        st.subheader("Prestadores")
        modo_p = st.checkbox("Editar prestador existente")
        dados_p_ant = None
        if modo_p and not df_prestadores.empty:
            sel_p = st.selectbox("Selecione:", [f"{r['id']} - {r['nome']}" for _, r in df_prestadores.iterrows()])
            dados_p_ant = df_prestadores[df_prestadores['id'].astype(str) == sel_p.split(" - ")[0]].iloc[0]
            
        n_prest = st.text_input("Nome:", value=str(dados_p_ant['nome']) if dados_p_ant is not None else "")
        tel_p = st.text_input("Telefone:", value=str(dados_p_ant['telefone']) if dados_p_ant is not None else "")
        tipo = st.multiselect("Serviços:", SERVICOS_DISPONIVEIS, default=[s.strip() for s in str(dados_p_ant['tipo']).split(",")] if dados_p_ant is not None else ["Guincho"])
        est_p = st.selectbox("UF:", ESTADOS_BR, index=ESTADOS_BR.index(dados_p_ant['est']) if dados_p_ant is not None else 19)
        
        if st.button("Salvar Prestador"):
            tipo_f = ", ".join(tipo)
            if not modo_p:
                prox = int(df_prestadores['id'].max() + 1) if not df_prestadores.empty else 1
                novo_p = pd.DataFrame([{'id': prox, 'nome': n_prest.upper(), 'tipo': tipo_f, 'telefone': tel_p, 'est': est_p, 'status': 'Ativo'}])
                df_prestadores = pd.concat([df_prestadores, novo_p], ignore_index=True)
            else:
                df_prestadores.loc[df_prestadores['id'].astype(str) == str(dados_p_ant['id']), ['nome','tipo','telefone','est']] = [n_prest.upper(), tipo_f, tel_p, est_p]
            salvar_dados(df_prestadores, FILE_PRESTADORES)
            st.success("Salvo!")
            st.rerun()
