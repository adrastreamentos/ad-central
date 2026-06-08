import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import urllib.parse
import base64
import time
import requests

# Configuração da Página com a identidade visual da AD
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
    </style>
""", unsafe_allow_html=True)

# Lista Oficial de Estados do Brasil
ESTADOS_BR = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

# Caminhos dos arquivos de banco de dados locais
FOLDER = "AD_Assistencia"
os.makedirs(FOLDER, exist_ok=True)

FILE_CLIENTES = os.path.join(FOLDER, "banco_clientes.csv")
FILE_EMPRESAS = os.path.join(FOLDER, "banco_empresas.csv")
FILE_PRESTADORES = os.path.join(FOLDER, "banco_prestadores.csv")
FILE_OS = os.path.join(FOLDER, "banco_os.csv")

# ===================================================================================
# PORTA LATERAL DO PRESTADOR (Acessível apenas via URL com ?portal=prestador)
# ===================================================================================
query_params = st.query_params
if query_params.get("portal") == "prestador":
    st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Portal Exclusivo para Prestadores de Serviço</div>', unsafe_allow_html=True)
    
    st.info("Para se cadastrar na nossa rede ou acessar seu painel, utilize as opções abaixo.")
    
    def carregar_prestadores_portal():
        try:
            df = pd.read_csv(FILE_PRESTADORES)
            for col in ['id','nome','tipo','telefone','est','status','homologado','senha','frota']:
                if col not in df.columns: df[col] = ""
            return df
        except:
            return pd.DataFrame(columns=['id','nome','tipo','telefone','est','status','homologado','senha','frota'])

    df_p_portal = carregar_prestadores_portal()
    
    tab_p1, tab_p2 = st.tabs(["🔒 Já tenho cadastro (Login)", "📝 Quero me cadastrar"])
    
    with tab_p1:
        doc_login = st.text_input("CPF ou CNPJ (Apenas números)", key="login_doc_p")
        senha_login = st.text_input("Senha", type="password", key="login_senha_p")
        if st.button("Acessar Painel"):
            doc_limpo = "".join(filter(str.isalnum, str(doc_login)))
            match = df_p_portal[(df_p_portal['telefone'] == doc_limpo) & (df_p_portal['senha'] == senha_login)]
            match = df_p_portal[df_p_portal['senha'] == senha_login]
            
            if not match.empty:
                status_hom = match.iloc[0].get('homologado', 'Pendente')
                if status_hom == 'Aprovado':
                    st.success(f"Bem-vindo, {match.iloc[0]['nome']}! (Funcionalidade de frota multiveículo em construção para a próxima fase).")
                elif status_hom == 'Reprovado':
                    st.error("Seu cadastro foi arquivado. Entre em contato com o suporte da AD Rastreamento.")
                else:
                    st.warning("Seu cadastro ainda está em análise pela nossa central.")
            else:
                st.error("Dados incorretos ou não encontrados.")
                
    with tab_p2:
        with st.form("form_novo_prestador"):
            st.write("Preencha os dados para análise da central:")
            c1, c2 = st.columns(2)
            novo_nome = c1.text_input("Razão Social / Nome Completo")
            novo_tipo = c2.selectbox("Tipo Principal de Guincho", ["Plataforma", "Asa Delta", "Lança", "Munck", "Outro"])
            novo_tel = c1.text_input("Telefone com DDD (Será seu Login)")
            nova_senha = c2.text_input("Crie uma Senha", type="password")
            novo_est = c1.selectbox("Estado Base de Atuação", ESTADOS_BR, index=ESTADOS_BR.index("RN"))
            
            if st.form_submit_button("Enviar Cadastro"):
                tel_limpo = "".join(filter(str.isalnum, str(novo_tel)))
                if not novo_nome or not tel_limpo or not nova_senha:
                    st.error("Nome, Telefone e Senha são obrigatórios.")
                else:
                    prox_id = int(df_p_portal['id'].astype(float).max() + 1) if not df_p_portal.empty else 1
                    novo_p = pd.DataFrame([{
                        'id': str(prox_id), 'nome': novo_nome.upper(), 'tipo': novo_tipo.upper(), 
                        'telefone': tel_limpo, 'est': novo_est, 'status': 'Ativo', 
                        'homologado': 'Pendente', 'senha': nova_senha, 'frota': '[]'
                    }])
                    df_p_portal = pd.concat([df_p_portal, novo_p], ignore_index=True)
                    df_p_portal.to_csv(FILE_PRESTADORES, index=False)
                    st.success("Cadastro enviado com sucesso! Aguarde aprovação da central.")
    st.stop()

# ===================================================================================
# FUNÇÕES CORE E SISTEMA PRINCIPAL
# ===================================================================================

if not os.path.exists(FILE_CLIENTES):
    pd.DataFrame(columns=['id','nome','cpf','tel','vei','pla','est','emp_name','status','vei_2','pla_2']).to_csv(FILE_CLIENTES, index=False)
if not os.path.exists(FILE_EMPRESAS):
    pd.DataFrame(columns=['cnpj','nome','responsavel','telefone','email','est','status']).to_csv(FILE_EMPRESAS, index=False)
if not os.path.exists(FILE_PRESTADORES):
    pd.DataFrame(columns=['id','nome','tipo','telefone','est','status','homologado','senha','frota']).to_csv(FILE_PRESTADORES, index=False)
if not os.path.exists(FILE_OS):
    pd.DataFrame(columns=['id','data_hora','cliente_id','cliente_nome','placa','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os']).to_csv(FILE_OS, index=False)

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
            if col not in df.columns:
                df[col] = "" 
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
        veiculo_cliente = ""
        placa_cliente = str(row.get('placa', '')).upper()
        estado_cliente = "RN"
        status_da_os = str(row.get('status_os', 'ENCERRADO')).upper()
        
        if not df_c_alvo.empty:
            if not tel_cliente: tel_cliente = df_c_alvo.iloc[0].get('tel', '')
            if not veiculo_cliente: veiculo_cliente = str(df_c_alvo.iloc[0].get('vei', '')).upper()
            if not placa_cliente or placa_cliente == 'NAN' or placa_cliente == 'N/D': 
                placa_cliente = str(df_c_alvo.iloc[0].get('pla', '')).upper()
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
        
    html_completo = f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ background-color: #fff; padding: 20px; }}
    </style>
    </head>
    <body>
        {cards_html}
    </body>
    </html>
    """
    b64 = base64.b64encode(html_completo.encode('utf-8')).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{titulo_pdf}_{datetime.now().strftime("%Y%m%d")}.html" style="text-decoration: none;"><button style="background-color: #E53935; color: white; padding: 12px 24px; border: none; border-radius: 6px; font-size: 15px; font-weight: bold; cursor: pointer; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">🖨️ Baixar Relatório Oficial (PDF)</button></a>'
    return href

