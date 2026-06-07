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
    pd.DataFrame(columns=['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs']).to_csv(FILE_OS, index=False)

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
        
    data = {
        "message": f"🔥 Auto-salvamento de dados: {caminho_local}",
        "content": content,
        "branch": "main"
    }
    if sha:
        data["sha"] = sha
        
    requests.put(url, headers=headers, json=data)

# Funções de Leitura e Escrita
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
                <p style="margin: 3px 0; font-size: 13px; color: #333;">Horário de Abertura: {row['data_hora']} | Status Atual: Encerrado</p>
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

# Controle de Sessão / Login
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.user = ""
    st.session_state.perfil = ""
    st.session_state.empresa_vinculada = ""

# Carregamento dos Bancos de Dados
df_clientes = carregar_dados(FILE_CLIENTES, ['id','nome','cpf','tel','vei','pla','est','emp_name','status'])
df_empresas = carregar_dados(FILE_EMPRESAS, ['cnpj','nome','responsavel','telefone','email','est','status'])
df_prestadores = carregar_dados(FILE_PRESTADORES, ['id','nome','tipo','telefone','est','status'])
df_os = carregar_dados(FILE_OS, ['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs'])

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
with col_user:
    st.write(f"**Central AD 24h | Operador:** `{st.session_state.user}`")
with col_logout:
    if st.button("Sair / Logoff"):
        st.session_state.logado = False
        st.rerun()

