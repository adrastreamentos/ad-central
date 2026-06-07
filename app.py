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
    pd.DataFrame(columns=['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os']).to_csv(FILE_OS, index=False)

def obter_hora_brasilia():
    fuso_brasilia = timezone(timedelta(hours=-3))
    return datetime.now(fuso_brasilia).strftime("%Y-%m-%d %H:%M:%S")

def apenas_numeros_letras(texto):
    return "".join(caractere for caractere in str(texto) if caractere.isalnum()).strip().lower()

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

def exportar_pdf_html_oficial(df_os_rows, df_clientes_completo, titulo_pdf="relatorio_atendimento"):
    cards_html = ""
    for _, row in df_os_rows.iterrows():
        empresa_os = str(row['empresa']).upper()
        cli_id_busca = str(row['cliente_id'])
        df_c_alvo = df_clientes_completo[df_clientes_completo['id'].astype(str) == cli_id_busca]
        tel_cliente = row.get('tel', '')
        veiculo_cliente = str(row.get('vei', '')).upper()
        placa_cliente = str(row.get('pla', '')).upper()
        estado_cliente = "RN"
        status_da_os = str(row.get('status_os', 'ENCERRADO')).upper()
        if not df_c_alvo.empty:
            if not tel_cliente: tel_cliente = df_c_alvo.iloc[0].get('tel', '')
            if not veiculo_cliente: veiculo_cliente = str(df_c_alvo.iloc[0].get('vei', '')).upper()
            if not placa_cliente: placa_cliente = str(df_c_alvo.iloc[0].get('pla', '')).upper()
            estado_cliente = str(df_c_alvo.iloc[0].get('est', '')).upper()
        motivo_str = str(row['motivo']).upper() if 'motivo' in row and row['motivo'] else "PANE MECÂNICA"
        obs_str = row['obs'] if row['obs'] else 'Nenhuma observação registrada.'
        cards_html += f"""
        <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto 40px auto; padding: 20px; background-color: #fff; page-break-inside: avoid;">
            <div style="text-align: center; margin-bottom: 10px;">
                <h2 style="margin: 0; color: #7B2CBF; font-size: 22px; font-weight: bold; letter-spacing: 0.5px;">{empresa_os} - ASSISTÊNCIA 24H</h2>
                <p style="margin: 5px 0; font-style: italic; color: #555; font-size: 13px;">Relatorio de Atendimento - OS Numero: {row['id']}</p>
            </div>
            <hr style="border: 0; border-top: 1px solid #333; margin-bottom: 20px;">
            <div style="margin-bottom: 20px;">
                <h3 style="margin: 0 0 10px 0; font-size: 14px; color: #000; font-weight: bold;">1. DETALHES DO CLIENTE E VÍNCULO</h3>
                <p style="margin: 3px 0; font-size: 13px; color: #333;">Nome do Titular: {str(row['cliente_nome']).upper()} | Tel: {tel_cliente}</p>
                <p style="margin: 3px 0; font-size: 13px; color: #333;">Empresa Responsável: {empresa_os}</p>
                <p style="margin: 3px 0; font-size: 13px; color: #333;">Veículo Cadastrado: {veiculo_cliente} | Placa: {placa_cliente}</p>
                <p style="margin: 3px 0; font-size: 13px; color: #333;">Estado de Origem (UF): {estado_cliente}</p>
            </div>
            <div style="margin-bottom: 20px;">
                <h3 style="margin: 0 0 10px 0; font-size: 14px; color: #000; font-weight: bold;">2. DADOS DO ACIONAMENTO E SERVIÇO</h3>
                <p style="margin: 3px 0; font-size: 13px; color: #333;">Serviço Solicitado: {row['tipo_servico']} | Motivo: {motivo_str}</p>
                <p style="margin: 3px 0; font-size: 13px; color: #333;">Horário de Abertura: {row['data_hora']} | Status Atual: <span style="color: {'orange' if status_da_os == 'EM ATENDIMENTO' else 'green'}; font-weight: bold;">{status_da_os}</span></p>
                <p style="margin: 3px 0; font-size: 13px; color: #333;">Local de Origem: <span style="font-size: 12px; color: #555;">{row['localizacao']}</span></p>
                <p style="margin: 3px 0; font-size: 13px; color: #333;">Destino Final: {row['destino']}</p>
            </div>
            <div style="margin-bottom: 20px;">
                <h3 style="margin: 0 0 10px 0; font-size: 14px; color: #000; font-weight: bold;">3. PRESTADOR ACIONADO</h3>
                <p style="margin: 3px 0; font-size: 13px; color: #333;">Nome do Prestador: {str(row['prestador']).upper()}</p>
            </div>
            <div style="margin-bottom: 10px;">
                <h3 style="margin: 0 0 10px 0; font-size: 14px; color: #000; font-weight: bold;">4. DESCRIÇÃO DO OCORRIDO</h3>
                <p style="margin: 3px 0; font-size: 13px; color: #444; background-color: #fcfcfc; padding: 5px; border-radius: 4px;">{obs_str}</p>
            </div>
            <hr style="border: 0; border-top: 1px dashed #ccc; margin-top: 30px;">
        </div>
        """
    html_completo = f"<html><body>{cards_html}</body></html>"
    b64 = base64.b64encode(html_completo.encode('utf-8')).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{titulo_pdf}_{datetime.now().strftime("%Y%m%d")}.html" style="text-decoration: none;"><button style="background-color: #E53935; color: white; padding: 12px 24px; border: none; border-radius: 6px; font-size: 15px; font-weight: bold; cursor: pointer; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">🖨️ Baixar Relatório Oficial (PDF)</button></a>'
    return href

