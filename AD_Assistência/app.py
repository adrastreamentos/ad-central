import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
from fpdf import FPDF

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA E DESIGN CLEAN (Identidade Visual AD)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="AD Rastreamento Veicular - Central 24h", layout="wide")

st.markdown("""
    <style>
    h3 { font-size: 16px !important; margin-bottom: 5px !important; margin-top: 10px !important; }
    .stButton > button { padding: 4px 8px !important; font-size: 13px !important; border-radius: 4px !important; }
    div.stButton > button:first-child { background-color: #cc0000; color: white; border: none; }
    div.stButton > button:first-child:hover { background-color: #990000; }
    .stTabs [data-baseweb="tab"] { font-size: 14px !important; font-weight: bold !important; }
    .titulo-marca { color: #2e0854; font-size: 28px; font-weight: bold; text-align: center; margin-bottom: 0px; }
    .subtitulo-marca { color: #cc0000; font-size: 14px; font-weight: bold; text-align: center; margin-top: -8px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# MEMÓRIA VOLÁTIL (Até configurarmos o banco embutido do Streamlit Secrets)
# -----------------------------------------------------------------------------
if "empresas" not in st.session_state:
    st.session_state.empresas = [
        {"id": 1, "nome": "AD Rastreamento Veicular", "cid": "São Gonçalo do Amarante", "est": "RN", "tel": "84999999999", "resp": "David", "cnpj": "00000000000000"},
        {"id": 2, "nome": "Parceiro Teste", "cid": "Natal", "est": "RN", "tel": "84988888888", "resp": "Gerente", "cnpj": "11111111111111"}
    ]
if "prestadores" not in st.session_state:
    st.session_state.prestadores = [{"id": 1, "nome": "Guincho RN Comando", "est": "RN", "tipo": "Guincho", "tel": "84988888888"}]
if "clientes" not in st.session_state:
    st.session_state.clientes = [
        {"id": 1, "nome": "Cliente Ativo AD", "cpf": "123", "tel": "8499", "vei": "Polo", "pla": "QRA1234", "est": "RN", "emp_nome": "AD Rastreamento Veicular", "status": "Ativo"},
        {"id": 2, "nome": "Cliente Inativo Parceiro", "cpf": "456", "tel": "8498", "vei": "Gol", "pla": "KKK4321", "est": "RN", "emp_nome": "Parceiro Teste", "status": "Inativo"}
    ]
if "ordens_servico" not in st.session_state:
    st.session_state.ordens_servico = []

# -----------------------------------------------------------------------------
# TELA DE LOGIN DINÂMICA
# -----------------------------------------------------------------------------
if "autenticado" not in st.session_state or not st.session_state.autenticado:
    st.markdown('<p class="titulo-marca">AD Rastreamento Veicular</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitulo-marca">🔒 Central 24h - Área Restrita</p>', unsafe_allow_html=True)
    
    with st.form("form_login"):
        st.subheader("🔑 Digite suas credenciais de acesso")
        usuario_input = st.text_input("Usuário (Nome da Empresa)").strip().lower()
        senha_input = st.text_input("Senha (CNPJ)", type="password").strip()
        
        if st.form_submit_button("Entrar no Sistema"):
            autenticou = False
            
            # Varre as empresas cadastradas para validar o login automaticamente
            for emp in st.session_state.empresas:
                nome_login = str(emp["nome"]).replace(" ", "").lower()
                if usuario_input == nome_login and senha_input == str(emp["cnpj"]):
                    st.session_state.autenticado = True
                    st.session_state.usuario_logado = emp["nome"]
                    st.session_state.perfil_logado = "admin" if emp["id"] == 1 else "parceiro"
                    st.session_state.empresa_logada = emp["nome"]
                    autenticou = True
                    st.rerun()
            
            if not autenticou:
                st.error("Usuário ou senha incorretos para a empresa informada.")
    st.stop()

ESTADOS_BR = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
SERVICOS = ["Guincho", "Pane Seca", "Pane Elétrica", "Borracheiro", "Chaveiro"]
MOTIVOS = ["Furto", "Roubo", "Colisão", "Pane Mecânica", "Outros"]
LIMITES_ANUAIS = {"Guincho": 2, "Pane Seca": 1, "Pane Elétrica": 1, "Borracheiro": 1, "Chaveiro": 1}

# Barra Superior
col_user1, col_user2 = st.columns([8, 2])
with col_user1:
    st.markdown(f'**Central AD 24h** | Empresa: `{st.session_state.usuario_logado.upper()}` ({st.session_state.perfil_logado.upper()})')
with col_user2:
    if st.button("🚪 Sair / Logoff"):
        st.session_state.autenticado = False
        st.rerun()

st.markdown('<p class="titulo-marca">AD Rastreamento Veicular</p>', unsafe_allow_html=True)
st.markdown(f'<p class="subtitulo-marca">⚡ Operação Atendimento - {st.session_state.empresa_logada}</p>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# FILTRAGEM DE PERMISSÕES DE ABAS
# -----------------------------------------------------------------------------
if st.session_state.perfil_logado == "admin":
    clientes_visiveis = st.session_state.clientes
    os_visiveis = st.session_state.ordens_servico
    lista_abas = ["📋 Nova OS", "📊 Relatórios & Baixa PDF", "👤 Clientes", "🏢 Empresas", "👨‍🔧 Prestadores"]
else:
    clientes_visiveis = [c for c in st.session_state.clientes if c['emp_nome'] == st.session_state.empresa_logada]
    os_visiveis = [o for o in st.session_state.ordens_servico if o['empresa_vinculada'] == st.session_state.empresa_logada]
    lista_abas = ["👤 Clientes"] # Conforme alinhado, parceiro só mexe na aba de clientes dele

aba = st.tabs(lista_abas)

# -----------------------------------------------------------------------------
# SE FOR ADMIN: MONTA AS ABAS DE ATENDIMENTO E LOGÍSTICA
# -----------------------------------------------------------------------------
if st.session_state.perfil_logado == "admin":
    # ABA 1: NOVA OS
    with aba[0]:
        st.subheader("📋 Abertura de Chamado Emergencial")
        termo_busca = st.text_input("🔍 Buscar Cliente por Nome, Placa ou CPF (Digite pelo menos 3 letras):", "", key="b_os")
        
        if len(termo_busca) >= 3:
            filtrados_busca = [c for c in clientes_visiveis if termo_busca.lower() in f"{str(c['nome'])} {str(c['pla'])} {str(c['cpf'])}".lower()]
        else:
            filtrados_busca = clientes_visiveis
            
        if filtrados_busca:
            lista_select = [f"{c['nome']} | Placa: {c['pla']} | Status: {c['status']}" for c in filtrados_busca]
            cliente_sel_str = st.selectbox("Confirmar Solicitante do Serviço:", lista_select, key="sel_c")
            cliente_dados = filtrados_busca[lista_select.index(cliente_sel_str)]
            
            st.markdown("---")
            col_o1, col_o2 = st.columns(2)
            with col_o1:
                servico = st.selectbox("Serviço Solicitado", SERVICOS)
                motivo = st.selectbox("Motivo", MOTIVOS)
            with col_o2:
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Regra de Cores Ativo/Inativo na OS (Alerta Visual sem Bloqueio)
                if cliente_dados['status'] == "Inativo":
                    st.error(f"⚠️ **ATENÇÃO:** Este cliente está marcado como **INATIVO** pela empresa parceira ({cliente_dados['emp_nome']}). Verifique antes de enviar o guincho!")
                    texto_botao = "🚀 Autorizar Atendimento (Exceção)"
                else:
                    st.success(f"✔️ Cliente **ATIVO** na base de dados da empresa `{cliente_dados['emp_nome']}`.")
                    texto_botao = "🚀 Iniciar Atendimento / Gerar OS"

            # Busca prestador automático
            p_estado = [p for p in st.session_state.prestadores if str(p['est']).strip().upper() == str(cliente_dados['est']).strip().upper() and p['tipo'] == servico]
            
            with st.form("form_os", clear_on_submit=True):
                descricao = st.text_area("Descrição Detalhada da Situação")
                local_origem = st.text_input("Local de Origem (Link do Maps ou Endereço)")
                destino = st.text_input("Endereço de Destino")
                
                p_final, t_final = "Autônomo", "000"
                if p_estado:
                    lista_p = [f"{p['nome']} (Zap: {p['tel']})" for p in p_estado]
                    p_sel = st.selectbox("Prestador homologado para o Estado:", lista_p)
                    p_final = p_estado[lista_p.index(p_sel)]['nome']
                    t_final = p_estado[lista_p.index(p_sel)]['tel']
                
                if st.form_submit_button(texto_botao):
                    nova_os = {
                        "id": len(st.session_state.ordens_servico) + 1, "cliente": cliente_dados['nome'], "tel_cliente": cliente_dados['tel'],
                        "empresa_vinculada": cliente_dados['emp_nome'], "veiculo": cliente_dados['vei'], "placa": cliente_dados['pla'],
                        "estado_uf": cliente_dados['est'], "servico": servico, "motivo": motivo, "descricao": descricao,
                        "local_origem": local_origem, "destino": destino, "prestador": p_final, "tel_prestador": t_final,
                        "status": "Iniciado", "abertura": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    }
                    st.session_state.ordens_servico.append(nova_os)
                    st.success("OS Gerada com sucesso!")
                    st.rerun()

    # ABA 2: RELATÓRIOS
    with aba[1]:
        st.subheader("📊 Relatórios Gerais")
        if os_visiveis:
            st.dataframe(pd.DataFrame(os_visiveis), use_container_width=True)
        else:
            st.info("Nenhuma OS aberta.")

# -----------------------------------------------------------------------------
# ABA COMPARTILHADA OU EXCLUSIVA: CLIENTES
# -----------------------------------------------------------------------------
# Se for admin, a aba de clientes é a de índice 2. Se for parceiro, é a de índice 0.
indice_aba_cliente = 2 if st.session_state.perfil_logado == "admin" else 0

with aba[indice_aba_cliente]:
    st.subheader("👤 Base de Clientes Cadastrados")
    
    # Formulário de Cadastro de Clientes
    with st.expander("➕ Cadastrar Novo Cliente"):
        with st.form("form_add_c", clear_on_submit=True):
            nome = st.text_input("Nome do Cliente")
            cpf = st.text_input("CPF")
            tel = st.text_input("Telefone Celular")
            vei = st.text_input("Modelo do Veículo")
            pla = st.text_input("Placa do Veículo")
            est = st.selectbox("Estado", ESTADOS_BR)
            status_c = st.selectbox("Status Inicial", ["Ativo", "Inativo"])
            
            if st.session_state.perfil_logado == "admin":
                emp_ops = [e['nome'] for e in st.session_state.empresas]
                emp_nome_c = st.selectbox("Vincular à Empresa", emp_ops)
            else:
                emp_nome_c = st.session_state.empresa_logada
                st.info(f"Empresa Vinculada automaticamente: **{emp_nome_c}**")
                
            if st.form_submit_button("Salvar Cliente"):
                st.session_state.clientes.append({
                    "id": len(st.session_state.clientes)+1, "nome": nome, "cpf": cpf, "tel": tel, "vei": vei, "pla": pla.upper(), "est": est, "emp_nome": emp_nome_c, "status": status_c
                })
                st.success("Cliente cadastrado!")
                st.rerun()

    # Exibição da Tabela com Destaque de Cores para o Status
    if clientes_visiveis:
        df_c = pd.DataFrame(clientes_visiveis)
        
        # Função para pintar a linha/texto baseado no status ativo/inativo
        def colorir_status(val):
            color = '#cc0000' if val == 'Inativo' else '#00cc00'
            return f'color: {color}; font-weight: bold;'
            
        st.dataframe(df_c[['id', 'nome', 'pla', 'vei', 'tel', 'emp_nome', 'status']].style.applymap(colorir_status, subset=['status']), use_container_width=True)

        # Modificação completa dentro da setinha (Retrátil)
        st.markdown("### ⚙️ Modificar Cadastro")
        busca_c_ed = st.text_input("🔎 Procure por ID, Nome ou Placa para liberar a edição:", "", key="b_ed")
        
        filtrados_ed = [c for c in clientes_visiveis if busca_c_ed.lower() in f"{str(c['id'])} {str(c['nome'])} {str(c['pla'])}".lower()] if busca_c_ed else clientes_visiveis
        
        if filtrados_ed:
            lista_ed_ops = [f"ID: {c['id']} | {c['nome']} | Placa: {c['pla']}" for c in filtrados_ed]
            c_ed_str = st.selectbox("Selecione o cliente alvo:", lista_ops=lista_ed_ops, key="sel_ed")
            c_alvo = filtrados_ed[lista_ed_ops.index(c_ed_str)]
            idx_c = st.session_state.clientes.index(c_alvo)
            
            with st.expander(f"📝 Editar Dados de: {c_alvo['nome']}"):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    ed_nome = st.text_input("Nome", c_alvo['nome'], key=f"n_{c_alvo['id']}")
                    ed_cpf = st.text_input("CPF", c_alvo['cpf'], key=f"c_{c_alvo['id']}")
                    ed_tel = st.text_input("Telefone", c_alvo['tel'], key=f"t_{c_alvo['id']}")
                with col_e2:
                    ed_vei = st.text_input("Veículo", c_alvo['vei'], key=f"v_{c_alvo['id']}")
                    ed_pla = st.text_input("Placa", c_alvo['pla'], key=f"p_{c_alvo['id']}")
                    ed_status = st.selectbox("Status do Cliente", ["Ativo", "Inativo"], index=0 if c_alvo['status'] == "Ativo" else 1, key=f"s_{c_alvo['id']}")
                
                if st.button("💾 Mudar e Salvar Alterações", key=f"btn_{c_alvo['id']}"):
                    st.session_state.clientes[idx_c].update({
                        "nome": ed_nome, "cpf": ed_cpf, "tel": ed_tel, "vei": ed_vei, "pla": ed_pla.upper(), "status": ed_status
                    })
                    st.success("Alterações gravadas com sucesso!")
                    st.rerun()

# -----------------------------------------------------------------------------
# ABAS EXCLUSIVAS DO ADMIN (SÓ CARREGAM SE FOR DAVID OU ANDREA)
# -----------------------------------------------------------------------------
if st.session_state.perfil_logado == "admin":
    with aba[3]:
        st.subheader("🏢 Configuração de Empresas")
        with st.expander("➕ Cadastrar Nova Empresa Parceira"):
            with st.form("form_add_e", clear_on_submit=True):
                e_nome = st.text_input("Nome da Empresa")
                e_cnpj = st.text_input("CNPJ (Apenas números - Será a senha de acesso)")
                e_cid = st.text_input("Cidade")
                e_est = st.selectbox("Sede UF", ESTADOS_BR)
                e_tel = st.text_input("Telefone corporativo")
                
                if st.form_submit_button("Salvar Nova Empresa"):
                    if e_nome and e_cnpj:
                        st.session_state.empresas.append({
                            "id": len(st.session_state.empresas)+1, "nome": e_nome, "cnpj": e_cnpj.strip(), "cid": e_cid, "est": e_est, "tel": e_tel, "resp": "Gerente"
                        })
                        st.success(f"Empresa salva! Login gerado: '{e_nome.replace(' ', '').lower()}' | Senha: CNPJ")
                        st.rerun()
        st.dataframe(pd.DataFrame(st.session_state.empresas)[['id', 'nome', 'cnpj', 'cid', 'est', 'tel']], use_container_width=True)

    with aba[4]:
        st.subheader("👨‍🔧 Rede de Prestadores Credenciados")
        st.dataframe(pd.DataFrame(st.session_state.prestadores), use_container_width=True)