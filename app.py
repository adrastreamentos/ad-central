import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import urllib.parse
import base64
import time
import requests
import json
from PIL import Image
import numpy as np
from streamlit_drawable_canvas import st_canvas

# ===================================================================================
# FUNÇÕES GLOBAIS E ESTILIZAÇÃO (NOVO VISUAL)
# ===================================================================================
def colorir_status(val):
    return 'color: #2e7d32; font-weight: bold;' if str(val).strip() == 'Ativo' else 'color: #c62828; font-weight: bold;'

def formatar_status_financeiro(val):
    if str(val).strip() == 'Pago': return 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold;'
    elif str(val).strip() == 'Atrasado': return 'background-color: #ffebee; color: #c62828; font-weight: bold;'
    else: return 'background-color: #fff8e1; color: #f57f17; font-weight: bold;'

def get_ultimos_3_meses():
    hoje = datetime.now()
    meses = []
    for i in range(3):
        m = hoje.month - i
        y = hoje.year
        if m <= 0:
            m += 12
            y -= 1
        meses.append(f"{m:02d}/{y}")
    return meses

st.set_page_config(page_title="Central 24h - AD Rastreamento Veicular", layout="wide", page_icon="🔒")

st.markdown("""
    <style>
    /* Ocultar menu e rodapé padrão do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Scrollbar customizada */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #f8f9fa; }
    ::-webkit-scrollbar-thumb { background: #d1c4e9; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #7B2CBF; }

    /* Títulos principais */
    .main-title { 
        font-size: 38px; 
        font-weight: 900; 
        background: -webkit-linear-gradient(45deg, #7B2CBF, #E53935);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center; 
        margin-bottom: 5px; 
        letter-spacing: 1px;
    }
    .subtitle { 
        font-size: 16px; 
        color: #666; 
        text-align: center; 
        margin-bottom: 35px; 
        font-weight: 600; 
        text-transform: uppercase;
        letter-spacing: 2px;
    }

    /* Estilização das Abas */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; padding-bottom: 5px; }
    .stTabs [data-baseweb="tab"] { 
        font-size: 15px; font-weight: 600; border-radius: 8px 8px 0px 0px;
        padding: 10px 20px; background-color: #f8f9fa; border: 1px solid #e0e0e0;
        border-bottom: none; color: #555;
    }
    .stTabs [aria-selected="true"] { background-color: #7B2CBF; color: white !important; border: 1px solid #7B2CBF; }

    /* Botões padronizados */
    div.stButton > button:first-child { 
        background-color: #7B2CBF; color: white; border: none; border-radius: 8px; 
        padding: 10px 24px; font-size: 15px; font-weight: 700; transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(123, 44, 191, 0.2);
    }
    div.stButton > button:first-child:hover { 
        background-color: #E53935; box-shadow: 0 6px 12px rgba(229, 57, 53, 0.3);
        transform: translateY(-2px); color: white;
    }

    /* Caixas de Alerta */
    .alert-box { padding: 16px; border-radius: 8px; margin: 15px 0; border-left: 6px solid; font-weight: 500; font-size: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .alert-danger { background-color: #ffebee; color: #c62828; border-color: #E53935; }
    .alert-success { background-color: #e8f5e9; color: #2e7d32; border-color: #4CAF50; }
    .alert-info { background-color: #e3f2fd; color: #1565c0; border-color: #1976D2; }
    .info-box { background-color: #f3e5f5; color: #4a148c; border-color: #7B2CBF; padding: 16px; border-radius: 8px; margin: 15px 0; border-left: 6px solid; font-weight: 600; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    
    /* Cards Financeiros */
    .metric-card { 
        background-color: #ffffff; border-radius: 12px; padding: 25px; text-align: center; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.06); margin-bottom: 20px; border: 1px solid #f0f0f0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.12); }
    .metric-value { font-size: 32px; font-weight: 800; margin-top: 12px; letter-spacing: -0.5px;}
    .val-pago { color: #2e7d32; }
    .val-pendente { color: #f57f17; }
    .val-atrasado { color: #E53935; }

    /* Estilo elegante para Inputs */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] { border-radius: 8px; border: 1px solid #d1d5db; padding: 10px; }
    .stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within { border-color: #7B2CBF; box-shadow: 0 0 0 1px #7B2CBF; }
    </style>
""", unsafe_allow_html=True)

ESTADOS_BR = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
PLANOS_KM = ["Sem Limite", "50km", "100km", "150km", "200km", "300km", "400km", "500km"]
OPCOES_SERVICOS = ["Guincho", "Pane Seca", "Pane Elétrica", "Borracheiro", "Chaveiro"]

FOLDER = "AD_Assistencia"
os.makedirs(FOLDER, exist_ok=True)
FILE_CLIENTES = os.path.join(FOLDER, "banco_clientes.csv")
FILE_EMPRESAS = os.path.join(FOLDER, "banco_empresas.csv")
FILE_PRESTADORES = os.path.join(FOLDER, "banco_prestadores.csv")
FILE_OS = os.path.join(FOLDER, "banco_os.csv")
FILE_LOGS = os.path.join(FOLDER, "banco_logs.csv")
FILE_FINANCEIRO = os.path.join(FOLDER, "banco_financeiro.csv")

def obter_hora_brasilia(): return datetime.now(timezone(timedelta(hours=-3)))
def obter_hora_str(): return obter_hora_brasilia().strftime("%Y-%m-%d %H:%M:%S")
def apenas_numeros_letras(texto): return "".join(caractere for caractere in str(texto) if caractere.isalnum()).strip().lower()

# ===================================================================================
# SISTEMA DE SEGURANÇA E LOGS
# ===================================================================================
def salvar_no_github(caminho_local, tentativas=3):
    token = st.secrets.get("GITHUB_TOKEN", None)
    repo = "adrastreamentos/ad-central"
    if not token: return False, "Token ausente"
    url = f"https://api.github.com/repos/{repo}/contents/{caminho_local.replace(os.sep, '/')}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    for tentativa in range(tentativas):
        try:
            res = requests.get(url, headers=headers)
            sha = res.json().get("sha", None) if res.status_code == 200 else None
            with open(caminho_local, "rb") as f: content = base64.b64encode(f.read()).decode("utf-8")
            data = {"message": f"🔥 Auto-salvamento: {caminho_local}", "content": content, "branch": "main"}
            if sha: data["sha"] = sha
            res_put = requests.put(url, headers=headers, json=data)
            if res_put.status_code in [200, 201]: return True, "Sucesso"
            else: time.sleep(2)
        except Exception: time.sleep(2)
    return False, "Falha de conexão após 3 tentativas."

def salvar_dados(df, caminho):
    df.to_csv(caminho, index=False)
    return salvar_no_github(caminho)

def gerar_botao_whatsapp(dados_dict):
    texto = "🚨 *ERRO DE SINCRONIZAÇÃO - LANÇAMENTO MANUAL* 🚨\nOlá, Central AD!\nTentei salvar dados na plataforma, mas falhou. Seguem os dados:\n\n"
    for k, v in dados_dict.items(): texto += f"*{k}:* {v}\n"
    link = f"https://api.whatsapp.com/send?phone=5584999305771&text={urllib.parse.quote(texto)}"
    st.markdown(f'<a href="{link}" target="_blank" style="text-decoration: none;"><button style="background-color: #25D366; color: white; padding: 12px 24px; border: none; border-radius: 6px; width: 100%; margin-top: 10px;">📲 Informar Falha via WhatsApp</button></a>', unsafe_allow_html=True)

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
    except: return pd.DataFrame(columns=colunas_obrigatorias)

col_logs = ['data_hora', 'usuario', 'acao', 'detalhes']
if not os.path.exists(FILE_LOGS): pd.DataFrame(columns=col_logs).to_csv(FILE_LOGS, index=False)
df_logs = carregar_dados(FILE_LOGS, col_logs)

def registrar_atividade(usuario, acao, detalhes):
    global df_logs
    novo_log = pd.DataFrame([{'data_hora': obter_hora_str(), 'usuario': usuario, 'acao': acao, 'detalhes': detalhes}])
    df_logs = pd.concat([df_logs, novo_log], ignore_index=True)
    df_logs.to_csv(FILE_LOGS, index=False)
    salvar_no_github(FILE_LOGS)

def calcular_fatura_parceiro(nome_empresa, mes, ano, df_clientes_atuais, df_os_atuais):
    tb_precos = {
        "2%": {"50km": 6.90, "100km": 8.90, "200km": 11.20, "Sem Limite": 11.20},
        "3%": {"50km": 9.10, "100km": 13.15, "200km": 17.20, "Sem Limite": 17.20},
        "4%": {"50km": 11.80, "100km": 17.20, "200km": 22.60, "Sem Limite": 22.60},
        "5%": {"50km": 14.50, "100km": 21.25, "200km": 28.00, "Sem Limite": 28.00},
        "6%": {"50km": 17.20, "100km": 25.30, "200km": 33.40, "Sem Limite": 33.40},
        "7%": {"50km": 19.90, "100km": 29.35, "200km": 38.80, "Sem Limite": 38.80},
        "8%": {"50km": 22.60, "100km": 33.40, "200km": 44.20, "Sem Limite": 44.20},
        "9%": {"50km": 25.30, "100km": 37.45, "200km": 49.60, "Sem Limite": 49.60},
        "10%": {"50km": 28.00, "100km": 41.50, "200km": 55.00, "Sem Limite": 55.00},
    }
    lista_veiculos_emp = []
    df_cli_fat = df_clientes_atuais[df_clientes_atuais['emp_name'].str.upper() == nome_empresa.upper()]
    
    for _, r_cli in df_cli_fat.iterrows():
        if pd.notna(r_cli.get('veiculos_lista')) and str(r_cli['veiculos_lista']).strip() not in ['', '[]']:
            try:
                frota_json = json.loads(r_cli['veiculos_lista'])
                for v in frota_json:
                    if v.get('Placa'): lista_veiculos_emp.append(str(r_cli.get('plano_km', '50km')))
            except:
                if pd.notna(r_cli.get('pla')) and str(r_cli['pla']).strip(): lista_veiculos_emp.append(str(r_cli.get('plano_km', '50km')))
        else:
            if pd.notna(r_cli.get('pla')) and str(r_cli['pla']).strip(): lista_veiculos_emp.append(str(r_cli.get('plano_km', '50km')))
            if pd.notna(r_cli.get('pla_2')) and str(r_cli['pla_2']).strip(): lista_veiculos_emp.append(str(r_cli.get('plano_km', '50km')))

    total_v = len(lista_veiculos_emp)
    df_os_temp = df_os_atuais.copy()
    df_os_temp['data_hora'] = pd.to_datetime(df_os_temp['data_hora'], errors='coerce')
    os_filtro = df_os_temp[(df_os_temp['empresa'].str.upper() == nome_empresa.upper()) & 
                           (df_os_temp['status_os'].str.upper() == 'ENCERRADO') & 
                           (df_os_temp['data_hora'].dt.month == int(mes)) & 
                           (df_os_temp['data_hora'].dt.year == int(ano))]
    total_os = len(os_filtro)
    taxa = (total_os / total_v * 100) if total_v > 0 else 0
    
    faixa = "2%"
    if taxa >= 26: faixa = "10%"
    elif taxa >= 24: faixa = "9%"
    elif taxa >= 22: faixa = "8%"
    elif taxa >= 20: faixa = "7%"
    elif taxa >= 18: faixa = "6%"
    elif taxa >= 16: faixa = "5%"
    elif taxa >= 14: faixa = "4%"
    elif taxa >= 10: faixa = "3%"

    fatura_total = 0.0
    if total_v > 0:
        fatura_total += 300.00
        if total_v > 20:
            excedentes = lista_veiculos_emp[20:]
            for p_km in excedentes:
                plano_limpo = "50km" if "50" in p_km else "100km" if "100" in p_km else "200km" if "200" in p_km else "Sem Limite"
                fatura_total += tb_precos[faixa].get(plano_limpo, tb_precos[faixa]["50km"])
                
    return fatura_total, total_v, total_os, taxa, faixa

