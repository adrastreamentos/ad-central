import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import urllib.parse
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

# Definições de caminhos e arquivos
FOLDER = "AD_Assistencia"
os.makedirs(FOLDER, exist_ok=True)
FILE_CLIENTES = os.path.join(FOLDER, "banco_clientes.csv")
FILE_EMPRESAS = os.path.join(FOLDER, "banco_empresas.csv")
FILE_PRESTADORES = os.path.join(FOLDER, "banco_prestadores.csv")
FILE_OS = os.path.join(FOLDER, "banco_os.csv")
ESTADOS_BR = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
SERVICOS = ["Guincho", "Pane Seca", "Pane Elétrica", "Borraceiro", "Chaveiro"]

# Funções Auxiliares
def carregar(f, cols):
    if not os.path.exists(f): return pd.DataFrame(columns=cols)
    return pd.read_csv(f)

def salvar(df, f): df.to_csv(f, index=False)

# Carregamento dos dados
df_c = carregar(FILE_CLIENTES, ['id','nome','cpf','tel','vei','pla','est','emp_name','status'])
df_e = carregar(FILE_EMPRESAS, ['cnpj','nome','responsavel','telefone','email','est','status'])
df_p = carregar(FILE_PRESTADORES, ['id','nome','tipo','telefone','est','status'])
df_os = carregar(FILE_OS, ['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os','zap_enviado'])

if "logado" not in st.session_state: st.session_state.logado = False

# LOGIN
if not st.session_state.logado:
    st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Login de Acesso</div>', unsafe_allow_html=True)
    user = st.text_input("Usuário (Nome da Empresa):")
    pwd = st.text_input("Senha (CNPJ):", type="password")
    if st.button("Entrar"):
        if user == "AD Rastreamento" and pwd == "00000000000000":
            st.session_state.logado = True
            st.session_state.perfil = "Admin"
            st.rerun()
        else: st.error("Dados incorretos")
    st.stop()

# INTERFACE PRINCIPAL
if st.sidebar.button("Sair"): st.session_state.logado = False; st.rerun()