# --- VISÃO DO ADMINISTRADOR MASTER ---
if st.session_state.perfil == "Admin":
    menu = st.tabs(["📋 Nova OS", "📊 Relatórios & Baixa PDF", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores"])
    
    # ==================== ABA: NOVA OS ====================
    with menu[0]:
        if df_clientes.empty:
            st.warning("Nenhum cliente cadastrado no sistema.")
        else:
            st.subheader("🔍 Localizar Cliente")
            busca = st.text_input("Digite o Nome, Placa ou CPF do cliente para buscar:").strip().lower()
            
            if busca:
                df_clientes_busca = df_clientes.copy()
                df_clientes_busca['cpf_limpo'] = df_clientes_busca['cpf'].apply(apenas_numeros_letras)
                busca_limpa = apenas_numeros_letras(busca)
                
                df_filtrado_cli = df_clientes_busca[
                    df_clientes_busca['nome'].str.lower().str.contains(busca) |
                    df_filtrado_cli['pla'].str.lower().str.contains(busca) |
                    df_clientes_busca['cpf_limpo'].str.contains(busca_limpa)
                ]
            else:
                df_filtrado_cli = df_clientes
                
            if df_filtrado_cli.empty:
                st.error("Nenhum cliente encontrado com esse termo de busca.")
            else:
                lista_ed_ops = [f"ID: {str(c['id'])} | {str(c['nome']).upper()} | Placa: {str(c['pla']).upper()} | Empresa: {str(c['emp_name']).upper()}" for _, c in df_filtrado_cli.iterrows()]
                c_ed_str = st.selectbox("Selecione o cliente confirmado abaixo:", options=lista_ed_ops, key="sel_ed")
                c_id = c_ed_str.split("|")[0].replace("ID:", "").strip()
                cliente_dados = df_clientes[df_clientes['id'].astype(str) == c_id].iloc[0]
                
                uf_cliente = str(cliente_dados['est']).strip().upper()
                if not uf_cliente: uf_cliente = "RN"
                st.info(f"📍 Cliente vinculado à empresa: **{str(cliente_dados['emp_name']).upper()}** | Estado do Veículo: **{uf_cliente}**")
                
                # Contador anual de acionamentos
                ano_atual = datetime.now().year
                total_guinchos, total_p_seca, total_p_eletrica, total_borraceiro, total_chaveiro = 0, 0, 0, 0, 0
                
                if not df_os.empty and 'cliente_id' in df_os.columns:
                    df_os['data_hora'] = pd.to_datetime(df_os['data_hora'], errors='coerce')
                    os_cliente_ano = df_os[(df_os['cliente_id'].astype(str) == str(c_id)) & (df_os['data_hora'].dt.year == ano_atual)]
                    for _, o in os_cliente_ano.iterrows():
                        serv = str(o['tipo_servico']).lower()
                        if "guincho" in serv: total_guinchos += 1
                        elif "pane seca" in serv: total_p_seca += 1
                        elif "pane el" in serv or "eletrica" in serv: total_p_eletrica += 1
                        elif "chaveiro" in serv: total_chaveiro += 1
                        elif "borraceiro" in serv: total_borraceiro += 1
                
                st.markdown(f"#### 📊 Saldo de Acionamentos no Ano ({ano_atual})")
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
                    df_prest_filtrados = df_prestadores[df_prestadores['est'].str.strip().str.upper() == uf_cliente]
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
                
                localizacao = st.text_input("Endereço de Origem (Localização atual):")
                destino = st.text_input("Endereço de Destino:")
                obs = st.text_area("Observações:")
                
                if st.button("🚀 Iniciar Atendimento / Gerar OS"):
                    if not prestador_final or not tel_prestador_final:
                        st.error("Identifique o Nome e o Telefone do prestador.")
                    else:
                        nova_id = int(df_os['id'].astype(float).max() + 1) if not df_os.empty else 1
                        agora_str = obter_hora_brasilia()
                        
                        nova_os = pd.DataFrame([{
                            'id': str(nova_id), 'data_hora': agora_str, 'cliente_id': str(c_id),
                            'cliente_nome': str(cliente_dados['nome']), 'empresa': str(cliente_dados['emp_name']),
                            'tipo_servico': tipo_servico, 'motivo': motivo_servico, 'prestador': f"{prestador_final} | Telefone/Zap: {tel_prestador_final}",
                            'localizacao': localizacao, 'destino': destino, 'obs': obs
                        }])
                        df_os = pd.concat([df_os, nova_os], ignore_index=True)
                        salvar_dados(df_os, FILE_OS)
                        st.success("✅ Ordem de Serviço gravada com sucesso!")
                        
                        texto_whatsapp = (
                            f"*{str(cliente_dados['emp_name']).upper()} - ASSISTÊNCIA 24H*\n"
                            f"-----------------------------------------\n"
                            f"*Chamado Nº:* {nova_id}\n"
                            f"*Data/Hora:* {agora_str}\n"
                            f"*Serviço:* {tipo_servico} | *Motivo:* {motivo_servico}\n\n"
                            f"*Cliente:* {str(cliente_dados['nome']).upper()}\n"
                            f"*Telefone do Cliente:* {str(cliente_dados['tel'])}\n\n"
                            f"*Veículo:* {str(cliente_dados['vei'])} - Placa: {str(cliente_dados['pla']).upper()}\n\n"
                            f"*Origem:* {localizacao}\n"
                            f"*Destino:* {destino}\n\n"
                            f"*Obs:* {obs}"
                        )
                        link_w = f"https://api.whatsapp.com/send?phone=55{tel_prestador_final}&text={urllib.parse.quote(texto_whatsapp)}"
                        st.markdown(f'<a href="{link_w}" target="_blank"><button style="background-color: #25D366; color: white; padding: 10px 20px; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">➡️ Enviar Diretamente para o WhatsApp do Prestador</button></a>', unsafe_allow_html=True)

    # ==================== ABA: RELATÓRIOS ====================
    with menu[1]:
        st.subheader("📊 Emissão e Impressão de Relatórios")
        if df_os.empty: 
            st.info("Nenhuma OS aberta no sistema.")
        else:
            tipo_relatorio = st.radio("Escolha o modelo de exportação:", ["Tabela Filtrada Geral", "Documento de uma OS Específica"], horizontal=True)
            
            if tipo_relatorio == "Tabela Filtrada Geral":
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    lista_filt_emp = ["TODAS"] + list(df_os['empresa'].unique())
                    emp_escolhida = st.selectbox("Filtrar por Empresa:", options=lista_filt_emp)
                with col_f2:
                    lista_filt_cli = ["TODOS"] + list(df_os['cliente_nome'].unique())
                    cli_escolhido = st.selectbox("Filtrar por Cliente Específico:", options=lista_filt_cli)
                    
                df_os_filtrada = df_os.copy()
                if emp_escolhida != "TODAS":
                    df_os_filtrada = df_os_filtrada[df_os_filtrada['empresa'] == emp_escolhida]
                if cli_escolhido != "TODOS":
                    df_os_filtrada = df_os_filtrada[df_os_filtrada['cliente_nome'] == cli_escolhido]
                    
                st.write("---")
                st.dataframe(df_os_filtrada, use_container_width=True)
                
                if not df_os_filtrada.empty:
                    st.markdown(exportar_pdf_html_oficial(df_os_filtrada, df_clientes, "relatorio_geral_filtrado"), unsafe_allow_html=True)
            
            else:
                st.markdown("### 📄 Localizar OS por Cliente")
                lista_clientes_com_os = list(df_os['cliente_nome'].unique())
                cli_alvo_pdf = st.selectbox("Selecione o Cliente para listar os acionamentos:", options=lista_clientes_com_os)
                
                df_os_do_cliente = df_os[df_os['cliente_nome'] == cli_alvo_pdf].sort_values(by='id', ascending=False)
                lista_os_dele = [f"Chamado Nº: {r['id']} | Data: {r['data_hora']} | Servicio: {r['tipo_servico']}" for _, r in df_os_do_cliente.iterrows()]
                
                os_escolhida_str = st.selectbox("Selecione qual acionamento deseja extrair o PDF:", options=lista_os_dele, index=0)
                os_alvo_id = os_escolhida_str.split("|")[0].replace("Chamado Nº:", "").strip()
                
                df_os_unica = df_os[df_os['id'].astype(str) == os_alvo_id]
                
                st.write("---")
                st.markdown("#### Preview do Documento Selecionado:")
                st.markdown(exportar_pdf_html_oficial(df_os_unica, df_clientes, f"os_individual_{os_alvo_id}"), unsafe_allow_html=True)

    # ==================== ABA: CLIENTES ====================
    with menu[2]:
        st.subheader("👤 Gerenciamento de Clientes")
        if "aba_cliente_index" not in st.session_state: st.session_state.aba_cliente_index = "Listar"
        opcao = st.radio("Ação Clientes:", ["Listar", "Incluir / Editar"], horizontal=True, index=0 if st.session_state.aba_cliente_index == "Listar" else 1)
        
        if opcao == "Listar":
            st.session_state.aba_cliente_index = "Listar"
            if df_clientes.empty: st.info("Nenhum cliente cadastrado.")
            else: st.dataframe(df_clientes.style.map(colorir_status, subset=['status']), use_container_width=True)
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
            
            # BLINK DE DADOS ATUAIS EM TELA (PREVENÇÃO DE ERROS)
            if modo and dados_ant is not None:
                st.markdown(f"""
                > 📑 **Dados Cadastrados Atualmente:** > * **Nome:** {dados_ant['nome']} | **CPF/CNPJ:** {dados_ant['cpf']} | **Telefone:** {dados_ant['tel']}  
                > * **Veículo:** {dados_ant['vei']} | **Placa:** {dados_ant['pla']} | **Vínculo:** {dados_ant['emp_name']}  
                """)
                
            nome_in = st.text_input("Nome Completo:", key="c_nome")
            cpf_raw = st.text_input("CPF/CNPJ (Aceita pontos/traços):", key="c_cpf")
            tel_raw = st.text_input("Telefone de Contato:", key="c_tel")
            vei_in = st.text_input("Veículo (Modelo/Ano):", key="c_vei")
            pla_in = st.text_input("Placa do Veículo:", key="c_pla")
            
            idx_est_c = ESTADOS_BR.index(str(dados_ant['est']).upper()) if (dados_ant is not None and str(dados_ant['est']).upper() in ESTADOS_BR) else ESTADOS_BR.index("RN")
            est = st.selectbox("Selecione o Estado (UF) do Veículo:", options=ESTADOS_BR, index=idx_est_c, key="c_est")
            
            lista_empresas_disponiveis = ["AD RASTREAMENTO VEICULAR"]
            if not df_empresas.empty:
                lista_empresas_disponiveis = [str(e['nome']).upper() for _, e in df_empresas.iterrows()]
                if "AD RASTREAMENTO VEICULAR" not in lista_empresas_disponiveis:
                    lista_empresas_disponiveis.insert(0, "AD RASTREAMENTO VEICULAR")
            
            idx_emp = 0
            if dados_ant is not None:
                emp_ant_upper = str(dados_ant['emp_name']).upper()
                if emp_ant_upper in lista_empresas_disponiveis: idx_emp = lista_empresas_disponiveis.index(emp_ant_upper)
                    
            emp = st.selectbox("Selecione a Empresa Vinculada para este Cliente:", options=lista_empresas_disponiveis, index=idx_emp, key="c_emp")
            status = st.selectbox("Status do Cliente:", ["Ativo", "Inativo"], index=0 if dados_ant is None else ["Ativo", "Inativo"].index(str(dados_ant['status'])), key="c_status")
            
            if st.button("Salvar Cliente", key="save_cli_btn_novo"):
                # LÓGICA DE MESCLAGEM BLINDADA CONTRA APAGAMENTOS
                if modo and dados_ant is not None:
                    nome = nome_in if nome_in else dados_ant['nome']
                    cpf = apenas_numeros_letras(cpf_raw) if cpf_raw else dados_ant['cpf']
                    tel = apenas_numeros_letras(tel_raw) if tel_raw else dados_ant['tel']
                    vei = vei_in if vei_in else dados_ant['vei']
                    pla = pla_in.upper().replace("-","").replace(" ","") if pla_in else dados_ant['pla']
                else:
                    nome = nome_in
                    cpf = apenas_numeros_letras(cpf_raw)
                    tel = apenas_numeros_letras(tel_raw)
                    vei = vei_in
                    pla = pla_in.upper().replace("-","").replace(" ","")
                
                if not nome or not pla:
                    st.error("Nome e Placa são obrigatórios para concluir o registro.")
                else:
                    if not modo:
                        prox = int(df_clientes['id'].astype(float).max() + 1) if not df_clientes.empty else 1
                        novo = pd.DataFrame([{'id': str(prox), 'nome': nome.upper(), 'cpf': cpf, 'tel': tel, 'vei': vei.upper(), 'pla': pla, 'est': est, 'emp_name': emp.upper(), 'status': status}])
                        df_clientes = pd.concat([df_clientes, novo], ignore_index=True)
                    else:
                        df_clientes.loc[df_clientes['id'].astype(str) == c_target, ['nome','cpf','tel','vei','pla','est','emp_name','status']] = [nome.upper(), cpf, tel, vei.upper(), pla, est, emp.upper(), status]
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
        if "aba_empresa_index" not in st.session_state: st.session_state.aba_empresa_index = "Listar"
        opcao_e = st.radio("Ação Empresas:", ["Listar", "Incluir / Editar"], horizontal=True, index=0 if st.session_state.aba_empresa_index == "Listar" else 1)
        
        if opcao_e == "Listar":
            st.session_state.aba_empresa_index = "Listar"
            if df_empresas.empty: st.info("Nenhuma empresa cadastrada.")
            else: st.dataframe(df_empresas.style.map(colorir_status, subset=['status']), use_container_width=True)
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
            
            # NOVO: Texto fixo inabalável trazendo as informações do banco para a tela!
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
                # REGRA DE OURO DE MESCLAGEM: Se o usuário não digitou nada na caixa, pega o que já estava salvo no banco!
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
        if "aba_prestador_index" not in st.session_state: st.session_state.aba_prestador_index = "Listar"
        opcao_p = st.radio("Ação Prestadores:", ["Listar", "Incluir / Editar"], horizontal=True, index=0 if st.session_state.aba_prestador_index == "Listar" else 1)
        
        if opcao_p == "Listar":
            st.session_state.aba_prestador_index = "Listar"
            if df_prestadores.empty: st.info("Nenhum prestador cadastrado.")
            else: st.dataframe(df_prestadores, use_container_width=True)
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
                        novo_p = pd.DataFrame([{'id': str(prox_p), 'nome': n_prest, 'tipo': t_prest, 'telefone': tel_p, 'est': est_p, 'status': stat_p}])
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
                > * **Veículo:** {dados_part_ant['vei']} | **Placa:** {dados_part_ant['pla']}  
                """)
            
            p_nome_in = st.text_input("Nome Completo:", key="part_nome")
            p_cpf_raw = st.text_input("CPF:", key="part_cpf")
            p_tel_raw = st.text_input("Telefone:", key="part_tel")
            p_vei_in = st.text_input("Veículo:", key="part_vei")
            p_pla_in = st.text_input("Placa:", key="part_pla")
            
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
                else:
                    p_nome = p_nome_in.upper()
                    p_cpf = apenas_numeros_letras(p_cpf_raw)
                    p_tel = apenas_numeros_letras(p_tel_raw)
                    p_vei = p_vei_in.upper()
                    p_pla = p_pla_in.upper().replace("-","").replace(" ","")
                
                if not p_nome or not p_pla:
                    st.error("Nome e Placa são obrigatórios.")
                else:
                    if not modo_part:
                        prox_id = int(df_clientes['id'].astype(float).max() + 1) if not df_clientes.empty else 1
                        novo_reg = pd.DataFrame([{'id': str(prox_id), 'nome': p_nome.upper(), 'cpf': p_cpf, 'tel': p_tel, 'vei': p_vei.upper(), 'pla': p_pla, 'est': p_est, 'emp_name': st.session_state.empresa_vinculada.upper(), 'status': p_stat}])
                        df_clientes = pd.concat([df_clientes, novo_reg], ignore_index=True)
                    else:
                        df_clientes.loc[df_clientes['id'].astype(str) == part_target, ['nome','cpf','tel','vei','pla','est','status']] = [p_nome.upper(), p_cpf, p_tel, p_vei.upper(), p_pla, p_est, p_stat]
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
