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
    if not token:
        return
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
        return df[colunas_obrigatorias]
    except:
        return pd.DataFrame(columns=colunas_obrigatorias)

def salvar_dados(df, caminho):
    df.to_csv(caminho, index=False)
    salvar_no_github(caminho)

# Gerador de Relatório Oficial Estruturado
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
        
    html_completo = f"<html><head><meta charset='utf-8'></head><body>{cards_html}</body></html>"
    b64 = base64.b64encode(html_completo.encode('utf-8')).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{titulo_pdf}_{datetime.now().strftime("%Y%m%d")}.html" style="text-decoration: none;"><button style="background-color: #E53935; color: white; padding: 12px 24px; border: none; border-radius: 6px; font-size: 15px; font-weight: bold; cursor: pointer; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">🖨️ Baixar Relatório Oficial (PDF)</button></a>'
    return href

# Carregamento e Alinhamento Seguro dos Dados
df_clientes = carregar_dados(FILE_CLIENTES, ['id','nome','cpf','tel','vei','pla','est','emp_name','status'])
df_empresas = carregar_dados(FILE_EMPRESAS, ['cnpj','nome','responsavel','telefone','email','est','status'])
df_prestadores = carregar_dados(FILE_PRESTADORES, ['id','nome','tipo','telefone','est','status'])
df_os = carregar_dados(FILE_OS, ['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os','zap_enviado'])

# Login
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.user = ""
    st.session_state.perfil = ""
    st.session_state.empresa_vinculada = ""

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
                    else: st.error("Usuário ou senha incorretos.")
                else: st.error("Usuário ou senha incorretos.")
    st.stop()

col_user, col_logout = st.columns([5, 1])
with col_user: st.write(f"**Central AD 24h | Operador:** `{st.session_state.user}`")
with col_logout:
    if st.button("Sair / Logoff"):
        st.session_state.logado = False
        st.rerun()

def colorir_status(val):
    return 'color: green; font-weight: bold;' if val == 'Ativo' else 'color: red; font-weight: bold;'