menu = st.tabs(["📋 Nova OS", "📊 Relatórios", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores"])

# ABA: NOVA OS
with menu[0]:
    st.subheader("Nova OS")
    busca = st.text_input("Buscar Cliente:")
    if busca:
        filtro = df_c[df_c['nome'].str.contains(busca, case=False, na=False)]
        sel = st.selectbox("Selecione o Cliente:", [f"{r['id']} - {r['nome']}" for _, r in filtro.iterrows()])
        c_id = sel.split(" - ")[0]
        cliente = df_c[df_c['id'].astype(str) == c_id].iloc[0]
        
        serv = st.selectbox("Serviço:", SERVICOS)
        motivo = st.selectbox("Motivo:", ["Acidente", "Furto", "Roubo", "Outros"])
        prest = st.text_input("Prestador:")
        loc = st.text_input("Origem:")
        dest = st.text_input("Destino:")
        obs = st.text_area("Obs:")
        
        if st.button("Gerar OS"):
            nova_id = int(df_os['id'].max() + 1) if not df_os.empty else 1
            nova_os = pd.DataFrame([{'id': nova_id, 'data_hora': datetime.now().strftime("%d/%m/%Y %H:%M"), 'cliente_id': c_id, 'cliente_nome': cliente['nome'], 'empresa': cliente['emp_name'], 'tipo_servico': serv, 'motivo': motivo, 'prestador': prest, 'localizacao': loc, 'destino': dest, 'obs': obs, 'status_os': "EM ATENDIMENTO", 'zap_enviado': "NÃO"}])
            df_os = pd.concat([df_os, nova_os], ignore_index=True)
            salvar(df_os, FILE_OS)
            st.success("OS Gerada com sucesso!")
            st.rerun()

# ABA: RELATÓRIOS
with menu[1]:
    st.subheader("Relatórios e Despacho")
    for idx, row in df_os.sort_values(by='id', ascending=False).iterrows():
        if str(row['status_os']) == "EM ATENDIMENTO":
            col1, col2 = st.columns([3, 1])
            with col1: st.write(f"OS {row['id']} | {row['cliente_nome']} | {row['prestador']}")
            with col2:
                tel = "".join(filter(str.isdigit, str(row['prestador'])))
                link = f"https://api.whatsapp.com/send?phone=55{tel}&text=OS%20{row['id']}"
                st.markdown(f'<a href="{link}" target="_blank">📲 Despachar</a>', unsafe_allow_html=True)
                if st.button("Encerrar", key=f"enc_{row['id']}"):
                    df_os.loc[idx, 'status_os'] = "ENCERRADO"
                    salvar(df_os, FILE_OS)
                    st.rerun()
            st.markdown("---")

# ABA: CLIENTES
with menu[2]:
    st.subheader("Gerenciamento de Clientes")
    modo = st.checkbox("Editar cliente existente")
    dados = None
    if modo:
        sel = st.selectbox("Selecione:", [f"{r['id']} - {r['nome']}" for _, r in df_c.iterrows()])
        dados = df_c[df_c['id'].astype(str) == sel.split(" - ")[0]].iloc[0]
    
    n = st.text_input("Nome:", value=dados['nome'] if dados is not None else "")
    c = st.text_input("CPF:", value=dados['cpf'] if dados is not None else "")
    t = st.text_input("Tel:", value=dados['tel'] if dados is not None else "")
    v = st.text_input("Veículo:", value=dados['vei'] if dados is not None else "")
    p = st.text_input("Placa:", value=dados['pla'] if dados is not None else "")
    
    if st.button("Salvar Cliente"):
        if not modo:
            novo = pd.DataFrame([{'id': int(df_c['id'].max()+1) if not df_c.empty else 1, 'nome': n.upper(), 'cpf': c, 'tel': t, 'vei': v.upper(), 'pla': p.upper(), 'est': 'RN', 'emp_name': 'AD', 'status': 'Ativo'}])
            df_c = pd.concat([df_c, novo], ignore_index=True)
        else:
            df_c.loc[df_c['id'].astype(str) == str(dados['id']), ['nome','cpf','tel','vei','pla']] = [n.upper(), c, t, v.upper(), p.upper()]
        salvar(df_c, FILE_CLIENTES)
        st.success("Salvo com sucesso!")
        st.rerun()
    if modo and dados is not None and st.button("Excluir Cliente"):
        df_c = df_c[df_c['id'].astype(str) != str(dados['id'])]
        salvar(df_c, FILE_CLIENTES)
        st.error("Excluído!")
        st.rerun()

# ABA: EMPRESAS
with menu[3]:
    st.subheader("Empresas")
    modo_e = st.checkbox("Editar empresa existente")
    dados_e = None
    if modo_e:
        sel_e = st.selectbox("Selecione:", [f"{r['cnpj']} - {r['nome']}" for _, r in df_e.iterrows()])
        dados_e = df_e[df_e['cnpj'].astype(str) == sel_e.split(" - ")[0]].iloc[0]
    
    cnpj = st.text_input("CNPJ:", value=str(dados_e['cnpj']) if dados_e is not None else "")
    nome_e = st.text_input("Nome:", value=str(dados_e['nome']) if dados_e is not None else "")
    
    if st.button("Salvar Empresa"):
        if not modo_e:
            novo_e = pd.DataFrame([{'cnpj': cnpj, 'nome': nome_e.upper(), 'responsavel': '', 'telefone': '', 'email': '', 'est': 'RN', 'status': 'Ativo'}])
            df_e = pd.concat([df_e, novo_e], ignore_index=True)
        else:
            df_e.loc[df_e['cnpj'].astype(str) == str(dados_e['cnpj']), ['nome']] = [nome_e.upper()]
        salvar(df_e, FILE_EMPRESAS)
        st.success("Salvo com sucesso!")
        st.rerun()
    if modo_e and dados_e is not None and st.button("Excluir Empresa"):
        df_e = df_e[df_e['cnpj'].astype(str) != str(dados_e['cnpj'])]
        salvar(df_e, FILE_EMPRESAS)
        st.error("Excluído!")
        st.rerun()

# ABA: PRESTADORES
with menu[4]:
    st.subheader("Prestadores")
    modo_p = st.checkbox("Editar existente")
    dados_p = None
    if modo_p:
        sel_p = st.selectbox("Selecione:", [f"{r['id']} - {r['nome']}" for _, r in df_p.iterrows()])
        dados_p = df_p[df_p['id'].astype(str) == sel_p.split(" - ")[0]].iloc[0]
        
    n_p = st.text_input("Nome:", value=str(dados_p['nome']) if dados_p is not None else "")
    if st.button("Salvar Prestador"):
        if not modo_p:
            novo_p = pd.DataFrame([{'id': int(df_p['id'].max()+1) if not df_p.empty else 1, 'nome': n_p.upper(), 'tipo': 'Guincho', 'telefone': '', 'est': 'RN', 'status': 'Ativo'}])
            df_p = pd.concat([df_p, novo_p], ignore_index=True)
        else:
            df_p.loc[df_p['id'].astype(str) == str(dados_p['id']), ['nome']] = [n_p.upper()]
        salvar(df_p, FILE_PRESTADORES)
        st.success("Salvo com sucesso!")
        st.rerun()
    if modo_p and dados_p is not None and st.button("Excluir Prestador"):
        df_p = df_p[df_p['id'].astype(str) != str(dados_p['id'])]
        salvar(df_p, FILE_PRESTADORES)
        st.error("Excluído!")
        st.rerun()