# ===================================================================================
# RELATÓRIO PDF HTML
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
            
        v_path = os.path.join(FOLDER, "vistorias", str(row['id']))
        vistoria_html = ""
        if os.path.exists(v_path):
            vistoria_html += """
            <div style="margin-bottom: 20px;">
                <h3 style="margin: 0 0 10px 0; font-size: 14px; font-weight: bold; color: #7B2CBF;">5. VISTORIA DE ENTRADA E ASSINATURA</h3>
                <div style="display: table; width: 100%; border-collapse: collapse;">
                    <div style="display: table-row;">
            """
            fotos = ['Frente', 'Traseira', 'Lateral_Esquerda', 'Lateral_Direita', 'Placa', 'Assinatura']
            col_count = 0
            for f_name in fotos:
                img_path = os.path.join(v_path, f"{f_name}.jpg")
                if os.path.exists(img_path):
                    with open(img_path, "rb") as img_f: b64 = base64.b64encode(img_f.read()).decode()
                    if col_count > 0 and col_count % 3 == 0: vistoria_html += '</div><div style="display: table-row;">'
                    vistoria_html += f"""
                        <div style="display: table-cell; text-align: center; padding: 5px; width: 33%;">
                            <p style="font-size: 11px; margin-bottom: 5px; font-weight: bold;">{f_name.replace('_', ' ')}</p>
                            <img src="data:image/jpeg;base64,{b64}" style="width: 100%; max-height: 180px; object-fit: contain; border: 1px solid #ccc; border-radius: 4px;" />
                        </div>
                    """
                    col_count += 1
            vistoria_html += "</div></div></div>"

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
            </div>
            {vistoria_html}
            <hr style="border: 0; border-top: 1px dashed #ccc; margin-top: 30px;">
        </div>
        """
    b64 = base64.b64encode(f"<html><head><meta charset='utf-8'></head><body>{cards_html}</body></html>".encode('utf-8')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{titulo_pdf}_{datetime.now().strftime("%Y%m%d")}.html" style="text-decoration: none;"><button style="background-color: #E53935; color: white; padding: 12px 24px; border: none; border-radius: 6px; font-size: 15px; font-weight: bold; cursor: pointer;">🖨️ Baixar Relatório Completo (PDF)</button></a>'

# INICIALIZAÇÃO DE DADOS
col_cli = ['id','nome','cpf','tel','endereco','cidade','cep','plano_km','est','emp_name','status','vei','pla','vei_2','pla_2','veiculos_lista']
col_emp = ['cnpj','nome','responsavel','telefone','email','est','status', 'modo_faturamento']
col_pre = ['id','nome','cpf','tipo','telefone','endereco','cidade','cep','est','status','homologado','senha','frota']
col_os = ['id','data_hora','cliente_id','cliente_nome','placa','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os','veiculo_desc','plano_km','valor_cobrado']
col_fin = ['id', 'mes_ano', 'empresa', 'valor_faturado', 'valor_pago', 'status']

if not os.path.exists(FILE_CLIENTES): pd.DataFrame(columns=col_cli).to_csv(FILE_CLIENTES, index=False)
if not os.path.exists(FILE_EMPRESAS): pd.DataFrame(columns=col_emp).to_csv(FILE_EMPRESAS, index=False)
if not os.path.exists(FILE_PRESTADORES): pd.DataFrame(columns=col_pre).to_csv(FILE_PRESTADORES, index=False)
if not os.path.exists(FILE_OS): pd.DataFrame(columns=col_os).to_csv(FILE_OS, index=False)
if not os.path.exists(FILE_FINANCEIRO): pd.DataFrame(columns=col_fin).to_csv(FILE_FINANCEIRO, index=False)

df_clientes = carregar_dados(FILE_CLIENTES, col_cli)
df_empresas = carregar_dados(FILE_EMPRESAS, col_emp)
df_prestadores = carregar_dados(FILE_PRESTADORES, col_pre)
df_os = carregar_dados(FILE_OS, col_os)
df_financeiro = carregar_dados(FILE_FINANCEIRO, col_fin)

# ===================================================================================
# LOGIN E CADASTRO INICIAL (COM TRAVA DE PORTAL)
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
    portal = st.query_params.get("portal", "")
    st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    col_esp1, col_meio, col_esp2 = st.columns([1, 2, 1])
    
    with col_meio:
        if portal == "prestador":
            st.markdown('<div class="subtitle">🚛 Portal Exclusivo do Prestador</div>', unsafe_allow_html=True)
            tab_login, tab_cadastro = st.tabs(["🔐 Entrar", "📝 Quero me Cadastrar"])
            with tab_login:
                usuario_input = apenas_numeros_letras(st.text_input("Seu Nome (Usuário):"))
                senha_input = apenas_numeros_letras(st.text_input("Sua Senha (ou CPF):", type="password"))
                if st.button("Acessar Meu Painel", use_container_width=True):
                    df_prestadores_login = df_prestadores.copy()
                    df_prestadores_login['cpf_comparar'] = df_prestadores_login['cpf'].astype(str).apply(apenas_numeros_letras)
                    df_prestadores_login['nome_comparar'] = df_prestadores_login['nome'].astype(str).apply(apenas_numeros_letras)
                    df_prestadores_login['senha_comparar'] = df_prestadores_login.get('senha', 'admin').astype(str)
                    prestador_valid = df_prestadores_login[(df_prestadores_login['nome_comparar'] == usuario_input) & ((df_prestadores_login['cpf_comparar'] == senha_input) | (df_prestadores_login['senha_comparar'] == senha_input))]
                    
                    if not prestador_valid.empty:
                        prest_row = prestador_valid.iloc[0]
                        if str(prest_row.get('homologado', 'Pendente')).strip() != 'Aprovado': st.error("⚠️ Seu cadastro ainda não foi aprovado pela Central.")
                        else:
                            st.session_state.update({"logado": True, "user": prest_row['nome'].upper(), "perfil": "Prestador", "empresa_vinculada": ""})
                            time.sleep(0.5); st.rerun()
                    else: st.error("Usuário ou senha incorretos.")
            with tab_cadastro:
                with st.form("form_cad_prestador"):
                    c_cad1, c_cad2 = st.columns(2)
                    cad_nome = c_cad1.text_input("Nome Completo / Empresa do Guincho:")
                    cad_cpf = c_cad2.text_input("CPF ou CNPJ:")
                    cad_tel = c_cad1.text_input("Telefone (WhatsApp com DDD):")
                    cad_cidade = c_cad2.text_input("Cidade Base:")
                    cad_est = c_cad1.selectbox("Estado (UF):", ESTADOS_BR, index=ESTADOS_BR.index("RN"))
                    cad_tipo = c_cad2.multiselect("Serviços Prestados:", OPCOES_SERVICOS, default=["Guincho"])
                    cad_senha = st.text_input("Crie uma Senha para o aplicativo:", type="password")
                    if st.form_submit_button("Enviar Solicitação de Cadastro", use_container_width=True):
                        if not cad_nome or not cad_cpf or not cad_senha: st.error("Nome, CPF/CNPJ e Senha são obrigatórios!")
                        else:
                            prox_p = int(df_prestadores['id'].astype(float).max() + 1) if not df_prestadores.empty else 1
                            novo_p = pd.DataFrame([{'id': str(prox_p), 'nome': cad_nome.upper(), 'cpf': apenas_numeros_letras(cad_cpf), 'tipo': ", ".join(cad_tipo), 'telefone': apenas_numeros_letras(cad_tel), 'endereco': '', 'cidade': cad_cidade.upper(), 'cep': '', 'est': cad_est, 'status': 'Ativo', 'homologado': 'Pendente', 'senha': cad_senha, 'frota': '[]'}])
                            df_prestadores_temp = pd.concat([df_prestadores, novo_p], ignore_index=True)
                            sucesso, erro = salvar_dados(df_prestadores_temp, FILE_PRESTADORES)
                            if sucesso: st.success("✅ Cadastro enviado! Aguarde a aprovação."); time.sleep(2); st.rerun()
                            else: st.error("Erro ao salvar cadastro. Tente novamente.")
        else:
            st.markdown('<div class="subtitle">⚡ Operação Atendimento (Acesso Restrito)</div>', unsafe_allow_html=True)
            usuario_input = apenas_numeros_letras(st.text_input("Usuário (Nome da Empresa ou Central):"))
            senha_input = apenas_numeros_letras(st.text_input("Senha (CNPJ):", type="password"))
            if st.button("Entrar no Sistema", use_container_width=True):
                if usuario_input == "adrastreamentoveicular" and senha_input == "00000000000000":
                    st.session_state.update({"logado": True, "user": "AD Rastreamento Veicular (ADMIN)", "perfil": "Admin"})
                    st.query_params["session"] = "admin_ad"
                    time.sleep(0.5); st.rerun()
                else:
                    df_empresas_login = df_empresas.copy()
                    df_empresas_login['cnpj_comparar'] = df_empresas_login['cnpj'].astype(str).apply(apenas_numeros_letras)
                    df_empresas_login['nome_comparar'] = df_empresas_login['nome'].astype(str).apply(apenas_numeros_letras)
                    parceiro_valid = df_empresas_login[(df_empresas_login['cnpj_comparar'] == senha_input) & (df_empresas_login['nome_comparar'] == usuario_input)]
                    if not parceiro_valid.empty:
                        st.session_state.update({"logado": True, "user": parceiro_valid.iloc[0]['nome'].upper(), "perfil": "Parceiro", "empresa_vinculada": parceiro_valid.iloc[0]['nome']})
                        st.query_params["session"] = f"parc_{urllib.parse.quote(parceiro_valid.iloc[0]['nome'])}"
                        time.sleep(0.5); st.rerun()
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
    menu = st.tabs(["📋 Nova OS", "📊 Relatórios & PDF", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores", "💾 Backup", "🕵️ Auditoria", "💰 Financeiro"])
    
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
        cliente_id_os, cliente_nome_os, placa_alvo, veiculo_desc_alvo, empresa_os, plano_km_os, uf_cliente, cidade_cliente, valor_cobrado_os = "", "", "", "", "", "", "RN", "", "0,00"

        if tipo_atendimento == "Cliente Cadastrado":
            if df_clientes.empty: st.warning("Nenhum cliente cadastrado no sistema para busca.")
            else:
                busca = st.text_input("Digite o Nome, Placa ou CPF do cliente para buscar:", value=st.session_state.os_busca_val)
                st.session_state.os_busca_val = busca
                if not busca: st.info("👆 Digite o Nome, Placa ou CPF do cliente acima para iniciar o atendimento.")
                else:
                    df_clientes_busca = df_clientes.copy()
                    df_clientes_busca['cpf_limpo'] = df_clientes_busca['cpf'].apply(apenas_numeros_letras)
                    busca_limpa = apenas_numeros_letras(busca)
                    df_filtrado_cli = df_clientes_busca[df_clientes_busca['nome'].str.lower().str.contains(busca.lower(), na=False) | df_clientes_busca['pla'].str.lower().str.contains(busca.lower(), na=False) | df_clientes_busca['cpf_limpo'].str.contains(busca_limpa, na=False) | df_clientes_busca['veiculos_lista'].str.lower().str.contains(busca.lower(), na=False)]
                    
                    if df_filtrado_cli.empty: st.error("Nenhum cliente ou veículo encontrado com esse termo de busca.")
                    else:
                        opcoes_cli_os = {"": "Selecione um cliente..."}
                        for _, r in df_filtrado_cli.iterrows(): opcoes_cli_os[str(r['id'])] = f"{str(r['nome']).upper()} | Empresa: {str(r['emp_name']).upper()}"
                        idx_cli_os = list(opcoes_cli_os.keys()).index(st.session_state.os_cli_val) if st.session_state.os_cli_val in opcoes_cli_os else 0
                        c_target_os = st.selectbox("Selecione o Cliente:", options=list(opcoes_cli_os.keys()), format_func=lambda x: opcoes_cli_os[x], index=idx_cli_os)
                        st.session_state.os_cli_val = c_target_os
                        
                        if c_target_os != "":
                            cliente_dados = df_clientes[df_clientes['id'].astype(str) == c_target_os].iloc[0]
                            lista_frota_opcoes = []
                            if pd.notna(cliente_dados.get('veiculos_lista')) and cliente_dados['veiculos_lista']:
                                try:
                                    for v in json.loads(cliente_dados['veiculos_lista']):
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
                                plano_km_os, cidade_cliente, cliente_id_os, cliente_nome_os, empresa_os = str(cliente_dados.get('plano_km', 'N/D')), str(cliente_dados.get('cidade', '')).strip().upper(), str(c_target_os), str(cliente_dados['nome']), str(cliente_dados['emp_name'])
                                st.info(f"📍 Cliente: **{empresa_os.upper()}** | UF do Veículo: **{uf_cliente}**")
                                st.markdown(f'<div class="info-box">🛣️ PLANO KM CONTRATADO: {plano_km_os}</div>', unsafe_allow_html=True)
                                
                                status_cliente_os = str(cliente_dados.get('status', 'Ativo')).strip()
                                if status_cliente_os == 'Inativo':
                                    st.write("---")
                                    st.markdown('<div class="alert-box alert-danger" style="font-size: 16px; text-align: center;">🚫 ALERTA VERMELHO: CLIENTE INATIVO 🚫<br><span style="font-size: 14px; font-weight: normal;">Possível inadimplência ou cancelamento. O atendimento padrão está bloqueado.</span></div>', unsafe_allow_html=True)
                                    liberar_excecao = st.checkbox("⚠️ Ciente do status: Liberar Atendimento por Exceção (Autorização manual)")
                                    if liberar_excecao: pronto_para_prosseguir = True
                                    else: pronto_para_prosseguir = False
                                else: pronto_para_prosseguir = True
        else:
            st.info("📝 Digite as informações do atendimento avulso particular abaixo:")
            col_av1, col_av2 = st.columns(2)
            nome_avulso, tel_avulso = col_av1.text_input("Nome Completo do Cliente:"), col_av2.text_input("Telefone de Contato:")
            veiculo_avulso, placa_avulso = col_av1.text_input("Veículo (Modelo/Ano/Cor):"), col_av2.text_input("Placa do Veículo:")
            uf_cliente, cidade_cliente = col_av1.selectbox("Estado (UF) do Atendimento:", options=ESTADOS_BR, index=ESTADOS_BR.index("RN")), col_av2.text_input("Cidade do Atendimento:")
            valor_cobrado_os = col_av1.text_input("Valor Cobrado do Particular (R$):", value="0,00")
            cliente_id_os, cliente_nome_os, placa_alvo, veiculo_desc_alvo, empresa_os, plano_km_os = "AVULSO", nome_avulso, placa_avulso.upper().strip(), veiculo_avulso, "CLIENTE PARTICULAR (AVULSO)", "Particular"
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
                    with st.spinner("Registrando OS e sincronizando com a nuvem..."):
                        nova_id = int(df_os['id'].astype(float).max() + 1) if not df_os.empty else 1
                        nova_os = pd.DataFrame([{'id': str(nova_id), 'data_hora': obter_hora_str(), 'cliente_id': str(cliente_id_os), 'cliente_nome': str(cliente_nome_os).upper(), 'placa': placa_alvo, 'veiculo_desc': str(veiculo_desc_alvo).upper(), 'empresa': empresa_os, 'tipo_servico': tipo_servico, 'motivo': motivo_servico, 'prestador': f"{prestador_final} | Telefone/Zap: {tel_prestador_final}", 'localizacao': localizacao, 'destino': destino, 'obs': obs, 'status_os': "EM ATENDIMENTO", 'plano_km': plano_km_os, 'valor_cobrado': valor_cobrado_os}])
                        df_os_temp = pd.concat([df_os, nova_os], ignore_index=True)
                        sucesso, erro = salvar_dados(df_os_temp, FILE_OS)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "NOVA OS", f"Abriu chamado {nova_id} para a placa {placa_alvo}")
                            st.success(f"✅ Chamado Nº {nova_id} Aberto! Redirecionando...")
                            st.session_state.os_busca_val = ""
                            st.session_state.os_cli_val = ""
                            st.session_state.os_loc_val = ""
                            st.session_state.os_dest_val = ""
                            st.session_state.os_obs_val = ""
                            time.sleep(1.5)
                            st.rerun()
                        else: st.error(f"⚠️ Erro ao salvar OS na nuvem: {erro}")

    # === RELATÓRIOS E HISTÓRICO ===
    with menu[1]:
        st.subheader("📊 Gestão de Chamados e Relatórios")
        st.write("---")
        st.markdown("### 🛠️ Editar ou Excluir Chamado (OS)")
        st.info("Caso tenha lançado um acionamento para a placa errada, digite o ID da OS abaixo para corrigir ou cancelar.")
        
        os_id_edit = st.text_input("Digite o ID da OS:")
        if os_id_edit:
            os_encontrada = df_os[df_os['id'].astype(str) == str(os_id_edit)]
            if not os_encontrada.empty:
                row_os = os_encontrada.iloc[0]
                with st.form("form_edit_os"):
                    st.write(f"**Empresa:** {row_os.get('empresa','')} | **Cliente:** {row_os.get('cliente_nome','')} | **Data:** {row_os.get('data_hora','')}")
                    c_os1, c_os2 = st.columns(2)
                    nova_placa = c_os1.text_input("Placa do Veículo:", value=row_os['placa'])
                    
                    status_opcoes = ["EM ATENDIMENTO", "EM ROTA (VISTORIA OK)", "FINALIZADO PELO PRESTADOR", "ENCERRADO", "CANCELADO"]
                    idx_stat = status_opcoes.index(row_os['status_os'].upper()) if row_os['status_os'].upper() in status_opcoes else 0
                    novo_status = c_os2.selectbox("Status da OS:", status_opcoes, index=idx_stat)
                    
                    if st.form_submit_button("Salvar Correção da OS"):
                        with st.spinner("Atualizando OS..."):
                            df_os.loc[df_os['id'].astype(str) == str(os_id_edit), ['placa', 'status_os']] = [nova_placa.upper(), novo_status]
                            sucesso, erro = salvar_dados(df_os, FILE_OS)
                            if sucesso:
                                registrar_atividade(st.session_state.user, "CORREÇÃO DE OS", f"Editou a OS ID: {os_id_edit} | Nova Placa: {nova_placa.upper()} | Novo Status: {novo_status}")
                                st.success("✅ OS atualizada com sucesso! O cálculo de acionamento foi reajustado.")
                                time.sleep(1.5); st.rerun()
                            else: st.error(f"Erro na nuvem: {erro}")
                
                st.write("")
                if "os_del_confirm" not in st.session_state: st.session_state.os_del_confirm = None
                if st.session_state.os_del_confirm != os_id_edit:
                    if st.button("🗑️ Excluir esta OS permanentemente"):
                        st.session_state.os_del_confirm = os_id_edit
                        st.rerun()
                if st.session_state.get("os_del_confirm") == os_id_edit:
                    st.error(f"⚠️ Atenção: Deseja realmente excluir a OS {os_id_edit}?")
                    col_s, col_n = st.columns(2)
                    if col_s.button("✅ Sim, excluir OS"):
                        with st.spinner("Excluindo..."):
                            os_apagada = df_os[df_os['id'].astype(str) == str(os_id_edit)].iloc[0]
                            detalhes_exclusao_os = f"Apagou OS ID: {os_id_edit} | Cliente: {os_apagada['cliente_nome']} | Placa: {os_apagada['placa']} | Empresa: {os_apagada['empresa']}"
                            
                            df_os = df_os[df_os['id'].astype(str) != str(os_id_edit)]
                            sucesso, erro = salvar_dados(df_os, FILE_OS)
                            if sucesso:
                                registrar_atividade(st.session_state.user, "EXCLUSÃO OS", detalhes_exclusao_os)
                                st.success("🗑️ OS excluída! Taxa de acionamento atualizada.")
                                st.session_state.os_del_confirm = None
                                time.sleep(1.5); st.rerun()
                            else: st.error(f"Erro: {erro}")
                    if col_n.button("❌ Não, cancelar"):
                        st.session_state.os_del_confirm = None
                        st.rerun()
            else: st.warning("Nenhuma OS encontrada com esse ID.")

        st.write("---")
        if df_os.empty: st.info("Nenhuma OS registrada no sistema.")
        else:
            visao_relatorio = st.radio("Escolha a Visão:", ["🚨 OS em Andamento (Gerenciar)", "✅ Histórico e Gerar PDF (Finalizadas)", "Tabela Geral"], horizontal=True)
            if visao_relatorio == "🚨 OS em Andamento (Gerenciar)":
                st.markdown("### 🚨 Chamados Atualmente em Andamento")
                
                df_abertas = df_os[~df_os['status_os'].str.upper().isin(['ENCERRADO', 'CANCELADO'])]
                if df_abertas.empty: st.success("Nenhum chamado pendente no momento!")
                else:
                    lista_abertas = [f"OS Nº: {r['id']} | Status: {r['status_os']} | Placa: {r.get('placa','N/D')}" for _, r in df_abertas.iterrows()]
                    os_sel_str = st.selectbox("Selecione o chamado para Gerenciar / Dar Baixa:", lista_abertas)
                    os_id_alvo = os_sel_str.split("|")[0].replace("OS Nº:", "").strip()
                    row_os = df_abertas[df_abertas['id'].astype(str) == os_id_alvo].iloc[0]
                    status_dessa_os = str(row_os['status_os']).upper()

                    st.write("---")
                    st.markdown(f"#### Detalhes do Chamado Nº {os_id_alvo}")
                    prestador_info = str(row_os['prestador'])
                    tel_prestador_final = prestador_info.split("Telefone/Zap: ")[1].strip() if "Telefone/Zap: " in prestador_info else ""
                    cli_id_os = str(row_os['cliente_id'])
                    df_cli_orig = df_clientes[df_clientes['id'].astype(str) == cli_id_os]
                    tel_cliente_os = df_cli_orig.iloc[0]['tel'] if not df_cli_orig.empty else ""
                    
                    if status_dessa_os == 'FINALIZADO PELO PRESTADOR':
                        st.markdown('<div class="alert-box alert-success">🏁 O PRESTADOR CHEGOU AO DESTINO E FINALIZOU NO APLICATIVO! <br>A Vistoria está completa e o veículo foi entregue. Clique no botão abaixo para dar a Baixa Definitiva.</div>', unsafe_allow_html=True)
                    elif status_dessa_os == 'EM ROTA (VISTORIA OK)':
                        st.markdown('<div class="alert-box alert-info">📸 Vistoria de Entrada Concluída! O prestador já anexou as fotos e a assinatura e está a caminho do destino.</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="alert-box alert-danger">⏳ Aguardando Vistoria de Entrada pelo Prestador...</div>', unsafe_allow_html=True)
                    
                    # ATUALIZAÇÃO: Link no WhatsApp para o Portal do Prestador
                    texto_whatsapp = (f"*{str(row_os['empresa']).upper()} - ASSISTÊNCIA 24H*\n-----------------------------------------\n*Chamado Nº:* {row_os['id']}\n*Data/Hora:* {row_os['data_hora']}\n*Plano KM:* {row_os.get('plano_km', 'N/D')}\n*Valor Particular:* R$ {row_os.get('valor_cobrado', '0,00')}\n*Serviço:* {row_os['tipo_servico']} | *Motivo:* {row_os['motivo']}\n\n*Cliente:* {str(row_os['cliente_nome']).upper()}\n*Telefone do Cliente:* {tel_cliente_os}\n\n*Veículo:* {row_os.get('veiculo_desc', 'N/D')} - Placa: {row_os.get('placa', 'N/D')}\n\n*Origem:* {row_os['localizacao']}\n*Destino:* {row_os['destino']}\n\n*Obs:* {row_os['obs']}\n\n🔗 *Acesse seu painel para Vistoria:* https://mrssupqbb9ux69bi4qgisa.streamlit.app/?portal=prestador")
                    link_w = f"https://api.whatsapp.com/send?phone=55{tel_prestador_final}&text={urllib.parse.quote(texto_whatsapp)}"
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1: 
                        st.markdown(f'<a href="{link_w}" target="_blank"><button style="background-color: #25D366; color: white; padding: 10px 20px; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; width: 100%;">📲 Enviar OS para o Prestador</button></a>', unsafe_allow_html=True)
                    with col_btn2:
                        texto_botao = "🔒 Confirmar Entrega e Dar Baixa Definitiva (Encerrar OS)" if status_dessa_os == 'FINALIZADO PELO PRESTADOR' else "🔒 Forçar Encerramento da OS Manualmente"
                        if st.button(texto_botao):
                            with st.spinner("Encerrando OS e movendo para o Histórico..."):
                                df_os.loc[df_os['id'].astype(str) == os_id_alvo, 'status_os'] = "ENCERRADO"
                                sucesso, erro = salvar_dados(df_os, FILE_OS)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "ENCERRAMENTO OS", f"Finalizou o chamado {os_id_alvo}")
                                    st.success(f"🎉 Chamado Nº {os_id_alvo} Encerrado com sucesso! Ele foi movido para a aba de PDF.")
                                    time.sleep(1.5); st.rerun()
                                else: st.error(f"Erro na nuvem: {erro}")

            elif visao_relatorio == "✅ Histórico e Gerar PDF (Finalizadas)":
                st.markdown("### 📄 Localizar OS Finalizada (Por Placa ou Nome)")
                df_fechadas = df_os[df_os['status_os'].str.upper() == 'ENCERRADO'].sort_values(by='id', ascending=False)
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
                st.dataframe(df_os, use_container_width=True)

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
                    df_view_cli = df_view_cli[df_view_cli['nome'].str.contains(busca_cli_lista, case=False, na=False) | df_view_cli['pla'].str.contains(busca_cli_lista, case=False, na=False) | df_view_cli['cpf'].str.contains(busca_cli_lista, case=False, na=False) | df_view_cli['veiculos_lista'].str.lower().str.contains(busca_cli_lista.lower(), na=False)]
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
                                os_mes_atual = df_os_temp[(df_os_temp['empresa'].str.upper() == nome_emp) & (df_os_temp['status_os'].str.upper() == 'ENCERRADO') & (df_os_temp['data_hora'].dt.month == mes_a) & (df_os_temp['data_hora'].dt.year == ano_a)]
                                total_os_mes_emp = len(os_mes_atual)
                            taxa = (total_os_mes_emp / len(df_emp_filtrada) * 100) if len(df_emp_filtrada) > 0 else 0
                            st.markdown(f"📊 **De acordo com a base de {len(df_emp_filtrada)} veículos, a taxa de acionamento neste mês é de {taxa:.1f}%.**")
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
                    with st.spinner("Salvando novo cliente..."):
                        prox = int(df_clientes['id'].astype(float).max() + 1) if not df_clientes.empty else 1
                        novo = pd.DataFrame([{'id': str(prox), 'nome': nome, 'cpf': cpf, 'tel': tel, 'endereco': end_in, 'cidade': cid_in.upper(), 'cep': cep_in, 'plano_km': plano_km, 'vei': vei_prin, 'pla': pla_prin, 'est': est, 'emp_name': emp.upper(), 'status': status, 'veiculos_lista': frota_json_str}])
                        df_clientes_temp = pd.concat([df_clientes, novo], ignore_index=True)
                        sucesso, erro = salvar_dados(df_clientes_temp, FILE_CLIENTES)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "NOVO CLIENTE", f"Cadastrou {nome} para a empresa {emp} (Placa: {pla_prin})")
                            st.success("✅ Cliente cadastrado com sucesso!")
                            for k in ["cli_inc_nome", "cli_inc_cpf", "cli_inc_tel", "cli_inc_end", "cli_inc_cid", "cli_inc_cep"]: st.session_state[k] = ""
                            st.session_state.aba_cli = "Listar"
                            time.sleep(1); st.rerun()
                        else:
                            st.error(f"⚠️ Erro ao salvar cliente na nuvem: {erro}")
                            gerar_botao_whatsapp({"Ação": "Admin Cadastrando Cliente", "Nome": nome, "CPF": cpf, "Empresa": emp})
                        
        elif opcao_cli == "Importação em Lote":
            lista_empresas_disponiveis = [str(e['nome']).upper() for _, e in df_empresas.iterrows()] if not df_empresas.empty else ["NENHUMA EMPRESA CADASTRADA"]
            empresa_selecionada = st.selectbox("Selecione a Empresa Vinculada para esta importação:", options=lista_empresas_disponiveis)
            arquivo_csv_upload = st.file_uploader("Selecione o arquivo CSV da frota do parceiro", type=["csv"])
            if arquivo_csv_upload is not None:
                if st.button("Iniciar Importação e Salvar no GitHub"):
                    with st.spinner(f"Processando frota para a empresa {empresa_selecionada}..."):
                        sucesso, mensagem = importar_clientes_csv(arquivo_csv_upload, empresa_selecionada, df_clientes)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "IMPORTAÇÃO EM LOTE", f"Importou clientes/frota para {empresa_selecionada}")
                            st.success(mensagem); st.balloons(); time.sleep(2); st.session_state.aba_cli = "Listar"; st.rerun()
                        else: st.error(mensagem)
                    
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
                            with st.spinner("Sincronizando edição..."):
                                df_clientes.loc[df_clientes['id'].astype(str) == c_target, ['nome','cpf','tel','endereco','cidade','cep','plano_km','vei','pla','est','emp_name','status','veiculos_lista']] = [nome, cpf, tel, end_in, cid_in.upper(), cep_in, plano_km, vei_prin, pla_prin, est, emp.upper(), status, frota_json_str]
                                sucesso, erro = salvar_dados(df_clientes, FILE_CLIENTES)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EDIÇÃO DE CLIENTE", f"Editou os dados do cliente {nome} (Placa: {pla_prin})")
                                    st.success("✅ Alterações salvas com sucesso!"); st.session_state.aba_cli = "Listar"; time.sleep(1); st.rerun()
                                else:
                                    st.error(f"⚠️ Erro ao salvar edição na nuvem: {erro}")
                                    gerar_botao_whatsapp({"Ação": "Admin Editando Cliente", "Nome": nome})

        elif opcao_cli == "Excluir":
            if df_clientes.empty: st.warning("Nenhum cliente cadastrado.")
            else:
                opcoes_cli = {str(r['id']): f"{str(r['nome']).upper()} | CPF: {str(r['cpf'])} | Empresa: {str(r['emp_name']).upper()}" for _, r in df_clientes.iterrows()}
                c_target_del = st.selectbox("🔎 Selecione o Cliente para EXCLUIR:", options=[""] + list(opcoes_cli.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_cli[x])
                if c_target_del != "":
                    if "cli_del_confirm" not in st.session_state: st.session_state.cli_del_confirm = None
                    if st.session_state.cli_del_confirm != c_target_del:
                        if st.button("🗑️ Excluir permanentemente"): st.session_state.cli_del_confirm = c_target_del; st.rerun()
                    if st.session_state.get("cli_del_confirm") == c_target_del:
                        st.error(f"⚠️ Tem certeza absoluta que deseja excluir o cliente **{opcoes_cli[c_target_del]}**?")
                        col_sim, col_nao = st.columns(2)
                        if col_sim.button("✅ Sim, excluir cliente"):
                            with st.spinner("Apagando registro..."):
                                # ATUALIZAÇÃO: LOG DETALHADO DE EXCLUSÃO
                                cliente_apagado = df_clientes[df_clientes['id'].astype(str) == c_target_del].iloc[0]
                                detalhes_del = f"Apagou o cliente -> ID: {c_target_del} | Nome: {cliente_apagado['nome']} | CPF: {cliente_apagado.get('cpf','')} | Placa Principal: {cliente_apagado.get('pla','')} | Empresa: {cliente_apagado.get('emp_name','')}"
                                
                                df_clientes = df_clientes[df_clientes['id'].astype(str) != c_target_del]
                                sucesso, erro = salvar_dados(df_clientes, FILE_CLIENTES)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EXCLUSÃO CLIENTE", detalhes_del)
                                    st.success("🗑️ Cliente excluído permanentemente!"); st.session_state.cli_del_confirm = None; st.session_state.aba_cli = "Listar"; time.sleep(1); st.rerun()
                                else: st.error(f"Falha na nuvem: {erro}")
                        if col_nao.button("❌ Não, cancelar"): st.session_state.cli_del_confirm = None; st.rerun()

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
            c1, c2 = st.columns(2)
            n_emp_in = c1.text_input("Nome da Empresa:", value=st.session_state.get("emp_inc_nome", ""))
            st.session_state.emp_inc_nome = n_emp_in
            cnpj_raw = c2.text_input("CNPJ da Empresa:", value=st.session_state.get("emp_inc_cnpj", ""))
            st.session_state.emp_inc_cnpj = cnpj_raw
            resp_in = c1.text_input("Nome do Responsável:", value=st.session_state.get("emp_inc_resp", ""))
            st.session_state.emp_inc_resp = resp_in
            tel_e_raw = c2.text_input("Telefone da Central 24h:", value=st.session_state.get("emp_inc_tel", ""))
            st.session_state.emp_inc_tel = tel_e_raw
            mail_in = c1.text_input("E-mail corporativo:", value=st.session_state.get("emp_inc_mail", ""))
            st.session_state.emp_inc_mail = mail_in
            est_e = c2.selectbox("Selecione o Estado (UF) da Sede:", options=ESTADOS_BR, index=ESTADOS_BR.index("RN"))
            stat_e = c1.selectbox("Status Parceria:", ["Ativo", "Inativo"], index=0)
            modo_fat_e = st.selectbox("Modo de Faturamento:", ["Tradicional", "Performance (Escalonado)"], index=0)
            if st.button("Salvar Nova Empresa"):
                cnpj = apenas_numeros_letras(cnpj_raw)
                if not cnpj or not n_emp_in: st.error("CNPJ e Nome da Empresa são obrigatórios.")
                else:
                    with st.spinner("Salvando empresa..."):
                        novo_e = pd.DataFrame([{'cnpj': cnpj, 'nome': n_emp_in.upper(), 'responsavel': resp_in.upper(), 'telefone': apenas_numeros_letras(tel_e_raw), 'email': mail_in, 'est': est_e, 'status': stat_e, 'modo_faturamento': modo_fat_e}])
                        df_empresas_temp = pd.concat([df_empresas, novo_e], ignore_index=True)
                        sucesso, erro = salvar_dados(df_empresas_temp, FILE_EMPRESAS)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "NOVA EMPRESA", f"Cadastrou a empresa {n_emp_in.upper()} (CNPJ: {cnpj})")
                            st.success("✅ Empresa cadastrada com sucesso!"); st.session_state.aba_emp = "Listar"; time.sleep(1); st.rerun()
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
                    idx_modo_fat = ["Tradicional", "Performance (Escalonado)"].index(str(dados_e_ant.get('modo_faturamento', 'Tradicional'))) if str(dados_e_ant.get('modo_faturamento', 'Tradicional')) in ["Tradicional", "Performance (Escalonado)"] else 0
                    modo_fat_e = st.selectbox("Modo de Faturamento:", ["Tradicional", "Performance (Escalonado)"], index=idx_modo_fat)
                    if st.button("Salvar Alterações"):
                        cnpj = apenas_numeros_letras(cnpj_raw)
                        if not cnpj or not n_emp_in: st.error("CNPJ e Nome da Empresa são obrigatórios.")
                        else:
                            with st.spinner("Atualizando dados da empresa..."):
                                df_empresas.loc[df_empresas['cnpj'] == e_target, ['cnpj', 'nome','responsavel','telefone','email','est','status', 'modo_faturamento']] = [cnpj, n_emp_in.upper(), resp_in.upper(), apenas_numeros_letras(tel_e_raw), mail_in, est_e, stat_e, modo_fat_e]
                                sucesso, erro = salvar_dados(df_empresas, FILE_EMPRESAS)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EDIÇÃO EMPRESA", f"Editou a empresa {n_emp_in.upper()}")
                                    st.success("✅ Empresa atualizada com sucesso!"); st.session_state.aba_emp = "Listar"; time.sleep(1); st.rerun()
                                else: st.error(f"Erro na nuvem: {erro}")
        elif opcao_emp == "Excluir":
            if df_empresas.empty: st.warning("Nenhuma empresa cadastrada.")
            else:
                opcoes_emp = {str(r['cnpj']): f"{str(r['nome']).upper()} | CNPJ: {str(r['cnpj'])}" for _, r in df_empresas.iterrows()}
                e_target_del = st.selectbox("🔎 Selecione a Empresa para EXCLUIR:", options=[""] + list(opcoes_emp.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_emp[x])
                if e_target_del != "":
                    if "emp_del_confirm" not in st.session_state: st.session_state.emp_del_confirm = None
                    if st.session_state.emp_del_confirm != e_target_del:
                        if st.button("🗑️ Excluir permanentemente"): st.session_state.emp_del_confirm = e_target_del; st.rerun()
                    if st.session_state.get("emp_del_confirm") == e_target_del:
                        st.error(f"⚠️ Tem certeza que deseja excluir a empresa **{opcoes_emp[e_target_del]}**?")
                        col_sim, col_nao = st.columns(2)
                        if col_sim.button("✅ Sim, excluir empresa"):
                            with st.spinner("Excluindo empresa..."):
                                # ATUALIZAÇÃO: LOG DETALHADO
                                emp_apagada = df_empresas[df_empresas['cnpj'] == e_target_del].iloc[0]
                                detalhes_emp = f"Apagou a empresa -> CNPJ: {e_target_del} | Nome: {emp_apagada['nome']} | Resp: {emp_apagada.get('responsavel', '')}"
                                
                                df_empresas = df_empresas[df_empresas['cnpj'] != e_target_del]
                                sucesso, erro = salvar_dados(df_empresas, FILE_EMPRESAS)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EXCLUSÃO EMPRESA", detalhes_emp)
                                    st.success("🗑️ Empresa excluída permanentemente!"); st.session_state.emp_del_confirm = None; st.session_state.aba_emp = "Listar"; time.sleep(1); st.rerun()
                                else: st.error(f"Falha na nuvem: {erro}")
                        if col_nao.button("❌ Não, cancelar"): st.session_state.emp_del_confirm = None; st.rerun()

    # === PRESTADORES ===
    with menu[4]:
        st.subheader("🔧 Gerenciamento de Prestadores (Guinchos e Endereço)")
        pendentes = df_prestadores[df_prestadores['homologado'] == 'Pendente']
        if not pendentes.empty:
            st.error(f"⚠️ Atenção Administrativa: Existem {len(pendentes)} prestadores aguardando homologação! Eles se cadastraram via Portal externo.")
            for idx, p in pendentes.iterrows():
                with st.expander(f"Solicitação de: {p['nome']} - {p['est']}"):
                    st.write(f"**Tipo:** {p['tipo']} | **Telefone:** {p['telefone']} | **Cidade:** {p.get('cidade','N/D')}")
                    texto_zap = urllib.parse.quote(f"Olá *{str(p['nome']).upper()}*! \n\nSeu cadastro na plataforma de prestadores da *AD Rastreamento Veicular* foi analisado e *APROVADO*! ✅🚛\n\nVocê já pode acessar o seu painel exclusivo utilizando o seu Nome e a senha que você criou (ou seu CPF).\n\nSeja bem-vindo à nossa rede 24h!")
                    link_w_aprov = f"https://api.whatsapp.com/send?phone=55{apenas_numeros_letras(p['telefone'])}&text={texto_zap}"
                    st.markdown(f'<a href="{link_w_aprov}" target="_blank" style="text-decoration: none;"><button style="background-color: #25D366; color: white; padding: 6px 12px; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; margin-bottom: 10px;">📲 1º Clique aqui para Avisar no WhatsApp</button></a>', unsafe_allow_html=True)
                    col_h1, col_h2 = st.columns(2)
                    if col_h1.button("✅ 2º Confirmar Aprovação no Sistema", key=f"apr_{p['id']}"):
                        df_prestadores.loc[df_prestadores['id'] == p['id'], 'homologado'] = 'Aprovado'
                        sucesso, erro = salvar_dados(df_prestadores, FILE_PRESTADORES)
                        if sucesso: 
                            registrar_atividade(st.session_state.user, "APROVAÇÃO PRESTADOR", f"Aprovou o cadastro de {p['nome']}")
                            st.success("Aprovado com sucesso!"); time.sleep(1); st.rerun()
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
            c1, c2 = st.columns(2)
            n_prest_in = c1.text_input("Nome do Guincho/Prestador:", value=st.session_state.get("pre_inc_nome", ""))
            st.session_state.pre_inc_nome = n_prest_in
            cpf_p_raw = c2.text_input("CPF/CNPJ do Prestador:", value=st.session_state.get("pre_inc_cpf", ""))
            st.session_state.pre_inc_cpf = cpf_p_raw
            t_prest_lista = c1.multiselect("Tipos de Serviço Prestado:", options=OPCOES_SERVICOS, default=["Guincho"])
            tel_p_raw = c2.text_input("Telefone de Contato (Com DDD):", value=st.session_state.get("pre_inc_tel", ""))
            st.session_state.pre_inc_tel = tel_p_raw
            end_p_in = c1.text_input("Endereço / Base:", value=st.session_state.get("pre_inc_end", ""))
            st.session_state.pre_inc_end = end_p_in
            cid_p_in = c2.text_input("Cidade Base:", value=st.session_state.get("pre_inc_cid", ""))
            st.session_state.pre_inc_cid = cid_p_in
            cep_p_in = c1.text_input("CEP:", value=st.session_state.get("pre_inc_cep", ""))
            st.session_state.pre_inc_cep = cep_p_in
            est_p = c2.selectbox("Estado (UF) de Atuação:", options=ESTADOS_BR, index=ESTADOS_BR.index("RN"))
            stat_p = c1.selectbox("Status do Guincho:", ["Ativo", "Inativo"], index=0)
            if st.button("Salvar Novo Prestador"):
                cpf_p = apenas_numeros_letras(cpf_p_raw)
                t_prest = ", ".join(t_prest_lista)
                if not n_prest_in or not cpf_p: st.error("O Nome e o CPF/CNPJ do prestador são obrigatórios.")
                elif not t_prest_lista: st.error("Selecione ao menos um tipo de serviço prestado.")
                else:
                    with st.spinner("Salvando prestador..."):
                        prox_p = int(df_prestadores['id'].astype(float).max() + 1) if not df_prestadores.empty else 1
                        novo_p = pd.DataFrame([{'id': str(prox_p), 'nome': n_prest_in.upper(), 'cpf': cpf_p, 'tipo': t_prest, 'telefone': apenas_numeros_letras(tel_p_raw), 'endereco': end_p_in, 'cidade': cid_p_in.upper(), 'cep': cep_p_in, 'est': est_p, 'status': stat_p, 'homologado': 'Aprovado', 'senha': 'admin', 'frota': '[]'}])
                        df_prestadores_temp = pd.concat([df_prestadores, novo_p], ignore_index=True)
                        sucesso, erro = salvar_dados(df_prestadores_temp, FILE_PRESTADORES)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "NOVO PRESTADOR", f"Cadastrou prestador {n_prest_in.upper()} ({t_prest})")
                            st.success("✅ Prestador cadastrado com sucesso!"); st.session_state.aba_pre = "Listar"; time.sleep(1); st.rerun()
                        else:
                            st.error(f"Erro na nuvem: {erro}")
                            gerar_botao_whatsapp({"Ação": "Admin Cadastrando Prestador", "Nome": n_prest_in, "Serviços": t_prest})
        elif opcao_pre == "Editar":
            if df_prestadores.empty: st.warning("Nenhuma prestador cadastrado.")
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
                            with st.spinner("Atualizando prestador..."):
                                df_prestadores.loc[df_prestadores['id'].astype(str) == p_target, ['nome','cpf','tipo','telefone','endereco','cidade','cep','est','status']] = [n_prest_in.upper(), cpf_p, t_prest, apenas_numeros_letras(tel_p_raw), end_p_in, cid_p_in.upper(), cep_p_in, est_p, stat_p]
                                sucesso, erro = salvar_dados(df_prestadores, FILE_PRESTADORES)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EDIÇÃO PRESTADOR", f"Editou o prestador {n_prest_in.upper()}")
                                    st.success("✅ Prestador atualizado com sucesso!"); st.session_state.aba_pre = "Listar"; time.sleep(1); st.rerun()
                                else: st.error(f"Erro na nuvem: {erro}")
        elif opcao_pre == "Excluir":
            if df_prestadores.empty: st.warning("Nenhum prestador cadastrado.")
            else:
                opcoes_pre = {str(r['id']): f"{str(r['nome']).upper()} | Cidade: {str(r['cidade']).upper()} | Tipo: {str(r['tipo'])}" for _, r in df_prestadores.iterrows()}
                p_target_del = st.selectbox("🔎 Selecione o Prestador para EXCLUIR:", options=[""] + list(opcoes_pre.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_pre[x])
                if p_target_del != "":
                    if "pre_del_confirm" not in st.session_state: st.session_state.pre_del_confirm = None
                    if st.session_state.pre_del_confirm != p_target_del:
                        if st.button("🗑️ Excluir permanentemente"): st.session_state.pre_del_confirm = p_target_del; st.rerun()
                    if st.session_state.get("pre_del_confirm") == p_target_del:
                        st.error(f"⚠️ Tem certeza que deseja excluir o prestador **{opcoes_pre[p_target_del]}**?")
                        col_sim, col_nao = st.columns(2)
                        if col_sim.button("✅ Sim, excluir prestador"):
                            with st.spinner("Excluindo prestador..."):
                                # ATUALIZAÇÃO: LOG DETALHADO
                                pre_apagado = df_prestadores[df_prestadores['id'].astype(str) == p_target_del].iloc[0]
                                detalhes_pre = f"Apagou prestador -> ID: {p_target_del} | Nome: {pre_apagado['nome']} | Tipo: {pre_apagado.get('tipo','')}"
                                
                                df_prestadores = df_prestadores[df_prestadores['id'].astype(str) != p_target_del]
                                sucesso, erro = salvar_dados(df_prestadores, FILE_PRESTADORES)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EXCLUSÃO PRESTADOR", detalhes_pre)
                                    st.success("🗑️ Prestador excluído permanentemente!"); st.session_state.pre_del_confirm = None; st.session_state.aba_pre = "Listar"; time.sleep(1); st.rerun()
                                else: st.error(f"Falha na nuvem: {erro}")
                        if col_nao.button("❌ Não, cancelar"): st.session_state.pre_del_confirm = None; st.rerun()

    # === ABA 6: SEGURANÇA E BACKUP ===
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
            if os.path.exists(FILE_FINANCEIRO):
                with open(FILE_FINANCEIRO, "rb") as f: st.download_button("Baixar Relatório Financeiro (.csv)", f, file_name="banco_financeiro.csv", use_container_width=True)
        with c_b2:
            st.markdown("### 📤 2. Restaurar Sistema")
            uploaded_file = st.file_uploader("Arraste o arquivo de backup aqui para restaurar", type=['csv'])
            if uploaded_file is not None:
                if st.button(f"🚀 Restaurar dados de: {uploaded_file.name}"):
                    caminho_salvar = os.path.join(FOLDER, uploaded_file.name)
                    with open(caminho_salvar, "wb") as f: f.write(uploaded_file.getbuffer())
                    sucesso, erro = salvar_no_github(caminho_salvar)
                    if sucesso:
                        registrar_atividade(st.session_state.user, "RESTAURAÇÃO BACKUP", f"Restaurou o arquivo {uploaded_file.name}")
                        st.success(f"✅ Arquivo {uploaded_file.name} restaurado no sistema e salvo na nuvem com sucesso!"); time.sleep(2); st.rerun()
                    else: st.error(f"⚠️ Arquivo restaurado apenas localmente. Falha ao enviar para o GitHub: {erro}")

    # === ABA 7: AUDITORIA E LOGS (COM NOVA CAIXA DE DETALHES) ===
    with menu[6]:
        st.subheader("🕵️ Painel de Auditoria e Registro de Atividades")
        st.write("Acompanhe o histórico de alterações. Selecione o registro para ver detalhes ou excluí-lo.")
        if df_logs.empty: st.info("Nenhuma atividade registrada ainda.")
        else:
            df_logs_exibicao = df_logs.copy().sort_values(by='data_hora', ascending=False)
            busca_log = st.text_input("🔍 Buscar no registro:")
            if busca_log: df_logs_exibicao = df_logs_exibicao[df_logs_exibicao['usuario'].str.contains(busca_log, case=False, na=False) | df_logs_exibicao['detalhes'].str.contains(busca_log, case=False, na=False) | df_logs_exibicao['acao'].str.contains(busca_log, case=False, na=False)]
            st.write("---")
            
            df_logs_exibicao['idx_temp'] = df_logs_exibicao.index
            opcoes_log = {str(i): f"{r['data_hora']} - {r['usuario']} - {r['acao']}" for i, r in df_logs_exibicao.iterrows()}
            log_selecionado = st.selectbox("Selecione um registro para ver os Detalhes Completos ou Excluir:", options=[""] + list(opcoes_log.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_log[x])
            
            if log_selecionado != "":
                detalhe_row = df_logs_exibicao.loc[int(log_selecionado)]
                
                # ATUALIZAÇÃO: CAIXA DE DETALHAMENTO NO ADMIN
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #7B2CBF; margin-bottom: 15px;">
                    <p style="margin-bottom:5px;"><strong>🕒 Data/Hora:</strong> {detalhe_row['data_hora']}</p>
                    <p style="margin-bottom:5px;"><strong>👤 Usuário:</strong> {detalhe_row['usuario']}</p>
                    <p style="margin-bottom:5px;"><strong>⚙️ Ação:</strong> {detalhe_row['acao']}</p>
                    <p style="margin-bottom:5px;"><strong>📝 Detalhes Completos:</strong> {detalhe_row['detalhes']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("❌ Excluir este registro selecionado"):
                    with st.spinner("Removendo registro..."):
                        df_logs = df_logs.drop(int(log_selecionado))
                        df_logs.to_csv(FILE_LOGS, index=False)
                        salvar_no_github(FILE_LOGS)
                        st.success("Registro removido com sucesso!"); time.sleep(1); st.rerun()
            st.write("---")
            st.dataframe(df_logs_exibicao.drop(columns=['idx_temp']), use_container_width=True)
            st.write("")
            st.write("---")
            if "confirmar_limpeza_total" not in st.session_state: st.session_state.confirmar_limpeza_total = False
            if not st.session_state.confirmar_limpeza_total:
                if st.button("🗑️ LIMPAR TODO O HISTÓRICO"): st.session_state.confirmar_limpeza_total = True; st.rerun()
            if st.session_state.confirmar_limpeza_total:
                st.warning("⚠️ Tem certeza? Isso apagará todos os logs irrecuperavelmente.")
                c1, c2 = st.columns(2)
                if c1.button("✅ Sim, apagar tudo"):
                    df_logs_vazio = pd.DataFrame(columns=col_logs)
                    df_logs_vazio.to_csv(FILE_LOGS, index=False)
                    salvar_no_github(FILE_LOGS)
                    df_logs = df_logs_vazio
                    st.session_state.confirmar_limpeza_total = False; st.rerun()
                if c2.button("❌ Não"): st.session_state.confirmar_limpeza_total = False; st.rerun()

    # === ABA 8: GESTÃO FINANCEIRA ===
    with menu[7]:
        st.subheader("💰 Gestão Financeira - Controle de Recebimentos")
        st.write("Visão unificada do seu contas a receber. As empresas ativas aparecem automaticamente aqui e a taxa de acionamento é atualizada em tempo real.")
        
        # ATUALIZAÇÃO: Seletor Inteligente de Meses (Últimos 3 + Busca Específica)
        opcoes_meses_admin = get_ultimos_3_meses()
        escolha_mes_admin = st.selectbox("Selecione o Mês/Ano de Referência:", opcoes_meses_admin + ["Outro (Buscar por data)"])
        if escolha_mes_admin == "Outro (Buscar por data)":
            data_busca_admin = st.date_input("Escolha uma data para filtrar o mês/ano:")
            mes_filtro = data_busca_admin.strftime("%m/%Y")
        else:
            mes_filtro = escolha_mes_admin

        empresas_ativas = df_empresas[df_empresas['status'].str.upper() == 'ATIVO']
        
        if empresas_ativas.empty: st.warning("Nenhuma empresa ativa cadastrada para gerar o financeiro.")
        else:
            alterado = False
            for _, emp_row in empresas_ativas.iterrows():
                nome_emp = emp_row['nome'].upper()
                id_unico = f"{nome_emp}_{mes_filtro}"
                existe = df_financeiro[df_financeiro['id'] == id_unico] if not df_financeiro.empty and 'id' in df_financeiro.columns else pd.DataFrame()
                if existe.empty:
                    novo_fin = pd.DataFrame([{'id': id_unico, 'mes_ano': mes_filtro, 'empresa': nome_emp, 'valor_faturado': '0.00', 'valor_pago': '0.00', 'status': 'Pendente'}])
                    df_financeiro = pd.concat([df_financeiro, novo_fin], ignore_index=True)
                    alterado = True
            if alterado:
                df_financeiro.to_csv(FILE_FINANCEIRO, index=False)
                salvar_no_github(FILE_FINANCEIRO)
            
            lista_nomes_ativos = empresas_ativas['nome'].str.upper().tolist()
            df_fin_mes = df_financeiro[(df_financeiro['mes_ano'] == mes_filtro) & (df_financeiro['empresa'].str.upper().isin(lista_nomes_ativos))].copy()
            total_faturado_mes, total_recebido_mes, taxas_exibicao = 0.0, 0.0, []
            
            for idx, r_fin in df_fin_mes.iterrows():
                emp_name = r_fin['empresa']
                dados_emp_base = empresas_ativas[empresas_ativas['nome'].str.upper() == emp_name.upper()]
                if not dados_emp_base.empty:
                    modo_fat = str(dados_emp_base.iloc[0].get('modo_faturamento', '')).strip()
                    try: mes_s, ano_s = mes_filtro.split('/')
                    except: mes_s, ano_s = datetime.now().month, datetime.now().year
                    fatura_calc, _, _, taxa, _ = calcular_fatura_parceiro(emp_name, mes_s, ano_s, df_clientes, df_os)
                    taxas_exibicao.append(f"{taxa:.1f}%")
                    if modo_fat == 'Performance (Escalonado)':
                        df_fin_mes.at[idx, 'valor_faturado'] = f"{fatura_calc:.2f}"
                        df_financeiro.loc[df_financeiro['id'] == r_fin['id'], 'valor_faturado'] = f"{fatura_calc:.2f}"
                else: taxas_exibicao.append("0.0%")
                try: total_faturado_mes += float(str(df_fin_mes.at[idx, 'valor_faturado']).replace(',', '.'))
                except: pass
                try: total_recebido_mes += float(str(df_fin_mes.at[idx, 'valor_pago']).replace(',', '.'))
                except: pass
            
            inadimplencia = total_faturado_mes - total_recebido_mes if total_faturado_mes > total_recebido_mes else 0.0
            
            st.markdown("---")
            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1: st.markdown(f'<div class="metric-card"><div style="color: #666; font-size: 16px;">Total Faturado no Mês</div><div class="metric-value" style="color: #1976D2;">R$ {total_faturado_mes:.2f}</div></div>', unsafe_allow_html=True)
            with col_d2: st.markdown(f'<div class="metric-card"><div style="color: #666; font-size: 16px;">Total Recebido (Caixa)</div><div class="metric-value val-pago">R$ {total_recebido_mes:.2f}</div></div>', unsafe_allow_html=True)
            with col_d3: st.markdown(f'<div class="metric-card"><div style="color: #666; font-size: 16px;">Inadimplência / A Receber</div><div class="metric-value val-atrasado">R$ {inadimplencia:.2f}</div></div>', unsafe_allow_html=True)
            
            st.markdown("### Lançamentos")
            df_view_fin = df_fin_mes.copy()
            diferencas = []
            for _, r in df_view_fin.iterrows():
                try: 
                    vf, vp = float(str(r['valor_faturado']).replace(',','.')), float(str(r['valor_pago']).replace(',','.'))
                    diferencas.append(f"R$ {(vf - vp):.2f}")
                except: diferencas.append("R$ 0.00")
            df_view_fin['diferenca'] = diferencas
            df_view_fin['taxa_de_uso'] = taxas_exibicao
            st.dataframe(df_view_fin[['empresa', 'taxa_de_uso', 'valor_faturado', 'valor_pago', 'diferenca', 'status']].style.map(formatar_status_financeiro, subset=['status']), use_container_width=True)
            
            st.write("---")
            st.markdown("### ✏️ Editar Lançamento (Dar Baixa)")
            col_e1, col_e2 = st.columns(2)
            lista_empresas_fin = df_fin_mes['empresa'].tolist()
            emp_edit = col_e1.selectbox("Selecione a Empresa para dar baixa ou editar o status:", lista_empresas_fin)
            if emp_edit:
                row_edit = df_fin_mes[df_fin_mes['empresa'] == emp_edit].iloc[0]
                dados_emp_base_edit = empresas_ativas[empresas_ativas['nome'].str.upper() == emp_edit.upper()].iloc[0]
                modo_fat_edit = str(dados_emp_base_edit.get('modo_faturamento', '')).strip()
                with st.form("form_financeiro"):
                    st.write(f"**Empresa:** {emp_edit} | **Mês:** {mes_filtro}")
                    c_f1, c_f2, c_f3 = st.columns(3)
                    if modo_fat_edit == 'Performance (Escalonado)':
                        v_fat_atual = str(row_edit['valor_faturado'])
                        c_f1.text_input("Valor Calculado pelo Sistema (R$):", value=v_fat_atual, disabled=True)
                        val_fat_final = v_fat_atual
                    else:
                        v_fat_atual = str(row_edit['valor_faturado'])
                        val_fat_final = c_f1.text_input("Valor da Fatura Manual (R$):", value=v_fat_atual)
                    val_pago_final = c_f2.text_input("Valor Pago pelo Cliente (R$):", value=str(row_edit['valor_pago']))
                    status_final = c_f3.selectbox("Status:", ["Pendente", "Pago", "Atrasado"], index=["Pendente", "Pago", "Atrasado"].index(row_edit['status']))
                    try:
                        v1, v2 = float(val_fat_final.replace(',','.')), float(val_pago_final.replace(',','.'))
                        if modo_fat_edit == 'Performance (Escalonado)' and v2 < v1 and status_final == 'Pago': st.warning("⚠️ Atenção: O valor pago digitado é MENOR que a fatura calculada. A diferença ficará registrada na tabela.")
                    except: pass
                    if st.form_submit_button("Salvar Edição Financeira"):
                        with st.spinner("Atualizando registros financeiros..."):
                            df_financeiro.loc[df_financeiro['id'] == row_edit['id'], ['valor_faturado', 'valor_pago', 'status']] = [val_fat_final, val_pago_final, status_final]
                            sucesso, erro = salvar_dados(df_financeiro, FILE_FINANCEIRO)
                            if sucesso:
                                registrar_atividade(st.session_state.user, "BAIXA FINANCEIRA", f"Editou o faturamento de {emp_edit} ({mes_filtro}) para status {status_final}")
                                st.success("✅ Registro atualizado com sucesso!"); time.sleep(1); st.rerun()
                            else: st.error(f"Falha na nuvem: {erro}")

# ===================================================================================
# INTERFACE DE PARCEIROS RESTRITA (COM NOVAS ABAS DE FINANCEIRO E AUDITORIA)
# ===================================================================================
elif st.session_state.perfil == "Parceiro":
    menu_parceiro = st.tabs(["👥 Cadastro de Clientes", "📋 Histórico de Chamados", "💰 Meu Financeiro", "🕵️ Auditoria"])
    
    with menu_parceiro[0]:
        df_filtrado_p = df_clientes[df_clientes['emp_name'].str.lower() == st.session_state.empresa_vinculada.lower()]
        mes_atual_taxa_p = datetime.now().month
        ano_atual_taxa_p = datetime.now().year
        base_clientes_taxa_p = len(df_filtrado_p)
        total_os_mes_p = 0
        if not df_os.empty:
            df_os_temp_p = df_os.copy()
            df_os_temp_p['data_hora'] = pd.to_datetime(df_os_temp_p['data_hora'], errors='coerce')
            os_mes_atual_p = df_os_temp_p[(df_os_temp_p['empresa'].str.upper() == st.session_state.empresa_vinculada.upper()) & (df_os_temp_p['status_os'].str.upper() == 'ENCERRADO') & (df_os_temp_p['data_hora'].dt.month == mes_atual_taxa_p) & (df_os_temp_p['data_hora'].dt.year == ano_atual_taxa_p)]
            total_os_mes_p = len(os_mes_atual_p)
        taxa_p = (total_os_mes_p / base_clientes_taxa_p * 100) if base_clientes_taxa_p > 0 else 0
        st.markdown(f"📊 **De acordo com a base de {base_clientes_taxa_p} veículos, a taxa de acionamento neste mês é de {taxa_p:.1f}%.**")
        st.write("---")
        
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
            uf_padrao_parceiro = "RN"
            if not df_empresas.empty:
                emp_dados = df_empresas[df_empresas['nome'].str.upper() == st.session_state.empresa_vinculada.upper()]
                if not emp_dados.empty: uf_padrao_parceiro = str(emp_dados.iloc[0].get('est', 'RN')).upper()
            idx_uf_parceiro = ESTADOS_BR.index(uf_padrao_parceiro) if uf_padrao_parceiro in ESTADOS_BR else ESTADOS_BR.index("RN")

            p_est = col_pb1.selectbox("UF do Veículo:", options=ESTADOS_BR, index=idx_uf_parceiro)
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
                    with st.spinner("Salvando novo registro e sincronizando com a nuvem..."):
                        prox_id = int(df_clientes['id'].astype(float).max() + 1) if not df_clientes.empty else 1
                        novo_reg = pd.DataFrame([{'id': str(prox_id), 'nome': p_nome_in.upper(), 'cpf': p_cpf, 'tel': apenas_numeros_letras(p_tel_raw), 'endereco': p_end_in, 'cidade': p_cid_in.upper(), 'cep': p_cep_in, 'plano_km': p_plano_km, 'vei': vei_prin_p, 'pla': pla_prin_p, 'est': p_est, 'emp_name': st.session_state.empresa_vinculada.upper(), 'status': p_stat, 'veiculos_lista': frota_json_str_p}])
                        df_clientes_temp = pd.concat([df_clientes, novo_reg], ignore_index=True)
                        sucesso, erro = salvar_dados(df_clientes_temp, FILE_CLIENTES)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "NOVO CLIENTE PARCEIRO", f"Cadastrou o cliente {p_nome_in.upper()}")
                            st.success("✅ Registro salvo com sucesso!")
                            for k in ["part_inc_nome", "part_inc_cpf", "part_inc_tel", "part_inc_end", "part_inc_cid", "part_inc_cep"]: st.session_state[k] = ""
                            st.session_state.aba_part = "Visualizar"; time.sleep(1); st.rerun()
                        else:
                            st.error("⚠️ Atenção: Instabilidade na Conexão com a Nuvem.")
                            gerar_botao_whatsapp({"Ação": "Novo Cadastro", "Parceiro": st.session_state.empresa_vinculada.upper(), "Cliente": p_nome_in.upper(), "CPF": p_cpf, "Placa": pla_prin_p, "Erro": erro})

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
                            with st.spinner("Atualizando cadastro na nuvem..."):
                                df_clientes.loc[df_clientes['id'].astype(str) == part_target, ['nome','cpf','tel','endereco','cidade','cep','plano_km','vei','pla','est','status','veiculos_lista']] = [p_nome_in.upper(), p_cpf, apenas_numeros_letras(p_tel_raw), p_end_in, p_cid_in.upper(), p_cep_in, p_plano_km, vei_prin_p, pla_prin_p, p_est, p_stat, frota_json_str_p]
                                sucesso, erro = salvar_dados(df_clientes, FILE_CLIENTES)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EDIÇÃO CLIENTE PARCEIRO", f"Editou o cliente {p_nome_in.upper()}")
                                    st.success("✅ Registro atualizado com sucesso!"); st.session_state.aba_part = "Visualizar"; time.sleep(1); st.rerun()
                                else:
                                    st.error("⚠️ Atenção: Falha de comunicação com a nuvem da Central AD.")
                                    gerar_botao_whatsapp({"Ação": "Edição de Cadastro", "Parceiro": st.session_state.empresa_vinculada.upper(), "Cliente": p_nome_in.upper(), "Placa Principal": pla_prin_p})

        elif op_part == "Excluir Cliente":
            if df_filtrado_p.empty: st.warning("Nenhum cliente cadastrado.")
            else:
                opcoes_dict_p = {str(r['id']): f"{str(r['nome']).upper()} | CPF: {str(r['cpf'])}" for _, r in df_filtrado_p.iterrows()}
                part_target_del = st.selectbox("🔎 Selecione o cliente para EXCLUIR:", options=[""] + list(opcoes_dict_p.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_dict_p[x])
                if part_target_del != "":
                    if "part_del_confirm" not in st.session_state: st.session_state.part_del_confirm = None
                    if st.session_state.part_del_confirm != part_target_del:
                        if st.button("🗑️ Excluir permanentemente"): st.session_state.part_del_confirm = part_target_del; st.rerun()
                    if st.session_state.get("part_del_confirm") == part_target_del:
                        st.error(f"⚠️ Tem certeza que deseja excluir permanentemente o cliente **{opcoes_dict_p[part_target_del]}**?")
                        col_sim, col_nao = st.columns(2)
                        if col_sim.button("✅ Sim, excluir cliente"):
                            with st.spinner("Excluindo registro..."):
                                # ATUALIZAÇÃO: LOG DETALHADO DO PARCEIRO
                                cli_p_apagado = df_clientes[df_clientes['id'].astype(str) == part_target_del].iloc[0]
                                detalhes_del_p = f"Apagou o cliente -> ID: {part_target_del} | Nome: {cli_p_apagado['nome']} | CPF: {cli_p_apagado.get('cpf','')} | Placa Principal: {cli_p_apagado.get('pla','')}"
                                
                                df_clientes = df_clientes[df_clientes['id'].astype(str) != part_target_del]
                                sucesso, erro = salvar_dados(df_clientes, FILE_CLIENTES)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EXCLUSÃO CLIENTE PARCEIRO", detalhes_del_p)
                                    st.success("🗑️ Cliente excluído permanentemente!"); st.session_state.part_del_confirm = None; st.session_state.aba_part = "Visualizar"; time.sleep(1); st.rerun()
                                else: st.error(f"Erro na nuvem: {erro}")
                        if col_nao.button("❌ Não, cancelar"): st.session_state.part_del_confirm = None; st.rerun()

    with menu_parceiro[1]:
        df_os_parceiro = df_os[df_os['empresa'].str.lower() == st.session_state.empresa_vinculada.lower()]
        if df_os_parceiro.empty: st.info("Nenhum acionamento registrado para sua empresa.")
        else: st.dataframe(df_os_parceiro, use_container_width=True)

    # ATUALIZAÇÃO: Aba Financeira Restrita para a Empresa
    with menu_parceiro[2]:
        st.subheader("💰 Gestão Financeira (Meu Faturamento)")
        st.write("Confira as faturas e o status dos pagamentos exclusivos da sua empresa de forma atualizada.")
        
        opcoes_meses_p = get_ultimos_3_meses()
        escolha_mes_p = st.selectbox("Mês de Referência:", opcoes_meses_p + ["Outro (Buscar por data)"], key="mes_parc")
        if escolha_mes_p == "Outro (Buscar por data)":
            data_busca_p = st.date_input("Data de referência:", key="data_parc")
            mes_filtro_p = data_busca_p.strftime("%m/%Y")
        else:
            mes_filtro_p = escolha_mes_p
            
        df_fin_parc = df_financeiro[(df_financeiro['mes_ano'] == mes_filtro_p) & (df_financeiro['empresa'].str.upper() == st.session_state.empresa_vinculada.upper())]
        
        if df_fin_parc.empty:
            st.info("Nenhum faturamento gerado ou disponível para visualização neste mês ainda.")
        else:
            row_fin = df_fin_parc.iloc[0]
            v_fat = str(row_fin.get('valor_faturado', '0.00'))
            v_pag = str(row_fin.get('valor_pago', '0.00'))
            status_f = str(row_fin.get('status', 'Pendente')).strip()
                
            st.markdown("---")
            c_f1, c_f2, c_f3 = st.columns(3)
            c_f1.markdown(f'<div class="metric-card"><div style="color: #666; font-size: 16px;">Sua Fatura Total</div><div class="metric-value" style="color: #1976D2;">R$ {v_fat}</div></div>', unsafe_allow_html=True)
            c_f2.markdown(f'<div class="metric-card"><div style="color: #666; font-size: 16px;">Valor que Consta como Pago</div><div class="metric-value val-pago">R$ {v_pag}</div></div>', unsafe_allow_html=True)
            
            cor_borda = "#4CAF50" if status_f == "Pago" else "#E53935" if status_f == "Atrasado" else "#f57f17"
            bg_cor = "#e8f5e9" if status_f == "Pago" else "#ffebee" if status_f == "Atrasado" else "#fff8e1"
            c_f3.markdown(f'<div class="metric-card" style="border: 2px solid {cor_borda}; background-color: {bg_cor};"><div style="color: #666; font-size: 16px;">Status no Sistema Central</div><div class="metric-value" style="color: {cor_borda}; font-size: 28px;">{status_f.upper()}</div></div>', unsafe_allow_html=True)

    # ATUALIZAÇÃO: Aba de Auditoria Restrita para a Empresa (Apenas Leitura)
    with menu_parceiro[3]:
        st.subheader("🕵️ Auditoria e Histórico de Atividades")
        st.write("Verifique com transparência as ações realizadas exclusivamente pelo seu usuário no sistema.")
        
        df_logs_parc = df_logs[df_logs['usuario'].str.upper() == st.session_state.user.upper()].copy()
        
        if df_logs_parc.empty:
            st.info("Nenhuma atividade registrada por sua empresa ainda.")
        else:
            df_logs_parc = df_logs_parc.sort_values(by='data_hora', ascending=False)
            busca_log_p = st.text_input("🔍 Buscar no seu registro (ex: placa, nome):")
            if busca_log_p:
                df_logs_parc = df_logs_parc[df_logs_parc['detalhes'].str.contains(busca_log_p, case=False, na=False) | df_logs_parc['acao'].str.contains(busca_log_p, case=False, na=False)]
            
            st.write("---")
            opcoes_log_p = {str(i): f"{r['data_hora']} - {r['acao']}" for i, r in df_logs_parc.iterrows()}
            log_sel_p = st.selectbox("Selecione um registro para ver os Detalhes Completos:", options=[""] + list(opcoes_log_p.keys()), format_func=lambda x: "Selecione para ver o detalhamento..." if x == "" else opcoes_log_p[x])
            
            if log_sel_p != "":
                detalhe_row = df_logs_parc.loc[int(log_sel_p)]
                
                # CAIXA DE DETALHAMENTO NO PARCEIRO (Sem botões de exclusão)
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #7B2CBF; margin-bottom: 15px;">
                    <p style="margin-bottom:5px;"><strong>🕒 Data/Hora:</strong> {detalhe_row['data_hora']}</p>
                    <p style="margin-bottom:5px;"><strong>⚙️ Ação:</strong> {detalhe_row['acao']}</p>
                    <p style="margin-bottom:5px;"><strong>📝 Detalhes Completos do Evento:</strong> {detalhe_row['detalhes']}</p>
                </div>
                """, unsafe_allow_html=True)
                
            st.write("---")
            st.dataframe(df_logs_parc[['data_hora', 'acao', 'detalhes']], use_container_width=True)

