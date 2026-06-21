import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import urllib.parse
import base64
import time
import requests
import json

# ===================================================================================
# FUNÇÕES GLOBAIS E ESTILIZAÇÃO
# ===================================================================================
def colorir_status(val):
    return 'color: green; font-weight: bold;' if str(val).strip() == 'Ativo' else 'color: red; font-weight: bold;'

st.set_page_config(page_title="Central 24h - AD Rastreamento Veicular", layout="wide", page_icon="🔒")

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

FOLDER = "AD_Assistencia"
os.makedirs(FOLDER, exist_ok=True)
FILE_CLIENTES = os.path.join(FOLDER, "banco_clientes.csv")
FILE_EMPRESAS = os.path.join(FOLDER, "banco_empresas.csv")
FILE_PRESTADORES = os.path.join(FOLDER, "banco_prestadores.csv")
FILE_OS = os.path.join(FOLDER, "banco_os.csv")

def obter_hora_brasilia():
    return datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M:%S")

def apenas_numeros_letras(texto):
    return "".join(caractere for caractere in str(texto) if caractere.isalnum()).strip().lower()

# ===================================================================================
# NOVO SISTEMA DE SEGURANÇA E BACKUP DE NUVEM
# ===================================================================================
def salvar_no_github(caminho_local):
    token = st.secrets.get("GITHUB_TOKEN", None)
    repo = "adrastreamentos/ad-central"
    if not token: return False, "Token ausente"
    url = f"https://api.github.com/repos/{repo}/contents/{caminho_local.replace(os.sep, '/')}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    try:
        res = requests.get(url, headers=headers)
        sha = res.json().get("sha", None) if res.status_code == 200 else None
        with open(caminho_local, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")
        data = {"message": f"🔥 Auto-salvamento: {caminho_local}", "content": content, "branch": "main"}
        if sha: data["sha"] = sha
        res_put = requests.put(url, headers=headers, json=data)
        if res_put.status_code in [200, 201]: 
            return True, "Sucesso"
        return False, f"GitHub recusou o salvamento. (Erro {res_put.status_code})"
    except Exception as e:
        return False, f"Falha de conexão: {str(e)}"

def salvar_dados(df, caminho):
    df.to_csv(caminho, index=False)
    sucesso, erro = salvar_no_github(caminho)
    return sucesso, erro

def gerar_botao_whatsapp(dados_dict):
    texto = "🚨 *ERRO DE SINCRONIZAÇÃO - LANÇAMENTO MANUAL* 🚨\nOlá, Central AD!\nTentei salvar dados na plataforma, mas o sistema relatou falha na nuvem. Seguem os dados preenchidos para não perdermos o registro:\n\n"
    for k, v in dados_dict.items():
        texto += f"*{k}:* {v}\n"
    texto += "\nPor favor, confirmem o recebimento."
    link = f"https://api.whatsapp.com/send?phone=5584999305771&text={urllib.parse.quote(texto)}"
    st.markdown(f'<a href="{link}" target="_blank" style="text-decoration: none;"><button style="background-color: #25D366; color: white; padding: 12px 24px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; width: 100%; margin-top: 10px;">📲 Informar Falha e Enviar Dados via WhatsApp (Central AD)</button></a>', unsafe_allow_html=True)

def carregar_dados(caminho, colunas_obrigatorias):
    try:
        df = pd.read_csv(caminho, dtype=str)
        df.columns = df.columns.str.strip().str.lower()
        for col in colunas_obrigatorias:
            if col not in df.columns: df[col] = "" 
        for col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
            df[col] = df[col].str.replace(r'\.0$', '', regex=True)
        return df
    except:
        return pd.DataFrame(columns=colunas_obrigatorias)

# ===================================================================================
# IMPORTAÇÃO EM LOTE COM AGRUPAMENTO INTELIGENTE DE FROTA
# ===================================================================================
def importar_clientes_csv(uploaded_file, empresa_vinculada, df_clientes_atual):
    try:
        df_novo = pd.read_csv(uploaded_file, dtype=str)
        df_novo.columns = df_novo.columns.str.strip().str.lower()
        
        colunas_padrao = ['id', 'nome', 'cpf', 'tel', 'endereco', 'cidade', 'cep', 'plano_km', 'est', 'emp_name', 'status', 'vei', 'pla', 'vei_2', 'pla_2', 'veiculos_lista']
        
        for col in colunas_padrao:
            if col not in df_novo.columns:
                df_novo[col] = ""
                
        for col in df_novo.columns:
            df_novo[col] = df_novo[col].fillna("").astype(str).str.strip()
            df_novo[col] = df_novo[col].str.replace(r'\.0$', '', regex=True)
            
        # Normalização inicial de texto e placas
        df_novo['nome'] = df_novo['nome'].str.upper()
        df_novo['pla'] = df_novo['pla'].str.upper().str.replace("-", "").str.replace(" ", "")
        df_novo['pla_2'] = df_novo['pla_2'].str.upper().str.replace("-", "").str.replace(" ", "")
        
        # Cria uma chave invisível para agrupamento (Usa o CPF limpo. Se não houver, usa o Nome limpo)
        df_novo['chave_grupo'] = df_novo['cpf'].apply(lambda x: "".join(filter(str.isalnum, str(x))) if x else "")
        df_novo['chave_grupo'] = df_novo.apply(lambda r: r['chave_grupo'] if r['chave_grupo'] else "".join(filter(str.isalnum, str(r['nome']))), axis=1)
        
        prox_id = int(df_clientes_atual['id'].astype(float).max() + 1) if not df_clientes_atual.empty else 1
        clientes_unificados = []
        
        # Executa a mágica de compactação por cliente
        for chave, g in df_novo.groupby('chave_grupo'):
            if g.empty: continue
            primeira_linha = g.iloc[0].copy()
            
            # Reúne todos os veículos encontrados nas linhas repetidas do cliente
            lista_veiculos = []
            for _, r in g.iterrows():
                if r['pla']:
                    lista_veiculos.append({"Modelo/Ano": r['vei'].upper(), "Placa": r['pla']})
                if r['pla_2']:
                    lista_veiculos.append({"Modelo/Ano": r['vei_2'].upper(), "Placa": r['pla_2']})
            
            # Remove eventuais duplicatas de placa dentro da mesma frota
            veiculos_unicos = []
            placas_vistas = set()
            for v in lista_veiculos:
                if v['Placa'] not in placas_vistas:
                    veiculos_unicos.append(v)
                    placas_vistas.add(v['Placa'])
            
            primeira_linha['emp_name'] = empresa_vinculada
            primeira_linha['status'] = primeira_linha['status'] if primeira_linha['status'] else "Ativo"
            
            if veiculos_unicos:
                primeira_linha['vei'] = veiculos_unicos[0]['Modelo/Ano']
                primeira_linha['pla'] = veiculos_unicos[0]['Placa']
                primeira_linha['veiculos_lista'] = json.dumps(veiculos_unicos)
                if len(veiculos_unicos) > 1:
                    primeira_linha['vei_2'] = veiculos_unicos[1]['Modelo/Ano']
                    primeira_linha['pla_2'] = veiculos_unicos[1]['Placa']
                else:
                    primeira_linha['vei_2'] = ""
                    primeira_linha['pla_2'] = ""
            else:
                primeira_linha['veiculos_lista'] = "[]"
                
            primeira_linha['id'] = str(prox_id)
            prox_id += 1
            
            del primeira_linha['chave_grupo']
            clientes_unificados.append(primeira_linha.to_dict())
            
        df_novos_agrupados = pd.DataFrame(clientes_unificados)
        if df_novos_agrupados.empty:
            return False, "Nenhum dado de veículo ou cliente válido foi identificado."
            
        df_final = pd.concat([df_clientes_atual, df_novos_agrupados], ignore_index=True)
        df_final = df_final[colunas_padrao]
        
        sucesso, erro = salvar_dados(df_final, FILE_CLIENTES)
        if sucesso:
            return True, f"Sucesso! {len(df_novos_agrupados)} cliente(s) frotista(s) unificado(s) (totalizando {len(df_novo)} veículos) foram inseridos no sistema com sucesso!"
        return False, f"Erro ao gravar na nuvem: {erro}"
    except Exception as e:
        return False, f"Erro no processamento lógico dos frotistas: {str(e)}"

# ===================================================================================
# PORTA LATERAL DO PRESTADOR
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
                if match.empty: match = df_p_portal[df_p_portal['senha'] == senha_login]
                if not match.empty:
                    status_hom = match.iloc[0].get('homologado', 'Pendente')
                    if status_hom == 'Aprovado':
                        st.session_state.logado_prestador = True
                        st.session_state.id_prestador_logado = match.iloc[0]['id']
                        st.rerun()
                    elif status_hom == 'Reprovado': st.error("Seu cadastro foi arquivado. Entre em contato com o suporte.")
                    else: st.warning("Seu cadastro ainda está em análise pela nossa central.")
                else: st.error("Dados incorretos ou não encontrados.")
        with tab_p2:
            with st.form("form_novo_prestador"):
                st.write("Preencha os dados para análise:")
                c1, c2 = st.columns(2)
                novo_nome = c1.text_input("Razão Social / Nome Completo")
                novo_cpf = c2.text_input("CPF ou CNPJ (Será seu Login)")
                novo_tipos_lista = c1.multiselect("Tipos de Serviço Prestado:", OPCOES_SERVICOS, default=["Guincho"])
                novo_tel = c2.text_input("Telefone com DDD")
                novo_end = c1.text_input("Endereço / Logradouro")
                nova_senha = c2.text_input("Crie sua Senha", type="password")
                novo_cid = c1.text_input("Cidade")
                novo_cep = c2.text_input("CEP")
                novo_est = c1.selectbox("Estado Base de Atuação", ESTADOS_BR, index=ESTADOS_BR.index("RN"))
                if st.form_submit_button("Enviar Cadastro"):
                    cpf_limpo = apenas_numeros_letras(novo_cpf)
                    tel_limpo = apenas_numeros_letras(novo_tel)
                    tipo_final_str = ", ".join(novo_tipos_lista)
                    if not novo_nome or not cpf_limpo or not nova_senha: st.error("Nome, CPF/CNPJ e Senha são obrigatórios.")
                    elif not novo_tipos_lista: st.error("Selecione ao menos um tipo de serviço prestado.")
                    else:
                        prox_id = int(df_p_portal['id'].astype(float).max() + 1) if not df_p_portal.empty else 1
                        novo_p = pd.DataFrame([{'id': str(prox_id), 'nome': novo_nome.upper(), 'cpf': cpf_limpo, 'tipo': tipo_final_str, 'telefone': tel_limpo, 'endereco': novo_end, 'cidade': novo_cid.upper(), 'cep': novo_cep, 'est': novo_est, 'status': 'Ativo', 'homologado': 'Pendente', 'senha': nova_senha, 'frota': '[]'}])
                        df_p_portal_temp = pd.concat([df_p_portal, novo_p], ignore_index=True)
                        sucesso, erro = salvar_dados(df_p_portal_temp, FILE_PRESTADORES)
                        if sucesso:
                            st.success("✅ Cadastro enviado com sucesso! Aguarde nossa mensagem no WhatsApp.")
                        else:
                            st.error("⚠️ ALERTA: Falha na nuvem da Central AD.")
                            gerar_botao_whatsapp({"Ação": "Novo Cadastro de Prestador", "Nome": novo_nome, "CPF/CNPJ": cpf_limpo, "Telefone": novo_tel, "Cidade": novo_cid, "Serviços": tipo_final_str})
    
    if st.session_state.logado_prestador:
        p_dados_atual = df_p_portal[df_p_portal['id'] == str(st.session_state.id_prestador_logado)].iloc[0]
        col_cab1, col_cab2 = st.columns([4, 1])
        col_cab1.subheader(f"Painel Operacional: {p_dados_atual['nome']}")
        if col_cab2.button("Sair do Painel"):
            st.session_state.logado_prestador = False
            st.rerun()
            
        with st.form("form_edit_prestador"):
            servicos_atuais_logado = [s for s in [x.strip() for x in str(p_dados_atual.get('tipo', '')).split(',')] if s in OPCOES_SERVICOS]
            e_cpf = st.text_input("CPF/CNPJ", value=p_dados_atual.get('cpf',''), disabled=True)
            e_tipos_lista = st.multiselect("Tipos de Serviço Prestado:", OPCOES_SERVICOS, default=servicos_atuais_logado)
            e_tel = st.text_input("Telefone de Contato", value=p_dados_atual.get('telefone',''))
            e_end = st.text_input("Endereço / Base", value=p_dados_atual.get('endereco',''))
            c1, c2 = st.columns(2)
            e_cid = c1.text_input("Cidade Base", value=p_dados_atual.get('cidade',''))
            e_cep = c2.text_input("CEP", value=p_dados_atual.get('cep',''))
            idx_est = ESTADOS_BR.index(str(p_dados_atual.get('est','RN')).upper()) if str(p_dados_atual.get('est','RN')).upper() in ESTADOS_BR else ESTADOS_BR.index("RN")
            e_est = st.selectbox("Estado", ESTADOS_BR, index=idx_est)
            
            if st.form_submit_button("Salvar Minhas Informações"):
                df_p_portal.loc[df_p_portal['id'] == str(st.session_state.id_prestador_logado), ['tipo','telefone','endereco','cidade','cep','est']] = [", ".join(e_tipos_lista), apenas_numeros_letras(e_tel), e_end, e_cid.upper(), e_cep, e_est]
                sucesso, erro = salvar_dados(df_p_portal, FILE_PRESTADORES)
                if sucesso:
                    st.success("Dados updated com sucesso!")
                    time.sleep(1.5); st.rerun()
                else:
                    st.error("⚠️ Falha ao salvar alterações na nuvem.")
                    gerar_botao_whatsapp({"Ação": "Atualização de Prestador", "Nome": p_dados_atual['nome'], "Novos Serviços": ", ".join(e_tipos_lista), "Novo Telefone": e_tel})
    st.stop()

# ===================================================================================
# GERAÇÃO DE RELATÓRIO PDF (HTML) E CARREGAMENTO DE DADOS
# ===================================================================================
def exportar_pdf_html_oficial(df_os_rows, df_clientes_completo, titulo_pdf="relatorio_atendimento"):
    cards_html = ""
    for _, row in df_os_rows.iterrows():
        empresa_os = str(row['empresa']).upper()
        df_c_alvo = df_clientes_completo[df_clientes_completo['id'].astype(str) == str(row['cliente_id'])]
        tel_cliente, veiculo_cliente, placa_cliente, estado_cliente, plano_km_pdf = row.get('tel', ''), "", str(row.get('placa', '')).upper(), "RN", str(row.get('plano_km', 'N/D'))
        valor_cobrado_pdf = str(row.get('valor_cobrado', '0,00'))
        if not df_c_alvo.empty:
            if not tel_cliente: tel_cliente = df_c_alvo.iloc[0].get('tel', '')
            veiculo_cliente = str(df_c_alvo.iloc[0].get('vei', '')).upper()
            if placa_cliente in ['NAN', 'N/D', '']: placa_cliente = str(df_c_alvo.iloc[0].get('pla', '')).upper()
            estado_cliente = str(df_c_alvo.iloc[0].get('est', '')).upper()
            if plano_km_pdf in ['N/D', 'nan']: plano_km_pdf = str(df_c_alvo.iloc[0].get('plano_km', 'N/D'))
            
        cards_html += f"""
        <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto 40px auto; padding: 20px; background-color: #fff; page-break-inside: avoid;">
            <div style="text-align: center; margin-bottom: 10px;">
                <h2 style="margin: 0; color: #7B2CBF; font-size: 22px; font-weight: bold;">{empresa_os} - ASSISTÊNCIA 24H</h2>
                <p style="margin: 5px 0; font-style: italic; color: #555; font-size: 13px;">Relatorio de Atendimento - OS Numero: {row['id']}</p>
            </div>
            <hr style="border: 0; border-top: 1px solid #333; margin-bottom: 20px;">
            <div style="margin-bottom: 20px;">
                <h3 style="margin: 0 0 10px 0; font-size: 14px; font-weight: bold;">1. DETALHES DO CLIENTE E VÍNCULO</h3>
                <p style="margin: 3px 0; font-size: 13px;">Nome: {str(row['cliente_nome']).upper()} | Tel: {tel_cliente}</p>
                <p style="margin: 3px 0; font-size: 13px;">Empresa: {empresa_os} | Franquia: <strong>{plano_km_pdf}</strong></p>
                <p style="margin: 3px 0; font-size: 13px;">Valor do Serviço Particular: <strong>R$ {valor_cobrado_pdf}</strong></p>
                <p style="margin: 3px 0; font-size: 13px;">Veículo: {veiculo_cliente} | Placa: {placa_cliente} | UF: {estado_cliente}</p>
            </div>
            <div style="margin-bottom: 20px;">
                <h3 style="margin: 0 0 10px 0; font-size: 14px; font-weight: bold;">2. DADOS DO ACIONAMENTO E SERVIÇO</h3>
                <p style="margin: 3px 0; font-size: 13px;">Serviço: {row['tipo_servico']} | Motivo: {str(row['motivo']).upper()}</p>
                <p style="margin: 3px 0; font-size: 13px;">Horário: {row['data_hora']} | Status: {str(row.get('status_os', 'ENCERRADO')).upper()}</p>
                <p style="margin: 3px 0; font-size: 13px;">Origem: {row['localizacao']} | Destino: {row['destino']}</p>
            </div>
            <div style="margin-bottom: 20px;">
                <h3 style="margin: 0 0 10px 0; font-size: 14px; font-weight: bold;">3. PRESTADOR ACIONADO</h3>
                <p style="margin: 3px 0; font-size: 13px;">Nome: {str(row['prestador']).upper()}</p>
            </div>
            <div style="margin-bottom: 10px;">
                <h3 style="margin: 0 0 10px 0; font-size: 14px; font-weight: bold;">4. DESCRIÇÃO</h3>
                <p style="margin: 3px 0; font-size: 13px; background-color: #fcfcfc; padding: 5px;">{row['obs']}</p>
            </div><hr style="border: 0; border-top: 1px dashed #ccc; margin-top: 30px;">
        </div>
        """
    b64 = base64.b64encode(f"<html><head><meta charset='utf-8'></head><body>{cards_html}</body></html>".encode('utf-8')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{titulo_pdf}_{datetime.now().strftime("%Y%m%d")}.html" style="text-decoration: none;"><button style="background-color: #E53935; color: white; padding: 12px 24px; border: none; border-radius: 6px; font-size: 15px; font-weight: bold; cursor: pointer;">🖨️ Baixar Relatório (PDF)</button></a>'

col_cli = ['id','nome','cpf','tel','endereco','cidade','cep','plano_km','est','emp_name','status','vei','pla','vei_2','pla_2','veiculos_lista']
col_emp = ['cnpj','nome','responsavel','telefone','email','est','status']
col_pre = ['id','nome','cpf','tipo','telefone','endereco','cidade','cep','est','status','homologado','senha','frota']
col_os = ['id','data_hora','cliente_id','cliente_nome','placa','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os','veiculo_desc','plano_km','valor_cobrado']

if not os.path.exists(FILE_CLIENTES): pd.DataFrame(columns=col_cli).to_csv(FILE_CLIENTES, index=False)
if not os.path.exists(FILE_EMPRESAS): pd.DataFrame(columns=col_emp).to_csv(FILE_EMPRESAS, index=False)
if not os.path.exists(FILE_PRESTADORES): pd.DataFrame(columns=col_pre).to_csv(FILE_PRESTADORES, index=False)
if not os.path.exists(FILE_OS): pd.DataFrame(columns=col_os).to_csv(FILE_OS, index=False)

df_clientes = carregar_dados(FILE_CLIENTES, col_cli)
df_empresas = carregar_dados(FILE_EMPRESAS, col_emp)
df_prestadores = carregar_dados(FILE_PRESTADORES, col_pre)
df_os = carregar_dados(FILE_OS, col_os)

# ===================================================================================
# LOGIN
# ===================================================================================
if "logado" not in st.session_state:
    st.session_state.update({"logado": False, "user": "", "perfil": "", "empresa_vinculada": ""})

if not st.session_state.logado:
    sess_param = st.query_params.get("session")
    if sess_param == "admin_ad": st.session_state.update({"logado": True, "user": "AD Rastreamento Veicular (ADMIN)", "perfil": "Admin"})
    elif sess_param and sess_param.startswith("parc_"):
        nome_parc = urllib.parse.unquote(sess_param.split("parc_")[1])
        st.session_state.update({"logado": True, "user": nome_parc.upper(), "perfil": "Parceiro", "empresa_vinculada": nome_parc})

if not st.session_state.logado:
    st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">⚡ Operação Atendimento</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        usuario_input = apenas_numeros_letras(st.text_input("Usuário (Empresa):"))
        senha_input = apenas_numeros_letras(st.text_input("Senha (CNPJ):", type="password"))
        if st.button("Entrar no Sistema", use_container_width=True):
            if usuario_input == "adrastreamentoveicular" and senha_input == "00000000000000":
                st.session_state.update({"logado": True, "user": "AD Rastreamento Veicular (ADMIN)", "perfil": "Admin"})
                st.query_params["session"] = "admin_ad"
                time.sleep(0.5); st.rerun()
            else:
                if not df_empresas.empty:
                    df_empresas_login = df_empresas.copy()
                    df_empresas_login['cnpj_comparar'] = df_empresas_login['cnpj'].apply(apenas_numeros_letras)
                    df_empresas_login['nome_comparar'] = df_empresas_login['nome'].apply(apenas_numeros_letras)
                    parceiro_valid = df_empresas_login[(df_empresas_login['cnpj_comparar'] == senha_input) & (df_empresas_login['nome_comparar'] == usuario_input)]
                    if not parceiro_valid.empty:
                        st.session_state.update({"logado": True, "user": parceiro_valid.iloc[0]['nome'].upper(), "perfil": "Parceiro", "empresa_vinculada": parceiro_valid.iloc[0]['nome']})
                        st.query_params["session"] = f"parc_{urllib.parse.quote(parceiro_valid.iloc[0]['nome'])}"
                        time.sleep(0.5); st.rerun()
                    else: st.error("Usuário ou senha incorretos.")
                else: st.error("Usuário ou senha incorretos.")
    st.stop()

col_user, col_logout = st.columns([5, 1])
with col_user: st.write(f"**Central AD 24h | Operador:** `{st.session_state.user}`")
with col_logout:
    if st.button("Sair / Logoff"):
        st.session_state.logado = False
        st.query_params.clear()
        st.rerun()

# ===================================================================================
# TELA ADMIN MASTER
# ===================================================================================
if st.session_state.perfil == "Admin":
    menu = st.tabs(["📋 Nova OS", "📊 Relatórios & PDF", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores", "💾 Segurança & Backup"])
    
    # === NOVA OS ===
    with menu[0]:
        st.subheader("🚀 Abertura de Chamado / Nova OS")
        
        tipo_atendimento = st.radio("Tipo de Atendimento:", ["Cliente Cadastrado", "Atendimento Avulso (Particular)"], horizontal=True)
        st.write("---")
        
        if "os_busca_val" not in st.session_state: st.session_state.os_busca_val = ""
        if "os_cli_val" not in st.session_state: st.session_state.os_cli_val = ""
        if "os_loc_val" not in st.session_state: st.session_state.os_loc_val = ""
        if "os_dest_val" not in st.session_state: st.session_state.os_dest_val = ""
        if "os_obs_val" not in st.session_state: st.session_state.os_obs_val = ""

        pronto_para_prosseguir = False
        cliente_id_os = ""
        cliente_nome_os = ""
        placa_alvo = ""
        veiculo_desc_alvo = ""
        empresa_os = ""
        plano_km_os = ""
        uf_cliente = "RN"
        cidade_cliente = ""
        valor_cobrado_os = "0,00"

        if tipo_atendimento == "Cliente Cadastrado":
            if df_clientes.empty:
                st.warning("Nenhum cliente cadastrado no sistema para busca.")
            else:
                busca = st.text_input("Digite o Nome, Placa ou CPF do cliente para buscar:", value=st.session_state.os_busca_val)
                st.session_state.os_busca_val = busca
                
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
                        opcoes_cli_os = {"": "Selecione um cliente..."}
                        for _, r in df_filtrado_cli.iterrows():
                            opcoes_cli_os[str(r['id'])] = f"{str(r['nome']).upper()} | Empresa: {str(r['emp_name']).upper()}"
                        
                        idx_cli_os = list(opcoes_cli_os.keys()).index(st.session_state.os_cli_val) if st.session_state.os_cli_val in opcoes_cli_os else 0
                        c_target_os = st.selectbox("Selecione o Cliente:", options=list(opcoes_cli_os.keys()), format_func=lambda x: opcoes_cli_os[x], index=idx_cli_os)
                        st.session_state.os_cli_val = c_target_os
                        
                        if c_target_os != "":
                            cliente_dados = df_clientes[df_clientes['id'].astype(str) == c_target_os].iloc[0]
                            lista_frota_opcoes = []
                            if pd.notna(cliente_dados.get('veiculos_lista')) and cliente_dados['veiculos_lista']:
                                try:
                                    frota_json = json.loads(cliente_dados['veiculos_lista'])
                                    for v in frota_json:
                                        if v.get('Placa'): lista_frota_opcoes.append(f"{v.get('Modelo/Ano', 'Veículo')} - Placa: {v.get('Placa')}")
                                except: pass 
                            
                            if not lista_frota_opcoes:
                                if pd.notna(cliente_dados.get('pla')) and str(cliente_dados['pla']).strip(): lista_frota_opcoes.append(f"{cliente_dados.get('vei', 'Veículo')} - Placa: {cliente_dados['pla']}")
                                if pd.notna(cliente_dados.get('pla_2')) and str(cliente_dados['pla_2']).strip(): lista_frota_opcoes.append(f"{cliente_dados.get('vei_2', 'Veículo')} - Placa: {cliente_dados['pla_2']}")
                            
                            if not lista_frota_opcoes: st.error("Este cliente não possui veículos cadastrados com placa válida.")
                            else:
                                veiculo_sel_os = st.selectbox("Selecione qual Veículo da frota será atendido:", lista_frota_opcoes)
                                placa_alvo = veiculo_sel_os.split("Placa: ")[1].strip().upper()
                                veiculo_desc_alvo = veiculo_sel_os.split(" - Placa:")[0].strip()
                                uf_cliente = str(cliente_dados['est']).strip().upper() if cliente_dados['est'] else "RN"
                                plano_km_os = str(cliente_dados.get('plano_km', 'N/D'))
                                cidade_cliente = str(cliente_dados.get('cidade', '')).strip().upper()
                                cliente_id_os = str(c_target_os)
                                cliente_nome_os = str(cliente_dados['nome'])
                                empresa_os = str(cliente_dados['emp_name'])
                                valor_cobrado_os = "0,00"

                                st.info(f"📍 Cliente: **{empresa_os.upper()}** | UF do Veículo: **{uf_cliente}**")
                                st.markdown(f'<div class="info-box">🛣️ PLANO KM CONTRATADO: {plano_km_os}</div>', unsafe_allow_html=True)

                                if not df_os.empty and 'placa' in df_os.columns:
                                    df_os_copy = df_os.copy()
                                    df_os_copy['data_hora'] = pd.to_datetime(df_os_copy['data_hora'], errors='coerce')
                                    os_hist = df_os_copy[df_os_copy['placa'].astype(str).str.upper() == placa_alvo]
                                    if not os_hist.empty:
                                        ultima_data = os_hist['data_hora'].max()
                                        if pd.notna(ultima_data):
                                            dias_passados = (datetime.now() - ultima_data).days
                                            if dias_passados < 60: st.markdown(f'<div class="alert-box alert-danger">⚠️ ATENÇÃO: Último acionamento da placa {placa_alvo} foi há {dias_passados} dias (Data: {ultima_data.strftime("%d/%m/%Y")}). Cliente sujeito à restrição contratual dos 60 dias.</div>', unsafe_allow_html=True)
                                            else: st.markdown(f'<div class="alert-box alert-success">✅ VIGÊNCIA LIBERADA: Último uso há {dias_passados} dias (Mais de 60 dias).</div>', unsafe_allow_html=True)

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
                                        elif "borrach" in serv or "borrac" in serv: total_b += 1
                                
                                st.markdown(f"#### 📊 Saldo de Acionamentos no Ano ({ano_atual}) - Placa: {placa_alvo}")
                                c1, c2, c3, c4, c5 = st.columns(5)
                                c1.metric("Guinchos", f"{total_g} / 2"); c2.metric("Pane Seca", f"{total_ps} / 1"); c3.metric("Elétrica", f"{total_pe} / 1"); c4.metric("Chaveiro", f"{total_c} / 1"); c5.metric("Borracheiro", f"{total_b} / 1")
                                
                                status_cliente_os = str(cliente_dados.get('status', 'Ativo')).strip()
                                if status_cliente_os == 'Inativo':
                                    st.write("---")
                                    st.markdown('<div class="alert-box alert-danger" style="font-size: 16px; text-align: center;">🚫 ALERTA VERMELHO: CLIENTE INATIVO 🚫<br><span style="font-size: 14px; font-weight: normal;">Possível inadimplência ou cancelamento. O atendimento padrão está bloqueado.</span></div>', unsafe_allow_html=True)
                                    liberar_excecao = st.checkbox("⚠️ Ciente do status: Liberar Atendimento por Exceção (Autorização manual)")
                                    if liberar_excecao: pronto_para_prosseguir = True
                                    else:
                                        pronto_para_prosseguir = False
                                        st.warning("👆 Marque a caixa acima se desejar abrir uma OS para este cliente inativo.")
                                else: pronto_para_prosseguir = True
        
        else:
            st.info("📝 Digite as informações do atendimento avulso particular abaixo:")
            col_av1, col_av2 = st.columns(2)
            nome_avulso = col_av1.text_input("Nome Completo do Cliente:")
            tel_avulso = col_av2.text_input("Telefone de Contato:")
            veiculo_avulso = col_av1.text_input("Veículo (Modelo/Ano/Cor):")
            placa_avulso = col_av2.text_input("Placa do Veículo:")
            uf_cliente = col_av1.selectbox("Estado (UF) do Atendimento:", options=ESTADOS_BR, index=ESTADOS_BR.index("RN"))
            cidade_cliente = col_av2.text_input("Cidade do Atendimento:")
            valor_cobrado_os = col_av1.text_input("Valor Cobrado do Particular (R$):", value="0,00")
            
            cliente_id_os = "AVULSO"
            cliente_nome_os = nome_avulso
            placa_alvo = placa_avulso.upper().strip()
            veiculo_desc_alvo = veiculo_avulso
            empresa_os = "CLIENTE PARTICULAR (AVULSO)"
            plano_km_os = "Particular"
            
            if nome_avulso and placa_alvo: pronto_para_prosseguir = True
            else: st.warning("⚠️ Nome do Cliente e Placa são obrigatórios para liberar o atendimento avulso.")

        if pronto_para_prosseguir:
            st.write("---")
            st.subheader("🛠️ Detalhes da Assistência e Acionamento")
            tipo_servico = st.selectbox("Tipo de Serviço:", ["Guincho", "Pane Seca", "Pane Elétrica", "Borracheiro", "Chaveiro"])
            motivo_servico = st.selectbox("Motivo do Acionamento:", ["Acidente", "Furto", "Roubo", "Outros"])
            
            lista_p_ops = ["Outro (Digitar Manualmente)"]
            if not df_prestadores.empty:
                df_prest_filtrados = df_prestadores[(df_prestadores['est'].str.strip().str.upper() == uf_cliente.upper()) & (df_prestadores['status'] == 'Ativo') & (df_prestadores['homologado'] == 'Aprovado')].copy()
                if not df_prest_filtrados.empty:
                    cidade_busca = cidade_cliente.strip().upper()
                    df_prest_filtrados['prioridade'] = df_prest_filtrados['cidade'].apply(lambda x: 0 if str(x).strip().upper() == cidade_busca and cidade_busca != "" else 1)
                    df_prest_filtrados = df_prest_filtrados.sort_values(by=['prioridade', 'nome'])
                    for _, r in df_prest_filtrados.iterrows():
                        marcador = "📍 [MAIS PRÓXIMO] " if r['prioridade'] == 0 else ""
                        lista_p_ops.append(f"{marcador}{str(r['nome'])} - Tel: {str(r['telefone'])} - {str(r['cidade']).upper()}/{str(r['est']).upper()}")
                else:
                    df_aprovados = df_prestadores[df_prestadores['homologado'] == 'Aprovado']
                    for _, r in df_aprovados.iterrows(): lista_p_ops.append(f"{str(r['nome'])} - Tel: {str(r['telefone'])} - {str(r['cidade']).upper()}/{str(r['est']).upper()}")
            
            prestador_sel = st.selectbox("Prestadores homologados (Ordenados por proximidade):", lista_p_ops)
            if prestador_sel == "Outro (Digitar Manualmente)":
                prestador_final = st.text_input("Nome do Prestador Manual:")
                tel_prestador_final = apenas_numeros_letras(st.text_input("Telefone do Prestador Manual (DDD + Número):"))
            else:
                prestador_limpo = prestador_sel.replace("📍 [MAIS PRÓXIMO] ", "")
                prestador_final = prestador_limpo.split(" - Tel:")[0]
                tel_prestador_final = apenas_numeros_letras(prestador_limpo.split(" - Tel:")[1].split("-")[0].strip())
            
            localizacao = st.text_input("Endereço de Origem (Localização atual):", value=st.session_state.os_loc_val)
            st.session_state.os_loc_val = localizacao
            destino = st.text_input("Endereço de Destino:", value=st.session_state.os_dest_val)
            st.session_state.os_dest_val = destino
            obs = st.text_area("Observações:", value=st.session_state.os_obs_val)
            st.session_state.os_obs_val = obs
            
            if st.button("🚀 Iniciar Atendimento / Gerar OS"):
                if not prestador_final or not tel_prestador_final: st.error("Identifique o Nome e o Telefone do prestador.")
                else:
                    nova_id = int(df_os['id'].astype(float).max() + 1) if not df_os.empty else 1
                    nova_os = pd.DataFrame([{'id': str(nova_id), 'data_hora': obter_hora_brasilia(), 'cliente_id': str(cliente_id_os), 'cliente_nome': str(cliente_nome_os).upper(), 'placa': placa_alvo, 'veiculo_desc': str(veiculo_desc_alvo).upper(), 'empresa': empresa_os, 'tipo_servico': tipo_servico, 'motivo': motivo_servico, 'prestador': f"{prestador_final} | Telefone/Zap: {tel_prestador_final}", 'localizacao': localizacao, 'destino': destino, 'obs': obs, 'status_os': "EM ATENDIMENTO", 'plano_km': plano_km_os, 'valor_cobrado': valor_cobrado_os}])
                    df_os_temp = pd.concat([df_os, nova_os], ignore_index=True)
                    sucesso, erro = salvar_dados(df_os_temp, FILE_OS)
                    ifsucesso:
                        st.success(f"✅ Chamado Nº {nova_id} Aberto! Redirecionando...")
                        st.session_state.os_busca_val = ""
                        st.session_state.os_cli_val = ""
                        st.session_state.os_loc_val = ""
                        st.session_state.os_dest_val = ""
                        st.session_state.os_obs_val = ""
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error(f"⚠️ Erro ao salvar OS na nuvem: {erro}")

    # === RELATÓRIOS E HISTÓRICO ===
    with menu[1]:
        st.subheader("📊 Gestão de Chamados e Relatórios")
        st.write("---")
        with st.expander("⚠️ Área de Risco: Limpar Dados de Teste"):
            st.warning("Use este botão apenas na fase de implementação para apagar as OS fantasmas de testes anteriores.")
            if st.button("Zerar Histórico de Ordens de Serviço"):
                df_os_vazio = pd.DataFrame(columns=df_os.columns)
                sucesso, erro = salvar_dados(df_os_vazio, FILE_OS)
                if sucesso:
                    st.success("Banco de OS zerado! O histórico dos clientes está limpo e pronto para uso real.")
                    time.sleep(2); st.rerun()
                else:
                    st.error(f"Erro na nuvem: {erro}")
        st.write("---")
        
        if df_os.empty: st.info("Nenhuma OS registrada no sistema.")
        else:
            visao_relatorio = st.radio("Escolha a Visão:", ["🚨 OS em Andamento (Gerenciar)", "✅ Histórico e Gerar PDF (Finalizadas)", "Tabela Geral"], horizontal=True)
            if visao_relatorio == "🚨 OS em Andamento (Gerenciar)":
                st.markdown("### 🚨 Chamados Atualmente em Andamento")
                df_abertas = df_os[df_os['status_os'] == 'EM ATENDIMENTO']
                if df_abertas.empty: st.success("Nenhum chamado em andamento no momento!")
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
                    
                    texto_whatsapp = (f"*{str(row_os['empresa']).upper()} - ASSISTÊNCIA 24H*\n-----------------------------------------\n*Chamado Nº:* {row_os['id']}\n*Data/Hora:* {row_os['data_hora']}\n*Plano KM:* {row_os.get('plano_km', 'N/D')}\n*Valor Particular:* R$ {row_os.get('valor_cobrado', '0,00')}\n*Serviço:* {row_os['tipo_servico']} | *Motivo:* {row_os['motivo']}\n\n*Cliente:* {str(row_os['cliente_nome']).upper()}\n*Telefone do Cliente:* {tel_cliente_os}\n\n*Veículo:* {row_os.get('veiculo_desc', 'N/D')} - Placa: {row_os.get('placa', 'N/D')}\n\n*Origem:* {row_os['localizacao']}\n*Destino:* {row_os['destino']}\n\n*Obs:* {row_os['obs']}")
                    link_w = f"https://api.whatsapp.com/send?phone=55{tel_prestador_final}&text={urllib.parse.quote(texto_whatsapp)}"
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1: st.markdown(f'<a href="{link_w}" target="_blank"><button style="background-color: #25D366; color: white; padding: 10px 20px; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; width: 100%;">📲 Enviar OS para o Prestador</button></a>', unsafe_allow_html=True)
                    with col_btn2:
                        if st.button("🔒 Finalizar Atendimento"):
                            df_os.loc[df_os['id'].astype(str) == os_id_alvo, 'status_os'] = "ENCERRADO"
                            sucesso, erro = salvar_dados(df_os, FILE_OS)
                            if sucesso:
                                st.success(f"🎉 Chamado Nº {os_id_alvo} Finalizado! Ele foi movido para o Histórico (PDF).")
                                time.sleep(1.5); st.rerun()
                            else:
                                st.error(f"Erro na nuvem: {erro}")

            elif visao_relatorio == "✅ Histórico e Gerar PDF (Finalizadas)":
                st.markdown("### 📄 Localizar OS Finalizada (Por Placa ou Nome)")
                df_fechadas = df_os[df_os['status_os'] == 'ENCERRADO'].sort_values(by='id', ascending=False)
                if df_fechadas.empty: st.info("Nenhum chamado foi finalizado ainda.")
                else:
                    busca_os_relatorio = st.text_input("Digite a Placa do veículo ou o Nome para encontrar o relatório:")
                    if busca_os_relatorio:
                        df_filtrado_fechadas = df_fechadas[df_fechadas['cliente_nome'].str.contains(busca_os_relatorio, case=False, na=False) | df_fechadas['placa'].str.contains(busca_os_relatorio, case=False, na=False)]
                        if df_filtrado_fechadas.empty: st.warning("Nenhum acionamento finalizado encontrado para essa placa ou nome.")
                        else:
                            lista_os_dele = [f"Chamado Nº: {r['id']} | Placa: {r.get('placa', 'N/D')} | Data: {r['data_hora']} | Serviço: {r['tipo_servico']}" for _, r in df_filtrado_fechadas.iterrows()]
                            os_escolhida_str = st.selectbox("Selecione qual acionamento deseja gerar o PDF:", options=lista_os_dele)
                            os_alvo_id = os_escolhida_str.split("|")[0].replace("Chamado Nº:", "").strip()
                            df_os_unica = df_os[df_os['id'].astype(str) == os_alvo_id]
                            st.write("---")
                            st.success("✅ Chamado Finalizado. Baixe o relatório abaixo:")
                            st.markdown(exportar_pdf_html_oficial(df_os_unica, df_clientes, f"relatorio_os_{os_alvo_id}"), unsafe_allow_html=True)
                    else: st.info("👆 Digite a Placa ou Nome acima para exibir as opções de download.")

            else:
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    empresas_ativas = [str(e).upper() for e in df_empresas['nome'].unique()] if not df_empresas.empty else []
                    emp_escolhida = st.selectbox("Filtrar por Empresa:", options=["TODAS"] + empresas_ativas)
                with col_f2: cli_escolhido = st.text_input("Filtrar Tabela por Nome ou Placa:")
                df_os_filtrada = df_os.copy()
                if emp_escolhida != "TODAS": df_os_filtrada = df_os_filtrada[df_os_filtrada['empresa'].str.upper() == emp_escolhida]
                if cli_escolhido: df_os_filtrada = df_os_filtrada[df_os_filtrada['cliente_nome'].str.contains(cli_escolhido, case=False, na=False) | df_os_filtrada['placa'].str.contains(cli_escolhido, case=False, na=False)]
                st.write("---")
                st.dataframe(df_os_filtrada, use_container_width=True)

    # === CLIENTES ===
    with menu[2]:
        st.subheader("👤 Gerenciamento de Clientes (Frota Ilimitada e Endereço)")
        
        if "aba_cli" not in st.session_state: st.session_state.aba_cli = "Listar"
        opcoes_radio = ["Listar", "Incluir Novo", "Importação em Lote", "Editar", "Excluir"]
        idx_radio = opcoes_radio.index(st.session_state.aba_cli) if st.session_state.aba_cli in opcoes_radio else 0
        opcao_cli = st.radio("Ação Clientes:", opcoes_radio, horizontal=True, index=idx_radio)
        st.session_state.aba_cli = opcao_cli
        
        if opcao_cli == "Listar":
            busca_cli_lista = st.text_input("🔍 Buscar Cliente na Lista (Nome, Placa ou CPF):")
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
                        except: d_str = str(r['data_hora'])[:10]
                        res.append(f"{r['tipo_servico']} ({d_str})")
                    return " | ".join(res)
                
                df_view_cli['Histórico'] = df_view_cli['id'].apply(formatar_historico)
                empresas_na_lista = df_view_cli['emp_name'].unique()
                if len(empresas_na_lista) == 0: st.warning("Nenhum cliente encontrado com esse termo.")
                else:
                    for emp in empresas_na_lista:
                        nome_emp = str(emp).upper() if pd.notna(emp) and str(emp).strip() != "" else "SEM EMPRESA VINCULADA"
                        with st.expander(f"📁 Clientes da Empresa: {nome_emp}", expanded=expandir_pastas):
                            df_emp_filtrada = df_view_cli[df_view_cli['emp_name'] == emp]
                            
                            mes_a = datetime.now().month
                            ano_a = datetime.now().year
                            total_os_mes_emp = 0
                            if not df_os.empty:
                                df_os_temp = df_os.copy()
                                df_os_temp['data_hora'] = pd.to_datetime(df_os_temp['data_hora'], errors='coerce')
                                os_mes_atual = df_os_temp[(df_os_temp['empresa'].str.upper() == nome_emp) & (df_os_temp['data_hora'].dt.month == mes_a) & (df_os_temp['data_hora'].dt.year == ano_a)]
                                total_os_mes_emp = len(os_mes_atual)
                            
                            taxa = (total_os_mes_emp / len(df_emp_filtrada) * 100) if len(df_emp_filtrada) > 0 else 0
                            st.markdown(f"📊 **De acordo com a base de {len(df_emp_filtrada)} clientes/veículos, a taxa de acionamento neste mês é de {taxa:.1f}%.**")
                            
                            st.dataframe(df_emp_filtrada[['nome','cpf','tel','cidade','plano_km','Histórico','status']].style.map(colorir_status, subset=['status']), use_container_width=True)
                            
                            st.markdown("---")
                            key_sel_admin = f"sel_det_{emp}"
                            widget_key_admin = f"sel_sb_{emp}"
                            if key_sel_admin not in st.session_state: st.session_state[key_sel_admin] = ""
                            cli_opcoes = [""] + df_emp_filtrada['nome'].tolist()
                            idx_sel_admin = cli_opcoes.index(st.session_state[key_sel_admin]) if st.session_state[key_sel_admin] in cli_opcoes else 0
                            cli_sel = st.selectbox(f"🔍 Selecione um cliente da {nome_emp} para ver a Ficha Completa:", cli_opcoes, index=idx_sel_admin, key=widget_key_admin)
                            st.session_state[key_sel_admin] = cli_sel
                            
                            if cli_sel != "":
                                cli_data = df_emp_filtrada[df_emp_filtrada['nome'] == cli_sel].iloc[0]
                                st.markdown(f"### 📋 Ficha do Cliente: {cli_data['nome']}")
                                c1, c2 = st.columns(2)
                                c1.write(f"**CPF/CNPJ:** {cli_data['cpf']}"); c1.write(f"**Telefone:** {cli_data['tel']}"); c1.write(f"**Plano Contratado:** {cli_data.get('plano_km', 'N/D')}")
                                c2.write(f"**Endereço:** {cli_data.get('endereco', 'N/D')} - {cli_data.get('cidade', 'N/D')}/{cli_data.get('est', 'N/D')}"); c2.write(f"**Status:** {'🟢 Ativo' if cli_data['status'] == 'Ativo' else '🔴 Inativo'}")
                                st.write("**🚗 Frota Cadastrada:**")
                                try:
                                    frota = json.loads(cli_data['veiculos_lista'])
                                    st.table(pd.DataFrame(frota))
                                except: st.write(f"{cli_data.get('vei', '')} - Placa: {cli_data.get('pla', '')}")
                                st.write("---")
                                st.write(f"**📊 Saldo de Acionamentos no Ano ({datetime.now().year}) - Geral do Cliente:**")
                                ano_atual = datetime.now().year
                                total_g, total_ps, total_pe, total_b, total_c = 0, 0, 0, 0, 0
                                if not df_os.empty:
                                    df_os_copy = df_os.copy()
                                    df_os_copy['data_hora'] = pd.to_datetime(df_os_copy['data_hora'], errors='coerce')
                                    os_cliente_ano = df_os_copy[(df_os_copy['cliente_id'].astype(str).str.strip() == str(cli_data['id']).strip()) & (df_os_copy['data_hora'].dt.year == ano_atual)]
                                    for _, o in os_cliente_ano.iterrows():
                                        serv = str(o['tipo_servico']).lower()
                                        if "guincho" in serv: total_g += 1
                                        elif "seca" in serv: total_ps += 1
                                        elif "elét" in serv or "elet" in serv: total_pe += 1
                                        elif "chaveiro" in serv: total_c += 1
                                        elif "borrach" in serv or "borrac" in serv: total_b += 1
                                col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
                                col_m1.metric("Guinchos", f"{total_g} / 2"); col_m2.metric("Pane Seca", f"{total_ps} / 1"); col_m3.metric("Elétrica", f"{total_pe} / 1"); col_m4.metric("Chaveiro", f"{total_c} / 1"); col_m5.metric("Borracheiro", f"{total_b} / 1")
                                st.write("---")
                                st.write("**🚨 Histórico Completo de Atendimentos:**")
                                if df_os.empty: st.info("Nenhum acionamento.")
                                else:
                                    os_cli = df_os[df_os['cliente_id'].astype(str).str.strip() == str(cli_data['id']).strip()]
                                    if os_cli.empty: st.info("Nenhum acionamento.")
                                    else: st.dataframe(os_cli[['data_hora', 'tipo_servico', 'placa', 'prestador', 'status_os']], use_container_width=True)
                                if st.button("❌ Fechar Ficha do Cliente", key=f"btn_close_{emp}"):
                                    st.session_state[key_sel_admin] = ""
                                    if widget_key_admin in st.session_state: del st.session_state[widget_key_admin]
                                    st.rerun()

        elif opcao_cli == "Incluir Novo":
            if "cli_inc_nome" not in st.session_state: st.session_state.cli_inc_nome = ""
            if "cli_inc_cpf" not in st.session_state: st.session_state.cli_inc_cpf = ""
            if "cli_inc_tel" not in st.session_state: st.session_state.cli_inc_tel = ""
            if "cli_inc_end" not in st.session_state: st.session_state.cli_inc_end = ""
            if "cli_inc_cid" not in st.session_state: st.session_state.cli_inc_cid = ""
            if "cli_inc_cep" not in st.session_state: st.session_state.cli_inc_cep = ""

            st.info("✏️ Preencha os dados abaixo para cadastrar um novo cliente.")
            c1, c2 = st.columns(2)
            nome_in = c1.text_input("Nome Completo:", value=st.session_state.cli_inc_nome)
            st.session_state.cli_inc_nome = nome_in
            cpf_raw = c2.text_input("CPF/CNPJ:", value=st.session_state.cli_inc_cpf)
            st.session_state.cli_inc_cpf = cpf_raw
            tel_raw = c1.text_input("Telefone de Contato:", value=st.session_state.cli_inc_tel)
            st.session_state.cli_inc_tel = tel_raw
            end_in = c2.text_input("Endereço Completo:", value=st.session_state.cli_inc_end)
            st.session_state.cli_inc_end = end_in
            cid_in = c1.text_input("Cidade:", value=st.session_state.cli_inc_cid)
            st.session_state.cli_inc_cid = cid_in
            cep_in = c2.text_input("CEP:", value=st.session_state.cli_inc_cep)
            st.session_state.cli_inc_cep = cep_in
            
            st.write("---")
            st.write("🚗 **Frota do Cliente (Tabela Interativa - Adicione quantos quiser)**")
            df_frota_editavel = pd.DataFrame([{"Modelo/Ano": "", "Placa": ""}])
            frota_editada = st.data_editor(df_frota_editavel, num_rows="dynamic", use_container_width=True)
            st.write("---")
            
            col_b1, col_b2, col_b3 = st.columns(3)
            est = col_b1.selectbox("Estado (UF) do Veículo:", options=ESTADOS_BR, index=ESTADOS_BR.index("RN"))
            plano_km = col_b2.selectbox("Plano Contratado (KM):", options=PLANOS_KM, index=0)
            status = col_b3.selectbox("Status do Cliente:", ["Ativo", "Inativo"], index=0)
            
            lista_empresas_disponiveis = [str(e['nome']).upper() for _, e in df_empresas.iterrows()] if not df_empresas.empty else ["NENHUMA EMPRESA CADASTRADA"]
            emp = st.selectbox("Empresa Vinculada / Parceira:", options=lista_empresas_disponiveis, index=0)
            
            if st.button("Salvar Novo Cliente"):
                nome, cpf, tel = nome_in.upper(), apenas_numeros_letras(cpf_raw), apenas_numeros_letras(tel_raw)
                frota_limpa = frota_editada.dropna(how='all')
                frota_limpa['Placa'] = frota_limpa['Placa'].astype(str).str.upper().str.replace("-","").str.replace(" ","")
                frota_json_str = json.dumps(frota_limpa.to_dict('records'))
                vei_prin = frota_limpa.iloc[0]['Modelo/Ano'] if not frota_limpa.empty else ""
                pla_prin = frota_limpa.iloc[0]['Placa'] if not frota_limpa.empty else ""
                
                if not nome or not pla_prin: st.error("Nome e ao menos 1 Placa de Veículo são obrigatórios.")
                else:
                    prox = int(df_clientes['id'].astype(float).max() + 1) if not df_clientes.empty else 1
                    novo = pd.DataFrame([{'id': str(prox), 'nome': nome, 'cpf': cpf, 'tel': tel, 'endereco': end_in, 'cidade': cid_in.upper(), 'cep': cep_in, 'plano_km': plano_km, 'vei': vei_prin, 'pla': pla_prin, 'est': est, 'emp_name': emp.upper(), 'status': status, 'veiculos_lista': frota_json_str}])
                    df_clientes_temp = pd.concat([df_clientes, novo], ignore_index=True)
                    sucesso, erro = salvar_dados(df_clientes_temp, FILE_CLIENTES)
                    if sucesso:
                        st.success("✅ Cliente cadastrado com sucesso!")
                        for k in ["cli_inc_nome", "cli_inc_cpf", "cli_inc_tel", "cli_inc_end", "cli_inc_cid", "cli_inc_cep"]: st.session_state[k] = ""
                        st.session_state.aba_cli = "Listar"
                        time.sleep(1); st.rerun()
                    else:
                        st.error(f"⚠️ Erro ao salvar cliente na nuvem: {erro}")
                        gerar_botao_whatsapp({"Ação": "Admin Cadastrando Cliente", "Nome": nome, "CPF": cpf, "Empresa": emp})
                        
        elif opcao_cli == "Importação em Lote":
            st.info("📥 Faça o upload da planilha padrão em formato .csv para importar múltiplos veículos de uma vez. O sistema fará a vinculação automática de todos eles à empresa que você escolher.")
            
            lista_empresas_disponiveis = [str(e['nome']).upper() for _, e in df_empresas.iterrows()] if not df_empresas.empty else ["NENHUMA EMPRESA CADASTRADA"]
            empresa_selecionada = st.selectbox("Selecione a Empresa Vinculada para esta importação:", options=lista_empresas_disponiveis)
            
            arquivo_csv_upload = st.file_uploader("Selecione o arquivo CSV da frota do parceiro", type=["csv"])
            
            if arquivo_csv_upload is not None:
                if st.button("Iniciar Importação e Salvar no GitHub"):
                    with st.spinner(f"Processando frota para a empresa {empresa_selecionada}..."):
                        sucesso, mensagem = importar_clientes_csv(arquivo_csv_upload, empresa_selecionada, df_clientes)
                        if sucesso:
                            st.success(mensagem)
                            st.balloons()
                            time.sleep(2)
                            st.session_state.aba_cli = "Listar"
                            st.rerun()
                        else:
                            st.error(mensagem)
                    
        elif opcao_cli == "Editar":
            if df_clientes.empty: st.warning("Nenhum cliente cadastrado.")
            else:
                opcoes_cli = {str(r['id']): f"{str(r['nome']).upper()} | CPF: {str(r['cpf'])} | Empresa: {str(r['emp_name']).upper()}" for _, r in df_clientes.iterrows()}
                c_target = st.selectbox("🔎 Digite para achar o cliente (Nome, CPF ou Empresa):", options=[""] + list(opcoes_cli.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_cli[x])
                if c_target != "":
                    dados_ant = df_clientes[df_clientes['id'].astype(str) == c_target].iloc[0]
                    c1, c2 = st.columns(2)
                    nome_in = c1.text_input("Nome Completo:", value=dados_ant['nome'])
                    cpf_raw = c2.text_input("CPF/CNPJ:", value=dados_ant['cpf'])
                    tel_raw = c1.text_input("Telefone de Contato:", value=dados_ant['tel'])
                    end_in = c2.text_input("Endereço Completo:", value=dados_ant.get('endereco', ''))
                    cid_in = c1.text_input("Cidade:", value=dados_ant.get('cidade', ''))
                    cep_in = c2.text_input("CEP:", value=dados_ant.get('cep', ''))
                    
                    st.write("---")
                    st.write("🚗 **Frota do Cliente**")
                    frota_inicial = []
                    if pd.notna(dados_ant.get('veiculos_lista')) and dados_ant['veiculos_lista']:
                        try: frota_inicial = json.loads(dados_ant['veiculos_lista'])
                        except: pass
                    if not frota_inicial:
                        if pd.notna(dados_ant.get('vei')) and dados_ant['vei'] != 'nan': frota_inicial.append({"Modelo/Ano": dados_ant['vei'], "Placa": str(dados_ant['pla']).upper()})
                        if pd.notna(dados_ant.get('vei_2')) and dados_ant['vei_2'] != 'nan' and dados_ant['vei_2']: frota_inicial.append({"Modelo/Ano": dados_ant['vei_2'], "Placa": str(dados_ant['pla_2']).upper()})
                    if not frota_inicial: frota_inicial = [{"Modelo/Ano": "", "Placa": ""}]
                    frota_editada = st.data_editor(pd.DataFrame(frota_inicial), num_rows="dynamic", use_container_width=True)
                    st.write("---")
                    
                    col_b1, col_b2, col_b3 = st.columns(3)
                    idx_est_c = ESTADOS_BR.index(str(dados_ant['est']).upper()) if str(dados_ant['est']).upper() in ESTADOS_BR else ESTADOS_BR.index("RN")
                    est = col_b1.selectbox("Estado (UF) do Veículo:", options=ESTADOS_BR, index=idx_est_c)
                    idx_plano = PLANOS_KM.index(str(dados_ant.get('plano_km', 'Sem Limite'))) if str(dados_ant.get('plano_km', 'Sem Limite')) in PLANOS_KM else 0
                    plano_km = col_b2.selectbox("Plano Contratado (KM):", options=PLANOS_KM, index=idx_plano)
                    status = col_b3.selectbox("Status do Cliente:", ["Ativo", "Inativo"], index=["Ativo", "Inativo"].index(str(dados_ant['status'])))
                    
                    lista_empresas_disponiveis = [str(e['nome']).upper() for _, e in df_empresas.iterrows()] if not df_empresas.empty else ["NENHUMA EMPRESA CADASTRADA"]
                    idx_emp = lista_empresas_disponiveis.index(str(dados_ant['emp_name']).upper()) if str(dados_ant['emp_name']).upper() in lista_empresas_disponiveis else 0
                    emp = st.selectbox("Empresa Vinculada / Parceira:", options=lista_empresas_disponiveis, index=idx_emp)
                    
                    if st.button("Salvar Alterações"):
                        nome, cpf, tel = nome_in.upper(), apenas_numeros_letras(cpf_raw), apenas_numeros_letras(tel_raw)
                        frota_limpa = frota_editada.dropna(how='all')
                        frota_limpa['Placa'] = frota_limpa['Placa'].astype(str).str.upper().str.replace("-","").str.replace(" ","")
                        frota_json_str = json.dumps(frota_limpa.to_dict('records'))
                        vei_prin = frota_limpa.iloc[0]['Modelo/Ano'] if not frota_limpa.empty else ""
                        pla_prin = frota_limpa.iloc[0]['Placa'] if not frota_limpa.empty else ""
                        
                        if not nome or not pla_prin: st.error("Nome e ao menos 1 Placa de Veículo são obrigatórios.")
                        else:
                            df_clientes.loc[df_clientes['id'].astype(str) == c_target, ['nome','cpf','tel','endereco','cidade','cep','plano_km','vei','pla','est','emp_name','status','veiculos_lista']] = [nome, cpf, tel, end_in, cid_in.upper(), cep_in, plano_km, vei_prin, pla_prin, est, emp.upper(), status, frota_json_str]
                            sucesso, erro = salvar_dados(df_clientes, FILE_CLIENTES)
                            if sucesso:
                                st.success("✅ Alterações salvas com sucesso!")
                                st.session_state.aba_cli = "Listar"
                                time.sleep(1); st.rerun()
                            else:
                                st.error(f"⚠️ Erro ao salvar edição na nuvem: {erro}")
                                gerar_botao_whatsapp({"Ação": "Admin Editando Cliente", "Nome": nome})

        elif opcao_cli == "Excluir":
            if df_clientes.empty: st.warning("Nenhum cliente cadastrado.")
            else:
                opcoes_cli = {str(r['id']): f"{str(r['nome']).upper()} | CPF: {str(r['cpf'])} | Empresa: {str(r['emp_name']).upper()}" for _, r in df_clientes.iterrows()}
                c_target_del = st.selectbox("🔎 Selecione o Cliente para EXCLUIR:", options=[""] + list(opcoes_cli.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_cli[x])
                if c_target_del != "":
                    st.error(f"⚠️ Atenção: Você está prestes a excluir permanentemente o cliente **{opcoes_cli[c_target_del]}**.")
                    if st.button("❌ Confirmar Exclusão"):
                        df_clientes = df_clientes[df_clientes['id'].astype(str) != c_target_del]
                        sucesso, erro = salvar_dados(df_clientes, FILE_CLIENTES)
                        if sucesso:
                            st.success("🗑️ Cliente excluído permanentemente!")
                            st.session_state.aba_cli = "Listar"
                            time.sleep(1); st.rerun()
                        else: st.error(f"Falha na nuvem: {erro}")

    # === EMPRESAS ===
    with menu[3]:
        st.subheader("🏢 Gerenciamento de Empresas Parceiras")
        
        if "aba_emp" not in st.session_state: st.session_state.aba_emp = "Listar"
        opcoes_radio_emp = ["Listar", "Incluir Nova", "Editar", "Excluir"]
        idx_radio_emp = opcoes_radio_emp.index(st.session_state.aba_emp) if st.session_state.aba_emp in opcoes_radio_emp else 0
        opcao_emp = st.radio("Ação Empresas:", opcoes_radio_emp, horizontal=True, index=idx_radio_emp)
        st.session_state.aba_emp = opcao_emp
        
        if opcao_emp == "Listar":
            busca_emp_lista = st.text_input("🔍 Buscar Empresa na Lista (Nome ou CNPJ):")
            if df_empresas.empty: st.info("Nenhuma empresa cadastrada.")
            else: 
                df_view_emp = df_empresas.copy()
                if busca_emp_lista: df_view_emp = df_view_emp[df_view_emp['nome'].str.contains(busca_emp_lista, case=False, na=False) | df_view_emp['cnpj'].str.contains(busca_emp_lista, case=False, na=False)]
                st.dataframe(df_view_emp.style.map(colorir_status, subset=['status']), use_container_width=True)
        
        elif opcao_emp == "Incluir Nova":
            if "emp_inc_nome" not in st.session_state: st.session_state.emp_inc_nome = ""
            if "emp_inc_cnpj" not in st.session_state: st.session_state.emp_inc_cnpj = ""
            if "emp_inc_resp" not in st.session_state: st.session_state.emp_inc_resp = ""
            if "emp_inc_tel" not in st.session_state: st.session_state.emp_inc_tel = ""
            if "emp_inc_mail" not in st.session_state: st.session_state.emp_inc_mail = ""
            
            c1, c2 = st.columns(2)
            n_emp_in = c1.text_input("Nome da Empresa:", value=st.session_state.emp_inc_nome)
            st.session_state.emp_inc_nome = n_emp_in
            cnpj_raw = c2.text_input("CNPJ da Empresa:", value=st.session_state.emp_inc_cnpj)
            st.session_state.emp_inc_cnpj = cnpj_raw
            resp_in = c1.text_input("Nome do Responsável:", value=st.session_state.emp_inc_resp)
            st.session_state.emp_inc_resp = resp_in
            tel_e_raw = c2.text_input("Telefone da Central 24h:", value=st.session_state.emp_inc_tel)
            st.session_state.emp_inc_tel = tel_e_raw
            mail_in = c1.text_input("E-mail corporativo:", value=st.session_state.emp_inc_mail)
            st.session_state.emp_inc_mail = mail_in
            est_e = c2.selectbox("Selecione o Estado (UF) da Sede:", options=ESTADOS_BR, index=ESTADOS_BR.index("RN"))
            stat_e = c1.selectbox("Status Parceria:", ["Ativo", "Inativo"], index=0)
            
            if st.button("Salvar Nova Empresa"):
                cnpj = apenas_numeros_letras(cnpj_raw)
                if not cnpj or not n_emp_in: st.error("CNPJ e Nome da Empresa são obrigatórios.")
                else:
                    novo_e = pd.DataFrame([{'cnpj': cnpj, 'nome': n_emp_in.upper(), 'responsavel': resp_in.upper(), 'telefone': apenas_numeros_letras(tel_e_raw), 'email': mail_in, 'est': est_e, 'status': stat_e}])
                    df_empresas_temp = pd.concat([df_empresas, novo_e], ignore_index=True)
                    sucesso, erro = salvar_dados(df_empresas_temp, FILE_EMPRESAS)
                    if sucesso:
                        st.success("✅ Empresa cadastrada com sucesso!")
                        for k in ["emp_inc_nome", "emp_inc_cnpj", "emp_inc_resp", "emp_inc_tel", "emp_inc_mail"]: st.session_state[k] = ""
                        st.session_state.aba_emp = "Listar"
                        time.sleep(1); st.rerun()
                    else:
                        st.error(f"Erro na nuvem: {erro}")
                        gerar_botao_whatsapp({"Ação": "Admin Cadastrando Empresa", "Nome": n_emp_in, "CNPJ": cnpj})

        elif opcao_emp == "Editar":
            if df_empresas.empty: st.warning("Nenhuma empresa cadastrada.")
            else:
                opcoes_emp = {str(r['cnpj']): f"{str(r['nome']).upper()} | CNPJ: {str(r['cnpj'])}" for _, r in df_empresas.iterrows()}
                e_target = st.selectbox("🔎 Selecione a Empresa para Editar:", options=[""] + list(opcoes_emp.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_emp[x])
                if e_target != "":
                    dados_e_ant = df_empresas[df_empresas['cnpj'].astype(str) == e_target].iloc[0]
                    c1, c2 = st.columns(2)
                    n_emp_in = c1.text_input("Nome da Empresa:", value=dados_e_ant['nome'])
                    cnpj_raw = c2.text_input("CNPJ da Empresa:", value=dados_e_ant['cnpj'])
                    resp_in = c1.text_input("Nome do Responsável:", value=dados_e_ant['responsavel'])
                    tel_e_raw = c2.text_input("Telefone da Central 24h:", value=dados_e_ant['telefone'])
                    mail_in = c1.text_input("E-mail corporativo:", value=dados_e_ant['email'])
                    idx_est_e = ESTADOS_BR.index(str(dados_e_ant['est']).upper()) if str(dados_e_ant['est']).upper() in ESTADOS_BR else ESTADOS_BR.index("RN")
                    est_e = c2.selectbox("Selecione o Estado (UF) da Sede:", options=ESTADOS_BR, index=idx_est_e)
                    stat_e = c1.selectbox("Status Parceria:", ["Ativo", "Inativo"], index=["Ativo", "Inativo"].index(str(dados_e_ant['status'])))
                    
                    if st.button("Salvar Alterações"):
                        cnpj = apenas_numeros_letras(cnpj_raw)
                        if not cnpj or not n_emp_in: st.error("CNPJ e Nome da Empresa são obrigatórios.")
                        else:
                            df_empresas.loc[df_empresas['cnpj'] == e_target, ['cnpj', 'nome','responsavel','telefone','email','est','status']] = [cnpj, n_emp_in.upper(), resp_in.upper(), apenas_numeros_letras(tel_e_raw), mail_in, est_e, stat_e]
                            sucesso, erro = salvar_dados(df_empresas, FILE_EMPRESAS)
                            if sucesso:
                                st.success("✅ Empresa atualizada com sucesso!")
                                st.session_state.aba_emp = "Listar"
                                time.sleep(1); st.rerun()
                            else: st.error(f"Erro na nuvem: {erro}")

        elif opcao_emp == "Excluir":
            if df_empresas.empty: st.warning("Nenhuma empresa cadastrada.")
            else:
                opcoes_emp = {str(r['cnpj']): f"{str(r['nome']).upper()} | CNPJ: {str(r['cnpj'])}" for _, r in df_empresas.iterrows()}
                e_target_del = st.selectbox("🔎 Selecione a Empresa para EXCLUIR:", options=[""] + list(opcoes_emp.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_emp[x])
                if e_target_del != "":
                    st.error(f"⚠️ Atenção: Você está prestes a excluir a empresa **{opcoes_emp[e_target_del]}**.")
                    if st.button("❌ Confirmar Exclusão"):
                        df_empresas = df_empresas[df_empresas['cnpj'] != e_target_del]
                        sucesso, erro = salvar_dados(df_empresas, FILE_EMPRESAS)
                        if sucesso:
                            st.success("🗑️ Empresa excluída permanentemente!")
                            st.session_state.aba_emp = "Listar"
                            time.sleep(1); st.rerun()
                        else: st.error(f"Falha na nuvem: {erro}")

    # === PRESTADORES ===
    with menu[4]:
        st.subheader("🔧 Gerenciamento de Prestadores (Guinchos e Endereço)")
        
        pendentes = df_prestadores[df_prestadores['homologado'] == 'Pendente']
        if not pendentes.empty:
            st.error(f"⚠️ Atenção Administrativa: Existem {len(pendentes)} prestadores aguardando homologação! Eles se cadastraram via Portal externo.")
            for idx, p in pendentes.iterrows():
                with st.expander(f"Solicitação de: {p['nome']} - {p['est']}"):
                    st.write(f"**Tipo:** {p['tipo']} | **Telefone:** {p['telefone']} | **Cidade:** {p.get('cidade','N/D')}")
                    
                    texto_zap = urllib.parse.quote(f"Olá *{str(p['nome']).upper()}*! \n\nSeu cadastro na plataforma de prestadores da *AD Rastreamento Veicular* foi analisado e *APROVADO*! ✅🚛\n\nVocê já pode acessar o seu painel exclusivo utilizando o seu CPF/CNPJ e a senha que você criou.\n\nSeja bem-vindo à nossa rede 24h!")
                    link_w_aprov = f"https://api.whatsapp.com/send?phone=55{apenas_numeros_letras(p['telefone'])}&text={texto_zap}"
                    
                    st.markdown(f'<a href="{link_w_aprov}" target="_blank" style="text-decoration: none;"><button style="background-color: #25D366; color: white; padding: 6px 12px; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; margin-bottom: 10px;">📲 1º Clique aqui para Avisar no WhatsApp</button></a>', unsafe_allow_html=True)
                    
                    col_h1, col_h2 = st.columns(2)
                    if col_h1.button("✅ 2º Confirmar Aprovação no Sistema", key=f"apr_{p['id']}"):
                        df_prestadores.loc[df_prestadores['id'] == p['id'], 'homologado'] = 'Aprovado'
                        sucesso, erro = salvar_dados(df_prestadores, FILE_PRESTADORES)
                        if sucesso: st.success("Aprovado com sucesso!"); time.sleep(1); st.rerun()
                        else: st.error(f"Falha na nuvem: {erro}")
                    if col_h2.button("❌ Reprovar/Arquivar", key=f"rep_{p['id']}"):
                        df_prestadores.loc[df_prestadores['id'] == p['id'], 'homologado'] = 'Reprovado'
                        sucesso, erro = salvar_dados(df_prestadores, FILE_PRESTADORES)
                        if sucesso: st.info("Movido para reprovados."); time.sleep(1); st.rerun()
                        else: st.error(f"Falha na nuvem: {erro}")
            st.write("---")
        
        if "aba_pre" not in st.session_state: st.session_state.aba_pre = "Listar"
        opcoes_radio_pre = ["Listar", "Incluir Novo", "Editar", "Excluir"]
        idx_radio_pre = opcoes_radio_pre.index(st.session_state.aba_pre) if st.session_state.aba_pre in opcoes_radio_pre else 0
        opcao_pre = st.radio("Ação Prestadores:", opcoes_radio_pre, horizontal=True, index=idx_radio_pre)
        st.session_state.aba_pre = opcao_pre
        
        if opcao_pre == "Listar":
            busca_pres_lista = st.text_input("🔍 Buscar Prestador na Lista (Nome, Tipo ou Cidade):")
            if df_prestadores.empty: st.info("Nenhum prestador cadastrado.")
            else: 
                df_view_pres = df_prestadores.copy()
                expandir_pastas_pre = False
                if busca_pres_lista: 
                    expandir_pastas_pre = True
                    df_view_pres = df_view_pres[df_view_pres['nome'].str.contains(busca_pres_lista, case=False, na=False) | df_view_pres['tipo'].str.contains(busca_pres_lista, case=False, na=False) | df_view_pres['cidade'].str.contains(busca_pres_lista, case=False, na=False)]
                
                estados_na_lista = df_view_pres['est'].dropna().unique()
                if len(estados_na_lista) == 0: st.warning("Nenhum prestador encontrado.")
                else:
                    for est_sigla in sorted(estados_na_lista):
                        nome_est = str(est_sigla).upper() if str(est_sigla).strip() != "" else "SEM ESTADO VINCULADO"
                        with st.expander(f"📁 Prestadores do Estado: {nome_est}", expanded=expandir_pastas_pre):
                            df_est_filtrada = df_view_pres[df_view_pres['est'] == est_sigla]
                            st.dataframe(df_est_filtrada[['nome','cpf','tipo','telefone','cidade','status','homologado']].style.map(colorir_status, subset=['status']), use_container_width=True)
        
        elif opcao_pre == "Incluir Novo":
            if "pre_inc_nome" not in st.session_state: st.session_state.pre_inc_nome = ""
            if "pre_inc_cpf" not in st.session_state: st.session_state.pre_inc_cpf = ""
            if "pre_inc_tel" not in st.session_state: st.session_state.pre_inc_tel = ""
            if "pre_inc_end" not in st.session_state: st.session_state.pre_inc_end = ""
            if "pre_inc_cid" not in st.session_state: st.session_state.pre_inc_cid = ""
            if "pre_inc_cep" not in st.session_state: st.session_state.pre_inc_cep = ""
            
            c1, c2 = st.columns(2)
            n_prest_in = c1.text_input("Nome do Guincho/Prestador:", value=st.session_state.pre_inc_nome)
            st.session_state.pre_inc_nome = n_prest_in
            cpf_p_raw = c2.text_input("CPF/CNPJ do Prestador:", value=st.session_state.pre_inc_cpf)
            st.session_state.pre_inc_cpf = cpf_p_raw
            
            t_prest_lista = c1.multiselect("Tipos de Serviço Prestado:", options=OPCOES_SERVICOS, default=["Guincho"])
            tel_p_raw = c2.text_input("Telefone de Contato (Com DDD):", value=st.session_state.pre_inc_tel)
            st.session_state.pre_inc_tel = tel_p_raw
            
            end_p_in = c1.text_input("Endereço / Base:", value=st.session_state.pre_inc_end)
            st.session_state.pre_inc_end = end_p_in
            cid_p_in = c2.text_input("Cidade Base:", value=st.session_state.pre_inc_cid)
            st.session_state.pre_inc_cid = cid_p_in
            cep_p_in = c1.text_input("CEP:", value=st.session_state.pre_inc_cep)
            st.session_state.pre_inc_cep = cep_p_in
            
            est_p = c2.selectbox("Estado (UF) de Atuação:", options=ESTADOS_BR, index=ESTADOS_BR.index("RN"))
            stat_p = c1.selectbox("Status do Guincho:", ["Ativo", "Inativo"], index=0)
            
            if st.button("Salvar Novo Prestador"):
                cpf_p = apenas_numeros_letras(cpf_p_raw)
                t_prest = ", ".join(t_prest_lista)
                if not n_prest_in or not cpf_p: st.error("O Nome e o CPF/CNPJ do prestador são obrigatórios.")
                elif not t_prest_lista: st.error("Selecione ao menos um tipo de serviço prestado.")
                else:
                    prox_p = int(df_prestadores['id'].astype(float).max() + 1) if not df_prestadores.empty else 1
                    novo_p = pd.DataFrame([{'id': str(prox_p), 'nome': n_prest_in.upper(), 'cpf': cpf_p, 'tipo': t_prest, 'telefone': apenas_numeros_letras(tel_p_raw), 'endereco': end_p_in, 'cidade': cid_p_in.upper(), 'cep': cep_p_in, 'est': est_p, 'status': stat_p, 'homologado': 'Aprovado', 'senha': 'admin', 'frota': '[]'}])
                    df_prestadores_temp = pd.concat([df_prestadores, novo_p], ignore_index=True)
                    sucesso, erro = salvar_dados(df_prestadores_temp, FILE_PRESTADORES)
                    if sucesso:
                        st.success("✅ Prestador cadastrado com sucesso!")
                        for k in ["pre_inc_nome", "pre_inc_cpf", "pre_inc_tel", "pre_inc_end", "pre_inc_cid", "pre_inc_cep"]: st.session_state[k] = ""
                        st.session_state.aba_pre = "Listar"
                        time.sleep(1); st.rerun()
                    else:
                        st.error(f"Erro na nuvem: {erro}")
                        gerar_botao_whatsapp({"Ação": "Admin Cadastrando Prestador", "Nome": n_prest_in, "Serviços": t_prest})

        elif opcao_pre == "Editar":
            if df_prestadores.empty: st.warning("Nenhum prestador cadastrado.")
            else:
                opcoes_pre = {str(r['id']): f"{str(r['nome']).upper()} | Cidade: {str(r['cidade']).upper()} | Tipo: {str(r['tipo'])}" for _, r in df_prestadores.iterrows()}
                p_target = st.selectbox("🔎 Selecione o Prestador para Editar:", options=[""] + list(opcoes_pre.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_pre[x])
                if p_target != "":
                    dados_p_ant = df_prestadores[df_prestadores['id'].astype(str) == p_target].iloc[0]
                    c1, c2 = st.columns(2)
                    n_prest_in = c1.text_input("Nome do Guincho/Prestador:", value=dados_p_ant['nome'])
                    cpf_p_raw = c2.text_input("CPF/CNPJ do Prestador:", value=dados_p_ant.get('cpf',''))
                    servicos_atuais = [s for s in [x.strip() for x in str(dados_p_ant.get('tipo', '')).split(',')] if s in OPCOES_SERVICOS]
                    if not servicos_atuais: servicos_atuais = ["Guincho"]
                    t_prest_lista = c1.multiselect("Tipos de Serviço Prestado:", options=OPCOES_SERVICOS, default=servicos_atuais)
                    tel_p_raw = c2.text_input("Telefone de Contato (Com DDD):", value=dados_p_ant['telefone'])
                    end_p_in = c1.text_input("Endereço / Base:", value=dados_p_ant.get('endereco',''))
                    cid_p_in = c2.text_input("Cidade Base:", value=dados_p_ant.get('cidade',''))
                    cep_p_in = c1.text_input("CEP:", value=dados_p_ant.get('cep',''))
                    idx_est_p = ESTADOS_BR.index(str(dados_p_ant['est']).upper()) if str(dados_p_ant['est']).upper() in ESTADOS_BR else ESTADOS_BR.index("RN")
                    est_p = c2.selectbox("Estado (UF) de Atuação:", options=ESTADOS_BR, index=idx_est_p)
                    stat_p = c1.selectbox("Status do Guincho:", ["Ativo", "Inativo"], index=["Ativo", "Inativo"].index(str(dados_p_ant['status'])))
                    
                    if st.button("Salvar Alterações"):
                        cpf_p = apenas_numeros_letras(cpf_p_raw)
                        t_prest = ", ".join(t_prest_lista)
                        if not n_prest_in or not cpf_p: st.error("O Nome e o CPF/CNPJ do prestador são obrigatórios.")
                        elif not t_prest_lista: st.error("Selecione ao menos um tipo de serviço prestado.")
                        else:
                            df_prestadores.loc[df_prestadores['id'].astype(str) == p_target, ['nome','cpf','tipo','telefone','endereco','cidade','cep','est','status']] = [n_prest_in.upper(), cpf_p, t_prest, apenas_numeros_letras(tel_p_raw), end_p_in, cid_p_in.upper(), cep_p_in, est_p, stat_p]
                            sucesso, erro = salvar_dados(df_prestadores, FILE_PRESTADORES)
                            if sucesso:
                                st.success("✅ Prestador updated com sucesso!")
                                st.session_state.aba_pre = "Listar"
                                time.sleep(1); st.rerun()
                            else: st.error(f"Erro na nuvem: {erro}")

        elif opcao_pre == "Excluir":
            if df_prestadores.empty: st.warning("Nenhum prestador cadastrado.")
            else:
                opcoes_pre = {str(r['id']): f"{str(r['nome']).upper()} | Cidade: {str(r['cidade']).upper()} | Tipo: {str(r['tipo'])}" for _, r in df_prestadores.iterrows()}
                p_target_del = st.selectbox("🔎 Selecione o Prestador para EXCLUIR:", options=[""] + list(opcoes_pre.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_pre[x])
                if p_target_del != "":
                    st.error(f"⚠️ Atenção: Você está prestes a excluir o prestador **{opcoes_pre[p_target_del]}**.")
                    if st.button("❌ Confirmar Exclusão"):
                        df_prestadores = df_prestadores[df_prestadores['id'].astype(str) != p_target_del]
                        sucesso, erro = salvar_dados(df_prestadores, FILE_PRESTADORES)
                        if sucesso:
                            st.success("🗑️ Prestador excluído permanentemente!")
                            st.session_state.aba_pre = "Listar"
                            time.sleep(1); st.rerun()
                        else: st.error(f"Falha na nuvem: {erro}")

    # === ABA 6: SEGURANÇA E BACKUP DE EMERGÊNCIA (NOVO) ===
    with menu[5]:
        st.subheader("💾 Backup e Restauração de Emergência")
        st.info("Baixe seus arquivos regularmente. Em caso de apagão da nuvem, faça o upload aqui para restaurar o sistema em segundos.")
        c_b1, c_b2 = st.columns(2)
        
        with c_b1:
            st.markdown("### 📥 1. Baixar Backups Locais")
            if os.path.exists(FILE_CLIENTES):
                with open(FILE_CLIENTES, "rb") as f: st.download_button("Baixar Clientes (.csv)", f, file_name="banco_clientes.csv", use_container_width=True)
            if os.path.exists(FILE_EMPRESAS):
                with open(FILE_EMPRESAS, "rb") as f: st.download_button("Baixar Empresas (.csv)", f, file_name="banco_empresas.csv", use_container_width=True)
            if os.path.exists(FILE_PRESTADORES):
                with open(FILE_PRESTADORES, "rb") as f: st.download_button("Baixar Prestadores (.csv)", f, file_name="banco_prestadores.csv", use_container_width=True)
            if os.path.exists(FILE_OS):
                with open(FILE_OS, "rb") as f: st.download_button("Baixar Atendimentos / OS (.csv)", f, file_name="banco_os.csv", use_container_width=True)
                
        with c_b2:
            st.markdown("### 📤 2. Restaurar Sistema")
            uploaded_file = st.file_uploader("Arraste o arquivo de backup aqui para restaurar", type=['csv'])
            if uploaded_file is not None:
                if st.button(f"🚀 Restaurar dados de: {uploaded_file.name}"):
                    caminho_salvar = os.path.join(FOLDER, uploaded_file.name)
                    with open(caminho_salvar, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    sucesso, erro = salvar_no_github(caminho_salvar)
                    if sucesso:
                        st.success(f"✅ Arquivo {uploaded_file.name} restaurado no sistema e salvo na nuvem com sucesso!")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"⚠️ Arquivo restaurado apenas localmente. Falha ao enviar para o GitHub: {erro}")


# --- INTERFACE DE PARCEIROS RESTRITA ---
else:
    menu_parceiro = st.tabs(["👥 Cadastro de Clientes", "📋 Histórico de Chamados"])
    
    with menu_parceiro[0]:
        df_filtrado_p = df_clientes[df_clientes['emp_name'].str.lower() == st.session_state.empresa_vinculada.lower()]
        
        # --- CALCULO DA TAXA DE ACIONAMENTO DO MÊS (VISÃO PARCEIRO) ---
        mes_atual_taxa_p = datetime.now().month
        ano_atual_taxa_p = datetime.now().year
        base_clientes_taxa_p = len(df_filtrado_p)
        total_os_mes_p = 0
        if not df_os.empty:
            df_os_temp_p = df_os.copy()
            df_os_temp_p['data_hora'] = pd.to_datetime(df_os_temp_p['data_hora'], errors='coerce')
            os_mes_atual_p = df_os_temp_p[(df_os_temp_p['empresa'].str.upper() == st.session_state.empresa_vinculada.upper()) & (df_os_temp_p['data_hora'].dt.month == mes_atual_taxa_p) & (df_os_temp_p['data_hora'].dt.year == ano_atual_taxa_p)]
            total_os_mes_p = len(os_mes_atual_p)
        taxa_p = (total_os_mes_p / base_clientes_taxa_p * 100) if base_clientes_taxa_p > 0 else 0
        st.markdown(f"📊 **De acordo com a base de {base_clientes_taxa_p} clientes/veículos, a taxa de acionamento neste mês é de {taxa_p:.1f}%.**")
        st.write("---")
        # --------------------------------------------------------------
        
        if "aba_part" not in st.session_state: st.session_state.aba_part = "Visualizar"
        opcoes_radio_part = ["Visualizar", "Incluir Novo", "Editar Cliente", "Excluir Cliente"]
        idx_radio_part = opcoes_radio_part.index(st.session_state.aba_part) if st.session_state.aba_part in opcoes_radio_part else 0
        op_part = st.radio("Ação Parceiro:", opcoes_radio_part, horizontal=True, index=idx_radio_part)
        st.session_state.aba_part = op_part
        
        if op_part == "Visualizar":
            busca_cli_part = st.text_input("🔍 Buscar Cliente (Nome, Placa ou CPF):")
            df_view_cli_part = df_filtrado_p.copy()
            if busca_cli_part:
                df_view_cli_part = df_view_cli_part[df_view_cli_part['nome'].str.contains(busca_cli_part, case=False, na=False) | df_view_cli_part['pla'].str.contains(busca_cli_part, case=False, na=False) | df_view_cli_part['cpf'].str.contains(busca_cli_part, case=False, na=False) | df_view_cli_part['veiculos_lista'].str.lower().str.contains(busca_cli_part.lower(), na=False)]
            
            if df_view_cli_part.empty: st.info("Nenhum cliente encontrado.")
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
                        except: d_str = str(r['data_hora'])[:10]
                        res.append(f"{r['tipo_servico']} ({d_str})")
                    return " | ".join(res)
                
                df_view_cli_part['Histórico'] = df_view_cli_part['id'].apply(formatar_historico_p)
                st.dataframe(df_view_cli_part[['nome','cpf','tel','cidade','plano_km','Histórico','status']].style.map(colorir_status, subset=['status']), use_container_width=True)
                
                st.markdown("---")
                
                if "sel_det_part" not in st.session_state: st.session_state.sel_det_part = ""
                widget_key_part = "sb_det_part_wid"
                
                cli_opcoes_part = [""] + df_view_cli_part['nome'].tolist()
                idx_sel_part = cli_opcoes_part.index(st.session_state.sel_det_part) if st.session_state.sel_det_part in cli_opcoes_part else 0
                
                cli_sel_part = st.selectbox("🔍 Selecione um cliente para ver a Ficha Completa:", cli_opcoes_part, index=idx_sel_part, key=widget_key_part)
                st.session_state.sel_det_part = cli_sel_part
                
                if cli_sel_part != "":
                    cli_data_p = df_view_cli_part[df_view_cli_part['nome'] == cli_sel_part].iloc[0]
                    st.markdown(f"### 📋 Ficha do Cliente: {cli_data_p['nome']}")
                    c1, c2 = st.columns(2)
                    c1.write(f"**CPF:** {cli_data_p['cpf']}")
                    c1.write(f"**Telefone:** {cli_data_p['tel']}")
                    c1.write(f"**Plano Contratado:** {cli_data_p.get('plano_km', 'N/D')}")
                    c2.write(f"**Endereço:** {cli_data_p.get('endereco', 'N/D')} - {cli_data_p.get('cidade', 'N/D')}/{cli_data_p.get('est', 'N/D')}")
                    status_color_p = "🟢 Ativo" if cli_data_p['status'] == 'Ativo' else "🔴 Inativo"
                    c2.write(f"**Status:** {status_color_p}")
                    
                    st.write("**🚗 Frota Cadastrada:**")
                    try:
                        frota_p = json.loads(cli_data_p['veiculos_lista'])
                        st.table(pd.DataFrame(frota_p))
                    except:
                        st.write(f"{cli_data_p.get('vei', '')} - Placa: {cli_data_p.get('pla', '')}")
                        
                    st.write("---")
                    st.write(f"**📊 Saldo de Acionamentos no Ano ({datetime.now().year}) - Geral do Cliente:**")
                    ano_atual = datetime.now().year
                    total_g, total_ps, total_pe, total_b, total_c = 0, 0, 0, 0, 0
                    if not df_os.empty:
                        df_os_copy = df_os.copy()
                        df_os_copy['data_hora'] = pd.to_datetime(df_os_copy['data_hora'], errors='coerce')
                        os_cliente_ano = df_os_copy[(df_os_copy['cliente_id'].astype(str).str.strip() == str(cli_data_p['id']).strip()) & (df_os_copy['data_hora'].dt.year == ano_atual)]
                        for _, o in os_cliente_ano.iterrows():
                            serv = str(o['tipo_servico']).lower()
                            if "guincho" in serv: total_g += 1
                            elif "seca" in serv: total_ps += 1
                            elif "elét" in serv or "elet" in serv: total_pe += 1
                            elif "chaveiro" in serv: total_c += 1
                            elif "borrach" in serv or "borrac" in serv: total_b += 1
                    
                    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
                    col_m1.metric("Guinchos", f"{total_g} / 2"); col_m2.metric("Pane Seca", f"{total_ps} / 1"); col_m3.metric("Elétrica", f"{total_pe} / 1"); col_m4.metric("Chaveiro", f"{total_c} / 1"); col_m5.metric("Borracheiro", f"{total_b} / 1")
                    st.write("---")
                        
                    st.write("**🚨 Histórico Completo de Atendimentos:**")
                    if df_os.empty: st.info("Nenhum acionamento.")
                    else:
                        os_cli_p = df_os[df_os['cliente_id'].astype(str).str.strip() == str(cli_data_p['id']).strip()]
                        if os_cli_p.empty: st.info("Nenhum acionamento.")
                        else: st.dataframe(os_cli_p[['data_hora', 'tipo_servico', 'placa', 'prestador', 'status_os']], use_container_width=True)
                            
                    if st.button("❌ Fechar Ficha do Cliente", key="btn_close_part"):
                        st.session_state.sel_det_part = ""
                        if widget_key_part in st.session_state: del st.session_state[widget_key_part]
                        st.rerun()
        
        elif op_part == "Incluir Novo":
            if "part_inc_nome" not in st.session_state: st.session_state.part_inc_nome = ""
            if "part_inc_cpf" not in st.session_state: st.session_state.part_inc_cpf = ""
            if "part_inc_tel" not in st.session_state: st.session_state.part_inc_tel = ""
            if "part_inc_end" not in st.session_state: st.session_state.part_inc_end = ""
            if "part_inc_cid" not in st.session_state: st.session_state.part_inc_cid = ""
            if "part_inc_cep" not in st.session_state: st.session_state.part_inc_cep = ""
            
            c1, c2 = st.columns(2)
            p_nome_in = c1.text_input("Nome Completo:", value=st.session_state.part_inc_nome)
            st.session_state.part_inc_nome = p_nome_in
            p_cpf_raw = c2.text_input("CPF:", value=st.session_state.part_inc_cpf)
            st.session_state.part_inc_cpf = p_cpf_raw
            p_tel_raw = c1.text_input("Telefone:", value=st.session_state.part_inc_tel)
            st.session_state.part_inc_tel = p_tel_raw
            p_end_in = c2.text_input("Endereço Completo:", value=st.session_state.part_inc_end)
            st.session_state.part_inc_end = p_end_in
            p_cid_in = c1.text_input("Cidade:", value=st.session_state.part_inc_cid)
            st.session_state.part_inc_cid = p_cid_in
            p_cep_in = c2.text_input("CEP:", value=st.session_state.part_inc_cep)
            st.session_state.part_inc_cep = p_cep_in
            
            st.write("---")
            st.write("🚗 **Frota do Cliente (Tabela Interativa)**")
            frota_editada_p = st.data_editor(pd.DataFrame([{"Modelo/Ano": "", "Placa": ""}]), num_rows="dynamic", use_container_width=True)
            st.write("---")
            
            col_pb1, col_pb2, col_pb3 = st.columns(3)
            p_est = col_pb1.selectbox("UF do Veículo:", options=ESTADOS_BR, index=ESTADOS_BR.index("RN"))
            p_plano_km = col_pb2.selectbox("Plano Contratado (KM):", options=PLANOS_KM, index=0)
            p_stat = col_pb3.selectbox("Status do Serviço:", ["Ativo", "Inativo"], index=0)
            
            if st.button("Salvar Novo Registro"):
                p_cpf = apenas_numeros_letras(p_cpf_raw)
                frota_limpa_p = frota_editada_p.dropna(how='all')
                frota_limpa_p['Placa'] = frota_limpa_p['Placa'].astype(str).str.upper().str.replace("-","").str.replace(" ","")
                frota_json_str_p = json.dumps(frota_limpa_p.to_dict('records'))
                vei_prin_p = frota_limpa_p.iloc[0]['Modelo/Ano'] if not frota_limpa_p.empty else ""
                pla_prin_p = frota_limpa_p.iloc[0]['Placa'] if not frota_limpa_p.empty else ""
                
                if not p_nome_in or not pla_prin_p: st.error("Nome e ao menos 1 Placa são obrigatórios.")
                else:
                    prox_id = int(df_clientes['id'].astype(float).max() + 1) if not df_clientes.empty else 1
                    novo_reg = pd.DataFrame([{'id': str(prox_id), 'nome': p_nome_in.upper(), 'cpf': p_cpf, 'tel': apenas_numeros_letras(p_tel_raw), 'endereco': p_end_in, 'cidade': p_cid_in.upper(), 'cep': p_cep_in, 'plano_km': p_plano_km, 'vei': vei_prin_p, 'pla': pla_prin_p, 'est': p_est, 'emp_name': st.session_state.empresa_vinculada.upper(), 'status': p_stat, 'veiculos_lista': frota_json_str_p}])
                    df_clientes_temp = pd.concat([df_clientes, novo_reg], ignore_index=True)
                    
                    sucesso, erro = salvar_dados(df_clientes_temp, FILE_CLIENTES)
                    if sucesso:
                        st.success("✅ Registro salvo com sucesso!")
                        for k in ["part_inc_nome", "part_inc_cpf", "part_inc_tel", "part_inc_end", "part_inc_cid", "part_inc_cep"]: st.session_state[k] = ""
                        st.session_state.aba_part = "Visualizar"
                        time.sleep(1); st.rerun()
                    else:
                        st.error("⚠️ Atenção: Instabilidade na Conexão com a Nuvem. Ocorreu um erro ao sincronizar este cadastro com a base de dados da Central AD. Para não perder as informações preenchidas, clique no botão abaixo e envie os dados diretamente para o nosso WhatsApp de emergência.")
                        gerar_botao_whatsapp({
                            "Ação": "Novo Cadastro", 
                            "Parceiro": st.session_state.empresa_vinculada.upper(),
                            "Cliente": p_nome_in.upper(), 
                            "CPF": p_cpf, 
                            "Placa": pla_prin_p,
                            "Erro": erro
                        })

        elif op_part == "Editar Cliente":
            if df_filtrado_p.empty: st.warning("Nenhum cliente cadastrado para editar.")
            else:
                opcoes_dict_p = {str(r['id']): f"{str(r['nome']).upper()} | CPF: {str(r['cpf'])}" for _, r in df_filtrado_p.iterrows()}
                part_target = st.selectbox("🔎 Selecione o cliente para Editar:", options=[""] + list(opcoes_dict_p.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_dict_p[x])
                
                if part_target != "":
                    dados_part_ant = df_filtrado_p[df_filtrado_p['id'].astype(str) == part_target].iloc[0]
                    c1, c2 = st.columns(2)
                    p_nome_in = c1.text_input("Nome Completo:", value=dados_part_ant['nome'])
                    p_cpf_raw = c2.text_input("CPF:", value=dados_part_ant['cpf'])
                    p_tel_raw = c1.text_input("Telefone:", value=dados_part_ant['tel'])
                    p_end_in = c2.text_input("Endereço Completo:", value=dados_part_ant.get('endereco', ''))
                    p_cid_in = c1.text_input("Cidade:", value=dados_part_ant.get('cidade', ''))
                    p_cep_in = c2.text_input("CEP:", value=dados_part_ant.get('cep', ''))
                    
                    st.write("---")
                    st.write("🚗 **Frota do Cliente**")
                    frota_inicial_p = []
                    if pd.notna(dados_part_ant.get('veiculos_lista')) and dados_part_ant['veiculos_lista']:
                        try: frota_inicial_p = json.loads(dados_part_ant['veiculos_lista'])
                        except: pass
                    if not frota_inicial_p:
                        if pd.notna(dados_part_ant.get('vei')) and dados_part_ant['vei'] != 'nan': frota_inicial_p.append({"Modelo/Ano": dados_part_ant['vei'], "Placa": str(dados_part_ant['pla']).upper()})
                        if pd.notna(dados_part_ant.get('vei_2')) and dados_part_ant['vei_2'] != 'nan' and dados_part_ant['vei_2']: frota_inicial_p.append({"Modelo/Ano": dados_part_ant['vei_2'], "Placa": str(dados_part_ant['pla_2']).upper()})
                    if not frota_inicial_p: frota_inicial_p = [{"Modelo/Ano": "", "Placa": ""}]
                    frota_editada_p = st.data_editor(pd.DataFrame(frota_inicial_p), num_rows="dynamic", use_container_width=True)
                    st.write("---")
                    
                    col_pb1, col_pb2, col_pb3 = st.columns(3)
                    idx_est_part = ESTADOS_BR.index(str(dados_part_ant['est']).upper()) if str(dados_part_ant['est']).upper() in ESTADOS_BR else ESTADOS_BR.index("RN")
                    p_est = col_pb1.selectbox("UF do Veículo:", options=ESTADOS_BR, index=idx_est_part)
                    idx_plano_p = PLANOS_KM.index(str(dados_part_ant.get('plano_km', 'Sem Limite'))) if str(dados_part_ant.get('plano_km', 'Sem Limite')) in PLANOS_KM else 0
                    p_plano_km = col_pb2.selectbox("Plano Contratado (KM):", options=PLANOS_KM, index=idx_plano_p)
                    p_stat = col_pb3.selectbox("Status do Serviço:", ["Ativo", "Inativo"], index=["Ativo", "Inativo"].index(str(dados_part_ant['status'])))
                    
                    if st.button("Salvar Alterações"):
                        p_cpf = apenas_numeros_letras(p_cpf_raw)
                        frota_limpa_p = frota_editada_p.dropna(how='all')
                        frota_limpa_p['Placa'] = frota_limpa_p['Placa'].astype(str).str.upper().str.replace("-","").str.replace(" ","")
                        frota_json_str_p = json.dumps(frota_limpa_p.to_dict('records'))
                        vei_prin_p = frota_limpa_p.iloc[0]['Modelo/Ano'] if not frota_limpa_p.empty else ""
                        pla_prin_p = frota_limpa_p.iloc[0]['Placa'] if not frota_limpa_p.empty else ""
                        
                        if not p_nome_in or not pla_prin_p: st.error("Nome e ao menos 1 Placa são obrigatórios.")
                        else:
                            df_clientes.loc[df_clientes['id'].astype(str) == part_target, ['nome','cpf','tel','endereco','cidade','cep','plano_km','vei','pla','est','status','veiculos_lista']] = [p_nome_in.upper(), p_cpf, apenas_numeros_letras(p_tel_raw), p_end_in, p_cid_in.upper(), p_cep_in, p_plano_km, vei_prin_p, pla_prin_p, p_est, p_stat, frota_json_str_p]
                            sucesso, erro = salvar_dados(df_clientes, FILE_CLIENTES)
                            if sucesso:
                                st.success("✅ Registro atualizado com sucesso!")
                                st.session_state.aba_part = "Visualizar"
                                time.sleep(1); st.rerun()
                            else:
                                st.error("⚠️ Atenção: Falha de comunicação com a nuvem da Central AD.")
                                gerar_botao_whatsapp({
                                    "Ação": "Edição de Cadastro",
                                    "Parceiro": st.session_state.empresa_vinculada.upper(),
                                    "Cliente": p_nome_in.upper(),
                                    "Placa Principal": pla_prin_p
                                })

        elif op_part == "Excluir Cliente":
            if df_filtrado_p.empty: st.warning("Nenhum cliente cadastrado.")
            else:
                opcoes_dict_p = {str(r['id']): f"{str(r['nome']).upper()} | CPF: {str(r['cpf'])}" for _, r in df_filtrado_p.iterrows()}
                part_target_del = st.selectbox("🔎 Selecione o cliente para EXCLUIR:", options=[""] + list(opcoes_dict_p.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_dict_p[x])
                if part_target_del != "":
                    st.error(f"⚠️ Atenção: Você está prestes a excluir permanentemente o cliente **{opcoes_dict_p[part_target_del]}**.")
                    if st.button("❌ Confirmar Exclusão"):
                        df_clientes = df_clientes[df_clientes['id'].astype(str) != part_target_del]
                        sucesso, erro = salvar_dados(df_clientes, FILE_CLIENTES)
                        if sucesso:
                            st.success("🗑️ Cliente excluído permanentemente!")
                            st.session_state.aba_part = "Visualizar"
                            time.sleep(1); st.rerun()
                        else: st.error(f"Erro na nuvem: {erro}")

    with menu_parceiro[1]:
        df_os_parceiro = df_os[df_os['empresa'].str.lower() == st.session_state.empresa_vinculada.lower()]
        if df_os_parceiro.empty: st.info("Nenhum acionamento registrado para sua empresa.")
        else: st.dataframe(df_os_parceiro, use_container_width=True)
