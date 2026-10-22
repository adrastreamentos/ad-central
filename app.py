import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import urllib.parse
import base64
import time
import requests
import json
import numpy as np
import calendar
import streamlit.components.v1 as components
import plotly.express as px
from supabase import create_client
from PIL import Image
import io

try:
    from streamlit_drawable_canvas import st_canvas
    CANVAS_AVAILABLE = True
except ImportError:
    CANVAS_AVAILABLE = False

st.set_page_config(page_title="Central 24h - AD Rastreamento", layout="wide", page_icon="🔒")

# ===================================================================================
# CONEXÃO COM O BANCO DE DADOS EM NUVEM (SUPABASE)
# ===================================================================================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def iniciar_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = iniciar_supabase()

# ===================================================================================
# CONSTANTES DE NEGÓCIO E PLANOS
# ===================================================================================
ESTADOS_BR = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
PLANOS_KM = ["Sem Limite", "50km", "100km", "150km", "200km", "300km", "400km", "500km"]
OPCOES_SERVICOS = ["Guincho", "Pane Seca", "Pane Elétrica", "Borracheiro", "Chaveiro"]
OPCOES_DIAS_VENC = ["5", "10", "15", "20", "25", "30", "31"]

LIMITES_ANUAIS = {"GUINCHO": 2, "PANE SECA": 1, "PANE ELÉTRICA": 1, "BORRACHEIRO": 1, "CHAVEIRO": 1}

MODOS_FATURAMENTO = [
    "Tradicional", 
    "Performance (Escalonado)", 
    "Plano Frota Pequena (0 a 20 veículos)", 
    "Plano Até 40 Veículos (Opção A - 2 Acionamentos)", 
    "Plano Até 40 Veículos (Opção B - 4 Acionamentos)"
]

FROTA_COL_CONFIG = {
    "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Carro", "Moto", "Caminhonete/SUV", "Van", "Caminhão", "Utilitário", "Outro"], default="Carro", required=True),
    "Modelo/Ano": st.column_config.TextColumn("Modelo/Ano/Cor", required=True),
    "Placa": st.column_config.TextColumn("Placa", required=True),
    "Blindado": st.column_config.CheckboxColumn("Blindado?", default=False)
}

MARCAS_MOTO = ['YAMAHA', 'HONDA', 'SUZUKI', 'KAWASAKI', 'SHINERAY', 'DAFRA', 'TRAXX', 'BROS', 'TITAN', 'BIZ', 'XRE', 'POP', 'PCX', 'NMAX', 'CB']

