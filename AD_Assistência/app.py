import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse

# Configuração da Página
st.set_page_config(page_title="Central 24h - AD Rastreamento", layout="wide", page_icon="🔒")

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
    pd.DataFrame(columns=['cnpj','nome','responsavel','telefone','email','status']).to_csv(FILE_EMPRESAS, index=False)
if not os.path.exists(FILE_PRESTADORES):
    pd.DataFrame(columns=['id','nome','tipo','telefone','cidade','status']).to_csv(FILE_PRESTADORES, index=False)
if not os.path.exists(FILE_OS):
    pd.DataFrame(columns=['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','prestador','localizacao','destino','obs']).to_csv(FILE_OS, index=False)

# Funções de Leitura e Escrita
def carregar_dados(caminho):
    try:
        df = pd.read_csv(caminho)
        df.columns = df.columns.str.strip().str.lower()
        return df
    except:
        return pd.DataFrame()

def salvar_dados(df, caminho):
    df.to_csv(caminho, index=False)

# Controle de Sessão / Login
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.user = ""
    st.session_state.perfil = ""
    st.session_state.empresa_vinculada = ""

# Tela de Login
if not st.session_state.logado:
    st.markdown("<h1 style='text-align: center; color: #7B2CBF;'>AD Rastreamento Veicular</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #E53935;'>Central de Assistência 24h</h3>", unsafe_allow_html=True)
    
    with st.container():
        st.write("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.subheader("🔒 Área Restrita - Login")
            usuario_input = st.text_input("Usuário (Nome da Empresa):").strip().lower()
            senha_input = st.text_input("Senha (CNPJ):", type="password").strip()
            
            if st.button("Entrar no Sistema", use_container_width=True):
                # 1. Verificar Admin Mestre
                if usuario_input == "adrastreamentoveicular" and senha_input == "00000000000000":
                    st.session_state.logado = True
                    st.session_state.user = "AD Rastreamento (Admin)"
                    st.session_state.perfil = "Admin"
                    st.rerun()
                else:
                    # 2. Verificar se é uma Empresa Parceira cadastrada
                    df_emp = carregar_dados(FILE_EMPRESAS)
                    if not df_emp.empty:
                        # Compara limpando espaços para evitar erros de digitação
                        parceiro_valid = df_emp[(df_emp['cnpj'].astype(str) == senha_input) & (df_emp['nome'].str.lower().str.replace(" ", "") == usuario_input.replace(" ", ""))]
                        if not parceiro_valid.empty:
                            st.session_state.logado = True
                            st.session_state.user = parceiro_valid.iloc[0]['nome']
                            st.session_state.perfil = "Parceiro"
                            st.session_state.empresa_vinculada = parceiro_valid.iloc[0]['nome']
                            st.rerun()
                        else:
                            st.error("❌ Usuário ou senha incorretos. Tente novamente.")
                    else:
                        st.error("❌ Usuário ou senha incorretos. Tente novamente.")
    st.stop()

# --- SISTEMA LOGADO ---
st.sidebar.title("📌 Menu de Navegação")
st.sidebar.write(f"Conectado como:\n**{st.session_state.user}**")

if st.sidebar.button("Logout / Sair"):
    st.session_state.logado = False
    st.rerun()

# Definição de permissões de Abas baseadas no Perfil
if st.session_state.perfil == "Admin":
    abas = ["Nova OS", "Relatórios", "Clientes", "Empresas", "Prestadores"]
else:
    # Perfil Parceiro: Só gerencia os próprios clientes e vê histórico operacional deles
    abas = ["Clientes (Parceiro)", "Histórico de OS"]

aba_selecionada = st.sidebar.radio("Ir para:", abas)

# Carregamento Geral dos DataFrames
df_clientes = carregar_dados(FILE_CLIENTES)
df_empresas = carregar_dados(FILE_EMPRESAS)
df_prestadores = carregar_dados(FILE_PRESTADORES)
df_os = carregar_dados(FILE_OS)

# Função para colorir status nas tabelas
def colorir_status(val):
    color = '#C8E6C9' if val == 'Ativo' else '#FFCDD2'
    return f'background-color: {color}'

# ==================== ABA: NOVA OS (Apenas Admin) ====================
if aba_selecionada == "Nova OS":
    st.header("🛠️ Abertura de Chamado - Nova Ordem de Serviço")
    
    if df_clientes.empty:
        st.warning("Cadastre clientes antes de abrir uma Ordem de Serviço.")
    else:
        lista_clientes_ops = [f"ID: {row['id']} | {row['nome']} - {row['pla'] if 'pla' in row else ''}" for _, row in df_clientes.iterrows()]
        cliente_sel_str = st.selectbox("Selecione o Cliente Alvo:", lista_clientes_ops)
        c_id = int(cliente_sel_str.split("|")[0].replace("ID:", "").strip())
        cliente_dados = df_clientes[df_clientes['id'] == c_id].iloc[0]
        
        # --- CONTROLE DE ACIONAMENTOS NO ANO ALINHADO ---
        ano_atual = datetime.now().year
        total_guinchos = 0
        total_pane_seca = 0
        total_pane_eletrica = 0
        total_borraceiro = 0
        total_chaveiro = 0
        
        if not df_os.empty and 'cliente_id' in df_os.columns:
            df_os['data_hora'] = pd.to_datetime(df_os['data_hora'], errors='coerce')
            os_cliente_ano = df_os[(df_os['cliente_id'] == c_id) & (df_os['data_hora'].dt.year == ano_atual)]
            
            for _, o in os_cliente_ano.iterrows():
                serv = str(o['tipo_servico']).lower()
                if "prancha" in serv or "guincho" in serv:
                    total_guinchos += 1
                elif "seca" in serv:
                    total_pane_seca += 1
                elif "elétrica" in serv or "eletrica" in serv:
                    total_pane_eletrica += 1
                elif "chaveiro" in serv:
                    total_chaveiro += 1
                elif "borraceiro" in serv:
                    total_borraceiro += 1
        
        st.markdown(f"### 📊 Histórico de Utilização do Cliente em {ano_atual}:")
        col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns(5)
        
        with col_c1:
            st.metric("Guinchos (Máx: 2)", f"{total_guinchos} / 2")
            if total_guinchos >= 2: st.error("⚠️ Limite Atingido!")
        with col_c2:
            st.metric("Pane Seca (Máx: 1)", f"{total_pane_seca} / 1")
            if total_pane_seca >= 1: st.error("⚠️ Limite Atingido!")
        with col_c3:
            st.metric("Pane Elétrica (Máx: 1)", f"{total_pane_eletrica} / 1")
            if total_pane_eletrica >= 1: st.error("⚠️ Limite Atingido!")
        with col_c4:
            st.metric("Chaveiro (Máx: 1)", f"{total_chaveiro} / 1")
            if total_chaveiro >= 1: st.error("⚠️ Limite Atingido!")
        with col_c5:
            st.metric("Borraceiro (Máx: 1)", f"{total_borraceiro} / 1")
            if total_borraceiro >= 1: st.error("⚠️ Limite Atingido!")
            
        st.write("---")
        
        col_os1, col_os2 = st.columns(2)
        with col_os1:
            tipo_servico = st.selectbox("Tipo de Serviço Solicitado:", ["Guincho - Prancha Seca", "Pane Seca", "Pane Elétrica", "Chaveiro", "Borraceiro"])
            
            lista_p_ops = ["Outro (Digitar Manualmente)"]
            if not df_prestadores.empty:
                lista_p_ops += [f"{r['nome']} ({r['tipo']}) - {r['telefone']}" for _, r in df_prestadores.iterrows()]
            
            prestador_sel = st.selectbox("Prestador de Serviço:", lista_p_ops)
            prestador_final = st.text_input("Digite o Prestador/Telefone Manual:") if prestador_sel == "Outro (Digitar Manualmente)" else prestador_sel
                
        with col_os2:
            localizacao = st.text_input("Localização Atual do Veículo (Origem):")
            destino = st.text_input("Destino do Guincho/Atendimento:")
            obs = st.text_area("Observações / Motivo do Acionamento:")
            
        if st.button("Gravar Ordem de Serviço e Gerar Link do WhatsApp", type="primary"):
            if not prestador_final:
                st.error("Por favor, identifique o prestador de serviço.")
            else:
                nova_id = int(df_os['id'].max() + 1) if not df_os.empty else 1
                agora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                nova_os = pd.DataFrame([{
                    'id': nova_id, 'data_hora': agora_str, 'cliente_id': c_id,
                    'cliente_nome': cliente_dados['nome'], 'empresa': cliente_dados['emp_name'],
                    'tipo_servico': tipo_servico, 'prestador': prestador_final,
                    'localizacao': localizacao, 'destino': destino, 'obs': obs
                }])
                
                df_os = pd.concat([df_os, nova_os], ignore_index=True)
                salvar_dados(df_os, FILE_OS)
                st.success(f"✅ Ordem de Serviço nº {nova_id} gravada com sucesso com data e hora salvas!")
                
                # Texto Formatado para WhatsApp (Identidade da Empresa Parceira vinculada)
                texto_whatsapp = (
                    f"*{str(cliente_dados['emp_name']).upper()} - ASSISTÊNCIA 24H*\n"
                    f"-----------------------------------------\n"
                    f"*Chamado Nº:* {nova_id}\n"
                    f"*Data/Hora:* {agora_str}\n"
                    f"*Serviço solicitado:* {tipo_servico}\n\n"
                    f"*Dados do Cliente:*\n"
                    f"- Nome: {cliente_dados['nome']}\n"
                    f"- Telefone: {cliente_dados['tel']}\n\n"
                    f"*Dados do Veículo:*\n"
                    f"- Modelo: {cliente_dados['vei']}\n"
                    f"- Placa: {cliente_dados['pla']}\n\n"
                    f"*Locais:*\n"
                    f"- Origem: {localizacao}\n"
                    f"- Destino: {destino}\n\n"
                    f"*Observações:* {obs}"
                )
                
                texto_codificado = urllib.parse.quote(texto_whatsapp)
                link_whatsapp = f"https://api.whatsapp.com/send?text={texto_codificado}"
                
                st.markdown(f'### 📱 Enviar Ordem de Serviço:')
                st.markdown(f'<a href="{link_whatsapp}" target="_blank"><button style="background-color: #25D366; color: white; padding: 12px 24px; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; font-weight: bold;">➡️ Enviar via WhatsApp</button></a>', unsafe_allow_html=True)

# ==================== ABA: RELATÓRIOS (Apenas Admin) ====================
elif aba_selecionada == "Relatórios":
    st.header("📊 Painel de Controle de Chamados Gerados")
    if df_os.empty:
        st.info("Nenhum chamado registrado no banco.")
    else:
        st.subheader("📋 Histórico Geral de Atendimentos")
        st.dataframe(df_os, use_container_width=True)
        st.write("---")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.markdown("##### Tipos de Acionamentos Executados")
            if 'tipo_servico' in df_os.columns: st.bar_chart(df_os['tipo_servico'].value_counts())
        with col_r2:
            st.markdown("##### Demandas por Empresa Parceira")
            if 'empresa' in df_os.columns: st.bar_chart(df_os['empresa'].value_counts())

# ==================== ABA: CLIENTES (Mestre Admin) ====================
elif aba_selecionada == "Clientes":
    st.header("👥 Gestão Geral de Clientes")
    tab1, tab2 = st.tabs(["Lista de Clientes", "Incluir / Editar Registro"])
    
    with tab1:
        if df_clientes.empty: st.info("Nenhum cliente na base.")
        else: st.dataframe(df_clientes.style.map(colorir_status, subset=['status']), use_container_width=True)
            
    with tab2:
        opcao_modo = st.radio("Ação:", ["Novo Cliente", "Editar Cliente"], horizontal=True)
        dados_antigos = None
        cliente_id_target = None
        
        if opcao_modo == "Editar Cliente" and not df_clientes.empty:
            lista_c_edit = [f"{r['id']} - {r['nome']}" for _, r in df_clientes.iterrows()]
            selecionado_edit = st.selectbox("Escolha o cliente:", lista_c_edit)
            cliente_id_target = int(selecionado_edit.split("-")[0].strip())
            dados_antigos = df_clientes[df_clientes['id'] == cliente_id_target].iloc[0]
            
        with st.form("form_cliente"):
            c_nome = st.text_input("Nome Completo:", value=str(dados_antigos['nome']) if dados_antigos is not None else "")
            c_cpf = st.text_input("CPF / CNPJ:", value=str(dados_antigos['cpf']) if dados_antigos is not None else "")
            c_tel = st.text_input("Telefone:", value=str(dados_antigos['tel']) if dados_antigos is not None else "")
            c_vei = st.text_input("Veículo:", value=str(dados_antigos['vei']) if dados_antigos is not None else "")
            c_pla = st.text_input("Placa:", value=str(dados_antigos['pla']) if dados_antigos is not None else "")
            c_est = st.text_input("UF:", value=str(dados_antigos['est']) if dados_antigos is not None else "RN")
            
            lista_emp_nomes = ["AD Rastreamento Veicular"]
            if not df_empresas.empty: lista_emp_nomes += df_empresas['nome'].tolist()
            c_emp = st.selectbox("Empresa Vinculada:", lista_emp_nomes, index=lista_emp_nomes.index(dados_antigos['emp_name']) if dados_antigos is not None and dados_antigos['emp_name'] in lista_emp_nomes else 0)
            c_status = st.selectbox("Status:", ["Ativo", "Inativo"], index=0 if dados_antigos is None else ["Ativo", "Inativo"].index(dados_antigos['status']))
            
            if st.form_submit_button("Salvar Alterações"):
                if not c_nome or not c_pla: st.error("Nome e Placa são obrigatórios.")
                else:
                    if opcao_modo == "Novo Cliente":
                        prox_id = int(df_clientes['id'].max() + 1) if not df_clientes.empty else 1
                        novo_reg = pd.DataFrame([{'id': prox_id, 'nome': c_nome, 'cpf': c_cpf, 'tel': c_tel, 'vei': c_vei, 'pla': c_pla, 'est': c_est, 'emp_name': c_emp, 'status': c_status}])
                        df_clientes = pd.concat([df_clientes, novo_reg], ignore_index=True)
                    else:
                        df_clientes.loc[df_clientes['id'] == cliente_id_target, ['nome', 'cpf', 'tel', 'vei', 'pla', 'est', 'emp_name', 'status']] = [c_nome, c_cpf, c_tel, c_vei, c_pla, c_est, c_emp, c_status]
                    salvar_dados(df_clientes, FILE_CLIENTES)
                    st.success("Base de clientes atualizada!")
                    st.rerun()

# ==================== ABA: EMPRESAS ====================
elif aba_selecionada == "Empresas":
    st.header("🏢 Gerenciamento de Empresas Parceiras")
    tab_e1, tab_e2 = st.tabs(["Listar Empresas", "Incluir / Editar Empresa"])
    
    with tab_e1:
        if df_empresas.empty: st.info("Nenhuma empresa cadastrada.")
        else: st.dataframe(df_empresas.style.map(colorir_status, subset=['status']), use_container_width=True)
            
    with tab_e2:
        opcao_modo_e = st.radio("Ação:", ["Nova Empresa", "Editar Empresa Existente"], horizontal=True, key="m_emp")
        emp_cnpj_target = None
        dados_emp_antigos = None
        
        if opcao_modo_e == "Editar Empresa Existente" and not df_empresas.empty:
            lista_e_edit = [f"{r['cnpj']} - {r['nome']}" for _, r in df_empresas.iterrows()]
            selecionado_e_edit = st.selectbox("Escolha a empresa:", lista_e_edit)
            emp_cnpj_target = selecionado_e_edit.split("-")[0].strip()
            dados_emp_antigos = df_empresas[df_empresas['cnpj'].astype(str) == emp_cnpj_target].iloc[0]
            
        with st.form("form_empresa"):
            e_cnpj = st.text_input("CNPJ (Apenas números - Será a Senha de Acesso):", value=str(dados_emp_antigos['cnpj']) if dados_emp_antigos is not None else "")
            e_nome = st.text_input("Nome da Empresa (Será o Nome de Usuário):", value=str(dados_emp_antigos['nome']) if dados_emp_antigos is not None else "")
            e_resp = st.text_input("Responsável Técnico:", value=str(dados_emp_antigos['responsavel']) if dados_emp_antigos is not None else "")
            e_tel = st.text_input("Telefone da Empresa:", value=str(dados_emp_antigos['telefone']) if dados_emp_antigos is not None else "")
            e_email = st.text_input("E-mail corporativo:", value=str(dados_emp_antigos['email']) if dados_emp_antigos is not None else "")
            e_status = st.selectbox("Status da Parceria:", ["Ativo", "Inativo"], index=0 if dados_emp_antigos is None else ["Ativo", "Inativo"].index(dados_emp_antigos['status']))
            
            if st.form_submit_button("Salvar Empresa"):
                if not e_cnpj or not e_nome: st.error("CNPJ e Nome são obrigatórios.")
                else:
                    if opcao_modo_e == "Nova Empresa":
                        novo_reg_e = pd.DataFrame([{'cnpj': e_cnpj, 'nome': e_nome.lower(), 'responsavel': e_resp, 'telefone': e_tel, 'email': e_email, 'status': e_status}])
                        df_empresas = pd.concat([df_empresas, novo_reg_e], ignore_index=True)
                    else:
                        df_empresas.loc[df_empresas['cnpj'].astype(str) == emp_cnpj_target, ['nome', 'responsavel', 'telefone', 'email', 'status']] = [e_nome.lower(), e_resp, e_tel, e_email, e_status]
                    salvar_dados(df_empresas, FILE_EMPRESAS)
                    st.success("Dados de empresas salvos!")
                    st.rerun()

# ==================== ABA: PRESTADORES ====================
elif aba_selecionada == "Prestadores":
    st.header("🛞 Rede de Prestadores de Serviço")
    tab_p1, tab_p2 = st.tabs(["Listar Prestadores", "Incluir / Editar Prestador"])
    
    with tab_p1:
        if df_prestadores.empty: st.info("Nenhum prestador na rede.")
        else: st.dataframe(df_prestadores.style.map(colorir_status, subset=['status']), use_container_width=True)
            
    with tab_p2:
        opcao_modo_p = st.radio("Ação:", ["Novo Prestador", "Editar Prestador"], horizontal=True, key="m_prest")
        prest_id_target = None
        dados_p_antigos = None
        
        if opcao_modo_p == "Editar Prestador" and not df_prestadores.empty:
            lista_p_edit = [f"{r['id']} - {r['nome']}" for _, r in df_prestadores.iterrows()]
            selecionado_p_edit = st.selectbox("Escolha o prestador:", lista_p_edit)
            prest_id_target = int(selecionado_p_edit.split("-")[0].strip())
            dados_p_antigos = df_prestadores[df_prestadores['id'] == prest_id_target].iloc[0]
            
        with st.form("form_prestador"):
            p_nome = st.text_input("Nome do Prestador / Guincho:", value=str(dados_p_antigos['nome']) if dados_p_antigos is not None else "")
            p_tipo = st.selectbox("Especialidade:", ["Guincho Prancha", "Chaveiro 24h", "Borracheiro / Auto Socorro"], index=0 if dados_p_antigos is None else ["Guincho Prancha", "Chaveiro 24h", "Borracheiro / Auto Socorro"].index(dados_p_antigos['tipo']) if dados_p_antigos['tipo'] in ["Guincho Prancha", "Chaveiro 24h", "Borracheiro / Auto Socorro"] else 0)
            p_tel = st.text_input("Telefone de Contato:", value=str(dados_p_antigos['telefone']) if dados_p_antigos is not None else "")
            p_cid = st.text_input("Cidade Base:", value=str(dados_p_antigos['cidade']) if dados_p_antigos is not None else "")
            p_status = st.selectbox("Status:", ["Ativo", "Inativo"], index=0 if dados_p_antigos is None else ["Ativo", "Inativo"].index(dados_p_antigos['status']))
            
            if st.form_submit_button("Salvar Prestador"):
                if not p_nome or not p_tel: st.error("Nome e Telefone são obrigatórios.")
                else:
                    if opcao_modo_p == "Novo Prestador":
                        prox_p_id = int(df_prestadores['id'].max() + 1) if not df_prestadores.empty else 1
                        novo_reg_p = pd.DataFrame([{'id': prox_p_id, 'nome': p_nome, 'tipo': p_tipo, 'telefone': p_tel, 'cidade': p_cid, 'status': p_status}])
                        df_prestadores = pd.concat([df_prestadores, novo_reg_p], ignore_index=True)
                    else:
                        df_prestadores.loc[df_prestadores['id'] == prest_id_target, ['nome', 'tipo', 'telefone', 'cidade', 'status']] = [p_nome, p_tipo, p_tel, p_cid, p_status]
                    salvar_dados(df_prestadores, FILE_PRESTADORES)
                    st.success("Base de Prestadores atualizada!")
                    st.rerun()

# ==================== ÁREA LIMITADA DA EMPRESA PARCEIRA ====================
elif aba_selecionada == "Clientes (Parceiro)":
    st.header(f"🏢 Painel de Clientes Vinculados - {st.session_state.empresa_vinculada.upper()}")
    
    # Filtra apenas os clientes que pertencem a essa empresa logada
    df_filtrado_p = df_clientes[df_clientes['emp_name'].str.lower() == st.session_state.empresa_vinculada.lower()]
    
    t_p1, t_p2 = st.tabs(["Nossos Clientes Cadastrados", "Cadastrar / Alterar Status"])
    with t_p1:
        if df_filtrado_p.empty: st.info("Sua empresa não possui clientes cadastrados ainda.")
        else: st.dataframe(df_filtrado_p.style.map(colorir_status, subset=['status']), use_container_width=True)
            
    with t_p2:
        opcao_p = st.radio("Selecione:", ["Cadastrar Novo Cliente", "Modificar Status de Cliente Existente"], horizontal=True)
        dados_p_ant = None
        id_p_target = None
        
        if opcao_p == "Modificar Status de Cliente Existente" and not df_filtrado_p.empty:
            lista_p_c = [f"{r['id']} - {r['nome']}" for _, r in df_filtrado_p.iterrows()]
            sel_p_c = st.selectbox("Escolha o cliente:", lista_p_c)
            id_p_target = int(sel_p_c.split("-")[0].strip())
            dados_p_ant = df_filtrado_p[df_filtrado_p['id'] == id_p_target].iloc[0]
            
        with st.form("form_parceiro_cliente"):
            cp_nome = st.text_input("Nome Completo:", value=str(dados_p_ant['nome']) if dados_p_ant is not None else "")
            cp_cpf = st.text_input("CPF / CNPJ:", value=str(dados_p_ant['cpf']) if dados_p_ant is not None else "")
            cp_tel = st.text_input("Telefone:", value=str(dados_p_ant['tel']) if dados_p_ant is not None else "")
            cp_vei = st.text_input("Veículo:", value=str(dados_p_ant['vei']) if dados_p_ant is not None else "")
            cp_pla = st.text_input("Placa:", value=str(dados_p_ant['pla']) if dados_p_ant is not None else "")
            cp_est = st.text_input("UF:", value=str(dados_p_ant['est']) if dados_p_ant is not None else "RN")
            cp_status = st.selectbox("Status do Serviço:", ["Ativo", "Inativo"], index=0 if dados_p_ant is None else ["Ativo", "Inativo"].index(dados_p_ant['status']))
            
            if st.form_submit_button("Confirmar Atualização"):
                if not cp_nome or not cp_pla: st.error("Nome e Placa são obrigatórios.")
                else:
                    if opcao_p == "Cadastrar Novo Cliente":
                        prox_id = int(df_clientes['id'].max() + 1) if not df_clientes.empty else 1
                        novo_reg = pd.DataFrame([{'id': prox_id, 'nome': cp_nome, 'cpf': cp_cpf, 'tel': cp_tel, 'vei': cp_vei, 'pla': cp_pla, 'est': cp_est, 'emp_name': st.session_state.empresa_vinculada, 'status': cp_status}])
                        df_clientes = pd.concat([df_clientes, novo_reg], ignore_index=True)
                    else:
                        df_clientes.loc[df_clientes['id'] == id_p_target, ['nome', 'cpf', 'tel', 'vei', 'pla', 'est', 'status']] = [cp_nome, cp_cpf, cp_tel, cp_vei, cp_pla, cp_est, cp_status]
                    salvar_dados(df_clientes, FILE_CLIENTES)
                    st.success("Alterações salvas com sucesso!")
                    st.rerun()

elif aba_selecionada == "Histórico de OS":
    st.header(f"📋 Histórico Operacional - {st.session_state.empresa_vinculada.upper()}")
    if df_os.empty:
        st.info("Nenhum acionamento registrado para a sua empresa.")
    else:
        df_os_filtrada_p = df_os[df_os['empresa'].str.lower() == st.session_state.empresa_vinculada.lower()]
        if df_os_filtrada_p.empty:
            st.info("Nenhum acionamento registrado para os seus clientes até o momento.")
        else:
            st.dataframe(df_os_filtrada_p, use_container_width=True)