if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.user = ""
    st.session_state.perfil = ""
    st.session_state.empresa_vinculada = ""

df_clientes = carregar_dados(FILE_CLIENTES, ['id','nome','cpf','tel','vei','pla','est','emp_name','status', 'vei_2', 'pla_2'])
df_empresas = carregar_dados(FILE_EMPRESAS, ['cnpj','nome','responsavel','telefone','email','est','status'])
df_prestadores = carregar_dados(FILE_PRESTADORES, ['id','nome','tipo','telefone','est','status','homologado','senha','frota'])
df_os = carregar_dados(FILE_OS, ['id','data_hora','cliente_id','cliente_nome','placa','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os'])

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
            
            if busca:
                df_clientes_busca = df_clientes.copy()
                df_clientes_busca['cpf_limpo'] = df_clientes_busca['cpf'].apply(apenas_numeros_letras)
                busca_limpa = apenas_numeros_letras(busca)
                
                df_filtrado_cli = df_clientes_busca[
                    df_clientes_busca['nome'].str.lower().str.contains(busca.lower(), na=False) |
                    df_clientes_busca['pla'].str.lower().str.contains(busca.lower(), na=False) |
                    df_clientes_busca['cpf_limpo'].str.contains(busca_limpa, na=False)
                ]
            else:
                df_filtrado_cli = df_clientes
                
            if df_filtrado_cli.empty:
                st.error("Nenhum cliente ou veículo encontrado com esse termo de busca.")
            else:
                lista_ed_ops = [f"ID: {str(c['id'])} | {str(c['nome']).upper()} | Veículo: {str(c['vei']).upper()} | Placa: {str(c['pla']).upper()} | Empresa: {str(c['emp_name']).upper()}" for _, c in df_filtrado_cli.iterrows()]
                c_ed_str = st.selectbox("Selecione o cliente e o veículo exato para este atendimento:", options=lista_ed_ops, key="sel_ed")
                c_id = c_ed_str.split("|")[0].replace("ID:", "").strip()
                cliente_dados = df_clientes[df_clientes['id'].astype(str) == c_id].iloc[0]
                
                uf_cliente = str(cliente_dados['est']).strip().upper()
                placa_alvo = str(cliente_dados['pla']).strip().upper()
                if not uf_cliente: uf_cliente = "RN"
                st.info(f"📍 Cliente vinculado à empresa: **{str(cliente_dados['emp_name']).upper()}** | Estado do Veículo: **{uf_cliente}**")
                
                if not df_os.empty and 'placa' in df_os.columns:
                    df_os_copy = df_os.copy()
                    df_os_copy['data_hora'] = pd.to_datetime(df_os_copy['data_hora'], errors='coerce')
                    os_hist = df_os_copy[df_os_copy['placa'].astype(str).str.upper() == placa_alvo]
                    
                    if not os_hist.empty:
                        ultima_data = os_hist['data_hora'].max()
                        if pd.notna(ultima_data):
                            dias_passados = (datetime.now() - ultima_data).days
                            if dias_passados < 60:
                                st.markdown(f'<div class="alert-box alert-danger">⚠️ ATENÇÃO: Último acionamento deste veículo foi há {dias_passados} dias (Data: {ultima_data.strftime("%d/%m/%Y")}). Cliente sujeito à restrição contratual dos 60 dias.</div>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<div class="alert-box alert-success">✅ VIGÊNCIA LIBERADA: Último uso há {dias_passados} dias (Mais de 60 dias).</div>', unsafe_allow_html=True)

                ano_atual = datetime.now().year
                total_guinchos, total_p_seca, total_p_eletrica, total_borraceiro, total_chaveiro = 0, 0, 0, 0, 0
                
                if not df_os.empty and 'placa' in df_os.columns:
                    os_cliente_ano = df_os_copy[(df_os_copy['placa'].astype(str).str.upper() == placa_alvo) & (df_os_copy['data_hora'].dt.year == ano_atual)]
                    
                    for _, o in os_cliente_ano.iterrows():
                        serv = str(o['tipo_servico']).lower()
                        if "guincho" in serv: total_guinchos += 1
                        elif "pane seca" in serv: total_p_seca += 1
                        elif "pane el" in serv or "eletrica" in serv: total_p_eletrica += 1
                        elif "chaveiro" in serv: total_chaveiro += 1
                        elif "borraceiro" in serv: total_borraceiro += 1
                
                st.markdown(f"#### 📊 Saldo de Acionamentos no Ano ({ano_atual}) - Exclusivo do Veículo (Placa: {placa_alvo})")
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Guinchos Utilizados", f"{total_guinchos} / 2")
                c2.metric("Pane Seca Utilizada", f"{total_p_seca} / 1")
                c3.metric("Pane Elétrica Utilizada", f"{total_p_eletrica} / 1")
                c4.metric("Chaveiro Utilizado", f"{total_chaveiro} / 1")
                c5.metric("Borraceiro Utilizado", f"{total_borraceiro} / 1")
                
                st.write("---")
                
                tipo_servico = st.selectbox("Tipo de Serviço:", ["Guincho", "Pane Seca", "Pane Elétrica", "Borraceiro", "Chaveiro"])
                motivo_servico = st.selectbox("Motivo do Acionamento:", ["Acidente", "Furto", "Roubo", "Outros"])
                
                lista_p_ops = ["Outro (Digitar Manualmente)"]
                if not df_prestadores.empty:
                    df_prest_filtrados = df_prestadores[(df_prestadores['est'].str.strip().str.upper() == uf_cliente) & (df_prestadores['status'] == 'Ativo')]
                    if not df_prest_filtrados.empty:
                        lista_p_ops += [f"{str(r['nome'])} - Tel: {str(r['telefone'])} ({str(r['est']).upper()})" for _, r in df_prest_filtrados.iterrows()]
                    else:
                        lista_p_ops += [f"{str(r['nome'])} - Tel: {str(r['telefone'])} ({str(r['est']).upper()})" for _, r in df_prestadores.iterrows()]
                
                prestador_sel = st.selectbox("Prestador homologado para o Estado do Cliente:", lista_p_ops)
                
                if prestador_sel == "Outro (Digitar Manualmente)":
                    p_nome_manual = st.text_input("Nome do Prestador Manual:")
                    p_tel_manual = st.text_input("Telefone do Prestador Manual (DDD + Número):")
                    prestador_final = p_nome_manual
                    tel_prestador_final = apenas_numeros_letras(p_tel_manual)
                else:
                    prestador_final = prestador_sel.split(" - Tel:")[0]
                    tel_cru = prestador_sel.split(" - Tel:")[1].split("(")[0].strip()
                    tel_prestador_final = apenas_numeros_letras(tel_cru)
                
                localizacao = st.text_input("Endereço de Origem (Localização atual):", value=st.session_state.loc_input)
                destino = st.text_input("Endereço de Destino:", value=st.session_state.dest_input)
                obs = st.text_area("Observações:", value=st.session_state.obs_input)
                
                if st.button("🚀 Iniciar Atendimento / Gerar OS"):
                    if not prestador_final or not tel_prestador_final:
                        st.error("Identifique o Nome e o Telefone do prestador.")
                    else:
                        nova_id = int(df_os['id'].astype(float).max() + 1) if not df_os.empty else 1
                        agora_str = obter_hora_brasilia()
                        
                        nova_os = pd.DataFrame([{
                            'id': str(nova_id), 'data_hora': agora_str, 'cliente_id': str(c_id),
                            'cliente_nome': str(cliente_dados['nome']), 'placa': placa_alvo, 'empresa': str(cliente_dados['emp_name']),
                            'tipo_servico': tipo_servico, 'motivo': motivo_servico, 'prestador': f"{prestador_final} | Telefone/Zap: {tel_prestador_final}",
                            'localizacao': localizacao, 'destino': destino, 'obs': obs, 'status_os': "EM ATENDIMENTO"
                        }])
                        df_os = pd.concat([df_os, nova_os], ignore_index=True)
                        salvar_dados(df_os, FILE_OS)
                        st.success(f"✅ Chamado Nº {nova_id} Aberto! Vá para a aba 'Relatórios' -> 'OS em Andamento' para notificar o prestador e finalizar.")
                        
                        st.session_state.busca_input = ""
                        st.session_state.loc_input = ""
                        st.session_state.dest_input = ""
                        st.session_state.obs_input = ""
                        time.sleep(2.5)
                        st.rerun()

    # ==================== ABA: RELATÓRIOS & ENCERRAMENTO ====================
    with menu[1]:
        st.subheader("📊 Gestão de Chamados e Relatórios")
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
                    vei_cliente_os = df_cli_orig.iloc[0]['vei'] if not df_cli_orig.empty else ""
                    pla_cliente_os = str(row_os.get('placa', '')).upper()
                    
                    texto_whatsapp = (
                        f"*{str(row_os['empresa']).upper()} - ASSISTÊNCIA 24H*\n"
                        f"-----------------------------------------\n"
                        f"*Chamado Nº:* {row_os['id']}\n"
                        f"*Data/Hora:* {row_os['data_hora']}\n"
                        f"*Serviço:* {row_os['tipo_servico']} | *Motivo:* {row_os['motivo']}\n\n"
                        f"*Cliente:* {str(row_os['cliente_nome']).upper()}\n"
                        f"*Telefone do Cliente:* {tel_cliente_os}\n\n"
                        f"*Veículo:* {vei_cliente_os} - Placa: {pla_cliente_os}\n\n"
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
        st.subheader("👤 Gerenciamento de Clientes (Multiveículos)")
        
        busca_cli = st.text_input("🔍 Buscar Cliente na Lista (Nome, Placa ou CPF):", key="busca_cli_tab")
        
        if "aba_cliente_index" not in st.session_state: st.session_state.aba_cliente_index = "Listar"
        opcao = st.radio("Ação Clientes:", ["Listar", "Incluir / Editar"], horizontal=True, index=0 if st.session_state.aba_cliente_index == "Listar" else 1)
        
        if opcao == "Listar":
            st.session_state.aba_cliente_index = "Listar"
            if df_clientes.empty: 
                st.info("Nenhum cliente cadastrado.")
            else: 
                df_view_cli = df_clientes.copy()
                if busca_cli:
                    df_view_cli = df_view_cli[
                        df_view_cli['nome'].str.contains(busca_cli, case=False, na=False) | 
                        df_view_cli['pla'].str.contains(busca_cli, case=False, na=False) | 
                        df_view_cli['cpf'].str.contains(busca_cli, case=False, na=False) |
                        df_view_cli['pla_2'].str.contains(busca_cli, case=False, na=False)
                    ]
                
                empresas_na_lista = df_view_cli['emp_name'].unique()
                
                for emp in empresas_na_lista:
                    nome_emp = str(emp).upper() if pd.notna(emp) and str(emp).strip() != "" else "SEM EMPRESA VINCULADA"
                    with st.expander(f"📁 Clientes da Empresa: {nome_emp}", expanded=False):
                        df_emp_filtrada = df_view_cli[df_view_cli['emp_name'] == emp]
                        st.dataframe(df_emp_filtrada.style.map(colorir_status, subset=['status']), use_container_width=True)
        else:
            st.session_state.aba_cliente_index = "Incluir / Editar"
            modo = st.checkbox("Editar cliente existente")
            c_target = None
            dados_ant = None
            
            if modo and not df_clientes.empty:
                lista_ops_c = [f"{str(r['id'])} - {str(r['nome']).upper()}" for _, r in df_clientes.iterrows()]
                sel = st.selectbox("Selecione o cliente para visualizar e alterar os dados:", options=lista_ops_c)
                c_target = sel.split(" - ")[0].strip()
                df_busca_c = df_clientes[df_clientes['id'].astype(str) == c_target]
                if not df_busca_c.empty: dados_ant = df_busca_c.iloc[0]
            
            if modo and dados_ant is not None:
                st.markdown(f"""
                > 📑 **Dados Cadastrados Atualmente:** > * **Nome:** {dados_ant['nome']} | **CPF/CNPJ:** {dados_ant['cpf']} | **Telefone:** {dados_ant['tel']}  
                > * **Veículo 1:** {dados_ant['vei']} | **Placa 1:** {dados_ant['pla']} | **Vínculo:** {dados_ant['emp_name']}  
                > * **Veículo 2:** {dados_ant.get('vei_2','')} | **Placa 2:** {dados_ant.get('pla_2','')}
                """)
                
            nome_in = st.text_input("Nome Completo:", key="c_nome")
            cpf_raw = st.text_input("CPF/CNPJ (Aceita pontos/traços):", key="c_cpf")
            tel_raw = st.text_input("Telefone de Contato:", key="c_tel")
            
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                st.write("**Veículo Principal**")
                vei_in = st.text_input("Veículo 1 (Modelo/Ano):", key="c_vei")
                pla_in = st.text_input("Placa 1:", key="c_pla")
            with col_v2:
                st.write("**Veículo Adicional (Opcional)**")
                vei_2_in = st.text_input("Veículo 2 (Modelo/Ano):", key="c_vei2")
                pla_2_in = st.text_input("Placa 2:", key="c_pla2")
            
            idx_est_c = ESTADOS_BR.index(str(dados_ant['est']).upper()) if (dados_ant is not None and str(dados_ant['est']).upper() in ESTADOS_BR) else ESTADOS_BR.index("RN")
            est = st.selectbox("Selecione o Estado (UF) do Veículo Principal:", options=ESTADOS_BR, index=idx_est_c, key="c_est")
            
            lista_empresas_disponiveis = []
            if not df_empresas.empty:
                lista_empresas_disponiveis = [str(e['nome']).upper() for _, e in df_empresas.iterrows()]
            if not lista_empresas_disponiveis:
                lista_empresas_disponiveis = ["NENHUMA EMPRESA CADASTRADA"]
            
            idx_emp = 0
            if dados_ant is not None:
                emp_ant_upper = str(dados_ant['emp_name']).upper()
                if emp_ant_upper in lista_empresas_disponiveis: idx_emp = lista_empresas_disponiveis.index(emp_ant_upper)
                    
            emp = st.selectbox("Selecione a Empresa Vinculada para este Cliente:", options=lista_empresas_disponiveis, index=idx_emp, key="c_emp")
            status = st.selectbox("Status do Cliente:", ["Ativo", "Inativo"], index=0 if dados_ant is None else ["Ativo", "Inativo"].index(str(dados_ant['status'])), key="c_status")
            
            if st.button("Salvar Cliente", key="save_cli_btn_novo"):
                if modo and dados_ant is not None:
                    nome = nome_in if nome_in else dados_ant['nome']
                    cpf = apenas_numeros_letras(cpf_raw) if cpf_raw else dados_ant['cpf']
                    tel = apenas_numeros_letras(tel_raw) if tel_raw else dados_ant['tel']
                    vei = vei_in if vei_in else dados_ant['vei']
                    pla = pla_in.upper().replace("-","").replace(" ","") if pla_in else dados_ant['pla']
                    vei_2 = vei_2_in if vei_2_in else dados_ant.get('vei_2', '')
                    pla_2 = pla_2_in.upper().replace("-","").replace(" ","") if pla_2_in else dados_ant.get('pla_2', '')
                else:
                    nome = nome_in
                    cpf = apenas_numeros_letras(cpf_raw)
                    tel = apenas_numeros_letras(tel_raw)
                    vei = vei_in
                    pla = pla_in.upper().replace("-","").replace(" ","")
                    vei_2 = vei_2_in
                    pla_2 = pla_2_in.upper().replace("-","").replace(" ","")
                
                if not nome or not pla:
                    st.error("Nome e Placa 1 são obrigatórios para concluir o registro.")
                else:
                    if not modo:
                        prox = int(df_clientes['id'].astype(float).max() + 1) if not df_clientes.empty else 1
                        novo = pd.DataFrame([{'id': str(prox), 'nome': nome.upper(), 'cpf': cpf, 'tel': tel, 'vei': vei.upper(), 'pla': pla, 'est': est, 'emp_name': emp.upper(), 'status': status, 'vei_2': vei_2.upper(), 'pla_2': pla_2}])
                        df_clientes = pd.concat([df_clientes, novo], ignore_index=True)
                    else:
                        df_clientes.loc[df_clientes['id'].astype(str) == c_target, ['nome','cpf','tel','vei','pla','est','emp_name','status','vei_2','pla_2']] = [nome.upper(), cpf, tel, vei.upper(), pla, est, emp.upper(), status, vei_2.upper(), pla_2]
                    salvar_dados(df_clientes, FILE_CLIENTES)
                    st.success("✅ Cliente salvo com sucesso!")
                    st.session_state.aba_cliente_index = "Listar"
                    time.sleep(1)
                    st.rerun()

            if modo and c_target is not None:
                st.write("---")
                if st.button("❌ Excluir Cliente Permanentemente", key="del_cli_btn_novo"):
                    df_clientes = df_clientes[df_clientes['id'].astype(str) != c_target]
                    salvar_dados(df_clientes, FILE_CLIENTES)
                    st.error("🗑️ Cliente excluído permanentemente!")
                    st.session_state.aba_cliente_index = "Listar"
                    time.sleep(1)
                    st.rerun()

    # ==================== ABA: EMPRESAS ====================
    with menu[3]:
        st.subheader("🏢 Gerenciamento de Empresas Parceiras")
        
        busca_emp = st.text_input("🔍 Buscar Empresa na Lista (Nome ou CNPJ):", key="busca_emp_tab")
        
        if "aba_empresa_index" not in st.session_state: st.session_state.aba_empresa_index = "Listar"
        opcao_e = st.radio("Ação Empresas:", ["Listar", "Incluir / Editar"], horizontal=True, index=0 if st.session_state.aba_empresa_index == "Listar" else 1)
        
        if opcao_e == "Listar":
            st.session_state.aba_empresa_index = "Listar"
            if df_empresas.empty: 
                st.info("Nenhuma empresa cadastrada.")
            else: 
                df_view_emp = df_empresas.copy()
                if busca_emp:
                    df_view_emp = df_view_emp[
                        df_view_emp['nome'].str.contains(busca_emp, case=False, na=False) | 
                        df_view_emp['cnpj'].str.contains(busca_emp, case=False, na=False)
                    ]
                st.dataframe(df_view_emp.style.map(colorir_status, subset=['status']), use_container_width=True)
        else:
            st.session_state.aba_empresa_index = "Incluir / Editar"
            modo_e = st.checkbox("Editar empresa existente")
            e_target = None
            dados_e_ant = None
            
            if modo_e and not df_empresas.empty:
                lista_ops_e = [f"{str(r['cnpj'])} - {str(r['nome']).upper()}" for _, r in df_empresas.iterrows()]
                sel_e = st.selectbox("Selecione a empresa para visualizar e alterar os dados:", options=lista_ops_e)
                e_target = apenas_numeros_letras(sel_e.split(" - ")[0].strip())
                
                df_empresas_busca = df_empresas.copy()
                df_empresas_busca['cnpj_limpo'] = df_empresas_busca['cnpj'].apply(apenas_numeros_letras)
                df_resultado_e = df_empresas_busca[df_empresas_busca['cnpj_limpo'] == e_target]
                if not df_resultado_e.empty: dados_e_ant = df_resultado_e.iloc[0]
            
            if modo_e and dados_e_ant is not None:
                st.markdown(f"""
                > 🏢 **Dados Cadastrados Atualmente:** > * **CNPJ:** {dados_e_ant['cnpj']} | **Nome Empresa (User):** {str(dados_e_ant['nome']).upper()}  
                > * **Responsável:** {dados_e_ant['responsavel']} | **Telefone Central:** {dados_e_ant['telefone']} | **E-mail:** {dados_e_ant['email']}  
                """)
            
            cnpj_raw = st.text_input("Alterar CNPJ da Empresa (Deixe em branco para não mexer):", key="e_cnpj")
            n_emp_in = st.text_input("Alterar Nome da Empresa (Deixe em branco para não mexer):", key="e_nome")
            resp_in = st.text_input("Alterar Nome do Responsável:", key="e_resp")
            tel_e_raw = st.text_input("Alterar Telefone da Central 24h:", key="e_tel")
            mail_in = st.text_input("Alterar E-mail corporativo:", key="e_mail")
            
            idx_est_e = ESTADOS_BR.index(str(dados_e_ant['est']).upper()) if (dados_e_ant is not None and str(dados_e_ant['est']).upper() in ESTADOS_BR) else ESTADOS_BR.index("RN")
            est_e = st.selectbox("Selecione o Estado (UF) da Sede:", options=ESTADOS_BR, index=idx_est_e, key="e_est")
            stat_e = st.selectbox("Status Parceria:", ["Ativo", "Inativo"], index=0 if dados_e_ant is None else ["Ativo", "Inativo"].index(str(dados_e_ant['status'])), key="e_status")
            
            if st.button("Salvar Empresa", key="save_emp_btn_novo_direto"):
                if modo_e and dados_e_ant is not None:
                    cnpj = apenas_numeros_letras(cnpj_raw) if cnpj_raw else dados_e_ant['cnpj']
                    nome_empresa = n_emp_in.upper() if n_emp_in else str(dados_e_ant['nome']).upper()
                    responsavel = resp_in.upper() if resp_in else dados_e_ant['responsavel']
                    telefone = apenas_numeros_letras(tel_e_raw) if tel_e_raw else dados_e_ant['telefone']
                    email = mail_in if mail_in else dados_e_ant['email']
                else:
                    cnpj = apenas_numeros_letras(cnpj_raw)
                    nome_empresa = n_emp_in.upper()
                    responsavel = resp_in.upper()
                    telefone = apenas_numeros_letras(tel_e_raw)
                    email = mail_in
                
                if not cnpj or not nome_empresa:
                    st.error("CNPJ e Nome da Empresa são obrigatórios para novos cadastros.")
                else:
                    if not modo_e:
                        novo_e = pd.DataFrame([{'cnpj': cnpj, 'nome': nome_empresa, 'responsavel': responsavel, 'telefone': telefone, 'email': email, 'est': est_e, 'status': stat_e}])
                        df_empresas = pd.concat([df_empresas, novo_e], ignore_index=True)
                    else:
                        df_empresas['cnpj_limpo_check'] = df_empresas['cnpj'].apply(apenas_numeros_letras)
                        df_empresas.loc[df_empresas['cnpj_limpo_check'] == e_target, ['cnpj', 'nome','responsavel','telefone','email','est','status']] = [cnpj, nome_empresa, responsavel, telefone, email, est_e, stat_e]
                        df_empresas = df_empresas.drop(columns=['cnpj_limpo_check'])
                        
                    salvar_dados(df_empresas, FILE_EMPRESAS)
                    st.success("✅ Empresa salva com sucesso!")
                    st.session_state.aba_empresa_index = "Listar"
                    time.sleep(1)
                    st.rerun()

            if modo_e and e_target is not None:
                st.write("---")
                if st.button("❌ Excluir Empresa Permanentemente", key="excluir_emp_definitivo"):
                    df_empresas['cnpj_limpo_check'] = df_empresas['cnpj'].apply(apenas_numeros_letras)
                    df_empresas = df_empresas[df_empresas['cnpj_limpo_check'] != e_target]
                    df_empresas = df_empresas.drop(columns=['cnpj_limpo_check'])
                    salvar_dados(df_empresas, FILE_EMPRESAS)
                    st.error("🗑️ Empresa excluída permanentemente!")
                    st.session_state.aba_empresa_index = "Listar"
                    time.sleep(1)
                    st.rerun()

    # ==================== ABA: PRESTADORES ====================
    with menu[4]:
        st.subheader("🔧 Gerenciamento de Prestadores (Guinchos)")
        
        pendentes = df_prestadores[df_prestadores['homologado'] == 'Pendente']
        if not pendentes.empty:
            st.error(f"⚠️ Atenção Administrativa: Existem {len(pendentes)} prestadores aguardando homologação! Eles se cadastraram via Portal externo.")
            for idx, p in pendentes.iterrows():
                with st.expander(f"Solicitação de: {p['nome']} - {p['est']}"):
                    st.write(f"**Tipo:** {p['tipo']} | **Telefone:** {p['telefone']}")
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
        
        busca_pres = st.text_input("🔍 Buscar Prestador na Lista (Nome ou Tipo):", key="busca_pres_tab")
        
        if "aba_prestador_index" not in st.session_state: st.session_state.aba_prestador_index = "Listar"
        opcao_p = radio_p = st.radio("Ação Prestadores:", ["Listar", "Incluir / Editar"], horizontal=True, index=0 if st.session_state.aba_prestador_index == "Listar" else 1)
        
        if opcao_p == "Listar":
            st.session_state.aba_prestador_index = "Listar"
            if df_prestadores.empty: 
                st.info("Nenhum prestador cadastrado.")
            else: 
                df_view_pres = df_prestadores.copy()
                if busca_pres:
                    df_view_pres = df_view_pres[
                        df_view_pres['nome'].str.contains(busca_pres, case=False, na=False) | 
                        df_view_pres['tipo'].str.contains(busca_pres, case=False, na=False)
                    ]
                st.dataframe(df_view_pres, use_container_width=True)
        else:
            st.session_state.aba_prestador_index = "Incluir / Editar"
            modo_p = st.checkbox("Editar prestador existente")
            p_target = None
            dados_p_ant = None
            
            if modo_p and not df_prestadores.empty:
                lista_ops_p = [f"{str(r['id'])} - {str(r['nome']).upper()}" for _, r in df_prestadores.iterrows()]
                sel_p = st.selectbox("Selecione o prestador para visualizar e alterar os dados:", options=lista_ops_p)
                p_target = sel_p.split(" - ")[0].strip()
                df_busca_p = df_prestadores[df_prestadores['id'].astype(str) == p_target]
                if not df_busca_p.empty: dados_p_ant = df_busca_p.iloc[0]
            
            if modo_p and dados_p_ant is not None:
                st.markdown(f"""
                > 🔧 **Dados Cadastrados Atualmente:** > * **Nome Prestador:** {dados_p_ant['nome']} | **Serviço:** {dados_p_ant['tipo']}  
                > * **Telefone:** {dados_p_ant['telefone']} | **Estado (UF):** {dados_p_ant['est']}  
                > * **Status Homologação:** {dados_p_ant.get('homologado', 'N/D')}
                """)
            
            n_prest_in = st.text_input("Nome do Guincho/Prestador:", key="p_nome")
            t_prest_in = st.text_input("Tipo de Serviço prestado:", key="p_tipo")
            tel_p_raw = st.text_input("Telefone de Contato (Com DDD):", key="p_tel")
            
            idx_est_p = ESTADOS_BR.index(str(dados_p_ant['est']).upper()) if (dados_p_ant is not None and str(dados_p_ant['est']).upper() in ESTADOS_BR) else ESTADOS_BR.index("RN")
            est_p = st.selectbox("Selecione o Estado (UF) de Atuação do Prestador:", options=ESTADOS_BR, index=idx_est_p, key="p_est")
            stat_p = st.selectbox("Status do Guincho:", ["Ativo", "Inativo"], index=0 if dados_p_ant is None else ["Ativo", "Inativo"].index(str(dados_p_ant['status'])), key="p_status")
            
            if st.button("Salvar Prestador", key="save_prest_btn_novo"):
                if modo_p and dados_p_ant is not None:
                    n_prest = n_prest_in.upper() if n_prest_in else dados_p_ant['nome']
                    t_prest = t_prest_in.upper() if t_prest_in else dados_p_ant['tipo']
                    tel_p = apenas_numeros_letras(tel_p_raw) if tel_p_raw else dados_p_ant['telefone']
                else:
                    n_prest = n_prest_in.upper()
                    t_prest = t_prest_in.upper()
                    tel_p = apenas_numeros_letras(tel_p_raw)
                
                if not n_prest:
                    st.error("O Nome do prestador é obrigatório para novos registros.")
                else:
                    if not modo_p:
                        prox_p = int(df_prestadores['id'].astype(float).max() + 1) if not df_prestadores.empty else 1
                        novo_p = pd.DataFrame([{'id': str(prox_p), 'nome': n_prest, 'tipo': t_prest, 'telefone': tel_p, 'est': est_p, 'status': stat_p, 'homologado': 'Aprovado', 'senha': 'admin', 'frota': '[]'}])
                        df_prestadores = pd.concat([df_prestadores, novo_p], ignore_index=True)
                    else:
                        df_prestadores.loc[df_prestadores['id'].astype(str) == p_target, ['nome','tipo','telefone','est','status']] = [n_prest, t_prest, tel_p, est_p, stat_p]
                    salvar_dados(df_prestadores, FILE_PRESTADORES)
                    st.success("✅ Prestador salvo com sucesso!")
                    st.session_state.aba_prestador_index = "Listar"
                    time.sleep(1)
                    st.rerun()

            if modo_p and p_target is not None:
                st.write("---")
                if st.button("❌ Excluir Prestador Permanentemente", key="del_prest_btn_novo"):
                    df_prestadores = df_prestadores[df_prestadores['id'].astype(str) != p_target]
                    salvar_dados(df_prestadores, FILE_PRESTADORES)
                    st.error("🗑️ Prestador excluído permanentemente!")
                    st.session_state.aba_prestador_index = "Listar"
                    time.sleep(1)
                    st.rerun()

# --- INTERFACE DE PARCEIROS RESTRITA ---
else:
    menu_parceiro = st.tabs(["👥 Cadastro de Clientes", "📋 Histórico de Chamados"])
    
    with menu_parceiro[0]:
        df_filtrado_p = df_clientes[df_clientes['emp_name'].str.lower() == st.session_state.empresa_vinculada.lower()]
        if "aba_parceiro_index" not in st.session_state: st.session_state.aba_parceiro_index = "Visualizar"
        op_part = st.radio("Ação Parceiro:", ["Visualizar", "Incluir / Editar Cliente"], horizontal=True, index=0 if st.session_state.aba_parceiro_index == "Visualizar" else 1)
        
        if op_part == "Visualizar":
            st.session_state.aba_parceiro_index = "Visualizar"
            if df_filtrado_p.empty: st.info("Nenhum cliente cadastrado por sua empresa.")
            else: st.dataframe(df_filtrado_p.style.map(colorir_status, subset=['status']), use_container_width=True)
        else:
            st.session_state.aba_parceiro_index = "Incluir / Editar Cliente"
            modo_part = st.checkbox("Editar cliente existente")
            part_target = None
            dados_part_ant = None
            
            if modo_part and not df_filtrado_p.empty:
                sel_part = st.selectbox("Selecione o seu cliente:", [f"{str(r['id'])} - {str(r['nome'])}" for _, r in df_filtrado_p.iterrows()])
                part_target = sel_part.split(" - ")[0].strip()
                df_busca_part = df_filtrado_p[df_filtrado_p['id'].astype(str) == part_target]
                if not df_busca_part.empty: dados_part_ant = df_busca_part.iloc[0]
            
            if modo_part and dados_part_ant is not None:
                st.markdown(f"""
                > 👥 **Dados Cadastrados Atualmente:** > * **Cliente:** {dados_part_ant['nome']} | **CPF:** {dados_part_ant['cpf']} | **Tel:** {dados_part_ant['tel']}  
                > * **Veículo 1:** {dados_part_ant['vei']} | **Placa 1:** {dados_part_ant['pla']}  
                > * **Veículo 2:** {dados_part_ant.get('vei_2','')} | **Placa 2:** {dados_part_ant.get('pla_2','')}
                """)
            
            p_nome_in = st.text_input("Nome Completo:", key="part_nome")
            p_cpf_raw = st.text_input("CPF:", key="part_cpf")
            p_tel_raw = st.text_input("Telefone:", key="part_tel")
            
            col_p_v1, col_p_v2 = st.columns(2)
            with col_p_v1:
                p_vei_in = st.text_input("Veículo 1:", key="part_vei")
                p_pla_in = st.text_input("Placa 1:", key="part_pla")
            with col_p_v2:
                p_vei_2_in = st.text_input("Veículo 2 (Opcional):", key="part_vei2")
                p_pla_2_in = st.text_input("Placa 2:", key="part_pla2")
            
            idx_est_part = ESTADOS_BR.index(str(dados_part_ant['est']).upper()) if (dados_part_ant is not None and str(dados_part_ant['est']).upper() in ESTADOS_BR) else ESTADOS_BR.index("RN")
            p_est = st.selectbox("UF do Veículo:", options=ESTADOS_BR, index=idx_est_part, key="part_est")
            p_stat = st.selectbox("Status do Serviço:", ["Ativo", "Inativo"], index=0 if dados_part_ant is None else ["Ativo", "Inativo"].index(str(dados_part_ant['status'])), key="part_status")
            
            if st.button("Confirmar Registro", key="save_part_btn_novo"):
                if modo_part and dados_part_ant is not None:
                    p_nome = p_nome_in.upper() if p_nome_in else dados_part_ant['nome']
                    p_cpf = apenas_numeros_letras(p_cpf_raw) if p_cpf_raw else dados_part_ant['cpf']
                    p_tel = apenas_numeros_letras(p_tel_raw) if p_tel_raw else dados_part_ant['tel']
                    p_vei = p_vei_in.upper() if p_vei_in else dados_part_ant['vei']
                    p_pla = p_pla_in.upper().replace("-","").replace(" ","") if p_pla_in else dados_part_ant['pla']
                    p_vei_2 = p_vei_2_in.upper() if p_vei_2_in else dados_part_ant.get('vei_2','')
                    p_pla_2 = p_pla_2_in.upper().replace("-","").replace(" ","") if p_pla_2_in else dados_part_ant.get('pla_2','')
                else:
                    p_nome = p_nome_in.upper()
                    p_cpf = apenas_numeros_letras(p_cpf_raw)
                    p_tel = apenas_numeros_letras(p_tel_raw)
                    p_vei = p_vei_in.upper()
                    p_pla = p_pla_in.upper().replace("-","").replace(" ","")
                    p_vei_2 = p_vei_2_in.upper()
                    p_pla_2 = p_pla_2_in.upper().replace("-","").replace(" ","")
                
                if not p_nome or not p_pla:
                    st.error("Nome e Placa 1 são obrigatórios.")
                else:
                    if not modo_part:
                        prox_id = int(df_clientes['id'].astype(float).max() + 1) if not df_clientes.empty else 1
                        novo_reg = pd.DataFrame([{'id': str(prox_id), 'nome': p_nome, 'cpf': p_cpf, 'tel': p_tel, 'vei': p_vei, 'pla': p_pla, 'est': p_est, 'emp_name': st.session_state.empresa_vinculada.upper(), 'status': p_stat, 'vei_2': p_vei_2, 'pla_2': p_pla_2}])
                        df_clientes = pd.concat([df_clientes, novo_reg], ignore_index=True)
                    else:
                        df_clientes.loc[df_clientes['id'].astype(str) == part_target, ['nome','cpf','tel','vei','pla','est','status','vei_2','pla_2']] = [p_nome, p_cpf, p_tel, p_vei, p_pla, p_est, p_stat, p_vei_2, p_pla_2]
                    salvar_dados(df_clientes, FILE_CLIENTES)
                    st.success("✅ Registro atualizado com sucesso!")
                    st.session_state.aba_parceiro_index = "Visualizar"
                    time.sleep(1)
                    st.rerun()

            if modo_part and part_target is not None:
                st.write("---")
                if st.button("❌ Excluir Cliente Permanentemente", key="del_part_btn_novo"):
                    df_clientes = df_clientes[df_clientes['id'].astype(str) != part_target]
                    salvar_dados(df_clientes, FILE_CLIENTES)
                    st.error("🗑️ Cliente excluído permanentemente!")
                    st.session_state.aba_parceiro_index = "Visualizar"
                    time.sleep(1)
                    st.rerun()

    with menu_parceiro[1]:
        df_os_parceiro = df_os[df_os['empresa'].str.lower() == st.session_state.empresa_vinculada.lower()]
        if df_os_parceiro.empty: st.info("Nenhum acionamento registrado para sua empresa.")
        else: st.dataframe(df_os_parceiro, use_container_width=True)