if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.user = ""
    st.session_state.perfil = ""
    st.session_state.empresa_vinculada = ""

df_clientes = carregar_dados(FILE_CLIENTES, ['id','nome','cpf','tel','vei','pla','est','emp_name','status'])
df_empresas = carregar_dados(FILE_EMPRESAS, ['cnpj','nome','responsavel','telefone','email','est','status'])
df_prestadores = carregar_dados(FILE_PRESTADORES, ['id','nome','tipo','telefone','est','status'])
df_os = carregar_dados(FILE_OS, ['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os'])

if not st.session_state.logado:
    st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">⚡ Operação Atendimento – AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    st.write("---")
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        usuario_input = apenas_numeros_letras(st.text_input("Usuário (Nome da Empresa):"))
        senha_input = apenas_numeros_letras(st.text_input("Senha (CNPJ):", type="password"))
        if st.button("Entrar no Sistema", use_container_width=True):
            if usuario_input == "adrastreamentoveicular" and senha_input == "00000000000000":
                st.session_state.logado = True
                st.session_state.user = "AD Rastreamento (ADMIN)"
                st.session_state.perfil = "Admin"
                st.rerun()
            else:
                if not df_empresas.empty:
                    df_empresas_login = df_empresas.copy()
                    df_empresas_login['cnpj_comparar'] = df_empresas_login['cnpj'].apply(apenas_numeros_letras)
                    df_empresas_login['nome_comparar'] = df_empresas_login['nome'].apply(apenas_numeros_letras)
                    parceiro_valid = df_empresas_login[(df_empresas_login['cnpj_comparar'] == senha_input) & (df_empresas_login['nome_comparar'] == usuario_input)]
                    if not parceiro_valid.empty:
                        st.session_state.logado = True
                        st.session_state.user = parceiro_valid.iloc[0]['nome'].upper()
                        st.session_state.perfil = "Parceiro"
                        st.session_state.empresa_vinculada = parceiro_valid.iloc[0]['nome']
                        st.rerun()
                    else: st.error("Dados incorretos.")
                else: st.error("Dados incorretos.")
    st.stop()

if st.button("Sair / Logoff"): st.session_state.logado = False; st.rerun()

menu = st.tabs(["📋 Nova OS", "📊 Relatórios & Baixa PDF", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores"])

with menu[0]:
    st.subheader("Nova OS")
    busca = st.text_input("Buscar Cliente:")
    if busca:
        filtro = df_clientes[df_clientes['nome'].str.contains(busca, case=False, na=False)]
        if not filtro.empty:
            sel = st.selectbox("Selecione o Cliente:", [f"{r['id']} - {r['nome']}" for _, r in filtro.iterrows()])
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
                nova_os = pd.DataFrame([{'id': str(nova_id), 'data_hora': obter_hora_brasilia(), 'cliente_id': c_id, 'cliente_nome': cliente['nome'], 'empresa': cliente['emp_name'], 'tipo_servico': serv, 'motivo': motivo, 'prestador': prest, 'localizacao': loc, 'destino': dest, 'obs': obs, 'status_os': "EM ATENDIMENTO"}])
                df_os = pd.concat([df_os, nova_os], ignore_index=True)
                salvar_dados(df_os, FILE_OS)
                st.success("OS Gerada!")
                st.rerun()

with menu[1]:
    st.subheader("Relatórios")
    for idx, row in df_os.sort_values(by='id', ascending=False).iterrows():
        if str(row['status_os']).upper() == "EM ATENDIMENTO":
            st.write(f"OS {row['id']} | {row['cliente_nome']} | {row['prestador']}")
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
            novo = pd.DataFrame([{'id': int(df_clientes['id'].astype(float).max()+1) if not df_clientes.empty else 1, 'nome': n.upper(), 'cpf': c, 'tel': t, 'vei': v.upper(), 'pla': p.upper(), 'est': 'RN', 'emp_name': 'AD', 'status': 'Ativo'}])
            df_clientes = pd.concat([df_clientes, novo], ignore_index=True)
        else:
            df_clientes.loc[df_clientes['id'].astype(str) == str(dados['id']), ['nome','cpf','tel','vei','pla']] = [n.upper(), c, t, v.upper(), p.upper()]
        salvar_dados(df_clientes, FILE_CLIENTES)
        st.success("Salvo!")
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

with menu[4]:
    st.subheader("🔧 Gerenciamento de Prestadores")
    modo_p = st.checkbox("Editar existente")
    dados_p = None
    if modo_p and not df_prestadores.empty:
        sel_p = st.selectbox("Selecione:", [f"{r['id']} - {r['nome']}" for _, r in df_prestadores.iterrows()])
        dados_p = df_prestadores[df_prestadores['id'].astype(str) == sel_p.split(" - ")[0]].iloc[0]
    n_p = st.text_input("Nome:", value=str(dados_p['nome']) if dados_p is not None else "")
    
    # MELHORIA: Multiselect com Guincho padrão
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
        st.success("Salvo!")
        st.rerun()
