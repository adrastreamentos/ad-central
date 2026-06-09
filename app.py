import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import urllib.parse
import base64
import time
import requests
import json

# Configuração da Página com a identidade visual da AD Rastreamento Veicular
st.set_page_config(page_title="Central 24h - AD Rastreamento Veicular", layout="wide", page_icon="🔒")

# Estilização Customizada - Cores Roxa e Vermelha da marca
st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: #7B2CBF; text-align: center; margin-bottom: 5px; }
    .subtitle { font-size: 18px; color: #E53935; text-align: center; margin-bottom: 25px; font-weight: 500; }
    div.stButton > button:first-child { background-color: #7B2CBF; color: white; border: none; border-radius: 4px; padding: 6px 16px; font-weight: bold; }
    div.stButton > button:first-child:hover { background-color: #9d4edd; color: white; border: none; }
    .stTabs [data-baseweb="tab"] { font-size: 16px; font-weight: bold; }
    .alert-box { padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 5px solid; font-weight: bold; }
    .alert-danger { background-color: #FFCDD2; color: #B71C1C; border-color: #E53935; }
    .alert-success { background-color: #C8E6C9; color: #1B5E20; border-color: #4CAF50; }
    .info-box { background-color: #E3F2FD; color: #0D47A1; border-color: #2196F3; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 5px solid; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Lista Oficial de Estados do Brasil, Planos KM e Serviços
ESTADOS_BR = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
PLANOS_KM = ["Sem Limite", "50km", "100km", "150km", "200km", "300km", "400km", "500km"]
OPCOES_SERVICOS = ["Guincho", "Pane Seca", "Pane Elétrica", "Borracheiro", "Chaveiro"]

# Caminhos dos arquivos de banco de dados locais
FOLDER = "AD_Assistencia"
os.makedirs(FOLDER, exist_ok=True)

FILE_CLIENTES = os.path.join(FOLDER, "banco_clientes.csv")
FILE_EMPRESAS = os.path.join(FOLDER, "banco_empresas.csv")
FILE_PRESTADORES = os.path.join(FOLDER, "banco_prestadores.csv")
FILE_OS = os.path.join(FOLDER, "banco_os.csv")

# ===================================================================================
# FUNÇÕES CORE E SISTEMA PRINCIPAL
# ===================================================================================

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

def salvar_dados(df, caminho):
    df.to_csv(caminho, index=False)
    salvar_no_github(caminho)

def carregar_dados(caminho, colunas_obrigatorias):
    try:
        # Lê os dados forçando como string para evitar que o Pandas crie o ".0" (float) nos telefones/CPFs
        df = pd.read_csv(caminho, dtype=str)
        df.columns = df.columns.str.strip().str.lower()
        for col in colunas_obrigatorias:
            if col not in df.columns:
                df[col] = "" 
        for col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
            # Vacina extra para limpar o ".0" caso ele já esteja salvo no arquivo CSV antigo
            df[col] = df[col].str.replace(r'\.0$', '', regex=True)
        return df
    except:
        return pd.DataFrame(columns=colunas_obrigatorias)

# ===================================================================================
# PORTA LATERAL DO PRESTADOR (Acesso via URL com ?portal=prestador)
# ===================================================================================
if st.query_params.get("portal") == "prestador":
    st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Portal Exclusivo para Prestadores de Serviço</div>', unsafe_allow_html=True)
    
    df_p_portal = carregar_dados(FILE_PRESTADORES, ['id','nome','cpf','tipo','telefone','endereco','cidade','cep','est','status','homologado','senha','frota'])
    
    if "logado_prestador" not in st.session_state:
        st.session_state.logado_prestador = False
        st.session_state.id_prestador_logado = None

    if not st.session_state.logado_prestador:
        st.info("Para se cadastrar na nossa rede ou acessar seu painel, utilize as opções abaixo.")
        tab_p1, tab_p2 = st.tabs(["🔒 Já tenho cadastro (Login)", "📝 Quero me cadastrar"])
        
        with tab_p1:
            doc_login = st.text_input("CPF ou CNPJ (Apenas números)", key="login_doc_p")
            senha_login = st.text_input("Senha", type="password", key="login_senha_p")
            if st.button("Acessar Painel"):
                doc_limpo = "".join(filter(str.isalnum, str(doc_login)))
                match = df_p_portal[(df_p_portal['cpf'] == doc_limpo) & (df_p_portal['senha'] == senha_login)]
                if match.empty:
                    match = df_p_portal[df_p_portal['senha'] == senha_login]
                
                if not match.empty:
                    status_hom = match.iloc[0].get('homologado', 'Pendente')
                    if status_hom == 'Aprovado':
                        st.session_state.logado_prestador = True
                        st.session_state.id_prestador_logado = match.iloc[0]['id']
                        st.rerun()
                    elif status_hom == 'Reprovado':
                        st.error("Seu cadastro foi arquivado. Entre em contato com o suporte da AD Rastreamento Veicular.")
                    else:
                        st.warning("Seu cadastro ainda está em análise pela nossa central.")
                else:
                    st.error("Dados incorretos ou não encontrados.")
                    
        with tab_p2:
            with st.form("form_novo_prestador"):
                st.write("Preencha os dados para análise da central:")
                c1, c2 = st.columns(2)
                novo_nome = c1.text_input("Razão Social / Nome Completo")
                novo_cpf = c2.text_input("CPF ou CNPJ (Será seu Login, apenas números)")
                
                novo_tipos_lista = c1.multiselect("Tipos de Serviço Prestado:", OPCOES_SERVICOS, default=["Guincho"])
                novo_tel = c2.text_input("Telefone com DDD")
                
                novo_end = c1.text_input("Endereço / Logradouro")
                nova_senha = c2.text_input("Crie sua Senha", type="password")
                
                novo_cid = c1.text_input("Cidade")
                novo_cep = c2.text_input("CEP")
                
                novo_est = c1.selectbox("Estado Base de Atuação", ESTADOS_BR, index=ESTADOS_BR.index("RN"))
                
                if st.form_submit_button("Enviar Cadastro"):
                    cpf_limpo = "".join(filter(str.isalnum, str(novo_cpf)))
                    tel_limpo = "".join(filter(str.isalnum, str(novo_tel)))
                    tipo_final_str = ", ".join(novo_tipos_lista)
                    
                    if not novo_nome or not cpf_limpo or not nova_senha:
                        st.error("Nome, CPF/CNPJ e Senha são obrigatórios.")
                    elif not novo_tipos_lista:
                        st.error("Selecione ao menos um tipo de serviço prestado.")
                    else:
                        prox_id = int(df_p_portal['id'].astype(float).max() + 1) if not df_p_portal.empty else 1
                        novo_p = pd.DataFrame([{
                            'id': str(prox_id), 'nome': novo_nome.upper(), 'cpf': cpf_limpo, 'tipo': tipo_final_str, 
                            'telefone': tel_limpo, 'endereco': novo_end, 'cidade': novo_cid.upper(), 'cep': novo_cep,
                            'est': novo_est, 'status': 'Ativo', 'homologado': 'Pendente', 'senha': nova_senha, 'frota': '[]'
                        }])
                        df_p_portal = pd.concat([df_p_portal, novo_p], ignore_index=True)
                        salvar_dados(df_p_portal, FILE_PRESTADORES)
                        st.success("Cadastro enviado com sucesso! Aguarde aprovação da central.")
    
    # PAINEL LOGADO DO PRESTADOR
    if st.session_state.logado_prestador:
        id_logado = st.session_state.id_prestador_logado
        p_dados_atual = df_p_portal[df_p_portal['id'] == str(id_logado)].iloc[0]
        
        col_cab1, col_cab2 = st.columns([4, 1])
        col_cab1.subheader(f"Painel Operacional: {p_dados_atual['nome']}")
        if col_cab2.button("Sair do Painel"):
            st.session_state.logado_prestador = False
            st.rerun()
            
        st.write("Atualize seus dados de contato, serviços e localização para garantir acionamentos precisos.")
        
        with st.form("form_edit_prestador"):
            servicos_atuais_logado = []
            if pd.notna(p_dados_atual.get('tipo')):
                servicos_atuais_logado = [s.strip() for s in str(p_dados_atual['tipo']).split(',')]
                servicos_atuais_logado = [s for s in servicos_atuais_logado if s in OPCOES_SERVICOS]
            
            e_cpf = st.text_input("CPF ou CNPJ (Seu Login)", value=p_dados_atual.get('cpf',''), disabled=True)
            e_tipos_lista = st.multiselect("Tipos de Serviço Prestado:", OPCOES_SERVICOS, default=servicos_atuais_logado)
            e_tel = st.text_input("Telefone de Contato (Com DDD)", value=p_dados_atual.get('telefone',''))
            e_end = st.text_input("Endereço / Base", value=p_dados_atual.get('endereco',''))
            c1, c2 = st.columns(2)
            e_cid = c1.text_input("Cidade Base", value=p_dados_atual.get('cidade',''))
            e_cep = c2.text_input("CEP", value=p_dados_atual.get('cep',''))
            
            idx_est = ESTADOS_BR.index(str(p_dados_atual.get('est','RN')).upper()) if str(p_dados_atual.get('est','RN')).upper() in ESTADOS_BR else ESTADOS_BR.index("RN")
            e_est = st.selectbox("Estado", ESTADOS_BR, index=idx_est)
            
            if st.form_submit_button("Salvar Minhas Informações"):
                e_tipo_str = ", ".join(e_tipos_lista)
                df_p_portal.loc[df_p_portal['id'] == str(id_logado), ['tipo','telefone','endereco','cidade','cep','est']] = [
                    e_tipo_str, apenas_numeros_letras(e_tel), e_end, e_cid.upper(), e_cep, e_est
                ]
                salvar_dados(df_p_portal, FILE_PRESTADORES)
                st.success("Dados atualizados com sucesso na Central da AD Rastreamento Veicular!")
                time.sleep(1.5)
                st.rerun()

    st.stop()

# ===================================================================================
# GERAÇÃO DE RELATÓRIO PDF (HTML)
# ===================================================================================
def exportar_pdf_html_oficial(df_os_rows, df_clientes_completo, titulo_pdf="relatorio_atendimento"):
    cards_html = ""
    for _, row in df_os_rows.iterrows():
        empresa_os = str(row['empresa']).upper()
        cli_id_busca = str(row['cliente_id'])
        df_c_alvo = df_clientes_completo[df_clientes_completo['id'].astype(str) == cli_id_busca]
        
        tel_cliente = row.get('tel', '')
        veiculo_cliente = ""
        placa_cliente = str(row.get('placa', '')).upper()
        estado_cliente = "RN"
        plano_km_pdf = str(row.get('plano_km', 'N/D'))
        status_da_os = str(row.get('status_os', 'ENCERRADO')).upper()
        
        if not df_c_alvo.empty:
            if not tel_cliente: tel_cliente = df_c_alvo.iloc[0].get('tel', '')
            if not veiculo_cliente: veiculo_cliente = str(df_c_alvo.iloc[0].get('vei', '')).upper()
            if not placa_cliente or placa_cliente == 'NAN' or placa_cliente == 'N/D': 
                placa_cliente = str(df_c_alvo.iloc[0].get('pla', '')).upper()
            estado_cliente = str(df_c_alvo.iloc[0].get('est', '')).upper()
            if plano_km_pdf == 'N/D' or plano_km_pdf == 'nan': plano_km_pdf = str(df_c_alvo.iloc[0].get('plano_km', 'N/D'))
            
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
                <p style="margin: 3px 0; font-size: 13px; color: #333;">Franquia Contratada: <strong>{plano_km_pdf}</strong></p>
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
        
    html_completo = f"""
    <html>
    <head><meta charset="utf-8"><style>body {{ background-color: #fff; padding: 20px; }}</style></head>
    <body>{cards_html}</body></html>
    """
    b64 = base64.b64encode(html_completo.encode('utf-8')).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{titulo_pdf}_{datetime.now().strftime("%Y%m%d")}.html" style="text-decoration: none;"><button style="background-color: #E53935; color: white; padding: 12px 24px; border: none; border-radius: 6px; font-size: 15px; font-weight: bold; cursor: pointer; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">🖨️ Baixar Relatório Oficial (PDF)</button></a>'
    return href

# Carregamento e Preparação de Dados Principais
col_cli = ['id','nome','cpf','tel','endereco','cidade','cep','plano_km','est','emp_name','status','vei','pla','vei_2','pla_2','veiculos_lista']
col_emp = ['cnpj','nome','responsavel','telefone','email','est','status']
col_pre = ['id','nome','cpf','tipo','telefone','endereco','cidade','cep','est','status','homologado','senha','frota']
col_os = ['id','data_hora','cliente_id','cliente_nome','placa','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os','veiculo_desc','plano_km']

if not os.path.exists(FILE_CLIENTES): pd.DataFrame(columns=col_cli).to_csv(FILE_CLIENTES, index=False)
if not os.path.exists(FILE_EMPRESAS): pd.DataFrame(columns=col_emp).to_csv(FILE_EMPRESAS, index=False)
if not os.path.exists(FILE_PRESTADORES): pd.DataFrame(columns=col_pre).to_csv(FILE_PRESTADORES, index=False)
if not os.path.exists(FILE_OS): pd.DataFrame(columns=col_os).to_csv(FILE_OS, index=False)

df_clientes = carregar_dados(FILE_CLIENTES, col_cli)
df_empresas = carregar_dados(FILE_EMPRESAS, col_emp)
df_prestadores = carregar_dados(FILE_PRESTADORES, col_pre)
df_os = carregar_dados(FILE_OS, col_os)

# ===================================================================================
# CONTROLE DE SESSÃO E LOGIN (ANTI-F5 com URL Params)
# ===================================================================================
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.user = ""
    st.session_state.perfil = ""
    st.session_state.empresa_vinculada = ""

if not st.session_state.logado:
    sess_param = st.query_params.get("session")
    if sess_param == "admin_ad":
        st.session_state.logado = True
        st.session_state.user = "AD Rastreamento Veicular (ADMIN)"
        st.session_state.perfil = "Admin"
    elif sess_param and sess_param.startswith("parc_"):
        nome_parc = urllib.parse.unquote(sess_param.split("parc_")[1])
        st.session_state.logado = True
        st.session_state.user = nome_parc.upper()
        st.session_state.perfil = "Parceiro"
        st.session_state.empresa_vinculada = nome_parc

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">⚡ Operação Atendimento – AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    
    st.write("---")
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("### 🔑 Digite suas credenciais de acesso")
        usuario_input = apenas_numeros_letras(st.text_input("Usuário (Nome da Empresa):"))
        senha_input = apenas_numeros_letras(st.text_input("Senha (CNPJ):", type="password"))
        
        if st.button("Entrar no Sistema", use_container_width=True):
            if usuario_input == "adrastreamentoveicular" and senha_input == "00000000000000":
                st.session_state.logado = True
                st.session_state.user = "AD Rastreamento Veicular (ADMIN)"
                st.session_state.perfil = "Admin"
                st.query_params["session"] = "admin_ad"
                time.sleep(0.5) 
                st.rerun()
            else:
                if not df_empresas.empty:
                    df_empresas_login = df_empresas.copy()
                    df_empresas_login['cnpj_comparar'] = df_empresas_login['cnpj'].apply(apenas_numeros_letras)
                    df_empresas_login['nome_comparar'] = df_empresas_login['nome'].apply(apenas_numeros_letras)
                    
                    parceiro_valid = df_empresas_login[(df_empresas_login['cnpj_comparar'] == senha_input) & (df_empresas_login['nome_comparar'] == usuario_input)]
                    if not parceiro_valid.empty:
                        st.session_state.logado = True
                        nome_valido = parceiro_valid.iloc[0]['nome']
                        st.session_state.user = nome_valido.upper()
                        st.session_state.perfil = "Parceiro"
                        st.session_state.empresa_vinculada = nome_valido
                        st.query_params["session"] = f"parc_{urllib.parse.quote(nome_valido)}"
                        time.sleep(0.5)
                        st.rerun()
                    else: st.error("Usuário ou senha incorretos.")
                else: st.error("Usuário ou senha incorretos.")
    st.stop()

# Cabeçalho Interno
st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">⚡ Operação Atendimento – AD Rastreamento Veicular</div>', unsafe_allow_html=True)

col_user, col_logout = st.columns([5, 1])
with col_user:
    st.write(f"**Central AD 24h | Operador:** `{st.session_state.user}`")
with col_logout:
    if st.button("Sair / Logoff"):
        st.session_state.logado = False
        st.query_params.clear()
        st.rerun()

def colorir_status(val):
    return 'color: green; font-weight: bold;' if val == 'Ativo' else 'color: red; font-weight: bold;'

# --- VISÃO DO ADMINISTRADOR MASTER ---
if st.session_state.perfil == "Admin":
    menu = st.tabs(["📋 Nova OS", "📊 Relatórios & Baixa PDF", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores"])
    
    # ==================== ABA: NOVA OS ====================
    with menu[0]:
        if df_clientes.empty:
            st.warning("Nenhum cliente cadastrado no sistema.")
        else:
            st.subheader("🔍 Localizar Cliente e Veículo")
            
            if "busca_input" not in st.session_state: st.session_state.busca_input = ""
            if "loc_input" not in st.session_state: st.session_state.loc_input = ""
            if "dest_input" not in st.session_state: st.session_state.dest_input = ""
            if "obs_input" not in st.session_state: st.session_state.obs_input = ""
            
            busca = st.text_input("Digite o Nome, Placa ou CPF do cliente para buscar:", value=st.session_state.busca_input)
            
            if not busca:
                st.info("👆 Digite o Nome, Placa ou CPF do cliente acima para iniciar o atendimento.")
            else:
                df_clientes_busca = df_clientes.copy()
                df_clientes_busca['cpf_limpo'] = df_clientes_busca['cpf'].apply(apenas_numeros_letras)
                busca_limpa = apenas_numeros_letras(busca)
                
                df_filtrado_cli = df_clientes_busca[
                    df_clientes_busca['nome'].str.lower().str.contains(busca.lower(), na=False) |
                    df_clientes_busca['pla'].str.lower().str.contains(busca.lower(), na=False) |
                    df_clientes_busca['cpf_limpo'].str.contains(busca_limpa, na=False) |
                    df_clientes_busca['veiculos_lista'].str.lower().str.contains(busca.lower(), na=False)
                ]
                
                if df_filtrado_cli.empty:
                    st.error("Nenhum cliente ou veículo encontrado com esse termo de busca.")
                else:
                    # Uso de dicionário na seleção resolve o bug de nomes idênticos e traços
                    opcoes_cli_os = {str(r['id']): f"{str(r['nome']).upper()} | Empresa: {str(r['emp_name']).upper()}" for _, r in df_filtrado_cli.iterrows()}
                    c_target_os = st.selectbox("Selecione o Cliente:", options=list(opcoes_cli_os.keys()), format_func=lambda x: opcoes_cli_os[x], key="sel_ed")
                    
                    cliente_dados = df_clientes[df_clientes['id'].astype(str) == c_target_os].iloc[0]
                    
                    lista_frota_opcoes = []
                    if pd.notna(cliente_dados.get('veiculos_lista')) and cliente_dados['veiculos_lista']:
                        try:
                            frota_json = json.loads(cliente_dados['veiculos_lista'])
                            for v in frota_json:
                                if v.get('Placa'):
                                    lista_frota_opcoes.append(f"{v.get('Modelo/Ano', 'Veículo')} - Placa: {v.get('Placa')}")
                        except: pass
                    
                    if not lista_frota_opcoes:
                        if pd.notna(cliente_dados.get('pla')) and str(cliente_dados['pla']).strip():
                            lista_frota_opcoes.append(f"{cliente_dados.get('vei', 'Veículo')} - Placa: {cliente_dados['pla']}")
                        if pd.notna(cliente_dados.get('pla_2')) and str(cliente_dados['pla_2']).strip():
                            lista_frota_opcoes.append(f"{cliente_dados.get('vei_2', 'Veículo')} - Placa: {cliente_dados['pla_2']}")
                    
                    if not lista_frota_opcoes:
                        st.error("Este cliente não possui veículos cadastrados com placa válida.")
                    else:
                        veiculo_sel_os = st.selectbox("Selecione qual Veículo da frota será atendido:", lista_frota_opcoes)
                        
                        placa_alvo = veiculo_sel_os.split("Placa: ")[1].strip().upper()
                        veiculo_desc_alvo = veiculo_sel_os.split(" - Placa:")[0].strip()
                        uf_cliente = str(cliente_dados['est']).strip().upper() if cliente_dados['est'] else "RN"
                        plano_km_cliente = str(cliente_dados.get('plano_km', 'N/D'))
                        cidade_cliente = str(cliente_dados.get('cidade', '')).strip().upper()
                        
                        st.info(f"📍 Cliente: **{str(cliente_dados['emp_name']).upper()}** | UF do Veículo: **{uf_cliente}**")
                        st.markdown(f'<div class="info-box">🛣️ PLANO KM CONTRATADO: {plano_km_cliente}</div>', unsafe_allow_html=True)
                        
                        if not df_os.empty and 'placa' in df_os.columns:
                            df_os_copy = df_os.copy()
                            df_os_copy['data_hora'] = pd.to_datetime(df_os_copy['data_hora'], errors='coerce')
                            os_hist = df_os_copy[df_os_copy['placa'].astype(str).str.upper() == placa_alvo]
                            if not os_hist.empty:
                                ultima_data = os_hist['data_hora'].max()
                                if pd.notna(ultima_data):
                                    dias_passados = (datetime.now() - ultima_data).days
                                    if dias_passados < 60:
                                        st.markdown(f'<div class="alert-box alert-danger">⚠️ ATENÇÃO: Último acionamento da placa {placa_alvo} foi há {dias_passados} dias (Data: {ultima_data.strftime("%d/%m/%Y")}). Cliente sujeito à restrição contratual dos 60 dias.</div>', unsafe_allow_html=True)
                                    else:
                                        st.markdown(f'<div class="alert-box alert-success">✅ VIGÊNCIA LIBERADA: Último uso há {dias_passados} dias (Mais de 60 dias).</div>', unsafe_allow_html=True)

                        ano_atual = datetime.now().year
                        total_g, total_ps, total_pe, total_b, total_c = 0, 0, 0, 0, 0
                        if not df_os.empty and 'placa' in df_os.columns:
                            os_cliente_ano = df_os_copy[(df_os_copy['placa'].astype(str).str.upper() == placa_alvo) & (df_os_copy['data_hora'].dt.year == ano_atual)]
                            for _, o in os_cliente_ano.iterrows():
                                serv = str(o['tipo_servico']).lower()
                                if "guincho" in serv: total_g += 1
                                elif "pane seca" in serv: total_ps += 1
                                elif "pane el" in serv or "eletrica" in serv: total_pe += 1
                                elif "chaveiro" in serv: total_c += 1
                                elif "borraceiro" in serv: total_b += 1
                        
                        st.markdown(f"#### 📊 Saldo de Acionamentos no Ano ({ano_atual}) - Placa: {placa_alvo}")
                        c1, c2, c3, c4, c5 = st.columns(5)
                        c1.metric("Guinchos", f"{total_g} / 2")
                        c2.metric("Pane Seca", f"{total_ps} / 1")
                        c3.metric("Elétrica", f"{total_pe} / 1")
                        c4.metric("Chaveiro", f"{total_c} / 1")
                        c5.metric("Borraceiro", f"{total_b} / 1")
                        
                        st.write("---")
                        
                        tipo_servico = st.selectbox("Tipo de Serviço:", ["Guincho", "Pane Seca", "Pane Elétrica", "Borraceiro", "Chaveiro"])
                        motivo_servico = st.selectbox("Motivo do Acionamento:", ["Acidente", "Furto", "Roubo", "Outros"])
                        
                        lista_p_ops = ["Outro (Digitar Manualmente)"]
                        if not df_prestadores.empty:
                            df_prest_filtrados = df_prestadores[(df_prestadores['est'].str.strip().str.upper() == uf_cliente) & (df_prestadores['status'] == 'Ativo') & (df_prestadores['homologado'] == 'Aprovado')].copy()
                            
                            if not df_prest_filtrados.empty:
                                df_prest_filtrados['prioridade'] = df_prest_filtrados['cidade'].apply(lambda x: 0 if str(x).strip().upper() == cidade_cliente and cidade_cliente != "" else 1)
                                df_prest_filtrados = df_prest_filtrados.sort_values(by=['prioridade', 'nome'])
                                
                                for _, r in df_prest_filtrados.iterrows():
                                    marcador = "📍 [MAIS PRÓXIMO] " if r['prioridade'] == 0 else ""
                                    lista_p_ops.append(f"{marcador}{str(r['nome'])} - Tel: {str(r['telefone'])} - {str(r['cidade']).upper()}/{str(r['est']).upper()}")
                            else:
                                df_aprovados = df_prestadores[df_prestadores['homologado'] == 'Aprovado']
                                for _, r in df_aprovados.iterrows():
                                    lista_p_ops.append(f"{str(r['nome'])} - Tel: {str(r['telefone'])} - {str(r['cidade']).upper()}/{str(r['est']).upper()}")
                        
                        prestador_sel = st.selectbox("Prestadores homologados (Ordenados por proximidade):", lista_p_ops)
                        
                        if prestador_sel == "Outro (Digitar Manualmente)":
                            p_nome_manual = st.text_input("Nome do Prestador Manual:")
                            p_tel_manual = st.text_input("Telefone do Prestador Manual (DDD + Número):")
                            prestador_final = p_nome_manual
                            tel_prestador_final = apenas_numeros_letras(p_tel_manual)
                        else:
                            prestador_limpo = prestador_sel.replace("📍 [MAIS PRÓXIMO] ", "")
                            prestador_final = prestador_limpo.split(" - Tel:")[0]
                            tel_prestador_final = apenas_numeros_letras(prestador_limpo.split(" - Tel:")[1].split("-")[0].strip())
                        
                        localizacao = st.text_input("Endereço de Origem (Localização atual):", value=st.session_state.loc_input)
                        destino = st.text_input("Endereço de Destino:", value=st.session_state.dest_input)
                        obs = st.text_area("Observações:", value=st.session_state.obs_input)
                        
                        if st.button("🚀 Iniciar Atendimento / Gerar OS"):
                            if not prestador_final or not tel_prestador_final:
                                st.error("Identifique o Nome e o Telefone do prestador.")
                            else:
                                nova_id = int(df_os['id'].astype(float).max() + 1) if not df_os.empty else 1
                                nova_os = pd.DataFrame([{
                                    'id': str(nova_id), 'data_hora': obter_hora_brasilia(), 'cliente_id': str(c_target_os),
                                    'cliente_nome': str(cliente_dados['nome']), 'placa': placa_alvo, 'veiculo_desc': veiculo_desc_alvo,
                                    'empresa': str(cliente_dados['emp_name']), 'tipo_servico': tipo_servico, 'motivo': motivo_servico, 
                                    'prestador': f"{prestador_final} | Telefone/Zap: {tel_prestador_final}",
                                    'localizacao': localizacao, 'destino': destino, 'obs': obs, 'status_os': "EM ATENDIMENTO",
                                    'plano_km': plano_km_cliente
                                }])
                                df_os = pd.concat([df_os, nova_os], ignore_index=True)
                                salvar_dados(df_os, FILE_OS)
                                st.success(f"✅ Chamado Nº {nova_id} Aberto! Vá para a aba 'Relatórios' -> 'OS em Andamento' para notificar o prestador e finalizar.")
                                
                                st.session_state.busca_input = ""
                                st.session_state.loc_input = ""
                                st.session_state.dest_input = ""
                                st.session_state.obs_input = ""
                                time.sleep(2)
                                st.rerun()

    # ==================== ABA: RELATÓRIOS & ENCERRAMENTO ====================
    with menu[1]:
        st.subheader("📊 Gestão de Chamados e Relatórios")
        
        st.write("---")
        with st.expander("⚠️ Área de Risco: Limpar Dados de Teste"):
            st.warning("Use este botão apenas na fase de implementação para apagar as OS fantasmas de testes anteriores.")
            if st.button("Zerar Histórico de Ordens de Serviço"):
                df_os_vazio = pd.DataFrame(columns=df_os.columns)
                salvar_dados(df_os_vazio, FILE_OS)
                st.success("Banco de OS zerado! O histórico dos clientes está limpo e pronto para uso real.")
                time.sleep(2)
                st.rerun()
        st.write("---")
        
        if df_os.empty: 
            st.info("Nenhuma OS registrada no sistema.")
        else:
            visao_relatorio = st.radio("Escolha a Visão:", ["🚨 OS em Andamento (Gerenciar)", "✅ Histórico e Gerar PDF (Finalizadas)", "Tabela Geral"], horizontal=True)
            
            if visao_relatorio == "🚨 OS em Andamento (Gerenciar)":
                st.markdown("### 🚨 Chamados Atualmente em Andamento")
                df_abertas = df_os[df_os['status_os'] == 'EM ATENDIMENTO']
                
                if df_abertas.empty:
                    st.success("Nenhum chamado em andamento no momento!")
                else:
                    lista_abertas = [f"OS Nº: {r['id']} | Placa: {r.get('placa','N/D')} | Cliente: {r['cliente_nome']}" for _, r in df_abertas.iterrows()]
                    os_sel_str = st.selectbox("Selecione o chamado para Notificar/Finalizar:", lista_abertas)
                    os_id_alvo = os_sel_str.split("|")[0].replace("OS Nº:", "").strip()
                    
                    row_os = df_abertas[df_abertas['id'].astype(str) == os_id_alvo].iloc[0]
                    
                    st.write("---")
                    st.markdown(f"#### Detalhes do Chamado Nº {os_id_alvo}")
                    
                    prestador_info = str(row_os['prestador'])
                    tel_prestador_final = prestador_info.split("Telefone/Zap: ")[1].strip() if "Telefone/Zap: " in prestador_info else ""
                    
                    cli_id_os = str(row_os['cliente_id'])
                    df_cli_orig = df_clientes[df_clientes['id'].astype(str) == cli_id_os]
                    tel_cliente_os = df_cli_orig.iloc[0]['tel'] if not df_cli_orig.empty else ""
                    
                    texto_whatsapp = (
                        f"*{str(row_os['empresa']).upper()} - ASSISTÊNCIA 24H*\n"
                        f"-----------------------------------------\n"
                        f"*Chamado Nº:* {row_os['id']}\n"
                        f"*Data/Hora:* {row_os['data_hora']}\n"
                        f"*Plano KM:* {row_os.get('plano_km', 'N/D')}\n"
                        f"*Serviço:* {row_os['tipo_servico']} | *Motivo:* {row_os['motivo']}\n\n"
                        f"*Cliente:* {str(row_os['cliente_nome']).upper()}\n"
                        f"*Telefone do Cliente:* {tel_cliente_os}\n\n"
                        f"*Veículo:* {row_os.get('veiculo_desc', 'N/D')} - Placa: {row_os.get('placa', 'N/D')}\n\n"
                        f"*Origem:* {row_os['localizacao']}\n"
                        f"*Destino:* {row_os['destino']}\n\n"
                        f"*Obs:* {row_os['obs']}"
                    )
                    link_w = f"https://api.whatsapp.com/send?phone=55{tel_prestador_final}&text={urllib.parse.quote(texto_whatsapp)}"
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        st.markdown(f'<a href="{link_w}" target="_blank"><button style="background-color: #25D366; color: white; padding: 10px 20px; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; width: 100%;">📲 Enviar OS para o Prestador (WhatsApp)</button></a>', unsafe_allow_html=True)
                    with col_btn2:
                        if st.button("🔒 Finalizar Atendimento", key="btn_close_os_new"):
                            df_os.loc[df_os['id'].astype(str) == os_id_alvo, 'status_os'] = "ENCERRADO"
                            salvar_dados(df_os, FILE_OS)
                            st.success(f"🎉 Chamado Nº {os_id_alvo} Finalizado! Ele foi movido para o Histórico (PDF).")
                            time.sleep(1.5)
                            st.rerun()

            elif visao_relatorio == "✅ Histórico e Gerar PDF (Finalizadas)":
                st.markdown("### 📄 Localizar OS Finalizada (Por Placa ou Nome)")
                df_fechadas = df_os[df_os['status_os'] == 'ENCERRADO'].sort_values(by='id', ascending=False)
                
                if df_fechadas.empty:
                    st.info("Nenhum chamado foi finalizado ainda.")
                else:
                    busca_os_relatorio = st.text_input("Digite a Placa do veículo ou o Nome para encontrar o relatório:")
                    
                    if busca_os_relatorio:
                        df_filtrado_fechadas = df_fechadas[df_fechadas['cliente_nome'].str.contains(busca_os_relatorio, case=False, na=False) | df_fechadas['placa'].str.contains(busca_os_relatorio, case=False, na=False)]
                        
                        if df_filtrado_fechadas.empty:
                            st.warning("Nenhum acionamento finalizado encontrado para essa placa ou nome.")
                        else:
                            lista_os_dele = [f"Chamado Nº: {r['id']} | Placa: {r.get('placa', 'N/D')} | Data: {r['data_hora']} | Serviço: {r['tipo_servico']}" for _, r in df_filtrado_fechadas.iterrows()]
                            os_escolhida_str = st.selectbox("Selecione qual acionamento deseja gerar o PDF:", options=lista_os_dele)
                            os_alvo_id = os_escolhida_str.split("|")[0].replace("Chamado Nº:", "").strip()
                            
                            df_os_unica = df_os[df_os['id'].astype(str) == os_alvo_id]
                            
                            st.write("---")
                            st.success("✅ Chamado Finalizado. Baixe o relatório abaixo:")
                            st.markdown(exportar_pdf_html_oficial(df_os_unica, df_clientes, f"relatorio_os_{os_alvo_id}"), unsafe_allow_html=True)
                    else:
                        st.info("👆 Digite a Placa ou Nome acima para exibir as opções de download.")

            else:
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    empresas_ativas = [str(e).upper() for e in df_empresas['nome'].unique()] if not df_empresas.empty else []
                    lista_filt_emp = ["TODAS"] + empresas_ativas
                    emp_escolhida = st.selectbox("Filtrar por Empresa:", options=lista_filt_emp)
                with col_f2:
                    cli_escolhido = st.text_input("Filtrar Tabela por Nome ou Placa:")
                    
                df_os_filtrada = df_os.copy()
                if emp_escolhida != "TODAS":
                    df_os_filtrada = df_os_filtrada[df_os_filtrada['empresa'].str.upper() == emp_escolhida]
                if cli_escolhido:
                    df_os_filtrada = df_os_filtrada[df_os_filtrada['cliente_nome'].str.contains(cli_escolhido, case=False, na=False) | df_os_filtrada['placa'].str.contains(cli_escolhido, case=False, na=False)]
                    
                st.write("---")
                st.dataframe(df_os_filtrada, use_container_width=True)

    # ==================== ABA: CLIENTES ====================
    with menu[2]:
        st.subheader("👤 Gerenciamento de Clientes (Frota Ilimitada e Endereço)")
        
        busca_cli_lista = st.text_input("🔍 Buscar Cliente na Lista (Nome, Placa ou CPF):", key="busca_cli_tab")
        if "acao_cli_admin" not in st.session_state: st.session_state.acao_cli_admin = "Listar"
        opcao = st.radio("Ação Clientes:", ["Listar", "Incluir / Editar"], horizontal=True, key="acao_cli_admin")
        
        if opcao == "Listar":
            if df_clientes.empty: st.info("Nenhum cliente cadastrado.")
            else: 
                df_view_cli = df_clientes.copy()
                expandir_pastas = False 
                if busca_cli_lista:
                    expandir_pastas = True 
                    df_view_cli = df_view_cli[
                        df_view_cli['nome'].str.contains(busca_cli_lista, case=False, na=False) | 
                        df_view_cli['pla'].str.contains(busca_cli_lista, case=False, na=False) | 
                        df_view_cli['cpf'].str.contains(busca_cli_lista, case=False, na=False) |
                        df_view_cli['veiculos_lista'].str.lower().str.contains(busca_cli_lista.lower(), na=False)
                    ]
                
                # FUNÇÃO DE HISTÓRICO COM PROTEÇÃO CONTRA FANTASMAS
                def formatar_historico(c_id):
                    if df_os.empty: return "Nenhum Serviço Solicitado"
                    c_id_str = str(c_id).strip()
                    if not c_id_str or c_id_str.lower() == 'nan': return "Nenhum Serviço Solicitado"
                    
                    os_cli = df_os[df_os['cliente_id'].astype(str).str.strip() == c_id_str]
                    if os_cli.empty: return "Nenhum Serviço Solicitado"
                    
                    res = []
                    for _, r in os_cli.iterrows():
                        try:
                            d = datetime.strptime(str(r['data_hora']), "%Y-%m-%d %H:%M:%S")
                            d_str = d.strftime("%d/%m/%Y")
                        except:
                            d_str = str(r['data_hora'])[:10]
                        res.append(f"{r['tipo_servico']} ({d_str})")
                    return " | ".join(res)
                
                df_view_cli['Histórico'] = df_view_cli['id'].apply(formatar_historico)
                
                empresas_na_lista = df_view_cli['emp_name'].unique()
                if len(empresas_na_lista) == 0:
                    st.warning("Nenhum cliente encontrado com esse termo.")
                else:
                    for emp in empresas_na_lista:
                        nome_emp = str(emp).upper() if pd.notna(emp) and str(emp).strip() != "" else "SEM EMPRESA VINCULADA"
                        with st.expander(f"📁 Clientes da Empresa: {nome_emp}", expanded=expandir_pastas):
                            df_emp_filtrada = df_view_cli[df_view_cli['emp_name'] == emp]
                            st.dataframe(df_emp_filtrada[['nome','cpf','tel','cidade','plano_km','Histórico','status']].style.map(colorir_status, subset=['status']), use_container_width=True)
        else:
            modo = st.checkbox("Editar cliente existente")
            c_target = None
            dados_ant = None
            
            if modo and not df_clientes.empty:
                # BUSCA NATIVA INTELIGENTE (Streamlit Native Selectbox Search)
                opcoes_dict = {}
                for _, r in df_clientes.iterrows():
                    opcoes_dict[str(r['id'])] = f"{str(r['nome']).upper()} | CPF: {str(r['cpf'])} | Empresa: {str(r['emp_name']).upper()}"
                
                c_target = st.selectbox("🔎 Clique e digite para achar o cliente (Nome, CPF ou Empresa):", options=list(opcoes_dict.keys()), format_func=lambda x: opcoes_dict[x])
                
                df_busca_c = df_clientes[df_clientes['id'].astype(str) == c_target]
                if not df_busca_c.empty: dados_ant = df_busca_c.iloc[0]
            
            k_cli = str(c_target) if c_target else "new"
            
            # Só mostra formulário se for inclusão nova ou se achou um cliente para editar
            if not modo or dados_ant is not None:
                c1, c2 = st.columns(2)
                nome_in = c1.text_input("Nome Completo:", key=f"c_nome_{k_cli}", value=dados_ant['nome'] if dados_ant is not None else "")
                cpf_raw = c2.text_input("CPF/CNPJ:", key=f"c_cpf_{k_cli}", value=dados_ant['cpf'] if dados_ant is not None else "")
                tel_raw = c1.text_input("Telefone de Contato:", key=f"c_tel_{k_cli}", value=dados_ant['tel'] if dados_ant is not None else "")
                
                end_in = c2.text_input("Endereço Completo:", key=f"c_end_{k_cli}", value=dados_ant.get('endereco', '') if dados_ant is not None else "")
                cid_in = c1.text_input("Cidade:", key=f"c_cid_{k_cli}", value=dados_ant.get('cidade', '') if dados_ant is not None else "")
                cep_in = c2.text_input("CEP:", key=f"c_cep_{k_cli}", value=dados_ant.get('cep', '') if dados_ant is not None else "")
                
                st.write("---")
                st.write("🚗 **Frota do Cliente (Tabela Interativa - Adicione quantos quiser)**")
                
                frota_inicial = []
                if dados_ant is not None:
                    if pd.notna(dados_ant.get('veiculos_lista')) and dados_ant['veiculos_lista']:
                        try: frota_inicial = json.loads(dados_ant['veiculos_lista'])
                        except: pass
                    if not frota_inicial:
                        if pd.notna(dados_ant.get('vei')) and dados_ant['vei'] != 'nan':
                            frota_inicial.append({"Modelo/Ano": dados_ant['vei'], "Placa": str(dados_ant['pla']).upper()})
                        if pd.notna(dados_ant.get('vei_2')) and dados_ant['vei_2'] != 'nan' and dados_ant['vei_2']:
                            frota_inicial.append({"Modelo/Ano": dados_ant['vei_2'], "Placa": str(dados_ant['pla_2']).upper()})
                
                if not frota_inicial:
                    frota_inicial = [{"Modelo/Ano": "", "Placa": ""}]
                    
                df_frota_editavel = pd.DataFrame(frota_inicial)
                frota_editada = st.data_editor(df_frota_editavel, num_rows="dynamic", use_container_width=True, key=f"ed_frota_cli_{k_cli}")
                st.write("---")
                
                col_b1, col_b2, col_b3 = st.columns(3)
                idx_est_c = ESTADOS_BR.index(str(dados_ant['est']).upper()) if (dados_ant is not None and str(dados_ant['est']).upper() in ESTADOS_BR) else ESTADOS_BR.index("RN")
                est = col_b1.selectbox("Estado (UF) do Veículo:", options=ESTADOS_BR, index=idx_est_c, key=f"c_est_{k_cli}")
                
                idx_plano = PLANOS_KM.index(str(dados_ant.get('plano_km', 'Sem Limite'))) if dados_ant is not None and str(dados_ant.get('plano_km', 'Sem Limite')) in PLANOS_KM else 0
                plano_km = col_b2.selectbox("Plano Contratado (KM):", options=PLANOS_KM, index=idx_plano, key=f"c_plano_{k_cli}")
                
                status = col_b3.selectbox("Status do Cliente:", ["Ativo", "Inativo"], index=0 if dados_ant is None else ["Ativo", "Inativo"].index(str(dados_ant['status'])), key=f"c_status_{k_cli}")
                
                lista_empresas_disponiveis = [str(e['nome']).upper() for _, e in df_empresas.iterrows()] if not df_empresas.empty else ["NENHUMA EMPRESA CADASTRADA"]
                idx_emp = lista_empresas_disponiveis.index(str(dados_ant['emp_name']).upper()) if dados_ant is not None and str(dados_ant['emp_name']).upper() in lista_empresas_disponiveis else 0
                emp = st.selectbox("Empresa Vinculada / Parceira:", options=lista_empresas_disponiveis, index=idx_emp, key=f"c_emp_{k_cli}")
                
                if st.button("Salvar Cliente", key="save_cli_btn_novo"):
                    nome = nome_in.upper()
                    cpf = apenas_numeros_letras(cpf_raw)
                    tel = apenas_numeros_letras(tel_raw)
                    
                    frota_limpa = frota_editada.dropna(how='all')
                    frota_limpa['Placa'] = frota_limpa['Placa'].astype(str).str.upper().str.replace("-","").str.replace(" ","")
                    frota_json_str = json.dumps(frota_limpa.to_dict('records'))
                    
                    vei_prin = frota_limpa.iloc[0]['Modelo/Ano'] if not frota_limpa.empty else ""
                    pla_prin = frota_limpa.iloc[0]['Placa'] if not frota_limpa.empty else ""
                    
                    if not nome or not pla_prin:
                        st.error("Nome e ao menos 1 Placa de Veículo são obrigatórios.")
                    else:
                        if not modo:
                            prox = int(df_clientes['id'].astype(float).max() + 1) if not df_clientes.empty else 1
                            novo = pd.DataFrame([{'id': str(prox), 'nome': nome, 'cpf': cpf, 'tel': tel, 'endereco': end_in, 'cidade': cid_in.upper(), 'cep': cep_in, 'plano_km': plano_km, 'vei': vei_prin, 'pla': pla_prin, 'est': est, 'emp_name': emp.upper(), 'status': status, 'veiculos_lista': frota_json_str}])
                            df_clientes = pd.concat([df_clientes, novo], ignore_index=True)
                        else:
                            df_clientes.loc[df_clientes['id'].astype(str) == c_target, ['nome','cpf','tel','endereco','cidade','cep','plano_km','vei','pla','est','emp_name','status','veiculos_lista']] = [nome, cpf, tel, end_in, cid_in.upper(), cep_in, plano_km, vei_prin, pla_prin, est, emp.upper(), status, frota_json_str]
                        salvar_dados(df_clientes, FILE_CLIENTES)
                        st.success("✅ Cliente e Frota salvos com sucesso!")
                        st.session_state.acao_cli_admin = "Listar"
                        time.sleep(1)
                        st.rerun()
                
                if modo and c_target is not None:
                    st.write("---")
                    if st.button("❌ Excluir Cliente Permanentemente", key="del_cli_btn_novo"):
                        df_clientes = df_clientes[df_clientes['id'].astype(str) != c_target]
                        salvar_dados(df_clientes, FILE_CLIENTES)
                        st.error("🗑️ Cliente excluído permanentemente!")
                        st.session_state.acao_cli_admin = "Listar"
                        time.sleep(1)
                        st.rerun()

    # ==================== ABA: EMPRESAS ====================
    with menu[3]:
        st.subheader("🏢 Gerenciamento de Empresas Parceiras")
        
        busca_emp_lista = st.text_input("🔍 Buscar Empresa na Lista (Nome ou CNPJ):", key="busca_emp_tab")
        
        if "acao_emp_admin" not in st.session_state: st.session_state.acao_emp_admin = "Listar"
        opcao_e = st.radio("Ação Empresas:", ["Listar", "Incluir / Editar"], horizontal=True, key="acao_emp_admin")
        
        if opcao_e == "Listar":
            if df_empresas.empty: 
                st.info("Nenhuma empresa cadastrada.")
            else: 
                df_view_emp = df_empresas.copy()
                if busca_emp_lista:
                    df_view_emp = df_view_emp[
                        df_view_emp['nome'].str.contains(busca_emp_lista, case=False, na=False) | 
                        df_view_emp['cnpj'].str.contains(busca_emp_lista, case=False, na=False)
                    ]
                st.dataframe(df_view_emp.style.map(colorir_status, subset=['status']), use_container_width=True)
        else:
            modo_e = st.checkbox("Editar empresa existente")
            e_target = None
            dados_e_ant = None
            
            if modo_e and not df_empresas.empty:
                opcoes_emp = {str(r['cnpj']): f"{str(r['nome']).upper()} | CNPJ: {str(r['cnpj'])}" for _, r in df_empresas.iterrows()}
                e_target = st.selectbox("🔎 Clique e digite para achar a empresa:", options=list(opcoes_emp.keys()), format_func=lambda x: opcoes_emp[x])
                
                df_resultado_e = df_empresas[df_empresas['cnpj'].astype(str) == e_target]
                if not df_resultado_e.empty: dados_e_ant = df_resultado_e.iloc[0]
            
            if not modo_e or dados_e_ant is not None:
                k_emp = str(e_target) if e_target else "new"
                
                c1, c2 = st.columns(2)
                n_emp_in = c1.text_input("Nome da Empresa:", key=f"e_nome_{k_emp}", value=dados_e_ant['nome'] if dados_e_ant is not None else "")
                cnpj_raw = c2.text_input("CNPJ da Empresa:", key=f"e_cnpj_{k_emp}", value=dados_e_ant['cnpj'] if dados_e_ant is not None else "")
                
                resp_in = c1.text_input("Nome do Responsável:", key=f"e_resp_{k_emp}", value=dados_e_ant['responsavel'] if dados_e_ant is not None else "")
                tel_e_raw = c2.text_input("Telefone da Central 24h:", key=f"e_tel_{k_emp}", value=dados_e_ant['telefone'] if dados_e_ant is not None else "")
                mail_in = c1.text_input("E-mail corporativo:", key=f"e_mail_{k_emp}", value=dados_e_ant['email'] if dados_e_ant is not None else "")
                
                idx_est_e = ESTADOS_BR.index(str(dados_e_ant['est']).upper()) if (dados_e_ant is not None and str(dados_e_ant['est']).upper() in ESTADOS_BR) else ESTADOS_BR.index("RN")
                est_e = c2.selectbox("Selecione o Estado (UF) da Sede:", options=ESTADOS_BR, index=idx_est_e, key=f"e_est_{k_emp}")
                stat_e = c1.selectbox("Status Parceria:", ["Ativo", "Inativo"], index=0 if dados_e_ant is None else ["Ativo", "Inativo"].index(str(dados_e_ant['status'])), key=f"e_status_{k_emp}")
                
                if st.button("Salvar Empresa", key="save_emp_btn_novo_direto"):
                    cnpj = apenas_numeros_letras(cnpj_raw)
                    nome_empresa = n_emp_in.upper()
                    responsavel = resp_in.upper()
                    telefone = apenas_numeros_letras(tel_e_raw)
                    email = mail_in
                    
                    if not cnpj or not nome_empresa:
                        st.error("CNPJ e Nome da Empresa são obrigatórios para salvar.")
                    else:
                        if not modo_e:
                            novo_e = pd.DataFrame([{'cnpj': cnpj, 'nome': nome_empresa, 'responsavel': responsavel, 'telefone': telefone, 'email': email, 'est': est_e, 'status': stat_e}])
                            df_empresas = pd.concat([df_empresas, novo_e], ignore_index=True)
                        else:
                            df_empresas.loc[df_empresas['cnpj'] == e_target, ['cnpj', 'nome','responsavel','telefone','email','est','status']] = [cnpj, nome_empresa, responsavel, telefone, email, est_e, stat_e]
                            
                        salvar_dados(df_empresas, FILE_EMPRESAS)
                        st.success("✅ Empresa salva com sucesso!")
                        st.session_state.acao_emp_admin = "Listar"
                        time.sleep(1)
                        st.rerun()

                if modo_e and e_target is not None:
                    st.write("---")
                    if st.button("❌ Excluir Empresa Permanentemente", key="excluir_emp_definitivo"):
                        df_empresas = df_empresas[df_empresas['cnpj'] != e_target]
                        salvar_dados(df_empresas, FILE_EMPRESAS)
                        st.error("🗑️ Empresa excluída permanentemente!")
                        st.session_state.acao_emp_admin = "Listar"
                        time.sleep(1)
                        st.rerun()

    # ==================== ABA: PRESTADORES ====================
    with menu[4]:
        st.subheader("🔧 Gerenciamento de Prestadores (Guinchos e Endereço)")
        
        pendentes = df_prestadores[df_prestadores['homologado'] == 'Pendente']
        if not pendentes.empty:
            st.error(f"⚠️ Atenção Administrativa: Existem {len(pendentes)} prestadores aguardando homologação! Eles se cadastraram via Portal externo.")
            for idx, p in pendentes.iterrows():
                with st.expander(f"Solicitação de: {p['nome']} - {p['est']}"):
                    st.write(f"**Tipo:** {p['tipo']} | **Telefone:** {p['telefone']} | **Cidade:** {p.get('cidade','N/D')}")
                    col_h1, col_h2 = st.columns(2)
                    if col_h1.button("✅ Aprovar Cadastro", key=f"apr_{p['id']}"):
                        df_prestadores.loc[df_prestadores['id'] == p['id'], 'homologado'] = 'Aprovado'
                        salvar_dados(df_prestadores, FILE_PRESTADORES)
                        st.success("Aprovado com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    if col_h2.button("❌ Reprovar/Arquivar", key=f"rep_{p['id']}"):
                        df_prestadores.loc[df_prestadores['id'] == p['id'], 'homologado'] = 'Reprovado'
                        salvar_dados(df_prestadores, FILE_PRESTADORES)
                        st.info("Cadastro movido para os arquivos de reprovados.")
                        time.sleep(1)
                        st.rerun()
            st.write("---")
        
        busca_pres_lista = st.text_input("🔍 Buscar Prestador na Lista (Nome, Tipo ou Cidade):", key="busca_pres_tab")
        
        if "acao_pre_admin" not in st.session_state: st.session_state.acao_pre_admin = "Listar"
        opcao_p = st.radio("Ação Prestadores:", ["Listar", "Incluir / Editar"], horizontal=True, key="acao_pre_admin")
        
        if opcao_p == "Listar":
            if df_prestadores.empty: 
                st.info("Nenhum prestador cadastrado.")
            else: 
                df_view_pres = df_prestadores.copy()
                if busca_pres_lista:
                    df_view_pres = df_view_pres[
                        df_view_pres['nome'].str.contains(busca_pres_lista, case=False, na=False) | 
                        df_view_pres['tipo'].str.contains(busca_pres_lista, case=False, na=False) |
                        df_view_pres['cidade'].str.contains(busca_pres_lista, case=False, na=False)
                    ]
                st.dataframe(df_view_pres[['nome','cpf','tipo','telefone','cidade','est','status','homologado']], use_container_width=True)
        else:
            modo_p = st.checkbox("Editar prestador existente")
            p_target = None
            dados_p_ant = None
            
            if modo_p and not df_prestadores.empty:
                opcoes_pre = {str(r['id']): f"{str(r['nome']).upper()} | Cidade: {str(r['cidade']).upper()} | Tipo: {str(r['tipo'])}" for _, r in df_prestadores.iterrows()}
                p_target = st.selectbox("🔎 Clique e digite para achar o prestador:", options=list(opcoes_pre.keys()), format_func=lambda x: opcoes_pre[x])
                
                df_busca_p = df_prestadores[df_prestadores['id'].astype(str) == p_target]
                if not df_busca_p.empty: dados_p_ant = df_busca_p.iloc[0]
            
            if not modo_p or dados_p_ant is not None:
                k_pre = str(p_target) if p_target else "new"
                
                c1, c2 = st.columns(2)
                n_prest_in = c1.text_input("Nome do Guincho/Prestador:", key=f"p_nome_{k_pre}", value=dados_p_ant['nome'] if dados_p_ant is not None else "")
                cpf_p_raw = c2.text_input("CPF/CNPJ do Prestador:", key=f"p_cpf_{k_pre}", value=dados_p_ant.get('cpf','') if dados_p_ant is not None else "")
                
                servicos_atuais = []
                if dados_p_ant is not None and pd.notna(dados_p_ant['tipo']):
                    partes = [s.strip() for s in str(dados_p_ant['tipo']).split(',')]
                    servicos_atuais = [s for s in partes if s in OPCOES_SERVICOS]
                    if not servicos_atuais and partes and partes[0]:
                        servicos_atuais = ["Guincho"] 
                
                t_prest_lista = c1.multiselect("Tipos de Serviço Prestado:", options=OPCOES_SERVICOS, default=servicos_atuais, key=f"p_tipo_{k_pre}")
                tel_p_raw = c2.text_input("Telefone de Contato (Com DDD):", key=f"p_tel_{k_pre}", value=dados_p_ant['telefone'] if dados_p_ant is not None else "")
                
                end_p_in = c1.text_input("Endereço / Base:", key=f"p_end_{k_pre}", value=dados_p_ant.get('endereco','') if dados_p_ant is not None else "")
                cid_p_in = c2.text_input("Cidade Base:", key=f"p_cid_{k_pre}", value=dados_p_ant.get('cidade','') if dados_p_ant is not None else "")
                cep_p_in = c1.text_input("CEP:", key=f"p_cep_{k_pre}", value=dados_p_ant.get('cep','') if dados_p_ant is not None else "")
                
                idx_est_p = ESTADOS_BR.index(str(dados_p_ant['est']).upper()) if (dados_p_ant is not None and str(dados_p_ant['est']).upper() in ESTADOS_BR) else ESTADOS_BR.index("RN")
                est_p = c2.selectbox("Estado (UF) de Atuação:", options=ESTADOS_BR, index=idx_est_p, key=f"p_est_{k_pre}")
                stat_p = c1.selectbox("Status do Guincho:", ["Ativo", "Inativo"], index=0 if dados_p_ant is None else ["Ativo", "Inativo"].index(str(dados_p_ant['status'])), key=f"p_status_{k_pre}")
                
                if st.button("Salvar Prestador", key="save_prest_btn_novo"):
                    n_prest = n_prest_in.upper()
                    cpf_p = apenas_numeros_letras(cpf_p_raw)
                    t_prest = ", ".join(t_prest_lista)
                    tel_p = apenas_numeros_letras(tel_p_raw)
                    
                    if not n_prest or not cpf_p:
                        st.error("O Nome e o CPF/CNPJ do prestador são obrigatórios para registros.")
                    elif not t_prest_lista:
                        st.error("Selecione ao menos um tipo de serviço prestado.")
                    else:
                        if not modo_p:
                            prox_p = int(df_prestadores['id'].astype(float).max() + 1) if not df_prestadores.empty else 1
                            novo_p = pd.DataFrame([{'id': str(prox_p), 'nome': n_prest, 'cpf': cpf_p, 'tipo': t_prest, 'telefone': tel_p, 'endereco': end_p_in, 'cidade': cid_p_in.upper(), 'cep': cep_p_in, 'est': est_p, 'status': stat_p, 'homologado': 'Aprovado', 'senha': 'admin', 'frota': '[]'}])
                            df_prestadores = pd.concat([df_prestadores, novo_p], ignore_index=True)
                        else:
                            df_prestadores.loc[df_prestadores['id'].astype(str) == p_target, ['nome','cpf','tipo','telefone','endereco','cidade','cep','est','status']] = [n_prest, cpf_p, t_prest, tel_p, end_p_in, cid_p_in.upper(), cep_p_in, est_p, stat_p]
                        salvar_dados(df_prestadores, FILE_PRESTADORES)
                        st.success("✅ Prestador salvo com sucesso!")
                        st.session_state.acao_pre_admin = "Listar"
                        time.sleep(1)
                        st.rerun()

                if modo_p and p_target is not None:
                    st.write("---")
                    if st.button("❌ Excluir Prestador Permanentemente", key="del_prest_btn_novo"):
                        df_prestadores = df_prestadores[df_prestadores['id'].astype(str) != p_target]
                        salvar_dados(df_prestadores, FILE_PRESTADORES)
                        st.error("🗑️ Prestador excluído permanentemente!")
                        st.session_state.acao_pre_admin = "Listar"
                        time.sleep(1)
                        st.rerun()

# --- INTERFACE DE PARCEIROS RESTRITA ---
else:
    menu_parceiro = st.tabs(["👥 Cadastro de Clientes", "📋 Histórico de Chamados"])
    
    with menu_parceiro[0]:
        df_filtrado_p = df_clientes[df_clientes['emp_name'].str.lower() == st.session_state.empresa_vinculada.lower()]
        
        if "acao_cli_part" not in st.session_state: st.session_state.acao_cli_part = "Visualizar"
        op_part = st.radio("Ação Parceiro:", ["Visualizar", "Incluir / Editar Cliente"], horizontal=True, key="acao_cli_part")
        
        if op_part == "Visualizar":
            if df_filtrado_p.empty: st.info("Nenhum cliente cadastrado por sua empresa.")
            else: 
                def formatar_historico_p(c_id):
                    if df_os.empty: return "Nenhum Serviço Solicitado"
                    c_id_str = str(c_id).strip()
                    if not c_id_str or c_id_str.lower() == 'nan': return "Nenhum Serviço Solicitado"
                    
                    os_cli = df_os[df_os['cliente_id'].astype(str).str.strip() == c_id_str]
                    if os_cli.empty: return "Nenhum Serviço Solicitado"
                    
                    res = []
                    for _, r in os_cli.iterrows():
                        try:
                            d = datetime.strptime(str(r['data_hora']), "%Y-%m-%d %H:%M:%S")
                            d_str = d.strftime("%d/%m/%Y")
                        except:
                            d_str = str(r['data_hora'])[:10]
                        res.append(f"{r['tipo_servico']} ({d_str})")
                    return " | ".join(res)
                
                df_filtrado_p['Histórico'] = df_filtrado_p['id'].apply(formatar_historico_p)
                st.dataframe(df_filtrado_p[['nome','cpf','tel','cidade','plano_km','Histórico','status']].style.map(colorir_status, subset=['status']), use_container_width=True)
        else:
            modo_part = st.checkbox("Editar cliente existente")
            part_target = None
            dados_part_ant = None
            
            if modo_part and not df_filtrado_p.empty:
                opcoes_dict_p = {str(r['id']): f"{str(r['nome']).upper()} | CPF: {str(r['cpf'])}" for _, r in df_filtrado_p.iterrows()}
                part_target = st.selectbox("🔎 Clique e digite para achar o cliente (Nome ou CPF):", options=list(opcoes_dict_p.keys()), format_func=lambda x: opcoes_dict_p[x])
                
                df_busca_part = df_filtrado_p[df_filtrado_p['id'].astype(str) == part_target]
                if not df_busca_part.empty: dados_part_ant = df_busca_part.iloc[0]
            
            if not modo_part or dados_part_ant is not None:
                k_part = str(part_target) if part_target else "new"
                
                c1, c2 = st.columns(2)
                p_nome_in = c1.text_input("Nome Completo:", key=f"part_nome_{k_part}", value=dados_part_ant['nome'] if dados_part_ant is not None else "")
                p_cpf_raw = c2.text_input("CPF:", key=f"part_cpf_{k_part}", value=dados_part_ant['cpf'] if dados_part_ant is not None else "")
                p_tel_raw = c1.text_input("Telefone:", key=f"part_tel_{k_part}", value=dados_part_ant['tel'] if dados_part_ant is not None else "")
                
                p_end_in = c2.text_input("Endereço Completo:", key=f"part_end_{k_part}", value=dados_part_ant.get('endereco', '') if dados_part_ant is not None else "")
                p_cid_in = c1.text_input("Cidade:", key=f"part_cid_{k_part}", value=dados_part_ant.get('cidade', '') if dados_part_ant is not None else "")
                p_cep_in = c2.text_input("CEP:", key=f"part_cep_{k_part}", value=dados_part_ant.get('cep', '') if dados_part_ant is not None else "")
                
                st.write("---")
                st.write("🚗 **Frota do Cliente (Tabela Interativa)**")
                
                frota_inicial_p = []
                if dados_part_ant is not None:
                    if pd.notna(dados_part_ant.get('veiculos_lista')) and dados_part_ant['veiculos_lista']:
                        try: frota_inicial_p = json.loads(dados_part_ant['veiculos_lista'])
                        except: pass
                    if not frota_inicial_p:
                        if pd.notna(dados_part_ant.get('vei')) and dados_part_ant['vei'] != 'nan':
                            frota_inicial_p.append({"Modelo/Ano": dados_part_ant['vei'], "Placa": str(dados_part_ant['pla']).upper()})
                        if pd.notna(dados_part_ant.get('vei_2')) and dados_part_ant['vei_2'] != 'nan' and dados_part_ant['vei_2']:
                            frota_inicial_p.append({"Modelo/Ano": dados_part_ant['vei_2'], "Placa": str(dados_part_ant['pla_2']).upper()})
                
                if not frota_inicial_p:
                    frota_inicial_p = [{"Modelo/Ano": "", "Placa": ""}]
                    
                df_frota_editavel_p = pd.DataFrame(frota_inicial_p)
                frota_editada_p = st.data_editor(df_frota_editavel_p, num_rows="dynamic", use_container_width=True, key=f"ed_frota_cli_part_{k_part}")
                st.write("---")
                
                col_pb1, col_pb2, col_pb3 = st.columns(3)
                idx_est_part = ESTADOS_BR.index(str(dados_part_ant['est']).upper()) if (dados_part_ant is not None and str(dados_part_ant['est']).upper() in ESTADOS_BR) else ESTADOS_BR.index("RN")
                p_est = col_pb1.selectbox("UF do Veículo:", options=ESTADOS_BR, index=idx_est_part, key=f"part_est_{k_part}")
                
                idx_plano_p = PLANOS_KM.index(str(dados_part_ant.get('plano_km', 'Sem Limite'))) if dados_part_ant is not None and str(dados_part_ant.get('plano_km', 'Sem Limite')) in PLANOS_KM else 0
                p_plano_km = col_pb2.selectbox("Plano Contratado (KM):", options=PLANOS_KM, index=idx_plano_p, key=f"part_plano_{k_part}")
                
                p_stat = col_pb3.selectbox("Status do Serviço:", ["Ativo", "Inativo"], index=0 if dados_part_ant is None else ["Ativo", "Inativo"].index(str(dados_part_ant['status'])), key=f"part_status_{k_part}")
                
                if st.button("Confirmar Registro", key="save_part_btn_novo"):
                    p_nome = p_nome_in.upper()
                    p_cpf = apenas_numeros_letras(p_cpf_raw)
                    p_tel = apenas_numeros_letras(p_tel_raw)
                    
                    frota_limpa_p = frota_editada_p.dropna(how='all')
                    frota_limpa_p['Placa'] = frota_limpa_p['Placa'].astype(str).str.upper().str.replace("-","").str.replace(" ","")
                    frota_json_str_p = json.dumps(frota_limpa_p.to_dict('records'))
                    
                    vei_prin_p = frota_limpa_p.iloc[0]['Modelo/Ano'] if not frota_limpa_p.empty else ""
                    pla_prin_p = frota_limpa_p.iloc[0]['Placa'] if not frota_limpa_p.empty else ""
                    
                    if not p_nome or not pla_prin_p:
                        st.error("Nome e ao menos 1 Placa são obrigatórios.")
                    else:
                        if not modo_part:
                            prox_id = int(df_clientes['id'].astype(float).max() + 1) if not df_clientes.empty else 1
                            novo_reg = pd.DataFrame([{'id': str(prox_id), 'nome': p_nome, 'cpf': p_cpf, 'tel': p_tel, 'endereco': p_end_in, 'cidade': p_cid_in.upper(), 'cep': p_cep_in, 'plano_km': p_plano_km, 'vei': vei_prin_p, 'pla': pla_prin_p, 'est': p_est, 'emp_name': st.session_state.empresa_vinculada.upper(), 'status': p_stat, 'veiculos_lista': frota_json_str_p}])
                            df_clientes = pd.concat([df_clientes, novo_reg], ignore_index=True)
                        else:
                            df_clientes.loc[df_clientes['id'].astype(str) == part_target, ['nome','cpf','tel','endereco','cidade','cep','plano_km','vei','pla','est','status','veiculos_lista']] = [p_nome, p_cpf, p_tel, p_end_in, p_cid_in.upper(), p_cep_in, p_plano_km, vei_prin_p, pla_prin_p, p_est, p_stat, frota_json_str_p]
                        salvar_dados(df_clientes, FILE_CLIENTES)
                        st.success("✅ Registro atualizado com sucesso!")
                        st.session_state.acao_cli_part = "Visualizar"
                        time.sleep(1)
                        st.rerun()

                if modo_part and part_target is not None:
                    st.write("---")
                    if st.button("❌ Excluir Cliente Permanentemente", key="del_part_btn_novo"):
                        df_clientes = df_clientes[df_clientes['id'].astype(str) != part_target]
                        salvar_dados(df_clientes, FILE_CLIENTES)
                        st.error("🗑️ Cliente excluído permanentemente!")
                        st.session_state.acao_cli_part = "Visualizar"
                        time.sleep(1)
                        st.rerun()

    with menu_parceiro[1]:
        df_os_parceiro = df_os[df_os['empresa'].str.lower() == st.session_state.empresa_vinculada.lower()]
        if df_os_parceiro.empty: st.info("Nenhum acionamento registrado para sua empresa.")
        else: st.dataframe(df_os_parceiro, use_container_width=True)
