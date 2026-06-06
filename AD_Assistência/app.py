import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse

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

# Cabeçalho Fixo do Aplicativo
st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">⚡ Operação Atendimento – AD Rastreamento Veicular</div>', unsafe_allow_html=True)

# Tela de Login (Caso não esteja logado)
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
                df_emp = carregar_dados(FILE_EMPRESAS)
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

# Mostrar Usuário Logado e Botão de Sair no topo direito
col_user, col_logout = st.columns([5, 1])
with col_user:
    st.write(f"**Central AD 24h | Empresa:** `{st.session_state.user}`")
with col_logout:
    if st.button("Sair / Logoff"):
        st.session_state.logado = False
        st.rerun()

# Carregamento dos Bancos
df_clientes = carregar_dados(FILE_CLIENTES)
df_empresas = carregar_dados(FILE_EMPRESAS)
df_prestadores = carregar_dados(FILE_PRESTADORES)
df_os = carregar_dados(FILE_OS)

def colorir_status(val):
    return 'color: green; font-weight: bold;' if val == 'Ativo' else 'color: red; font-weight: bold;'

# --- NAVEGAÇÃO POR ABAS TRADICIONAIS ---
if st.session_state.perfil == "Admin":
    menu = st.tabs(["📋 Nova OS", "📊 Relatórios & Baixa PDF", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores"])
    
    # ==================== ABA: NOVA OS ====================
    with menu[0]:
        if df_clientes.empty:
            st.warning("Nenhum cliente cadastrado no sistema.")
        else:
            lista_ed_ops = [f"ID: {c['id']} | {c['nome']}" for _, c in df_clientes.iterrows()]
            c_ed_str = st.selectbox("Selecione o cliente alvo:", options=lista_ed_ops, key="sel_ed")
            c_id = int(c_ed_str.split("|")[0].replace("ID:", "").strip())
            cliente_dados = df_clientes[df_clientes['id'] == c_id].iloc[0]
            
            # --- CONTADOR DE ACIONAMENTOS NO ANO ---
            ano_atual = datetime.now().year
            total_guinchos, total_p_seca, total_p_eletrica, total_borraceiro, total_chaveiro = 0, 0, 0, 0, 0
            
            if not df_os.empty and 'cliente_id' in df_os.columns:
                df_os['data_hora'] = pd.to_datetime(df_os['data_hora'], errors='coerce')
                os_cliente_ano = df_os[(df_os['cliente_id'] == c_id) & (df_os['data_hora'].dt.year == ano_atual)]
                for _, o in os_cliente_ano.iterrows():
                    serv = str(o['tipo_servico']).lower()
                    if "prancha" in serv: total_guinchos += 1
                    elif "pane seca" in serv: total_p_seca += 1
                    elif "pane elétrica" in serv or "eletrica" in serv: total_p_eletrica += 1
                    elif "chaveiro" in serv: total_chaveiro += 1
                    elif "borraceiro" in serv: total_borraceiro += 1
            
            # Alertas Visuais de Saldo
            st.markdown(f"#### 📊 Saldo de Acionamentos no Ano ({ano_atual})")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Guinchos Utilizados", f"{total_guinchos} / 2")
            c2.metric("Pane Seca Utilizada", f"{total_p_seca} / 1")
            c3.metric("Pane Elétrica Utilizada", f"{total_p_eletrica} / 1")
            c4.metric("Chaveiro Utilizado", f"{total_chaveiro} / 1")
            c5.metric("Borraceiro Utilizado", f"{total_borraceiro} / 1")
            
            st.write("---")
            
            tipo_servico = st.selectbox("Tipo de Serviço:", ["Guincho - Prancha Seca", "Pane Seca", "Pane Elétrica", "Chaveiro", "Borraceiro"])
            
            lista_p_ops = ["Outro (Digitar Manualmente)"]
            if not df_prestadores.empty:
                lista_p_ops += [f"{r['nome']} - {r['telefone']}" for _, r in df_prestadores.iterrows()]
            prestador_sel = st.selectbox("Prestador homologado para o Estado:", lista_p_ops)
            prestador_final = st.text_input("Digite o prestador manual:") if prestador_sel == "Outro (Digitar Manualmente)" else prestador_sel
            
            localizacao = st.text_input("Endereço de Origem (Localização atual):")
            destino = st.text_input("Endereço de Destino:")
            obs = st.text_area("Observações:")
            
            if st.button("🚀 Iniciar Atendimento / Gerar OS"):
                if not prestador_final:
                    st.error("Identifique o prestador.")
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
                    st.success("✅ Ordem de Serviço gravada com sucesso!")
                    
                    # Formato Original de Mensagem para WhatsApp
                    texto_whatsapp = (
                        f"*{str(cliente_dados['emp_name']).upper()} - ASSISTÊNCIA 24H*\n"
                        f"-----------------------------------------\n"
                        f"*Chamado Nº:* {nova_id}\n"
                        f"*Data/Hora:* {agora_str}\n"
                        f"*Serviço:* {tipo_servico}\n\n"
                        f"*Cliente:* {cliente_dados['nome']}\n"
                        f"*Telefone:* {cliente_dados['tel']}\n\n"
                        f"*Veículo:* {cliente_dados['vei']} - Placa: {cliente_dados['pla']}\n\n"
                        f"*Origem:* {localizacao}\n"
                        f"*Destino:* {destino}\n\n"
                        f"*Obs:* {obs}"
                    )
                    link_w = f"https://api.whatsapp.com/send?text={urllib.parse.quote(texto_whatsapp)}"
                    st.markdown(f'<a href="{link_w}" target="_blank"><button style="background-color: #25D366; color: white; padding: 10px 20px; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">➡️ Enviar para o WhatsApp do Prestador</button></a>', unsafe_allow_html=True)

    # ==================== ABA: RELATÓRIOS ====================
    with menu[1]:
        st.subheader("📋 Relatórios Gerais")
        if df_os.empty: st.info("Nenhuma OS aberta.")
        else: st.dataframe(df_os, use_container_width=True)

    # ==================== ABA: CLIENTES ====================
    with menu[2]:
        st.subheader("Modificar Cadastro")
        opcao = st.radio("Ação Clientes:", ["Listar", "Incluir / Editar"], horizontal=True)
        if opcao == "Listar":
            st.dataframe(df_clientes.style.map(colorir_status, subset=['status']), use_container_width=True)
        else:
            modo = st.checkbox("Editar cliente existente")
            c_target = None
            if modo and not df_clientes.empty:
                sel = st.selectbox("Selecione o cliente para editar/excluir:", [f"{r['id']} - {r['nome']}" for _, r in df_clientes.iterrows()])
                c_target = int(sel.split("-")[0].strip())
                dados_ant = df_clientes[df_clientes['id'] == c_target].iloc[0]
            else: dados_ant = None
            
            with st.form("f_cli", clear_on_submit=True):
                nome = st.text_input("Nome:", value=str(dados_ant['nome']) if dados_ant is not None else "")
                cpf = st.text_input("CPF:", value=str(dados_ant['cpf']) if dados_ant is not None else "")
                tel = st.text_input("Telefone:", value=str(dados_ant['tel']) if dados_ant is not None else "")
                vei = st.text_input("Veículo:", value=str(dados_ant['vei']) if dados_ant is not None else "")
                pla = st.text_input("Placa:", value=str(dados_ant['pla']) if dados_ant is not None else "")
                est = st.text_input("Estado:", value=str(dados_ant['est']) if dados_ant is not None else "RN")
                emp = st.text_input("Empresa:", value=str(dados_ant['emp_name']) if dados_ant is not None else "AD Rastreamento Veicular")
                status = st.selectbox("Status:", ["Ativo", "Inativo"], index=0 if dados_ant is None else ["Ativo", "Inativo"].index(dados_ant['status']))
                
                if st.form_submit_button("Salvar Cliente"):
                    if not nome or not pla:
                        st.error("Nome e Placa são obrigatórios.")
                    else:
                        if not modo:
                            prox = int(df_clientes['id'].max() + 1) if not df_clientes.empty else 1
                            novo = pd.DataFrame([{'id': prox, 'nome': nome, 'cpf': cpf, 'tel': tel, 'vei': vei, 'pla': pla, 'est': est, 'emp_name': emp, 'status': status}])
                            df_clientes = pd.concat([df_clientes, novo], ignore_index=True)
                        else:
                            df_clientes.loc[df_clientes['id'] == c_target, ['nome','cpf','tel','vei','pla','est','emp_name','status']] = [nome, cpf, tel, vei, pla, est, emp, status]
                        salvar_dados(df_clientes, FILE_CLIENTES)
                        st.success("✅ Cliente salvo com sucesso!")
                        st.rerun()

            # Opção de Excluir Registro (Apenas se estiver no modo de edição)
            if modo and c_target is not None:
                st.write("---")
                st.markdown("⚠️ **Zona de Perigo**")
                if st.button("❌ Excluir este Cliente Permanentemente", key="del_cli_btn"):
                    df_clientes = df_clientes[df_clientes['id'] != c_target]
                    salvar_dados(df_clientes, FILE_CLIENTES)
                    st.success("🗑️ Cliente excluído com sucesso!")
                    st.rerun()

    # ==================== ABA: EMPRESAS ====================
    with menu[3]:
        st.subheader("Gerenciar Empresas")
        opcao_e = st.radio("Ação Empresas:", ["Listar", "Incluir / Editar"], horizontal=True)
        if opcao_e == "Listar":
            st.dataframe(df_empresas.style.map(colorir_status, subset=['status']), use_container_width=True)
        else:
            modo_e = st.checkbox("Editar empresa existente")
            e_target = None
            if modo_e and not df_empresas.empty:
                sel_e = st.selectbox("Selecione a empresa para editar/excluir:", [f"{r['cnpj']} - {r['nome']}" for _, r in df_empresas.iterrows()])
                e_target = str(sel_e.split("-")[0].strip())
                dados_e_ant = df_empresas[df_empresas['cnpj'].astype(str) == e_target].iloc[0]
            else: dados_e_ant = None
            
            with st.form("f_emp", clear_on_submit=True):
                cnpj = st.text_input("CNPJ (Senha):", value=str(dados_e_ant['cnpj']) if dados_e_ant is not None else "")
                n_emp = st.text_input("Nome Empresa (Usuário):", value=str(dados_e_ant['nome']) if dados_e_ant is not None else "")
                resp = st.text_input("Responsável:", value=str(dados_e_ant['responsavel']) if dados_e_ant is not None else "")
                tel_e = st.text_input("Telefone:", value=str(dados_e_ant['telefone']) if dados_e_ant is not None else "")
                mail = st.text_input("E-mail:", value=str(dados_e_ant['email']) if dados_e_ant is not None else "")
                stat_e = st.selectbox("Status:", ["Ativo", "Inativo"], index=0 if dados_e_ant is None else ["Ativo", "Inativo"].index(dados_e_ant['status']))
                
                if st.form_submit_button("Salvar Empresa"):
                    if not cnpj or not n_emp:
                        st.error("CNPJ e Nome da Empresa são obrigatórios.")
                    else:
                        if not modo_e:
                            novo_e = pd.DataFrame([{'cnpj': cnpj, 'nome': n_emp, 'responsavel': resp, 'telefone': tel_e, 'email': mail, 'status': stat_e}])
                            df_empresas = pd.concat([df_empresas, novo_e], ignore_index=True)
                        else:
                            df_empresas.loc[df_empresas['cnpj'].astype(str) == e_target, ['nome','responsavel','telefone','email','status']] = [n_emp, resp, tel_e, mail, stat_e]
                        salvar_dados(df_empresas, FILE_EMPRESAS)
                        st.success("✅ Empresa salva com sucesso!")
                        st.rerun()

            # Opção de Excluir Registro (Apenas se estiver no modo de edição)
            if modo_e and e_target is not None:
                st.write("---")
                st.markdown("⚠️ **Zona de Perigo**")
                if st.button("❌ Excluir esta Empresa Permanentemente", key="del_emp_btn"):
                    df_empresas = df_empresas[df_empresas['cnpj'].astype(str) != e_target]
                    salvar_dados(df_empresas, FILE_EMPRESAS)
                    st.success("🗑️ Empresa excluída com sucesso!")
                    st.rerun()

    # ==================== ABA: PRESTADORES ====================
    with menu[4]:
        st.subheader("Gerenciar Prestadores")
        opcao_p = st.radio("Ação Prestadores:", ["Listar", "Incluir / Editar"], horizontal=True)
        if opcao_p == "Listar":
            st.dataframe(df_prestadores.style.map(colorir_status, subset=['status']), use_container_width=True)
        else:
            modo_p = st.checkbox("Editar prestador existente")
            p_target = None
            if modo_p and not df_prestadores.empty:
                sel_p = st.selectbox("Selecione o prestador para editar/excluir:", [f"{r['id']} - {r['nome']}" for _, r in df_prestadores.iterrows()])
                p_target = int(sel_p.split("-")[0].strip())
                dados_p_ant = df_prestadores[df_prestadores['id'] == p_target].iloc[0]
            else: dados_p_ant = None
            
            with st.form("f_prest", clear_on_submit=True):
                n_prest = st.text_input("Nome:", value=str(dados_p_ant['nome']) if dados_p_ant is not None else "")
                t_prest = st.text_input("Tipo:", value=str(dados_p_ant['tipo']) if dados_p_ant is not None else "Guincho Prancha")
                tel_p = st.text_input("Telefone:", value=str(dados_p_ant['telefone']) if dados_p_ant is not None else "")
                cid_p = st.text_input("Cidade:", value=str(dados_p_ant['cidade']) if dados_p_ant is not None else "")
                stat_p = st.selectbox("Status:", ["Ativo", "Inativo"], index=0 if dados_p_ant is None else ["Ativo", "Inativo"].index(dados_p_ant['status']))
                
                if st.form_submit_button("Salvar Prestador"):
                    if not n_prest or not tel_p:
                        st.error("Nome e Telefone são obrigatórios.")
                    else:
                        if not modo_p:
                            prox_p = int(df_prestadores['id'].max() + 1) if not df_prestadores.empty else 1
                            novo_p = pd.DataFrame([{'id': prox_p, 'nome': n_prest, 'tipo': t_prest, 'telefone': tel_p, 'cidade': cid_p, 'status': stat_p}])
                            df_prestadores = pd.concat([df_prestadores, novo_p], ignore_index=True)
                        else:
                            df_prestadores.loc[df_prestadores['id'] == p_target, ['nome','tipo','telefone','cidade','status']] = [n_prest, t_prest, tel_p, cid_p, stat_p]
                        salvar_dados(df_prestadores, FILE_PRESTADORES)
                        st.success("✅ Prestador salvo com sucesso!")
                        st.rerun()

            # Opção de Excluir Registro (Apenas se estiver no modo de edição)
            if modo_p and p_target is not None:
                st.write("---")
                st.markdown("⚠️ **Zona de Perigo**")
                if st.button("❌ Excluir este Prestador Permanentemente", key="del_prest_btn"):
                    df_prestadores = df_prestadores[df_prestadores['id'] != p_target]
                    salvar_dados(df_prestadores, FILE_PRESTADORES)
                    st.success("🗑️ Prestador excluído com sucesso!")
                    st.rerun()

# --- INTERFACE RESTRITA DAS EMPRESAS PARCEIRAS ---
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
                sel_part = st.selectbox("Selecione o seu cliente para editar/excluir:", [f"{r['id']} - {r['nome']}" for _, r in df_filtrado_p.iterrows()])
                part_target = int(sel_part.split("-")[0].strip())
                dados_part_ant = df_filtrado_p[df_filtrado_p['id'] == part_target].iloc[0]
            else: dados_part_ant = None
            
            with st.form("f_parceiro", clear_on_submit=True):
                p_nome = st.text_input("Nome Completo:", value=str(dados_part_ant['nome']) if dados_part_ant is not None else "")
                p_cpf = st.text_input("CPF:", value=str(dados_part_ant['cpf']) if dados_part_ant is not None else "")
                p_tel = st.text_input("Telefone:", value=str(dados_part_ant['tel']) if dados_part_ant is not None else "")
                p_vei = st.text_input("Veículo:", value=str(dados_part_ant['vei']) if dados_part_ant is not None else "")
                p_pla = st.text_input("Placa:", value=str(dados_part_ant['pla']) if dados_part_ant is not None else "")
                p_est = st.text_input("UF:", value=str(dados_part_ant['est']) if dados_part_ant is not None else "RN")
                p_stat = st.selectbox("Status do Serviço:", ["Ativo", "Inativo"], index=0 if dados_part_ant is None else ["Ativo", "Inativo"].index(dados_part_ant['status']))
                
                if st.form_submit_button("Confirmar Registro"):
                    if not p_nome or not p_pla:
                        st.error("Nome e Placa são obrigatórios.")
                    else:
                        if not modo_part:
                            prox_id = int(df_clientes['id'].max() + 1) if not df_clientes.empty else 1
                            novo_reg = pd.DataFrame([{'id': prox_id, 'nome': p_nome, 'cpf': p_cpf, 'tel': p_tel, 'vei': p_vei, 'pla': p_pla, 'est': p_est, 'emp_name': st.session_state.empresa_vinculada, 'status': p_stat}])
                            df_clientes = pd.concat([df_clientes, novo_reg], ignore_index=True)
                        else:
                            df_clientes.loc[df_clientes['id'] == part_target, ['nome','cpf','tel','vei','pla','est','status']] = [p_nome, p_cpf, p_tel, p_vei, p_pla, p_est, p_stat]
                        salvar_dados(df_clientes, FILE_CLIENTES)
                        st.success("✅ Atualizado com sucesso!")
                        st.rerun()

            # Opção do Parceiro Excluir o próprio cliente
            if modo_part and part_target is not None:
                st.write("---")
                st.markdown("⚠️ **Zona de Perigo**")
                if st.button("❌ Excluir este Cliente Permanentemente", key="del_part_cli_btn"):
                    df_clientes = df_clientes[df_clientes['id'] != part_target]
                    salvar_dados(df_clientes, FILE_CLIENTES)
                    st.success("🗑️ Cliente excluído com sucesso!")
                    st.rerun()

    with menu_parceiro[1]:
        df_os_parceiro = df_os[df_os['empresa'].str.lower() == st.session_state.empresa_vinculada.lower()]
        if df_os_parceiro.empty: st.info("Nenhum acionamento registrado.")
        else: st.dataframe(df_os_parceiro, use_container_width=True)
