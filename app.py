import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
import base64

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

# Caminhos dos arquivos de banco de dados
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
    pd.DataFrame(columns=['id','nome','tipo','telefone','cidade','est','status']).to_csv(FILE_PRESTADORES, index=False)
if not os.path.exists(FILE_OS):
    pd.DataFrame(columns=['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','prestador','localizacao','destino','obs']).to_csv(FILE_OS, index=False)

# Funções de Leitura e Escrita - PROTEGIDA CONTRA COLUNAS FALTANTES
def carregar_dados(caminho, colunas_obrigatorias):
    try:
        df = pd.read_csv(caminho)
        df.columns = df.columns.str.strip().str.lower()
        
        # Garante que todas as colunas obrigatórias existam para evitar o KeyError
        for col in colunas_obrigatorias:
            if col not in df.columns:
                df[col] = ""
                
        for col in df.columns:
            df[col] = df[col].fillna("").astype(str)
        return df
    except:
        return pd.DataFrame(columns=colunas_obrigatorias)

def salvar_dados(df, caminho):
    df.to_csv(caminho, index=False)

# Gerador de Relatório PDF/HTML Elegante e Personalizado por Empresa
def exportar_pdf_html_bonito(df_os_rows):
    cards_html = ""
    for _, row in df_os_rows.iterrows():
        empresa_os = str(row['empresa']).upper()
        cor_topo = "#7B2CBF" if "AD RASTREAMENTO" in empresa_os else "#1E3A8A"
        
        cards_html += f"""
        <div style="border: 2px solid #ddd; border-radius: 8px; margin-bottom: 30px; overflow: hidden; page-break-inside: avoid;">
            <div style="background-color: {cor_topo}; color: white; padding: 15px; font-size: 18px; font-weight: bold; text-align: center;">
                {empresa_os} - CENTRAL DE ASSISTÊNCIA 24H
            </div>
            <div style="padding: 20px; font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="width: 50%; padding: 5px; font-size: 14px;"><strong>Nº do Chamado (OS):</strong> {row['id']}</td>
                        <td style="width: 50%; padding: 5px; font-size: 14px; text-align: right;"><strong>Data/Hora:</strong> {row['data_hora']}</td>
                    </tr>
                    <tr>
                        <td colspan="2" style="padding: 5px; font-size: 14px; border-bottom: 1px solid #eee;"><strong>Tipo de Serviço:</strong> <span style="color: #E53935; font-weight: bold;">{row['tipo_servico']}</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 5px 5px 5px; font-size: 14px;"><strong>Cliente:</strong> {str(row['cliente_nome']).upper()} (ID: {row['cliente_id']})</td>
                        <td style="padding: 10px 5px 5px 5px; font-size: 14px; text-align: right;"><strong>Prestador Acionado:</strong> {str(row['prestador']).upper()}</td>
                    </tr>
                    <tr>
                        <td colspan="2" style="padding: 5px; font-size: 14px;"><strong>Endereço de Origem:</strong> {row['localizacao']}</td>
                    </tr>
                    <tr>
                        <td colspan="2" style="padding: 5px; font-size: 14px; border-bottom: 1px solid #eee;"><strong>Endereço de Destino:</strong> {row['destino']}</td>
                    </tr>
                    <tr>
                        <td colspan="2" style="padding: 10px 5px 5px 5px; font-size: 13px; background-color: #f9f9f9; border-radius: 4px; margin-top: 5px;">
                            <strong>Observações do Atendimento:</strong><br>
                            {row['obs'] if row['obs'] else 'Nenhuma observação registrada.'}
                        </td>
                    </tr>
                </table>
            </div>
        </div>
        """
        
    html_completo = f"""
    <html>
    <head>
    <title>Relatório de Acionamentos</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 30px; background-color: #fff; }}
        .header {{ text-align: center; margin-bottom: 40px; border-bottom: 3px double #7B2CBF; padding-bottom: 10px; }}
        .header h1 {{ margin: 0; color: #333; font-size: 26px; }}
        .header p {{ margin: 5px 0 0 0; color: #666; font-size: 14px; }}
    </style>
    </head>
    <body>
        <div class="header">
            <h1>RELATÓRIO FILTRADO DE ACIONAMENTOS</h1>
            <p>Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>
        {cards_html}
    </body>
    </html>
    """
    b64 = base64.b64encode(html_completo.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="relatorio_filtrado_{datetime.now().strftime("%Y%m%d")}.html" style="text-decoration: none;"><button style="background-color: #E53935; color: white; padding: 12px 24px; border: none; border-radius: 6px; font-size: 15px; font-weight: bold; cursor: pointer; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">🖨️ Baixar Relatório Selecionado (PDF)</button></a>'
    return href

# Controle de Sessão / Login
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.user = ""
    st.session_state.perfil = ""
    st.session_state.empresa_vinculada = ""

# Interface de Login
if not st.session_state.logado:
    st.write("---")
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("### 🔑 Digite suas credenciais de acesso")
        usuario_input = st.text_input("Usuário (Nome da Empresa):").strip().lower()
        senha_input = st.text_input("Senha (CNPJ):", type="password").strip()
        
        if st.button("Entrar no Sistema", use_container_width=True):
            if usuario_input == "adrastreamentoveicular" and senha_input == "00000000000000":
                st.session_state.logado = True
                st.session_state.user = "AD Rastreamento (ADMIN)"
                st.session_state.perfil = "Admin"
                st.rerun()
            else:
                df_emp = carregar_dados(FILE_EMPRESAS, ['cnpj','nome','responsavel','telefone','email','est','status'])
                if not df_emp.empty:
                    parceiro_valid = df_emp[(df_emp['cnpj'].astype(str) == senha_input) & (df_emp['nome'].str.lower().str.replace(" ", "") == usuario_input.replace(" ", ""))]
                    if not parceiro_valid.empty:
                        st.session_state.logado = True
                        st.session_state.user = parceiro_valid.iloc[0]['nome'].upper()
                        st.session_state.perfil = "Parceiro"
                        st.session_state.empresa_vinculada = parceiro_valid.iloc[0]['nome']
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos para a empresa informada.")
                else:
                    st.error("Usuário ou senha incorretos para a empresa informada.")
    st.stop()

# Menu superior
col_user, col_logout = st.columns([5, 1])
with col_user:
    st.write(f"**Central AD 24h | Empresa:** `{st.session_state.user}`")
with col_logout:
    if st.button("Sair / Logoff"):
        st.session_state.logado = False
        st.rerun()

# Carregamento Seguro com validação de colunas obrigatorias
df_clientes = carregar_dados(FILE_CLIENTES, ['id','nome','cpf','tel','vei','pla','est','emp_name','status'])
df_empresas = carregar_dados(FILE_EMPRESAS, ['cnpj','nome','responsavel','telefone','email','est','status'])
df_prestadores = carregar_dados(FILE_PRESTADORES, ['id','nome','tipo','telefone','cidade','est','status'])
df_os = carregar_dados(FILE_OS, ['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','prestador','localizacao','destino','obs'])

def colorir_status(val):
    return 'color: green; font-weight: bold;' if val == 'Ativo' else 'color: red; font-weight: bold;'

# --- VISÃO DO ADMINISTRADOR ---
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
                df_filtrado_cli = df_clientes[
                    df_clientes['nome'].str.lower().str.contains(busca) |
                    df_clientes['pla'].str.lower().str.contains(busca) |
                    df_clientes['cpf'].astype(str).str.contains(busca)
                ]
            else:
                df_filtrado_cli = df_clientes
                
            if df_filtrado_cli.empty:
                st.error("Nenhum cliente encontrado com esse termo de busca.")
            else:
                lista_ed_ops = [f"ID: {str(c['id'])} | {str(c['nome']).upper()} | Placa: {str(c['pla']).upper()} | UF: {str(c['est']).upper()}" for _, c in df_filtrado_cli.iterrows()]
                c_ed_str = st.selectbox("Selecione o cliente confirmado abaixo:", options=lista_ed_ops, key="sel_ed")
                c_id = c_ed_str.split("|")[0].replace("ID:", "").strip()
                cliente_dados = df_clientes[df_clientes['id'].astype(str) == c_id].iloc[0]
                
                uf_cliente = str(cliente_dados['est']).strip().upper()
                if not uf_cliente:
                    uf_cliente = "RN"
                st.info(f"📍 Cliente localizado no estado: **{uf_cliente}**")
                
                # Contador anual de acionamentos
                ano_atual = datetime.now().year
                total_guinchos, total_p_seca, total_p_eletrica, total_borraceiro, total_chaveiro = 0, 0, 0, 0, 0
                
                if not df_os.empty and 'cliente_id' in df_os.columns:
                    df_os['data_hora'] = pd.to_datetime(df_os['data_hora'], errors='coerce')
                    os_cliente_ano = df_os[(df_os['cliente_id'].astype(str) == str(c_id)) & (df_os['data_hora'].dt.year == ano_atual)]
                    for _, o in os_cliente_ano.iterrows():
                        serv = str(o['tipo_servico']).lower()
                        if "guinch" in serv or "prancha" in serv: total_guinchos += 1
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
                
                tipo_servico = st.selectbox("Tipo de Serviço:", ["Guincho - Prancha Seca", "Pane Seca", "Pane Elétrica", "Chaveiro", "Borraceiro"])
                
                # FILTRAGEM INTELIGENTE DE PRESTADORES POR ESTADO (UF)
                lista_p_ops = ["Outro (Digitar Manualmente)"]
                if not df_prestadores.empty:
                    df_prest_filtrados = df_prestadores[df_prestadores['est'].str.strip().str.upper() == uf_cliente]
                    if not df_prest_filtrados.empty:
                        lista_p_ops += [f"{str(r['nome'])} - Tel: {str(r['telefone'])} ({str(r['cidade']).upper()}-{str(r['est']).upper()})" for _, r in df_prest_filtrados.iterrows()]
                    else:
                        st.warning(f"⚠️ Nenhum prestador cadastrado para o estado {uf_cliente}. Mostrando todos os prestadores do Brasil como contingência.")
                        lista_p_ops += [f"{str(r['nome'])} - Tel: {str(r['telefone'])} ({str(r['cidade']).upper()}-{str(r['est']).upper()})" for _, r in df_prestadores.iterrows()]
                
                prestador_sel = st.selectbox("Prestador homologado para o Estado do Cliente:", lista_p_ops)
                
                if prestador_sel == "Outro (Digitar Manualmente)":
                    p_nome_manual = st.text_input("Nome do Prestador Manual:")
                    p_tel_manual = st.text_input("Telefone do Prestador Manual (DDD + Número):")
                    prestador_final = p_nome_manual
                    tel_prestador_final = p_tel_manual.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
                else:
                    prestador_final = prestador_sel.split(" - Tel:")[0]
                    tel_cru = prestador_sel.split(" - Tel:")[1].split("(")[0].strip()
                    tel_prestador_final = tel_cru.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
                
                localizacao = st.text_input("Endereço de Origem (Localização atual):")
                destino = st.text_input("Endereço de Destino:")
                obs = st.text_area("Observações:")
                
                if st.button("🚀 Iniciar Atendimento / Gerar OS"):
                    if not prestador_final or not tel_prestador_final:
                        st.error("Identifique o Nome e o Telefone do prestador.")
                    else:
                        nova_id = int(df_os['id'].astype(float).max() + 1) if not df_os.empty else 1
                        agora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        nova_os = pd.DataFrame([{
                            'id': str(nova_id), 'data_hora': agora_str, 'cliente_id': str(c_id),
                            'cliente_nome': str(cliente_dados['nome']), 'empresa': str(cliente_dados['emp_name']),
                            'tipo_servico': tipo_servico, 'prestador': f"{prestador_final} ({tel_prestador_final})",
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
                            f"*Serviço:* {tipo_servico}\n\n"
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
        st.subheader("📊 Painel de Filtros para Emissão de Relatório")
        
        if df_os.empty: 
            st.info("Nenhuma OS aberta no momento.")
        else:
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
            
            st.write("---")
            st.markdown("### 🖨️ Impressão do Relatório Customizado da Seleção")
            if df_os_filtrada.empty:
                st.warning("Nenhum dado corresponde aos filtros selecionados para gerar o PDF.")
            else:
                st.markdown(exportar_pdf_html_bonito(df_os_filtrada), unsafe_allow_html=True)

    # ==================== ABA: CLIENTES ====================
    with menu[2]:
        st.subheader("Modificar Cadastro Clientes")
        opcao = st.radio("Ação Clientes:", ["Listar", "Incluir / Editar"], horizontal=True)
        if opcao == "Listar":
            if df_clientes.empty: st.info("Nenhum cliente cadastrado.")
            else: st.dataframe(df_clientes.style.map(colorir_status, subset=['status']), use_container_width=True)
        else:
            modo = st.checkbox("Editar cliente existente")
            c_target = None
            if modo and not df_clientes.empty:
                sel = st.selectbox("Selecione o cliente para editar/excluir:", [f"{str(r['id'])} - {str(r['nome'])}" for _, r in df_clientes.iterrows()])
                c_target = sel.split("-")[0].strip()
                dados_ant = df_clientes[df_clientes['id'].astype(str) == c_target].iloc[0]
            else: dados_ant = None
            
            nome = st.text_input("Nome Completo:", value=str(dados_ant['nome']) if dados_ant is not None else "", key="c_nome")
            cpf = st.text_input("CPF/CNPJ:", value=str(dados_ant['cpf']) if dados_ant is not None else "", key="c_cpf")
            tel = st.text_input("Telefone:", value=str(dados_ant['tel']) if dados_ant is not None else "", key="c_tel")
            vei = st.text_input("Veículo:", value=str(dados_ant['vei']) if dados_ant is not None else "", key="c_vei")
            pla = st.text_input("Placa:", value=str(dados_ant['pla']) if dados_ant is not None else "", key="c_pla")
            est = st.text_input("Estado (UF) do Veículo (Ex: SP, RN, MG):", value=str(dados_ant['est']).upper() if dados_ant is not None else "RN", key="c_est").strip().upper()
            
            lista_empresas_disponiveis = ["AD RASTREAMENTO VEICULAR"]
            if not df_empresas.empty:
                lista_empresas_disponiveis = [str(e['nome']).upper() for _, e in df_empresas.iterrows()]
                if "AD RASTREAMENTO VEICULAR" not in lista_empresas_disponiveis:
                    lista_empresas_disponiveis.insert(0, "AD RASTREAMENTO VEICULAR")
            
            idx_emp = 0
            if dados_ant is not None:
                emp_ant_upper = str(dados_ant['emp_name']).upper()
                if emp_ant_upper in lista_empresas_disponiveis:
                    idx_emp = lista_empresas_disponiveis.index(emp_ant_upper)
                    
            emp = st.selectbox("Selecione a Empresa Vinculada para este Cliente:", options=lista_empresas_disponiveis, index=idx_emp, key="c_emp")
            status = st.selectbox("Status:", ["Ativo", "Inativo"], index=0 if dados_ant is None else ["Ativo", "Inativo"].index(str(dados_ant['status'])), key="c_status")
            
            if st.button("Salvar Cliente", key="save_cli_btn_novo"):
                if not nome or not pla or not est:
                    st.error("Nome, Placa e Estado (UF) são obrigatórios.")
                else:
                    if not modo:
                        prox = int(df_clientes['id'].astype(float).max() + 1) if not df_clientes.empty else 1
                        novo = pd.DataFrame([{'id': str(prox), 'nome': nome, 'cpf': cpf, 'tel': tel, 'vei': vei, 'pla': pla, 'est': est, 'emp_name': emp.upper(), 'status': status}])
                        df_clientes = pd.concat([df_clientes, novo], ignore_index=True)
                    else:
                        df_clientes.loc[df_clientes['id'].astype(str) == c_target, ['nome','cpf','tel','vei','pla','est','emp_name','status']] = [nome, cpf, tel, vei, pla, est, emp.upper(), status]
                    salvar_dados(df_clientes, FILE_CLIENTES)
                    st.success("✅ Cliente salvo e vinculado com sucesso!")
                    st.rerun()

            if modo and c_target is not None:
                st.write("---")
                if st.button("❌ Excluir Cliente Permanentemente", key="del_cli_btn_novo"):
                    df_clientes = df_clientes[df_clientes['id'].astype(str) != c_target]
                    salvar_dados(df_clientes, FILE_CLIENTES)
                    st.success("🗑️ Cliente excluído com sucesso!")
                    st.rerun()

    # ==================== ABA: EMPRESAS ====================
    with menu[3]:
        st.subheader("Gerenciar Empresas")
        opcao_e = st.radio("Ação Empresas:", ["Listar", "Incluir / Editar"], horizontal=True)
        if opcao_e == "Listar":
            if df_empresas.empty: st.info("Nenhuma empresa cadastrada.")
            else: st.dataframe(df_empresas.style.map(colorir_status, subset=['status']), use_container_width=True)
        else:
            modo_e = st.checkbox("Editar empresa existente")
            e_target = None
            if modo_e and not df_empresas.empty:
                sel_e = st.selectbox("Selecione a empresa para editar/excluir:", [f"{str(r['cnpj'])} - {str(r['nome'])}" for _, r in df_empresas.iterrows()])
                e_target = sel_e.split("-")[0].strip()
                dados_e_ant = df_empresas[df_empresas['cnpj'].astype(str) == e_target].iloc[0]
            else: dados_e_ant = None
            
            cnpj = st.text_input("CNPJ (Senha de acesso):", value=str(dados_e_ant['cnpj']) if dados_e_ant is not None else "", key="e_cnpj")
            n_emp = st.text_input("Nome da Empresa (Usuário):", value=str(dados_e_ant['nome']).upper() if dados_e_ant is not None else "", key="e_nome")
            resp = st.text_input("Responsável:", value=str(dados_e_ant['responsavel']) if dados_e_ant is not None else "", key="e_resp")
            tel_e = st.text_input("Telefone da Central:", value=str(dados_e_ant['telefone']) if dados_e_ant is not None else "", key="e_tel")
            mail = st.text_input("E-mail corporativo:", value=str(dados_e_ant['email']) if dados_e_ant is not None else "", key="e_mail")
            est_e = st.text_input("Estado (UF) Sede da Empresa (Ex: RN, SP):", value=str(dados_e_ant['est']).upper() if dados_e_ant is not None else "RN", key="e_est").strip().upper()
            stat_e = st.selectbox("Status Parceria:", ["Ativo", "Inativo"], index=0 if dados_e_ant is None else ["Ativo", "Inativo"].index(str(dados_e_ant['status'])), key="e_status")
            
            if st.button("Salvar Empresa", key="save_emp_btn_novo_direto"):
                if not cnpj or not n_emp:
                    st.error("CNPJ e Nome da Empresa são obrigatórios.")
                else:
                    if not modo_e:
                        novo_e = pd.DataFrame([{'cnpj': cnpj, 'nome': n_emp.upper(), 'responsavel': resp, 'telefone': tel_e, 'email': mail, 'est': est_e, 'status': stat_e}])
                        df_empresas = pd.concat([df_empresas, novo_e], ignore_index=True)
                    else:
                        df_empresas.loc[df_empresas['cnpj'].astype(str) == e_target, ['nome','responsavel','telefone','email','est','status']] = [n_emp.upper(), resp, tel_e, mail, est_e, stat_e]
                    salvar_dados(df_empresas, FILE_EMPRESAS)
                    st.success("✅ Empresa salva com sucesso!")
                    st.rerun()

            if modo_e and e_target is not None:
                st.write("---")
                if st.button("❌ Excluir Empresa Permanentemente", key="excluir_emp_definitivo"):
                    df_empresas = df_empresas[df_empresas['cnpj'].astype(str) != e_target]
                    salvar_dados(df_empresas, FILE_EMPRESAS)
                    st.success("🗑️ Empresa excluída com sucesso!")
                    st.rerun()

    # ==================== ABA: PRESTADORES ====================
    with menu[4]:
        st.subheader("Gerenciar Prestadores")
        opcao_p = st.radio("Ação Prestadores:", ["Listar", "Incluir / Editar"], horizontal=True)
        if opcao_p == "Listar":
            if df_prestadores.empty: st.info("Nenhum prestador cadastrado.")
            else: st.dataframe(df_prestadores.style.map(colorir_status, subset=['status']), use_container_width=True)
        else:
            modo_p = st.checkbox("Editar prestador existente")
            p_target = None
            if modo_p and not df_prestadores.empty:
                sel_p = st.selectbox("Selecione o prestador para editar/excluir:", [f"{str(r['id'])} - {str(r['nome'])}" for _, r in df_prestadores.iterrows()])
                p_target = sel_p.split("-")[0].strip()
                dados_p_ant = df_prestadores[df_prestadores['id'].astype(str) == p_target].iloc[0]
            else: dados_p_ant = None
            
            n_prest = st.text_input("Nome do Guincho/Prestador:", value=str(dados_p_ant['nome']) if dados_p_ant is not None else "", key="p_nome")
            t_prest = st.text_input("Tipo de Serviço:", value=str(dados_p_ant['tipo']) if dados_p_ant is not None else "Guincho Prancha", key="p_tipo")
            tel_p = st.text_input("Telefone de Contato (Com DDD):", value=str(dados_p_ant['telefone']) if dados_p_ant is not None else "", key="p_tel")
            cid_p = st.text_input("Cidade Base:", value=str(dados_p_ant['cidade']) if dados_p_ant is not None else "", key="p_cid")
            est_p = st.text_input("Estado (UF) de Atuação (Ex: SP, RN, MG):", value=str(dados_p_ant['est']).upper() if dados_p_ant is not None else "RN", key="p_est").strip().upper()
            stat_p = st.selectbox("Status:", ["Ativo", "Inativo"], index=0 if dados_p_ant is None else ["Ativo", "Inativo"].index(str(dados_p_ant['status'])), key="p_status")
            
            if st.button("Salvar Prestador", key="save_prest_btn_novo"):
                if not n_prest or not tel_p or not est_p:
                    st.error("Nome, Telefone e Estado (UF) são obrigatórios.")
                else:
                    if not modo_p:
                        prox_p = int(df_prestadores['id'].astype(float).max() + 1) if not df_prestadores.empty else 1
                        novo_p = pd.DataFrame([{'id': str(prox_p), 'nome': n_prest, 'tipo': t_prest, 'telefone': tel_p, 'cidade': cid_p, 'est': est_p, 'status': stat_p}])
                        df_prestadores = pd.concat([df_prestadores, novo_p], ignore_index=True)
                    else:
                        df_prestadores.loc[df_prestadores['id'].astype(str) == p_target, ['nome','tipo','telefone','cidade','est','status']] = [n_prest, t_prest, tel_p, cid_p, est_p, stat_p]
                    salvar_dados(df_prestadores, FILE_PRESTADORES)
                    st.success("✅ Prestador salvo com sucesso!")
                    st.rerun()

            if modo_p and p_target is not None:
                st.write("---")
                if st.button("❌ Excluir Prestador Permanentemente", key="del_prest_btn_novo"):
                    df_prestadores = df_prestadores[df_prestadores['id'].astype(str) != p_target]
                    salvar_dados(df_prestadores, FILE_PRESTADORES)
                    st.success("🗑️ Prestador excluído com sucesso!")
                    st.rerun()

# --- VISÃO DAS EMPRESAS PARCEIRAS ---
else:
    menu_parceiro = st.tabs(["👥 Nossos Clientes", "📋 Histórico de Chamados"])
    
    with menu_parceiro[0]:
        df_filtrado_p = df_clientes[df_clientes['emp_name'].str.lower() == st.session_state.empresa_vinculada.lower()]
        op_part = st.radio("Ação Parceiro:", ["Visualizar", "Incluir / Alterar Status"], horizontal=True)
        
        if op_part == "Visualizar":
            if df_filtrado_p.empty: st.info("Nenhum cliente cadastrado.")
            else: st.dataframe(df_filtrado_p.style.map(colorir_status, subset=['status']), use_container_width=True)
        else:
            modo_part = st.checkbox("Alterar status de cliente existente")
            part_target = None
            if modo_part and not df_filtrado_p.empty:
                sel_part = st.selectbox("Selecione o seu cliente para editar/excluir:", [f"{str(r['id'])} - {str(r['nome'])}" for _, r in df_filtrado_p.iterrows()])
                part_target = sel_part.split("-")[0].strip()
                dados_part_ant = df_filtrado_p[df_filtrado_p['id'].astype(str) == part_target].iloc[0]
            else: dados_part_ant = None
            
            p_nome = st.text_input("Nome Completo:", value=str(dados_part_ant['nome']) if dados_part_ant is not None else "", key="part_nome")
            p_cpf = st.text_input("CPF:", value=str(dados_part_ant['cpf']) if dados_part_ant is not None else "", key="part_cpf")
            p_tel = st.text_input("Telefone:", value=str(dados_part_ant['tel']) if dados_part_ant is not None else "", key="part_tel")
            p_vei = st.text_input("Veículo:", value=str(dados_ant['vei']) if dados_part_ant is not None else "", key="part_vei")
            p_pla = st.text_input("Placa:", value=str(dados_part_ant['pla']) if dados_part_ant is not None else "", key="part_pla")
            p_est = st.text_input("UF:", value=str(dados_part_ant['est']) if dados_part_ant is not None else "RN", key="part_est")
            p_stat = st.selectbox("Status do Serviço:", ["Ativo", "Inativo"], index=0 if dados_part_ant is None else ["Ativo", "Inativo"].index(str(dados_part_ant['status'])), key="part_status")
            
            if st.button("Confirmar Registro", key="save_part_btn_novo"):
                if not p_nome or not p_pla:
                    st.error("Nome e Placa são obrigatórios.")
                else:
                    if not modo_part:
                        prox_id = int(df_clientes['id'].astype(float).max() + 1) if not df_clientes.empty else 1
                        novo_reg = pd.DataFrame([{'id': str(prox_id), 'nome': p_nome, 'cpf': p_cpf, 'tel': p_tel, 'vei': p_vei, 'pla': p_pla, 'est': p_est, 'emp_name': st.session_state.empresa_vinculada.upper(), 'status': p_stat}])
                        df_clientes = pd.concat([df_clientes, novo_reg], ignore_index=True)
                    else:
                        df_clientes.loc[df_clientes['id'].astype(str) == part_target, ['nome','cpf','tel','vei','pla','est','status']] = [p_nome, p_cpf, p_tel, p_vei, p_pla, p_est, p_stat]
                    salvar_dados(df_clientes, FILE_CLIENTES)
                    st.success("✅ Atualizado com sucesso!")
                    st.rerun()

            if modo_part and part_target is not None:
                st.write("---")
                if st.button("❌ Excluir Cliente Permanentemente", key="del_part_btn_novo"):
                    df_clientes = df_clientes[df_clientes['id'].astype(str) != part_target]
                    salvar_dados(df_clientes, FILE_CLIENTES)
                    st.success("🗑️ Cliente excluído com sucesso!")
                    st.rerun()

    with menu_parceiro[1]:
        df_os_parceiro = df_os[df_os['empresa'].str.lower() == st.session_state.empresa_vinculada.lower()]
        if df_os_parceiro.empty: st.info("Nenhum acionamento registrado.")
        else: st.dataframe(df_os_parceiro, use_container_width=True)