# --- VISÃO DO ADMINISTRADOR MASTER ---
if st.session_state.perfil == "Admin":
    menu = st.tabs(["📋 Nova OS", "📊 Relatórios & Baixa PDF", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores"])
    
    # Nova OS
    with menu[0]:
        if df_clientes.empty: st.warning("Nenhum cliente cadastrado no sistema.")
        else:
            st.subheader("📋 Abertura Rápida de Atendimento")
            if "busca_input" not in st.session_state: st.session_state.busca_input = ""
            if "loc_input" not in st.session_state: st.session_state.loc_input = ""
            if "dest_input" not in st.session_state: st.session_state.dest_input = ""
            if "obs_input" not in st.session_state: st.session_state.obs_input = ""
            
            busca = st.text_input("Digite o Nome, Placa ou CPF do cliente para buscar:", value=st.session_state.busca_input)
            if busca:
                df_clientes_busca = df_clientes.copy()
                df_clientes_busca['cpf_limpo'] = df_clientes_busca['cpf'].apply(apenas_numeros_letras)
                df_filtrado_cli = df_clientes_busca[df_clientes_busca['nome'].str.lower().str.contains(busca.lower()) | df_clientes_busca['pla'].str.lower().str.contains(busca.lower()) | df_clientes_busca['cpf_limpo'].str.contains(apenas_numeros_letras(busca))]
            else: df_filtrado_cli = df_clientes
                
            if df_filtrado_cli.empty: st.error("Nenhum cliente encontrado.")
            else:
                lista_ed_ops = [f"ID: {str(c['id'])} | {str(c['nome']).upper()} | Placa: {str(c['pla']).upper()} | Empresa: {str(c['emp_name']).upper()}" for _, c in df_filtrado_cli.iterrows()]
                c_ed_str = st.selectbox("Selecione o cliente confirmado abaixo:", options=lista_ed_ops, key="sel_ed")
                c_id = c_ed_str.split("|")[0].replace("ID:", "").strip()
                cliente_dados = df_clientes[df_clientes['id'].astype(str) == c_id].iloc[0]
                
                uf_cliente = str(cliente_dados['est']).strip().upper()
                if not uf_cliente: uf_cliente = "RN"
                st.info(f"📍 Empresa: **{str(cliente_dados['emp_name']).upper()}** | UF: **{uf_cliente}**")
                
                # Contador anual
                total_guinchos, total_p_seca, total_p_eletrica, total_borraceiro, total_chaveiro = 0, 0, 0, 0, 0
                if not df_os.empty:
                    df_os_copy = df_os.copy()
                    df_os_copy['data_hora'] = pd.to_datetime(df_os_copy['data_hora'], errors='coerce')
                    os_cliente_ano = df_os_copy[(df_os_copy['cliente_id'].astype(str) == str(c_id)) & (df_os_copy['data_hora'].dt.year == datetime.now().year)]
                    for _, o in os_cliente_ano.iterrows():
                        serv = str(o['tipo_servico']).lower()
                        if "guincho" in serv: total_guinchos += 1
                        elif "pane seca" in serv: total_p_seca += 1
                        elif "pane el" in serv or "eletrica" in serv: total_p_eletrica += 1
                        elif "chaveiro" in serv: total_chaveiro += 1
                        elif "borraceiro" in serv: total_borraceiro += 1
                
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Guinchos", f"{total_guinchos} / 2")
                c2.metric("Pane Seca", f"{total_p_seca} / 1")
                c3.metric("Pane Elétrica", f"{total_p_eletrica} / 1")
                c4.metric("Chaveiro", f"{total_chaveiro} / 1")
                c5.metric("Borraceiro", f"{total_borraceiro} / 1")
                
                tipo_servico = st.selectbox("Tipo de Serviço:", ["Guincho", "Pane Seca", "Pane Elétrica", "Borraceiro", "Chaveiro"])
                motivo_servico = st.selectbox("Motivo do Acionamento:", ["Acidente", "Furto", "Roubo", "Outros"])
                
                lista_p_ops = ["Outro (Digitar Manualmente)"]
                if not df_prestadores.empty:
                    df_prest_filtrados = df_prestadores[(df_prestadores['est'].str.strip().str.upper() == uf_cliente) & (df_prestadores['tipo'].str.lower().str.contains(tipo_servico.lower()))]
                    if not df_prest_filtrados.empty:
                        lista_p_ops += [f"{str(r['nome'])} - Tel: {str(r['telefone'])} ({str(r['est']).upper()})" for _, r in df_prest_filtrados.iterrows()]
                    else:
                        df_prest_estado = df_prestadores[df_prestadores['est'].str.strip().str.upper() == uf_cliente]
                        lista_p_ops += [f"{str(r['nome'])} - Tel: {str(r['telefone'])} ({str(r['est']).upper()})" for _, r in df_prest_estado.iterrows()]
                
                prestador_sel = st.selectbox("Prestador homologado:", options=lista_p_ops)
                if prestador_sel == "Outro (Digitar Manualmente)":
                    prestador_final = st.text_input("Nome do Prestador Manual:")
                    tel_prestador_final = apenas_numeros_letras(st.text_input("Telefone do Prestador Manual:"))
                else:
                    prestador_final = prestador_sel.split(" - Tel:")[0]
                    tel_prestador_final = apenas_numeros_letras(prestador_sel.split(" - Tel:")[1].split("(")[0])
                
                localizacao = st.text_input("Endereço de Origem:", value=st.session_state.loc_input)
                destino = st.text_input("Endereço de Destino:", value=st.session_state.dest_input)
                obs = st.text_area("Observações:", value=st.session_state.obs_input)
                
                if st.button("🚀 Registrar Chamado / Iniciar Atendimento"):
                    if not prestador_final: st.error("Identifique o prestador.")
                    else:
                        nova_id = int(df_os['id'].astype(float).max() + 1) if not df_os.empty else 1
                        nova_os = pd.DataFrame([{'id': str(nova_id), 'data_hora': obter_hora_brasilia(), 'cliente_id': str(c_id), 'cliente_nome': str(cliente_dados['nome']), 'empresa': str(cliente_dados['emp_name']), 'tipo_servico': tipo_servico, 'motivo': motivo_servico, 'prestador': f"{prestador_final} ({tel_prestador_final})", 'localizacao': localizacao, 'destino': destino, 'obs': obs, 'status_os': "EM ATENDIMENTO", 'zap_enviado': "NÃO"}])
                        df_os = pd.concat([df_os, nova_os], ignore_index=True)
                        salvar_dados(df_os, FILE_OS)
                        st.session_state.busca_input, st.session_state.loc_input, st.session_state.dest_input, st.session_state.obs_input = "", "", "", ""
                        st.success("✅ Chamado Aberto com Sucesso!")
                        time.sleep(1)
                        st.rerun()

    # Relatórios e Despacho
    with menu[1]:
        st.subheader("📊 Painel Logístico de Acompanhamento e Despacho 24h")
        if df_os.empty: st.info("Nenhuma OS aberta.")
        else:
            tipo_relatorio = st.radio("Escolha o modelo:", ["Painel de Chamados Ativos", "Tabela Geral Filtrada"], horizontal=True)
            if tipo_relatorio == "Tabela Geral Filtrada":
                st.dataframe(df_os, use_container_width=True)
            else:
                for idx, row in df_os.sort_values(by='id', ascending=False).iterrows():
                    os_id_str = str(row['id'])
                    status_os_atual = str(row['status_os']).upper()
                    if status_os_atual == "EM ATENDIMENTO":
                        with st.container():
                            col_os, col_status, col_acao = st.columns([3, 1.5, 2.5])
                            with col_os:
                                st.markdown(f"**OS Nº {row['id']}** | `{str(row['cliente_nome']).upper()}` | `{str(row['empresa']).upper()}`")
                                st.caption(f"📍 Origem: {row['localizacao']} ➡️ Destino: {row['destino']}")
                            with col_status:
                                st.markdown("🟠 `EM ATENDIMENTO`")
                                if str(row.get('zap_enviado', 'NÃO')).upper() == "SIM": st.markdown("✅ `💬 ENVIADO`")
                            with col_acao:
                                tel_p = "".join(filter(str.isdigit, str(row['prestador'])))
                                texto_w = f"*{str(row['empresa']).upper()} - ASSISTÊNCIA*\n*Chamado Nº:* {row['id']}\n*Serviço:* {row['tipo_servico']}\n*Cliente:* {str(row['cliente_nome']).upper()}\n*Origem:* {row['localizacao']}\n*Destino:* {row['destino']}"
                                link_d = f"https://api.whatsapp.com/send?phone=55{tel_p}&text={urllib.parse.quote(texto_w)}"
                                
                                c_zap, c_close = st.columns(2)
                                with c_zap:
                                    st.markdown(f'<a href="{link_d}" target="_blank"><button style="background-color: #25D366; color: white; padding: 6px 12px; border: none; border-radius: 4px; font-weight: bold; width: 100%;">📲 Despachar</button></a>', unsafe_allow_html=True)
                                    if st.button("✔️ Confirmar", key=f"conf_{os_id_str}"):
                                        df_os.loc[df_os['id'].astype(str) == os_id_str, 'zap_enviado'] = "SIM"
                                        salvar_dados(df_os, FILE_OS)
                                        st.rerun()
                                with c_close:
                                    if st.button("🔒 Encerrar", key=f"close_{os_id_str}"):
                                        df_os.loc[df_os['id'].astype(str) == os_id_str, 'status_os'] = "ENCERRADO"
                                        salvar_dados(df_os, FILE_OS)
                                        st.rerun()
                        st.markdown("---")
                    else:
                        st.write(f"✅ OS {os_id_str} Encerrada.")
                        st.markdown(exportar_pdf_html_oficial(df_os[df_os['id'].astype(str) == os_id_str], df_clientes, f"os_{os_id_str}"), unsafe_allow_html=True)

    # ==================== ABA: CLIENTES ====================
    with menu[2]:
        st.subheader("👤 Gerenciamento de Clientes")
        if "aba_cliente_index" not in st.session_state: st.session_state.aba_cliente_index = "Listar"
        opcao = st.radio("Ação Clientes:", ["Listar", "Incluir / Editar"], horizontal=True, index=0 if st.session_state.aba_cliente_index == "Listar" else 1)
        
        if opcao == "Listar":
            st.session_state.aba_cliente_index = "Listar"
            st.dataframe(df_clientes.style.map(colorir_status, subset=['status']), use_container_width=True)
        else:
            st.session_state.aba_cliente_index = "Incluir / Editar"
            modo = st.checkbox("Editar cliente existente")
            c_target = None
            dados_ant = None
            
            if modo and not df_clientes.empty:
                lista_ops_c = [f"{r['id']} - {r['nome']}" for _, r in df_clientes.iterrows()]
                sel = st.selectbox("Selecione o cliente:", options=lista_ops_c)
                c_target = sel.split(" - ")[0].strip()
                dados_ant = df_clientes[df_clientes['id'].astype(str) == c_target].iloc[0]
            
            # ATUALIZAÇÃO VIA SESSION_STATE PARA PREENCHIMENTO AUTOMÁTICO REAL INABALÁVEL
            val_nome = str(dados_ant['nome']).upper() if dados_ant is not None else ""
            val_cpf = str(dados_ant['cpf']) if dados_ant is not None else ""
            val_tel = str(dados_ant['tel']) if dados_ant is not None else ""
            val_vei = str(dados_ant['vei']).upper() if dados_ant is not None else ""
            val_pla = str(dados_ant['pla']).upper() if dados_ant is not None else ""
            
            nome_in = st.text_input("Nome Completo:", value=val_nome, key="txt_c_nome")
            cpf_raw = st.text_input("CPF:", value=val_cpf, key="txt_c_cpf")
            tel_raw = st.text_input("Telefone:", value=val_tel, key="txt_c_tel")
            vei_in = st.text_input("Veículo:", value=val_vei, key="txt_c_vei")
            pla_in = st.text_input("Placa:", value=val_pla, key="txt_c_pla")
            
            idx_est_c = ESTADOS_BR.index(dados_ant['est']) if (dados_ant is not None and dados_ant['est'] in ESTADOS_BR) else 19
            est = st.selectbox("UF:", ESTADOS_BR, index=idx_est_c, key="c_est")
            emp = st.selectbox("Empresa:", ["AD RASTREAMENTO VEICULAR"] + list(df_empresas['nome'].unique()), key="c_emp")
            status = st.selectbox("Status:", ["Ativo", "Inativo"], index=0 if dados_ant is None else ["Ativo", "Inativo"].index(dados_ant['status']), key="c_status")
            
            if st.button("Salvar Cliente", key="save_cli_master_btn"):
                if not nome_in or not pla_in: st.error("Nome e Placa obrigatórios.")
                else:
                    cnpj_limpo = apenas_numeros_letras(cpf_raw)
                    tel_limpo = apenas_numeros_letras(tel_raw)
                    if not modo:
                        prox = str(int(df_clientes['id'].astype(float).max() + 1) if not df_clientes.empty else 1)
                        novo = pd.DataFrame([{'id': prox, 'nome': nome_in.upper(), 'cpf': cnpj_limpo, 'tel': tel_limpo, 'vei': vei_in.upper(), 'pla': pla_in.upper(), 'est': est, 'emp_name': emp.upper(), 'status': status}])
                        df_clientes = pd.concat([df_clientes, novo], ignore_index=True)
                    else:
                        df_clientes.loc[df_clientes['id'].astype(str) == c_target, ['nome','cpf','tel','vei','pla','est','emp_name','status']] = [nome_in.upper(), cnpj_limpo, tel_limpo, vei_in.upper(), pla_in.upper(), est, emp.upper(), status]
                    salvar_dados(df_clientes, FILE_CLIENTES)
                    st.success("✅ Cliente salvo com sucesso!")
                    st.session_state.aba_cliente_index = "Listar"
                    time.sleep(1)
                    st.rerun()

            if modo and c_target is not None:
                st.write("---")
                if st.button("❌ Excluir Cliente Permanentemente", key="del_cli_btn_master"):
                    df_clientes = df_clientes[df_clientes['id'].astype(str) != c_target]
                    salvar_dados(df_clientes, FILE_CLIENTES)
                    st.error("🗑️ Cliente excluído permanentemente!")
                    st.session_state.aba_cliente_index = "Listar"
                    time.sleep(1)
                    st.rerun()

    # ==================== ABA: EMPRESAS ====================
    with menu[3]:
        st.subheader("🏢 Gerenciamento de Empresas Parceiras")
        if "aba_empresa_index" not in st.session_state: st.session_state.aba_empresa_index = "Listar"
        opcao_e = st.radio("Ação Empresas:", ["Listar", "Incluir / Editar"], horizontal=True, index=0 if st.session_state.aba_empresa_index == "Listar" else 1)
        
        if opcao_e == "Listar":
            st.session_state.aba_empresa_index = "Listar"
            st.dataframe(df_empresas.style.map(colorir_status, subset=['status']), use_container_width=True)
        else:
            st.session_state.aba_empresa_index = "Incluir / Editar"
            modo_e = st.checkbox("Editar empresa existente")
            e_target = None
            dados_e_ant = None
            
            if modo_e and not df_empresas.empty:
                lista_ops_e = [f"{r['cnpj']} - {r['nome']}" for _, r in df_empresas.iterrows()]
                sel_e = st.selectbox("Selecione a empresa:", options=lista_ops_e)
                e_target = apenas_numeros_letras(sel_e.split(" - ")[0])
                dados_e_ant = df_empresas[df_empresas['cnpj'].apply(apenas_numeros_letras) == e_target].iloc[0]
            
            # ATUALIZAÇÃO VIA SESSION_STATE PARA PREENCHIMENTO AUTOMÁTICO REAL INABALÁVEL
            val_cnpj = str(dados_e_ant['cnpj']) if dados_e_ant is not None else ""
            val_n_emp = str(dados_e_ant['nome']).upper() if dados_e_ant is not None else ""
            val_resp = str(dados_e_ant['responsavel']).upper() if dados_e_ant is not None else ""
            val_tel_e = str(dados_e_ant['telefone']) if dados_e_ant is not None else ""
            val_mail = str(dados_e_ant['email']) if dados_e_ant is not None else ""
            
            cnpj_raw = st.text_input("CNPJ da Empresa:", value=val_cnpj, key="txt_e_cnpj")
            n_emp = st.text_input("Nome da Empresa (Usuário de Login):", value=val_n_emp, key="txt_e_nome")
            resp = st.text_input("Nome do Responsável / Contato:", value=val_resp, key="txt_e_resp")
            tel_e_raw = st.text_input("Telefone da Central 24h:", value=val_tel_e, key="txt_e_tel")
            mail = st.text_input("E-mail corporativo:", value=val_mail, key="txt_e_mail")
            
            idx_est_e = ESTADOS_BR.index(dados_e_ant['est']) if (dados_e_ant is not None and dados_e_ant['est'] in ESTADOS_BR) else 19
            est_e = st.selectbox("Selecione o Estado (UF) da Sede:", ESTADOS_BR, index=idx_est_e, key="e_est")
            stat_e = st.selectbox("Status Parceria:", ["Ativo", "Inativo"], index=0 if dados_e_ant is None else ["Ativo", "Inativo"].index(dados_e_ant['status']), key="e_status")
            
            if st.button("Salvar Empresa", key="btn_save_empresa_master"):
                cnpj_f = apenas_numeros_letras(cnpj_raw)
                nome_f = n_emp.upper().strip()
                if not cnpj_f or not nome_f: st.error("CNPJ e Nome obrigatórios.")
                else:
                    if not modo_e:
                        novo_e = pd.DataFrame([{'cnpj': cnpj_f, 'nome': nome_f, 'responsavel': resp.upper(), 'telefone': apenas_numeros_letras(tel_e_raw), 'email': mail, 'est': est_e, 'status': stat_e}])
                        df_empresas = pd.concat([df_empresas, novo_e], ignore_index=True)
                    else:
                        df_empresas.loc[df_empresas['cnpj'].apply(apenas_numeros_letras) == e_target, ['cnpj', 'nome','responsavel','telefone','email','est','status']] = [cnpj_f, nome_f, resp.upper(), apenas_numeros_letras(tel_e_raw), mail, est_e, stat_e]
                    salvar_dados(df_empresas, FILE_EMPRESAS)
                    st.success("✅ Empresa salva com sucesso!")
                    st.session_state.aba_empresa_index = "Listar"
                    time.sleep(1)
                    st.rerun()

            if modo_e and e_target is not None:
                st.write("---")
                if st.button("❌ Excluir Empresa Permanentemente", key="del_emp_btn_master"):
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
        if "aba_prestador_index" not in st.session_state: st.session_state.aba_prestador_index = "Listar"
        opcao_p = st.radio("Ação Prestadores:", ["Listar", "Incluir / Editar"], horizontal=True, index=0 if st.session_state.aba_prestador_index == "Listar" else 1)
        
        if opcao_p == "Listar":
            st.session_state.aba_prestador_index = "Listar"
            st.dataframe(df_prestadores, use_container_width=True)
        else:
            st.session_state.aba_prestador_index = "Incluir / Editar"
            modo_p = st.checkbox("Editar prestador existente")
            p_target = None
            dados_p_ant = None
            
            if modo_p and not df_prestadores.empty:
                lista_ops_p = [f"{r['id']} - {r['nome']}" for _, r in df_prestadores.iterrows()]
                sel_p = st.selectbox("Selecione o prestador:", options=lista_ops_p)
                p_target = sel_p.split(" - ")[0].strip()
                dados_p_ant = df_prestadores[df_prestadores['id'].astype(str) == p_target].iloc[0]
            
            # ATUALIZAÇÃO VIA SESSION_STATE PARA PREENCHIMENTO AUTOMÁTICO REAL INABALÁVEL
            val_n_prest = str(dados_p_ant['nome']).upper() if dados_p_ant is not None else ""
            val_tel_p = str(dados_p_ant['telefone']) if dados_p_ant is not None else ""
            
            n_prest = st.text_input("Nome do Guincho/Prestador:", value=val_n_prest, key="txt_p_nome")
            tel_p_raw = st.text_input("Telefone de Contato (Com DDD):", value=val_tel_p, key="txt_p_tel")
            
            lista_valores_padrao = ["Guincho"]
            if modo_p and dados_p_ant is not None:
                lista_valores_padrao = [s.strip() for s in str(dados_p_ant['tipo']).split(",") if s.strip() in SERVICOS_DISPONIVEIS]
            tipos_sel = st.multiselect("Serviços Cobertos:", options=SERVICOS_DISPONIVEIS, default=lista_valores_padrao, key="p_tipo_multi")
            
            idx_est_p = ESTADOS_BR.index(dados_p_ant['est']) if (dados_p_ant is not None and dados_p_ant['est'] in ESTADOS_BR) else 19
            est_p = st.selectbox("Selecione o Estado (UF) de Atuação:", ESTADOS_BR, index=idx_est_p, key="p_est")
            stat_p = st.selectbox("Status Prestador:", ["Ativo", "Inativo"], index=0 if dados_p_ant is None else ["Ativo", "Inativo"].index(dados_p_ant['status']), key="p_status")
            
            if st.button("Salvar Prestador", key="btn_save_prestador_master"):
                if not n_prest: st.error("Nome obrigatório.")
                else:
                    tipo_f = ", ".join(tipos_sel) if tipos_sel else "Guincho"
                    tel_limpo = apenas_numeros_letras(tel_p_raw)
                    if not modo_p:
                        prox_p = str(int(df_prestadores['id'].astype(float).max() + 1) if not df_prestadores.empty else 1)
                        novo_p = pd.DataFrame([{'id': prox_p, 'nome': n_prest.upper(), 'tipo': tipo_f, 'telefone': tel_limpo, 'est': est_p, 'status': stat_p}])
                        df_prestadores = pd.concat([df_prestadores, novo_p], ignore_index=True)
                    else:
                        df_prestadores.loc[df_prestadores['id'].astype(str) == p_target, ['nome','tipo','telefone','est','status']] = [n_prest.upper(), tipo_f, tel_limpo, est_p, stat_p]
                    salvar_dados(df_prestadores, FILE_PRESTADORES)
                    st.success("✅ Prestador salvo com sucesso!")
                    st.session_state.aba_prestador_index = "Listar"
                    time.sleep(1)
                    st.rerun()

            if modo_p and p_target is not None:
                st.write("---")
                if st.button("❌ Excluir Prestador Permanentemente", key="del_prest_btn_master"):
                    df_prestadores = df_prestadores[df_prestadores['id'].astype(str) != p_target]
                    salvar_dados(df_prestadores, FILE_PRESTADORES)
                    st.error("🗑️ Prestador excluído permanentemente!")
                    st.session_state.aba_prestador_index = "Listar"
                    time.sleep(1)
                    st.rerun()

# --- ABA DE VISÃO DAS EMPRESAS PARCEIRAS ---
else:
    menu_parceiro = st.tabs(["👥 Nossos Clientes", "📋 Chamados Cobertos"])
    with menu_parceiro[0]:
        df_filtrado_p = df_clientes[df_clientes['emp_name'].str.lower() == st.session_state.empresa_vinculada.lower()]
        st.dataframe(df_filtrado_p, use_container_width=True)
