import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DA PÁGINA E IDENTIDADE VISUAL ---
st.set_page_config(
    page_title="Central 24h - AD Rastreamento Veicular",
    layout="wide",
    page_icon="🔒"
)

# Estilização customizada com as cores da marca (Roxo e Vermelho)
st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: #7B2CBF; text-align: center; margin-bottom: 5px; }
    .subtitle { font-size: 16px; color: #E53935; text-align: center; margin-bottom: 25px; font-weight: 500; }
    .stButton>button { background-color: #7B2CBF; color: white; border-radius: 5px; }
    .stButton>button:hover { background-color: #9D4EDD; color: white; }
    .alert-box { padding: 10px; border-radius: 5px; margin: 10px 0; }
    .alert-danger { background-color: #FFCDD2; color: #B71C1C; border: 1px solid #E53935; }
    .alert-success { background-color: #C8E6C9; color: #1B5E20; border: 1px solid #4CAF50; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">AD RASTREAMENTO VEICULAR</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Sistema Central de Gestão de Assistência 24h</div>', unsafe_allow_html=True)

# --- DIRETÓRIOS E BANCO DE DADOS (CSV) ---
DB_DIR = "AD_Assistencia"
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

ARQUIVOS = {
    "clientes": os.path.join(DB_DIR, "banco_clientes.csv"),
    "prestadores": os.path.join(DB_DIR, "banco_prestadores.csv"),
    "os": os.path.join(DB_DIR, "banco_os.csv"),
    "parceiros": os.path.join(DB_DIR, "banco_parceiros.csv")
}

# --- FUNÇÕES DE SUPORTE E SEGURANÇA DE DADOS ---
def carregar_dados(tipo):
    caminho = ARQUIVOS[tipo]
    if os.path.exists(caminho):
        # Garantir tipagem string para evitar perda de zeros à esquerda ou acréscimo de .0
        return pd.read_csv(caminho, dtype=str)
    
    # Inicialização caso os arquivos não existam (Estrutura Completa de Colunas)
    if tipo == "clientes":
        return pd.DataFrame(columns=["id_cliente", "empresa_parceira", "nome", "cpf_cnpj", "telefone", "rua", "numero", "bairro", "cidade", "uf", "cep", "plano_km", "veiculos"])
    elif tipo == "prestadores":
        return pd.DataFrame(columns=["cpf_cnpj", "nome", "telefone", "cidade", "uf", "bairro", "status", "homologado", "senha", "frota"])
    elif tipo == "os":
        return pd.DataFrame(columns=["id_os", "id_cliente", "data_hora", "tipo_servico", "prestador_cpf_cnpj", "veiculo_placa"])
    elif tipo == "parceiros":
        # Cadastro inicial padrão de empresas parceiras de teste
        return pd.DataFrame([
            {"usuario": "parceiro1", "senha": "123", "empresa": "G2 Rastreamento", "uf": "RN"},
            {"usuario": "fortia", "senha": "123", "empresa": "Fortia Rastreamento", "uf": "RN"}
        ], dtype=str)

def salvar_dados(df, tipo):
    caminho = ARQUIVOS[tipo]
    df.to_csv(caminho, index=False)

def normalizar_busca(texto):
    if not isinstance(texto, str):
        return ""
    return texto.replace(".", "").replace("-", "").replace("/", "").replace(" ", "").lower()

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO (LOGIN PERSISTENTE) ---
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'perfil' not in st.session_state:
    st.session_state.perfil = None
if 'empresa_parceira' not in st.session_state:
    st.session_state.empresa_parceira = None

# Carregamento inicial de tabelas
df_clientes = carregar_dados("clientes")
df_prestadores = carregar_dados("prestadores")
df_os = carregar_dados("os")
df_parceiros = carregar_dados("parceiros")

# --- TELA DE LOGIN ---
if st.session_state.usuario is None:
    st.sidebar.subheader("Acesso ao Sistema")
    login_tipo = st.sidebar.selectbox("Tipo de Acesso", ["Administração", "Empresa Parceira", "Prestador de Serviço"])
    user_input = st.sidebar.text_input("Usuário / CPF / CNPJ")
    pwd_input = st.sidebar.text_input("Senha", type="password")
    
    if st.sidebar.button("Entrar"):
        if login_tipo == "Administração" and user_input == "admin" and pwd_input == "admin":
            st.session_state.usuario = "admin"
            st.session_state.perfil = "admin"
            st.rerun()
        elif login_tipo == "Empresa Parceira":
            match = df_parceiros[(df_parceiros['usuario'] == user_input) & (df_parceiros['senha'] == pwd_input)]
            if not match.empty:
                st.session_state.usuario = user_input
                st.session_state.perfil = "parceiro"
                st.session_state.empresa_parceira = match.iloc[0]['empresa']
                st.rerun()
            else:
                st.sidebar.error("Credenciais inválidas para Parceiro.")
        elif login_tipo == "Prestador de Serviço":
            match = df_prestadores[(df_prestadores['cpf_cnpj'] == user_input) & (df_prestadores['senha'] == pwd_input)]
            if not match.empty:
                if match.iloc[0]['homologado'] == "Aprovado":
                    st.session_state.usuario = user_input
                    st.session_state.perfil = "prestador"
                    st.rerun()
                elif match.iloc[0]['homologado'] == "Reprovado":
                    st.sidebar.error("Seu cadastro foi arquivado. Entre em contato com o suporte.")
                else:
                    st.sidebar.warning("Cadastro aguardando homologação da administração.")
            else:
                st.sidebar.error("Prestador não encontrado ou senha incorreta.")
                
    # Opção de Auto-Cadastro para o Prestador (Porta Lateral)
    st.subheader("É um novo prestador de serviço? Cadastre-se na nossa rede.")
    with st.form("auto_cadastro_prestador", clear_on_submit=True):
        col1, col2 = st.columns(2)
        p_nome = col1.text_input("Nome Completo / Razão Social")
        p_doc = col2.text_input("CPF ou CNPJ (Apenas números)")
        p_tel = col1.text_input("Telefone com DDD (Apenas números)")
        p_senha = col2.text_input("Crie sua Senha de Acesso", type="password")
        p_rua = col1.text_input("Rua")
        p_bairro = col2.text_input("Bairro")
        p_cidade = col1.text_input("Cidade")
        p_uf = col2.text_input("UF", value="RN", max_chars=2)
        
        submit_p = st.form_submit_button("Enviar Cadastro para Análise")
        if submit_p:
            if p_doc and p_nome and p_senha:
                if p_doc in df_prestadores['cpf_cnpj'].values:
                    st.error("Este CPF/CNPJ já possui cadastro no sistema.")
                else:
                    novo_p = pd.DataFrame([{
                        "cpf_cnpj": str(p_doc), "nome": p_nome, "telefone": str(p_tel),
                        "cidade": p_cidade, "uf": p_uf.upper(), "bairro": p_bairro,
                        "status": "Ativo", "homologado": "Pendente", "senha": p_senha, "frota": ""
                    }])
                    df_prestadores = pd.concat([df_prestadores, novo_p], ignore_index=True)
                    salvar_dados(df_prestadores, "prestadores")
                    st.success("Cadastro enviado com sucesso! Aguarde a homologação da administração.")
            else:
                st.error("Por favor, preencha todos os campos obrigatórios (Nome, CPF/CNPJ e Senha).")

else:
    # --- USUÁRIO LOGADO: BARRA LATERAL ---
    st.sidebar.write(f"**Perfil:** {st.session_state.perfil.upper()}")
    st.sidebar.write(f"**Usuário:** {st.session_state.usuario}")
    if st.session_state.empresa_parceira:
        st.sidebar.write(f"**Empresa:** {st.session_state.empresa_parceira}")
        
    if st.sidebar.button("Sair / Logout"):
        st.session_state.usuario = None
        st.session_state.perfil = None
        st.session_state.empresa_parceira = None
        st.rerun()

    # =========================================================================
    # PERFIL INTERFACE: ADMINISTRADOR (TORRE DE COMANDO)
    # =========================================================================
    if st.session_state.perfil == "admin":
        abas = st.tabs(["Nova Ordem de Serviço", "Gestão de Clientes", "Homologação de Prestadores", "Prestadores Ativos", "Arquivados / Reprovados"])
        
        # ABA 1: NOVA OS (ADMIN)
        with abas[0]:
            st.subheader("Abertura Rápida de Chamado")
            busca_query = st.text_input("Buscar Cliente por Nome, CPF ou Placa do Veículo")
            
            cliente_selecionado = None
            if busca_query:
                q = normalizar_busca(busca_query)
                # Filtro inteligente varrendo campos e string interna de veículos
                resultados = df_clientes[
                    df_clientes['nome'].str.lower().str.contains(q, na=False) |
                    df_clientes['cpf_cnpj'].str.contains(q, na=False) |
                    df_clientes['veiculos'].str.lower().str.contains(q, na=False)
                ]
                
                if not resultados.empty:
                    opcoes_clientes = {f"{r['nome']} ({r['cpf_cnpj']})": r for _, r in resultados.iterrows()}
                    escolha = st.selectbox("Selecione o Cliente Encontrado", list(opcoes_clientes.keys()))
                    cliente_selecionado = opcoes_clientes[escolha]
                else:
                    st.warning("Nenhum cliente localizado com os termos informados.")
            
            if cliente_selecionado is not None:
                st.markdown("---")
                st.markdown(f"### Dados do Contrato - Plano KM: **{cliente_selecionado['plano_km']}**")
                
                # --- LÓGICA DE VALIDAÇÃO DE VIGÊNCIA (60 DIAS) E LIMITES DE SERVIÇO ---
                os_cliente = df_os[df_os['id_cliente'] == cliente_selecionado['id_cliente']]
                
                # Checar última OS para o semáforo visual de 60 dias
                bloqueio_vigencia = False
                if not os_cliente.empty:
                    os_cliente = os_cliente.copy()
                    os_cliente['data_hora'] = pd.to_datetime(os_cliente['data_hora'], errors='coerce')
                    ultima_data = os_cliente['data_hora'].max()
                    
                    if pd.notna(ultima_data):
                        dias_passados = (datetime.now() - ultima_data).days
                        if dias_passados < 60:
                            st.markdown(f'<div class="alert-box alert-danger">⚠️ **PONTO DE ATENÇÃO (VIGÊNCIA DOS 60 DIAS):** Último acionamento realizado há {dias_passados} dias (Data: {ultima_data.strftime("%d/%m/%Y")}). Cliente em período de restrição contratual.</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="alert-box alert-success">✅ **STATUS CONTRATUAL:** Fora do período de vigência de 60 dias. Último uso há {dias_passados} dias.</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="alert-box alert-success">✅ **STATUS CONTRATUAL:** Sem registros de acionamentos anteriores. Liberado.</div>', unsafe_allow_html=True)

                # Contagem de tipos de serviços utilizados histórico
                qtd_guincho = len(os_cliente[os_cliente['tipo_servico'] == "Guincho"])
                qtd_outros = len(os_cliente[os_cliente['tipo_servico'] != "Guincho"])
                
                st.write(f"**Histórico de Utilização:** {qtd_guincho}/5 Guinchos utilizados.")
                
                # Formulário Limpo para abertura de OS
                with st.form("nova_os_form", clear_on_submit=True):
                    # Desmembrar string de veículos cadastrados
                    lista_veiculos = eval(cliente_selecionado['veiculos']) if isinstance(cliente_selecionado['veiculos'], str) and cliente_selecionado['veiculos'].startswith('[') else [{"placa": "Padrão", "modelo": "Veículo Principal"}]
                    opcoes_v = [f"{v['modelo']} - Placa: {v['placa']}" for v in lista_veiculos]
                    
                    v_escolhido = st.selectbox("Selecione o Veículo para o Atendimento", opcoes_v)
                    tipo_s = st.selectbox("Tipo de Assistência Requerida", ["Guincho", "Pane Seca", "Elétrica", "Chaveiro", "Borracheiro"])
                    
                    # LOGÍSTICA DE PRESTADORES POR PROXIMIDADE
                    st.write("**Prestadores Disponíveis na Região (Ordenados por Proximidade):**")
                    prestadores_validos = df_prestadores[(df_prestadores['status'] == "Ativo") & (df_prestadores['homologado'] == "Aprovado")]
                    
                    if not prestadores_validos.empty:
                        # Criar ranking de ordenação com base no endereço do cliente
                        def calcular_proximidade(row):
                            if str(row['bairro']).lower() == str(cliente_selecionado['bairro']).lower() and str(row['cidade']).lower() == str(cliente_selecionado['cidade']).lower():
                                return 0 # Mesmo Bairro e Cidade
                            elif str(row['cidade']).lower() == str(cliente_selecionado['cidade']).lower():
                                return 1 # Mesma Cidade, Bairros distintos
                            elif str(row['uf']).lower() == str(cliente_selecionado['uf']).lower():
                                return 2 # Mesmo Estado
                            return 3 # Fora do Estado
                        
                        prestadores_validos = prestadores_validos.copy()
                        prestadores_validos['proximidade'] = prestadores_validos.apply(calcular_proximidade, axis=1)
                        prestadores_validos = prestadores_validos.sort_values(by='proximidade')
                        
                        lista_p_nomes = []
                        p_mapeamento = {}
                        for _, row in prestadores_validos.iterrows():
                            desc = f"{row['nome']} | Local: {row['bairro']} - {row['cidade']}/{row['uf']} [Telefone: {row['telefone']}]"
                            lista_p_nomes.append(desc)
                            p_mapeamento[desc] = row['cpf_cnpj']
                            
                        p_selecionado_desc = st.selectbox("Selecione o Prestador Logístico", lista_p_nomes)
                        p_final_id = p_mapeamento[p_selecionado_desc]
                    else:
                        st.error("Nenhum prestador homologado e ativo cadastrado no sistema.")
                        p_final_id = None
                        
                    fechar_os = st.form_submit_button("Confirmar e Registrar Ordem de Serviço")
                    
                    if fechar_os:
                        if p_final_id:
                            nova_os_row = pd.DataFrame([{
                                "id_os": str(len(df_os) + 1001),
                                "id_cliente": cliente_selecionado['id_cliente'],
                                "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "tipo_servico": tipo_s,
                                "prestador_cpf_cnpj": p_final_id,
                                "veiculo_placa": v_escolhido
                            }])
                            df_os = pd.concat([df_os, nova_os_row], ignore_index=True)
                            salvar_dados(df_os, "os")
                            st.success(f"Ordem de Serviço registrada com sucesso! Data/Hora sincronizada com o servidor.")
        
        # ABA 2: GESTÃO DE CLIENTES (HIERARQUIA POR EMPRESA)
        with abas[1]:
            st.subheader("Painel Administrativo da Base de Clientes")
            
            with st.expander("➕ Adicionar Novo Cliente Manualmente", expanded=False):
                with st.form("form_novo_cliente", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    c_nome = col1.text_input("Nome do Cliente")
                    c_doc = col2.text_input("CPF ou CNPJ (Apenas números)")
                    c_tel = col1.text_input("Telefone")
                    c_parceiro = col2.selectbox("Empresa Vinculada / Parceira", df_parceiros['empresa'].unique())
                    
                    c_rua = col1.text_input("Rua")
                    c_num = col2.text_input("Número")
                    c_bairro = col1.text_input("Bairro")
                    c_cidade = col2.text_input("Cidade")
                    
                    # Herança de UF da Empresa Parceira selecionada
                    uf_sugerida = df_parceiros[df_parceiros['empresa'] == c_parceiro].iloc[0]['uf']
                    c_uf = col1.text_input("UF", value=uf_sugerida, max_chars=2)
                    c_cep = col2.text_input("CEP")
                    c_plano = col1.selectbox("Franquia Contratada (Plano KM)", ["50km", "100km", "200km"])
                    
                    st.write("**Dados dos Veículos do Cliente (Múltiplos Veículos)**")
                    v1_placa = col1.text_input("Placa Veículo 1")
                    v1_mod = col2.text_input("Modelo Veículo 1")
                    v2_placa = col1.text_input("Placa Veículo 2 (Opcional)")
                    v2_mod = col2.text_input("Modelo Veículo 2 (Opcional)")
                    
                    cadastrar_c = st.form_submit_button("Salvar Registro de Cliente")
                    if cadastrar_c:
                        if c_nome and c_doc:
                            lista_v = [{"placa": v1_placa, "modelo": v1_mod}]
                            if v2_placa:
                                lista_v.append({"placa": v2_placa, "modelo": v2_mod})
                                
                            novo_cli = pd.DataFrame([{
                                "id_cliente": str(len(df_clientes) + 1),
                                "empresa_parceira": c_parceiro, "nome": c_nome, "cpf_cnpj": str(c_doc),
                                "telefone": str(c_tel), "rua": c_rua, "numero": c_num, "bairro": c_bairro,
                                "cidade": c_cidade, "uf": c_uf.upper(), "cep": c_cep, "plano_km": c_plano,
                                "veiculos": str(lista_v)
                            }])
                            df_clientes = pd.concat([df_clientes, novo_cli], ignore_index=True)
                            salvar_dados(df_clientes, "clientes")
                            st.success("Cliente indexado com sucesso na base de dados.")
                            st.rerun()

            # Exibição Hierárquica organizada por Empresas Parceiras
            st.markdown("### Organização de Carteira de Clientes por Parceiros")
            empresas_ativas = df_clientes['empresa_parceira'].unique()
            for emp in empresas_ativas:
                with st.expander(f"📁 Carteira de Clientes - {emp}", expanded=False):
                    clis_da_empresa = df_clientes[df_clientes['empresa_parceira'] == emp]
                    st.dataframe(clis_da_empresa[["nome", "cpf_cnpj", "telefone", "cidade", "plano_km", "veiculos"]], use_container_width=True)

        # ABA 3: HOMOLOGAÇÃO DE PRESTADORES (PENDENTES)
        with abas[2]:
            st.subheader("Solicitações de Cadastro de Prestadores Pendentes")
            pendentes = df_prestadores[df_prestadores['homologado'] == "Pendente"]
            
            if not pendentes.empty:
                st.warning(f"⚠️ Existem {len(pendentes)} cadastros aguardando sua revisão.")
                for idx, row in pendentes.iterrows():
                    st.markdown(f"**Prestador:** {row['nome']} | **Documento:** {row['cpf_cnpj']} | **Local:** {row['cidade']}/{row['uf']}")
                    col_b1, col_b2 = st.columns(6)
                    if col_b1.button("Aprovar Cadastro", key=f"ap_ {row['cpf_cnpj']}"):
                        df_prestadores.at[idx, 'homologado'] = "Aprovado"
                        salvar_dados(df_prestadores, "prestadores")
                        st.success(f"Prestador {row['nome']} homologado com sucesso.")
                        st.rerun()
                    if col_b2.button("Arquivar / Reprovar", key=f"rep_ {row['cpf_cnpj']}"):
                        df_prestadores.at[idx, 'homologado'] = "Reprovado"
                        salvar_dados(df_prestadores, "prestadores")
                        st.error(f"Cadastro de {row['nome']} movido para arquivos reprovados.")
                        st.rerun()
                    st.markdown("---")
            else:
                st.info("Nenhuma solicitação de homologação pendente no momento.")

        # ABA 4: PRESTADORES ATIVOS
        with abas[3]:
            st.subheader("Rede de Prestadores Credenciados e Ativos")
            ativos_p = df_prestadores[df_prestadores['homologado'] == "Aprovado"]
            st.dataframe(ativos_p[["nome", "cpf_cnpj", "telefone", "cidade", "bairro", "status", "frota"]], use_container_width=True)
            
            st.markdown("### Cadastro Direto de Prestador por Administração")
            with st.form("admin_cadastro_prestador", clear_on_submit=True):
                col1, col2 = st.columns(2)
                adm_p_nome = col1.text_input("Nome / Razão")
                adm_p_doc = col2.text_input("CPF / CNPJ")
                adm_p_tel = col1.text_input("Telefone")
                adm_p_cidade = col2.text_input("Cidade")
                adm_p_uf = col1.text_input("UF", value="RN")
                adm_p_bairro = col2.text_input("Bairro")
                adm_p_senha = col1.text_input("Definir Senha do Prestador", type="password")
                
                btn_adm_p = st.form_submit_button("Inserir Prestador Homologado")
                if btn_adm_p:
                    if adm_p_doc and adm_p_nome:
                        novo_adm_p = pd.DataFrame([{
                            "cpf_cnpj": str(adm_p_doc), "nome": adm_p_nome, "telefone": str(adm_p_tel),
                            "cidade": adm_p_cidade, "uf": adm_p_uf.upper(), "bairro": adm_p_bairro,
                            "status": "Ativo", "homologado": "Aprovado", "senha": adm_p_senha, "frota": "[]"
                        }])
                        df_prestadores = pd.concat([df_prestadores, novo_adm_p], ignore_index=True)
                        salvar_dados(df_prestadores, "prestadores")
                        st.success("Prestador cadastrado e homologado diretamente.")
                        st.rerun()

        # ABA 5: ARQUIVADOS / REPROVADOS (REVERSIBILIDADE)
        with abas[4]:
            st.subheader("Histórico de Prestadores Recusados / Arquivados")
            reprovados = df_prestadores[df_prestadores['homologado'] == "Reprovado"]
            
            if not reprovados.empty:
                for idx, row in reprovados.iterrows():
                    st.markdown(f"❌ **{row['nome']}** ({row['cpf_cnpj']}) - {row['cidade']}/{row['uf']}")
                    if st.button("Reverter Reprovação & Homologar", key=f"rev_{row['cpf_cnpj']}"):
                        df_prestadores.at[idx, 'homologado'] = "Aprovado"
                        salvar_dados(df_prestadores, "prestadores")
                        st.success(f"Cadastro de {row['nome']} recuperado e aprovado com sucesso!")
                        st.rerun()
            else:
                st.info("Nenhum cadastro arquivado no banco.")

    # =========================================================================
    # PERFIL INTERFACE: EMPRESA PARCEIRA (MÓDULO PARCEIRO)
    # =========================================================================
    elif st.session_state.perfil == "parceiro":
        st.subheader(f"Painel Integrado de Gerenciamento - {st.session_state.empresa_parceira}")
        
        p_abas = st.tabs(["Minha Base de Clientes", "Incluir Novo Cliente Contractual"])
        
        with p_abas[0]:
            st.write("### Pesquisa Rápida na Minha Base de Clientes")
            query_parc = st.text_input("Procurar por Nome, Placa ou CPF")
            
            meus_clientes = df_clientes[df_clientes['empresa_parceira'] == st.session_state.empresa_parceira]
            
            if query_parc:
                qp = normalizar_busca(query_parc)
                meus_clientes = meus_clientes[
                    meus_clientes['nome'].str.lower().str.contains(qp, na=False) |
                    meus_clientes['cpf_cnpj'].str.contains(qp, na=False) |
                    meus_clientes['veiculos'].str.lower().str.contains(qp, na=False)
                ]
            st.dataframe(meus_clientes[["nome", "cpf_cnpj", "telefone", "cidade", "plano_km", "veiculos"]], use_container_width=True)
            
        with p_abas[1]:
            st.write("### Cadastrar Cliente sob minha Tutela")
            with st.form("parceiro_cadastro_cliente", clear_on_submit=True):
                col1, col2 = st.columns(2)
                pc_nome = col1.text_input("Nome do Beneficiário")
                pc_doc = col2.text_input("CPF / CNPJ (Apenas números)")
                pc_tel = col1.text_input("Telefone de Contato")
                
                pc_rua = col1.text_input("Rua")
                pc_num = col2.text_input("Número")
                pc_bairro = col1.text_input("Bairro")
                pc_cidade = col2.text_input("Cidade")
                
                # Herança Automática de UF baseada na empresa parceira logada
                uf_heranca = df_parceiros[df_parceiros['empresa'] == st.session_state.empresa_parceira].iloc[0]['uf']
                pc_uf = col1.text_input("UF", value=uf_heranca, max_chars=2)
                pc_cep = col2.text_input("CEP")
                pc_plano = col1.selectbox("Franquia Contratada (Plano KM)", ["50km", "100km", "200km"])
                
                st.write("**Cadastro de Frota do Cliente**")
                pc_v1_placa = col1.text_input("Placa")
                pc_v1_mod = col2.text_input("Modelo")
                
                submit_pc = st.form_submit_button("Efetivar Cadastro")
                if submit_pc:
                    if pc_nome and pc_doc:
                        lista_v_pc = [{"placa": pc_v1_placa, "modelo": pc_v1_mod}]
                        
                        novo_c_pc = pd.DataFrame([{
                            "id_cliente": str(len(df_clientes) + 1),
                            "empresa_parceira": st.session_state.empresa_parceira,
                            "nome": pc_nome, "cpf_cnpj": str(pc_doc), "telefone": str(pc_tel),
                            "rua": pc_rua, "numero": pc_num, "bairro": pc_bairro,
                            "cidade": pc_cidade, "uf": pc_uf.upper(), "cep": pc_cep,
                            "plano_km": pc_plano, "veiculos": str(lista_v_pc)
                        }])
                        df_clientes = pd.concat([df_clientes, novo_c_pc], ignore_index=True)
                        salvar_dados(df_clientes, "clientes")
                        st.success("Cliente indexado com sucesso na carteira de parceiro.")
                        st.rerun()

    # =========================================================================
    # PERFIL INTERFACE: PRESTADOR DE SERVIÇO (PORTAL AUTÔNOMO)
    # =========================================================================
    elif st.session_state.perfil == "prestador":
        idx_prestador = df_prestadores[df_prestadores['cpf_cnpj'] == st.session_state.usuario].index[0]
        dados_p = df_prestadores.loc[idx_prestador]
        
        st.subheader(f"Portal de Serviços Logísticos - Prestador: {dados_p['nome']}")
        
        # Canal Direto de Suporte WhatsApp Oficial da Operação
        st.sidebar.markdown("---")
        st.sidebar.write("💬 **Suporte Operacional Técnico:**")
        url_whatsapp = "https://wa.me/5508001500209"
        st.sidebar.markdown(f'<a href="{url_whatsapp}" target="_blank"><button style="background-color:#25D366;color:white;border-radius:5px;width:100%;border:none;padding:8px;font-weight:bold;cursor:pointer;">Suporte Central 0800</button></a>', unsafe_allow_html=True)
        
        pr_abas = st.tabs(["Atualização de Cadastro", "Gerenciamento de Frota (Multiveículos)"])
        
        with pr_abas[0]:
            st.write("### Informações Cadastrais e Operacionais")
            
            # Atualização de status operacional (Ativo/Inativo)
            status_atual = dados_p['status'] if pd.notna(dados_p['status']) else "Ativo"
            novo_status = st.selectbox("Seu Status Operacional de Disponibilidade", ["Ativo", "Inativo"], index=0 if status_atual == "Ativo" else 1)
            
            p_telefone = st.text_input("Telefone de Contato para Chamados", value=dados_p['telefone'])
            p_bairro_u = st.text_input("Bairro Base de Atuação", value=dados_p['bairro'])
            p_cidade_u = st.text_input("Cidade Base", value=dados_p['cidade'])
            
            if st.button("Atualizar Perfil Operacional"):
                df_prestadores.at[idx_prestador, 'status'] = novo_status
                df_prestadores.at[idx_prestador, 'telefone'] = p_telefone
                df_prestadores.at[idx_prestador, 'bairro'] = p_bairro_u
                df_prestadores.at[idx_prestador, 'cidade'] = p_cidade_u
                salvar_dados(df_prestadores, "prestadores")
                st.success("Perfil e status operacional atualizados na central.")
                st.rerun()
                
        with pr_abas[1]:
            st.write("### Minha Frota Registrada (Multiveículos)")
            
            # Lógica de tratamento de frota multiveicular por string estruturada
            frota_str = dados_p['frota']
            lista_frota = eval(frota_str) if isinstance(frota_str, str) and frota_str.startswith('[') else []
            
            if lista_frota:
                df_frota = pd.DataFrame(lista_frota)
                st.table(df_frota)
            else:
                st.info("Nenhum veículo adicionado à sua frota operacional.")
                
            with st.expander("➕ Incluir Novo Veículo / Guincho à Frota", expanded=False):
                with st.form("add_veiculo_prestador", clear_on_submit=True):
                    v_placa = st.text_input("Placa do Veículo")
                    v_modelo = st.text_input("Modelo / Tipo (Ex: Caminhão Prancha, Saveiro Asa Delta)")
                    submit_v = st.form_submit_button("Adicionar Veículo")
                    
                    if submit_v:
                        if v_placa and v_modelo:
                            lista_frota.append({"placa": v_placa.upper(), "modelo": v_modelo})
                            df_prestadores.at[idx_prestador, 'frota'] = str(lista_frota)
                            salvar_dados(df_prestadores, "prestadores")
                            st.success(f"Veículo de placa {v_placa.upper()} anexado com sucesso à sua frota.")
                            st.rerun()
