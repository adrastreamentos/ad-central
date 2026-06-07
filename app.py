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

# Estilização Customizada - Cores Roxa e Vermelha da marca
st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: #7B2CBF; text-align: center; margin-bottom: 5px; }
    .subtitle { font-size: 18px; color: #E53935; text-align: center; margin-bottom: 25px; font-weight: 500; }
    div.stButton > button:first-child { background-color: #7B2CBF; color: white; border: none; border-radius: 4px; padding: 6px 16px; font-weight: bold; }
    div.stButton > button:first-child:hover { background-color: #9d4edd; color: white; border: none; }
    .stTabs [data-baseweb="tab"] { font-size: 16px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Lista Oficial de Estados do Brasil
ESTADOS_BR = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
SERVICOS_DISPONIVEIS = ["Guincho", "Pane Seca", "Pane Elétrica", "Borraceiro", "Chaveiro"]

# Caminhos dos arquivos de banco de dados locais
FOLDER = "AD_Assistencia"
os.makedirs(FOLDER, exist_ok=True)

FILE_CLIENTES = os.path.join(FOLDER, "banco_clientes.csv")
FILE_EMPRESAS = os.path.join(FOLDER, "banco_empresas.csv")
FILE_PRESTADORES = os.path.join(FOLDER, "banco_prestadores.csv")
FILE_OS = os.path.join(FOLDER, "banco_os.csv")

# Inicialização dos arquivos CSV caso não existam
if not os.path.exists(FILE_CLIENTES):
    pd.DataFrame(columns=['id','nome','cpf','tel','vei','pla','est','emp_name','status']).to_csv(FILE_CLIENTES, index=False)
if not os.path.exists(FILE_EMPRESAS):
    pd.DataFrame(columns=['cnpj','nome','responsavel','telefone','email','est','status']).to_csv(FILE_EMPRESAS, index=False)
if not os.path.exists(FILE_PRESTADORES):
    pd.DataFrame(columns=['id','nome','tipo','telefone','est','status']).to_csv(FILE_PRESTADORES, index=False)
if not os.path.exists(FILE_OS):
    pd.DataFrame(columns=['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os','zap_enviado']).to_csv(FILE_OS, index=False)

# Função para capturar o Horário de Brasília real (GMT-3)
def obter_hora_brasilia():
    fuso_brasilia = timezone(timedelta(hours=-3))
    return datetime.now(fuso_brasilia).strftime("%Y-%m-%d %H:%M:%S")

# Função de limpeza de documentos e textos
def apenas_numeros_letras(texto):
    return "".join(caractere for caractere in str(texto) if caractere.isalnum()).strip().lower()

# FUNÇÃO DE SALVAMENTO EM NUVEM (COFRE GITHUB)
def salvar_no_github(caminho_local):
    token = st.secrets.get("GITHUB_TOKEN", None)
    repo = "adrastreamentos/ad-central"
    if not token: return
    url = f"https://api.github.com/repos/{repo}/contents/{caminho_local.replace(os.sep, '/')}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha", None) if res.status_code == 200 else None
    with open(caminho_local, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")
    data = {"message": f"🔥 Auto-salvamento: {caminho_local}", "content": content, "branch": "main"}
    if sha: data["sha"] = sha
    requests.put(url, headers=headers, json=data)

# Funções de Leitura e Escrita
def carregar_dados(caminho, colunas_obrigatorias):
    try:
        df = pd.read_csv(caminho)
        df.columns = df.columns.str.strip().str.lower()
        for col in colunas_obrigatorias:
            if col not in df.columns: df[col] = ""
        for col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
        return df
    except:
        return pd.DataFrame(columns=colunas_obrigatorias)

def salvar_dados(df, caminho):
    df.to_csv(caminho, index=False)
    salvar_no_github(caminho)

# Gerador de Relatório
def exportar_pdf_html_oficial(df_os_rows, df_clientes_completo, titulo_pdf="relatorio"):
    cards_html = ""
    for _, row in df_os_rows.iterrows():
        cards_html += f"<div>OS: {row['id']} - {row['empresa']} - {row['prestador']}</div>"
    html = f"<html><body>{cards_html}</body></html>"
    b64 = base64.b64encode(html.encode('utf-8')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{titulo_pdf}.html">📥 Baixar Relatório</a>'

# Sessão
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.user = ""
    st.session_state.perfil = ""
    st.session_state.empresa_vinculada = ""

# Carregamento
df_clientes = carregar_dados(FILE_CLIENTES, ['id','nome','cpf','tel','vei','pla','est','emp_name','status'])
df_empresas = carregar_dados(FILE_EMPRESAS, ['cnpj','nome','responsavel','telefone','email','est','status'])
df_prestadores = carregar_dados(FILE_PRESTADORES, ['id','nome','tipo','telefone','est','status'])
df_os = carregar_dados(FILE_OS, ['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os','zap_enviado'])

# LOGIN
if not st.session_state.logado:
    st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">⚡ Operação Atendimento – AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    usuario_input = st.text_input("Usuário (Nome da Empresa):")
    senha_input = st.text_input("Senha (CNPJ):", type="password")
    if st.button("Entrar no Sistema"):
        if usuario_input == "AD Rastreamento" and senha_input == "00000000000000":
            st.session_state.logado = True
            st.session_state.perfil = "Admin"
            st.rerun()
        else: st.error("Dados incorretos")
    st.stop()

if st.button("Sair"): st.session_state.logado = False; st.rerun()

menu = st.tabs(["📋 Nova OS", "📊 Relatórios", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores"])

with menu[0]:
    st.subheader("Nova OS")
    busca = st.text_input("Buscar Cliente:")
    if busca:
        filtro = df_clientes[df_clientes['nome'].str.contains(busca, case=False, na=False)]
        if not filtro.empty:
            sel = st.selectbox("Selecione:", [f"{r['id']} - {r['nome']}" for _, r in filtro.iterrows()])
            c_id = sel.split(" - ")[0]
            cliente = df_clientes[df_clientes['id'].astype(str) == c_id].iloc[0]
            serv = st.selectbox("Serviço:", SERVICOS_DISPONIVEIS)
            motivo = st.selectbox("Motivo:", ["Acidente", "Furto", "Roubo", "Outros"])
            prest = st.text_input("Prestador:")
            loc = st.text_input("Origem:")
            dest = st.text_input("Destino:")
            obs = st.text_area("Obs:")
            if st.button("Gerar OS"):
                nova_id = int(df_os['id'].astype(float).max() + 1) if not df_os.empty else 1
                nova_os = pd.DataFrame([{'id': str(nova_id), 'data_hora': obter_hora_brasilia(), 'cliente_id': c_id, 'cliente_nome': cliente['nome'], 'empresa': cliente['emp_name'], 'tipo_servico': serv, 'motivo': motivo, 'prestador': prest, 'localizacao': loc, 'destino': dest, 'obs': obs, 'status_os': "EM ATENDIMENTO", 'zap_enviado': "NÃO"}])
                df_os = pd.concat([df_os, nova_os], ignore_index=True)
                salvar_dados(df_os, FILE_OS)
                st.success("OS Gerada!")
                st.rerun()

with menu[1]:
    st.subheader("Relatórios e Despacho")
    for idx, row in df_os.sort_values(by='id', ascending=False).iterrows():
        if str(row['status_os']).upper() == "EM ATENDIMENTO":
            st.write(f"OS {row['id']} | {row['cliente_nome']} | {row['prestador']}")
            tel = "".join(filter(str.isdigit, str(row['prestador'])))
            link = f"https://api.whatsapp.com/send?phone=55{tel}&text=OS%20{row['id']}"
            st.markdown(f'<a href="{link}" target="_blank">📲 Despachar</a>', unsafe_allow_html=True)
            if st.button("Encerrar", key=f"enc_{row['id']}"):
                df_os.loc[idx, 'status_os'] = "ENCERRADO"
                salvar_dados(df_os, FILE_OS)
                st.rerun()
            st.markdown("---")

with menu[2]:
    st.subheader("Clientes")
    modo = st.checkbox("Editar cliente")
    dados = None
    if modo and not df_clientes.empty:
        sel = st.selectbox("Selecione:", [f"{r['id']} - {r['nome']}" for _, r in df_clientes.iterrows()])
        dados = df_clientes[df_clientes['id'].astype(str) == sel.split(" - ")[0]].iloc[0]
    n = st.text_input("Nome:", value=dados['nome'] if dados is not None else "")
    c = st.text_input("CPF:", value=dados['cpf'] if dados is not None else "")
    t = st.text_input("Tel:", value=dados['tel'] if dados is not None else "")
    v = st.text_input("Veículo:", value=dados['vei'] if dados is not None else "")
    p = st.text_input("Placa:", value=dados['pla'] if dados is not None else "")
    if st.button("Salvar Cliente"):
        if not modo:
            novo = pd.DataFrame([{'id': int(df_clientes['id'].astype(float).max()+1) if not df_clientes.empty else 1, 'nome': n.upper(), 'cpf': c, 'tel': t, 'vei': v.upper(), 'pla': p.upper(), 'est': 'RN', 'emp_name': 'AD RASTREAMENTO VEICULAR', 'status': 'Ativo'}])
            df_clientes = pd.concat([df_clientes, novo], ignore_index=True)
        else:
            df_clientes.loc[df_clientes['id'].astype(str) == str(dados['id']), ['nome','cpf','tel','vei','pla']] = [n.upper(), c, t, v.upper(), p.upper()]
        salvar_dados(df_clientes, FILE_CLIENTES)
        st.success("Salvo!")
        st.rerun()
    if modo and dados is not None and st.button("Excluir Cliente"):
        df_clientes = df_clientes[df_clientes['id'].astype(str) != str(dados['id'])]
        salvar_dados(df_clientes, FILE_CLIENTES)
        st.error("🗑️ Excluído!")
        st.rerun()

with menu[3]:
    st.subheader("Empresas")
    modo_e = st.checkbox("Editar empresa")
    dados_e = None
    if modo_e and not df_empresas.empty:
        sel_e = st.selectbox("Selecione:", [f"{r['cnpj']} - {r['nome']}" for _, r in df_empresas.iterrows()])
        dados_e = df_empresas[df_empresas['cnpj'].astype(str) == sel_e.split(" - ")[0]].iloc[0]
    cnpj = st.text_input("CNPJ:", value=str(dados_e['cnpj']) if dados_e is not None else "")
    n_e = st.text_input("Nome:", value=str(dados_e['nome']) if dados_e is not None else "")
    if st.button("Salvar Empresa"):
        if not modo_e:
            novo = pd.DataFrame([{'cnpj': cnpj, 'nome': n_e.upper(), 'responsavel': '', 'telefone': '', 'email': '', 'est': 'RN', 'status': 'Ativo'}])
            df_empresas = pd.concat([df_empresas, novo], ignore_index=True)
        else:
            df_empresas.loc[df_empresas['cnpj'].astype(str) == str(dados_e['cnpj']), ['nome']] = [n_e.upper()]
        salvar_dados(df_empresas, FILE_EMPRESAS)
        st.success("Salvo!")
        st.rerun()
    if modo_e and dados_e is not None and st.button("Excluir Empresa"):
        df_empresas = df_empresas[df_empresas['cnpj'].astype(str) != str(dados_e['cnpj'])]
        salvar_dados(df_empresas, FILE_EMPRESAS)
        st.error("🗑️ Excluído!")
        st.rerun()

with menu[4]:
    st.subheader("🔧 Gerenciamento de Prestadores")
    modo_p = st.checkbox("Editar prestador")
    dados_p = None
    if modo_p and not df_prestadores.empty:
        sel_p = st.selectbox("Selecione:", [f"{r['id']} - {r['nome']}" for _, r in df_prestadores.iterrows()])
        dados_p = df_prestadores[df_prestadores['id'].astype(str) == sel_p.split(" - ")[0]].iloc[0]
    n_p = st.text_input("Nome:", value=str(dados_p['nome']) if dados_p is not None else "")
    
    # A MELHORIA SOLICITADA:
    serv_atuais = [s.strip() for s in str(dados_p['tipo']).split(",")] if dados_p is not None else ["Guincho"]
    tipos_sel = st.multiselect("Serviços:", SERVICOS_DISPONIVEIS, default=serv_atuais)
    
    if st.button("Salvar Prestador"):
        tipo_f = ", ".join(tipos_sel) if tipos_sel else "Guincho"
        if not modo_p:
            novo_p = pd.DataFrame([{'id': int(df_prestadores['id'].astype(float).max()+1) if not df_prestadores.empty else 1, 'nome': n_p.upper(), 'tipo': tipo_f, 'telefone': '', 'est': 'RN', 'status': 'Ativo'}])
            df_prestadores = pd.concat([df_prestadores, novo_p], ignore_index=True)
        else:
            df_prestadores.loc[df_prestadores['id'].astype(str) == str(dados_p['id']), ['nome', 'tipo']] = [n_p.upper(), tipo_f]
        salvar_dados(df_prestadores, FILE_PRESTADORES)
        st.success("✅ Prestador salvo!")
        st.session_state.aba_prestador_index = "Listar"
        time.sleep(1)
        st.rerun()
    if modo_p and dados_p is not None and st.button("Excluir Prestador"):
        df_prestadores = df_prestadores[df_prestadores['id'].astype(str) != str(dados_p['id'])]
        salvar_dados(df_prestadores, FILE_PRESTADORES)
        st.error("🗑️ Excluído!")
        st.rerun()