# --- INTERFACE DE PRESTADOR (GUINCHO) RESTRITA ---
elif st.session_state.perfil == "Prestador":
    st.subheader(f"🚛 Meu Painel de Atendimento | Prestador: {st.session_state.user}")
    st.write("---")

    df_os_prest = df_os[~df_os['status_os'].str.upper().isin(['ENCERRADO', 'CANCELADO'])]
    meus_chamados = df_os_prest[df_os_prest['prestador'].str.upper().str.contains(str(st.session_state.user).upper(), na=False)]
    
    if meus_chamados.empty:
        st.success("🎉 Nenhuma ordem de serviço pendente para você no momento. Aguarde novos chamados.")
    else:
        for _, os_row in meus_chamados.iterrows():
            st.markdown(f"### 🚨 Chamado Nº {os_row['id']}")
            status_atual_prestador = str(os_row.get('status_os', '')).upper()
            
            c1, c2 = st.columns(2)
            c1.write(f"**Cliente:** {os_row['cliente_nome']}")
            c1.write(f"**Serviço:** {os_row['tipo_servico']} ({os_row['motivo']})")
            c1.write(f"**Veículo:** {os_row.get('veiculo_desc', 'N/D')} | **Placa:** {os_row['placa']}")
            c2.write(f"**Local de Retirada:** {os_row['localizacao']}")
            c2.write(f"**Destino:** {os_row['destino']}")
            c2.write(f"**Observações:** {os_row['obs']}")
            
            if status_atual_prestador == 'FINALIZADO PELO PRESTADOR':
                st.success("🏁 Você já chegou ao destino e finalizou esta OS! O veículo foi entregue. Aguardando a Central AD confirmar o encerramento do chamado no sistema.")
            else:
                # Controle de Vistoria
                vistoria_path = os.path.join(FOLDER, "vistorias", str(os_row['id']))
                os.makedirs(vistoria_path, exist_ok=True)
                fotos_necessarias = ['Frente', 'Traseira', 'Lateral_Esquerda', 'Lateral_Direita', 'Placa', 'Assinatura']
                vistoria_completa = True
                for f in fotos_necessarias:
                    if not os.path.exists(os.path.join(vistoria_path, f"{f}.jpg")):
                        vistoria_completa = False
                
                if not vistoria_completa:
                    st.markdown('<div class="alert-box alert-danger">⚠️ AÇÃO OBRIGATÓRIA: Realize a Vistoria de Entrada ANTES de carregar o veículo no guincho. O botão de finalizar está bloqueado.</div>', unsafe_allow_html=True)
                    
                    if "passo_vistoria" not in st.session_state: st.session_state.passo_vistoria = 0
                    passo = st.session_state.passo_vistoria
                    nomes_exibicao = ["1. Foto da Frente", "2. Foto da Traseira", "3. Lateral Esquerda", "4. Lateral Direita", "5. Foco na Placa", "6. Assinatura Digital do Cliente"]
                    
                    if passo < 5: # Fotos 0 a 4
                        st.markdown(f"#### 📸 Etapa Atual: {nomes_exibicao[passo]}")
                        img_capturada = st.camera_input("Tirar Foto Agora", key=f"cam_{os_row['id']}_{fotos_necessarias[passo]}")
                        if img_capturada:
                            with open(os.path.join(vistoria_path, f"{fotos_necessarias[passo]}.jpg"), "wb") as f_img:
                                f_img.write(img_capturada.getbuffer())
                            st.success(f"✅ Foto salva!")
                            if st.button("Confirmar e Avançar ➡️", key=f"btn_next_{os_row['id']}_{fotos_necessarias[passo]}"):
                                st.session_state.passo_vistoria += 1
                                st.rerun()
                        if passo > 0:
                            if st.button("🔄 Reiniciar Fotos", key=f"btn_reset_{os_row['id']}"):
                                st.session_state.passo_vistoria = 0; st.rerun()
                                
                    elif passo == 5: # Assinatura com Canvas
                        st.markdown(f"#### ✍️ Etapa Atual: {nomes_exibicao[passo]}")
                        st.info("Peça para o cliente assinar no quadro abaixo com o dedo. (Pode virar o celular de lado para ter mais espaço).")
                        canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 0.3)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=250, drawing_mode="freedraw", key=f"canvas_{os_row['id']}")
                        
                        if st.button("Salvar Assinatura e Concluir Vistoria", type="primary"):
                            if canvas_result.image_data is not None:
                                with st.spinner("Salvando assinatura e avisando a central..."):
                                    img = Image.fromarray((canvas_result.image_data).astype(np.uint8))
                                    img = img.convert("RGB") 
                                    img.save(os.path.join(vistoria_path, "Assinatura.jpg"))
                                    
                                    # MUDA O STATUS PARA "EM ROTA" E SALVA
                                    df_os.loc[df_os['id'] == os_row['id'], 'status_os'] = 'EM ROTA (VISTORIA OK)'
                                    salvar_dados(df_os, FILE_OS)
                                    
                                    st.session_state.passo_vistoria += 1
                                    st.rerun()
                            else: st.error("Peça ao cliente para assinar antes de salvar.")
                        if st.button("🔄 Voltar para a última foto", key=f"btn_voltar_ass"):
                            st.session_state.passo_vistoria = 4; st.rerun()
                    else: st.session_state.passo_vistoria = 0; st.rerun()
                
                else: # Vistoria Ok, Em Rota
                    st.markdown('<div class="alert-box alert-success">✅ VISTORIA DE ENTRADA CONCLUÍDA. Veículo liberado para o transporte.</div>', unsafe_allow_html=True)
                    st.markdown('<div class="info-box">ℹ️ ATENÇÃO EXTREMA: Desloque-se até o destino. Só clique no botão abaixo para FINALIZAR a OS após chegar no local e descarregar o veículo com segurança.</div>', unsafe_allow_html=True)
                    
                    if st.button(f"🏁 CHEGUEI E DESCARREGUEI (Finalizar OS)", key=f"btn_fin_{os_row['id']}"):
                        with st.spinner("Avisando a Central sobre a entrega..."):
                            df_os.loc[df_os['id'] == os_row['id'], 'status_os'] = 'FINALIZADO PELO PRESTADOR'
                            sucesso, erro = salvar_dados(df_os, FILE_OS)
                            if sucesso:
                                registrar_atividade(st.session_state.user, "ENTREGA DE VEÍCULO (PRESTADOR)", f"Prestador entregou a OS {os_row['id']}.")
                                st.success("🎉 Missão Cumprida! A Central foi notificada para dar a baixa.")
                                time.sleep(2); st.rerun()
                            else: st.error(f"Erro ao avisar central: {erro}")