# ===================================================================================
# ESTILIZAÇÃO CSS CORPORATIVA REFINADA (DESIGN PREMIUM)
# ===================================================================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    ::-webkit-scrollbar { width: 7px; height: 7px; }
    ::-webkit-scrollbar-thumb { background: #d1c4e9; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #7B2CBF; }
    
    .main-title { 
        font-size: 30px; 
        font-weight: 900; 
        background: linear-gradient(135deg, #7B2CBF 0%, #E53935 100%); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        text-align: center; 
        margin-bottom: 4px; 
        letter-spacing: -0.5px;
    }
    .subtitle { 
        font-size: 13px; 
        color: #64748b; 
        text-align: center; 
        margin-bottom: 22px; 
        font-weight: 600; 
        text-transform: uppercase; 
        letter-spacing: 1.2px; 
    }
    
    .section-title { 
        font-size: 19px !important; 
        font-weight: 800 !important; 
        color: #1e1b4b !important; 
        margin-top: 5px !important; 
        margin-bottom: 16px !important; 
        display: flex; 
        align-items: center; 
        gap: 8px; 
        letter-spacing: -0.3px;
    }
    
    .stTabs [data-baseweb="tab"] { 
        font-size: 13px; 
        font-weight: 600; 
        background-color: #f8fafc; 
        border: 1px solid #e2e8f0; 
        color: #475569; 
        border-radius: 6px 6px 0 0;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #7B2CBF; 
        color: white !important; 
        border-color: #7B2CBF;
    }
    
    div.stButton > button:first-child { 
        background: linear-gradient(135deg, #7B2CBF 0%, #6a1b9a 100%); 
        color: white; 
        border-radius: 8px; 
        font-weight: 700; 
        font-size: 13px; 
        border: none;
        box-shadow: 0 2px 6px rgba(123, 44, 191, 0.25);
        transition: all 0.2s ease;
    }
    div.stButton > button:first-child:hover { 
        background: linear-gradient(135deg, #E53935 0%, #c62828 100%); 
        color: white; 
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(229, 57, 53, 0.35);
    }
    
    /* CARDS DE MÉTRICAS EXECUTIVOS */
    .metric-card-pro { 
        background: #ffffff; 
        border-radius: 12px; 
        padding: 18px 16px; 
        text-align: left; 
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04); 
        margin-bottom: 14px; 
        border: 1px solid #e2e8f0; 
        position: relative;
        overflow: hidden;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card-pro:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(123, 44, 191, 0.1);
    }
    .card-bar-purple { position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #7B2CBF, #9d4edd); }
    .card-bar-blue   { position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #1976D2, #60a5fa); }
    .card-bar-red    { position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #E53935, #f87171); }
    .card-bar-green  { position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #2E7D32, #4ade80); }
    
    .metric-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
    .metric-title-pro { color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; }
    .metric-badge { font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 12px; }
    .badge-purple { background: #f3e8ff; color: #7B2CBF; }
    .badge-blue   { background: #eff6ff; color: #1976D2; }
    .badge-red    { background: #fee2e2; color: #dc2626; }
    .badge-green  { background: #dcfce7; color: #15803d; }
    .metric-value-pro { font-size: 30px; font-weight: 900; letter-spacing: -1px; margin: 0; line-height: 1; }
    .metric-footer-note { font-size: 11px; color: #94a3b8; margin-top: 8px; font-weight: 500; }

    /* CONTAINERS DE GRÁFICOS */
    .dash-box-pro { 
        background: #ffffff; 
        border-radius: 14px; 
        padding: 18px 20px; 
        border: 1px solid #e2e8f0; 
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.03); 
        margin-bottom: 18px; 
    }
    .dash-box-header { 
        display: flex; 
        align-items: center; 
        justify-content: space-between; 
        padding-bottom: 12px; 
        border-bottom: 1px solid #f1f5f9; 
        margin-bottom: 14px; 
    }
    .dash-box-title-pro { 
        font-size: 14px; 
        font-weight: 800; 
        color: #1e1b4b; 
        text-transform: uppercase; 
        letter-spacing: 0.6px; 
        display: flex; 
        align-items: center; 
        gap: 8px; 
    }
    
    /* LINHAS DE STATUS E DETALHAMENTO */
    .status-row-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 12px;
        margin-bottom: 6px;
        background: #f8fafc;
        border-radius: 8px;
        border: 1px solid #f1f5f9;
        font-size: 12.5px;
    }
    .status-row-left { display: flex; align-items: center; gap: 8px; font-weight: 600; color: #334155; }
    .status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
    .status-row-right { display: flex; align-items: center; gap: 8px; }
    .status-pill-count { font-weight: 800; color: #0f172a; }
    .status-pill-pct { font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 6px; }

    .alert-box { padding: 14px; border-radius: 8px; margin: 12px 0; border-left: 5px solid; font-weight: 500; font-size: 14px; }
    .alert-danger { background-color: #ffebee; color: #c62828; border-color: #E53935; }
    .alert-success { background-color: #e8f5e9; color: #2e7d32; border-color: #4CAF50; }
    .info-box { background-color: #f8fafc; color: #334155; border-color: #7B2CBF; padding: 14px; border-radius: 8px; margin: 12px 0; border-left: 5px solid #7B2CBF; font-weight: 500; line-height: 1.5; font-size: 13.5px; }
    .val-pago { color: #2e7d32; } .val-atrasado { color: #E53935; }
    </style>
""", unsafe_allow_html=True)

# ===================================================================================
# FUNÇÕES GLOBAIS E LEITURA DE DADOS NA NUVEM
# ===================================================================================
def obter_hora_brasilia(): return datetime.now(timezone(timedelta(hours=-3)))
def obter_hora_str(): return obter_hora_brasilia().strftime("%Y-%m-%d %H:%M:%S")
def apenas_numeros_letras(texto): return "".join(caractere for caractere in str(texto) if caractere.isalnum()).strip().lower()

def mascarar_telefone(tel):
    t = apenas_numeros_letras(tel)
    if len(t) >= 10: return f"({t[:2]}) {t[2]}****-**{t[-2:]}"
    return "(**) *****-****"

def mascarar_placa(placa):
    p = apenas_numeros_letras(placa).upper()
    if len(p) >= 6: return f"{p[0]}**•*{p[-2:]}"
    return "Oculta"

def comprimir_imagem_b64(img_file, max_size=(800, 800)):
    if img_file is None: return ""
    try:
        img = Image.open(img_file).convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=60)
        return base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        return ""

def buscar_endereco_por_cep(cep):
    cep_limpo = apenas_numeros_letras(str(cep))
    if len(cep_limpo) == 8:
        try:
            res = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", timeout=5)
            if res.status_code == 200:
                dados = res.json()
                if "erro" not in dados:
                    rua = dados.get("logradouro", "")
                    bairro = dados.get("bairro", "")
                    cidade = dados.get("localidade", "")
                    uf = dados.get("uf", "")
                    end_completo = f"{rua}, Bairro {bairro}, {cidade}-{uf} | Número/Ref: "
                    return end_completo, bairro, cidade, uf
        except: pass
    return None, "", "", ""

def exportar_pdf_html_oficial(df_os, df_clientes, nome_arquivo):
    if df_os.empty: return "<p style='color: red;'>Erro: Nenhuma OS encontrada para gerar o relatório.</p>"
    r = df_os.iloc[0]
    
    fotos_html = ""
    doc_cliente = "N/D"
    fotos_str = str(r.get('fotos_vistoria', ''))
    
    if fotos_str and fotos_str.lower() != 'nan' and '{' in fotos_str:
        try:
            fotos_dict = json.loads(fotos_str)
            doc_cliente = fotos_dict.get('doc_cliente', 'N/D')
            
            fotos_html = "<h3 style='color: #7B2CBF; margin-top: 20px; border-bottom: 1px solid #ccc; padding-bottom: 5px;'>📸 Vistoria Fotográfica</h3><div style='display: flex; gap: 15px; flex-wrap: wrap; margin-top: 10px;'>"
            for k, label in [('frente', 'Frente'), ('traseira', 'Traseira'), ('lat_dir', 'Lateral Direita'), ('lat_esq', 'Lateral Esquerda')]:
                if fotos_dict.get(k):
                    fotos_html += f"<div style='text-align:center;'><p style='font-size:13px; font-weight:bold; margin-bottom:5px; color:#555;'>{label}</p><img src='data:image/jpeg;base64,{fotos_dict[k]}' style='max-height: 180px; border: 2px solid #ddd; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);' /></div>"
            fotos_html += "</div>"
        except: pass

    ass_html = ""
    ass_str = str(r.get('assinatura_cliente', ''))
    if ass_str and ass_str.lower() not in ['nan', 'none', '']:
        ass_html = f"""
        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 2px solid #7B2CBF; margin-top: 25px;'>
            <h3 style='color: #7B2CBF; margin-top: 0; border-bottom: 1px solid #ccc; padding-bottom: 5px;'>✍️ Termo de Responsabilidade e Assinatura</h3>
            <p style='font-size: 14px; margin-bottom: 8px;'><strong>Documento Identificador (CPF/RG):</strong> <span class='destaque'>{doc_cliente}</span></p>
            <p style='font-size: 12px; color: #555; margin-bottom: 12px;'>O cliente ou responsável atesta que o serviço foi concluído e os dados do veículo conferem.</p>
            <div style='text-align: center;'>
                <img src='data:image/png;base64,{ass_str}' style='max-height: 140px; border: 2px solid #ddd; border-radius: 6px; background-color: #fff;' onerror="this.src='data:image/jpeg;base64,{ass_str}';" />
            </div>
        </div>
        """

    html = f"""
    <html>
        <head>
            <meta charset="utf-8">
            <title>Relatório de OS #{r['id']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; color: #333; }}
                h2 {{ color: #7B2CBF; border-bottom: 2px solid #E53935; padding-bottom: 5px; }}
                .info-box {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 20px; border-left: 4px solid #7B2CBF; line-height: 1.6; }}
                .info-box p {{ margin: 6px 0; font-size: 14px; }}
                .destaque {{ font-weight: bold; color: #E53935; }}
            </style>
        </head>
        <body>
            <h2>Relatório Oficial de Ordem de Serviço - AD Rastreamento Veicular</h2>
            <div class="info-box">
                <p><strong>Número da OS:</strong> #{r['id']}</p>
                <p><strong>Data e Hora do Chamado:</strong> {r['data_hora']}</p>
                <p><strong>Empresa Parceira:</strong> {r.get('empresa', 'N/D')}</p>
                <p><strong>Cliente Atendido:</strong> {r['cliente_nome']}</p>
                <p><strong>Veículo Solicitado:</strong> {r.get('veiculo_desc', 'N/D')}</p>
                <p><strong>Placa do Veículo:</strong> <span class="destaque">{r['placa']}</span></p>
                <p><strong>Tipo de Serviço:</strong> {r['tipo_servico']} ({r.get('motivo','N/D')})</p>
                <p><strong>Origem (Localização):</strong> {r.get('localizacao','N/D')}</p>
                <p><strong>Destino:</strong> {r.get('destino','N/D')}</p>
                <p><strong>Observações:</strong> {r.get('obs','Nenhuma')}</p>
                <p><strong>Prestador Acionado / Guincheiro:</strong> {r.get('motorista_nome', r['prestador'])}</p>
            </div>
            {fotos_html}
            {ass_html}
            <br><br>
            <p style="font-size: 12px; color: #666; text-align: center; margin-top: 30px; border-top: 1px solid #ccc; padding-top: 10px;"><em>Documento gerado automaticamente pelo sistema operacional Central AD 24h.</em></p>
        </body>
    </html>
    """
    b64 = base64.b64encode(html.encode('utf-8')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{nome_arquivo}.html" target="_blank" style="display: inline-block; padding: 10px 20px; background-color: #E53935; color: white; text-align: center; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 13px;">📥 Baixar Extrato de OS com Assinatura (PDF/HTML)</a>'

@st.cache_data(ttl=60, show_spinner=False)
def carregar_dados(tabela, col_obr):
    try:
        res = supabase.table(tabela).select("*").execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=col_obr)
        df.columns = df.columns.str.strip().str.lower()
        for col in col_obr:
            if col not in df.columns: 
                df[col] = datetime.now().strftime("%Y-%m-%d") if col == 'data_cadastro' else "" 
        for col in df.columns: 
            df[col] = df[col].fillna("").astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        return df
    except Exception as e: 
        return pd.DataFrame(columns=col_obr)

def salvar_dados(df, tabela):
    try:
        df_limpo = df.copy()
        for col in df_limpo.columns:
            df_limpo[col] = df_limpo[col].fillna("").astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        registros = df_limpo.to_dict(orient="records")
        if registros:
            supabase.table(tabela).upsert(registros).execute()
        st.cache_data.clear()
        return True, "Sucesso"
    except Exception as e: 
        return False, str(e)

def deletar_registro_banco(tabela, coluna_id, valor_id):
    try:
        supabase.table(tabela).delete().eq(coluna_id, str(valor_id)).execute()
        st.cache_data.clear()
        return True, "Sucesso"
    except Exception as e: 
        return False, str(e)

def registrar_atividade(usuario, acao, detalhes):
    global df_logs
    novo_log = {'data_hora': obter_hora_str(), 'usuario': usuario, 'acao': acao, 'detalhes': detalhes}
    df_novo = pd.DataFrame([novo_log])
    df_logs = pd.concat([df_logs, df_novo], ignore_index=True)
    try:
        supabase.table(FILE_LOGS).insert(novo_log).execute()
    except: pass

FILE_CLIENTES = "clientes"
FILE_EMPRESAS = "empresas"
FILE_PRESTADORES = "prestadores"
FILE_OS = "ordens_servico"
FILE_LOGS = "logs"
FILE_FINANCEIRO = "financeiro"
FILE_LOC = "localizacoes"
FILE_NPS = "nps"

col_cli = ['id','nome','cpf','tel','endereco','bairro','cidade','cep','plano_km','est','emp_name','status','vei','pla','vei_2','pla_2','veiculos_lista', 'data_cadastro']
col_emp = ['cnpj','nome','responsavel','telefone','email','est','status', 'modo_faturamento', 'dia_vencimento', 'data_ativacao']
col_pre = ['id','nome','cpf','tipo','telefone','endereco','bairro','cidade','cep','est','status','homologado','senha','frota']
col_os = ['id','data_hora','cliente_id','cliente_nome','cliente_tel','placa','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os','veiculo_desc','plano_km','valor_cobrado','motorista_nome','motorista_tel','fotos_vistoria','assinatura_cliente']
col_fin = ['id', 'mes_ano', 'empresa', 'valor_faturado', 'valor_pago', 'status']
col_logs = ['data_hora', 'usuario', 'acao', 'detalhes']
col_loc = ['placa', 'data_hora', 'link_maps']
col_nps = ['id_os', 'data_hora', 'nota_nps', 'nota_central', 'nota_guincho', 'comentario', 'status_nps']

df_clientes = carregar_dados(FILE_CLIENTES, col_cli)
df_empresas = carregar_dados(FILE_EMPRESAS, col_emp)
df_prestadores = carregar_dados(FILE_PRESTADORES, col_pre)
df_os = carregar_dados(FILE_OS, col_os)
df_financeiro = carregar_dados(FILE_FINANCEIRO, col_fin)
df_logs = carregar_dados(FILE_LOGS, col_logs)
df_loc = carregar_dados(FILE_LOC, col_loc)
df_nps = carregar_dados(FILE_NPS, col_nps)

# ===================================================================================
# DASHBOARD REESTRUTURADO E COMPACTO (VISUAL PREMIUM PROFISSIONAL)
# ===================================================================================
def gerar_laudo_atendimentos_html(empresa_filtro, total_veiculos, total_os, servicos_df):
    data_atual = obter_hora_brasilia().strftime("%d/%m/%Y às %H:%M")
    linhas_tabela = ""
    for _, row in servicos_df.iterrows():
        linhas_tabela += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #edf2f7; font-weight: 600; color: #1e293b;">{row['Serviço']}</td>
            <td style="padding: 10px; border-bottom: 1px solid #edf2f7; text-align: center; color: #475569;">{row['Quantidade']} chamado(s)</td>
            <td style="padding: 10px; border-bottom: 1px solid #edf2f7; text-align: right; color: #7B2CBF; font-weight: 800;">{row['Porcentagem']:.1f}%</td>
        </tr>
        """
        
    html = f"""
    <html>
        <head>
            <meta charset="utf-8">
            <title>Laudo Operacional de Atendimentos - AD Rastreamento</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; padding: 25px; color: #1e293b; max-width: 780px; margin: 0 auto; background: #fff; }}
                h2 {{ color: #7B2CBF; border-bottom: 2px solid #E53935; padding-bottom: 8px; margin-bottom: 4px; font-size: 22px; font-weight: 800; }}
                .sub {{ color: #64748b; font-size: 12px; margin-bottom: 22px; text-transform: uppercase; letter-spacing: 0.5px; }}
                .kpi-container {{ display: flex; gap: 14px; margin-bottom: 24px; }}
                .kpi-card {{ flex: 1; background: #f8fafc; padding: 14px; border-radius: 8px; border: 1px solid #e2e8f0; border-left: 4px solid #7B2CBF; }}
                .kpi-card h4 {{ margin: 0; font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 0.6px; }}
                .kpi-card p {{ margin: 6px 0 0 0; font-size: 20px; font-weight: 900; color: #0f172a; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 14px; font-size: 13px; }}
                th {{ background-color: #7B2CBF; color: white; padding: 10px; text-align: left; font-weight: 700; }}
            </style>
        </head>
        <body>
            <h2>AD RASTREAMENTO VEICULAR — LAUDO OPERACIONAL</h2>
            <div class="sub">Relatório de Inteligência e Incidência de Atendimentos 24h | Gerado em: {data_atual}</div>
            
            <div class="kpi-container">
                <div class="kpi-card">
                    <h4>Empresa / Escopo</h4>
                    <p>{empresa_filtro.upper()}</p>
                </div>
                <div class="kpi-card">
                    <h4>Frota Ativa Mapeada</h4>
                    <p>{total_veiculos} veículos</p>
                </div>
                <div class="kpi-card">
                    <h4>Total Ocorrências</h4>
                    <p>{total_os} chamados</p>
                </div>
            </div>

            <h3 style="color: #1e1b4b; font-size: 15px; margin-bottom: 8px; font-weight: 800;">📊 Distribuição Percentual de Eventos</h3>
            <table>
                <thead>
                    <tr>
                        <th>Tipo de Ocorrência</th>
                        <th style="text-align: center;">Quantidade</th>
                        <th style="text-align: right;">Participação (%)</th>
                    </tr>
                </thead>
                <tbody>
                    {linhas_tabela}
                </tbody>
            </table>

            <br>
            <p style="font-size: 11px; color: #94a3b8; text-align: center; border-top: 1px solid #edf2f7; padding-top: 10px;">
                <em>Este laudo técnico foi consolidado automaticamente pela Central de Operações AD Rastreamento Veicular.</em>
            </p>
        </body>
    </html>
    """
    b64 = base64.b64encode(html.encode('utf-8')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="Laudo_Atendimentos_{empresa_filtro}_{int(time.time())}.html" target="_blank" style="text-decoration: none;"><button style="background: linear-gradient(135deg, #7B2CBF, #5e17eb); color: white; padding: 12px 20px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; width: 100%; font-size: 13px; box-shadow: 0 4px 12px rgba(123, 44, 191, 0.25);">📥 Baixar Laudo Executivo (PDF/HTML)</button></a>'

def renderizar_dashboard(empresa_filtro="Todas"):
    data_atual_rotulo = obter_hora_brasilia().strftime("%d/%m/%Y • %H:%M")
    
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
        <div class="section-title" style="margin: 0 !important;">📊 Indicadores Operacionais da Central 24h</div>
        <div style="background: #f1f5f9; padding: 4px 12px; border-radius: 20px; font-size: 11px; color: #64748b; font-weight: 700;">
            🕒 Atualizado: {data_atual_rotulo}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if empresa_filtro != "Todas":
        df_os_dash = df_os[df_os['empresa'].str.upper() == empresa_filtro.upper()].copy()
        df_cli_dash = df_clientes[(df_clientes['emp_name'].str.upper() == empresa_filtro.upper()) & (df_clientes['status'].str.strip() == 'Ativo')].copy()
    else:
        df_os_dash = df_os.copy()
        df_cli_dash = df_clientes[df_clientes['status'].str.strip() == 'Ativo'].copy()

    total_veiculos = 0
    for _, r_cli in df_cli_dash.iterrows():
        placas_extraidas = []
        if pd.notna(r_cli.get('veiculos_lista')) and str(r_cli['veiculos_lista']).strip() not in ['', '[]', 'nan']:
            try:
                for v in json.loads(str(r_cli['veiculos_lista'])):
                    p = str(v.get('Placa', '')).strip().upper().replace("-","").replace(" ","")
                    if len(p) >= 6 and p not in ['NAN', 'N/D']: placas_extraidas.append(p)
            except: pass
        if not placas_extraidas:
            p1 = str(r_cli.get('pla', '')).strip().upper().replace("-","").replace(" ","")
            if len(p1) >= 6 and p1 not in ['NAN', 'N/D']: placas_extraidas.append(p1)
            p2 = str(r_cli.get('pla_2', '')).strip().upper().replace("-","").replace(" ","")
            if len(p2) >= 6 and p2 not in ['NAN', 'N/D']: placas_extraidas.append(p2)
        total_veiculos += len(placas_extraidas)

    total_os = len(df_os_dash)
    os_em_andamento = len(df_os_dash[~df_os_dash['status_os'].str.upper().isin(['ENCERRADO', 'CANCELADO'])])
    os_concluidas = len(df_os_dash[df_os_dash['status_os'].str.upper() == 'ENCERRADO'])

    # KPI CARDS MODERNOS
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""
        <div class="metric-card-pro">
            <div class="card-bar-purple"></div>
            <div class="metric-header">
                <span class="metric-title-pro">🚗 Frota Ativa Mapeada</span>
                <span class="metric-badge badge-purple">Monitorada</span>
            </div>
            <div class="metric-value-pro" style="color: #7B2CBF;">{total_veiculos}</div>
            <div class="metric-footer-note">Veículos cadastrados com cobertura ativa</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="metric-card-pro">
            <div class="card-bar-blue"></div>
            <div class="metric-header">
                <span class="metric-title-pro">🛠️ Total de Atendimentos</span>
                <span class="metric-badge badge-blue">{os_concluidas} finalizados</span>
            </div>
            <div class="metric-value-pro" style="color: #1976D2;">{total_os}</div>
            <div class="metric-footer-note">Volume histórico de ordens geradas</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c3:
        alerta_vermelho = "box-shadow: 0 0 0 2px #ef4444;" if os_em_andamento > 0 else ""
        cor_aberto = "#E53935" if os_em_andamento > 0 else "#2e7d32"
        badge_cor = "badge-red" if os_em_andamento > 0 else "badge-green"
        rotulo_aberto = "Requer Ação" if os_em_andamento > 0 else "Normalizado"
        
        st.markdown(f"""
        <div class="metric-card-pro" style="{alerta_vermelho}">
            <div class="card-bar-red"></div>
            <div class="metric-header">
                <span class="metric-title-pro">🚨 Chamados em Aberto</span>
                <span class="metric-badge {badge_cor}">{rotulo_aberto}</span>
            </div>
            <div class="metric-value-pro" style="color: {cor_aberto};">{os_em_andamento}</div>
            <div class="metric-footer-note">OS em trânsito, atendimento ou pendente</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    if total_os > 0:
        col_chart1, col_chart2 = st.columns(2)

        cores_grafico_servicos = ['#7B2CBF', '#E53935', '#1976D2', '#059669', '#d97706', '#9333ea', '#64748b']

        with col_chart1:
            st.markdown('<div class="dash-box-pro">', unsafe_allow_html=True)
            st.markdown("""
                <div class="dash-box-header">
                    <div class="dash-box-title-pro">🛠️ Incidência de Atendimentos</div>
                    <span style="font-size: 11px; color: #64748b; font-weight: 700;">POR MODALIDADE</span>
                </div>
            """, unsafe_allow_html=True)
            
            servicos_counts = df_os_dash['tipo_servico'].value_counts().reset_index()
            servicos_counts.columns = ['Serviço', 'Quantidade']
            servicos_counts['Porcentagem'] = (servicos_counts['Quantidade'] / total_os) * 100

            fig_incidencia = px.pie(
                servicos_counts, 
                names='Serviço', 
                values='Quantidade', 
                hole=0.68,
                color_discrete_sequence=cores_grafico_servicos
            )
            fig_incidencia.update_traces(
                textposition='outside',
                textinfo='percent',
                hovertemplate="<b>%{label}</b><br>Chamados: %{value}<br>Participação: %{percent}<extra></extra>"
            )
            fig_incidencia.update_layout(
                margin=dict(t=15, b=15, l=15, r=15),
                height=260,
                showlegend=True,
                legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5, font=dict(size=11)),
                annotations=[dict(text=f"<b>{total_os}</b><br><span style='font-size:10px; color:#64748b;'>TOTAL</span>", x=0.5, y=0.5, font_size=17, showarrow=False)]
            )
            st.plotly_chart(fig_incidencia, use_container_width=True)

            st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
            
            for idx_s, r in servicos_counts.iterrows():
                cor_item = cores_grafico_servicos[idx_s % len(cores_grafico_servicos)]
                st.markdown(f"""
                <div class="status-row-item">
                    <div class="status-row-left">
                        <span class="status-dot" style="background-color: {cor_item};"></span>
                        <span>{r['Serviço']}</span>
                    </div>
                    <div class="status-row-right">
                        <span class="status-pill-count">{r['Quantidade']} chamados</span>
                        <span class="status-pill-pct" style="background: #f1f5f9; color: {cor_item};">{r['Porcentagem']:.1f}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

        cores_grafico_status = ['#059669', '#E53935', '#d97706', '#1976D2', '#7B2CBF']

        with col_chart2:
            st.markdown('<div class="dash-box-pro">', unsafe_allow_html=True)
            st.markdown("""
                <div class="dash-box-header">
                    <div class="dash-box-title-pro">🚦 Status Operacional dos Chamados</div>
                    <span style="font-size: 11px; color: #64748b; font-weight: 700;">FLUXO ATUAL</span>
                </div>
            """, unsafe_allow_html=True)
            
            status_counts = df_os_dash['status_os'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Quantidade']
            status_counts['Porcentagem'] = (status_counts['Quantidade'] / total_os) * 100

            fig_status = px.pie(
                status_counts, 
                names='Status', 
                values='Quantidade', 
                hole=0.68,
                color_discrete_sequence=cores_grafico_status
            )
            fig_status.update_traces(
                textposition='outside',
                textinfo='percent',
                hovertemplate="<b>%{label}</b><br>Volume: %{value}<br>Percentual: %{percent}<extra></extra>"
            )
            fig_status.update_layout(
                margin=dict(t=15, b=15, l=15, r=15),
                height=260,
                showlegend=True,
                legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5, font=dict(size=11)),
                annotations=[dict(text=f"<b>{total_os}</b><br><span style='font-size:10px; color:#64748b;'>TOTAL</span>", x=0.5, y=0.5, font_size=17, showarrow=False)]
            )
            st.plotly_chart(fig_status, use_container_width=True)

            st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
            
            for idx_st, r in status_counts.iterrows():
                cor_item = cores_grafico_status[idx_st % len(cores_grafico_status)]
                st.markdown(f"""
                <div class="status-row-item">
                    <div class="status-row-left">
                        <span class="status-dot" style="background-color: {cor_item};"></span>
                        <span>{r['Status']}</span>
                    </div>
                    <div class="status-row-right">
                        <span class="status-pill-count">{r['Quantidade']} chamado(s)</span>
                        <span class="status-pill-pct" style="background: #f1f5f9; color: {cor_item};">{r['Porcentagem']:.1f}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

        st.write("---")
        if "exibir_laudo" not in st.session_state:
            st.session_state.exibir_laudo = False

        if not st.session_state.exibir_laudo:
            if st.button("📊 Processar Laudo Executivo do Mês", use_container_width=True, key=f"btn_proc_laudo_{empresa_filtro}"):
                st.session_state.exibir_laudo = True
                st.rerun()
        else:
            st.markdown("""
            <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid #7B2CBF; border-radius: 12px; padding: 18px; margin-bottom: 18px; box-shadow: 0 4px 14px rgba(123, 44, 191, 0.05);">
                <h3 style="color: #7B2CBF; margin-top:0; font-size: 18px; font-weight: 800;">📋 Laudo Executivo de Atendimentos 24h</h3>
                <p style="color: #64748b; font-size: 13px; margin-bottom: 0;">Análise consolidada e inteligência de ocorrências da frota no período apurado.</p>
            </div>
            """, unsafe_allow_html=True)
            
            data_atual_proc = obter_hora_brasilia().strftime("%d/%m/%Y às %H:%M")
            st.caption(f"🕒 Processado e auditado em: {data_atual_proc}")
            
            col_l1, col_l2, col_l3 = st.columns(3)
            col_l1.metric("Empresa / Unidade", empresa_filtro.upper())
            col_l2.metric("Frota Ativa Mapeada", f"{total_veiculos} veículos")
            col_l3.metric("Total Ocorrências", f"{total_os} chamados")
            
            st.markdown("##### 📊 Distribuição Analítica por Tipo de Serviço:")
            df_laudo_vis = servicos_counts.copy()
            df_laudo_vis['Porcentagem (%)'] = df_laudo_vis['Porcentagem'].apply(lambda x: f"{x:.1f}%")
            df_laudo_vis = df_laudo_vis.rename(columns={'Serviço': 'Tipo de Ocorrência', 'Quantidade': 'Acionamentos Registrados'})
            st.dataframe(df_laudo_vis[['Tipo de Ocorrência', 'Acionamentos Registrados', 'Porcentagem (%)']], use_container_width=True)
            
            st.write("")
            col_laudo_btn1, col_laudo_btn2 = st.columns(2)
            with col_laudo_btn1:
                st.markdown(gerar_laudo_atendimentos_html(empresa_filtro, total_veiculos, total_os, servicos_counts), unsafe_allow_html=True)
            with col_laudo_btn2:
                if st.button("❌ Fechar Laudo Executivo", use_container_width=True, key=f"btn_close_laudo_{empresa_filtro}"):
                    st.session_state.exibir_laudo = False
                    st.rerun()

    else:
        st.info("Nenhuma ordem de serviço registrada para montar os indicadores do período.")

# ===================================================================================
# TABELAS DE PREÇOS E FAIXAS
# ===================================================================================
TABELA_ESCALONADO = {
    "Enquadramento Base (Até 3%)":   {"max": 3.0,   "50km": 6.90,   "100km": 8.90,   "200km": 11.20,  "Sem Limite": 11.20},
    "Enquadramento 3% a 5%":         {"max": 5.0,   "50km": 9.10,   "100km": 13.15,  "200km": 17.20,  "Sem Limite": 17.20},
    "Enquadramento 5% a 7%":         {"max": 7.0,   "50km": 11.80,  "100km": 17.20,  "200km": 22.60,  "Sem Limite": 22.60},
    "Enquadramento 7% a 10%":        {"max": 10.0,  "50km": 14.50,  "100km": 21.25,  "200km": 28.00,  "Sem Limite": 28.00},
    "Enquadramento 10% a 13%":       {"max": 13.0,  "50km": 24.00,  "100km": 35.80,  "200km": 47.60,  "Sem Limite": 47.60},
    "Enquadramento 13% a 17%":       {"max": 17.0,  "50km": 33.50,  "100km": 50.40,  "200km": 67.20,  "Sem Limite": 67.20},
    "Enquadramento 17% a 20%":       {"max": 20.0,  "50km": 50.00,  "100km": 74.00,  "200km": 98.00,  "Sem Limite": 98.00},
    "Enquadramento 20% a 30%":       {"max": 30.0,  "50km": 68.00,  "100km": 102.00, "200km": 135.00, "Sem Limite": 135.00},
    "Enquadramento 30% a 40%":       {"max": 40.0,  "50km": 86.00,  "100km": 130.00, "200km": 172.00, "Sem Limite": 172.00},
    "Enquadramento 40% a 50%":       {"max": 50.0,  "50km": 104.00, "100km": 158.00, "200km": 209.00, "Sem Limite": 209.00},
    "Enquadramento 50% a 60%":       {"max": 60.0,  "50km": 122.00, "100km": 186.00, "200km": 246.00, "Sem Limite": 246.00},
    "Enquadramento 60% a 70%":       {"max": 70.0,  "50km": 140.00, "100km": 214.00, "200km": 283.00, "Sem Limite": 283.00},
    "Enquadramento Teto (> 70%)":    {"max": 999.0, "50km": 158.00, "100km": 242.00, "200km": 320.00, "Sem Limite": 320.00}
}

def obter_faixa_escalonado(taxa_uso):
    for nome_faixa, dados in TABELA_ESCALONADO.items():
        if taxa_uso <= dados["max"]: return nome_faixa, dados
    return "Enquadramento Teto (> 70%)", TABELA_ESCALONADO["Enquadramento Teto (> 70%)"]

# ===================================================================================
# FUNÇÕES DE CÁLCULO E REGRAS DE NEGÓCIO (FINANCEIRO ATUALIZADO)
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
        while m <= 0:
            m += 12
            y -= 1
        meses.append(f"{m:02d}/{y}")
    return meses

def calcular_datas_ciclo(mes, ano, dia_venc_str):
    mes, ano = int(mes), int(ano)
    try: dia_venc = int(dia_venc_str)
    except: dia_venc = 30
    try: dt_venc_atual = datetime(ano, mes, dia_venc)
    except ValueError: dt_venc_atual = datetime(ano, mes, calendar.monthrange(ano, mes)[1])
    dt_fim = (dt_venc_atual - timedelta(days=2)).replace(hour=23, minute=59, second=59)
    mes_ant = mes - 1 if mes > 1 else 12
    ano_ant = ano if mes > 1 else ano - 1
    try: dt_venc_ant = datetime(ano_ant, mes_ant, dia_venc)
    except ValueError: dt_venc_ant = datetime(ano_ant, mes_ant, calendar.monthrange(ano_ant, mes_ant)[1])
    dt_fim_ant = (dt_venc_ant - timedelta(days=2)).replace(hour=23, minute=59, second=59)
    dt_inicio = (dt_fim_ant + timedelta(days=1)).replace(hour=0, minute=0, second=0)
    return dt_inicio, dt_fim

def obter_mes_ano_vigente(dia_venc_str):
    try: dia_venc = int(dia_venc_str)
    except: dia_venc = 30
    hoje = datetime.now()
    try: dt_venc_este_mes = datetime(hoje.year, hoje.month, dia_venc)
    except ValueError: dt_venc_este_mes = datetime(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])
    dt_fechamento_este_mes = (dt_venc_este_mes - timedelta(days=2)).replace(hour=23, minute=59, second=59)
    if hoje <= dt_fechamento_este_mes: return hoje.month, hoje.year
    else:
        m = hoje.month + 1
        y = hoje.year
        if m > 12: m, y = 1, y + 1
        return m, y

def obter_ciclo_contrato_anual(data_cad_str):
    try: dt_cad = datetime.strptime(str(data_cad_str)[:10], "%Y-%m-%d")
    except: dt_cad = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    hoje = datetime.now()
    try: aniv_este_ano = dt_cad.replace(year=hoje.year)
    except ValueError: aniv_este_ano = dt_cad.replace(year=hoje.year, day=28)
    if hoje < aniv_este_ano:
        try: inicio = dt_cad.replace(year=hoje.year - 1)
        except ValueError: inicio = dt_cad.replace(year=hoje.year - 1, day=28)
        fim = aniv_este_ano - timedelta(seconds=1)
    else:
        inicio = aniv_este_ano
        try: fim = dt_cad.replace(year=hoje.year + 1)
        except ValueError: fim = dt_cad.replace(year=hoje.year + 1, day=28)
        fim = fim - timedelta(seconds=1)
    return inicio, fim

def calcular_fatura_parceiro(nome_empresa, mes, ano, df_clientes_atuais, df_os_atuais, df_empresas_atuais):
    lista_veiculos_emp = []
    df_cli_fat = df_clientes_atuais[(df_clientes_atuais['emp_name'].str.upper() == nome_empresa.upper()) & (df_clientes_atuais['status'].str.strip() == 'Ativo')]
    
    for _, r_cli in df_cli_fat.iterrows():
        p_km_cli = str(r_cli.get('plano_km', '50km')).strip()
        plano_limpo = "50km" if "50" in p_km_cli else "100km" if "100" in p_km_cli else "200km" if "200" in p_km_cli else "Sem Limite"
        placas_extraidas = []
        if pd.notna(r_cli.get('veiculos_lista')) and str(r_cli['veiculos_lista']).strip() not in ['', '[]', 'nan']:
            try:
                for v in json.loads(str(r_cli['veiculos_lista'])):
                    p = str(v.get('Placa', '')).strip().upper().replace("-","").replace(" ","")
                    if len(p) >= 6 and p not in ['NAN', 'N/D']: placas_extraidas.append(p)
            except: pass
        if not placas_extraidas:
            p1 = str(r_cli.get('pla', '')).strip().upper().replace("-","").replace(" ","")
            if len(p1) >= 6 and p1 not in ['NAN', 'N/D']: placas_extraidas.append(p1)
            p2 = str(r_cli.get('pla_2', '')).strip().upper().replace("-","").replace(" ","")
            if len(p2) >= 6 and p2 not in ['NAN', 'N/D']: placas_extraidas.append(p2)
        for placa in placas_extraidas:
            lista_veiculos_emp.append({'placa': placa, 'plano': plano_limpo, 'cliente': str(r_cli.get('nome', '')).upper()})

    total_v = len(lista_veiculos_emp)
    
    dia_venc_str, modo_fat_calc, status_emp = '30', "Tradicional", "Ativo"
    emp_dados_fat = df_empresas_atuais[df_empresas_atuais['nome'].str.upper() == nome_empresa.upper()]
    
    if not emp_dados_fat.empty:
        dia_venc_str = str(emp_dados_fat.iloc[0].get('dia_vencimento', '30')).strip()
        modo_fat_calc = str(emp_dados_fat.iloc[0].get('modo_faturamento', 'Tradicional')).strip()
        status_emp = str(emp_dados_fat.iloc[0].get('status', 'Ativo')).strip()
        if not dia_venc_str or dia_venc_str == 'nan': dia_venc_str = '30'

    dt_inicio, dt_fim = calcular_datas_ciclo(mes, ano, dia_venc_str)
    
    # === BLOQUEIO DE EMPRESA INATIVA ===
    if status_emp == 'Inativo':
        return {
            'fatura_total': 0.0, 'total_v': 0, 'total_os': 0,
            'taxa': 0.0, 'faixa': 'Inativo', 'veiculos': [],
            'valor_base': 0.0, 'soma_adicionais': 0.0, 'soma_excedentes': 0.0,
            'dt_inicio': dt_inicio, 'dt_fim': dt_fim, 'vencimento_dia': dia_venc_str,
            'modo_fat': 'Inativo', 'qtd_exc_50': 0, 'qtd_exc_100': 0,
            'total_ac': 0, 'acionamentos_isentos': 0
        }

    # === FILTRO DE OS ===
    df_os_temp = df_os_atuais.copy()
    df_os_temp['data_hora'] = pd.to_datetime(df_os_temp['data_hora'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    
    os_filtro_guinchos = df_os_temp[(df_os_temp['empresa'].str.upper() == nome_empresa.upper()) & 
                                    (df_os_temp['status_os'].str.upper() == 'ENCERRADO') & 
                                    (df_os_temp['tipo_servico'].str.upper().str.contains('GUINCHO')) & 
                                    (df_os_temp['data_hora'] >= dt_inicio) & 
                                    (df_os_temp['data_hora'] <= dt_fim) &
                                    (df_os_temp['valor_cobrado'].isin(['0,00', '0.00', '0', '']))]
                            
    total_guinchos = len(os_filtro_guinchos)
    fatura_total, soma_adicionais, soma_excedentes, valor_base = 0.0, 0.0, 0.0, 0.0
    qtd_exc_50, qtd_exc_100, taxa, faixa = 0, 0, 0.0, "N/A"
    total_ac, acionamentos_isentos = total_guinchos, 0
    
    # -----------------------------------------------------
    # LÓGICA: PLANOS DE FROTA FIXA
    # -----------------------------------------------------
    if "Frota Pequena" in modo_fat_calc or "Até 40" in modo_fat_calc:
        if "Frota Pequena" in modo_fat_calc:
            valor_base, acionamentos_isentos, taxa_50, taxa_100 = 300.00, 2, 50.00, 85.00
        elif "Opção A" in modo_fat_calc:
            valor_base, acionamentos_isentos, taxa_50, taxa_100 = 500.00, 2, 85.00, 100.00
        elif "Opção B" in modo_fat_calc:
            valor_base, acionamentos_isentos, taxa_50, taxa_100 = 650.00, 4, 150.00, 190.00

        for v in lista_veiculos_emp:
            p_km = str(v['plano'])
            custo_placa = 6.90 if "50" in p_km else 8.90
            soma_adicionais += custo_placa
            v['tipo_cobranca'] = f'Mensalidade (R$ {custo_placa:.2f})'
            v['valor_cobrado'] = custo_placa

        if total_guinchos > acionamentos_isentos:
            guinchos_excedentes = os_filtro_guinchos.iloc[acionamentos_isentos:]
            for _, g in guinchos_excedentes.iterrows():
                p_km_g = str(g.get('plano_km', '50km'))
                if "100" in p_km_g:
                    soma_excedentes += taxa_100
                    qtd_exc_100 += 1
                else:
                    soma_excedentes += taxa_50
                    qtd_exc_50 += 1

        fatura_total = valor_base + soma_adicionais + soma_excedentes
        faixa = f"Pacote Fixo + Placas ({modo_fat_calc})"
        
    # -----------------------------------------------------
    # LÓGICA: MODO ESCALONADO (PERFORMANCE)
    # -----------------------------------------------------
    elif modo_fat_calc == "Performance (Escalonado)":
        base_calc = max(30, total_v)
        taxa = (total_guinchos / base_calc * 100) if base_calc > 0 else 0.0
        faixa, precos_faixa = obter_faixa_escalonado(taxa)

        for v in lista_veiculos_emp:
            p_km = str(v['plano'])
            custo_placa = precos_faixa.get(p_km, precos_faixa['50km'])
            soma_adicionais += custo_placa
            v['tipo_cobranca'] = f'Tabela ({faixa})'
            v['valor_cobrado'] = custo_placa

        if soma_adicionais < 400.00:
            soma_excedentes = 400.00 - soma_adicionais
            fatura_total = 400.00
        else:
            fatura_total = soma_adicionais
            
    # -----------------------------------------------------
    # LÓGICA: TRADICIONAL
    # -----------------------------------------------------
    else:
        for v in lista_veiculos_emp:
            v['tipo_cobranca'] = 'Tradicional / Manual'
            v['valor_cobrado'] = 0.0
            
    return {
        'fatura_total': fatura_total, 'total_v': total_v, 'total_os': total_guinchos,
        'taxa': taxa, 'faixa': faixa, 'veiculos': lista_veiculos_emp,
        'valor_base': valor_base, 'soma_adicionais': soma_adicionais, 'soma_excedentes': soma_excedentes,
        'dt_inicio': dt_inicio, 'dt_fim': dt_fim, 'vencimento_dia': dia_venc_str,
        'modo_fat': modo_fat_calc, 'qtd_exc_50': qtd_exc_50, 'qtd_exc_100': qtd_exc_100,
        'total_ac': total_ac, 'acionamentos_isentos': acionamentos_isentos
    }

def gerar_texto_resumo_plano(dados_fat):
    modo = dados_fat.get('modo_fat', 'Tradicional')
    if modo == 'Inativo': return "<b style='color:#c62828;'>🚫 Empresa Inativa. Sem faturamento gerado.</b>"
    
    tot_v = dados_fat.get('total_v', 0)
    taxa = dados_fat.get('taxa', 0.0)
    faixa = dados_fat.get('faixa', 'Enquadramento Base (Até 3%)')
    fat_tot = dados_fat.get('fatura_total', 0.0)
    base = dados_fat.get('valor_base', 0.0)
    placas_tot = dados_fat.get('soma_adicionais', 0.0)
    exc = dados_fat.get('soma_excedentes', 0.0)
    dt_ini = dados_fat['dt_inicio'].strftime('%d/%m/%Y')
    dt_fim = dados_fat['dt_fim'].strftime('%d/%m/%Y')
    
    periodo_str = f"📅 <b>Ciclo Vigente:</b> {dt_ini} a {dt_fim} (Vencimento: Dia {dados_fat['vencimento_dia']})"
    
    if modo == "Performance (Escalonado)":
        texto = f"{periodo_str}<br>📊 <b>Plano Ativo:</b> {modo}<br>🚗 <b>Frota Apurada:</b> {tot_v} veículos ativos (Base Mínima: 30).<br>"
        if taxa == 0.0: texto += f"🎯 <b style='color:#2e7d32;'>Taxa de Acionamento: 0.0% (Mês zerado)</b><br>"
        else: texto += f"🎯 <b>Taxa de Acionamento:</b> {taxa:.1f}%<br>"
            
        texto += f"📈 <b>Enquadramento Comercial:</b> {faixa}<br>"
        if fat_tot == 400.00 and exc > 0:
            texto += f"💰 <b>Fatura Atualizada: R$ 400,00</b> <span style='color:#E53935; font-size:14px;'>(Piso Mínimo Garantido Atingido. Valor Real das Placas seria R$ {placas_tot:.2f})</span>"
        else:
            texto += f"💰 <b>Fatura Mapeada:</b> R$ {fat_tot:.2f}"
        return texto
        
    elif "Frota Pequena" in modo or "Até 40" in modo:
        tot_ac = dados_fat.get('total_ac', 0)
        isentos = dados_fat.get('acionamentos_isentos', 0)
        texto = f"{periodo_str}<br>📊 <b>Plano Ativo:</b> {modo}<br>🚗 <b>Base Apurada:</b> {tot_v} veículos<br>"
        texto += f"🎟️ <b>Franquia Utilizada:</b> {tot_ac} de {isentos} guinchos<br>"
        if exc > 0:
            detalhe_exc = []
            if dados_fat.get('qtd_exc_50', 0) > 0: detalhe_exc.append(f"{dados_fat['qtd_exc_50']}x excedente(s) de 50km")
            if dados_fat.get('qtd_exc_100', 0) > 0: detalhe_exc.append(f"{dados_fat['qtd_exc_100']}x excedente(s) de 100km")
            texto += f"💰 <b>Fatura Atualizada: R$ {fat_tot:.2f}</b> <span style='color:#E53935; font-size:14px;'>(R$ {base:.2f} Fixo + R$ {placas_tot:.2f} Placas + Adicional Extra: R$ {exc:.2f} de {' e '.join(detalhe_exc)})</span>"
        else:
            texto += f"💰 <b>Fatura Atual: R$ {fat_tot:.2f}</b> <span style='color:#2e7d32; font-size:14px;'>(Operando perfeitamente dentro da franquia do pacote)</span>"
        return texto
    else:
        return f"{periodo_str}<br>📊 <b>Plano Ativo:</b> {modo}<br>🚗 <b>Base Apurada:</b> {tot_v} veículos<br>💰 <b>Faturamento:</b> Lançamento Manual gerido pela Central"

def gerar_pdf_extrato_detalhado(nome_empresa, mes, ano, df_clientes_atuais, df_os_atuais, df_empresas_atuais):
    dados_fat = calcular_fatura_parceiro(nome_empresa, mes, ano, df_clientes_atuais, df_os_atuais, df_empresas_atuais)
    if dados_fat['modo_fat'] == 'Inativo': return "<p>Empresa inativa.</p>"
    
    df_os_temp = df_os_atuais.copy()
    df_os_temp['data_hora'] = pd.to_datetime(df_os_temp['data_hora'], errors='coerce')
    os_mes = df_os_temp[(df_os_temp['empresa'].str.upper() == nome_empresa.upper()) & (df_os_temp['status_os'].str.upper() == 'ENCERRADO') & (df_os_temp['data_hora'] >= dados_fat['dt_inicio']) & (df_os_temp['data_hora'] <= dados_fat['dt_fim'])].sort_values(by='data_hora')

    linhas_os_html = ""
    if os_mes.empty: linhas_os_html = "<tr><td colspan='6' style='text-align: center; padding: 10px; color: #666;'>Nenhum acionamento registrado neste ciclo.</td></tr>"
    else:
        for _, r in os_mes.iterrows():
            is_exc = "<br><span style='color:red; font-size:10px;'>(Exceção/PIX)</span>" if str(r.get('valor_cobrado','0')) not in ['0.00', '0,00', '0', ''] else ""
            linhas_os_html += f"<tr><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{r['id']}{is_exc}</td><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{str(r['data_hora'])[:16]}</td><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px; font-weight: bold;'>{r['placa']}</td><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{r['cliente_nome']}</td><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{r['tipo_servico']}</td><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{r['localizacao']} ➔ {r['destino']}</td></tr>"

    linhas_veiculos_html = ""
    for idx_v, v in enumerate(dados_fat['veiculos']):
        linhas_veiculos_html += f"<tr><td style='border: 1px solid #ddd; padding: 6px; font-size: 11px;'>{idx_v + 1}</td><td style='border: 1px solid #ddd; padding: 6px; font-size: 11px; font-weight: bold;'>{v['placa']}</td><td style='border: 1px solid #ddd; padding: 6px; font-size: 11px;'>{v['cliente']}</td><td style='border: 1px solid #ddd; padding: 6px; font-size: 11px;'>{v['plano']}</td><td style='border: 1px solid #ddd; padding: 6px; font-size: 11px;'>{v['tipo_cobranca']}</td></tr>"

    str_inicio = dados_fat['dt_inicio'].strftime('%d/%m/%Y')
    str_fim = dados_fat['dt_fim'].strftime('%d/%m/%Y')
    timestamp_arquivo = int(time.time())
    modo_pdf = dados_fat['modo_fat']

    if modo_pdf == "Performance (Escalonado)":
        secao_tabela = f"""<div style="margin-bottom: 20px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #7B2CBF;">3. TABELA DE REFERÊNCIA (AMOSTRAGEM)</h3><p style="margin: 4px 0 10px 0; font-size: 12px; color: #666;">A tarifa mensal baseia-se na % de uso em relação a base (Mínimo de 30 veículos). Enquadramento atual de fechamento: <b>{dados_fat['faixa']}</b>.</p></div>"""
        secao_memoria = f"""<div style="margin-bottom: 20px; background-color: #f3e5f5; padding: 15px; border-radius: 6px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #7B2CBF;">4. MEMÓRIA DE CÁLCULO FINANCEIRO DETALHADA</h3><p style="margin: 4px 0; font-size: 13px;">(+) Valor apurado pela tabela (Soma Placas Ativas): <strong>R$ {dados_fat['soma_adicionais']:.2f}</strong></p>"""
        if dados_fat['fatura_total'] == 400.00 and dados_fat['soma_adicionais'] < 400.00:
            secao_memoria += f"""<p style="margin: 4px 0; font-size: 13px; color: #E53935;">(+) Complemento de Piso Mínimo Garantido: <strong>R$ {dados_fat['soma_excedentes']:.2f}</strong></p>"""
        secao_memoria += f"""<hr style="border: 0; border-top: 1px solid #ccc; margin: 10px 0;"><p style="margin: 8px 0; font-size: 18px; color: #7B2CBF; text-align: right;"><strong>VALOR TOTAL DA FATURA: R$ {dados_fat['fatura_total']:.2f}</strong></p></div>"""
        
    elif "Frota Pequena" in modo_pdf or "Até 40 Veículos" in modo_pdf:
        franquia_qtd = f"{dados_fat.get('acionamentos_isentos', 2)} guinchos"
        uso_qtd = f"{dados_fat.get('total_ac', 0)} de {dados_fat.get('acionamentos_isentos', 2)}"
        secao_tabela = f"""<div style="margin-bottom: 20px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #7B2CBF;">3. INFORMAÇÕES DO PACOTE CONTRATADO</h3><p style="margin: 4px 0 10px 0; font-size: 13px;"><strong>Plano:</strong> {modo_pdf}</p><p style="margin: 4px 0 10px 0; font-size: 13px;"><strong>Franquia Inclusa:</strong> {franquia_qtd} mensais.</p><p style="margin: 4px 0 10px 0; font-size: 13px;"><strong>Consumo no Ciclo:</strong> {uso_qtd} utilizados.</p></div>"""
        secao_memoria = f"""<div style="margin-bottom: 20px; background-color: #f3e5f5; padding: 15px; border-radius: 6px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #7B2CBF;">4. MEMÓRIA DE CÁLCULO FINANCEIRO DETALHADA</h3><p style="margin: 4px 0; font-size: 13px;">(+) Base do Pacote Mensal Fixo: <strong>R$ {dados_fat['valor_base']:.2f}</strong></p><p style="margin: 4px 0; font-size: 13px;">(+) Custo das Placas Ativas (Pré-Pago): <strong>R$ {dados_fat['soma_adicionais']:.2f}</strong></p><p style="margin: 4px 0; font-size: 13px;">(+) Adicional de Acionamentos Excedentes (Pós-Pago): <strong>R$ {dados_fat['soma_excedentes']:.2f}</strong></p><hr style="border: 0; border-top: 1px solid #ccc; margin: 10px 0;"><p style="margin: 8px 0; font-size: 18px; color: #7B2CBF; text-align: right;"><strong>VALOR TOTAL DA FATURA: R$ {dados_fat['fatura_total']:.2f}</strong></p></div>"""
    else:
        secao_tabela = ""
        secao_memoria = f"""<div style="margin-bottom: 20px; background-color: #f3e5f5; padding: 15px; border-radius: 6px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #7B2CBF;">4. MEMÓRIA DE CÁLCULO FINANCEIRO</h3><p style="margin: 4px 0; font-size: 13px;">Este cliente opera no modo Tradicional. O valor faturado é gerido manualmente.</p></div>"""

    html_content = f"""<html><head><meta charset='utf-8'></head><body style="font-family: Arial, sans-serif; max-width: 850px; margin: 0 auto; padding: 20px; color: #333;"><div style="text-align: center; margin-bottom: 20px;"><h2 style="margin: 0; color: #7B2CBF; font-size: 24px;">AD RASTREAMENTO VEICULAR</h2><p style="margin: 5px 0; font-size: 14px; color: #555; text-transform: uppercase; font-weight: bold;">Extrato Detalhado de Faturamento e Auditoria</p><p style="margin: 3px 0; font-size: 13px; color: #777;">Empresa: <strong>{nome_empresa.upper()}</strong> | Competência Mês: {mes}/{ano}</p></div><hr style="border: 0; border-top: 2px solid #7B2CBF; margin-bottom: 20px;"><div style="margin-bottom: 20px; background-color: #f8f9fa; padding: 15px; border-radius: 6px; border: 1px solid #eee;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #7B2CBF;">1. RESUMO OPERACIONAL DO CICLO</h3><p style="margin: 4px 0; font-size: 13px;"><strong>Período de Apuração:</strong> {str_inicio} até {str_fim} (Vencimento dia {dados_fat['vencimento_dia']})</p><p style="margin: 4px 0; font-size: 13px;"><strong>Total Exato de Veículos na Base (Ativos):</strong> {dados_fat['total_v']} veículos</p><p style="margin: 4px 0; font-size: 13px;"><strong>Total de Acionamentos Ordinários no Ciclo:</strong> {dados_fat['total_os']} guinchos</p><p style="margin: 4px 0; font-size: 13px;"><strong>Modo Comercial Aplicado:</strong> {modo_pdf}</p></div><div style="margin-bottom: 20px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #7B2CBF;">2. HISTÓRICO DE ATENDIMENTOS DO CICLO</h3><table style="width: 100%; border-collapse: collapse;"><thead><tr style="background-color: #7B2CBF; color: white;"><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">OS</th><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">Data/Hora</th><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">Placa</th><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">Cliente</th><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">Serviço</th><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">Trajeto (Origem ➔ Destino)</th></tr></thead><tbody>{linhas_os_html}</tbody></table></div>{secao_tabela}{secao_memoria}<div style="margin-bottom: 20px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #7B2CBF;">5. ANEXO DE AUDITORIA: RELAÇÃO DE TODAS AS PLACAS</h3><p style="margin: 4px 0 10px 0; font-size: 11px; color: #666;">Abaixo constam rigorosamente todos os {dados_fat['total_v']} veículos lidos no banco de dados com status ativo para gerar esta fatura.</p><table style="width: 100%; border-collapse: collapse; font-size: 11px;"><thead><tr style="background-color: #e0e0e0; color: #333;"><th style="border: 1px solid #ddd; padding: 6px;">#</th><th style="border: 1px solid #ddd; padding: 6px;">Placa Identificada</th><th style="border: 1px solid #ddd; padding: 6px;">Nome do Cliente Cadastrado</th><th style="border: 1px solid #ddd; padding: 6px;">Plano (KM)</th><th style="border: 1px solid #ddd; padding: 6px;">Enquadramento de Cobrança</th></tr></thead><tbody>{linhas_veiculos_html}</tbody></table></div></body></html>"""
    b64 = base64.b64encode(html_content.encode('utf-8')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="Extrato_Auditavel_{nome_empresa}_{mes}_{ano}_{timestamp_arquivo}.html" style="text-decoration: none;"><button style="background-color: #7B2CBF; color: white; padding: 10px 18px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; width: 100%; font-size: 13px;">📄 Baixar Extrato Oficial e Auditável (PDF)</button></a>'

# ===================================================================================
# PORTAIS EXTERNOS (NPS, GPS DO CLIENTE E PORTAL DO GUINCHO)
# ===================================================================================
portal_atual = st.query_params.get("portal", "")

if portal_atual == "guincho":
    st.markdown('<div class="main-title" style="font-size:26px;">Portal do Prestador</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">AD Assistência 24h</div>', unsafe_allow_html=True)
    
    os_param = st.query_params.get("os", "")
    if not os_param:
        st.error("Número do chamado não identificado no link.")
        st.stop()
        
    os_relacionada = df_os[df_os['id'].astype(str) == str(os_param)]
    if os_relacionada.empty:
        st.error("Ordem de serviço não encontrada no sistema.")
        st.stop()
        
    os_info = os_relacionada.iloc[0]
    status_atual = str(os_info.get('status_os', '')).upper()
    placa_real = str(os_info.get('placa', '')).strip().upper()
    tel_cliente_real = str(os_info.get('cliente_tel', ''))
    
    motorista_os = str(os_info.get('motorista_nome', '')).strip()
    motorista_tel_raw = str(os_info.get('motorista_tel', '')).strip()
    
    if "|" in motorista_tel_raw:
        tel_motorista_os = motorista_tel_raw.split("|")[0]
        data_aceite = motorista_tel_raw.split("|")[1]
    else:
        tel_motorista_os = motorista_tel_raw
        data_aceite = "N/D"
        
    data_formatada = ""
    if data_aceite != "N/D":
        try:
            d_obj = datetime.strptime(data_aceite, "%Y-%m-%d %H:%M:%S")
            data_formatada = d_obj.strftime("%d/%m/%Y às %H:%M")
        except: data_formatada = data_aceite
    
    v_desc_portal = str(os_info.get('veiculo_desc', 'N/D'))
    if "CARRO " in v_desc_portal.upper() and any(m in v_desc_portal.upper() for m in MARCAS_MOTO):
        v_desc_portal = v_desc_portal.replace("CARRO ", "MOTO ").replace("Carro ", "Moto ")
        
    is_dono = st.session_state.get(f"dono_{os_param}", False)
    
    if status_atual not in ['PENDENTE', 'EM ATENDIMENTO', 'CANCELADO']:
        if not is_dono:
            st.error("🔒 CHAMADO INDISPONÍVEL / JÁ ASSUMIDO")
            if data_formatada: st.warning(f"A ordem de serviço foi aceita por **{motorista_os}** em {data_formatada}.")
            else: st.warning(f"A ordem de serviço já foi aceita e assumida por **{motorista_os}**.")
            
            st.info("Se você é este prestador e a página recarregou, confirme seu WhatsApp abaixo para retornar ao chamado:")
            tel_recuperacao = st.text_input("Seu WhatsApp (com DDD):", key="tel_rec")
            if st.button("Recuperar Acesso", use_container_width=True):
                if apenas_numeros_letras(tel_recuperacao) == tel_motorista_os and tel_motorista_os != "":
                    st.session_state[f"dono_{os_param}"] = True
                    st.success("Acesso recuperado! Redirecionando...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Telefone incorreto. Você não é o prestador que assumiu esta OS.")
            st.stop()
    
    st.markdown(f"**📍 Origem:** {os_info.get('localizacao', 'N/D')}")
    st.markdown(f"**🏁 Destino:** {os_info.get('destino', 'N/D')}")
    st.markdown(f"**🚙 Veículo:** {v_desc_portal}")
    st.markdown(f"**🛠️ Serviço:** {os_info.get('tipo_servico', '')} ({os_info.get('motivo', '')})")
    
    st.write("---")
    
    if status_atual in ['PENDENTE', 'EM ATENDIMENTO']:
        st.info("🚨 **Este chamado está disponível para atendimento.**")
        st.write(f"**Placa:** `{mascarar_placa(placa_real)}`")
        st.write(f"**Telefone do Cliente:** `{mascarar_telefone(tel_cliente_real)}`")
        
        st.markdown("### Assumir Ocorrência")
        st.write("Digite seu WhatsApp para buscar seu cadastro ou criar um novo:")
        
        tel_mot_raw = st.text_input("Seu Telefone/WhatsApp (com DDD):")
        tel_limpo = apenas_numeros_letras(tel_mot_raw)
        
        if tel_limpo and len(tel_limpo) >= 10:
            df_prestadores_atual = carregar_dados(FILE_PRESTADORES, col_pre)
            prestador_existente = df_prestadores_atual[df_prestadores_atual['telefone'] == tel_limpo]
            
            if not prestador_existente.empty:
                nome_mot = str(prestador_existente.iloc[0]['nome']).upper()
                st.success(f"👋 Olá novamente, **{nome_mot}**! Seu cadastro foi encontrado.")
                if st.button("✅ ACEITAR CHAMADO", type="primary", use_container_width=True):
                    df_check = carregar_dados(FILE_OS, col_os)
                    os_check = df_check[df_check['id'].astype(str) == str(os_param)]
                    
                    if not os_check.empty and str(os_check.iloc[0]['status_os']).upper() not in ['PENDENTE', 'EM ATENDIMENTO']:
                        st.error(f"❌ Poxa! Este chamado já foi assumido por outro prestador.")
                    else:
                        hora_agora = obter_hora_str()
                        tel_save = f"{tel_limpo}|{hora_agora}"
                        df_os.loc[df_os['id'].astype(str) == str(os_param), ['status_os', 'motorista_nome', 'motorista_tel']] = ['A CAMINHO', nome_mot, tel_save]
                        salvar_dados(df_os, FILE_OS)
                        st.session_state[f"dono_{os_param}"] = True
                        st.success("✅ Chamado assumido com sucesso! Dirija-se ao local.")
                        time.sleep(1.5)
                        st.rerun()
            else:
                st.warning("Número não encontrado. Faça seu cadastro rápido para assumir a OS e passar a receber nossos chamados:")
                nome_mot = st.text_input("Seu Nome / Nome da sua Base:")
                c_est, c_cid = st.columns(2)
                est_mot = c_est.selectbox("Estado (UF):", ESTADOS_BR, index=ESTADOS_BR.index("RN"))
                cid_mot = c_cid.text_input("Cidade:")
                bairro_mot = st.text_input("Bairro:")
                
                if st.button("✅ CADASTRAR E ACEITAR CHAMADO", type="primary", use_container_width=True):
                    if not nome_mot or not cid_mot:
                        st.error("Preencha seu Nome e Cidade para continuar.")
                    else:
                        df_check = carregar_dados(FILE_OS, col_os)
                        os_check = df_check[df_check['id'].astype(str) == str(os_param)]
                        
                        if not os_check.empty and str(os_check.iloc[0]['status_os']).upper() not in ['PENDENTE', 'EM ATENDIMENTO']:
                            st.error(f"❌ Poxa! Este chamado já foi assumido por outro prestador.")
                        else:
                            prox_p = int(df_prestadores_atual['id'].astype(float).max() + 1) if not df_prestadores_atual.empty else 1
                            novo_p = pd.DataFrame([{'id': str(prox_p), 'nome': nome_mot.upper(), 'cpf': '', 'tipo': 'Guincho', 'telefone': tel_limpo, 'endereco': '', 'bairro': bairro_mot.upper(), 'cidade': cid_mot.upper(), 'cep': '', 'est': est_mot, 'status': 'Ativo', 'homologado': 'Pendente', 'senha': 'admin', 'frota': '[]'}])
                            df_p_temp = pd.concat([df_prestadores_atual, novo_p], ignore_index=True)
                            salvar_dados(df_p_temp, FILE_PRESTADORES)
                            
                            hora_agora = obter_hora_str()
                            tel_save = f"{tel_limpo}|{hora_agora}"
                            df_os.loc[df_os['id'].astype(str) == str(os_param), ['status_os', 'motorista_nome', 'motorista_tel']] = ['A CAMINHO', nome_mot.upper(), tel_save]
                            salvar_dados(df_os, FILE_OS)
                            st.session_state[f"dono_{os_param}"] = True
                            st.success("✅ Cadastro criado e chamado assumido com sucesso! Dirija-se ao local.")
                            time.sleep(1.5)
                            st.rerun()
                    
    elif status_atual == 'A CAMINHO':
        st.success(f"🚚 Você assumiu este chamado. Dirija-se ao local de origem.")
        
        link_w_cli = f"https://api.whatsapp.com/send?phone=55{apenas_numeros_letras(tel_cliente_real)}"
        st.markdown(f"**📞 Contato Liberado do Cliente:** {tel_cliente_real}")
        st.markdown(f'<a href="{link_w_cli}" target="_blank"><button style="background-color: #25D366; color: white; padding: 10px; width: 100%; border: none; border-radius: 5px; font-weight: bold; margin-bottom: 15px;">Falar com Cliente no WhatsApp</button></a>', unsafe_allow_html=True)
        
        st.markdown("### Validação Física (Chegada)")
        st.info("Ao chegar no local, digite a placa completa do veículo para liberar o checklist de embarque.")
        placa_digitada = st.text_input("Digite a Placa Completa do Veículo (Só letras e números):")
        
        if "vistoria_liberada" not in st.session_state:
            st.session_state.vistoria_liberada = False
            
        if st.button("Validar Placa", use_container_width=True):
            if apenas_numeros_letras(placa_digitada).upper() == apenas_numeros_letras(placa_real).upper():
                st.session_state.vistoria_liberada = True
                st.success("Placa validada! Preencha o checklist abaixo.")
            else:
                st.error("Placa incorreta. Verifique o veículo ou tente novamente.")
                
        if st.session_state.vistoria_liberada:
            st.write("---")
            st.markdown("### 📸 Vistoria Fotográfica")
            st.write("Tire as 4 fotos obrigatórias do veículo (toque no botão para abrir a câmera):")
            
            c_cam1, c_cam2 = st.columns(2)
            with c_cam1: 
                frente = st.file_uploader("📸 Frente", type=['jpg', 'jpeg', 'png'])
                if frente: st.image(frente, use_container_width=True)
            with c_cam2: 
                traseira = st.file_uploader("📸 Traseira", type=['jpg', 'jpeg', 'png'])
                if traseira: st.image(traseira, use_container_width=True)
            with c_cam1: 
                lat_dir = st.file_uploader("📸 Lat. Direita", type=['jpg', 'jpeg', 'png'])
                if lat_dir: st.image(lat_dir, use_container_width=True)
            with c_cam2: 
                lat_esq = st.file_uploader("📸 Lat. Esquerda", type=['jpg', 'jpeg', 'png'])
                if lat_esq: st.image(lat_esq, use_container_width=True)
            
            st.markdown("### ✍️ Assinatura do Condutor")
            doc_cliente_input = st.text_input("Documento Identificador do Cliente (CPF ou RG):", placeholder="Obrigatório para validar a assinatura")
            
            st.info("Peça para o responsável pelo veículo assinar no quadro abaixo:")
            
            canvas_result = None
            assinatura_foto = None
            
            if CANVAS_AVAILABLE:
                canvas_result = st_canvas(
                    fill_color="rgba(255, 165, 0, 0.3)",
                    stroke_width=3,
                    stroke_color="#000000",
                    background_color="#EEEEEE",
                    height=200,
                    drawing_mode="freedraw",
                    key="canvas_assinatura",
                )
            else:
                st.warning("O módulo de assinatura digital está desativado no momento.")
                assinatura_foto = st.file_uploader("Tire uma foto do Documento e da Assinatura do Cliente", type=['jpg', 'jpeg', 'png'])
                if assinatura_foto: st.image(assinatura_foto, use_container_width=True)
                
            st.write("")
            if st.button("🚀 FINALIZAR CHECKLIST E INICIAR TRANSPORTE", type="primary", use_container_width=True):
                if not frente or not traseira or not lat_dir or not lat_esq:
                    st.error("As 4 fotos são obrigatórias para liberar o transporte.")
                elif not doc_cliente_input:
                    st.error("O número do Documento (CPF/RG) do cliente é obrigatório.")
                else:
                    with st.spinner("Processando imagens e enviando para a Central..."):
                        b_frente = comprimir_imagem_b64(frente)
                        b_traseira = comprimir_imagem_b64(traseira)
                        b_dir = comprimir_imagem_b64(lat_dir)
                        b_esq = comprimir_imagem_b64(lat_esq)
                        dict_fotos = {"frente": b_frente, "traseira": b_traseira, "lat_dir": b_dir, "lat_esq": b_esq, "doc_cliente": doc_cliente_input}
                        
                        b64_assinatura = ""
                        if CANVAS_AVAILABLE and canvas_result is not None:
                            try:
                                img_data = getattr(canvas_result, 'image_data', None)
                                if img_data is not None:
                                    img_ass = Image.fromarray(img_data.astype('uint8'), 'RGBA')
                                    buf = io.BytesIO()
                                    img_ass.save(buf, format="PNG")
                                    b64_assinatura = base64.b64encode(buf.getvalue()).decode()
                            except Exception:
                                pass
                        elif not CANVAS_AVAILABLE and assinatura_foto:
                            b64_assinatura = comprimir_imagem_b64(assinatura_foto)
                            
                        df_os.loc[df_os['id'].astype(str) == str(os_param), ['status_os', 'fotos_vistoria', 'assinatura_cliente']] = ['EM TRÂNSITO', json.dumps(dict_fotos), b64_assinatura]
                        salvar_dados(df_os, FILE_OS)
                        
                        st.success("✅ Vistoria registrada com sucesso! Transporte autorizado.")
                        st.session_state.vistoria_liberada = False
                        time.sleep(2)
                        st.rerun()
                        
    elif status_atual == 'EM TRÂNSITO':
        st.info("🚚 Veículo embarcado. Você está a caminho do destino.")
        st.markdown(f"**🏁 Destino Final:** {os_info.get('destino', 'N/D')}")
        st.markdown(f"**Observações Extras:** {os_info.get('obs', 'Nenhuma')}")
        
        st.write("---")
        if st.button("🛑 DESEMBARCAR E CONCLUIR ROTA", type="primary", use_container_width=True):
            with st.spinner("Avisando a central..."):
                df_os.loc[df_os['id'].astype(str) == str(os_param), 'status_os'] = 'CONCLUÍDO'
                salvar_dados(df_os, FILE_OS)
                st.success("🎉 Parabéns! Entrega finalizada com sucesso. A Central foi notificada para auditar o chamado.")
                time.sleep(2)
                st.rerun()
                
    elif status_atual in ['CONCLUÍDO', 'ENCERRADO', 'CANCELADO']:
        st.success(f"🔒 Este chamado encontra-se {status_atual}.")
        st.write("A sua entrega foi finalizada. A Central administrativa já foi informada. Obrigado e boa viagem de retorno!")
    
    st.stop()

elif portal_atual == "nps":
    st.markdown('<div class="main-title">Pesquisa de Qualidade</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Assistência 24h</div>', unsafe_allow_html=True)
    os_param = st.query_params.get("os", "")
    
    if not os_param:
        st.error("Número de atendimento não identificado.")
        st.stop()
        
    os_relacionada = df_os[df_os['id'].astype(str) == str(os_param)]
    if os_relacionada.empty:
        st.error("Ordem de serviço não encontrada no sistema.")
        st.stop()
        
    os_info = os_relacionada.iloc[0]
    nps_existente = df_nps[df_nps['id_os'].astype(str) == str(os_param)]
    
    if not nps_existente.empty:
        st.info("✅ Esta ordem de serviço já foi avaliada. Muito obrigado pelo seu tempo!")
        st.stop()

    st.write(f"**Veículo:** {os_info['placa']}")
    st.write(f"**Data do Chamado:** {os_info['data_hora'][:10]}")
    st.write("---")
    
    st.markdown("<h4 style='color: #7B2CBF; font-size: 15px;'>1. Em uma escala de 0 a 10, o quanto você recomendaria a assistência 24 horas para um amigo ou familiar?</h4>", unsafe_allow_html=True)
    nota_nps = st.slider("Arraste para dar sua nota:", min_value=0, max_value=10, value=10)
    
    st.markdown("<h4 style='color: #7B2CBF; margin-top: 15px; font-size: 15px;'>2. Como você avalia a agilidade e educação do nosso Operador da Central?</h4>", unsafe_allow_html=True)
    nota_central = st.feedback("stars", key="fb_central")
    
    st.markdown("<h4 style='color: #7B2CBF; margin-top: 15px; font-size: 15px;'>3. Como você avalia o atendimento presencial do Motorista do Guincho?</h4>", unsafe_allow_html=True)
    nota_guincho = st.feedback("stars", key="fb_guincho")
    
    comentario = st.text_area("Gostaria de deixar um comentário, elogio ou sugestão? (Opcional)")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Enviar minha avaliação", use_container_width=True, type="primary"):
        val_cen = nota_central + 1 if nota_central is not None else 5
        val_gui = nota_guincho + 1 if nota_guincho is not None else 5
        
        status_calc = "Promotor" if nota_nps >= 9 else "Neutro" if nota_nps >= 7 else "Detrator"
        
        novo_nps_dict = {
            'id_os': os_param,
            'data_hora': obter_hora_str(),
            'nota_nps': nota_nps,
            'nota_central': val_cen,
            'nota_guincho': val_gui,
            'comentario': comentario.strip(),
            'status_nps': status_calc
        }
        
        try:
            supabase.table(FILE_NPS).insert(novo_nps_dict).execute()
        except: pass

        st.success("🎉 Avaliação enviada com sucesso! Muito obrigado por nos ajudar a melhorar.")
        time.sleep(2)
        st.rerun()
    st.stop()

elif portal_atual == "cliente":
    st.markdown('<div class="main-title">AD Rastreamento</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Assistência 24h - Resgate</div>', unsafe_allow_html=True)
    placa_param = st.query_params.get("placa", "N/D")
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    body {{ font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #f8f9fa; margin: 0; }}
    .btn {{ background-color: #E53935; color: white; padding: 18px; font-size: 16px; border: none; border-radius: 8px; cursor: pointer; width: 100%; max-width: 300px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.2); margin-top: 15px; }}
    .btn:active {{ background-color: #b71c1c; }}
    #msg {{ margin-top: 15px; font-size: 15px; color: #555; font-weight: bold; }}
    </style>
    </head>
    <body>
    <h3 style="color: #7B2CBF; margin-top:0; font-size: 18px;">Localização de Emergência</h3>
    <p style="font-size:14px;">Precisamos saber onde você está para enviar o guincho exato até o veículo placa <b>{placa_param}</b>.</p>
    <button id="btn-loc" class="btn" onclick="getLocation()">📍 ENVIAR MINHA LOCALIZAÇÃO</button>
    <p id="msg"></p>
    <script>
    function getLocation() {{
        document.getElementById("msg").innerHTML = "Aguardando GPS... Autorize se o celular pedir.";
        document.getElementById("btn-loc").style.display = "none";
        
        if (navigator.geolocation) {{
            navigator.geolocation.getCurrentPosition(showPosition, showError, {{enableHighAccuracy: true}});
        }} else {{
            document.getElementById("msg").innerHTML = "Seu navegador não suporta GPS.";
            document.getElementById("btn-loc").style.display = "block";
        }}
    }}
    function showPosition(position) {{
        var lat = position.coords.latitude;
        var lon = position.coords.longitude;
        document.getElementById("msg").innerHTML = "Sinal capturado! Salvando no sistema... 🚀";
        
        var urlFinal = "https://ad-central-mrssupqbb9ux69bi4qgisa.streamlit.app/?portal=cliente_salvo&placa={placa_param}&lat=" + lat + "&lon=" + lon;
        
        try {{
            window.top.location.href = urlFinal; 
        }} catch(e) {{
            console.log("Fallback acionado.");
        }}
        
        setTimeout(function() {{
            window.location.href = urlFinal; 
        }}, 500);
    }}
    function showError(error) {{
        document.getElementById("btn-loc").style.display = "block";
        switch(error.code) {{
            case error.PERMISSION_DENIED:
                document.getElementById("msg").innerHTML = "❌ Você negou o acesso ao GPS. Libere a permissão e tente novamente.";
                break;
            case error.POSITION_UNAVAILABLE:
                document.getElementById("msg").innerHTML = "❌ Sinal de GPS indisponível no momento.";
                break;
            case error.TIMEOUT:
                document.getElementById("msg").innerHTML = "❌ Tempo esgotado para buscar o GPS.";
                break;
            default:
                document.getElementById("msg").innerHTML = "❌ Erro desconhecido ao tentar localizar.";
                break;
        }}
    }}
    </script>
    </body>
    </html>
    """
    components.html(html_code, height=500)
    st.stop()

elif portal_atual == "cliente_salvo":
    st.markdown('<div class="main-title">AD Rastreamento</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Assistência 24h - Resgate</div>', unsafe_allow_html=True)
    placa_cliente = st.query_params.get("placa", "N/D")
    lat = st.query_params.get("lat", "")
    lon = st.query_params.get("lon", "")
    
    if lat and lon:
        link_maps = f"https://www.google.com/maps?q={lat},{lon}"
        novo_loc_dict = {'placa': placa_cliente, 'data_hora': obter_hora_str(), 'link_maps': link_maps}
        try:
            supabase.table(FILE_LOC).insert(novo_loc_dict).execute()
        except: pass
        st.success("✅ Localização recebida com sucesso pela Central! O socorro já está sendo acionado. Você já pode fechar esta tela e aguardar.")
    else:
        st.error("Erro ao receber as coordenadas. Tente novamente.")
    st.stop()

# ===================================================================================
# CONTROLE DE SESSÃO E LOGIN
# ===================================================================================
if "logado" not in st.session_state:
    st.session_state.update({"logado": False, "user": "", "perfil": "", "empresa_vinculada": ""})

if not st.session_state.logado:
    sess_param = st.query_params.get("session")
    if sess_param == "admin_ad": 
        st.session_state.update({"logado": True, "user": "AD Rastreamento Veicular (ADMIN)", "perfil": "Admin"})
    elif sess_param and sess_param.startswith("parc_"):
        nome_parc = urllib.parse.unquote(sess_param.split("parc_")[1])
        st.session_state.update({"logado": True, "user": nome_parc.upper(), "perfil": "Parceiro", "empresa_vinculada": nome_parc})

if not st.session_state.logado:
    st.markdown('<div class="main-title">AD Rastreamento Veicular <span style="font-size: 14px; color: #ccc;">🚀 v13.0 (Estável)</span></div>', unsafe_allow_html=True)
    col_esp1, col_meio, col_esp2 = st.columns([1, 2, 1])
    with col_meio:
        st.markdown('<div class="subtitle">⚡ Operação Atendimento (Acesso Restrito)</div>', unsafe_allow_html=True)
        usuario_input = apenas_numeros_letras(st.text_input("Usuário (Nome da Empresa ou Central):"))
        senha_input = apenas_numeros_letras(st.text_input("Senha (CNPJ):", type="password"))
        if st.button("Entrar no Sistema", use_container_width=True, key="btn_login_geral"):
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

# ===================================================================================
# HEADER DO SISTEMA (QUANDO LOGADO)
# ===================================================================================
col_user, col_refresh, col_logout = st.columns([6, 2, 2])
with col_user: 
    st.markdown(f"<div style='font-size: 15px; font-weight: 800; color: #1e1b4b; padding-top: 6px;'>Central AD 24h &nbsp;|&nbsp; Operador: <span style='color: #E53935;'>{st.session_state.user}</span></div>", unsafe_allow_html=True)
with col_refresh:
    if st.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with col_logout:
    if st.button("Sair / Logoff", key="btn_logout_master", use_container_width=True):
        st.session_state.logado = False
        st.query_params.clear()
        st.rerun()
st.write("---")

# ===================================================================================
# INTERFACE 1: ADMIN MASTER
# ===================================================================================
if st.session_state.perfil == "Admin":
    qtd_pendencias = len(df_os[~df_os['status_os'].str.upper().isin(['ENCERRADO', 'CANCELADO'])])
    aba_pendencias_nome = f"🚨 Pendências ({qtd_pendencias})"
    
    opcoes_admin = ["📈 Dashboard", "📋 Nova OS", aba_pendencias_nome, "📊 Relatórios & PDF", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores", "⭐ Satisfação (NPS)", "💰 Financeiro", "🕵️ Auditoria", "💾 Dados"]
    
    aba_atual_admin = st.query_params.get("nav", opcoes_admin[0])
    
    if aba_atual_admin not in opcoes_admin: 
        if "Pendências" in aba_atual_admin:
            aba_atual_admin = aba_pendencias_nome
        else:
            aba_atual_admin = opcoes_admin[0]
            
    aba_selecionada = st.radio("Navegação Principal:", opcoes_admin, index=opcoes_admin.index(aba_atual_admin), horizontal=True, label_visibility="collapsed")
    
    if aba_selecionada != aba_atual_admin:
        st.query_params["nav"] = aba_selecionada
        st.rerun()
    
    if aba_selecionada == "📈 Dashboard":
        st.markdown('<div class="section-title">📈 Painel de Controle - Dashboard Inicial</div>', unsafe_allow_html=True)
        empresas_lista = ["Todas"] + sorted([str(e).upper() for e in df_empresas['nome'].unique() if str(e).strip() != ""])
        empresa_filtro = st.selectbox("Selecione a Empresa Parceira para filtrar os dados:", empresas_lista)
        
        renderizar_dashboard(empresa_filtro)

    elif aba_selecionada == "📋 Nova OS":
        st.markdown('<div class="section-title">🚀 Abertura de Chamado</div>', unsafe_allow_html=True)
        tipo_atendimento = st.radio("Tipo de Atendimento:", ["Cliente Cadastrado", "Atendimento Avulso (Particular)"], horizontal=True)
        st.write("---")
        
        if "os_busca_val" not in st.session_state: st.session_state.os_busca_val = ""
        if "os_cli_val" not in st.session_state: st.session_state.os_cli_val = ""
        if "os_loc_val" not in st.session_state: st.session_state.os_loc_val = ""
        if "os_bairro_orig_val" not in st.session_state: st.session_state.os_bairro_orig_val = ""
        if "os_cidade_orig_val" not in st.session_state: st.session_state.os_cidade_orig_val = ""
        if "os_cep_orig_val" not in st.session_state: st.session_state.os_cep_orig_val = ""
        if "os_dest_val" not in st.session_state: st.session_state.os_dest_val = ""
        if "os_obs_val" not in st.session_state: st.session_state.os_obs_val = ""

        pronto_para_prosseguir = False
        is_excecao_flag = False
        valor_excecao_val = "0,00"
        cliente_id_os, cliente_nome_os, placa_alvo, veiculo_desc_alvo, empresa_os, plano_km_os, uf_cliente, cidade_cliente, valor_cobrado_os = "", "", "", "", "", "", "RN", "", "0,00"
        tel_envio_link = ""

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
                                        if v.get('Placa'): 
                                            blindado_str = " 🛡️ BLINDADO" if v.get('Blindado') in [True, 'true', 'Sim', 'SIM', '1'] else ""
                                            tipo_str = v.get('Tipo', 'Carro')
                                            lista_frota_opcoes.append(f"{tipo_str} {v.get('Modelo/Ano', '')}{blindado_str} - Placa: {v.get('Placa')}")
                                except: pass 
                            if not lista_frota_opcoes:
                                if pd.notna(cliente_dados.get('pla')) and str(cliente_dados['pla']).strip(): lista_frota_opcoes.append(f"{cliente_dados.get('vei', 'Veículo')} - Placa: {cliente_dados['pla']}")
                                if pd.notna(cliente_dados.get('pla_2')) and str(cliente_dados['pla_2']).strip(): lista_frota_opcoes.append(f"{cliente_dados.get('vei_2', 'Veículo')} - Placa: {cliente_dados['pla_2']}")
                            
                            if not lista_frota_opcoes: st.error("Este cliente não possui veículos cadastrados com placa válida.")
                            else:
                                veiculo_sel_os = st.selectbox("Selecione qual Veículo da frota será atendido:", lista_frota_opcoes)
                                tipo_servico = st.selectbox("Tipo de Serviço Solicitado:", ["Guincho", "Pane Seca", "Pane Elétrica", "Borracheiro", "Chaveiro"])
                                motivo_servico = st.selectbox("Motivo do Acionamento:", ["Acidente", "Furto", "Roubo", "Outros"])
                                
                                placa_alvo = veiculo_sel_os.split("Placa: ")[1].strip().upper()
                                veiculo_desc_alvo = veiculo_sel_os.split(" - Placa:")[0].strip()
                                
                                is_blindado = "BLINDADO" in veiculo_desc_alvo
                                veiculo_blindado_os = st.radio("Veículo é Blindado?", ["Não", "Sim"], index=1 if is_blindado else 0, horizontal=True)
                                
                                if veiculo_blindado_os == "Sim" and "BLINDADO" not in veiculo_desc_alvo:
                                    veiculo_desc_alvo += " (BLINDADO)"
                                elif veiculo_blindado_os == "Não" and "BLINDADO" in veiculo_desc_alvo:
                                    veiculo_desc_alvo = veiculo_desc_alvo.replace(" 🛡️ BLINDADO", "").replace("🛡️ BLINDADO", "").replace("(BLINDADO)", "").strip()

                                uf_cliente = str(cliente_dados['est']).strip().upper() if cliente_dados['est'] else "RN"
                                plano_km_os, cidade_cliente, cliente_id_os, cliente_nome_os, empresa_os = str(cliente_dados.get('plano_km', 'N/D')), str(cliente_dados.get('cidade', '')).strip().upper(), str(c_target_os), str(cliente_dados['nome']), str(cliente_dados['emp_name'])
                                tel_envio_link = apenas_numeros_letras(cliente_dados.get('tel', ''))

                                st.info(f"📍 Cliente: **{empresa_os.upper()}** | UF do Veículo: **{uf_cliente}**")
                                dt_cad_str = str(cliente_dados.get('data_cadastro', ''))
                                inicio_ciclo, fim_ciclo = obter_ciclo_contrato_anual(dt_cad_str)
                                st.markdown(f'<div class="info-box" style="padding: 10px;">🛣️ PLANO CONTRATADO: <b>{plano_km_os}</b><br>📅 CICLO DE CONTRATO DA PLACA: <b>{inicio_ciclo.strftime("%d/%m/%Y")} a {fim_ciclo.strftime("%d/%m/%Y")}</b></div>', unsafe_allow_html=True)
                                
                                df_os_carencia = df_os.copy()
                                df_os_carencia['data_hora'] = pd.to_datetime(df_os_carencia['data_hora'], errors='coerce')
                                df_os_carencia = df_os_carencia.dropna(subset=['data_hora'])
                                placa_alvo_limpa = apenas_numeros_letras(placa_alvo).upper()
                                
                                os_placa_ano = df_os_carencia[
                                    (df_os_carencia['placa'].astype(str).apply(lambda x: apenas_numeros_letras(x).upper()) == placa_alvo_limpa) & 
                                    (~df_os_carencia['status_os'].str.upper().isin(['CANCELADO'])) &
                                    (df_os_carencia['data_hora'] >= inicio_ciclo) &
                                    (df_os_carencia['data_hora'] <= fim_ciclo)
                                ]
                                
                                uso_atual = {"GUINCHO": 0, "PANE SECA": 0, "PANE ELÉTRICA": 0, "BORRACHEIRO": 0, "CHAVEIRO": 0}
                                for _, o in os_placa_ano.iterrows():
                                    serv = str(o['tipo_servico']).upper()
                                    if "GUINCHO" in serv: uso_atual["GUINCHO"] += 1
                                    elif "SECA" in serv: uso_atual["PANE SECA"] += 1
                                    elif "ELÉTRICA" in serv: uso_atual["PANE ELÉTRICA"] += 1
                                    elif "BORRACHEIRO" in serv: uso_atual["BORRACHEIRO"] += 1
                                    elif "CHAVEIRO" in serv: uso_atual["CHAVEIRO"] += 1
                                
                                st.markdown("##### 🔍 Auditoria de Saldos desta Placa neste Ano de Contrato:")
                                c_s1, c_s2, c_s3, c_s4, c_s5 = st.columns(5)
                                c_s1.metric("Guinchos", f"{uso_atual['GUINCHO']} / {LIMITES_ANUAIS['GUINCHO']}")
                                c_s2.metric("Pane Seca", f"{uso_atual['PANE SECA']} / {LIMITES_ANUAIS['PANE SECA']}")
                                c_s3.metric("Pane Elétrica", f"{uso_atual['PANE ELÉTRICA']} / {LIMITES_ANUAIS['PANE ELÉTRICA']}")
                                c_s4.metric("Borracheiro", f"{uso_atual['BORRACHEIRO']} / {LIMITES_ANUAIS['BORRACHEIRO']}")
                                c_s5.metric("Chaveiro", f"{uso_atual['CHAVEIRO']} / {LIMITES_ANUAIS['CHAVEIRO']}")
                                
                                tipo_servico_limpo = tipo_servico.upper()
                                limite_excedido = uso_atual.get(tipo_servico_limpo, 0) >= LIMITES_ANUAIS.get(tipo_servico_limpo, 1)

                                os_recentes = df_os_carencia[
                                    (df_os_carencia['placa'].astype(str).apply(lambda x: apenas_numeros_letras(x).upper()) == placa_alvo_limpa) & 
                                    (~df_os_carencia['status_os'].str.upper().isin(['CANCELADO']))
                                ]
                                
                                bloqueio_60 = False
                                msg_bloqueio_60 = ""
                                if not os_recentes.empty:
                                    ultima_os = os_recentes.sort_values('data_hora', ascending=False).iloc[0]
                                    dias_passados = (obter_hora_brasilia().replace(tzinfo=None) - ultima_os['data_hora']).days
                                    if 0 <= dias_passados < 60:
                                        bloqueio_60 = True
                                        data_ult = ultima_os['data_hora'].strftime("%d/%m/%Y")
                                        msg_bloqueio_60 = f"Veículo acionou a Central há {dias_passados} dias (em {data_ult}). Faltam {60 - dias_passados} dias para novo acionamento."

                                status_cliente_os = str(cliente_dados.get('status', 'Ativo')).strip()
                                cliente_inativo = (status_cliente_os == 'Inativo')

                                if cliente_inativo or bloqueio_60 or limite_excedido:
                                    st.write("---")
                                    if cliente_inativo: st.markdown('<div class="alert-box alert-danger" style="font-size: 14px; text-align: center;">🚫 ALERTA: CLIENTE INATIVO 🚫<br><span style="font-size: 13px; font-weight: normal;">Possível inadimplência ou cancelamento.</span></div>', unsafe_allow_html=True)
                                    if bloqueio_60: st.markdown(f'<div class="alert-box alert-danger" style="font-size: 14px; text-align: center;">🚫 ALERTA: REGRA DOS 60 DIAS ATIVA 🚫<br><span style="font-size: 13px; font-weight: bold;">{msg_bloqueio_60}</span></div>', unsafe_allow_html=True)
                                    if limite_excedido: st.markdown(f'<div class="alert-box alert-danger" style="font-size: 14px; text-align: center;">🚫 ALERTA: LIMITE ANUAL ESTOURADO 🚫<br><span style="font-size: 13px; font-weight: bold;">Esta placa já utilizou o limite máximo de {tipo_servico} no ciclo de contrato atual.</span></div>', unsafe_allow_html=True)
                                        
                                    liberar_excecao = st.checkbox("⚠ Ciente dos bloqueios acima: Liberar Atendimento por Exceção")
                                    if liberar_excecao: 
                                        valor_excecao_val = st.text_input("Valor do Serviço Extra a ser Cobrado (R$):", value="0,00")
                                        valor_cobrado_os = valor_excecao_val
                                        is_excecao_flag = True
                                        pronto_para_prosseguir = True
                                    else: pronto_para_prosseguir = False
                                else: pronto_para_prosseguir = True
        else:
            st.info("📝 Digite as informações do atendimento avulso particular abaixo:")
            col_av1, col_av2 = st.columns(2)
            nome_avulso, tel_avulso = col_av1.text_input("Nome Completo do Cliente:"), col_av2.text_input("Telefone de Contato:")
            veiculo_avulso = col_av1.text_input("Veículo (Tipo/Modelo/Ano/Cor):")
            placa_avulso = col_av2.text_input("Placa do Veículo:")
            
            veiculo_blindado_os = col_av1.radio("Veículo é Blindado?", ["Não", "Sim"], horizontal=True)
            if veiculo_blindado_os == "Sim":
                veiculo_avulso += " (BLINDADO)"
                
            uf_cliente, cidade_cliente = col_av1.selectbox("Estado (UF) do Atendimento:", options=ESTADOS_BR, index=ESTADOS_BR.index("RN")), col_av2.text_input("Cidade do Atendimento:")
            valor_cobrado_os = col_av1.text_input("Valor Cobrado do Particular (R$):", value="0,00")
            tipo_servico = st.selectbox("Tipo de Serviço:", ["Guincho", "Pane Seca", "Pane Elétrica", "Borracheiro", "Chaveiro"])
            motivo_servico = st.selectbox("Motivo do Acionamento:", ["Acidente", "Furto", "Roubo", "Outros"])
            cliente_id_os, cliente_nome_os, placa_alvo, veiculo_desc_alvo, empresa_os, plano_km_os = "AVULSO", nome_avulso, placa_avulso.upper().strip(), veiculo_avulso, "CLIENTE PARTICULAR (AVULSO)", "Particular"
            tel_envio_link = apenas_numeros_letras(tel_avulso)
            
            if nome_avulso and placa_alvo: pronto_para_prosseguir = True
            else: st.warning("⚠️ Nome do Cliente e Placa são obrigatórios para liberar o atendimento avulso.")

        if pronto_para_prosseguir:
            st.write("---")
            st.markdown('<div class="section-title">📍 Endereço da Ocorrência e Destino</div>', unsafe_allow_html=True)
            st.info("Caso o cliente não saiba explicar onde está, use o botão verde abaixo para enviar o link de captura de GPS. Quando ele clicar, o endereço de origem será preenchido sozinho.")
            link_captura = f"https://ad-central-mrssupqbb9ux69bi4qgisa.streamlit.app/?portal=cliente&placa={placa_alvo}"
            col_loc1, col_loc2 = st.columns([1, 1])
            texto_zap_loc = f"Olá! Aqui é da *Central AD Assistência 24h*.\n\nPara despacharmos o seu socorro rápido, precisamos da sua localização exata. Por favor, clique no link abaixo, permita o uso do GPS e aperte no botão 'ENVIAR MINHA LOCALIZAÇÃO':\n\n{link_captura}"
            link_w_loc = f"https://api.whatsapp.com/send?phone=55{tel_envio_link}&text={urllib.parse.quote(texto_zap_loc)}"
            
            with col_loc1:
                st.markdown(f'<a href="{link_w_loc}" target="_blank"><button style="background-color: #25D366; color: white; padding: 10px; width: 100%; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; font-size: 13px;">📲 1. Enviar Link no WhatsApp do Cliente</button></a>', unsafe_allow_html=True)
            with col_loc2:
                if st.button("🔄 2. Puxar Localização Recebida do Cliente", use_container_width=True, key="btn_puxar_loc_admin"):
                    df_loc_temp = carregar_dados(FILE_LOC, ['placa', 'data_hora', 'link_maps'])
                    loc_cliente = df_loc_temp[df_loc_temp['placa'] == placa_alvo]
                    if not loc_cliente.empty:
                        ultima_loc = loc_cliente.iloc[-1]['link_maps']
                        st.session_state.os_loc_val = ultima_loc
                        st.success("✅ GPS recebido com sucesso! O campo 'Origem' foi preenchido.")
                        time.sleep(2); st.rerun()
                    else: st.warning("⏳ O cliente ainda não enviou a localização. Aguarde alguns segundos e clique novamente.")

            st.write("")
            c_orig1, c_orig_b, c_orig2 = st.columns([1, 1, 3])
            cep_orig = c_orig1.text_input("CEP Origem (Aperte Buscar):", value=st.session_state.os_cep_orig_val, placeholder="Somente números")
            st.session_state.os_cep_orig_val = cep_orig

            if c_orig1.button("🔍 Buscar Origem", use_container_width=True, key="btn_cep_orig_admin"):
                end_orig, bairro_api, cid_api, uf_api = buscar_endereco_por_cep(cep_orig)
                if end_orig:
                    st.session_state.os_loc_val = end_orig
                    st.session_state.os_bairro_orig_val = bairro_api
                    st.session_state.os_cidade_orig_val = cid_api
                    st.rerun()
                else: st.error("CEP inválido ou não encontrado.")
                
            bairro_orig = c_orig_b.text_input("Bairro Origem:", value=st.session_state.os_bairro_orig_val)
            st.session_state.os_bairro_orig_val = bairro_orig
            
            localizacao = c_orig2.text_input("Endereço de Origem Completo (Onde pegar o veículo):", value=st.session_state.os_loc_val)
            st.session_state.os_loc_val = localizacao

            c_dest1, c_dest2 = st.columns([1, 4])
            cep_dest = c_dest1.text_input("CEP Destino (Opcional):", placeholder="Somente números")
            if c_dest1.button("🔍 Buscar Destino", use_container_width=True, key="btn_cep_dest_admin"):
                end_dest, _, _, _ = buscar_endereco_por_cep(cep_dest)
                if end_dest:
                    st.session_state.os_dest_val = end_dest
                    st.rerun()
                else: st.error("CEP inválido ou não encontrado.")
            destino = c_dest2.text_input("Endereço de Destino Completo (Onde deixar o veículo):", value=st.session_state.os_dest_val)
            st.session_state.os_dest_val = destino
            
            obs = st.text_area("Observações Extras para o Guincheiro:", value=st.session_state.os_obs_val)
            st.session_state.os_obs_val = obs

            st.write("---")
            st.markdown('<div class="section-title">🛠️ Prestador Acionado (Inteligência de Despacho)</div>', unsafe_allow_html=True)
            
            lista_p_ops = ["Outro (Digitar Manualmente)"]
            
            cep_busca = apenas_numeros_letras(st.session_state.os_cep_orig_val)
            bairro_busca = st.session_state.os_bairro_orig_val.strip().upper()
            cid_busca_final = st.session_state.os_cidade_orig_val.strip().upper() if st.session_state.os_cidade_orig_val else cidade_cliente.strip().upper()

            if not df_prestadores.empty:
                df_prest_filtrados = df_prestadores[(df_prestadores['est'].str.strip().str.upper() == uf_cliente.upper()) & (df_prestadores['status'] == 'Ativo') & (df_prestadores['homologado'] == 'Aprovado')].copy()
                if not df_prest_filtrados.empty:
                    def calcular_prioridade(row):
                        p_cep = apenas_numeros_letras(row.get('cep', ''))
                        p_bairro = str(row.get('bairro', '')).strip().upper()
                        p_cidade = str(row.get('cidade', '')).strip().upper()

                        if cep_busca and p_cep == cep_busca: return 0
                        elif bairro_busca and p_bairro == bairro_busca and p_cidade == cid_busca_final: return 1
                        elif cid_busca_final and p_cidade == cid_busca_final: return 2
                        else: return 3

                    df_prest_filtrados['prioridade'] = df_prest_filtrados.apply(calcular_prioridade, axis=1)
                    df_prest_filtrados = df_prest_filtrados.sort_values(by=['prioridade', 'nome'])
                    
                    for _, r in df_prest_filtrados.iterrows():
                        if r['prioridade'] == 0: marcador = "📍 [EXATO - MESMO CEP] "
                        elif r['prioridade'] == 1: marcador = "📍 [PRÓXIMO - MESMO BAIRRO] "
                        elif r['prioridade'] == 2: marcador = "📍 [MESMA CIDADE] "
                        else: marcador = ""
                        lista_p_ops.append(f"{marcador}{str(r['nome'])} - Tel: {str(r['telefone'])} - Bairro: {str(r.get('bairro','N/D')).upper()} - {str(r['cidade']).upper()}/{str(r['est']).upper()}")
                else:
                    df_aprovados = df_prestadores[df_prestadores['homologado'] == 'Aprovado']
                    for _, r in df_aprovados.iterrows(): 
                        lista_p_ops.append(f"{str(r['nome'])} - Tel: {str(r['telefone'])} - Bairro: {str(r.get('bairro','N/D')).upper()} - {str(r['cidade']).upper()}/{str(r['est']).upper()}")
            
            prestador_sel = st.selectbox("Prestadores homologados (Ordenados por prioridade/proximidade automática):", lista_p_ops)
            if prestador_sel == "Outro (Digitar Manualmente)":
                prestador_final = "GUINCHEIRO AVULSO"
                tel_prestador_final = apenas_numeros_letras(st.text_input("WhatsApp do Guincheiro Avulso (DDD + Número):"))
            else:
                prestador_limpo = prestador_sel.replace("📍 [EXATO - MESMO CEP] ", "").replace("📍 [PRÓXIMO - MESMO BAIRRO] ", "").replace("📍 [MESMA CIDADE] ", "")
                prestador_final = prestador_limpo.split(" - Tel:")[0]
                tel_prestador_final = apenas_numeros_letras(prestador_limpo.split(" - Tel:")[1].split("-")[0].strip())
            
            st.write("---")
            
            if is_excecao_flag:
                emp_match = df_empresas[df_empresas['nome'].str.upper() == empresa_os.upper()]
                resp_empresa = emp_match.iloc[0].get('responsavel', 'Responsável') if not emp_match.empty else 'Responsável'
                tel_responsavel = apenas_numeros_letras(emp_match.iloc[0].get('telefone', '')) if not emp_match.empty else ''
                if not tel_responsavel: tel_responsavel = tel_envio_link

                texto_pix = (f"🚨 *ATENDIMENTO DE EXCEÇÃO - AD RASTREAMENTO* 🚨\n\nOlá *{resp_empresa}* (Empresa: *{empresa_os}*),\n\nO acionamento de exceção para o veículo *{veiculo_desc_alvo}* - Placa: *{placa_alvo}* foi autorizado.\n\n📋 *Detalhes completos do Atendimento:*\n• Serviço: {tipo_servico} ({motivo_servico})\n• Onde pegar (Origem): {localizacao if localizacao else 'A informar'}\n• Onde deixar (Destino): {destino if destino else 'A informar'}\n• Motivo da Exceção: Limite Anual ou Carência de 60 dias atingida\n\n💰 *Valor do Serviço Extra:* R$ {valor_excecao_val}\n\n⚠️ *Atenção:* O deslocamento do prestador será iniciado *somente após o envio do comprovante* de pagamento.\n\n📲 *DADOS PARA PAGAMENTO (PIX):*\nChave PIX (CNPJ): *55496449000184*\nNome: *AD Rastreamento Veicular LTDA*\n\nEnvie o comprovante nesta conversa para despacharmos o socorro imediatamente!")
                link_w_pix = f"https://api.whatsapp.com/send?phone=55{tel_responsavel}&text={urllib.parse.quote(texto_pix)}"
                if not tel_responsavel: st.warning("⚠️ Atenção: Nenhum telefone cadastrado para a empresa ou cliente. Cadastre no perfil para enviar direto.")
                st.markdown(f'<a href="{link_w_pix}" target="_blank" style="text-decoration: none;"><button style="background-color: #00bfa5; color: white; padding: 10px 20px; border: none; border-radius: 6px; font-weight: bold; margin-bottom: 5px; width: 100%; font-size: 13px;">💬 PASSO EXTRA: Enviar Cobrança PIX para o Responsável ({resp_empresa})</button></a>', unsafe_allow_html=True)

            texto_btn_os = "🚀 Finalizar e Gerar OS do Guincho"
            if st.button(texto_btn_os, type="primary", key="btn_gerar_os_admin"):
                if not tel_prestador_final: st.error("O número de WhatsApp do guincheiro é obrigatório.")
                elif not localizacao: st.error("O Endereço de Origem é obrigatório!")
                else:
                    with st.spinner("Registrando OS e sincronizando com a nuvem..."):
                        nova_id = int(df_os['id'].astype(float).max() + 1) if not df_os.empty else 1
                        nova_os = pd.DataFrame([{
                            'id': str(nova_id), 'data_hora': obter_hora_str(), 'cliente_id': str(cliente_id_os), 
                            'cliente_nome': str(cliente_nome_os).upper(), 'cliente_tel': tel_envio_link, 'placa': placa_alvo, 
                            'veiculo_desc': str(veiculo_desc_alvo).upper(), 'empresa': empresa_os, 'tipo_servico': tipo_servico, 
                            'motivo': motivo_servico, 'prestador': f"{prestador_final} | Telefone/Zap: {tel_prestador_final}", 
                            'localizacao': localizacao, 'destino': destino, 'obs': obs, 'status_os': "EM ATENDIMENTO", 
                            'plano_km': plano_km_os, 'valor_cobrado': valor_cobrado_os,
                            'motorista_nome': '', 'motorista_tel': '', 'fotos_vistoria': '', 'assinatura_cliente': ''
                        }])
                        df_os_temp = pd.concat([df_os, nova_os], ignore_index=True)
                        sucesso, erro = salvar_dados(df_os_temp, FILE_OS)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "NOVA OS", f"Abriu chamado {nova_id} para a placa {placa_alvo}")
                            st.success(f"✅ Chamado Nº {nova_id} Aberto! Redirecionando para aba de Pendências...")
                            for k in ["os_busca_val", "os_cli_val", "os_loc_val", "os_bairro_orig_val", "os_cidade_orig_val", "os_cep_orig_val", "os_dest_val", "os_obs_val"]: st.session_state[k] = ""
                            time.sleep(1.5); 
                            st.query_params["nav"] = aba_pendencias_nome
                            st.rerun()
                        else: st.error(f"⚠️ Erro ao salvar OS na nuvem: {erro}")

    elif aba_selecionada == aba_pendencias_nome:
        st.markdown(f'<div class="section-title">{aba_pendencias_nome} (OS em Andamento)</div>', unsafe_allow_html=True)

        df_abertas = df_os[~df_os['status_os'].str.upper().isin(['ENCERRADO', 'CANCELADO'])]
        
        if df_abertas.empty: 
            st.success("Nenhum chamado pendente no momento! 🎉")
        else:
            lista_abertas = []
            for _, r in df_abertas.iterrows():
                mot = f" | Resp: {r.get('motorista_nome')}" if r.get('motorista_nome') else ""
                lista_abertas.append(f"OS Nº: {r['id']} | Status: {r['status_os']} | Placa: {r.get('placa','N/D')}{mot}")
            
            os_sel_str = st.selectbox("Selecione o chamado para Gerenciar / Auditar / Dar Baixa:", lista_abertas)
            os_id_alvo = os_sel_str.split("|")[0].replace("OS Nº:", "").strip()
            row_os = df_abertas[df_abertas['id'].astype(str) == os_id_alvo].iloc[0]
            status_dessa_os = str(row_os['status_os']).upper()
            prestador_info = str(row_os['prestador'])
            tel_prestador_final = prestador_info.split("Telefone/Zap: ")[1].strip() if "Telefone/Zap: " in prestador_info else ""
            
            cli_id_os = str(row_os['cliente_id'])
            tel_cliente_os = str(row_os.get('cliente_tel', ''))
            
            v_desc_wpp = str(row_os.get('veiculo_desc', 'N/D'))
            if "CARRO " in v_desc_wpp.upper() and any(m in v_desc_wpp.upper() for m in MARCAS_MOTO):
                v_desc_wpp = v_desc_wpp.replace("CARRO ", "MOTO ").replace("Carro ", "Moto ")
            
            if status_dessa_os == 'CONCLUÍDO':
                st.success("🏁 **ATENÇÃO:** O guincheiro finalizou a entrega e marcou esta OS como CONCLUÍDA. Por favor, audite os dados abaixo e encerre a OS para liberar a pesquisa de satisfação (NPS).")
            
            st.write(f"**Cliente:** {row_os['cliente_nome']} | **Veículo:** {v_desc_wpp} - {row_os.get('placa', '')}")
            st.write(f"**Origem:** {row_os['localizacao']} | **Destino:** {row_os['destino']}")
            st.write(f"**Base/Grupo Acionado:** {prestador_info}")
            
            motorista_n = str(row_os.get('motorista_nome', '')).strip()
            if motorista_n and motorista_n.lower() != 'nan':
                st.markdown(f'<div class="alert-box alert-success" style="padding: 10px; margin-top: 10px;">🚚 <b>Guincheiro Responsável:</b> {motorista_n} | <b>Tel:</b> {row_os.get("motorista_tel", "").split("|")[0]}</div>', unsafe_allow_html=True)
            
            obs_val = str(row_os.get('obs', ''))
            if obs_val.strip() == "" or obs_val.lower() == "nan": obs_val = "Nenhuma"
            st.write(f"**Observações Extras:** {obs_val}")
            
            fotos_str = str(row_os.get('fotos_vistoria', ''))
            doc_cliente_nps = "N/D"
            if fotos_str and fotos_str.lower() != 'nan' and '{' in fotos_str:
                try:
                    fotos_dict = json.loads(fotos_str)
                    doc_cliente_nps = fotos_dict.get('doc_cliente', 'N/D')
                    st.write("**📸 Fotos da Vistoria (Embarque):**")
                    cf1, cf2, cf3, cf4 = st.columns(4)
                    if fotos_dict.get('frente'): cf1.image(base64.b64decode(fotos_dict['frente']), caption="Frente", use_container_width=True)
                    if fotos_dict.get('traseira'): cf2.image(base64.b64decode(fotos_dict['traseira']), caption="Traseira", use_container_width=True)
                    if fotos_dict.get('lat_dir'): cf3.image(base64.b64decode(fotos_dict['lat_dir']), caption="Lat. Direita", use_container_width=True)
                    if fotos_dict.get('lat_esq'): cf4.image(base64.b64decode(fotos_dict['lat_esq']), caption="Lat. Esquerda", use_container_width=True)
                except: pass
                
            ass_str = str(row_os.get('assinatura_cliente', ''))
            if ass_str and ass_str.lower() not in ['nan', 'none', '']:
                st.write("**✍️ Assinatura do Cliente:**")
                st.write(f"**Documento Identificador (CPF/RG):** {doc_cliente_nps}")
                try: st.image(base64.b64decode(ass_str), width=200)
                except: pass
            
            is_blindado_msg = "SIM 🛡 (Atenção ao peso/capacidade da plataforma)" if "BLINDADO" in v_desc_wpp.upper() else "NÃO"
            empresa_nome_wpp = str(row_os.get('empresa', 'AD Rastreamento')).upper()
            if empresa_nome_wpp == 'CLIENTE PARTICULAR (AVULSO)': empresa_nome_wpp = 'AD RASTREAMENTO'
            
            link_nps_cliente = f"https://ad-central-mrssupqbb9ux69bi4qgisa.streamlit.app/?portal=nps&os={os_id_alvo}"
            texto_w_nps = f"Olá! Seu atendimento de assistência 24 horas pela *{empresa_nome_wpp}* foi concluído.\n\nComo foi sua experiência? Conte para nós em menos de 30 segundos avaliando neste link: {link_nps_cliente}"
            
            valor_str = ""
            val_cobrado = str(row_os.get('valor_cobrado', '0,00')).strip()
            is_avulso = "AVULSO" in str(row_os.get('cliente_id', '')).upper() or str(row_os.get('plano_km', '')).strip().lower() == "particular"
            
            if is_avulso and val_cobrado not in ['0,00', '0.00', '0', '']:
                valor_str = f"*Valor Particular:* R$ {val_cobrado}\n"
                
            texto_whatsapp = (f"*{empresa_nome_wpp} - ASSISTÊNCIA 24H*\n"
                              f"-----------------------------------------\n"
                              f"*Chamado Nº:* {row_os['id']}\n"
                              f"*Data/Hora:* {row_os['data_hora']}\n"
                              f"*Plano KM:* {row_os.get('plano_km', 'N/D')}\n"
                              f"{valor_str}"
                              f"*Serviço:* {row_os['tipo_servico']} | *Motivo:* {row_os['motivo']}\n\n"
                              f"*Cliente:* {str(row_os['cliente_nome']).upper()}\n"
                              f"*Telefone do Cliente:* {mascarar_telefone(tel_cliente_os)}\n\n"
                              f"*Veículo:* {v_desc_wpp} - Placa: {mascarar_placa(row_os.get('placa', 'N/D'))}\n"
                              f"*Veículo Blindado:* {is_blindado_msg}\n\n"
                              f"*Origem:* {row_os['localizacao']}\n"
                              f"*Destino:* {row_os['destino']}\n\n"
                              f"*Obs:* {obs_val}\n\n"
                              f"🚨 *PARA ASSUMIR ESSE CHAMADO, CLIQUE NO LINK ABAIXO:*\n"
                              f"https://ad-central-mrssupqbb9ux69bi4qgisa.streamlit.app/?portal=guincho&os={os_id_alvo}")
            
            link_w = f"https://api.whatsapp.com/send?phone=55{tel_prestador_final}&text={urllib.parse.quote(texto_whatsapp)}"
            link_w_cli_nps = f"https://api.whatsapp.com/send?phone=55{apenas_numeros_letras(tel_cliente_os)}&text={urllib.parse.quote(texto_w_nps)}"
            
            st.write("---")
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1: 
                if status_dessa_os != 'CONCLUÍDO':
                    st.markdown(f'<a href="{link_w}" target="_blank"><button style="background-color: #25D366; color: white; padding: 10px 20px; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; width: 100%; font-size: 13px;">📲 1. Enviar OS para o Prestador</button></a>', unsafe_allow_html=True)
                else:
                    st.info("OS já concluída pelo guincheiro. Realize a auditoria ao lado.")
            with col_btn2:
                texto_btn_encerrar = "🔒 Auditar e Encerrar OS no Sistema" if status_dessa_os == 'CONCLUÍDO' else "🔒 Encerrar OS no Sistema"
                if st.button(texto_btn_encerrar, key="btn_encerrar_os_adm", type="primary", use_container_width=True):
                    with st.spinner("Encerrando OS e abrindo WhatsApp para envio de NPS..."):
                        df_os.loc[df_os['id'].astype(str) == os_id_alvo, 'status_os'] = "ENCERRADO"
                        sucesso, erro = salvar_dados(df_os, FILE_OS)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "ENCERRAMENTO OS", f"Finalizou o chamado {os_id_alvo}")
                            st.success("✅ OS Encerrada com sucesso! O WhatsApp do cliente abrirá em nova aba automaticamente...")
                            
                            js_auto_open = f"""
                            <script>
                                window.open("{link_w_cli_nps}", "_blank");
                            </script>
                            """
                            components.html(js_auto_open, height=0, width=0)
                            
                            time.sleep(2.5)
                            st.rerun()
                        else: st.error(f"Erro na nuvem: {erro}")

    elif aba_selecionada == "📊 Relatórios & PDF":
        st.markdown('<div class="section-title">📊 Chamados e Relatórios</div>', unsafe_allow_html=True)
        os_id_edit = st.text_input("Digite o ID da OS para editar ou excluir:")
        if os_id_edit:
            os_encontrada = df_os[df_os['id'].astype(str) == str(os_id_edit)]
            if not os_encontrada.empty:
                row_os = os_encontrada.iloc[0]
                with st.form(f"form_edit_os_{os_id_edit}"):
                    st.write(f"**Empresa:** {row_os.get('empresa','')} | **Cliente:** {row_os.get('cliente_nome','')} | **Data:** {row_os.get('data_hora','')}")
                    c_os1, c_os2 = st.columns(2)
                    nova_placa = c_os1.text_input("Placa do Veículo:", value=row_os['placa'])
                    status_opcoes = ["PENDENTE", "EM ATENDIMENTO", "A CAMINHO", "EM TRÂNSITO", "CONCLUÍDO", "ENCERRADO", "CANCELADO"]
                    idx_stat = status_opcoes.index(row_os['status_os'].upper()) if row_os['status_os'].upper() in status_opcoes else 0
                    novo_status = c_os2.selectbox("Status da OS:", status_opcoes, index=idx_stat)
                    if st.form_submit_button("Salvar Correção da OS"):
                        with st.spinner("Atualizando OS..."):
                            df_os.loc[df_os['id'].astype(str) == str(os_id_edit), ['placa', 'status_os']] = [nova_placa.upper(), novo_status]
                            sucesso, erro = salvar_dados(df_os, FILE_OS)
                            if sucesso:
                                registrar_atividade(st.session_state.user, "CORREÇÃO DE OS", f"Editou a OS ID: {os_id_edit} | Nova Placa: {nova_placa.upper()} | Novo Status: {novo_status}")
                                st.success("✅ OS atualizada com sucesso! O cálculo de acionamento foi reajustado."); time.sleep(1.5); st.rerun()
                            else: st.error(f"Erro na nuvem: {erro}")
                
                if "os_del_confirm" not in st.session_state: st.session_state.os_del_confirm = None
                if st.session_state.os_del_confirm != os_id_edit:
                    if st.button("🗑️ Excluir esta OS permanentemente", key=f"btn_del_os_{os_id_edit}"): st.session_state.os_del_confirm = os_id_edit; st.rerun()
                if st.session_state.get("os_del_confirm") == os_id_edit:
                    st.error(f"⚠️ Atenção: Deseja realmente excluir a OS {os_id_edit}?")
                    col_s, col_n = st.columns(2)
                    if col_s.button("✅ Sim, excluir OS", key=f"btn_sim_del_os_{os_id_edit}"):
                        with st.spinner("Excluindo..."):
                            os_apagada = df_os[df_os['id'].astype(str) == str(os_id_edit)].iloc[0]
                            detalhes_exclusao_os = f"Apagou OS ID: {os_id_edit} | Cliente: {os_apagada['cliente_nome']} | Placa: {os_apagada['placa']} | Empresa: {os_apagada['empresa']}"
                            
                            deletar_registro_banco(FILE_OS, "id", str(os_id_edit))
                            df_os = df_os[df_os['id'].astype(str) != str(os_id_edit)]
                            
                            registrar_atividade(st.session_state.user, "EXCLUSÃO OS", detalhes_exclusao_os)
                            st.success("🗑️ OS excluída! Taxa de acionamento atualizada."); st.session_state.os_del_confirm = None; time.sleep(1.5); st.rerun()
                    if col_n.button("❌ Não, cancelar", key=f"btn_nao_del_os_{os_id_edit}"): st.session_state.os_del_confirm = None; st.rerun()
            else: st.warning("Nenhuma OS encontrada com esse ID.")

        st.write("---")
        st.markdown("##### ✅ Histórico e Gerar PDF (OS Finalizadas)")
        df_fechadas = df_os[df_os['status_os'].str.upper() == 'ENCERRADO'].sort_values(by='id', ascending=False)
        if df_fechadas.empty: st.info("Nenhum chamado foi finalizado ainda.")
        else:
            busca_os_relatorio = st.text_input("Digite a Placa do veículo ou o Nome para encontrar o relatório:")
            if busca_os_relatorio:
                df_filtrado_fechadas = df_fechadas[df_fechadas['cliente_nome'].str.contains(busca_os_relatorio, case=False, na=False) | df_fechadas['placa'].str.contains(busca_os_relatorio, case=False, na=False)]
                if df_filtrado_fechadas.empty: st.warning("Nenhum acionamento finalizado encontrado.")
                else:
                    lista_os_dele = [f"Chamado Nº: {r['id']} | Placa: {r.get('placa', 'N/D')} | Data: {r['data_hora']} | Serviço: {r['tipo_servico']}" for _, r in df_filtrado_fechadas.iterrows()]
                    os_escolhida_str = st.selectbox("Selecione qual acionamento deseja gerar o PDF:", options=lista_os_dele)
                    os_alvo_id = os_escolhida_str.split("|")[0].replace("Chamado Nº:", "").strip()
                    df_os_unica = df_os[df_os['id'].astype(str) == os_alvo_id]
                    st.markdown(exportar_pdf_html_oficial(df_os_unica, df_clientes, f"relatorio_os_{os_alvo_id}"), unsafe_allow_html=True)
        
        st.write("---")
        st.markdown("##### 🗃️ Tabela Geral de Chamados")
        st.dataframe(df_os, use_container_width=True)

    elif aba_selecionada == "👤 Clientes":
        st.markdown('<div class="section-title">👤 Gestão de Clientes</div>', unsafe_allow_html=True)
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
                    os_cli = df_os[df_os['cliente_id'].astype(str).str.strip() == str(c_id).strip()]
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
                            dados_emp_v = df_empresas[df_empresas['nome'].str.upper() == nome_emp.upper()]
                            dia_v = dados_emp_v.iloc[0].get('dia_vencimento', '30') if not dados_emp_v.empty else '30'
                            mes_a, ano_a = obter_mes_ano_vigente(dia_v)
                            dados_taxa_admin = calcular_fatura_parceiro(nome_emp, mes_a, ano_a, df_clientes, df_os, df_empresas)
                            st.markdown(f'<div class="info-box" style="padding:10px;">{gerar_texto_resumo_plano(dados_taxa_admin)}</div>', unsafe_allow_html=True)
                            st.dataframe(df_emp_filtrada[['nome','cpf','tel','cidade','plano_km','Histórico','status']].style.map(colorir_status, subset=['status']), use_container_width=True)
                            
                            key_sel_admin = f"sel_det_{emp}"
                            widget_key_admin = f"sel_sb_{emp}"
                            if key_sel_admin not in st.session_state: st.session_state[key_sel_admin] = ""
                            cli_opcoes = [""] + df_emp_filtrada['nome'].tolist()
                            idx_sel_admin = cli_opcoes.index(st.session_state[key_sel_admin]) if st.session_state[key_sel_admin] in cli_opcoes else 0
                            cli_sel = st.selectbox(f"🔍 Selecione um cliente da {nome_emp} para ver a Ficha Completa:", cli_opcoes, index=idx_sel_admin, key=widget_key_admin)
                            st.session_state[key_sel_admin] = cli_sel
                            if cli_sel != "":
                                cli_data = df_emp_filtrada[df_emp_filtrada['nome'] == cli_sel].iloc[0]
                                dt_cad_cliente = str(cli_data.get('data_cadastro', ''))
                                inicio_cli, fim_cli = obter_ciclo_contrato_anual(dt_cad_cliente)
                                st.markdown(f"### 📋 Ficha do Cliente: {cli_data['nome']}")
                                c1, c2 = st.columns(2)
                                c1.write(f"**CPF/CNPJ:** {cli_data['cpf']}"); c1.write(f"**Telefone:** {cli_data['tel']}"); c1.write(f"**Plano Contratado:** {cli_data.get('plano_km', 'N/D')}")
                                c2.write(f"**Endereço:** {cli_data.get('endereco', 'N/D')}, {cli_data.get('bairro', 'N/D')} - {cli_data.get('cidade', 'N/D')}/{cli_data.get('est', 'N/D')}"); c2.write(f"**Status:** {'🟢 Ativo' if cli_data['status'] == 'Ativo' else '🔴 Inativo'}")
                                c2.write(f"**Data de Cadastro:** {dt_cad_cliente}")
                                try: st.table(pd.DataFrame(json.loads(cli_data['veiculos_lista'])))
                                except: st.write(f"{cli_data.get('vei', '')} - Placa: {cli_data.get('pla', '')}")
                                
                                lista_frota_ficha = []
                                if pd.notna(cli_data.get('veiculos_lista')) and cli_data['veiculos_lista']:
                                    try:
                                        for v in json.loads(cli_data['veiculos_lista']):
                                            if v.get('Placa'): lista_frota_ficha.append(str(v.get('Placa')).upper().strip())
                                    except: pass 
                                if not lista_frota_ficha:
                                    if pd.notna(cli_data.get('pla')) and str(cli_data['pla']).strip(): lista_frota_ficha.append(str(cli_data['pla']).upper().strip())
                                    if pd.notna(cli_data.get('pla_2')) and str(cli_data['pla_2']).strip(): lista_frota_ficha.append(str(cli_data['pla_2']).upper().strip())
                                
                                if not lista_frota_ficha: st.warning("Nenhum veículo válido cadastrado para exibir saldos.")
                                else:
                                    placa_sel_ficha = st.selectbox("🚗 Selecione a Placa para ver o Saldo Operacional no Ano:", lista_frota_ficha, key=f"sel_placa_{emp}")
                                    st.write(f"**📊 Saldo de Limites da Placa {placa_sel_ficha} no Ano de Contrato ({inicio_cli.strftime('%d/%m/%Y')} a {fim_cli.strftime('%d/%m/%Y')}):**")
                                    uso_atual_f = {"GUINCHO": 0, "PANE SECA": 0, "PANE ELÉTRICA": 0, "BORRACHEIRO": 0, "CHAVEIRO": 0}
                                    if not df_os.empty:
                                        df_os_copy = df_os.copy()
                                        df_os_copy['data_hora'] = pd.to_datetime(df_os_copy['data_hora'], errors='coerce')
                                        placa_limpa_f = apenas_numeros_letras(placa_sel_ficha).upper()
                                        os_placa_f = df_os_copy[(df_os_copy['placa'].astype(str).apply(lambda x: apenas_numeros_letras(x).upper()) == placa_limpa_f) & (~df_os_copy['status_os'].str.upper().isin(['CANCELADO'])) & (df_os_copy['data_hora'] >= inicio_cli) & (df_os_copy['data_hora'] <= fim_cli)]
                                        for _, o in os_placa_f.iterrows():
                                            serv_f = str(o['tipo_servico']).upper()
                                            if "GUINCHO" in serv_f: uso_atual_f["GUINCHO"] += 1
                                            elif "SECA" in serv_f: uso_atual_f["PANE SECA"] += 1
                                            elif "ELÉTRICA" in serv_f or "ELETRICA" in serv_f: uso_atual_f["PANE ELÉTRICA"] += 1
                                            elif "BORRACHEIRO" in serv_f: uso_atual_f["BORRACHEIRO"] += 1
                                            elif "CHAVEIRO" in serv_f: uso_atual_f["CHAVEIRO"] += 1
                                    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
                                    col_m1.metric("Guinchos", f"{uso_atual_f['GUINCHO']} / {LIMITES_ANUAIS['GUINCHO']}")
                                    col_m2.metric("Pane Seca", f"{uso_atual_f['PANE SECA']} / {LIMITES_ANUAIS['PANE SECA']}")
                                    col_m3.metric("Elétrica", f"{uso_atual_f['PANE ELÉTRICA']} / {LIMITES_ANUAIS['PANE ELÉTRICA']}")
                                    col_m4.metric("Chaveiro", f"{uso_atual_f['CHAVEIRO']} / {LIMITES_ANUAIS['CHAVEIRO']}")
                                    col_m5.metric("Borracheiro", f"{uso_atual_f['BORRACHEIRO']} / {LIMITES_ANUAIS['BORRACHEIRO']}")
                                
                                if st.button("❌ Fechar Ficha", key=f"btn_close_{emp}"):
                                    st.session_state[key_sel_admin] = ""
                                    if widget_key_admin in st.session_state: del st.session_state[widget_key_admin]
                                    st.rerun()

        elif opcao_cli == "Incluir Novo":
            c1, c2, c3 = st.columns([2, 2, 1])
            nome_in = c1.text_input("Nome Completo:", value=st.session_state.get("cli_inc_nome", ""))
            st.session_state.cli_inc_nome = nome_in
            cpf_raw = c2.text_input("CPF/CNPJ:", value=st.session_state.get("cli_inc_cpf", ""))
            st.session_state.cli_inc_cpf = cpf_raw
            tel_raw = c3.text_input("Telefone:", value=st.session_state.get("cli_inc_tel", ""))
            st.session_state.cli_inc_tel = tel_raw
            
            end_in = c1.text_input("Endereço Completo:", value=st.session_state.get("cli_inc_end", ""))
            st.session_state.cli_inc_end = end_in
            bairro_in = c2.text_input("Bairro:", value=st.session_state.get("cli_inc_bairro", ""))
            st.session_state.cli_inc_bairro = bairro_in
            cid_in = c3.text_input("Cidade:", value=st.session_state.get("cli_inc_cid", ""))
            st.session_state.cli_inc_cid = cid_in
            
            cep_in = c1.text_input("CEP:", value=st.session_state.get("cli_inc_cep", ""))
            st.session_state.cli_inc_cep = cep_in
            cad_data = c2.date_input("Data de Cadastro (Início do Contrato):", value=datetime.now())
            
            st.write("---")
            st.write("🚗 **Frota do Cliente (Tabela Interativa - Adicione quantos quiser)**")
            df_frota_editavel = pd.DataFrame([{"Tipo": "Carro", "Modelo/Ano": "", "Placa": "", "Blindado": False}])
            frota_editada = st.data_editor(df_frota_editavel, column_config=FROTA_COL_CONFIG, num_rows="dynamic", use_container_width=True)
            st.write("---")
            
            lista_empresas_disponiveis = [str(e['nome']).upper() for _, e in df_empresas.iterrows()] if not df_empresas.empty else ["NENHUMA EMPRESA CADASTRADA"]
            emp = st.selectbox("Empresa Vinculada / Parceira:", options=lista_empresas_disponiveis, index=0)
            
            modo_fat_selecionado = "Tradicional"
            if not df_empresas.empty:
                dados_emp = df_empresas[df_empresas['nome'].str.upper() == emp.upper()]
                if not dados_emp.empty:
                    modo_fat_selecionado = dados_emp.iloc[0].get('modo_faturamento', 'Tradicional')
            
            if "Frota Pequena" in modo_fat_selecionado or "Até 40" in modo_fat_selecionado:
                opcoes_km_cli = ["50km", "100km"]
                st.info(f"💡 A empresa {emp} utiliza o plano **{modo_fat_selecionado}**. O cadastro está restrito aos KMs permitidos para esta modalidade.")
            elif "Escalonado" in modo_fat_selecionado:
                opcoes_km_cli = ["50km", "100km", "200km"]
                st.info(f"💡 A empresa {emp} utiliza o **Modo Escalonado**. Opções de 50km, 100km e 200km liberadas.")
            else:
                opcoes_km_cli = PLANOS_KM

            col_b1, col_b2, col_b3 = st.columns(3)
            est = col_b1.selectbox("Estado (UF) do Veículo:", options=ESTADOS_BR, index=ESTADOS_BR.index("RN"))
            plano_km = col_b2.selectbox("Plano Contratado (KM):", options=opcoes_km_cli, index=0)
            status = col_b3.selectbox("Status do Cliente:", ["Ativo", "Inativo"], index=0)
            
            if st.button("Salvar Novo Cliente"):
                nome, cpf, tel = nome_in.upper(), apenas_numeros_letras(cpf_raw), apenas_numeros_letras(tel_raw)
                frota_limpa = frota_editada.dropna(subset=['Placa', 'Modelo/Ano'], how='any')
                frota_limpa = frota_limpa[frota_limpa['Placa'].astype(str).str.strip() != ""]
                frota_limpa['Placa'] = frota_limpa['Placa'].astype(str).str.upper().str.replace("-","").str.replace(" ","")
                frota_limpa['Blindado'] = frota_limpa['Blindado'].fillna(False).astype(bool)
                
                frota_json_str = json.dumps(frota_limpa.to_dict('records'))
                vei_prin = frota_limpa.iloc[0]['Modelo/Ano'] if not frota_limpa.empty else ""
                pla_prin = frota_limpa.iloc[0]['Placa'] if not frota_limpa.empty else ""
                if not nome or not pla_prin: st.error("Nome e ao menos 1 Placa de Veículo (com modelo) são obrigatórios.")
                else:
                    with st.spinner("Salvando novo cliente..."):
                        prox = int(df_clientes['id'].astype(float).max() + 1) if not df_clientes.empty else 1
                        dt_str_save = cad_data.strftime("%Y-%m-%d")
                        novo = pd.DataFrame([{'id': str(prox), 'nome': nome, 'cpf': cpf, 'tel': tel, 'endereco': end_in, 'bairro': bairro_in.upper(), 'cidade': cid_in.upper(), 'cep': cep_in, 'plano_km': plano_km, 'vei': vei_prin, 'pla': pla_prin, 'est': est, 'emp_name': emp.upper(), 'status': status, 'veiculos_lista': frota_json_str, 'data_cadastro': dt_str_save}])
                        df_clientes_temp = pd.concat([df_clientes, novo], ignore_index=True)
                        sucesso, erro = salvar_dados(df_clientes_temp, FILE_CLIENTES)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "NOVO CLIENTE", f"Cadastrou {nome} para a empresa {emp}")
                            st.success("✅ Cliente cadastrado com sucesso!")
                            for k in ["cli_inc_nome", "cli_inc_cpf", "cli_inc_tel", "cli_inc_end", "cli_inc_bairro", "cli_inc_cid", "cli_inc_cep"]: st.session_state[k] = ""
                            st.session_state.aba_cli = "Listar"
                            time.sleep(1); st.rerun()
                        else:
                            st.error(f"⚠️ Erro ao salvar cliente na nuvem: {erro}")
                        
        elif opcao_cli == "Importação em Lote":
            st.info("💡 Suba o
