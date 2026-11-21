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
import re
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from PIL import Image
import io

try:
    from streamlit_drawable_canvas import st_canvas
    CANVAS_AVAILABLE = True
except ImportError:
    CANVAS_AVAILABLE = False

st.set_page_config(
    page_title="Central de Assistência 24 Horas - AD Rastreamento",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===================================================================================
# CONTROLE DE TEMA (CLARO / ESCURO — FUNCIONA NO ADMIN, PARCEIRO E PORTAL DO PRESTADOR)
# ===================================================================================
if "tema_app" not in st.session_state:
    st.session_state.tema_app = "Claro"

is_dark = (st.session_state.tema_app == "Escuro")

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
# CONSTANTES DE NEGÓCIO, PLANOS E CHAVE DE CONTROLE DA OPÇÃO B (60 DIAS)
# ===================================================================================
ESTADOS_BR = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
PLANOS_KM = ["Sem Limite", "50km", "100km", "150km", "200km", "300km", "400km", "500km"]
OPCOES_SERVICOS = ["Guincho", "Pane Seca", "Pane Elétrica", "Borracheiro", "Chaveiro"]
OPCOES_DIAS_VENC = ["5", "10", "15", "20", "25", "30", "31"]

LIMITES_ANUAIS = {"GUINCHO": 2, "PANE SECA": 1, "PANE ELÉTRICA": 1, "BORRACHEIRO": 1, "CHAVEIRO": 1}

# Se após 60 dias quiser travar novos cadastros da Opção B apenas em 50km e 100km, troque True para False:
OPCAO_B_PERMITIR_200KM = True

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
# ESTILIZAÇÃO CSS CORPORATIVA DE ALTO CONTRASTE + MENU LATERAL MINIMALISTA COM LINHA
# ===================================================================================
if is_dark:
    COR_BG_APP = "#0F172A"
    COR_BG_CARD = "#1E293B"
    COR_BG_CARD_ALT = "#162032"
    COR_BG_SIDEBAR = "#111827"
    COR_BORDA = "#334155"
    COR_TEXTO = "#F8FAFC"
    COR_TEXTO_SEC = "#CBD5E1"
    COR_ROXO_TXT = "#D8B4FE"
    COR_ROXO_DEST = "#C084FC"
    COR_VERM_TXT = "#FCA5A5"
    COR_VERDE_TXT = "#86EFAC"
    COR_OPEN_OS_BG = "#2A1215"
    COR_INFO_BG = "#1E1B2E"
    COR_INFO_BORDER = "#7E22CE"
    COR_ALERT_DANGER_BG = "#3B1318"
    COR_ALERT_DANGER_TXT = "#FECACA"
    COR_ALERT_SUCCESS_BG = "#0F2E1D"
    COR_ALERT_SUCCESS_TXT = "#BBF7D0"
    COR_RADIO_HOVER = "#2E1065"
    COR_HR = "#334155"
else:
    COR_BG_APP = "#F1F5F9"
    COR_BG_CARD = "#FFFFFF"
    COR_BG_CARD_ALT = "#F8FAFC"
    COR_BG_SIDEBAR = "#FFFFFF"
    COR_BORDA = "#CBD5E1"
    COR_TEXTO = "#0F172A"
    COR_TEXTO_SEC = "#475569"
    COR_ROXO_TXT = "#4A148C"
    COR_ROXO_DEST = "#6A1B9A"
    COR_VERM_TXT = "#C62828"
    COR_VERDE_TXT = "#1B5E20"
    COR_OPEN_OS_BG = "#FFF5F5"
    COR_INFO_BG = "#FFFFFF"
    COR_INFO_BORDER = "#C084FC"
    COR_ALERT_DANGER_BG = "#FEE2E2"
    COR_ALERT_DANGER_TXT = "#991B1B"
    COR_ALERT_SUCCESS_BG = "#DCFCE7"
    COR_ALERT_SUCCESS_TXT = "#166534"
    COR_RADIO_HOVER = "#F3E5F5"
    COR_HR = "#CBD5E1"

CSS_TEMA_CONTRASTE = """
    .stApp, .stApp p, .stApp span, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] li,
    div[data-testid="stMarkdownContainer"] strong {
        color: #F8FAFC;
    }
    div[data-testid="stCaptionContainer"] p {
        color: #CBD5E1 !important;
    }
    div[data-testid="stMetric"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 10px;
        padding: 10px 14px;
    }
    div[data-testid="stMetricLabel"] p, div[data-testid="stMetricValue"] {
        color: #F8FAFC !important;
    }
    input, textarea, select,
    div[data-baseweb="input"] > div,
    div[data-baseweb="base-input"],
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] > div {
        background-color: #0F172A !important;
        color: #F8FAFC !important;
        border: 1.5px solid #475569 !important;
        -webkit-text-fill-color: #F8FAFC !important;
    }
    input::placeholder, textarea::placeholder {
        color: #94A3B8 !important;
        -webkit-text-fill-color: #94A3B8 !important;
    }
    div[data-baseweb="select"] span, div[data-baseweb="select"] div {
        color: #F8FAFC !important;
    }
    ul[data-baseweb="menu"], div[data-baseweb="popover"] > div {
        background-color: #1E293B !important;
        color: #F8FAFC !important;
        border: 1px solid #475569 !important;
    }
    li[role="option"]:hover {
        background-color: #3B0764 !important;
    }
    details[data-testid="stExpander"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
    }
    details[data-testid="stExpander"] summary {
        color: #F8FAFC !important;
    }
    div[data-testid="stForm"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
        padding: 14px !important;
    }
    div[data-testid="stFileUploader"] section {
        background-color: #0F172A !important;
        border: 1.5px dashed #64748B !important;
        color: #F8FAFC !important;
    }
    div[data-testid="stFileUploader"] section small,
    div[data-testid="stFileUploader"] section span,
    div[data-testid="stFileUploader"] button {
        color: #F8FAFC !important;
    }
    div[data-testid="stAlert"] {
        background-color: #1E293B !important;
        border: 1px solid #475569 !important;
        color: #F8FAFC !important;
    }
    div[data-testid="stAlert"] p, div[data-testid="stAlert"] div {
        color: #F8FAFC !important;
    }
    button[data-baseweb="tab"] {
        color: #CBD5E1 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #D8B4FE !important;
    }
    table {
        background-color: #1E293B !important;
        color: #F8FAFC !important;
    }
    th, td {
        color: #F8FAFC !important;
        border-color: #334155 !important;
    }
""" if is_dark else """
    .stApp, .stApp p, .stApp span, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] li,
    div[data-testid="stMarkdownContainer"] strong {
        color: #0F172A;
    }
    div[data-testid="stCaptionContainer"] p {
        color: #475569 !important;
    }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px;
        padding: 10px 14px;
    }
    div[data-testid="stMetricLabel"] p, div[data-testid="stMetricValue"] {
        color: #0F172A !important;
    }
    input, textarea, select,
    div[data-baseweb="input"] > div,
    div[data-baseweb="base-input"],
    div[data-baseweb="select"] > div,
    div[data-baseweb="textarea"] > div {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1.5px solid #94A3B8 !important;
        -webkit-text-fill-color: #0F172A !important;
    }
    input::placeholder, textarea::placeholder {
        color: #64748B !important;
        -webkit-text-fill-color: #64748B !important;
    }
    div[data-baseweb="select"] span, div[data-baseweb="select"] div {
        color: #0F172A !important;
    }
    ul[data-baseweb="menu"], div[data-baseweb="popover"] > div {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid #CBD5E1 !important;
    }
    li[role="option"] {
        color: #0F172A !important;
    }
    li[role="option"]:hover {
        background-color: #F3E5F5 !important;
    }
    details[data-testid="stExpander"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px !important;
    }
    details[data-testid="stExpander"] summary {
        color: #0F172A !important;
    }
    div[data-testid="stForm"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px !important;
        padding: 14px !important;
    }
    div[data-testid="stFileUploader"] section {
        background-color: #FFFFFF !important;
        border: 2px dashed #6A1B9A !important;
        color: #0F172A !important;
    }
    div[data-testid="stFileUploader"] section small,
    div[data-testid="stFileUploader"] section span {
        color: #334155 !important;
    }
    div[data-testid="stFileUploader"] button {
        background-color: #6A1B9A !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    div[data-testid="stAlert"] {
        border: 1.5px solid #CBD5E1 !important;
        color: #0F172A !important;
    }
    div[data-testid="stAlert"] p, div[data-testid="stAlert"] div {
        color: #0F172A !important;
    }
    button[data-baseweb="tab"] {
        color: #475569 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #4A148C !important;
    }
    table {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
    }
    th, td {
        color: #0F172A !important;
        border-color: #CBD5E1 !important;
    }
"""

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    [data-testid="stMainMenu"] {{visibility: hidden;}}
    [data-testid="stToolbarActions"] {{visibility: hidden;}}
    [data-testid="stAppDeployButton"], .stDeployButton {{display: none !important;}}
    header[data-testid="stHeader"] {{
        background: transparent !important;
        visibility: visible !important;
    }}

    /* Botão da setinha de recolher/reabrir a barra lateral SEMPRE visível */
    [data-testid="stExpandSidebarButton"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"] {{
        visibility: visible !important;
        opacity: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    [data-testid="stExpandSidebarButton"] button,
    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapseButton"] button {{
        background-color: #6A1B9A !important;
        color: #FFFFFF !important;
        border: 2px solid #FFFFFF !important;
        border-radius: 8px !important;
        box-shadow: 0 3px 10px rgba(106, 27, 154, 0.35) !important;
        visibility: visible !important;
        opacity: 1 !important;
    }}
    [data-testid="stExpandSidebarButton"] button:hover,
    [data-testid="collapsedControl"] button:hover,
    [data-testid="stSidebarCollapseButton"] button:hover {{
        background-color: #D32F2F !important;
        color: #FFFFFF !important;
    }}
    [data-testid="stExpandSidebarButton"] svg,
    [data-testid="collapsedControl"] svg,
    [data-testid="stSidebarCollapseButton"] svg {{
        fill: #FFFFFF !important;
        color: #FFFFFF !important;
        stroke: #FFFFFF !important;
    }}

    /* Alerta SLA Crítico para OS sem prestador acima de 15 min */
    @keyframes slaPulse {{
        0% {{ box-shadow: 0 0 0 0 rgba(211, 47, 47, 0.7); border-color: #D32F2F; }}
        50% {{ box-shadow: 0 0 16px 3px rgba(211, 47, 47, 0.4); border-color: #FF5252; }}
        100% {{ box-shadow: 0 0 0 0 rgba(211, 47, 47, 0.7); border-color: #D32F2F; }}
    }}
    .sla-critical-banner {{
        background: linear-gradient(90deg, #B71C1C 0%, #D32F2F 100%);
        color: #FFFFFF !important;
        padding: 14px 20px;
        border-radius: 10px;
        border: 2px solid #FF8A80;
        margin-bottom: 16px;
        animation: slaPulse 1.6s infinite;
    }}
    .sla-critical-banner * {{ color: #FFFFFF !important; }}

    .stApp {{
        background-color: {COR_BG_APP};
        color: {COR_TEXTO};
    }}

    .block-container {{
        padding-top: 2.2rem !important;
        padding-bottom: 2rem !important;
        max-width: 98% !important;
    }}

    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-thumb {{ background: #6A1B9A; border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: #D32F2F; }}

    /* Barra Lateral Esquerda — Minimalista (Sem quadrados, apenas nomes + linha inferior) */
    section[data-testid="stSidebar"] {{
        background-color: {COR_BG_SIDEBAR};
        border-right: 1px solid {COR_BORDA};
        box-shadow: 2px 0 12px rgba(106, 27, 154, 0.06);
    }}
    section[data-testid="stSidebar"] > div:first-child {{
        padding-top: 0.8rem;
    }}
    .sidebar-brand-box {{
        background: linear-gradient(135deg, #4A148C 0%, #6A1B9A 70%, #D32F2F 100%);
        color: #FFFFFF !important;
        padding: 14px 16px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 18px;
        box-shadow: 0 4px 12px rgba(106, 27, 154, 0.22);
    }}
    .sidebar-brand-title {{
        font-size: 15px;
        font-weight: 900;
        letter-spacing: 0.6px;
        color: #FFFFFF !important;
    }}
    .sidebar-brand-sub {{
        font-size: 10px;
        opacity: 0.92;
        text-transform: uppercase;
        letter-spacing: 0.9px;
        margin-top: 3px;
        color: #FFFFFF !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] {{
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 4px !important;
        gap: 2px !important;
        display: flex;
        flex-direction: column;
    }}
    /* Oculta a bolinha do rádio na barra lateral para exibir apenas os nomes */
    section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child:not(:has(p)) {{
        display: none !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label {{
        width: 100% !important;
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        border-bottom: 1px solid {COR_HR} !important;
        border-radius: 0px !important;
        box-shadow: none !important;
        padding: 11px 6px 9px 6px !important;
        margin: 0 !important;
        cursor: pointer !important;
        transition: all 0.18s ease !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label p {{
        color: {COR_TEXTO_SEC} !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        letter-spacing: 0.1px !important;
        margin: 0 !important;
        transition: all 0.18s ease !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        background: transparent !important;
        border-bottom: 2px solid #6A1B9A !important;
        padding-left: 10px !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover p {{
        color: {COR_ROXO_DEST} !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
        background: transparent !important;
        border: none !important;
        border-bottom: 2.5px solid #D32F2F !important;
        box-shadow: none !important;
        padding-left: 10px !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {{
        color: {COR_ROXO_TXT} !important;
        font-weight: 800 !important;
    }}

    /* Cabeçalho Executivo e Títulos */
    .main-title {{
        font-size: 28px;
        font-weight: 900;
        background: linear-gradient(90deg, {COR_ROXO_DEST} 0%, #EF4444 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 4px;
        letter-spacing: -0.5px;
    }}
    .subtitle {{
        font-size: 12px;
        color: {COR_TEXTO_SEC};
        text-align: center;
        margin-bottom: 18px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.2px;
    }}
    .section-title {{
        font-size: 17px !important;
        font-weight: 800 !important;
        color: {COR_ROXO_TXT} !important;
        background: {COR_BG_CARD};
        padding: 12px 18px;
        border-radius: 10px;
        border: 1px solid {COR_BORDA};
        border-left: 5px solid #D32F2F;
        box-shadow: 0 2px 6px rgba(106, 27, 154, 0.08);
        margin-top: 4px !important;
        margin-bottom: 16px !important;
        letter-spacing: -0.2px;
    }}

    /* Barra Superior */
    .ad-topbar {{
        background: linear-gradient(90deg, #4A148C 0%, #6A1B9A 65%, #D32F2F 100%);
        color: #FFFFFF !important;
        padding: 14px 22px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 14px rgba(106, 27, 154, 0.22);
        margin-bottom: 8px;
    }}
    .ad-topbar * {{ color: #FFFFFF !important; }}
    .ad-topbar-brand {{
        display: flex;
        align-items: center;
        gap: 12px;
    }}
    .ad-badge-logo {{
        background: #FFFFFF;
        color: #6A1B9A !important;
        font-weight: 900;
        font-size: 15px;
        padding: 6px 10px;
        border-radius: 8px;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    }}
    .ad-badge-logo span {{ color: #D32F2F !important; }}
    .status-dot {{
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #4ADE80;
        margin-right: 6px;
    }}

    /* Etapas Visuais do Portal do Prestador */
    .prest-stepper {{
        display: flex;
        gap: 8px;
        margin: 12px 0 16px 0;
    }}
    .prest-step {{
        flex: 1;
        text-align: center;
        padding: 8px 6px;
        border-radius: 8px;
        font-size: 11.5px;
        font-weight: 800;
        text-transform: uppercase;
        border: 1.5px solid {COR_BORDA};
        background: {COR_BG_CARD};
        color: {COR_TEXTO_SEC};
    }}
    .prest-step.ativo {{
        background: #6A1B9A;
        border-color: #6A1B9A;
        color: #FFFFFF !important;
    }}
    .prest-step.concluido {{
        background: #2E7D32;
        border-color: #2E7D32;
        color: #FFFFFF !important;
    }}
    .prest-card {{
        background-color: {COR_BG_CARD};
        border: 1.5px solid {COR_BORDA};
        border-top: 4px solid #6A1B9A;
        border-radius: 12px;
        padding: 16px 18px;
        margin-bottom: 14px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.08);
    }}
    .prest-card p, .prest-card div {{
        color: {COR_TEXTO} !important;
    }}
    .prest-card-label {{
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        color: {COR_ROXO_DEST} !important;
        margin-bottom: 2px;
    }}
    .prest-card-val {{
        font-size: 14.5px;
        font-weight: 700;
        color: {COR_TEXTO} !important;
        margin-bottom: 10px;
    }}

    /* Submenus Horizontais (somente na área principal) */
    section.main div[role="radiogroup"] {{
        background-color: {COR_BG_CARD};
        padding: 8px 12px;
        border-radius: 12px;
        border: 1px solid {COR_BORDA};
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        gap: 6px;
    }}
    section.main div[role="radiogroup"] label {{
        background-color: {COR_BG_CARD_ALT} !important;
        border: 1px solid {COR_BORDA} !important;
        border-radius: 8px !important;
        padding: 6px 14px !important;
        color: {COR_TEXTO} !important;
        transition: all 0.2s ease;
    }}
    section.main div[role="radiogroup"] label:hover {{
        border-color: #6A1B9A !important;
        background-color: {COR_RADIO_HOVER} !important;
    }}

    /* Botões Principais */
    div.stButton > button:first-child,
    div.stDownloadButton > button:first-child {{
        background: linear-gradient(135deg, #6A1B9A 0%, #7B2CBF 100%);
        color: #FFFFFF !important;
        border: none;
        border-radius: 8px;
        font-weight: 700;
        font-size: 13px;
        padding: 0.58rem 1rem;
        box-shadow: 0 3px 8px rgba(106, 27, 154, 0.25);
        transition: all 0.2s ease;
    }}
    div.stButton > button:first-child p,
    div.stDownloadButton > button:first-child p {{
        color: #FFFFFF !important;
    }}
    div.stButton > button:first-child:hover,
    div.stDownloadButton > button:first-child:hover {{
        background: linear-gradient(135deg, #D32F2F 0%, #B71C1C 100%);
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(211, 47, 47, 0.35);
        transform: translateY(-1px);
    }}

    /* Alertas e Caixas */
    .alert-box {{
        padding: 14px 16px;
        border-radius: 10px;
        margin: 12px 0;
        border-left: 5px solid;
        font-weight: 600;
        font-size: 13.5px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }}
    .alert-danger {{ background-color: {COR_ALERT_DANGER_BG}; color: {COR_ALERT_DANGER_TXT} !important; border-color: #D32F2F; }}
    .alert-danger * {{ color: {COR_ALERT_DANGER_TXT} !important; }}
    .alert-success {{ background-color: {COR_ALERT_SUCCESS_BG}; color: {COR_ALERT_SUCCESS_TXT} !important; border-color: #2E7D32; }}
    .alert-success * {{ color: {COR_ALERT_SUCCESS_TXT} !important; }}
    .info-box {{
        background-color: {COR_INFO_BG};
        color: {COR_TEXTO} !important;
        border: 1.5px solid {COR_INFO_BORDER};
        border-left: 5px solid #6A1B9A;
        padding: 12px 16px;
        border-radius: 10px;
        margin: 10px 0;
        font-weight: 600;
        line-height: 1.6;
        font-size: 13.5px;
        box-shadow: 0 2px 8px rgba(106, 27, 154, 0.08);
    }}
    .info-box b, .info-box strong {{ color: {COR_ROXO_TXT} !important; }}

    /* Cards KPI Corporativos */
    .metric-card {{
        background-color: {COR_BG_CARD};
        border-radius: 12px;
        padding: 16px 18px;
        text-align: left;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 12px;
        border: 1px solid {COR_BORDA};
        border-top: 4px solid #6A1B9A;
    }}
    .metric-card.red-accent {{ border-top: 4px solid #D32F2F; }}
    .metric-card.green-accent {{ border-top: 4px solid #2E7D32; }}
    .metric-title {{
        color: {COR_TEXTO_SEC} !important;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.7px;
        margin-bottom: 4px;
    }}
    .metric-value {{
        font-size: 26px;
        font-weight: 900;
        color: {COR_TEXTO};
        line-height: 1.15;
    }}
    .metric-sub {{
        font-size: 11px;
        color: {COR_TEXTO_SEC} !important;
        margin-top: 4px;
    }}
    .val-pago {{ color: {COR_VERDE_TXT} !important; }}
    .val-atrasado {{ color: {COR_VERM_TXT} !important; }}

    /* Containers do Dashboard */
    .dash-box {{
        background: {COR_BG_CARD};
        border-radius: 12px;
        padding: 18px;
        border: 1px solid {COR_BORDA};
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 16px;
        color: {COR_TEXTO};
    }}
    .dash-box-title {{
        font-size: 14px;
        font-weight: 800;
        color: {COR_ROXO_TXT} !important;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 2px solid {COR_HR};
        display: flex;
        align-items: center;
        justify-content: space-between;
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }}

    /* Feed de Últimos Serviços */
    .service-feed-item {{
        background: {COR_BG_CARD_ALT};
        border: 1px solid {COR_BORDA};
        border-left: 4px solid #6A1B9A;
        border-radius: 8px;
        padding: 10px 12px;
        margin-bottom: 6px;
    }}
    .service-feed-item.open-os {{
        border-left-color: #D32F2F;
        background: {COR_OPEN_OS_BG};
    }}
    .service-feed-top {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 12px;
        font-weight: 800;
        color: {COR_ROXO_TXT};
        margin-bottom: 4px;
    }}
    .service-badge {{
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 10px;
        font-weight: 800;
        text-transform: uppercase;
    }}
    .badge-red {{ background: #D32F2F; color: #FFFFFF !important; }}
    .badge-purple {{ background: #6A1B9A; color: #FFFFFF !important; }}
    .badge-green {{ background: #2E7D32; color: #FFFFFF !important; }}

    /* Leitor de Vistoria e Assinatura */
    .inspection-reader-header {{
        background: linear-gradient(90deg, #6A1B9A 0%, #D32F2F 100%);
        color: white !important;
        padding: 10px 16px;
        border-radius: 8px 8px 0 0;
        font-weight: 800;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 12px;
    }}
    .inspection-reader-header * {{ color: white !important; }}
    .inspection-reader-body {{
        background: {COR_BG_CARD};
        border: 1px solid {COR_BORDA};
        border-top: none;
        border-radius: 0 0 8px 8px;
        padding: 14px;
        margin-bottom: 14px;
    }}
    div[data-testid="stImage"] img {{
        border-radius: 8px;
        border: 2px solid {COR_BORDA};
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }}

    {CSS_TEMA_CONTRASTE}
    </style>
""", unsafe_allow_html=True)

# ===================================================================================
# FUNÇÕES GLOBAIS, ORDENAÇÃO CRONOLÓGICA REAL E METADADOS (SLA, CUSTOS, PIX)
# ===================================================================================
def obter_hora_brasilia(): return datetime.now(timezone(timedelta(hours=-3)))
def obter_hora_str(): return obter_hora_brasilia().strftime("%Y-%m-%d %H:%M:%S")
def apenas_numeros_letras(texto): return "".join(caractere for caractere in str(texto) if caractere.isalnum()).strip().lower()

def obter_opcoes_km_plano(modo_fat):
    """Centraliza quais quilometragens cada plano libera no cadastro/edição (pronto para limitar Opção B no futuro)."""
    m = str(modo_fat).strip()
    if "Frota Pequena" in m:
        return ["50km", "100km"], f"Plano **{m}**. Opções liberadas: 50km e 100km."
    elif "Opção A" in m:
        return ["50km", "100km", "200km"], f"Plano **{m}**. Opções liberadas: 50km, 100km e 200km."
    elif "Opção B" in m:
        if OPCAO_B_PERMITIR_200KM:
            return ["50km", "100km", "200km"], f"Plano **{m}**. Opções liberadas: 50km, 100km e 200km."
        return ["50km", "100km"], f"Plano **{m}** (limitado a 50km e 100km)."
    elif "Escalonado" in m:
        return ["50km", "100km", "200km"], "Modo **Performance (Escalonado)**. Opções liberadas: 50km, 100km e 200km."
    return PLANOS_KM, ""

def formatar_moeda_float(valor):
    try:
        s = str(valor).strip().replace("R$", "").replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", ".")
        return float(s) if s else 0.0
    except:
        return 0.0

def formatar_brl(valor):
    v = formatar_moeda_float(valor)
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

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
    except Exception:
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

def ler_meta_os(row_ou_str):
    raw = row_ou_str.get('fotos_vistoria', '') if isinstance(row_ou_str, (dict, pd.Series)) else str(row_ou_str)
    s = str(raw).strip()
    if s and s.lower() != 'nan' and '{' in s:
        try:
            d = json.loads(s)
            if isinstance(d, dict):
                return d
        except: pass
    return {}

def mesclar_meta_os(meta_atual, novos_dados):
    d = ler_meta_os(meta_atual)
    d.update(novos_dados)
    return json.dumps(d)

def ler_pix_prestador(row_pre):
    raw = str(row_pre.get('frota', '')).strip()
    if raw and '{' in raw:
        try:
            d = json.loads(raw)
            if isinstance(d, dict):
                return str(d.get('chave_pix', '')).strip()
        except: pass
    return ""

def empacotar_pix_prestador(frota_atual, chave_pix):
    d = {}
    raw = str(frota_atual).strip()
    if raw and '{' in raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                d = parsed
        except: pass
    d['chave_pix'] = str(chave_pix).strip()
    return json.dumps(d)

def localizar_prestador_os(row_os, df_prest_base):
    if df_prest_base.empty:
        return None, ""

    tel_mot = apenas_numeros_letras(str(row_os.get('motorista_tel', '')).split('|')[0])
    prest_raw = str(row_os.get('prestador', ''))
    tel_prest = apenas_numeros_letras(prest_raw.split('Telefone/Zap:')[1]) if 'Telefone/Zap:' in prest_raw else ""
    nome_mot = str(row_os.get('motorista_nome', '')).strip().upper()
    nome_prest = prest_raw.split('|')[0].strip().upper()

    tels_busca = [t for t in [tel_mot, tel_prest] if len(t) >= 8]
    if tels_busca:
        for t in tels_busca:
            m_tel = df_prest_base[df_prest_base['telefone'].apply(apenas_numeros_letras) == t]
            if not m_tel.empty:
                r = m_tel.iloc[0]
                return str(r['id']), ler_pix_prestador(r)

    nomes_busca = [n for n in [nome_mot, nome_prest] if n and n not in ['NAN', 'GUINCHEIRO AVULSO', 'N/D']]
    for n in nomes_busca:
        m_nome = df_prest_base[df_prest_base['nome'].str.strip().str.upper() == n]
        if not m_nome.empty:
            r = m_nome.iloc[0]
            return str(r['id']), ler_pix_prestador(r)

    return None, ""

def eh_os_particular(row_os):
    meta = ler_meta_os(row_os)
    if str(meta.get('status_pgto_prestador', '')).strip() == 'Particular':
        return True
    if str(row_os.get('cliente_id', '')).strip().upper() == 'AVULSO':
        return True
    if str(row_os.get('plano_km', '')).strip().lower() == 'particular':
        return True
    emp_u = str(row_os.get('empresa', '')).strip().upper()
    if 'PARTICULAR' in emp_u or 'AVULSO' in emp_u:
        return True
    return False

def parse_dt_seguro(val_str):
    s = str(val_str).strip()
    if not s or s.lower() in ['nan', 'none', 'n/d']:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(s[:19], fmt)
        except: pass
    try:
        dt = pd.to_datetime(s, errors='coerce')
        if pd.notna(dt):
            return dt.to_pydatetime().replace(tzinfo=None)
    except: pass
    return None

def ordenar_os_recentes(df_base):
    """Ordena sempre da OS mais recente para a mais antiga (por data/hora real e ID numérico)."""
    if df_base is None or df_base.empty:
        return df_base
    df_ord = df_base.copy()
    df_ord['_dt_ord_tmp'] = df_ord['data_hora'].apply(lambda x: parse_dt_seguro(x) or datetime(1970, 1, 1)) if 'data_hora' in df_ord.columns else datetime(1970, 1, 1)
    df_ord['_id_num_tmp'] = pd.to_numeric(df_ord['id'], errors='coerce').fillna(0) if 'id' in df_ord.columns else 0
    df_ord = df_ord.sort_values(by=['_dt_ord_tmp', '_id_num_tmp'], ascending=[False, False]).drop(columns=['_dt_ord_tmp', '_id_num_tmp'])
    return df_ord

def extrair_horarios_sla(row_os):
    meta = ler_meta_os(row_os)
    dt_ab = parse_dt_seguro(row_os.get('data_hora', ''))
    aceite_str = meta.get('sla_aceite', '')
    if not aceite_str:
        mtel = str(row_os.get('motorista_tel', ''))
        if '|' in mtel:
            aceite_str = mtel.split('|')[1]
    dt_ac = parse_dt_seguro(aceite_str)
    dt_em = parse_dt_seguro(meta.get('sla_embarque', ''))
    dt_co = parse_dt_seguro(meta.get('sla_conclusao', ''))
    return dt_ab, dt_ac, dt_em, dt_co

def formatar_minutos_sla(minutos):
    if minutos is None or np.isnan(minutos):
        return "—"
    m = int(round(minutos))
    if m < 60:
        return f"{m} min"
    h, r = divmod(m, 60)
    return f"{h}h {r:02d}m"

def exportar_pdf_html_oficial(df_os, df_clientes, nome_arquivo):
    if df_os.empty: return "<p style='color: red;'>Erro: Nenhuma OS encontrada para gerar o relatório.</p>"
    r = df_os.iloc[0]
    meta = ler_meta_os(r)
    dt_ab, dt_ac, dt_em, dt_co = extrair_horarios_sla(r)
    fmt_sla = lambda d: d.strftime("%d/%m/%Y %H:%M:%S") if d else "—"

    sla_html = f"""
    <div style='background-color: #f3e5f5; padding: 12px 15px; border-radius: 8px; border-left: 5px solid #6A1B9A; margin-top: 16px;'>
        <h3 style='color: #6A1B9A; margin: 0 0 8px 0; font-size: 15px;'>Linha do Tempo (SLA Operacional)</h3>
        <p style='margin: 4px 0; font-size: 13px;'><strong>Abertura:</strong> {fmt_sla(dt_ab)} &nbsp;|&nbsp; <strong>Aceite do Prestador:</strong> {fmt_sla(dt_ac)}</p>
        <p style='margin: 4px 0; font-size: 13px;'><strong>Chegada / Embarque:</strong> {fmt_sla(dt_em)} &nbsp;|&nbsp; <strong>Desembarque / Conclusão:</strong> {fmt_sla(dt_co)}</p>
    </div>
    """

    fotos_html = ""
    doc_cliente = meta.get('doc_cliente', 'N/D')
    if any(meta.get(k) for k in ['frente', 'traseira', 'lat_dir', 'lat_esq']):
        fotos_html = "<h3 style='color: #6A1B9A; margin-top: 20px; border-bottom: 2px solid #D32F2F; padding-bottom: 5px;'>Vistoria Fotográfica de Embarque</h3><div style='display: flex; gap: 15px; flex-wrap: wrap; margin-top: 12px;'>"
        for k, label in [('frente', 'Frente'), ('traseira', 'Traseira'), ('lat_dir', 'Lateral Direita'), ('lat_esq', 'Lateral Esquerda')]:
            if meta.get(k):
                fotos_html += f"<div style='text-align:center; background:#f8fafc; padding:10px; border-radius:8px; border:1px solid #e2e8f0;'><p style='font-size:12px; font-weight:800; margin:0 0 6px 0; color:#6A1B9A; text-transform:uppercase;'>{label}</p><img src='data:image/jpeg;base64,{meta[k]}' style='max-height: 180px; border: 2px solid #6A1B9A; border-radius: 6px; box-shadow: 0 2px 6px rgba(0,0,0,0.1);' /></div>"
        fotos_html += "</div>"

    desembarque_html = ""
    if meta.get('foto_desembarque'):
        desembarque_html = f"""
        <div style='margin-top: 20px;'>
            <h3 style='color: #2E7D32; border-bottom: 2px solid #2E7D32; padding-bottom: 5px;'>Comprovante Fotográfico de Desembarque (Entrega no Destino)</h3>
            <div style='text-align: center; background: #f8fafc; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; margin-top: 10px;'>
                <img src='data:image/jpeg;base64,{meta['foto_desembarque']}' style='max-height: 220px; border: 2px solid #2E7D32; border-radius: 6px; box-shadow: 0 2px 6px rgba(0,0,0,0.1);' />
            </div>
        </div>
        """

    ass_html = ""
    ass_str = str(r.get('assinatura_cliente', ''))
    if ass_str and ass_str.lower() not in ['nan', 'none', '']:
        ass_html = f"""
        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 2px solid #6A1B9A; margin-top: 25px;'>
            <h3 style='color: #6A1B9A; margin-top: 0; border-bottom: 1px solid #ccc; padding-bottom: 5px;'>Termo de Responsabilidade e Assinatura</h3>
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
                h2 {{ color: #6A1B9A; border-bottom: 3px solid #D32F2F; padding-bottom: 8px; }}
                .info-box {{ background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 5px solid #6A1B9A; line-height: 1.6; }}
                .info-box p {{ margin: 6px 0; font-size: 14px; }}
                .destaque {{ font-weight: bold; color: #D32F2F; }}
            </style>
        </head>
        <body>
            <h2>Relatório Oficial de Ordem de Serviço - Central de Assistência 24 Horas</h2>
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
                <p><strong>Prestador Acionado / Guincheiro:</strong> {r.get('motorista_nome') or r['prestador']}</p>
            </div>
            {sla_html}
            {fotos_html}
            {desembarque_html}
            {ass_html}
            <br><br>
            <p style="font-size: 12px; color: #666; text-align: center; margin-top: 30px; border-top: 1px solid #ccc; padding-top: 10px;"><em>Documento gerado automaticamente pela Central de Assistência 24 Horas — AD Rastreamento Veicular.</em></p>
        </body>
    </html>
    """
    b64 = base64.b64encode(html.encode('utf-8')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{nome_arquivo}.html" target="_blank" style="display: inline-block; padding: 10px 20px; background-color: #D32F2F; color: white; text-align: center; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 13px;">Baixar Extrato da OS (PDF/HTML)</a>'

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
    except Exception: 
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
df_os = ordenar_os_recentes(carregar_dados(FILE_OS, col_os))
df_financeiro = carregar_dados(FILE_FINANCEIRO, col_fin)
df_logs = carregar_dados(FILE_LOGS, col_logs)
df_loc = carregar_dados(FILE_LOC, col_loc)
df_nps = carregar_dados(FILE_NPS, col_nps)
# ===================================================================================
# DASHBOARD DE INTELIGÊNCIA (VISUAL CORPORATIVO + ORDENAÇÃO REAL + SLA + 6 MESES + SINISTRALIDADE)
# ===================================================================================
def contar_veiculos_df(df_cli_base):
    total_v = 0
    for _, r_cli in df_cli_base.iterrows():
        placas_extraidas = []
        if pd.notna(r_cli.get('veiculos_lista')) and str(r_cli['veiculos_lista']).strip() not in ['', '[]', 'nan']:
            try:
                for v in json.loads(str(r_cli['veiculos_lista'])):
                    p = str(v.get('Placa', '')).strip().upper().replace("-", "").replace(" ", "")
                    if len(p) >= 6 and p not in ['NAN', 'N/D']:
                        placas_extraidas.append(p)
            except:
                pass
        if not placas_extraidas:
            p1 = str(r_cli.get('pla', '')).strip().upper().replace("-", "").replace(" ", "")
            if len(p1) >= 6 and p1 not in ['NAN', 'N/D']:
                placas_extraidas.append(p1)
            p2 = str(r_cli.get('pla_2', '')).strip().upper().replace("-", "").replace(" ", "")
            if len(p2) >= 6 and p2 not in ['NAN', 'N/D']:
                placas_extraidas.append(p2)
        total_v += len(placas_extraidas)
    return total_v

def gerar_laudo_atendimentos_html(empresa_filtro, periodo_label, total_veiculos, total_os, sla_aceite, sla_embarque, sla_total, servicos_df):
    data_atual = obter_hora_brasilia().strftime("%d/%m/%Y às %H:%M")
    linhas_tabela = ""
    for _, row in servicos_df.iterrows():
        linhas_tabela += f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">{row['Serviço']}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center;">{row['Quantidade']} chamado(s)</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right; color: #6A1B9A; font-weight: bold;">{row['Porcentagem']:.1f}%</td>
        </tr>
        """
        
    html = f"""
    <html>
        <head>
            <meta charset="utf-8">
            <title>Laudo Operacional - Central de Assistência 24 Horas</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; color: #333; max-width: 780px; margin: 0 auto; }}
                h2 {{ color: #6A1B9A; border-bottom: 2px solid #D32F2F; padding-bottom: 6px; margin-bottom: 4px; font-size: 20px; }}
                .sub {{ color: #666; font-size: 12px; margin-bottom: 18px; }}
                .kpi-container {{ display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }}
                .kpi-card {{ flex: 1; min-width: 150px; background: #f8f9fa; padding: 12px; border-radius: 6px; border-left: 4px solid #6A1B9A; }}
                .kpi-card.red {{ border-left-color: #D32F2F; }}
                .kpi-card h4 {{ margin: 0; font-size: 11px; color: #666; text-transform: uppercase; }}
                .kpi-card p {{ margin: 4px 0 0 0; font-size: 16px; font-weight: bold; color: #333; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }}
                th {{ background-color: #6A1B9A; color: white; padding: 8px; text-align: left; }}
            </style>
        </head>
        <body>
            <h2>AD RASTREAMENTO VEICULAR — LAUDO OPERACIONAL</h2>
            <div class="sub">Central de Assistência 24 Horas | Período: <b>{periodo_label}</b> | Gerado em: {data_atual}</div>
            
            <div class="kpi-container">
                <div class="kpi-card">
                    <h4>Empresa / Escopo</h4>
                    <p>{empresa_filtro.upper()}</p>
                </div>
                <div class="kpi-card">
                    <h4>Frota Ativa</h4>
                    <p>{total_veiculos} veículos</p>
                </div>
                <div class="kpi-card">
                    <h4>Ocorrências no Período</h4>
                    <p>{total_os} chamados</p>
                </div>
            </div>

            <div class="kpi-container">
                <div class="kpi-card red">
                    <h4>SLA Aceite</h4>
                    <p>{sla_aceite}</p>
                </div>
                <div class="kpi-card red">
                    <h4>SLA Embarque</h4>
                    <p>{sla_embarque}</p>
                </div>
                <div class="kpi-card red">
                    <h4>SLA Conclusão</h4>
                    <p>{sla_total}</p>
                </div>
            </div>

            <h3 style="color: #4a148c; font-size: 15px; margin-bottom: 8px;">Distribuição Percentual de Eventos</h3>
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
            <p style="font-size: 11px; color: #888; text-align: center; border-top: 1px solid #eee; padding-top: 8px;">
                <em>Este laudo técnico foi consolidado automaticamente pela Central de Assistência 24 Horas — AD Rastreamento Veicular.</em>
            </p>
        </body>
    </html>
    """
    b64 = base64.b64encode(html.encode('utf-8')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="Laudo_Atendimentos_{empresa_filtro}_{int(time.time())}.html" target="_blank" style="text-decoration: none;"><button style="background-color: #6A1B9A; color: white; padding: 10px 18px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; width: 100%; font-size: 13px;">Baixar Laudo Executivo (PDF/HTML)</button></a>'

def renderizar_dashboard(empresa_filtro="Todas", eh_admin=True):
    st.markdown(f'<div class="section-title">Painel de Inteligência — {empresa_filtro.upper()}</div>', unsafe_allow_html=True)

    cor_chart_txt = "#F8FAFC" if is_dark else "#0F172A"
    cor_grid = "#334155" if is_dark else "#CBD5E1"
    agora_br = obter_hora_brasilia().replace(tzinfo=None)

    if empresa_filtro != "Todas":
        df_os_escopo = ordenar_os_recentes(df_os[df_os['empresa'].str.upper() == empresa_filtro.upper()].copy())
        df_cli_dash = df_clientes[(df_clientes['emp_name'].str.upper() == empresa_filtro.upper()) & (df_clientes['status'].str.strip() == 'Ativo')].copy()
    else:
        df_os_escopo = ordenar_os_recentes(df_os.copy())
        df_cli_dash = df_clientes[df_clientes['status'].str.strip() == 'Ativo'].copy()

    df_os_escopo['dt_parsed'] = df_os_escopo['data_hora'].apply(parse_dt_seguro)

    # =========================================================================
    # 1. ALERTA CRÍTICO SLA EM TEMPO REAL (OS SEM PRESTADOR HÁ MAIS DE 15 MIN)
    # =========================================================================
    df_sem_aceite = df_os_escopo[
        df_os_escopo['status_os'].str.upper().isin(['PENDENTE', 'EM ATENDIMENTO'])
    ].copy()

    alertas_criticos = []
    for _, r_sa in df_sem_aceite.iterrows():
        dt_ab_sa = r_sa.get('dt_parsed')
        if dt_ab_sa is not None:
            mins_espera = (agora_br - dt_ab_sa).total_seconds() / 60.0
            if mins_espera >= 15:
                alertas_criticos.append({
                    'id': r_sa.get('id', ''),
                    'placa': r_sa.get('placa', 'N/D'),
                    'cliente': r_sa.get('cliente_nome', 'N/D'),
                    'empresa': r_sa.get('empresa', 'N/D'),
                    'servico': r_sa.get('tipo_servico', 'N/D'),
                    'espera': formatar_minutos_sla(mins_espera)
                })

    if alertas_criticos:
        itens_alerta_html = "".join([
            f"<div style='font-size:13px; margin-top:4px;'>- <b>OS #{a['id']}</b> | Placa: <b>{a['placa']}</b> ({a['servico']}) — {a['cliente']} [{a['empresa']}] — <b>Aguardando há {a['espera']}</b></div>"
            for a in alertas_criticos[:5]
        ])
        st.markdown(f"""
            <div class="sla-critical-banner">
                <div style="font-size: 14px; font-weight: 900; letter-spacing: 0.4px; text-transform: uppercase;">
                    ALERTA DE SLA CRÍTICO — {len(alertas_criticos)} CHAMADO(S) ACIMA DE 15 MIN SEM PRESTADOR
                </div>
                {itens_alerta_html}
            </div>
        """, unsafe_allow_html=True)

    # =========================================================================
    # 2. FILTRO DE PERÍODO DO DASHBOARD
    # =========================================================================
    c_per1, c_per2, c_per3 = st.columns([2, 1.3, 1.3])
    with c_per1:
        modo_periodo = st.selectbox(
            "Período de Análise:",
            ["Mês Atual", "Últimos 30 dias", "Todo o Histórico", "Personalizado"],
            key=f"dash_periodo_{empresa_filtro}"
        )

    dt_ini_filtro = None
    dt_fim_filtro = None
    if modo_periodo == "Mês Atual":
        dt_ini_filtro = agora_br.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dt_fim_filtro = agora_br.replace(hour=23, minute=59, second=59)
        periodo_label = f"Mês Atual ({agora_br.strftime('%m/%Y')})"
    elif modo_periodo == "Últimos 30 dias":
        dt_ini_filtro = (agora_br - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        dt_fim_filtro = agora_br.replace(hour=23, minute=59, second=59)
        periodo_label = f"Últimos 30 dias ({dt_ini_filtro.strftime('%d/%m')} a {agora_br.strftime('%d/%m/%Y')})"
    elif modo_periodo == "Personalizado":
        with c_per2:
            d_ini_in = st.date_input("Data Inicial:", value=(agora_br - timedelta(days=30)).date(), key=f"dash_dini_{empresa_filtro}")
        with c_per3:
            d_fim_in = st.date_input("Data Final:", value=agora_br.date(), key=f"dash_dfim_{empresa_filtro}")
        dt_ini_filtro = datetime.combine(d_ini_in, datetime.min.time())
        dt_fim_filtro = datetime.combine(d_fim_in, datetime.max.time())
        periodo_label = f"{d_ini_in.strftime('%d/%m/%Y')} a {d_fim_in.strftime('%d/%m/%Y')}"
    else:
        periodo_label = "Todo o Histórico"

    if dt_ini_filtro is not None and dt_fim_filtro is not None:
        df_os_dash = df_os_escopo[
            df_os_escopo['dt_parsed'].notna() &
            (df_os_escopo['dt_parsed'] >= dt_ini_filtro) &
            (df_os_escopo['dt_parsed'] <= dt_fim_filtro)
        ].copy()
    else:
        df_os_dash = df_os_escopo.copy()

    df_os_dash = ordenar_os_recentes(df_os_dash)

    total_veiculos = contar_veiculos_df(df_cli_dash)
    total_os = len(df_os_dash)
    os_em_andamento = len(df_os_escopo[~df_os_escopo['status_os'].str.upper().isin(['ENCERRADO', 'CANCELADO'])])
    os_concluidas = len(df_os_dash[df_os_dash['status_os'].str.upper() == 'ENCERRADO'])

    # LINHA 1: CONTADORES OPERACIONAIS
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Frota Ativa</div>
            <div class="metric-value" style="color: {COR_ROXO_DEST};">{total_veiculos}</div>
            <div class="metric-sub">Veículos mapeados</div>
        </div>
    """, unsafe_allow_html=True)
    c2.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Chamados</div>
            <div class="metric-value" style="color: {COR_ROXO_TXT};">{total_os}</div>
            <div class="metric-sub">{modo_periodo}</div>
        </div>
    """, unsafe_allow_html=True)
    c3.markdown(f"""
        <div class="metric-card red-accent">
            <div class="metric-title">Em Aberto</div>
            <div class="metric-value" style="color: {COR_VERM_TXT};">{os_em_andamento}</div>
            <div class="metric-sub">Em andamento agora</div>
        </div>
    """, unsafe_allow_html=True)
    c4.markdown(f"""
        <div class="metric-card green-accent">
            <div class="metric-title">Concluídos</div>
            <div class="metric-value" style="color: {COR_VERDE_TXT};">{os_concluidas}</div>
            <div class="metric-sub">No período selecionado</div>
        </div>
    """, unsafe_allow_html=True)

    # =========================================================================
    # 3. PAINEL DE SLA EM TEMPO REAL
    # =========================================================================
    tempos_aceite, tempos_embarque, tempos_total = [], [], []
    for _, r_sla in df_os_dash.iterrows():
        dt_ab, dt_ac, dt_em, dt_co = extrair_horarios_sla(r_sla)
        if dt_ab and dt_ac and dt_ac >= dt_ab:
            tempos_aceite.append((dt_ac - dt_ab).total_seconds() / 60.0)
        if dt_ac and dt_em and dt_em >= dt_ac:
            tempos_embarque.append((dt_em - dt_ac).total_seconds() / 60.0)
        elif dt_ab and dt_em and dt_em >= dt_ab:
            tempos_embarque.append((dt_em - dt_ab).total_seconds() / 60.0)
        if dt_ab and dt_co and dt_co >= dt_ab:
            tempos_total.append((dt_co - dt_ab).total_seconds() / 60.0)

    media_aceite_str = formatar_minutos_sla(np.mean(tempos_aceite)) if tempos_aceite else "—"
    media_embarque_str = formatar_minutos_sla(np.mean(tempos_embarque)) if tempos_embarque else "—"
    media_total_str = formatar_minutos_sla(np.mean(tempos_total)) if tempos_total else "—"

    s1, s2, s3, s4 = st.columns(4)
    s1.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">SLA Aceite</div>
            <div class="metric-value" style="font-size:22px; color:{COR_ROXO_DEST};">{media_aceite_str}</div>
            <div class="metric-sub">Abertura ao aceite</div>
        </div>
    """, unsafe_allow_html=True)
    s2.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">SLA Embarque</div>
            <div class="metric-value" style="font-size:22px; color:{COR_ROXO_TXT};">{media_embarque_str}</div>
            <div class="metric-sub">Aceite ao embarque</div>
        </div>
    """, unsafe_allow_html=True)
    s3.markdown(f"""
        <div class="metric-card green-accent">
            <div class="metric-title">SLA Conclusão</div>
            <div class="metric-value" style="font-size:22px; color:{COR_VERDE_TXT};">{media_total_str}</div>
            <div class="metric-sub">Tempo total médio</div>
        </div>
    """, unsafe_allow_html=True)
    s4.markdown(f"""
        <div class="metric-card red-accent">
            <div class="metric-title">Sem Prestador</div>
            <div class="metric-value" style="font-size:22px; color:{COR_VERM_TXT};">{len(df_sem_aceite)}</div>
            <div class="metric-sub">{len(alertas_criticos)} acima de 15 min</div>
        </div>
    """, unsafe_allow_html=True)

    # =========================================================================
    # 4. GRÁFICOS DE DISTRIBUIÇÃO + ÚLTIMOS 5 REGISTROS (ORDEM CRONOLÓGICA REAL)
    # =========================================================================
    if total_os > 0:
        chave_sel_os = f"dash_os_detalhe_{empresa_filtro}"
        if chave_sel_os not in st.session_state:
            st.session_state[chave_sel_os] = None

        col_main_charts, col_side_feed = st.columns([2.2, 1.1])

        with col_main_charts:
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.markdown('<div class="dash-box">', unsafe_allow_html=True)
                st.markdown(f'<div class="dash-box-title"><span>Incidência por Serviço</span><span style="font-size:10.5px; color:{COR_ROXO_DEST};">PERÍODO</span></div>', unsafe_allow_html=True)
                
                servicos_counts = df_os_dash['tipo_servico'].value_counts().reset_index()
                servicos_counts.columns = ['Serviço', 'Quantidade']
                servicos_counts['Porcentagem'] = (servicos_counts['Quantidade'] / total_os) * 100

                fig_incidencia = px.pie(
                    servicos_counts, 
                    names='Serviço', 
                    values='Quantidade', 
                    hole=0.6,
                    color_discrete_sequence=['#6A1B9A', '#D32F2F', '#9C27B0', '#EF5350', '#4A148C', '#AB47BC']
                )
                fig_incidencia.update_traces(textposition='inside', textinfo='percent')
                fig_incidencia.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=cor_chart_txt),
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=230,
                    legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center", font=dict(color=cor_chart_txt))
                )
                st.plotly_chart(fig_incidencia, use_container_width=True)

                st.markdown(f"<hr style='margin: 8px 0; border-color: {COR_HR};'>", unsafe_allow_html=True)
                for _, r in servicos_counts.iterrows():
                    col_s_nome, col_s_qtd = st.columns([3, 2])
                    col_s_nome.write(f"**{r['Serviço']}**")
                    col_s_qtd.markdown(f"<div style='text-align: right;'><b>{r['Quantidade']}</b> <span style='color: {COR_ROXO_DEST}; font-size: 12px; font-weight:700;'>({r['Porcentagem']:.1f}%)</span></div>", unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

            with col_chart2:
                st.markdown('<div class="dash-box">', unsafe_allow_html=True)
                st.markdown(f'<div class="dash-box-title"><span>Status dos Chamados</span><span style="font-size:10.5px; color:{COR_VERM_TXT};">PERÍODO</span></div>', unsafe_allow_html=True)
                
                status_counts = df_os_dash['status_os'].value_counts().reset_index()
                status_counts.columns = ['Status', 'Quantidade']
                status_counts['Porcentagem'] = (status_counts['Quantidade'] / total_os) * 100

                fig_status = px.pie(
                    status_counts, 
                    names='Status', 
                    values='Quantidade', 
                    hole=0.6,
                    color_discrete_sequence=['#6A1B9A', '#D32F2F', '#2E7D32', '#FF9800']
                )
                fig_status.update_traces(textposition='inside', textinfo='percent')
                fig_status.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=cor_chart_txt),
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=230,
                    legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center", font=dict(color=cor_chart_txt))
                )
                st.plotly_chart(fig_status, use_container_width=True)

                st.markdown(f"<hr style='margin: 8px 0; border-color: {COR_HR};'>", unsafe_allow_html=True)
                for _, r in status_counts.iterrows():
                    col_st_nome, col_st_qtd = st.columns([3, 2])
                    col_st_nome.write(f"**{r['Status']}**")
                    col_st_qtd.markdown(f"<div style='text-align: right;'><b>{r['Quantidade']}</b> <span style='color: {COR_VERM_TXT}; font-size: 12px; font-weight:700;'>({r['Porcentagem']:.1f}%)</span></div>", unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

        with col_side_feed:
            st.markdown('<div class="dash-box">', unsafe_allow_html=True)
            st.markdown(f'<div class="dash-box-title"><span>Últimos 5 Registros</span><span style="font-size:10.5px; color:{COR_ROXO_DEST};">MAIS RECENTES</span></div>', unsafe_allow_html=True)
            df_ultimos = df_os_dash.head(5)
            for idx_u, r_ult in df_ultimos.iterrows():
                os_id_u = str(r_ult.get('id', '')).strip()
                st_os_val = str(r_ult.get('status_os', '')).upper()
                is_open = st_os_val not in ['ENCERRADO', 'CANCELADO']
                item_cls = "service-feed-item open-os" if is_open else "service-feed-item"
                badge_cls = "badge-red" if is_open else "badge-purple"
                st.markdown(f"""
                    <div class="{item_cls}">
                        <div class="service-feed-top">
                            <span>OS #{os_id_u} | {r_ult.get('placa','N/D')}</span>
                            <span class="service-badge {badge_cls}">{st_os_val}</span>
                        </div>
                        <div style="font-size:12.5px; font-weight:700; color:{COR_TEXTO};">{r_ult.get('tipo_servico','')} — {str(r_ult.get('cliente_nome',''))[:26]}</div>
                        <div style="font-size:11px; color:{COR_TEXTO_SEC}; margin-top:2px;">{str(r_ult.get('data_hora',''))[:16]} | {str(r_ult.get('empresa',''))[:22]}</div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"Abrir OS #{os_id_u}", key=f"btn_dash_reg_{empresa_filtro}_{os_id_u}_{idx_u}", use_container_width=True):
                    st.session_state[chave_sel_os] = os_id_u
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # FICHA COMPLETA AO CLICAR EM UM DOS 5 ÚLTIMOS REGISTROS
        os_det_id = st.session_state.get(chave_sel_os)
        if os_det_id:
            df_os_det = df_os_escopo[df_os_escopo['id'].astype(str) == str(os_det_id)]
            if not df_os_det.empty:
                r_det = df_os_det.iloc[0]
                meta_det = ler_meta_os(r_det)
                dt_ab_d, dt_ac_d, dt_em_d, dt_co_d = extrair_horarios_sla(r_det)
                fmt_d = lambda d: d.strftime("%d/%m/%Y %H:%M") if d else "—"
                obs_det = str(r_det.get('obs', '')).strip()
                if not obs_det or obs_det.lower() == 'nan':
                    obs_det = "Nenhuma"
                mot_nome_det = str(r_det.get('motorista_nome', '')).strip()
                mot_tel_det = str(r_det.get('motorista_tel', '')).split("|")[0].strip()
                mot_txt_det = "Ainda não assumido pelo portal" if (not mot_nome_det or mot_nome_det.lower() == 'nan') else (f"{mot_nome_det} ({mot_tel_det})" if mot_tel_det else mot_nome_det)

                st.markdown(f"""
                    <div class="dash-box" style="border: 2px solid #6A1B9A; border-left: 6px solid #D32F2F;">
                        <div class="dash-box-title">
                            <span>Detalhes do Atendimento — OS #{r_det.get('id','')}</span>
                            <span class="service-badge badge-purple">{str(r_det.get('status_os','')).upper()}</span>
                        </div>
                        <p style="margin: 6px 0; font-size: 13.5px;"><strong>Abertura:</strong> {fmt_d(dt_ab_d)} &nbsp;|&nbsp; <strong>Aceite:</strong> {fmt_d(dt_ac_d)} &nbsp;|&nbsp; <strong>Embarque:</strong> {fmt_d(dt_em_d)} &nbsp;|&nbsp; <strong>Conclusão:</strong> {fmt_d(dt_co_d)}</p>
                        <p style="margin: 6px 0; font-size: 13.5px;"><strong>Empresa:</strong> {r_det.get('empresa','N/D')} &nbsp;|&nbsp; <strong>Plano KM:</strong> {r_det.get('plano_km','N/D')} &nbsp;|&nbsp; <strong>Cliente:</strong> {r_det.get('cliente_nome','N/D')} ({r_det.get('cliente_tel','N/D')})</p>
                        <p style="margin: 6px 0; font-size: 13.5px;"><strong>Veículo:</strong> {r_det.get('veiculo_desc','N/D')} &nbsp;|&nbsp; <strong>Placa:</strong> <span style="color:{COR_VERM_TXT}; font-weight:800;">{r_det.get('placa','N/D')}</span></p>
                        <p style="margin: 6px 0; font-size: 13.5px;"><strong>Serviço:</strong> {r_det.get('tipo_servico','N/D')} ({r_det.get('motivo','N/D')}) &nbsp;|&nbsp; <strong>Valor Cobrado:</strong> R$ {r_det.get('valor_cobrado','0,00')}</p>
                        <p style="margin: 6px 0; font-size: 13.5px;"><strong>Origem:</strong> {r_det.get('localizacao','N/D')}</p>
                        <p style="margin: 6px 0; font-size: 13.5px;"><strong>Destino:</strong> {r_det.get('destino','N/D')}</p>
                        <p style="margin: 6px 0; font-size: 13.5px;"><strong>Base Acionada:</strong> {r_det.get('prestador','N/D')} &nbsp;|&nbsp; <strong>Guincheiro:</strong> {mot_txt_det}</p>
                        <p style="margin: 6px 0; font-size: 13px; color:{COR_TEXTO_SEC};"><strong>Observações:</strong> {obs_det}</p>
                    </div>
                """, unsafe_allow_html=True)

                doc_det = meta_det.get('doc_cliente', 'N/D')
                if any(meta_det.get(k) for k in ['frente', 'traseira', 'lat_dir', 'lat_esq']):
                    st.markdown('<div class="inspection-reader-header"><span>Fotos da Vistoria (Embarque)</span><span>4 ÂNGULOS</span></div>', unsafe_allow_html=True)
                    st.markdown('<div class="inspection-reader-body">', unsafe_allow_html=True)
                    cd1, cd2, cd3, cd4 = st.columns(4)
                    if meta_det.get('frente'): cd1.image(base64.b64decode(meta_det['frente']), caption="1. Frente", use_container_width=True)
                    if meta_det.get('traseira'): cd2.image(base64.b64decode(meta_det['traseira']), caption="2. Traseira", use_container_width=True)
                    if meta_det.get('lat_dir'): cd3.image(base64.b64decode(meta_det['lat_dir']), caption="3. Lat. Direita", use_container_width=True)
                    if meta_det.get('lat_esq'): cd4.image(base64.b64decode(meta_det['lat_esq']), caption="4. Lat. Esquerda", use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                if meta_det.get('foto_desembarque'):
                    st.markdown('<div class="inspection-reader-header"><span>Foto de Desembarque (Entrega no Destino)</span><span>CONFERÊNCIA</span></div>', unsafe_allow_html=True)
                    st.markdown('<div class="inspection-reader-body">', unsafe_allow_html=True)
                    try: st.image(base64.b64decode(meta_det['foto_desembarque']), caption="Veículo entregue no destino", width=360)
                    except: pass
                    st.markdown('</div>', unsafe_allow_html=True)

                ass_det_str = str(r_det.get('assinatura_cliente', ''))
                if ass_det_str and ass_det_str.lower() not in ['nan', 'none', '']:
                    st.markdown(f'<div class="inspection-reader-header"><span>Assinatura Digital do Condutor</span><span>DOC: {doc_det}</span></div>', unsafe_allow_html=True)
                    st.markdown('<div class="inspection-reader-body">', unsafe_allow_html=True)
                    try: st.image(base64.b64decode(ass_det_str), width=240)
                    except: pass
                    st.markdown('</div>', unsafe_allow_html=True)

                c_det_b1, c_det_b2 = st.columns(2)
                with c_det_b1:
                    st.markdown(exportar_pdf_html_oficial(df_os_det, df_clientes, f"relatorio_os_{os_det_id}"), unsafe_allow_html=True)
                with c_det_b2:
                    if st.button("Fechar Detalhes", key=f"btn_fechar_det_{empresa_filtro}", use_container_width=True):
                        st.session_state[chave_sel_os] = None
                        st.rerun()
    else:
        servicos_counts = pd.DataFrame(columns=['Serviço', 'Quantidade', 'Porcentagem'])
        st.info(f"Nenhuma ordem de serviço registrada no período selecionado ({periodo_label}).")

    # =========================================================================
    # 5. EVOLUÇÃO DOS ÚLTIMOS 6 MESES + RANKING DE SINISTRALIDADE POR PARCEIRO
    # =========================================================================
    meses_6 = []
    for i in range(5, -1, -1):
        m_calc = agora_br.month - i
        y_calc = agora_br.year
        while m_calc <= 0:
            m_calc += 12
            y_calc -= 1
        meses_6.append((y_calc, m_calc, f"{m_calc:02d}/{y_calc}"))

    evolucao_rows = []
    df_valid_dt = df_os_escopo[df_os_escopo['dt_parsed'].notna()].copy()
    for y_c, m_c, lbl_c in meses_6:
        qtd_m = len(df_valid_dt[(df_valid_dt['dt_parsed'].dt.year == y_c) & (df_valid_dt['dt_parsed'].dt.month == m_c)])
        evolucao_rows.append({'Mês': lbl_c, 'Chamados': qtd_m})
    df_evolucao = pd.DataFrame(evolucao_rows)

    mostrar_ranking = (eh_admin and empresa_filtro == "Todas")
    if mostrar_ranking:
        col_ev, col_rk = st.columns([1.2, 1.1])
    else:
        col_ev = st.container()
        col_rk = None

    with col_ev:
        st.markdown('<div class="dash-box">', unsafe_allow_html=True)
        st.markdown(f'<div class="dash-box-title"><span>Evolução de Chamados (6 Meses)</span><span style="font-size:10.5px; color:{COR_ROXO_DEST};">TENDÊNCIA</span></div>', unsafe_allow_html=True)
        fig_ev = go.Figure()
        fig_ev.add_trace(go.Bar(
            x=df_evolucao['Mês'], y=df_evolucao['Chamados'],
            name='Chamados', marker_color='#6A1B9A',
            text=df_evolucao['Chamados'], textposition='outside'
        ))
        fig_ev.add_trace(go.Scatter(
            x=df_evolucao['Mês'], y=df_evolucao['Chamados'],
            mode='lines+markers', name='Tendência',
            line=dict(color='#D32F2F', width=3), marker=dict(size=7)
        ))
        fig_ev.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color=cor_chart_txt),
            height=280,
            margin=dict(t=24, b=16, l=16, r=16),
            showlegend=False,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor=cor_grid, rangemode="tozero")
        )
        st.plotly_chart(fig_ev, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if mostrar_ranking and col_rk is not None:
        with col_rk:
            st.markdown('<div class="dash-box">', unsafe_allow_html=True)
            st.markdown(f'<div class="dash-box-title"><span>Ranking de Sinistralidade</span><span style="font-size:10.5px; color:{COR_VERM_TXT};">% SOBRE FROTA</span></div>', unsafe_allow_html=True)
            ranking_rows = []
            emps_ativas_rk = df_empresas[df_empresas['status'].str.upper() == 'ATIVO']
            for _, r_e in emps_ativas_rk.iterrows():
                nome_e = str(r_e['nome']).strip().upper()
                if not nome_e:
                    continue
                cli_e = df_clientes[(df_clientes['emp_name'].str.upper() == nome_e) & (df_clientes['status'].str.strip() == 'Ativo')]
                frota_e = contar_veiculos_df(cli_e)
                chamados_e = len(df_os_dash[(df_os_dash['empresa'].str.upper() == nome_e) & (~df_os_dash['status_os'].str.upper().isin(['CANCELADO']))])
                taxa_e = (chamados_e / frota_e * 100.0) if frota_e > 0 else 0.0
                if frota_e > 0 or chamados_e > 0:
                    ranking_rows.append({
                        'Empresa': nome_e,
                        'Frota Ativa': frota_e,
                        'Chamados': chamados_e,
                        'Sinistralidade (%)': round(taxa_e, 1)
                    })

            if ranking_rows:
                df_rk = pd.DataFrame(ranking_rows).sort_values(by=['Sinistralidade (%)', 'Chamados'], ascending=[False, False]).head(8)
                df_rk_plot = df_rk.sort_values(by='Sinistralidade (%)', ascending=True)
                fig_rk = px.bar(
                    df_rk_plot,
                    x='Sinistralidade (%)',
                    y='Empresa',
                    orientation='h',
                    text='Sinistralidade (%)',
                    color='Sinistralidade (%)',
                    color_continuous_scale=['#6A1B9A', '#D32F2F']
                )
                fig_rk.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_rk.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=cor_chart_txt),
                    height=280,
                    margin=dict(t=10, b=16, l=10, r=36),
                    coloraxis_showscale=False,
                    xaxis=dict(showgrid=True, gridcolor=cor_grid, title="Taxa (%)"),
                    yaxis=dict(showgrid=False, title="")
                )
                st.plotly_chart(fig_rk, use_container_width=True)
            else:
                st.info("Cadastre empresas e frotas ativas para gerar o ranking de sinistralidade.")
            st.markdown('</div>', unsafe_allow_html=True)

    # =========================================================================
    # 6. LAUDO EXECUTIVO DO PERÍODO
    # =========================================================================
    if total_os > 0:
        st.write("---")
        if "exibir_laudo" not in st.session_state:
            st.session_state.exibir_laudo = False

        if not st.session_state.exibir_laudo:
            if st.button("Processar Laudo Executivo do Período", use_container_width=True, key=f"btn_proc_laudo_{empresa_filtro}"):
                st.session_state.exibir_laudo = True
                st.rerun()
        else:
            st.markdown(f"""
            <div class="dash-box" style="border: 2px solid #6A1B9A; border-left: 6px solid #D32F2F; margin-bottom: 16px;">
                <h3 style="color: {COR_ROXO_TXT}; margin-top:0; font-size: 17px;">Laudo Executivo — Central de Assistência 24 Horas</h3>
                <p style="color: {COR_TEXTO_SEC}; font-size: 13px; margin-bottom: 0;">Análise consolidada de ocorrências e SLA no período: <b>{periodo_label}</b>.</p>
            </div>
            """, unsafe_allow_html=True)
            
            data_atual_proc = obter_hora_brasilia().strftime("%d/%m/%Y às %H:%M")
            st.caption(f"Processado em: {data_atual_proc}")
            
            col_l1, col_l2, col_l3 = st.columns(3)
            col_l1.metric("Empresa / Unidade", empresa_filtro.upper())
            col_l2.metric("Frota Ativa", f"{total_veiculos} veículos")
            col_l3.metric("Ocorrências", f"{total_os} chamados")
            
            st.markdown("##### Distribuição Analítica por Tipo de Serviço")
            df_laudo_vis = servicos_counts.copy()
            df_laudo_vis['Porcentagem (%)'] = df_laudo_vis['Porcentagem'].apply(lambda x: f"{x:.1f}%")
            df_laudo_vis = df_laudo_vis.rename(columns={'Serviço': 'Tipo de Ocorrência', 'Quantidade': 'Acionamentos'})
            st.dataframe(df_laudo_vis[['Tipo de Ocorrência', 'Acionamentos', 'Porcentagem (%)']], use_container_width=True)
            
            st.write("")
            col_laudo_btn1, col_laudo_btn2 = st.columns(2)
            with col_laudo_btn1:
                st.markdown(gerar_laudo_atendimentos_html(empresa_filtro, periodo_label, total_veiculos, total_os, media_aceite_str, media_embarque_str, media_total_str, servicos_counts), unsafe_allow_html=True)
            with col_laudo_btn2:
                if st.button("Fechar Laudo Executivo", use_container_width=True, key=f"btn_close_laudo_{empresa_filtro}"):
                    st.session_state.exibir_laudo = False
                    st.rerun()

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

def classificar_faixa_km(plano_str):
    """Identifica com precisão se o plano do veículo/OS é 50km, 100km ou 200km+ (nunca confunde 200km com 50km)."""
    s = str(plano_str).strip().lower()
    if "sem limite" in s or "200" in s or "300" in s or "400" in s or "500" in s:
        return "200km"
    elif "100" in s or "150" in s:
        return "100km"
    elif "50" in s:
        return "50km"
    return "50km"

# ===================================================================================
# FUNÇÕES DE CÁLCULO E REGRAS DE NEGÓCIO (FINANCEIRO 360º + PARTICULAR + 200KM OFICIAL)
# ===================================================================================
def colorir_status(val):
    if is_dark:
        return 'color: #86EFAC; font-weight: bold;' if str(val).strip() == 'Ativo' else 'color: #FCA5A5; font-weight: bold;'
    return 'color: #2e7d32; font-weight: bold;' if str(val).strip() == 'Ativo' else 'color: #c62828; font-weight: bold;'

def formatar_status_financeiro(val):
    s = str(val).strip()
    if s in ['Pago', 'Lucro']: return 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold;'
    elif s in ['Atrasado', 'Prejuízo']: return 'background-color: #ffebee; color: #c62828; font-weight: bold;'
    elif s == 'Particular': return 'background-color: #f3e5f5; color: #6a1b9a; font-weight: bold;'
    else: return 'background-color: #fff8e1; color: #f57f17; font-weight: bold;'

def obter_meses_referencia():
    hoje = obter_hora_brasilia()
    mes_atual = f"{hoje.month:02d}/{hoje.year}"
    m_ant = hoje.month - 1
    y_ant = hoje.year
    if m_ant <= 0:
        m_ant = 12
        y_ant -= 1
    mes_anterior = f"{m_ant:02d}/{y_ant}"
    return mes_atual, mes_anterior

def normalizar_mes_ano(texto):
    if not texto:
        return None
    limpo = str(texto).strip().replace("-", "/").replace(".", "/")
    m = re.match(r'^(\d{1,2})/(\d{4})$', limpo)
    if not m:
        return None
    mes_num = int(m.group(1))
    ano_num = int(m.group(2))
    if 1 <= mes_num <= 12 and 2020 <= ano_num <= 2100:
        return f"{mes_num:02d}/{ano_num}"
    return None

def mes_ano_para_tupla(mes_ano_str):
    try:
        m, y = str(mes_ano_str).strip().split("/")
        return (int(y), int(m))
    except:
        hoje = obter_hora_brasilia()
        return (hoje.year, hoje.month)

def get_ultimos_3_meses():
    hoje = obter_hora_brasilia()
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

def extrair_custos_os_df(df_os_base, df_prest_base, mes_filtro=None):
    """Monta base unificada de Custos por OS, Contas a Pagar e Particulares (ordenados das OS mais recentes)."""
    df_os_ord = ordenar_os_recentes(df_os_base)
    linhas = []
    m_alvo, y_alvo = None, None
    if mes_filtro and '/' in str(mes_filtro):
        try:
            ms, ys = str(mes_filtro).split('/')
            m_alvo, y_alvo = int(ms), int(ys)
        except:
            pass

    for _, r in df_os_ord.iterrows():
        if str(r.get('status_os', '')).upper() == 'CANCELADO':
            continue
        dt_r = parse_dt_seguro(r.get('data_hora', ''))
        if m_alvo and y_alvo:
            if not dt_r or dt_r.month != m_alvo or dt_r.year != y_alvo:
                continue

        meta = ler_meta_os(r)
        is_part = eh_os_particular(r)
        c_saida = formatar_moeda_float(meta.get('custo_saida', 0.0))
        c_km = formatar_moeda_float(meta.get('custo_km_exc', 0.0))
        c_pedagio = formatar_moeda_float(meta.get('custo_pedagio', 0.0))
        c_total = round(c_saida + c_km + c_pedagio, 2)

        st_pg_salvo = str(meta.get('status_pgto_prestador', '')).strip()
        if st_pg_salvo in ['A Pagar', 'Pago', 'Particular']:
            st_pg = st_pg_salvo
        else:
            st_pg = 'Particular' if is_part else 'A Pagar'

        prest_nome = str(r.get('motorista_nome', '')).strip().upper()
        if not prest_nome or prest_nome == 'NAN':
            prest_nome = str(r.get('prestador', '')).split('|')[0].strip().upper()

        prest_id_cad, pix_cadastrado = localizar_prestador_os(r, df_prest_base)
        pix_os = str(meta.get('pix_prestador_os', '')).strip()
        chave_pix_final = pix_cadastrado or pix_os or 'Não cadastrada'

        val_cobrado_os = formatar_moeda_float(r.get('valor_cobrado', 0.0))
        val_part_pago = formatar_moeda_float(meta.get('valor_particular_pago', 0.0))
        st_part_rec = str(meta.get('status_pgto_particular', '')).strip()
        if st_part_rec not in ['Pendente', 'Pago']:
            st_part_rec = 'Pago' if (val_cobrado_os > 0 and val_part_pago >= val_cobrado_os) else 'Pendente'

        linhas.append({
            'id_os': str(r.get('id', '')),
            'data_hora': str(r.get('data_hora', ''))[:16],
            'empresa': str(r.get('empresa', '')).upper(),
            'cliente_nome': str(r.get('cliente_nome', '')).upper(),
            'cliente_tel': str(r.get('cliente_tel', '')),
            'placa': str(r.get('placa', '')).upper(),
            'servico': str(r.get('tipo_servico', '')),
            'status_os': str(r.get('status_os', '')).upper(),
            'prestador': prest_nome or 'N/D',
            'prestador_id': prest_id_cad or '',
            'pix_cadastrado': pix_cadastrado,
            'chave_pix': chave_pix_final,
            'custo_saida': c_saida,
            'custo_km_exc': c_km,
            'custo_pedagio': c_pedagio,
            'custo_total': c_total,
            'status_pgto': st_pg,
            'data_pgto_prest': str(meta.get('data_pgto_prestador', '')),
            'obs_custo': str(meta.get('obs_custo', '')),
            'eh_particular': is_part,
            'valor_particular_cobrado': val_cobrado_os,
            'valor_particular_pago': val_part_pago,
            'status_particular': st_part_rec,
            'obs_particular': str(meta.get('obs_particular', ''))
        })

    return pd.DataFrame(linhas)

def calcular_fatura_parceiro(nome_empresa, mes, ano, df_clientes_atuais, df_os_atuais, df_empresas_atuais):
    lista_veiculos_emp = []
    df_cli_fat = df_clientes_atuais[(df_clientes_atuais['emp_name'].str.upper() == nome_empresa.upper()) & (df_clientes_atuais['status'].str.strip() == 'Ativo')]
    
    for _, r_cli in df_cli_fat.iterrows():
        p_km_cli = str(r_cli.get('plano_km', '50km')).strip()
        plano_limpo = classificar_faixa_km(p_km_cli)
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
    
    if status_emp == 'Inativo':
        return {
            'fatura_total': 0.0, 'total_v': 0, 'total_os': 0,
            'taxa': 0.0, 'faixa': 'Inativo', 'veiculos': [],
            'valor_base': 0.0, 'soma_adicionais': 0.0, 'soma_excedentes': 0.0,
            'dt_inicio': dt_inicio, 'dt_fim': dt_fim, 'vencimento_dia': dia_venc_str,
            'modo_fat': 'Inativo', 'qtd_exc_50': 0, 'qtd_exc_100': 0, 'qtd_exc_200': 0,
            'total_ac': 0, 'acionamentos_isentos': 0
        }

    df_os_temp = df_os_atuais.copy()
    df_os_temp['data_hora'] = pd.to_datetime(df_os_temp['data_hora'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    
    os_filtro_guinchos = df_os_temp[(df_os_temp['empresa'].str.upper() == nome_empresa.upper()) & 
                                    (df_os_temp['status_os'].str.upper() == 'ENCERRADO') & 
                                    (df_os_temp['tipo_servico'].str.upper().str.contains('GUINCHO')) & 
                                    (df_os_temp['data_hora'] >= dt_inicio) & 
                                    (df_os_temp['data_hora'] <= dt_fim) &
                                    (df_os_temp['valor_cobrado'].isin(['0,00', '0.00', '0', '']))].sort_values(by='data_hora', ascending=True)
                            
    total_guinchos = len(os_filtro_guinchos)
    fatura_total, soma_adicionais, soma_excedentes, valor_base = 0.0, 0.0, 0.0, 0.0
    qtd_exc_50, qtd_exc_100, qtd_exc_200, taxa, faixa = 0, 0, 0, 0.0, "N/A"
    total_ac, acionamentos_isentos = total_guinchos, 0
    
    if "Frota Pequena" in modo_fat_calc or "Até 40" in modo_fat_calc:
        if "Frota Pequena" in modo_fat_calc:
            valor_base, acionamentos_isentos, taxa_50, taxa_100, taxa_200 = 300.00, 2, 50.00, 85.00, 150.00
        elif "Opção A" in modo_fat_calc:
            valor_base, acionamentos_isentos, taxa_50, taxa_100, taxa_200 = 500.00, 2, 85.00, 100.00, 150.00
        elif "Opção B" in modo_fat_calc:
            valor_base, acionamentos_isentos, taxa_50, taxa_100, taxa_200 = 650.00, 4, 150.00, 190.00, 270.00

        precos_placa_fixo = {"50km": 6.90, "100km": 8.90, "200km": 11.20}
        for v in lista_veiculos_emp:
            faixa_v = classificar_faixa_km(v['plano'])
            custo_placa = precos_placa_fixo.get(faixa_v, 6.90)
            soma_adicionais += custo_placa
            v['tipo_cobranca'] = f'Mensalidade {faixa_v} (R$ {custo_placa:.2f})'
            v['valor_cobrado'] = custo_placa

        if total_guinchos > acionamentos_isentos:
            guinchos_excedentes = os_filtro_guinchos.iloc[acionamentos_isentos:]
            for _, g in guinchos_excedentes.iterrows():
                faixa_g = classificar_faixa_km(g.get('plano_km', '50km'))
                if faixa_g == "200km":
                    soma_excedentes += taxa_200
                    qtd_exc_200 += 1
                elif faixa_g == "100km":
                    soma_excedentes += taxa_100
                    qtd_exc_100 += 1
                else:
                    soma_excedentes += taxa_50
                    qtd_exc_50 += 1

        fatura_total = valor_base + soma_adicionais + soma_excedentes
        faixa = f"Pacote Fixo + Placas ({modo_fat_calc})"
        
    elif modo_fat_calc == "Performance (Escalonado)":
        base_calc = max(30, total_v)
        taxa = (total_guinchos / base_calc * 100) if base_calc > 0 else 0.0
        faixa, precos_faixa = obter_faixa_escalonado(taxa)

        for v in lista_veiculos_emp:
            faixa_v = classificar_faixa_km(v['plano'])
            custo_placa = precos_faixa.get(faixa_v, precos_faixa['50km'])
            soma_adicionais += custo_placa
            v['tipo_cobranca'] = f'Tabela {faixa_v} ({faixa})'
            v['valor_cobrado'] = custo_placa

        if soma_adicionais < 400.00:
            soma_excedentes = 400.00 - soma_adicionais
            fatura_total = 400.00
        else:
            fatura_total = soma_adicionais
            
    else:
        for v in lista_veiculos_emp:
            v['tipo_cobranca'] = 'Tradicional / Manual'
            v['valor_cobrado'] = 0.0
            
    return {
        'fatura_total': fatura_total, 'total_v': total_v, 'total_os': total_guinchos,
        'taxa': taxa, 'faixa': faixa, 'veiculos': lista_veiculos_emp,
        'valor_base': valor_base, 'soma_adicionais': soma_adicionais, 'soma_excedentes': soma_excedentes,
        'dt_inicio': dt_inicio, 'dt_fim': dt_fim, 'vencimento_dia': dia_venc_str,
        'modo_fat': modo_fat_calc, 'qtd_exc_50': qtd_exc_50, 'qtd_exc_100': qtd_exc_100, 'qtd_exc_200': qtd_exc_200,
        'total_ac': total_ac, 'acionamentos_isentos': acionamentos_isentos
    }

def sincronizar_financeiro_competencia(mes_filtro, df_fin_atual, df_emp_atual, df_cli_atual, df_os_atual):
    df_fin_work = df_fin_atual.copy()
    if df_fin_work.empty or 'id' not in df_fin_work.columns:
        df_fin_work = pd.DataFrame(columns=col_fin)

    mes_atual_str, _ = obter_meses_referencia()
    eh_mes_passado = mes_ano_para_tupla(mes_filtro) < mes_ano_para_tupla(mes_atual_str)

    try:
        mes_s, ano_s = mes_filtro.split('/')
    except:
        hoje = obter_hora_brasilia()
        mes_s, ano_s = f"{hoje.month:02d}", str(hoje.year)

    empresas_ativas = df_emp_atual[df_emp_atual['status'].str.upper() == 'ATIVO']
    alterou_banco = False

    for _, emp_row in empresas_ativas.iterrows():
        nome_emp = str(emp_row['nome']).strip().upper()
        if not nome_emp:
            continue
        id_unico = f"{nome_emp}_{mes_filtro}"
        modo_fat = str(emp_row.get('modo_faturamento', 'Tradicional')).strip()

        mask_reg = (df_fin_work['mes_ano'].str.strip() == mes_filtro) & (df_fin_work['empresa'].str.upper() == nome_emp)

        if not mask_reg.any():
            val_inicial = "0.00"
            if modo_fat != "Tradicional":
                dados_calc = calcular_fatura_parceiro(nome_emp, mes_s, ano_s, df_cli_atual, df_os_atual, df_emp_atual)
                val_inicial = f"{dados_calc['fatura_total']:.2f}"
            novo_fin = pd.DataFrame([{
                'id': id_unico,
                'mes_ano': mes_filtro,
                'empresa': nome_emp,
                'valor_faturado': val_inicial,
                'valor_pago': '0.00',
                'status': 'Pendente'
            }])
            df_fin_work = pd.concat([df_fin_work, novo_fin], ignore_index=True)
            alterou_banco = True
        else:
            idx_list = df_fin_work[mask_reg].index.tolist()
            for idx_r in idx_list:
                status_reg = str(df_fin_work.at[idx_r, 'status']).strip()
                val_salvo = formatar_moeda_float(df_fin_work.at[idx_r, 'valor_faturado'])
                if modo_fat != 'Tradicional' and status_reg != 'Pago':
                    if (not eh_mes_passado) or (eh_mes_passado and val_salvo == 0.0):
                        dados_calc = calcular_fatura_parceiro(nome_emp, mes_s, ano_s, df_cli_atual, df_os_atual, df_emp_atual)
                        novo_val_str = f"{dados_calc['fatura_total']:.2f}"
                        if f"{val_salvo:.2f}" != novo_val_str:
                            df_fin_work.at[idx_r, 'valor_faturado'] = novo_val_str
                            alterou_banco = True

    if alterou_banco:
        salvar_dados(df_fin_work, FILE_FINANCEIRO)

    nomes_ativos = set(empresas_ativas['nome'].str.strip().str.upper().tolist())
    df_fin_mes = df_fin_work[df_fin_work['mes_ano'].str.strip() == mes_filtro].copy()
    if not df_fin_mes.empty:
        df_fin_mes = df_fin_mes[
            df_fin_mes['empresa'].str.upper().isin(nomes_ativos) |
            (df_fin_mes['valor_faturado'].apply(formatar_moeda_float) > 0) |
            (df_fin_mes['valor_pago'].apply(formatar_moeda_float) > 0)
        ].drop_duplicates(subset=['empresa'], keep='last').sort_values(by='empresa')

    return df_fin_work, df_fin_mes

def gerar_texto_resumo_plano(dados_fat):
    modo = dados_fat.get('modo_fat', 'Tradicional')
    if modo == 'Inativo': return f"<b style='color:{COR_VERM_TXT};'>Empresa Inativa. Sem faturamento gerado.</b>"
    
    tot_v = dados_fat.get('total_v', 0)
    taxa = dados_fat.get('taxa', 0.0)
    faixa = dados_fat.get('faixa', 'Enquadramento Base (Até 3%)')
    fat_tot = dados_fat.get('fatura_total', 0.0)
    base = dados_fat.get('valor_base', 0.0)
    placas_tot = dados_fat.get('soma_adicionais', 0.0)
    exc = dados_fat.get('soma_excedentes', 0.0)
    dt_ini = dados_fat['dt_inicio'].strftime('%d/%m/%Y')
    dt_fim = dados_fat['dt_fim'].strftime('%d/%m/%Y')
    
    periodo_str = f"<b>Ciclo Vigente:</b> {dt_ini} a {dt_fim} (Vencimento: Dia {dados_fat['vencimento_dia']})"
    
    if modo == "Performance (Escalonado)":
        texto = f"{periodo_str}<br><b>Plano Ativo:</b> {modo}<br><b>Frota Apurada:</b> {tot_v} veículos ativos (Base Mínima: 30).<br>"
        if taxa == 0.0: texto += f"<b style='color:{COR_VERDE_TXT};'>Taxa de Acionamento: 0.0% (Mês zerado)</b><br>"
        else: texto += f"<b>Taxa de Acionamento:</b> {taxa:.1f}%<br>"
            
        texto += f"<b>Enquadramento Comercial:</b> {faixa}<br>"
        if fat_tot == 400.00 and exc > 0:
            texto += f"<b>Fatura Atualizada: R$ 400,00</b> <span style='color:{COR_VERM_TXT}; font-size:13.5px;'>(Piso Mínimo Garantido Atingido. Valor Real das Placas seria R$ {placas_tot:.2f})</span>"
        else:
            texto += f"<b>Fatura Mapeada:</b> R$ {fat_tot:.2f}"
        return texto
        
    elif "Frota Pequena" in modo or "Até 40" in modo:
        tot_ac = dados_fat.get('total_ac', 0)
        isentos = dados_fat.get('acionamentos_isentos', 0)
        texto = f"{periodo_str}<br><b>Plano Ativo:</b> {modo}<br><b>Base Apurada:</b> {tot_v} veículos<br>"
        texto += f"<b>Franquia Utilizada:</b> {tot_ac} de {isentos} guinchos<br>"
        if exc > 0:
            detalhe_exc = []
            if dados_fat.get('qtd_exc_50', 0) > 0: detalhe_exc.append(f"{dados_fat['qtd_exc_50']}x excedente(s) de 50km")
            if dados_fat.get('qtd_exc_100', 0) > 0: detalhe_exc.append(f"{dados_fat['qtd_exc_100']}x excedente(s) de 100km")
            if dados_fat.get('qtd_exc_200', 0) > 0: detalhe_exc.append(f"{dados_fat['qtd_exc_200']}x excedente(s) de 200km")
            texto += f"<b>Fatura Atualizada: R$ {fat_tot:.2f}</b> <span style='color:{COR_VERM_TXT}; font-size:13.5px;'>(R$ {base:.2f} Fixo + R$ {placas_tot:.2f} Placas + Adicional Extra: R$ {exc:.2f} de {', '.join(detalhe_exc)})</span>"
        else:
            texto += f"<b>Fatura Atual: R$ {fat_tot:.2f}</b> <span style='color:{COR_VERDE_TXT}; font-size:13.5px;'>(Operando dentro da franquia do pacote)</span>"
        return texto
    else:
        return f"{periodo_str}<br><b>Plano Ativo:</b> {modo}<br><b>Base Apurada:</b> {tot_v} veículos<br><b>Faturamento:</b> Lançamento Manual gerido pela Central"

def gerar_pdf_extrato_detalhado(nome_empresa, mes, ano, df_clientes_atuais, df_os_atuais, df_empresas_atuais):
    dados_fat = calcular_fatura_parceiro(nome_empresa, mes, ano, df_clientes_atuais, df_os_atuais, df_empresas_atuais)
    if dados_fat['modo_fat'] == 'Inativo': return "<p>Empresa inativa.</p>"
    
    df_os_temp = df_os_atuais.copy()
    df_os_temp['data_hora'] = pd.to_datetime(df_os_temp['data_hora'], errors='coerce')
    os_mes = df_os_temp[(df_os_temp['empresa'].str.upper() == nome_empresa.upper()) & (df_os_temp['status_os'].str.upper() == 'ENCERRADO') & (df_os_temp['data_hora'] >= dados_fat['dt_inicio']) & (df_os_temp['data_hora'] <= dados_fat['dt_fim'])].sort_values(by='data_hora', ascending=False)

    linhas_os_html = ""
    if os_mes.empty: linhas_os_html = "<tr><td colspan='6' style='text-align: center; padding: 10px; color: #666;'>Nenhum acionamento registrado neste ciclo.</td></tr>"
    else:
        for _, r in os_mes.iterrows():
            is_exc = "<br><span style='color:red; font-size:10px;'>(Exceção/PIX)</span>" if str(r.get('valor_cobrado','0')) not in ['0.00', '0,00', '0', ''] else ""
            linhas_os_html += f"<tr><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{r['id']}{is_exc}</td><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{str(r['data_hora'])[:16]}</td><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px; font-weight: bold;'>{r['placa']}</td><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{r['cliente_nome']}</td><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{r['tipo_servico']}</td><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{r['localizacao']} -> {r['destino']}</td></tr>"

    linhas_veiculos_html = ""
    for idx_v, v in enumerate(dados_fat['veiculos']):
        linhas_veiculos_html += f"<tr><td style='border: 1px solid #ddd; padding: 6px; font-size: 11px;'>{idx_v + 1}</td><td style='border: 1px solid #ddd; padding: 6px; font-size: 11px; font-weight: bold;'>{v['placa']}</td><td style='border: 1px solid #ddd; padding: 6px; font-size: 11px;'>{v['cliente']}</td><td style='border: 1px solid #ddd; padding: 6px; font-size: 11px;'>{v['plano']}</td><td style='border: 1px solid #ddd; padding: 6px; font-size: 11px;'>{v['tipo_cobranca']}</td></tr>"

    str_inicio = dados_fat['dt_inicio'].strftime('%d/%m/%Y')
    str_fim = dados_fat['dt_fim'].strftime('%d/%m/%Y')
    timestamp_arquivo = int(time.time())
    modo_pdf = dados_fat['modo_fat']

    if modo_pdf == "Performance (Escalonado)":
        secao_tabela = f"""<div style="margin-bottom: 20px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #6A1B9A;">3. TABELA DE REFERÊNCIA (AMOSTRAGEM)</h3><p style="margin: 4px 0 10px 0; font-size: 12px; color: #666;">A tarifa mensal baseia-se na % de uso em relação à base (Mínimo de 30 veículos). Enquadramento atual de fechamento: <b>{dados_fat['faixa']}</b>.</p></div>"""
        secao_memoria = f"""<div style="margin-bottom: 20px; background-color: #f3e5f5; padding: 15px; border-radius: 6px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #6A1B9A;">4. MEMÓRIA DE CÁLCULO FINANCEIRO DETALHADA</h3><p style="margin: 4px 0; font-size: 13px;">(+) Valor apurado pela tabela (Soma Placas Ativas): <strong>R$ {dados_fat['soma_adicionais']:.2f}</strong></p>"""
        if dados_fat['fatura_total'] == 400.00 and dados_fat['soma_adicionais'] < 400.00:
            secao_memoria += f"""<p style="margin: 4px 0; font-size: 13px; color: #D32F2F;">(+) Complemento de Piso Mínimo Garantido: <strong>R$ {dados_fat['soma_excedentes']:.2f}</strong></p>"""
        secao_memoria += f"""<hr style="border: 0; border-top: 1px solid #ccc; margin: 10px 0;"><p style="margin: 8px 0; font-size: 18px; color: #6A1B9A; text-align: right;"><strong>VALOR TOTAL DA FATURA: R$ {dados_fat['fatura_total']:.2f}</strong></p></div>"""
        
    elif "Frota Pequena" in modo_pdf or "Até 40 Veículos" in modo_pdf:
        franquia_qtd = f"{dados_fat.get('acionamentos_isentos', 2)} guinchos"
        uso_qtd = f"{dados_fat.get('total_ac', 0)} de {dados_fat.get('acionamentos_isentos', 2)}"
        secao_tabela = f"""<div style="margin-bottom: 20px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #6A1B9A;">3. INFORMAÇÕES DO PACOTE CONTRATADO</h3><p style="margin: 4px 0 10px 0; font-size: 13px;"><strong>Plano:</strong> {modo_pdf}</p><p style="margin: 4px 0 10px 0; font-size: 13px;"><strong>Franquia Inclusa:</strong> {franquia_qtd} mensais.</p><p style="margin: 4px 0 10px 0; font-size: 13px;"><strong>Consumo no Ciclo:</strong> {uso_qtd} utilizados.</p></div>"""
        secao_memoria = f"""<div style="margin-bottom: 20px; background-color: #f3e5f5; padding: 15px; border-radius: 6px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #6A1B9A;">4. MEMÓRIA DE CÁLCULO FINANCEIRO DETALHADA</h3><p style="margin: 4px 0; font-size: 13px;">(+) Base do Pacote Mensal Fixo: <strong>R$ {dados_fat['valor_base']:.2f}</strong></p><p style="margin: 4px 0; font-size: 13px;">(+) Custo das Placas Ativas (Pré-Pago): <strong>R$ {dados_fat['soma_adicionais']:.2f}</strong></p><p style="margin: 4px 0; font-size: 13px;">(+) Adicional de Acionamentos Excedentes (Pós-Pago): <strong>R$ {dados_fat['soma_excedentes']:.2f}</strong></p><hr style="border: 0; border-top: 1px solid #ccc; margin: 10px 0;"><p style="margin: 8px 0; font-size: 18px; color: #6A1B9A; text-align: right;"><strong>VALOR TOTAL DA FATURA: R$ {dados_fat['fatura_total']:.2f}</strong></p></div>"""
    else:
        secao_tabela = ""
        secao_memoria = f"""<div style="margin-bottom: 20px; background-color: #f3e5f5; padding: 15px; border-radius: 6px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #6A1B9A;">4. MEMÓRIA DE CÁLCULO FINANCEIRO</h3><p style="margin: 4px 0; font-size: 13px;">Este cliente opera no modo Tradicional. O valor faturado é gerido manualmente.</p></div>"""

    html_content = f"""<html><head><meta charset='utf-8'></head><body style="font-family: Arial, sans-serif; max-width: 850px; margin: 0 auto; padding: 20px; color: #333;"><div style="text-align: center; margin-bottom: 20px;"><h2 style="margin: 0; color: #6A1B9A; font-size: 24px;">AD RASTREAMENTO VEICULAR</h2><p style="margin: 5px 0; font-size: 14px; color: #555; text-transform: uppercase; font-weight: bold;">Central de Assistência 24 Horas — Extrato de Faturamento e Auditoria</p><p style="margin: 3px 0; font-size: 13px; color: #777;">Empresa: <strong>{nome_empresa.upper()}</strong> | Competência Mês: {mes}/{ano}</p></div><hr style="border: 0; border-top: 2px solid #6A1B9A; margin-bottom: 20px;"><div style="margin-bottom: 20px; background-color: #f8f9fa; padding: 15px; border-radius: 6px; border: 1px solid #eee;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #6A1B9A;">1. RESUMO OPERACIONAL DO CICLO</h3><p style="margin: 4px 0; font-size: 13px;"><strong>Período de Apuração:</strong> {str_inicio} até {str_fim} (Vencimento dia {dados_fat['vencimento_dia']})</p><p style="margin: 4px 0; font-size: 13px;"><strong>Total Exato de Veículos na Base (Ativos):</strong> {dados_fat['total_v']} veículos</p><p style="margin: 4px 0; font-size: 13px;"><strong>Total de Acionamentos Ordinários no Ciclo:</strong> {dados_fat['total_os']} guinchos</p><p style="margin: 4px 0; font-size: 13px;"><strong>Modo Comercial Aplicado:</strong> {modo_pdf}</p></div><div style="margin-bottom: 20px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #6A1B9A;">2. HISTÓRICO DE ATENDIMENTOS DO CICLO</h3><table style="width: 100%; border-collapse: collapse;"><thead><tr style="background-color: #6A1B9A; color: white;"><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">OS</th><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">Data/Hora</th><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">Placa</th><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">Cliente</th><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">Serviço</th><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">Trajeto (Origem -> Destino)</th></tr></thead><tbody>{linhas_os_html}</tbody></table></div>{secao_tabela}{secao_memoria}<div style="margin-bottom: 20px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #6A1B9A;">5. ANEXO DE AUDITORIA: RELAÇÃO DE TODAS AS PLACAS</h3><p style="margin: 4px 0 10px 0; font-size: 11px; color: #666;">Abaixo constam rigorosamente todos os {dados_fat['total_v']} veículos lidos no banco de dados com status ativo para gerar esta fatura.</p><table style="width: 100%; border-collapse: collapse; font-size: 11px;"><thead><tr style="background-color: #e0e0e0; color: #333;"><th style="border: 1px solid #ddd; padding: 6px;">#</th><th style="border: 1px solid #ddd; padding: 6px;">Placa Identificada</th><th style="border: 1px solid #ddd; padding: 6px;">Nome do Cliente Cadastrado</th><th style="border: 1px solid #ddd; padding: 6px;">Plano (KM)</th><th style="border: 1px solid #ddd; padding: 6px;">Enquadramento de Cobrança</th></tr></thead><tbody>{linhas_veiculos_html}</tbody></table></div></body></html>"""
    b64 = base64.b64encode(html_content.encode('utf-8')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="Extrato_Auditavel_{nome_empresa}_{mes}_{ano}_{timestamp_arquivo}.html" style="text-decoration: none;"><button style="background-color: #6A1B9A; color: white; padding: 10px 18px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; width: 100%; font-size: 13px;">Baixar Extrato Oficial e Auditável (PDF/HTML)</button></a>'
                # ===================================================================================
# PORTAIS EXTERNOS (PORTAL DO PRESTADOR ALTO CONTRASTE + CLARO/ESCURO, NPS E GPS)
# ===================================================================================
portal_atual = st.query_params.get("portal", "")

if portal_atual == "guincho":
    os_param = st.query_params.get("os", "")

    col_pt1, col_pt2 = st.columns([4.5, 1.5])
    with col_pt1:
        st.markdown(f"""
            <div class="ad-topbar" style="margin-bottom: 10px;">
                <div class="ad-topbar-brand">
                    <div class="ad-badge-logo">A<span>D</span> 24H</div>
                    <div>
                        <div style="font-size: 14px; font-weight: 800;">PORTAL DO PRESTADOR — CENTRAL DE ASSISTÊNCIA 24 HORAS</div>
                        <div style="font-size: 11.5px; opacity: 0.92;">Ordem de Serviço: <strong>#{os_param if os_param else 'N/D'}</strong></div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col_pt2:
        st.write("")
        lbl_tema_prest = "Modo Claro" if is_dark else "Modo Escuro"
        if st.button(lbl_tema_prest, key="btn_tema_portal_prest", use_container_width=True):
            st.session_state.tema_app = "Claro" if is_dark else "Escuro"
            st.rerun()
    
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
            st.markdown(f"""
                <div class="alert-box alert-danger">
                    <b>CHAMADO INDISPONÍVEL / JÁ ASSUMIDO</b><br>
                    {"A ordem de serviço foi aceita por <b>" + motorista_os + "</b> em " + data_formatada + "." if data_formatada else "A ordem de serviço já foi aceita por <b>" + motorista_os + "</b>."}
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="info-box">Se você é o prestador que assumiu esta OS e a tela recarregou, confirme seu WhatsApp abaixo para retornar ao atendimento:</div>', unsafe_allow_html=True)
            tel_recuperacao = st.text_input("Seu WhatsApp (com DDD):", key="tel_rec")
            if st.button("Recuperar Acesso", use_container_width=True):
                if apenas_numeros_letras(tel_recuperacao) == tel_motorista_os and tel_motorista_os != "":
                    st.session_state[f"dono_{os_param}"] = True
                    st.success("Acesso recuperado. Redirecionando...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Telefone incorreto. Você não é o prestador que assumiu esta OS.")
            st.stop()

    # Barra de etapas do atendimento
    st_p1 = "ativo" if status_atual in ['PENDENTE', 'EM ATENDIMENTO'] else "concluido"
    st_p2 = "ativo" if status_atual == 'A CAMINHO' else ("concluido" if status_atual in ['EM TRÂNSITO', 'CONCLUÍDO', 'ENCERRADO'] else "")
    st_p3 = "ativo" if status_atual == 'EM TRÂNSITO' else ("concluido" if status_atual in ['CONCLUÍDO', 'ENCERRADO'] else "")
    st_p4 = "concluido" if status_atual in ['CONCLUÍDO', 'ENCERRADO'] else ""

    st.markdown(f"""
        <div class="prest-stepper">
            <div class="prest-step {st_p1}">1. Aceite</div>
            <div class="prest-step {st_p2}">2. Chegada / Vistoria</div>
            <div class="prest-step {st_p3}">3. Em Trânsito</div>
            <div class="prest-step {st_p4}">4. Concluído</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="prest-card">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1.5px solid {COR_HR}; padding-bottom:8px; margin-bottom:12px;">
                <span style="font-weight:900; font-size:14px; color:{COR_ROXO_TXT};">RESUMO DA ORDEM DE SERVIÇO #{os_param}</span>
                <span class="service-badge {'badge-green' if status_atual in ['CONCLUÍDO', 'ENCERRADO'] else 'badge-purple' if status_atual in ['A CAMINHO', 'EM TRÂNSITO'] else 'badge-red'}">{status_atual}</span>
            </div>
            <div class="prest-card-label">Origem (Local de Retirada)</div>
            <div class="prest-card-val">{os_info.get('localizacao', 'N/D')}</div>
            <div class="prest-card-label">Destino (Local de Entrega)</div>
            <div class="prest-card-val">{os_info.get('destino', 'N/D')}</div>
            <div class="prest-card-label">Veículo</div>
            <div class="prest-card-val">{v_desc_portal}</div>
            <div class="prest-card-label">Serviço / Motivo</div>
            <div class="prest-card-val" style="margin-bottom:0;">{os_info.get('tipo_servico', '')} ({os_info.get('motivo', '')})</div>
        </div>
    """, unsafe_allow_html=True)
    
    if status_atual in ['PENDENTE', 'EM ATENDIMENTO']:
        st.markdown(f"""
            <div class="info-box">
                <b>Chamado disponível para atendimento.</b><br>
                <b>Placa (Parcial):</b> {mascarar_placa(placa_real)} &nbsp;|&nbsp; <b>Telefone do Cliente:</b> {mascarar_telefone(tel_cliente_real)}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-title">Assumir Ocorrência</div>', unsafe_allow_html=True)
        tel_mot_raw = st.text_input("Digite seu WhatsApp (com DDD) para localizar seu cadastro:")
        tel_limpo = apenas_numeros_letras(tel_mot_raw)
        
        if tel_limpo and len(tel_limpo) >= 10:
            df_prestadores_atual = carregar_dados(FILE_PRESTADORES, col_pre)
            prestador_existente = df_prestadores_atual[df_prestadores_atual['telefone'].apply(apenas_numeros_letras) == tel_limpo]
            
            if not prestador_existente.empty:
                row_p_ex = prestador_existente.iloc[0]
                nome_mot = str(row_p_ex['nome']).upper()
                pix_cadastrado = ler_pix_prestador(row_p_ex)
                st.markdown(f'<div class="alert-box alert-success">Cadastro localizado: <b>{nome_mot}</b>.</div>', unsafe_allow_html=True)
                pix_complemento = ""
                if not pix_cadastrado:
                    pix_complemento = st.text_input("Chave PIX para Pagamento (Opcional — salva no seu cadastro):", placeholder="CPF, CNPJ, E-mail ou Celular")

                if st.button("ACEITAR CHAMADO", type="primary", use_container_width=True):
                    df_check = carregar_dados(FILE_OS, col_os)
                    os_check = df_check[df_check['id'].astype(str) == str(os_param)]
                    
                    if not os_check.empty and str(os_check.iloc[0]['status_os']).upper() not in ['PENDENTE', 'EM ATENDIMENTO']:
                        st.error("Este chamado já foi assumido por outro prestador.")
                    else:
                        pix_final_aceite = pix_cadastrado or pix_complemento.strip()
                        if not pix_cadastrado and pix_complemento.strip():
                            df_prestadores_atual.loc[df_prestadores_atual['id'].astype(str) == str(row_p_ex['id']), 'frota'] = empacotar_pix_prestador(row_p_ex.get('frota', ''), pix_complemento.strip())
                            salvar_dados(df_prestadores_atual, FILE_PRESTADORES)

                        hora_agora = obter_hora_str()
                        tel_save = f"{tel_limpo}|{hora_agora}"
                        novos_meta = {'sla_aceite': hora_agora}
                        if pix_final_aceite:
                            novos_meta['pix_prestador_os'] = pix_final_aceite
                        meta_save = mesclar_meta_os(os_info.get('fotos_vistoria', ''), novos_meta)
                        df_os.loc[df_os['id'].astype(str) == str(os_param), ['status_os', 'motorista_nome', 'motorista_tel', 'fotos_vistoria']] = ['A CAMINHO', nome_mot, tel_save, meta_save]
                        salvar_dados(df_os, FILE_OS)
                        st.session_state[f"dono_{os_param}"] = True
                        st.success("Chamado assumido com sucesso. Dirija-se ao local.")
                        time.sleep(1.5)
                        st.rerun()
            else:
                st.markdown('<div class="alert-box alert-danger">Número não localizado. Preencha seu cadastro rápido abaixo para assumir a OS:</div>', unsafe_allow_html=True)
                nome_mot = st.text_input("Seu Nome / Nome da sua Base:")
                c_est, c_cid = st.columns(2)
                est_mot = c_est.selectbox("Estado (UF):", ESTADOS_BR, index=ESTADOS_BR.index("RN"))
                cid_mot = c_cid.text_input("Cidade:")
                bairro_mot = st.text_input("Bairro:")
                pix_mot = st.text_input("Chave PIX para Pagamento:", placeholder="CPF, CNPJ, E-mail ou Celular")
                
                if st.button("CADASTRAR E ACEITAR CHAMADO", type="primary", use_container_width=True):
                    if not nome_mot or not cid_mot:
                        st.error("Preencha seu Nome e Cidade para continuar.")
                    else:
                        df_check = carregar_dados(FILE_OS, col_os)
                        os_check = df_check[df_check['id'].astype(str) == str(os_param)]
                        
                        if not os_check.empty and str(os_check.iloc[0]['status_os']).upper() not in ['PENDENTE', 'EM ATENDIMENTO']:
                            st.error("Este chamado já foi assumido por outro prestador.")
                        else:
                            prox_p = int(df_prestadores_atual['id'].astype(float).max() + 1) if not df_prestadores_atual.empty else 1
                            frota_pix = empacotar_pix_prestador("", pix_mot)
                            novo_p = pd.DataFrame([{'id': str(prox_p), 'nome': nome_mot.upper(), 'cpf': '', 'tipo': 'Guincho', 'telefone': tel_limpo, 'endereco': '', 'bairro': bairro_mot.upper(), 'cidade': cid_mot.upper(), 'cep': '', 'est': est_mot, 'status': 'Ativo', 'homologado': 'Pendente', 'senha': 'admin', 'frota': frota_pix}])
                            df_p_temp = pd.concat([df_prestadores_atual, novo_p], ignore_index=True)
                            salvar_dados(df_p_temp, FILE_PRESTADORES)
                            
                            hora_agora = obter_hora_str()
                            tel_save = f"{tel_limpo}|{hora_agora}"
                            novos_meta = {'sla_aceite': hora_agora}
                            if pix_mot.strip():
                                novos_meta['pix_prestador_os'] = pix_mot.strip()
                            meta_save = mesclar_meta_os(os_info.get('fotos_vistoria', ''), novos_meta)
                            df_os.loc[df_os['id'].astype(str) == str(os_param), ['status_os', 'motorista_nome', 'motorista_tel', 'fotos_vistoria']] = ['A CAMINHO', nome_mot.upper(), tel_save, meta_save]
                            salvar_dados(df_os, FILE_OS)
                            st.session_state[f"dono_{os_param}"] = True
                            st.success("Cadastro criado e chamado assumido com sucesso. Dirija-se ao local.")
                            time.sleep(1.5)
                            st.rerun()
                    
    elif status_atual == 'A CAMINHO':
        link_w_cli = f"https://api.whatsapp.com/send?phone=55{apenas_numeros_letras(tel_cliente_real)}"
        st.markdown(f"""
            <div class="alert-box alert-success">
                <b>CHAMADO ASSUMIDO — DIRIJA-SE AO LOCAL DE ORIGEM</b><br>
                <b>Cliente:</b> {os_info.get('cliente_nome', 'N/D')} &nbsp;|&nbsp; <b>Telefone Liberado:</b> {tel_cliente_real}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f'<a href="{link_w_cli}" target="_blank" style="text-decoration:none;"><button style="background-color: #25D366; color: #FFFFFF; padding: 12px; width: 100%; border: none; border-radius: 8px; font-weight: 800; font-size: 14px; cursor: pointer; margin-bottom: 16px;">Falar com Cliente no WhatsApp</button></a>', unsafe_allow_html=True)
        
        st.markdown('<div class="section-title">Validação Física (Chegada no Local)</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-box">Ao chegar no local, digite a placa completa do veículo para liberar a vistoria fotográfica e a assinatura de embarque.</div>', unsafe_allow_html=True)
        placa_digitada = st.text_input("Placa Completa do Veículo (Somente letras e números):", placeholder="Ex: ABC1D23")
        
        if "vistoria_liberada" not in st.session_state:
            st.session_state.vistoria_liberada = False
            
        if st.button("Validar Placa e Liberar Vistoria", use_container_width=True):
            if apenas_numeros_letras(placa_digitada).upper() == apenas_numeros_letras(placa_real).upper():
                st.session_state.vistoria_liberada = True
                st.success("Placa validada. Preencha o checklist abaixo.")
            else:
                st.error("Placa incorreta. Verifique o veículo e tente novamente.")
                
        if st.session_state.vistoria_liberada:
            st.write("---")
            st.markdown('<div class="inspection-reader-header"><span>Vistoria Fotográfica de Embarque (4 Fotos Obrigatórias)</span><span>CHECKLIST</span></div>', unsafe_allow_html=True)
            st.markdown('<div class="inspection-reader-body">', unsafe_allow_html=True)
            c_cam1, c_cam2 = st.columns(2)
            with c_cam1: 
                frente = st.file_uploader("1. Foto Frente", type=['jpg', 'jpeg', 'png'])
                if frente: st.image(frente, use_container_width=True)
            with c_cam2: 
                traseira = st.file_uploader("2. Foto Traseira", type=['jpg', 'jpeg', 'png'])
                if traseira: st.image(traseira, use_container_width=True)
            with c_cam1: 
                lat_dir = st.file_uploader("3. Foto Lateral Direita", type=['jpg', 'jpeg', 'png'])
                if lat_dir: st.image(lat_dir, use_container_width=True)
            with c_cam2: 
                lat_esq = st.file_uploader("4. Foto Lateral Esquerda", type=['jpg', 'jpeg', 'png'])
                if lat_esq: st.image(lat_esq, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="section-title">Assinatura do Condutor (Embarque)</div>', unsafe_allow_html=True)
            doc_cliente_input = st.text_input("Documento Identificador do Cliente (CPF ou RG):", placeholder="Obrigatório para validar a assinatura")
            st.markdown('<div class="info-box">Solicite ao responsável pelo veículo que assine no quadro branco abaixo:</div>', unsafe_allow_html=True)
            
            canvas_result = None
            assinatura_foto = None
            
            if CANVAS_AVAILABLE:
                canvas_result = st_canvas(
                    fill_color="rgba(255, 165, 0, 0.3)",
                    stroke_width=3,
                    stroke_color="#000000",
                    background_color="#FFFFFF",
                    height=200,
                    drawing_mode="freedraw",
                    key="canvas_assinatura",
                )
            else:
                st.warning("Módulo de assinatura digital desativado no momento.")
                assinatura_foto = st.file_uploader("Envie uma foto do Documento e da Assinatura do Cliente", type=['jpg', 'jpeg', 'png'])
                if assinatura_foto: st.image(assinatura_foto, use_container_width=True)
                
            st.write("")
            if st.button("FINALIZAR CHECKLIST E INICIAR TRANSPORTE", type="primary", use_container_width=True):
                if not frente or not traseira or not lat_dir or not lat_esq:
                    st.error("As 4 fotos são obrigatórias para liberar o transporte.")
                elif not doc_cliente_input:
                    st.error("O número do Documento (CPF/RG) do cliente é obrigatório.")
                else:
                    with st.spinner("Processando imagens e gravando horário de embarque..."):
                        b_frente = comprimir_imagem_b64(frente)
                        b_traseira = comprimir_imagem_b64(traseira)
                        b_dir = comprimir_imagem_b64(lat_dir)
                        b_esq = comprimir_imagem_b64(lat_esq)
                        hora_embarque = obter_hora_str()
                        meta_emb = mesclar_meta_os(os_info.get('fotos_vistoria', ''), {
                            "frente": b_frente,
                            "traseira": b_traseira,
                            "lat_dir": b_dir,
                            "lat_esq": b_esq,
                            "doc_cliente": doc_cliente_input,
                            "sla_embarque": hora_embarque
                        })
                        
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
                            
                        df_os.loc[df_os['id'].astype(str) == str(os_param), ['status_os', 'fotos_vistoria', 'assinatura_cliente']] = ['EM TRÂNSITO', meta_emb, b64_assinatura]
                        salvar_dados(df_os, FILE_OS)
                        
                        st.success("Vistoria registrada com sucesso. Transporte autorizado.")
                        st.session_state.vistoria_liberada = False
                        time.sleep(2)
                        st.rerun()
                        
    elif status_atual == 'EM TRÂNSITO':
        st.markdown(f"""
            <div class="alert-box alert-success">
                <b>VEÍCULO EMBARCADO — EM DESLOCAMENTO PARA O DESTINO</b><br>
                <b>Destino Final:</b> {os_info.get('destino', 'N/D')}<br>
                <b>Observações Extras:</b> {os_info.get('obs', 'Nenhuma') or 'Nenhuma'}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="inspection-reader-header"><span>Vistoria de Desembarque (Entrega no Destino)</span><span>1 FOTO OBRIGATÓRIA</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="inspection-reader-body">', unsafe_allow_html=True)
        st.markdown('<div class="info-box" style="margin-top:0;">Ao descarregar o veículo no destino, envie <b>1 foto</b> comprovando a entrega. Não é necessária nova assinatura.</div>', unsafe_allow_html=True)
        foto_desembarque = st.file_uploader("Foto do Veículo Descarregado no Destino:", type=['jpg', 'jpeg', 'png'], key=f"up_desemb_{os_param}")
        if foto_desembarque:
            st.image(foto_desembarque, caption="Prévia da foto de entrega", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.write("")
        if st.button("DESEMBARCAR E CONCLUIR ROTA", type="primary", use_container_width=True):
            if not foto_desembarque:
                st.error("Envie a foto do veículo descarregado no destino antes de concluir a rota.")
            else:
                with st.spinner("Registrando foto de entrega e concluindo rota..."):
                    b_desemb = comprimir_imagem_b64(foto_desembarque)
                    hora_conc = obter_hora_str()
                    meta_conc = mesclar_meta_os(os_info.get('fotos_vistoria', ''), {
                        'foto_desembarque': b_desemb,
                        'sla_conclusao': hora_conc
                    })
                    df_os.loc[df_os['id'].astype(str) == str(os_param), ['status_os', 'fotos_vistoria']] = ['CONCLUÍDO', meta_conc]
                    salvar_dados(df_os, FILE_OS)
                    st.success("Entrega e foto de desembarque registradas com sucesso. A Central foi notificada.")
                    time.sleep(2)
                    st.rerun()
                
    elif status_atual in ['CONCLUÍDO', 'ENCERRADO', 'CANCELADO']:
        st.markdown(f"""
            <div class="alert-box alert-success">
                <b>CHAMADO {status_atual}</b><br>
                A entrega foi finalizada e a Central de Assistência 24 Horas já foi informada.
            </div>
        """, unsafe_allow_html=True)
    
    st.stop()

elif portal_atual == "nps":
    st.markdown('<div class="main-title">Pesquisa de Qualidade</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Central de Assistência 24 Horas</div>', unsafe_allow_html=True)
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
        st.info("Esta ordem de serviço já foi avaliada. Obrigado pela participação.")
        st.stop()

    st.write(f"**Veículo:** {os_info['placa']}")
    st.write(f"**Data do Chamado:** {os_info['data_hora'][:10]}")
    st.write("---")
    
    st.markdown(f"<h4 style='color: {COR_ROXO_DEST}; font-size: 15px;'>1. Em uma escala de 0 a 10, o quanto você recomendaria a assistência 24 horas para um amigo ou familiar?</h4>", unsafe_allow_html=True)
    nota_nps = st.slider("Arraste para dar sua nota:", min_value=0, max_value=10, value=10)
    
    st.markdown(f"<h4 style='color: {COR_ROXO_DEST}; margin-top: 15px; font-size: 15px;'>2. Como você avalia a agilidade e educação do nosso Operador da Central?</h4>", unsafe_allow_html=True)
    nota_central = st.feedback("stars", key="fb_central")
    
    st.markdown(f"<h4 style='color: {COR_ROXO_DEST}; margin-top: 15px; font-size: 15px;'>3. Como você avalia o atendimento presencial do Motorista do Guincho?</h4>", unsafe_allow_html=True)
    nota_guincho = st.feedback("stars", key="fb_guincho")
    
    comentario = st.text_area("Gostaria de deixar um comentário, elogio ou sugestão? (Opcional)")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Enviar avaliação", use_container_width=True, type="primary"):
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

        st.success("Avaliação enviada com sucesso. Obrigado pelo retorno.")
        time.sleep(2)
        st.rerun()
    st.stop()

elif portal_atual == "cliente":
    st.markdown('<div class="main-title">AD Rastreamento</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Central de Assistência 24 Horas - Resgate</div>', unsafe_allow_html=True)
    placa_param = st.query_params.get("placa", "N/D")
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    body {{ font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #f8f9fa; margin: 0; }}
    .btn {{ background-color: #D32F2F; color: white; padding: 18px; font-size: 15px; border: none; border-radius: 8px; cursor: pointer; width: 100%; max-width: 300px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.2); margin-top: 15px; }}
    .btn:active {{ background-color: #b71c1c; }}
    #msg {{ margin-top: 15px; font-size: 14px; color: #555; font-weight: bold; }}
    </style>
    </head>
    <body>
    <h3 style="color: #6A1B9A; margin-top:0; font-size: 18px;">Localização de Emergência</h3>
    <p style="font-size:14px;">Precisamos saber onde você está para enviar o guincho exato até o veículo placa <b>{placa_param}</b>.</p>
    <button id="btn-loc" class="btn" onclick="getLocation()">ENVIAR MINHA LOCALIZAÇÃO</button>
    <p id="msg"></p>
    <script>
    function getLocation() {{
        document.getElementById("msg").innerHTML = "Aguardando GPS... Autorize se o celular solicitar.";
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
        document.getElementById("msg").innerHTML = "Sinal capturado. Salvando no sistema...";
        
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
                document.getElementById("msg").innerHTML = "Acesso ao GPS negado. Libere a permissão e tente novamente.";
                break;
            case error.POSITION_UNAVAILABLE:
                document.getElementById("msg").innerHTML = "Sinal de GPS indisponível no momento.";
                break;
            case error.TIMEOUT:
                document.getElementById("msg").innerHTML = "Tempo esgotado para buscar o GPS.";
                break;
            default:
                document.getElementById("msg").innerHTML = "Erro desconhecido ao tentar localizar.";
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
    st.markdown('<div class="subtitle">Central de Assistência 24 Horas - Resgate</div>', unsafe_allow_html=True)
    placa_cliente = st.query_params.get("placa", "N/D")
    lat = st.query_params.get("lat", "")
    lon = st.query_params.get("lon", "")
    
    if lat and lon:
        link_maps = f"https://www.google.com/maps?q={lat},{lon}"
        novo_loc_dict = {'placa': placa_cliente, 'data_hora': obter_hora_str(), 'link_maps': link_maps}
        try:
            supabase.table(FILE_LOC).insert(novo_loc_dict).execute()
        except: pass
        st.success("Localização recebida com sucesso pela Central. O socorro já está sendo acionado. Você já pode fechar esta tela.")
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
    col_esp1, col_meio, col_esp2 = st.columns([1.2, 1.8, 1.2])
    with col_meio:
        st.markdown("""
            <div class="dash-box" style="border-top: 5px solid #6A1B9A; text-align:center; padding: 28px 20px 10px 20px; margin-top: 30px;">
                <div style="display:inline-block; background:#6A1B9A; color:#fff; font-weight:900; padding:8px 16px; border-radius:10px; font-size:20px; margin-bottom:10px;">
                    <span style="color:#fff;">A</span><span style="color:#FF5252;">D</span> RASTREAMENTO
                </div>
                <div class="main-title" style="font-size:24px;">Central de Assistência 24 Horas</div>
                <div class="subtitle" style="margin-bottom:10px;">Operação e Despacho — Acesso Restrito</div>
            </div>
        """, unsafe_allow_html=True)
        usuario_input = apenas_numeros_letras(st.text_input("Usuário (Nome da Empresa ou Central):"))
        senha_input = apenas_numeros_letras(st.text_input("Senha (CNPJ):", type="password"))
        if st.button("Entrar no Sistema Operacional", use_container_width=True, key="btn_login_geral"):
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
# HEADER DO SISTEMA (CENTRAL DE ASSISTÊNCIA 24 HORAS + TEMA CLARO/ESCURO + ATUALIZAR + SAIR)
# ===================================================================================
col_user, col_tema, col_refresh, col_logout = st.columns([5.4, 1.5, 1.6, 1.5])
with col_user: 
    st.markdown(f"""
        <div class="ad-topbar">
            <div class="ad-topbar-brand">
                <div class="ad-badge-logo">A<span>D</span> 24H</div>
                <div>
                    <div style="font-size: 14.5px; font-weight: 800; letter-spacing: 0.3px;">CENTRAL DE ASSISTÊNCIA 24 HORAS</div>
                    <div style="font-size: 12px; opacity: 0.9;">Operador Ativo: <strong>{st.session_state.user}</strong></div>
                </div>
            </div>
            <div style="background: rgba(255,255,255,0.16); padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700;">
                <span class="status-dot"></span>ONLINE
            </div>
        </div>
    """, unsafe_allow_html=True)
with col_tema:
    st.write("")
    label_tema = "Modo Claro" if is_dark else "Modo Escuro"
    if st.button(label_tema, key="btn_toggle_tema_topo", use_container_width=True):
        st.session_state.tema_app = "Claro" if is_dark else "Escuro"
        st.rerun()
with col_refresh:
    st.write("")
    if st.button("Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with col_logout:
    st.write("")
    if st.button("Sair", key="btn_logout_master", use_container_width=True):
        st.session_state.logado = False
        st.query_params.clear()
        st.rerun()

# ===================================================================================
# INTERFACE 1: ADMIN MASTER (MENU LATERAL MINIMALISTA + DASHBOARD + NOVA OS)
# ===================================================================================
if st.session_state.perfil == "Admin":
    qtd_pendencias = len(df_os[~df_os['status_os'].str.upper().isin(['ENCERRADO', 'CANCELADO'])])
    aba_pendencias_nome = f"Pendências ({qtd_pendencias})"
    
    opcoes_admin = [
        "Dashboard",
        "Nova OS",
        aba_pendencias_nome,
        "Empresas",
        "Clientes",
        "Prestadores",
        "Satisfação (NPS)",
        "Financeiro",
        "Auditoria",
        "Relatórios & PDF",
        "Dados"
    ]
    
    aba_atual_admin = st.query_params.get("nav", opcoes_admin[0])
    if aba_atual_admin not in opcoes_admin: 
        aba_atual_admin = aba_pendencias_nome if "Pendências" in aba_atual_admin else opcoes_admin[0]
            
    with st.sidebar:
        st.markdown("""
            <div class="sidebar-brand-box">
                <div class="sidebar-brand-title">AD ASSISTÊNCIA 24H</div>
                <div class="sidebar-brand-sub">Central de Assistência 24 Horas</div>
            </div>
        """, unsafe_allow_html=True)
        aba_selecionada = st.radio("Navegação Principal:", opcoes_admin, index=opcoes_admin.index(aba_atual_admin), label_visibility="collapsed")
    
    if aba_selecionada != aba_atual_admin:
        st.query_params["nav"] = aba_selecionada
        st.rerun()
    
    if aba_selecionada == "Dashboard":
        empresas_lista = ["Todas"] + sorted([str(e).upper() for e in df_empresas['nome'].unique() if str(e).strip() != ""])
        empresa_filtro = st.selectbox("Filtrar por Empresa Parceira:", empresas_lista)
        renderizar_dashboard(empresa_filtro, eh_admin=True)

    elif aba_selecionada == "Nova OS":
        st.markdown('<div class="section-title">Abertura de Chamado</div>', unsafe_allow_html=True)
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
        if "os_val_exc_num" not in st.session_state: st.session_state.os_val_exc_num = 0.0

        pronto_para_prosseguir = False
        is_excecao_flag = False
        valor_excecao_num = 0.0
        valor_excecao_fmt = "0,00"
        cliente_id_os, cliente_nome_os, placa_alvo, veiculo_desc_alvo, empresa_os, plano_km_os, uf_cliente, cidade_cliente, valor_cobrado_os = "", "", "", "", "", "", "RN", "", "0,00"
        tel_envio_link = ""

        if tipo_atendimento == "Cliente Cadastrado":
            if df_clientes.empty: st.warning("Nenhum cliente cadastrado no sistema para busca.")
            else:
                busca = st.text_input("Buscar cliente por Nome, Placa ou CPF:", value=st.session_state.os_busca_val)
                st.session_state.os_busca_val = busca
                if not busca: st.info("Digite o Nome, Placa ou CPF do cliente acima para iniciar o atendimento.")
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
                                            blindado_str = " [BLINDADO]" if v.get('Blindado') in [True, 'true', 'Sim', 'SIM', '1'] else ""
                                            tipo_str = v.get('Tipo', 'Carro')
                                            lista_frota_opcoes.append(f"{tipo_str} {v.get('Modelo/Ano', '')}{blindado_str} - Placa: {v.get('Placa')}")
                                except: pass 
                            if not lista_frota_opcoes:
                                if pd.notna(cliente_dados.get('pla')) and str(cliente_dados['pla']).strip(): lista_frota_opcoes.append(f"{cliente_dados.get('vei', 'Veículo')} - Placa: {cliente_dados['pla']}")
                                if pd.notna(cliente_dados.get('pla_2')) and str(cliente_dados['pla_2']).strip(): lista_frota_opcoes.append(f"{cliente_dados.get('vei_2', 'Veículo')} - Placa: {cliente_dados['pla_2']}")
                            
                            if not lista_frota_opcoes: st.error("Este cliente não possui veículos cadastrados com placa válida.")
                            else:
                                veiculo_sel_os = st.selectbox("Selecione o Veículo da frota:", lista_frota_opcoes)
                                tipo_servico = st.selectbox("Tipo de Serviço Solicitado:", ["Guincho", "Pane Seca", "Pane Elétrica", "Borracheiro", "Chaveiro"])
                                motivo_servico = st.selectbox("Motivo do Acionamento:", ["Acidente", "Furto", "Roubo", "Outros"])
                                
                                placa_alvo = veiculo_sel_os.split("Placa: ")[1].strip().upper()
                                veiculo_desc_alvo = veiculo_sel_os.split(" - Placa:")[0].strip()
                                
                                is_blindado = "BLINDADO" in veiculo_desc_alvo
                                veiculo_blindado_os = st.radio("Veículo é Blindado?", ["Não", "Sim"], index=1 if is_blindado else 0, horizontal=True)
                                
                                if veiculo_blindado_os == "Sim" and "BLINDADO" not in veiculo_desc_alvo:
                                    veiculo_desc_alvo += " [BLINDADO]"
                                elif veiculo_blindado_os == "Não" and "BLINDADO" in veiculo_desc_alvo:
                                    veiculo_desc_alvo = veiculo_desc_alvo.replace(" [BLINDADO]", "").replace("[BLINDADO]", "").replace("(BLINDADO)", "").strip()

                                uf_cliente = str(cliente_dados['est']).strip().upper() if cliente_dados['est'] else "RN"
                                plano_km_os, cidade_cliente, cliente_id_os, cliente_nome_os, empresa_os = str(cliente_dados.get('plano_km', 'N/D')), str(cliente_dados.get('cidade', '')).strip().upper(), str(c_target_os), str(cliente_dados['nome']), str(cliente_dados['emp_name'])
                                tel_envio_link = apenas_numeros_letras(cliente_dados.get('tel', ''))

                                st.info(f"Cliente: **{empresa_os.upper()}** | UF do Veículo: **{uf_cliente}**")
                                dt_cad_str = str(cliente_dados.get('data_cadastro', ''))
                                inicio_ciclo, fim_ciclo = obter_ciclo_contrato_anual(dt_cad_str)
                                st.markdown(f'<div class="info-box" style="padding: 10px;">PLANO CONTRATADO: <b>{plano_km_os}</b><br>CICLO DE CONTRATO DA PLACA: <b>{inicio_ciclo.strftime("%d/%m/%Y")} a {fim_ciclo.strftime("%d/%m/%Y")}</b></div>', unsafe_allow_html=True)
                                
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
                                    elif "ELÉTRICA" in serv or "ELETRICA" in serv: uso_atual["PANE ELÉTRICA"] += 1
                                    elif "BORRACHEIRO" in serv: uso_atual["BORRACHEIRO"] += 1
                                    elif "CHAVEIRO" in serv: uso_atual["CHAVEIRO"] += 1
                                
                                st.markdown("##### Auditoria de Saldos da Placa no Ciclo Atual")
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
                                    if cliente_inativo: st.markdown('<div class="alert-box alert-danger" style="font-size: 14px; text-align: center;">ALERTA: CLIENTE INATIVO<br><span style="font-size: 13px; font-weight: normal;">Possível inadimplência ou cancelamento.</span></div>', unsafe_allow_html=True)
                                    if bloqueio_60: st.markdown(f'<div class="alert-box alert-danger" style="font-size: 14px; text-align: center;">ALERTA: REGRA DOS 60 DIAS ATIVA<br><span style="font-size: 13px; font-weight: bold;">{msg_bloqueio_60}</span></div>', unsafe_allow_html=True)
                                    if limite_excedido: st.markdown(f'<div class="alert-box alert-danger" style="font-size: 14px; text-align: center;">ALERTA: LIMITE ANUAL ATINGIDO<br><span style="font-size: 13px; font-weight: bold;">Esta placa já utilizou o limite máximo de {tipo_servico} no ciclo de contrato atual.</span></div>', unsafe_allow_html=True)
                                        
                                    liberar_excecao = st.checkbox("Ciente dos bloqueios acima: Liberar Atendimento por Exceção")
                                    if liberar_excecao:
                                        c_ex1, c_ex2 = st.columns([2, 1])
                                        valor_excecao_num = c_ex1.number_input(
                                            "Valor do Serviço Extra a ser Cobrado (R$):",
                                            min_value=0.0,
                                            value=float(st.session_state.get("os_val_exc_num", 0.0)),
                                            step=10.0,
                                            format="%.2f",
                                            key="inp_val_exc_os"
                                        )
                                        st.session_state.os_val_exc_num = float(valor_excecao_num)
                                        with c_ex2:
                                            st.write("")
                                            if st.button("Confirmar Valor na Mensagem PIX", key="btn_conf_val_pix", use_container_width=True):
                                                st.session_state.os_val_exc_num = float(valor_excecao_num)
                                                st.rerun()

                                        valor_excecao_fmt = formatar_brl(st.session_state.os_val_exc_num)
                                        valor_cobrado_os = valor_excecao_fmt
                                        is_excecao_flag = True
                                        pronto_para_prosseguir = True
                                    else: pronto_para_prosseguir = False
                                else: pronto_para_prosseguir = True
        else:
            st.info("Preencha os dados do atendimento avulso particular abaixo:")
            col_av1, col_av2 = st.columns(2)
            nome_avulso, tel_avulso = col_av1.text_input("Nome Completo do Cliente:"), col_av2.text_input("Telefone de Contato:")
            veiculo_avulso = col_av1.text_input("Veículo (Tipo/Modelo/Ano/Cor):")
            placa_avulso = col_av2.text_input("Placa do Veículo:")
            
            veiculo_blindado_os = col_av1.radio("Veículo é Blindado?", ["Não", "Sim"], horizontal=True)
            if veiculo_blindado_os == "Sim":
                veiculo_avulso += " [BLINDADO]"
                
            uf_cliente, cidade_cliente = col_av1.selectbox("Estado (UF) do Atendimento:", options=ESTADOS_BR, index=ESTADOS_BR.index("RN")), col_av2.text_input("Cidade do Atendimento:")
            valor_cobrado_os = col_av1.text_input("Valor Cobrado do Particular (R$):", value="0,00")
            tipo_servico = st.selectbox("Tipo de Serviço:", ["Guincho", "Pane Seca", "Pane Elétrica", "Borracheiro", "Chaveiro"])
            motivo_servico = st.selectbox("Motivo do Acionamento:", ["Acidente", "Furto", "Roubo", "Outros"])
            cliente_id_os, cliente_nome_os, placa_alvo, veiculo_desc_alvo, empresa_os, plano_km_os = "AVULSO", nome_avulso, placa_avulso.upper().strip(), veiculo_avulso, "CLIENTE PARTICULAR (AVULSO)", "Particular"
            tel_envio_link = apenas_numeros_letras(tel_avulso)
            
            if nome_avulso and placa_alvo: pronto_para_prosseguir = True
            else: st.warning("Nome do Cliente e Placa são obrigatórios para liberar o atendimento avulso.")

        # =====================================================================
        # TRAVA ANTI-DUPLICIDADE
        # =====================================================================
        if placa_alvo and not df_os.empty:
            placa_chk = apenas_numeros_letras(placa_alvo).upper()
            os_duplicadas = df_os[
                (df_os['placa'].astype(str).apply(lambda x: apenas_numeros_letras(x).upper()) == placa_chk) &
                (~df_os['status_os'].str.upper().isin(['ENCERRADO', 'CANCELADO']))
            ]
            if not os_duplicadas.empty:
                r_dup = os_duplicadas.iloc[0]
                st.markdown(f"""
                    <div class="alert-box alert-danger" style="text-align:center; border: 2px solid #D32F2F;">
                        <b>TRAVA ANTI-DUPLICIDADE ATIVADA</b><br>
                        Já existe uma Ordem de Serviço em andamento para a placa <b>{placa_alvo}</b>.<br>
                        <span style="font-size:13px;">OS <b>#{r_dup['id']}</b> | Status: <b>{r_dup['status_os']}</b> | Aberta em: {r_dup['data_hora']} | Serviço: {r_dup['tipo_servico']}</span><br>
                        <span style="font-size:12px;">Encerre ou cancele a OS aberta na aba Pendências antes de abrir um novo chamado para este veículo.</span>
                    </div>
                """, unsafe_allow_html=True)
                pronto_para_prosseguir = False

        if pronto_para_prosseguir:
            st.write("---")
            st.markdown('<div class="section-title">Endereço da Ocorrência e Destino</div>', unsafe_allow_html=True)
            st.info("Caso o cliente não saiba informar o endereço, envie o link de captura de GPS pelo WhatsApp abaixo e puxe a localização automaticamente.")
            link_captura = f"https://ad-central-mrssupqbb9ux69bi4qgisa.streamlit.app/?portal=cliente&placa={placa_alvo}"
            col_loc1, col_loc2 = st.columns([1, 1])
            texto_zap_loc = f"Olá! Aqui é da *Central de Assistência 24 Horas — AD Rastreamento*.\n\nPara despacharmos o seu socorro rápido, precisamos da sua localização exata. Por favor, clique no link abaixo, permita o uso do GPS e aperte no botão 'ENVIAR MINHA LOCALIZAÇÃO':\n\n📍 {link_captura}"
            link_w_loc = f"https://api.whatsapp.com/send?phone=55{tel_envio_link}&text={urllib.parse.quote(texto_zap_loc)}"
            
            with col_loc1:
                st.markdown(f'<a href="{link_w_loc}" target="_blank"><button style="background-color: #25D366; color: white; padding: 10px; width: 100%; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; font-size: 13px;">1. Enviar Link GPS no WhatsApp do Cliente</button></a>', unsafe_allow_html=True)
            with col_loc2:
                if st.button("2. Puxar Localização Recebida", use_container_width=True, key="btn_puxar_loc_admin"):
                    df_loc_temp = carregar_dados(FILE_LOC, ['placa', 'data_hora', 'link_maps'])
                    loc_cliente = df_loc_temp[df_loc_temp['placa'] == placa_alvo]
                    if not loc_cliente.empty:
                        ultima_loc = loc_cliente.iloc[-1]['link_maps']
                        st.session_state.os_loc_val = ultima_loc
                        st.success("GPS recebido com sucesso. O campo Origem foi preenchido.")
                        time.sleep(2); st.rerun()
                    else: st.warning("O cliente ainda não enviou a localização. Aguarde alguns segundos e tente novamente.")

            st.write("")
            c_orig1, c_orig_b, c_orig2 = st.columns([1, 1, 3])
            cep_orig = c_orig1.text_input("CEP Origem:", value=st.session_state.os_cep_orig_val, placeholder="Somente números")
            st.session_state.os_cep_orig_val = cep_orig

            if c_orig1.button("Buscar Origem", use_container_width=True, key="btn_cep_orig_admin"):
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
            if c_dest1.button("Buscar Destino", use_container_width=True, key="btn_cep_dest_admin"):
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
            st.markdown('<div class="section-title">Prestador Acionado (Inteligência de Despacho)</div>', unsafe_allow_html=True)
            
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
                        if r['prioridade'] == 0: marcador = "[EXATO - MESMO CEP] "
                        elif r['prioridade'] == 1: marcador = "[PRÓXIMO - MESMO BAIRRO] "
                        elif r['prioridade'] == 2: marcador = "[MESMA CIDADE] "
                        else: marcador = ""
                        lista_p_ops.append(f"{marcador}{str(r['nome'])} - Tel: {str(r['telefone'])} - Bairro: {str(r.get('bairro','N/D')).upper()} - {str(r['cidade']).upper()}/{str(r['est']).upper()}")
                else:
                    df_aprovados = df_prestadores[df_prestadores['homologado'] == 'Aprovado']
                    for _, r in df_aprovados.iterrows(): 
                        lista_p_ops.append(f"{str(r['nome'])} - Tel: {str(r['telefone'])} - Bairro: {str(r.get('bairro','N/D')).upper()} - {str(r['cidade']).upper()}/{str(r['est']).upper()}")
            
            prestador_sel = st.selectbox("Prestadores homologados (ordenados por proximidade):", lista_p_ops)
            if prestador_sel == "Outro (Digitar Manualmente)":
                prestador_final = "GUINCHEIRO AVULSO"
                tel_prestador_final = apenas_numeros_letras(st.text_input("WhatsApp do Guincheiro Avulso (DDD + Número):"))
            else:
                prestador_limpo = prestador_sel.replace("[EXATO - MESMO CEP] ", "").replace("[PRÓXIMO - MESMO BAIRRO] ", "").replace("[MESMA CIDADE] ", "")
                prestador_final = prestador_limpo.split(" - Tel:")[0]
                tel_prestador_final = apenas_numeros_letras(prestador_limpo.split(" - Tel:")[1].split("-")[0].strip())
            
            st.write("---")
            
            if is_excecao_flag:
                emp_match = df_empresas[df_empresas['nome'].str.upper() == empresa_os.upper()]
                resp_empresa = emp_match.iloc[0].get('responsavel', 'Responsável') if not emp_match.empty else 'Responsável'
                tel_responsavel = apenas_numeros_letras(emp_match.iloc[0].get('telefone', '')) if not emp_match.empty else ''
                if not tel_responsavel: tel_responsavel = tel_envio_link

                valor_pix_final_num = float(st.session_state.get("os_val_exc_num", 0.0))
                valor_pix_final_str = formatar_brl(valor_pix_final_num)
                valor_cobrado_os = valor_pix_final_str

                if valor_pix_final_num <= 0:
                    st.warning("Informe o Valor do Serviço Extra acima e clique em 'Confirmar Valor na Mensagem PIX' (ou aperte Enter) antes de enviar a cobrança no WhatsApp.")
                else:
                    st.markdown(f'<div class="info-box" style="padding:10px 14px;"><b>Valor confirmado na mensagem PIX:</b> R$ {valor_pix_final_str} &nbsp;|&nbsp; <b>Responsável:</b> {resp_empresa}</div>', unsafe_allow_html=True)

                texto_pix = (
                    f"🚨 *ATENDIMENTO DE EXCEÇÃO - AD RASTREAMENTO* 🚨\n\n"
                    f"Olá *{resp_empresa}* (Empresa: *{empresa_os}*),\n\n"
                    f"O acionamento de exceção para o veículo *{veiculo_desc_alvo}* - Placa: *{placa_alvo}* foi autorizado.\n\n"
                    f"📋 *Detalhes completos do Atendimento:*\n"
                    f"• Serviço: {tipo_servico} ({motivo_servico})\n"
                    f"• Onde pegar (Origem): {localizacao if localizacao else 'A informar'}\n"
                    f"• Onde deixar (Destino): {destino if destino else 'A informar'}\n"
                    f"• Motivo da Exceção: Limite Anual ou Carência de 60 dias atingida\n\n"
                    f"💰 *Valor do Serviço Extra:* R$ {valor_pix_final_str}\n\n"
                    f"⚠️ *Atenção:* O deslocamento do prestador será iniciado *somente após o envio do comprovante* de pagamento.\n\n"
                    f"📲 *DADOS PARA PAGAMENTO (PIX):*\n"
                    f"Chave PIX (CNPJ): *55496449000184*\n"
                    f"Nome: *AD Rastreamento Veicular LTDA*\n\n"
                    f"Envie o comprovante nesta conversa para despacharmos o socorro imediatamente!"
                )
                link_w_pix = f"https://api.whatsapp.com/send?phone=55{tel_responsavel}&text={urllib.parse.quote(texto_pix)}"
                if not tel_responsavel: st.warning("Nenhum telefone cadastrado para a empresa ou cliente. Cadastre no perfil para enviar diretamente.")
                st.markdown(f'<a href="{link_w_pix}" target="_blank" style="text-decoration: none;"><button style="background-color: #00bfa5; color: white; padding: 11px 20px; border: none; border-radius: 6px; font-weight: bold; margin-bottom: 8px; width: 100%; font-size: 13px;">PASSO EXTRA: Enviar Cobrança PIX (R$ {valor_pix_final_str}) para {resp_empresa}</button></a>', unsafe_allow_html=True)

            if st.button("Finalizar e Gerar OS", type="primary", key="btn_gerar_os_admin"):
                if not tel_prestador_final: st.error("O número de WhatsApp do guincheiro é obrigatório.")
                elif not localizacao: st.error("O Endereço de Origem é obrigatório.")
                else:
                    st.cache_data.clear()
                    df_os_live = ordenar_os_recentes(carregar_dados(FILE_OS, col_os))
                    placa_chk_live = apenas_numeros_letras(placa_alvo).upper()
                    dup_live = df_os_live[
                        (df_os_live['placa'].astype(str).apply(lambda x: apenas_numeros_letras(x).upper()) == placa_chk_live) &
                        (~df_os_live['status_os'].str.upper().isin(['ENCERRADO', 'CANCELADO']))
                    ]
                    if not dup_live.empty:
                        st.error(f"Bloqueado: a OS #{dup_live.iloc[0]['id']} já está aberta para a placa {placa_alvo}.")
                    else:
                        with st.spinner("Registrando OS e sincronizando com a nuvem..."):
                            nova_id = int(pd.to_numeric(df_os_live['id'], errors='coerce').max() + 1) if not df_os_live.empty else 1
                            hora_ab = obter_hora_str()
                            meta_inicial = {'sla_abertura': hora_ab}
                            if tipo_atendimento != "Cliente Cadastrado":
                                meta_inicial['status_pgto_prestador'] = 'Particular'
                                meta_inicial['status_pgto_particular'] = 'Pendente'
                            nova_os = pd.DataFrame([{
                                'id': str(nova_id), 'data_hora': hora_ab, 'cliente_id': str(cliente_id_os), 
                                'cliente_nome': str(cliente_nome_os).upper(), 'cliente_tel': tel_envio_link, 'placa': placa_alvo, 
                                'veiculo_desc': str(veiculo_desc_alvo).upper(), 'empresa': empresa_os, 'tipo_servico': tipo_servico, 
                                'motivo': motivo_servico, 'prestador': f"{prestador_final} | Telefone/Zap: {tel_prestador_final}", 
                                'localizacao': localizacao, 'destino': destino, 'obs': obs, 'status_os': "EM ATENDIMENTO", 
                                'plano_km': plano_km_os, 'valor_cobrado': valor_cobrado_os,
                                'motorista_nome': '', 'motorista_tel': '', 'fotos_vistoria': json.dumps(meta_inicial), 'assinatura_cliente': ''
                            }])
                            df_os_temp = pd.concat([df_os_live, nova_os], ignore_index=True)
                            sucesso, erro = salvar_dados(df_os_temp, FILE_OS)
                            if sucesso:
                                registrar_atividade(st.session_state.user, "NOVA OS", f"Abriu chamado {nova_id} para a placa {placa_alvo}")
                                st.success(f"Chamado Nº {nova_id} aberto. Redirecionando para Pendências...")
                                for k in ["os_busca_val", "os_cli_val", "os_loc_val", "os_bairro_orig_val", "os_cidade_orig_val", "os_cep_orig_val", "os_dest_val", "os_obs_val"]: st.session_state[k] = ""
                                st.session_state.os_val_exc_num = 0.0
                                time.sleep(1.5)
                                st.query_params["nav"] = f"Pendências ({qtd_pendencias + 1})"
                                st.rerun()
                            else: st.error(f"Erro ao salvar OS na nuvem: {erro}")
                # ===================================================================================
# INTERFACE 1: ADMIN MASTER (PARTE 4 - PENDÊNCIAS + TROCA RÁPIDA + EMPRESAS + CLIENTES 200KM + PRESTADORES)
# ===================================================================================
if st.session_state.perfil == "Admin":
    if aba_selecionada == aba_pendencias_nome:
        st.markdown(f'<div class="section-title">{aba_pendencias_nome} — Monitoramento, Vistoria e Custos da OS</div>', unsafe_allow_html=True)

        df_abertas = ordenar_os_recentes(df_os[~df_os['status_os'].str.upper().isin(['ENCERRADO', 'CANCELADO'])])
        
        if df_abertas.empty: 
            st.success("Nenhum chamado pendente no momento.")
        else:
            lista_abertas = []
            for _, r in df_abertas.iterrows():
                mot = f" | Resp: {r.get('motorista_nome')}" if r.get('motorista_nome') else ""
                lista_abertas.append(f"OS Nº: {r['id']} | Status: {r['status_os']} | Placa: {r.get('placa','N/D')} | {str(r.get('data_hora',''))[:16]}{mot}")
            
            os_sel_str = st.selectbox("Selecione o chamado para gerenciar, auditar ou lançar custos (mais recentes primeiro):", lista_abertas)
            os_id_alvo = os_sel_str.split("|")[0].replace("OS Nº:", "").strip()
            row_os = df_abertas[df_abertas['id'].astype(str) == os_id_alvo].iloc[0]
            status_dessa_os = str(row_os['status_os']).upper()
            prestador_info = str(row_os['prestador'])
            tel_prestador_final = prestador_info.split("Telefone/Zap: ")[1].strip() if "Telefone/Zap: " in prestador_info else ""
            
            tel_cliente_os = str(row_os.get('cliente_tel', ''))
            v_desc_wpp = str(row_os.get('veiculo_desc', 'N/D'))
            if "CARRO " in v_desc_wpp.upper() and any(m in v_desc_wpp.upper() for m in MARCAS_MOTO):
                v_desc_wpp = v_desc_wpp.replace("CARRO ", "MOTO ").replace("Carro ", "Moto ")
            
            if status_dessa_os == 'CONCLUÍDO':
                st.success("ATENÇÃO: O prestador enviou a foto de desembarque e marcou esta OS como CONCLUÍDA. Confira as fotos, lance o custo operacional abaixo e encerre a OS para liberar a pesquisa NPS.")
            
            obs_val = str(row_os.get('obs', ''))
            if obs_val.strip() == "" or obs_val.lower() == "nan": obs_val = "Nenhuma"

            meta_os = ler_meta_os(row_os)
            dt_ab_p, dt_ac_p, dt_em_p, dt_co_p = extrair_horarios_sla(row_os)
            fmt_p = lambda d: d.strftime("%d/%m %H:%M") if d else "—"

            trocas_os = meta_os.get('historico_trocas', [])
            trocas_html = ""
            if isinstance(trocas_os, list) and len(trocas_os) > 0:
                ult_tr = trocas_os[-1]
                trocas_html = f"<p style='margin: 6px 0; font-size: 12.5px; color:{COR_VERM_TXT};'><strong>Trocas de Prestador ({len(trocas_os)}):</strong> Última em {ult_tr.get('data_hora', '')[:16]} — {ult_tr.get('anterior', 'N/D')} para {ult_tr.get('novo', 'N/D')} ({ult_tr.get('motivo', '')})</p>"

            st.markdown(f"""
                <div class="dash-box" style="border-top: 4px solid #6A1B9A;">
                    <div class="dash-box-title">
                        <span>Ficha Operacional — OS #{row_os['id']} ({row_os.get('empresa', 'AD Rastreamento')})</span>
                        <span class="service-badge badge-red">{status_dessa_os}</span>
                    </div>
                    <p style="margin: 6px 0; font-size: 13.5px;"><strong>SLA:</strong> Abertura: <b>{fmt_p(dt_ab_p)}</b> &nbsp;|&nbsp; Aceite: <b>{fmt_p(dt_ac_p)}</b> &nbsp;|&nbsp; Embarque: <b>{fmt_p(dt_em_p)}</b> &nbsp;|&nbsp; Conclusão: <b>{fmt_p(dt_co_p)}</b></p>
                    <p style="margin: 6px 0; font-size: 13.5px;"><strong>Cliente:</strong> {row_os['cliente_nome']} &nbsp;|&nbsp; <strong>Veículo:</strong> {v_desc_wpp} &nbsp;|&nbsp; <strong>Placa:</strong> <span style="color:{COR_VERM_TXT}; font-weight:800;">{row_os.get('placa', '')}</span></p>
                    <p style="margin: 6px 0; font-size: 13.5px;"><strong>Origem:</strong> {row_os['localizacao']}</p>
                    <p style="margin: 6px 0; font-size: 13.5px;"><strong>Destino:</strong> {row_os['destino']}</p>
                    <p style="margin: 6px 0; font-size: 13.5px;"><strong>Base/Grupo Acionado:</strong> {prestador_info}</p>
                    <p style="margin: 6px 0; font-size: 13px; color:{COR_TEXTO_SEC};"><strong>Observações Extras:</strong> {obs_val}</p>
                    {trocas_html}
                </div>
            """, unsafe_allow_html=True)
            
            motorista_n = str(row_os.get('motorista_nome', '')).strip()
            if motorista_n and motorista_n.lower() != 'nan':
                st.markdown(f'<div class="alert-box alert-success" style="padding: 10px; margin-top: 10px;"><b>Prestador Responsável:</b> {motorista_n} | <b>Telefone:</b> {row_os.get("motorista_tel", "").split("|")[0]}</div>', unsafe_allow_html=True)

            # =====================================================================
            # TROCA RÁPIDA DE PRESTADOR (DESBLOQUEIA LINK E MANTÉM SLA ORIGINAL)
            # =====================================================================
            if status_dessa_os != 'CONCLUÍDO':
                with st.expander("Trocar Prestador / Reenviar OS", expanded=False):
                    if status_dessa_os == 'EM TRÂNSITO':
                        st.warning("Atenção: esta OS já está em trânsito. Utilize a troca apenas em caso de imprevisto ou transbordo.")
                    st.caption("Ao confirmar, o chamado volta para EM ATENDIMENTO, o aceite anterior é liberado (mantendo o horário original de abertura no SLA) e o botão de WhatsApp abaixo é atualizado automaticamente para o novo prestador.")

                    lista_troca_ops = ["Outro (Digitar Manualmente)"]
                    if not df_prestadores.empty:
                        df_p_troca = df_prestadores[(df_prestadores['status'] == 'Ativo') & (df_prestadores['homologado'] == 'Aprovado')].copy()
                        if not df_p_troca.empty:
                            df_p_troca = df_p_troca.sort_values(by=['est', 'cidade', 'nome'])
                            for _, rp_t in df_p_troca.iterrows():
                                lista_troca_ops.append(f"{str(rp_t['nome'])} - Tel: {str(rp_t['telefone'])} - Bairro: {str(rp_t.get('bairro','N/D')).upper()} - {str(rp_t['cidade']).upper()}/{str(rp_t['est']).upper()}")

                    novo_prest_sel = st.selectbox("Selecione o novo prestador:", lista_troca_ops, key=f"sel_troca_prest_{os_id_alvo}")

                    if novo_prest_sel == "Outro (Digitar Manualmente)":
                        c_tr1, c_tr2 = st.columns(2)
                        novo_prest_nome = c_tr1.text_input("Nome do Novo Prestador / Base:", value="GUINCHEIRO AVULSO", key=f"inp_tr_nome_{os_id_alvo}").strip().upper()
                        novo_tel_prest = apenas_numeros_letras(c_tr2.text_input("WhatsApp do Novo Prestador (DDD + Número):", key=f"inp_tr_tel_{os_id_alvo}"))
                    else:
                        novo_prest_nome = novo_prest_sel.split(" - Tel:")[0].strip().upper()
                        novo_tel_prest = apenas_numeros_letras(novo_prest_sel.split(" - Tel:")[1].split("-")[0].strip())

                    motivo_troca = st.selectbox(
                        "Motivo da Troca:",
                        ["Atraso / Sem retorno", "Desistência do prestador", "Indisponibilidade de plataforma", "Erro na seleção inicial", "Outro"],
                        key=f"sel_tr_motivo_{os_id_alvo}"
                    )

                    if st.button("Confirmar Troca de Prestador", key=f"btn_conf_troca_{os_id_alvo}", type="primary", use_container_width=True):
                        if not novo_tel_prest:
                            st.error("Informe o WhatsApp do novo prestador para concluir a troca.")
                        elif not novo_prest_nome:
                            st.error("Informe o nome do novo prestador.")
                        else:
                            with st.spinner("Atualizando prestador e liberando link da OS..."):
                                anterior_nome = motorista_n if (motorista_n and motorista_n.lower() != 'nan') else prestador_info.split('|')[0].strip()
                                hist_trocas = list(meta_os.get('historico_trocas', [])) if isinstance(meta_os.get('historico_trocas', []), list) else []
                                hist_trocas.append({
                                    'data_hora': obter_hora_str(),
                                    'anterior': anterior_nome,
                                    'novo': novo_prest_nome,
                                    'motivo': motivo_troca
                                })

                                novo_pix_troca = ""
                                if not df_prestadores.empty:
                                    m_novo_p = df_prestadores[
                                        (df_prestadores['telefone'].apply(apenas_numeros_letras) == novo_tel_prest) |
                                        (df_prestadores['nome'].str.strip().str.upper() == novo_prest_nome)
                                    ]
                                    if not m_novo_p.empty:
                                        novo_pix_troca = ler_pix_prestador(m_novo_p.iloc[0])

                                novos_meta_troca = {
                                    'sla_aceite': '',
                                    'pix_prestador_os': novo_pix_troca,
                                    'historico_trocas': hist_trocas
                                }
                                meta_pos_troca = mesclar_meta_os(row_os.get('fotos_vistoria', ''), novos_meta_troca)
                                novo_prest_str = f"{novo_prest_nome} | Telefone/Zap: {novo_tel_prest}"

                                df_os.loc[
                                    df_os['id'].astype(str) == os_id_alvo,
                                    ['prestador', 'status_os', 'motorista_nome', 'motorista_tel', 'fotos_vistoria']
                                ] = [novo_prest_str, 'EM ATENDIMENTO', '', '', meta_pos_troca]

                                ok_tr, err_tr = salvar_dados(df_os, FILE_OS)
                                if ok_tr:
                                    registrar_atividade(
                                        st.session_state.user,
                                        "TROCA DE PRESTADOR",
                                        f"OS #{os_id_alvo} (Placa: {row_os.get('placa', '')}) alterada de {anterior_nome} para {novo_prest_nome} | Motivo: {motivo_troca}"
                                    )
                                    st.success(f"Prestador alterado para {novo_prest_nome}. O botão de WhatsApp abaixo já foi atualizado.")
                                    time.sleep(1.2)
                                    st.rerun()
                                else:
                                    st.error(f"Erro ao salvar troca na nuvem: {err_tr}")
            
            doc_cliente_nps = meta_os.get('doc_cliente', 'N/D')
            if any(meta_os.get(k) for k in ['frente', 'traseira', 'lat_dir', 'lat_esq']):
                st.markdown('<div class="inspection-reader-header"><span>Vistoria Fotográfica (Embarque)</span><span>4 ÂNGULOS</span></div>', unsafe_allow_html=True)
                st.markdown('<div class="inspection-reader-body">', unsafe_allow_html=True)
                cf1, cf2, cf3, cf4 = st.columns(4)
                if meta_os.get('frente'): cf1.image(base64.b64decode(meta_os['frente']), caption="1. Frente", use_container_width=True)
                if meta_os.get('traseira'): cf2.image(base64.b64decode(meta_os['traseira']), caption="2. Traseira", use_container_width=True)
                if meta_os.get('lat_dir'): cf3.image(base64.b64decode(meta_os['lat_dir']), caption="3. Lat. Direita", use_container_width=True)
                if meta_os.get('lat_esq'): cf4.image(base64.b64decode(meta_os['lat_esq']), caption="4. Lat. Esquerda", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            if meta_os.get('foto_desembarque'):
                st.markdown('<div class="inspection-reader-header"><span>Comprovante de Desembarque (Entrega no Destino)</span><span>CONFERÊNCIA</span></div>', unsafe_allow_html=True)
                st.markdown('<div class="inspection-reader-body">', unsafe_allow_html=True)
                try: st.image(base64.b64decode(meta_os['foto_desembarque']), caption="Veículo descarregado no destino", width=360)
                except: pass
                st.markdown('</div>', unsafe_allow_html=True)
                
            ass_str = str(row_os.get('assinatura_cliente', ''))
            if ass_str and ass_str.lower() not in ['nan', 'none', '']:
                st.markdown(f'<div class="inspection-reader-header"><span>Assinatura Digital do Condutor</span><span>DOC: {doc_cliente_nps}</span></div>', unsafe_allow_html=True)
                st.markdown('<div class="inspection-reader-body">', unsafe_allow_html=True)
                try: st.image(base64.b64decode(ass_str), width=240)
                except: pass
                st.markdown('</div>', unsafe_allow_html=True)

            # =====================================================================
            # LANÇAMENTO DE CUSTO DA OS (CHAVE PIX INTELIGENTE + STATUS PARTICULAR)
            # =====================================================================
            prest_id_os, pix_cad_os = localizar_prestador_os(row_os, df_prestadores)
            pix_salvo_os = pix_cad_os or str(meta_os.get('pix_prestador_os', '')).strip()

            c_saida_atual = formatar_moeda_float(meta_os.get('custo_saida', 0.0))
            c_km_atual = formatar_moeda_float(meta_os.get('custo_km_exc', 0.0))
            c_ped_atual = formatar_moeda_float(meta_os.get('custo_pedagio', 0.0))
            opcoes_st_pg = ["A Pagar", "Pago", "Particular"]
            st_pg_raw = str(meta_os.get('status_pgto_prestador', '')).strip()
            if st_pg_raw in opcoes_st_pg:
                st_pg_atual = st_pg_raw
            else:
                st_pg_atual = "Particular" if eh_os_particular(row_os) else "A Pagar"
            obs_c_atual = str(meta_os.get('obs_custo', '')).strip()
            c_tot_prev = c_saida_atual + c_km_atual + c_ped_atual

            with st.expander(f"Custo Operacional desta OS (Prestador) — Total Atual: R$ {c_tot_prev:.2f} | Status: {st_pg_atual}", expanded=(status_dessa_os == 'CONCLUÍDO')):
                with st.form(f"form_custo_os_pend_{os_id_alvo}"):
                    cc1, cc2, cc3 = st.columns(3)
                    v_saida_in = cc1.number_input("Valor Saída / Base (R$):", min_value=0.0, value=float(c_saida_atual), step=10.0, format="%.2f")
                    v_km_in = cc2.number_input("KM Excedente (R$):", min_value=0.0, value=float(c_km_atual), step=5.0, format="%.2f")
                    v_ped_in = cc3.number_input("Pedágio / Extras (R$):", min_value=0.0, value=float(c_ped_atual), step=5.0, format="%.2f")

                    cc4, cc5 = st.columns([2, 1])
                    if pix_salvo_os:
                        cc4.markdown(f'<div class="info-box" style="padding:8px 12px; margin:0;"><b>Chave PIX cadastrada:</b> {pix_salvo_os}</div>', unsafe_allow_html=True)
                        pix_os_in = pix_salvo_os
                    else:
                        pix_os_in = cc4.text_input("Chave PIX do Prestador (salva no cadastro automaticamente):", value="", placeholder="CPF, CNPJ, E-mail ou Celular")

                    st_pg_in = cc5.selectbox("Status Pagamento:", opcoes_st_pg, index=opcoes_st_pg.index(st_pg_atual))
                    obs_custo_in = st.text_input("Observação do Pagamento (Opcional):", value=obs_c_atual, placeholder="Ex: 15km excedentes negociados / comprovante enviado")

                    if st.form_submit_button("Salvar Custo da OS no Financeiro", use_container_width=True):
                        with st.spinner("Gravando custo operacional no Supabase..."):
                            total_custo_calc = round(v_saida_in + v_km_in + v_ped_in, 2)
                            pix_final_save = pix_os_in.strip()

                            if prest_id_os and not pix_cad_os and pix_final_save:
                                row_pr_ant = df_prestadores[df_prestadores['id'].astype(str) == str(prest_id_os)].iloc[0]
                                df_prestadores.loc[df_prestadores['id'].astype(str) == str(prest_id_os), 'frota'] = empacotar_pix_prestador(row_pr_ant.get('frota', ''), pix_final_save)
                                salvar_dados(df_prestadores, FILE_PRESTADORES)

                            novos_c = {
                                'custo_saida': f"{v_saida_in:.2f}",
                                'custo_km_exc': f"{v_km_in:.2f}",
                                'custo_pedagio': f"{v_ped_in:.2f}",
                                'custo_total': f"{total_custo_calc:.2f}",
                                'pix_prestador_os': pix_final_save,
                                'status_pgto_prestador': st_pg_in,
                                'obs_custo': obs_custo_in.strip()
                            }
                            if st_pg_in == "Pago" and not meta_os.get('data_pgto_prestador'):
                                novos_c['data_pgto_prestador'] = obter_hora_brasilia().strftime("%d/%m/%Y %H:%M")
                            elif st_pg_in != "Pago":
                                novos_c['data_pgto_prestador'] = ""

                            meta_upd = mesclar_meta_os(row_os.get('fotos_vistoria', ''), novos_c)
                            df_os.loc[df_os['id'].astype(str) == os_id_alvo, 'fotos_vistoria'] = meta_upd
                            sucesso_c, erro_c = salvar_dados(df_os, FILE_OS)
                            if sucesso_c:
                                registrar_atividade(st.session_state.user, "CUSTO OS", f"Lançou custo de R$ {total_custo_calc:.2f} na OS #{os_id_alvo} ({st_pg_in})")
                                st.success(f"Custo de R$ {total_custo_calc:.2f} salvo na OS #{os_id_alvo}.")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"Erro ao salvar custo: {erro_c}")
            
            is_blindado_msg = "SIM 🛡 (Atenção ao peso/capacidade da plataforma)" if "BLINDADO" in v_desc_wpp.upper() else "NÃO"
            empresa_nome_wpp = str(row_os.get('empresa', 'AD Rastreamento')).upper()
            if empresa_nome_wpp == 'CLIENTE PARTICULAR (AVULSO)': empresa_nome_wpp = 'AD RASTREAMENTO'
            
            link_nps_cliente = f"https://ad-central-mrssupqbb9ux69bi4qgisa.streamlit.app/?portal=nps&os={os_id_alvo}"
            texto_w_nps = f"Olá! Seu atendimento pela *{empresa_nome_wpp} — Central de Assistência 24 Horas* foi concluído.\n\nComo foi sua experiência? Conte para nós em menos de 30 segundos avaliando neste link: ⭐ {link_nps_cliente}"
            
            valor_str = ""
            val_cobrado = str(row_os.get('valor_cobrado', '0,00')).strip()
            is_avulso = "AVULSO" in str(row_os.get('cliente_id', '')).upper() or str(row_os.get('plano_km', '')).strip().lower() == "particular"
            
            if is_avulso and val_cobrado not in ['0,00', '0.00', '0', '']:
                valor_str = f"*Valor Particular:* R$ {val_cobrado}\n"
                
            texto_whatsapp = (f"*{empresa_nome_wpp} - CENTRAL DE ASSISTÊNCIA 24 HORAS*\n"
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
                    st.markdown(f'<a href="{link_w}" target="_blank"><button style="background-color: #25D366; color: white; padding: 10px 20px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; width: 100%; font-size: 13px;">1. Enviar OS para o Prestador (WhatsApp)</button></a>', unsafe_allow_html=True)
                else:
                    st.info("OS concluída pelo prestador. Confira a foto de entrega e encerre ao lado.")
            with col_btn2:
                texto_btn_encerrar = "Auditar e Encerrar OS no Sistema" if status_dessa_os == 'CONCLUÍDO' else "Encerrar OS no Sistema"
                if st.button(texto_btn_encerrar, key="btn_encerrar_os_adm", type="primary", use_container_width=True):
                    with st.spinner("Encerrando OS e abrindo WhatsApp para envio de NPS..."):
                        meta_enc = ler_meta_os(row_os)
                        if not meta_enc.get('sla_conclusao'):
                            meta_enc_str = mesclar_meta_os(row_os.get('fotos_vistoria', ''), {'sla_conclusao': obter_hora_str()})
                            df_os.loc[df_os['id'].astype(str) == os_id_alvo, ['status_os', 'fotos_vistoria']] = ["ENCERRADO", meta_enc_str]
                        else:
                            df_os.loc[df_os['id'].astype(str) == os_id_alvo, 'status_os'] = "ENCERRADO"
                        sucesso, erro = salvar_dados(df_os, FILE_OS)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "ENCERRAMENTO OS", f"Finalizou o chamado {os_id_alvo}")
                            st.success("OS encerrada com sucesso. O WhatsApp do cliente abrirá em nova aba.")
                            
                            js_auto_open = f"""
                            <script>
                                window.open("{link_w_cli_nps}", "_blank");
                            </script>
                            """
                            components.html(js_auto_open, height=0, width=0)
                            
                            time.sleep(2.5)
                            st.rerun()
                        else: st.error(f"Erro na nuvem: {erro}")

    elif aba_selecionada == "Empresas":
        st.markdown('<div class="section-title">Empresas Parceiras</div>', unsafe_allow_html=True)
        if "aba_emp" not in st.session_state: st.session_state.aba_emp = "Listar"
        opcoes_radio_emp = ["Listar", "Incluir Nova", "Editar", "Excluir"]
        idx_radio_emp = opcoes_radio_emp.index(st.session_state.aba_emp) if st.session_state.aba_emp in opcoes_radio_emp else 0
        opcao_emp = st.radio("Ação Empresas:", opcoes_radio_emp, horizontal=True, index=idx_radio_emp)
        st.session_state.aba_emp = opcao_emp
        
        if opcao_emp == "Listar":
            busca_emp_lista = st.text_input("Buscar Empresa (Nome ou CNPJ):")
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
            est_e = c2.selectbox("Estado (UF) da Sede:", options=ESTADOS_BR, index=ESTADOS_BR.index("RN"))
            
            c_v1, c_v2, c_v3 = st.columns(3)
            stat_e = c_v1.selectbox("Status Parceria:", ["Ativo", "Inativo"], index=0)
            modo_fat_e = c_v2.selectbox("Modo de Faturamento:", MODOS_FATURAMENTO, index=0)
            dia_v_e = c_v3.selectbox("Dia do Vencimento:", OPCOES_DIAS_VENC, index=OPCOES_DIAS_VENC.index("30"))

            if st.button("Salvar Nova Empresa"):
                cnpj = apenas_numeros_letras(cnpj_raw)
                if not cnpj or not n_emp_in: st.error("CNPJ e Nome da Empresa são obrigatórios.")
                else:
                    with st.spinner("Salvando empresa..."):
                        dt_ativacao = datetime.now().strftime("%Y-%m-%d") if stat_e == 'Ativo' else ''
                        novo_e = pd.DataFrame([{'cnpj': cnpj, 'nome': n_emp_in.upper(), 'responsavel': resp_in.upper(), 'telefone': apenas_numeros_letras(tel_e_raw), 'email': mail_in, 'est': est_e, 'status': stat_e, 'modo_faturamento': modo_fat_e, 'dia_vencimento': dia_v_e, 'data_ativacao': dt_ativacao}])
                        df_empresas_temp = pd.concat([df_empresas, novo_e], ignore_index=True)
                        sucesso, erro = salvar_dados(df_empresas_temp, FILE_EMPRESAS)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "NOVA EMPRESA", f"Cadastrou a empresa {n_emp_in.upper()} (CNPJ: {cnpj})")
                            st.success("Empresa cadastrada com sucesso."); st.session_state.aba_emp = "Listar"; time.sleep(1); st.rerun()
                        else:
                            st.error(f"Erro na nuvem: {erro}")
        elif opcao_emp == "Editar":
            if df_empresas.empty: st.warning("Nenhuma empresa cadastrada.")
            else:
                opcoes_emp = {str(r['cnpj']): f"{str(r['nome']).upper()} | CNPJ: {str(r['cnpj'])}" for _, r in df_empresas.iterrows()}
                e_target = st.selectbox("Selecione a Empresa para Editar:", options=[""] + list(opcoes_emp.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_emp[x])
                if e_target != "":
                    dados_e_ant = df_empresas[df_empresas['cnpj'].astype(str) == e_target].iloc[0]
                    c1, c2 = st.columns(2)
                    n_emp_in = c1.text_input("Nome da Empresa:", value=dados_e_ant['nome'])
                    cnpj_raw = c2.text_input("CNPJ da Empresa:", value=dados_e_ant['cnpj'])
                    resp_in = c1.text_input("Nome do Responsável:", value=dados_e_ant['responsavel'])
                    tel_e_raw = c2.text_input("Telefone da Central 24h:", value=dados_e_ant['telefone'])
                    mail_in = c1.text_input("E-mail corporativo:", value=dados_e_ant['email'])
                    idx_est_e = ESTADOS_BR.index(str(dados_e_ant['est']).upper()) if str(dados_e_ant['est']).upper() in ESTADOS_BR else ESTADOS_BR.index("RN")
                    est_e = c2.selectbox("Estado (UF) da Sede:", options=ESTADOS_BR, index=idx_est_e)
                    
                    c_v1, c_v2, c_v3 = st.columns(3)
                    stat_ant = str(dados_e_ant.get('status', 'Inativo')).strip()
                    stat_e = c_v1.selectbox("Status Parceria:", ["Ativo", "Inativo"], index=["Ativo", "Inativo"].index(stat_ant) if stat_ant in ["Ativo", "Inativo"] else 0)
                    
                    modo_fat_ant = str(dados_e_ant.get('modo_faturamento', 'Tradicional')).strip()
                    idx_modo_fat = MODOS_FATURAMENTO.index(modo_fat_ant) if modo_fat_ant in MODOS_FATURAMENTO else 0
                    modo_fat_e = c_v2.selectbox("Modo de Faturamento:", MODOS_FATURAMENTO, index=idx_modo_fat)
                    
                    venc_ant = str(dados_e_ant.get('dia_vencimento', '30')).strip()
                    if not venc_ant or venc_ant == 'nan': venc_ant = "30"
                    
                    opcoes_dias_edit = OPCOES_DIAS_VENC if venc_ant in OPCOES_DIAS_VENC else OPCOES_DIAS_VENC + [venc_ant]
                    idx_venc = opcoes_dias_edit.index(venc_ant)
                    dia_v_e = c_v3.selectbox("Dia do Vencimento:", opcoes_dias_edit, index=idx_venc)

                    if st.button("Salvar Alterações"):
                        cnpj = apenas_numeros_letras(cnpj_raw)
                        if not cnpj or not n_emp_in: st.error("CNPJ e Nome da Empresa são obrigatórios.")
                        else:
                            with st.spinner("Atualizando dados da empresa..."):
                                dt_ativacao = str(dados_e_ant.get('data_ativacao', ''))
                                
                                if stat_ant != 'Ativo' and stat_e == 'Ativo':
                                    dt_ativacao = datetime.now().strftime("%Y-%m-%d")
                                    dia_v_e = str(datetime.now().day)
                                elif modo_fat_ant == 'Tradicional' and modo_fat_e != 'Tradicional':
                                    dt_ativacao = datetime.now().strftime("%Y-%m-%d") 
                                    dia_v_e = str(datetime.now().day) 
                                    st.info(f"Migração de plano detectada. O ciclo de 30 dias foi ajustado a partir de hoje ({dt_ativacao}).")
                                    
                                df_empresas.loc[df_empresas['cnpj'] == e_target, ['cnpj', 'nome','responsavel','telefone','email','est','status', 'modo_faturamento', 'dia_vencimento', 'data_ativacao']] = [cnpj, n_emp_in.upper(), resp_in.upper(), apenas_numeros_letras(tel_e_raw), mail_in, est_e, stat_e, modo_fat_e, dia_v_e, dt_ativacao]
                                sucesso, erro = salvar_dados(df_empresas, FILE_EMPRESAS)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EDIÇÃO EMPRESA", f"Editou a empresa {n_emp_in.upper()} (Plano alterado para {modo_fat_e})")
                                    st.success("Empresa atualizada com sucesso."); st.session_state.aba_emp = "Listar"; time.sleep(2.5); st.rerun()
                                else: st.error(f"Erro na nuvem: {erro}")
        elif opcao_emp == "Excluir":
            if df_empresas.empty: st.warning("Nenhuma empresa cadastrada.")
            else:
                opcoes_emp = {str(r['cnpj']): f"{str(r['nome']).upper()} | CNPJ: {str(r['cnpj'])}" for _, r in df_empresas.iterrows()}
                e_target_del = st.selectbox("Selecione a Empresa para Excluir:", options=[""] + list(opcoes_emp.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_emp[x])
                if e_target_del != "":
                    if "emp_del_confirm" not in st.session_state: st.session_state.emp_del_confirm = None
                    if st.session_state.emp_del_confirm != e_target_del:
                        if st.button("Excluir permanentemente"): st.session_state.emp_del_confirm = e_target_del; st.rerun()
                    if st.session_state.get("emp_del_confirm") == e_target_del:
                        st.error(f"Tem certeza que deseja excluir a empresa **{opcoes_emp[e_target_del]}**?")
                        col_sim, col_nao = st.columns(2)
                        if col_sim.button("Confirmar exclusão"):
                            with st.spinner("Excluindo empresa do Supabase..."):
                                emp_apagada = df_empresas[df_empresas['cnpj'] == e_target_del].iloc[0]
                                detalhes_emp = f"Apagou a empresa -> CNPJ: {e_target_del} | Nome: {emp_apagada['nome']} | Resp: {emp_apagada.get('responsavel', '')}"
                                deletar_registro_banco(FILE_EMPRESAS, "cnpj", str(e_target_del))
                                df_empresas = df_empresas[df_empresas['cnpj'] != e_target_del]
                                registrar_atividade(st.session_state.user, "EXCLUSÃO EMPRESA", detalhes_emp)
                                st.success("Empresa excluída permanentemente."); st.session_state.emp_del_confirm = None; st.session_state.aba_emp = "Listar"; time.sleep(1); st.rerun()
                        if col_nao.button("Cancelar"): st.session_state.emp_del_confirm = None; st.rerun()

    elif aba_selecionada == "Clientes":
        st.markdown('<div class="section-title">Gestão de Clientes</div>', unsafe_allow_html=True)
        if "aba_cli" not in st.session_state: st.session_state.aba_cli = "Listar"
        opcoes_radio = ["Listar", "Incluir Novo", "Importação em Lote", "Editar", "Excluir"]
        idx_radio = opcoes_radio.index(st.session_state.aba_cli) if st.session_state.aba_cli in opcoes_radio else 0
        opcao_cli = st.radio("Ação Clientes:", opcoes_radio, horizontal=True, index=idx_radio)
        st.session_state.aba_cli = opcao_cli
        
        if opcao_cli == "Listar":
            busca_cli_lista = st.text_input("Buscar Cliente (Nome, Placa ou CPF):")
            if df_clientes.empty: st.info("Nenhum cliente cadastrado.")
            else: 
                df_view_cli = df_clientes.copy()
                expandir_pastas = False 
                if busca_cli_lista:
                    expandir_pastas = True 
                    df_view_cli = df_view_cli[df_view_cli['nome'].str.contains(busca_cli_lista, case=False, na=False) | df_view_cli['pla'].str.contains(busca_cli_lista, case=False, na=False) | df_view_cli['cpf'].str.contains(busca_cli_lista, case=False, na=False) | df_view_cli['veiculos_lista'].str.lower().str.contains(busca_cli_lista.lower(), na=False)]
                def formatar_historico(c_id):
                    if df_os.empty: return "Nenhum Serviço Solicitado"
                    os_cli = ordenar_os_recentes(df_os[df_os['cliente_id'].astype(str).str.strip() == str(c_id).strip()])
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
                        with st.expander(f"Clientes da Empresa: {nome_emp}", expanded=expandir_pastas):
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
                            cli_sel = st.selectbox(f"Selecione um cliente da {nome_emp} para ver a Ficha Completa:", cli_opcoes, index=idx_sel_admin, key=widget_key_admin)
                            st.session_state[key_sel_admin] = cli_sel
                            if cli_sel != "":
                                cli_data = df_emp_filtrada[df_emp_filtrada['nome'] == cli_sel].iloc[0]
                                dt_cad_cliente = str(cli_data.get('data_cadastro', ''))
                                inicio_cli, fim_cli = obter_ciclo_contrato_anual(dt_cad_cliente)
                                st.markdown(f"### Ficha do Cliente: {cli_data['nome']}")
                                c1, c2 = st.columns(2)
                                c1.write(f"**CPF/CNPJ:** {cli_data['cpf']}"); c1.write(f"**Telefone:** {cli_data['tel']}"); c1.write(f"**Plano Contratado:** {cli_data.get('plano_km', 'N/D')}")
                                c2.write(f"**Endereço:** {cli_data.get('endereco', 'N/D')}, {cli_data.get('bairro', 'N/D')} - {cli_data.get('cidade', 'N/D')}/{cli_data.get('est', 'N/D')}"); c2.write(f"**Status:** {cli_data['status']}")
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
                                    placa_sel_ficha = st.selectbox("Selecione a Placa para consultar o Saldo Operacional:", lista_frota_ficha, key=f"sel_placa_{emp}")
                                    st.write(f"**Saldo de Limites da Placa {placa_sel_ficha} ({inicio_cli.strftime('%d/%m/%Y')} a {fim_cli.strftime('%d/%m/%Y')}):**")
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
                                
                                if st.button("Fechar Ficha", key=f"btn_close_{emp}"):
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
            st.write("**Frota do Cliente (Tabela Interativa)**")
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
            
            opcoes_km_cli, msg_km_cli = obter_opcoes_km_plano(modo_fat_selecionado)
            if msg_km_cli:
                st.info(f"Empresa {emp}: {msg_km_cli}")

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
                            st.success("Cliente cadastrado com sucesso.")
                            for k in ["cli_inc_nome", "cli_inc_cpf", "cli_inc_tel", "cli_inc_end", "cli_inc_bairro", "cli_inc_cid", "cli_inc_cep"]: st.session_state[k] = ""
                            st.session_state.aba_cli = "Listar"
                            time.sleep(1); st.rerun()
                        else:
                            st.error(f"Erro ao salvar cliente na nuvem: {erro}")
                        
        elif opcao_cli == "Importação em Lote":
            st.info("Envie o arquivo CSV do parceiro. O sistema identificará automaticamente as colunas de cliente, placa, tipo e blindagem.")
            lista_empresas_disponiveis = [str(e['nome']).upper() for _, e in df_empresas.iterrows()] if not df_empresas.empty else ["NENHUMA EMPRESA CADASTRADA"]
            empresa_selecionada = st.selectbox("Empresa Vinculada para esta importação:", options=lista_empresas_disponiveis)
            
            modo_fat_lote = "Tradicional"
            if not df_empresas.empty:
                dados_emp_lote = df_empresas[df_empresas['nome'].str.upper() == empresa_selecionada.upper()]
                if not dados_emp_lote.empty:
                    modo_fat_lote = dados_emp_lote.iloc[0].get('modo_faturamento', 'Tradicional')
            
            opcoes_km_lote, msg_km_lote = obter_opcoes_km_plano(modo_fat_lote)
            if msg_km_lote:
                st.info(f"Empresa {empresa_selecionada}: {msg_km_lote}")

            c_imp1, c_imp2, c_imp3 = st.columns(3)
            plano_padrao = c_imp1.selectbox("Plano Padrão:", options=opcoes_km_lote, index=0)
            est_padrao = c_imp2.selectbox("Estado (UF) Padrão:", options=ESTADOS_BR, index=ESTADOS_BR.index("RN"))
            data_cad_padrao = c_imp3.date_input("Data de Cadastro Padrão:", value=datetime.now())

            arquivo_csv_upload = st.file_uploader("Selecione o arquivo CSV da frota", type=["csv"])
            
            if arquivo_csv_upload is not None:
                try:
                    try: df_import = pd.read_csv(arquivo_csv_upload, sep=None, engine='python', encoding='utf-8')
                    except: 
                        arquivo_csv_upload.seek(0)
                        df_import = pd.read_csv(arquivo_csv_upload, sep=None, engine='python', encoding='latin1')
                    
                    if not df_import.empty:
                        st.markdown("##### Mapeamento Automático de Colunas")
                        colunas_csv = [str(c).strip().lower() for c in df_import.columns]
                        
                        mapa_buscas = {
                            "nome": ["nome", "cliente", "razao", "razão", "proprietario", "proprietário", "empresa", "cadastro", "usuario", "titular", "associado", "condutor"],
                            "cpf": ["cpf", "cnpj", "documento", "doc", "identificacao", "cgc", "cic"],
                            "tel": ["tel", "telefone", "celular", "whatsapp", "contato", "fone", "cel", "zap", "movel"],
                            "endereco": ["end", "endereço", "endereco", "rua", "logradouro", "avenida", "local"],
                            "bairro": ["bairro", "brr", "distrito"],
                            "cidade": ["cidade", "municipio", "município", "localidade"],
                            "cep": ["cep", "c.e.p", "postal", "codigo postal"],
                            "placa": ["placa", "mercosul", "plano", "veiculo_placa", "placas"],
                            "modelo": ["modelo", "veiculo", "veículo", "carro", "marca", "ano", "descricao", "ano/modelo"],
                            "tipo": ["tipo", "categoria", "classificacao", "classificação", "especie", "porte", "segmento", "tipo_veiculo"],
                            "blindado": ["blindado", "blindagem", "armored", "blind", "protecao"]
                        }
                        
                        colunas_encontradas = {}
                        for campo_sistema, sinonimos in mapa_buscas.items():
                            colunas_encontradas[campo_sistema] = None
                            for idx_col, col_name in enumerate(colunas_csv):
                                if any(sin in col_name for sin in sinonimos):
                                    colunas_encontradas[campo_sistema] = df_import.columns[idx_col]
                                    break
                                    
                        cols_cols = st.columns(3)
                        i = 0
                        for k, v in colunas_encontradas.items():
                            status_map = f"OK (`{v}`)" if v else "Não localizada"
                            cols_cols[i % 3].write(f"**{k.upper()}:** {status_map}")
                            i += 1
                            
                        st.write("---")
                        if st.button("Iniciar Importação em Lote", type="primary"):
                            if colunas_encontradas['nome'] is None or colunas_encontradas['placa'] is None:
                                st.error("O sistema não conseguiu identificar automaticamente as colunas de NOME e PLACA.")
                            else:
                                with st.spinner("Agrupando veículos e salvando clientes no sistema..."):
                                    df_import = df_import.fillna("")
                                    novos_clientes = []
                                    id_counter = int(df_clientes['id'].astype(float).max() + 1) if not df_clientes.empty else 1
                                    
                                    col_nome = colunas_encontradas['nome']
                                    col_cpf = colunas_encontradas['cpf']
                                    agrupador = col_cpf if col_cpf else col_nome
                                    
                                    for key, group in df_import.groupby(agrupador):
                                        row_base = group.iloc[0]
                                        nome_cli = str(row_base[col_nome]).strip().upper()
                                        if not nome_cli: continue
                                        
                                        cpf_cli = apenas_numeros_letras(str(row_base[col_cpf])) if col_cpf else ""
                                        tel_cli = apenas_numeros_letras(str(row_base[colunas_encontradas['tel']])) if colunas_encontradas['tel'] else ""
                                        end_cli = str(row_base[colunas_encontradas['endereco']]).strip() if colunas_encontradas['endereco'] else ""
                                        bairro_cli = str(row_base[colunas_encontradas['bairro']]).strip().upper() if colunas_encontradas['bairro'] else ""
                                        cid_cli = str(row_base[colunas_encontradas['cidade']]).strip().upper() if colunas_encontradas['cidade'] else ""
                                        cep_cli = apenas_numeros_letras(str(row_base[colunas_encontradas['cep']])) if colunas_encontradas['cep'] else ""
                                        
                                        frota_lista = []
                                        for _, v_row in group.iterrows():
                                            placa_v = str(v_row[colunas_encontradas['placa']]).strip().upper().replace("-", "").replace(" ", "")
                                            if len(placa_v) >= 6:
                                                mod_v = str(v_row[colunas_encontradas['modelo']]).strip() if colunas_encontradas['modelo'] else "VEÍCULO"
                                                tipo_v = str(v_row[colunas_encontradas['tipo']]).strip().capitalize() if colunas_encontradas.get('tipo') else "Carro"
                                                blindado_v = False
                                                if colunas_encontradas.get('blindado'):
                                                    val_blind = str(v_row[colunas_encontradas['blindado']]).strip().lower()
                                                    if val_blind in ['sim', 's', 'true', '1', 'y', 'yes', 'x', 'blindado']:
                                                        blindado_v = True
                                                frota_lista.append({"Tipo": tipo_v, "Modelo/Ano": mod_v, "Placa": placa_v, "Blindado": blindado_v})
                                                
                                        if not frota_lista: continue 
                                        
                                        json_frota = json.dumps(frota_lista)
                                        pla_prin = frota_lista[0]['Placa']
                                        vei_prin = frota_lista[0]['Modelo/Ano']
                                        
                                        novos_clientes.append({
                                            'id': str(id_counter), 'nome': nome_cli, 'cpf': cpf_cli, 'tel': tel_cli, 'endereco': end_cli, 'bairro': bairro_cli, 'cidade': cid_cli, 'cep': cep_cli, 'plano_km': plano_padrao, 'vei': vei_prin, 'pla': pla_prin, 'est': est_padrao, 'emp_name': empresa_selecionada.upper(), 'status': 'Ativo', 'veiculos_lista': json_frota, 'data_cadastro': data_cad_padrao.strftime("%Y-%m-%d")
                                        })
                                        id_counter += 1
                                        
                                    if novos_clientes:
                                        df_novos = pd.DataFrame(novos_clientes)
                                        df_clientes_atualizado = pd.concat([df_clientes, df_novos], ignore_index=True)
                                        sucesso, erro = salvar_dados(df_clientes_atualizado, FILE_CLIENTES)
                                        if sucesso:
                                            registrar_atividade(st.session_state.user, "IMPORTAÇÃO LOTE", f"Importou {len(novos_clientes)} novos clientes para a empresa {empresa_selecionada}")
                                            st.success(f"Importação concluída: {len(novos_clientes)} novos clientes adicionados.")
                                            time.sleep(2); st.session_state.aba_cli = "Listar"; st.rerun()
                                        else:
                                            st.error(f"Erro de comunicação com a nuvem: {erro}")
                                    else:
                                        st.warning("Nenhum cliente válido com placa foi encontrado no arquivo.")
                except Exception as e:
                    st.error(f"Erro ao ler o arquivo CSV: {e}")
                    
        elif opcao_cli == "Editar":
            if df_clientes.empty: st.warning("Nenhum cliente cadastrado.")
            else:
                opcoes_cli = {str(r['id']): f"{str(r['nome']).upper()} | CPF: {str(r['cpf'])} | Empresa: {str(r['emp_name']).upper()}" for _, r in df_clientes.iterrows()}
                c_target = st.selectbox("Selecione o cliente para Editar:", options=[""] + list(opcoes_cli.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_cli[x])
                if c_target != "":
                    dados_ant = df_clientes[df_clientes['id'].astype(str) == c_target].iloc[0]
                    c1, c2, c3 = st.columns([2, 2, 1])
                    nome_in = c1.text_input("Nome Completo:", value=dados_ant['nome'])
                    cpf_raw = c2.text_input("CPF/CNPJ:", value=dados_ant['cpf'])
                    tel_raw = c3.text_input("Telefone:", value=dados_ant['tel'])
                    
                    end_in = c1.text_input("Endereço Completo:", value=dados_ant.get('endereco', ''))
                    bairro_in = c2.text_input("Bairro:", value=dados_ant.get('bairro', ''))
                    cid_in = c3.text_input("Cidade:", value=dados_ant.get('cidade', ''))
                    
                    cep_in = c1.text_input("CEP:", value=dados_ant.get('cep', ''))
                    try: val_data_cad = datetime.strptime(str(dados_ant.get('data_cadastro', ''))[:10], "%Y-%m-%d").date()
                    except: val_data_cad = datetime.now().date()
                    cad_data = c2.date_input("Data de Cadastro (Início do Contrato):", value=val_data_cad)
                    
                    st.write("---")
                    st.write("**Frota do Cliente**")
                    frota_inicial = []
                    if pd.notna(dados_ant.get('veiculos_lista')) and dados_ant['veiculos_lista']:
                        try: frota_inicial = json.loads(dados_ant['veiculos_lista'])
                        except: pass
                    if not frota_inicial:
                        if pd.notna(dados_ant.get('vei')) and dados_ant['vei'] != 'nan': frota_inicial.append({"Tipo": "Carro", "Modelo/Ano": dados_ant['vei'], "Placa": str(dados_ant['pla']).upper(), "Blindado": False})
                        if pd.notna(dados_ant.get('vei_2')) and dados_ant['vei_2'] != 'nan' and dados_ant['vei_2']: frota_inicial.append({"Tipo": "Carro", "Modelo/Ano": dados_ant['vei_2'], "Placa": str(dados_ant['pla_2']).upper(), "Blindado": False})
                    if not frota_inicial: frota_inicial = [{"Tipo": "Carro", "Modelo/Ano": "", "Placa": "", "Blindado": False}]
                    
                    for item in frota_inicial:
                        if "Tipo" not in item: item["Tipo"] = "Carro"
                        if "Blindado" not in item: item["Blindado"] = False

                    frota_editada = st.data_editor(pd.DataFrame(frota_inicial), column_config=FROTA_COL_CONFIG, num_rows="dynamic", use_container_width=True)
                    st.write("---")
                    
                    lista_empresas_disponiveis = [str(e['nome']).upper() for _, e in df_empresas.iterrows()] if not df_empresas.empty else ["NENHUMA EMPRESA CADASTRADA"]
                    idx_emp = lista_empresas_disponiveis.index(str(dados_ant['emp_name']).upper()) if str(dados_ant['emp_name']).upper() in lista_empresas_disponiveis else 0
                    emp = st.selectbox("Empresa Vinculada / Parceira:", options=lista_empresas_disponiveis, index=idx_emp)
                    
                    modo_fat_selecionado = "Tradicional"
                    if not df_empresas.empty:
                        dados_emp = df_empresas[df_empresas['nome'].str.upper() == emp.upper()]
                        if not dados_emp.empty:
                            modo_fat_selecionado = dados_emp.iloc[0].get('modo_faturamento', 'Tradicional')
                    
                    opcoes_km_cli, msg_km_cli = obter_opcoes_km_plano(modo_fat_selecionado)
                    if msg_km_cli:
                        st.info(f"Empresa {emp}: {msg_km_cli}")

                    plano_atual_cli = str(dados_ant.get('plano_km', '50km')).strip()
                    opcoes_km_edit = list(opcoes_km_cli)
                    if plano_atual_cli and plano_atual_cli not in opcoes_km_edit:
                        opcoes_km_edit.append(plano_atual_cli)

                    col_b1, col_b2, col_b3 = st.columns(3)
                    idx_est_c = ESTADOS_BR.index(str(dados_ant['est']).upper()) if str(dados_ant['est']).upper() in ESTADOS_BR else ESTADOS_BR.index("RN")
                    est = col_b1.selectbox("Estado (UF) do Veículo:", options=ESTADOS_BR, index=idx_est_c)
                    
                    idx_plano = opcoes_km_edit.index(plano_atual_cli) if plano_atual_cli in opcoes_km_edit else 0
                    plano_km = col_b2.selectbox("Plano Contratado (KM):", options=opcoes_km_edit, index=idx_plano)
                    status = col_b3.selectbox("Status do Cliente:", ["Ativo", "Inativo"], index=["Ativo", "Inativo"].index(str(dados_ant['status'])))
                    
                    if st.button("Salvar Alterações"):
                        nome, cpf, tel = nome_in.upper(), apenas_numeros_letras(cpf_raw), apenas_numeros_letras(tel_raw)
                        frota_limpa = frota_editada.dropna(subset=['Placa', 'Modelo/Ano'], how='any')
                        frota_limpa = frota_limpa[frota_limpa['Placa'].astype(str).str.strip() != ""]
                        frota_limpa['Placa'] = frota_limpa['Placa'].astype(str).str.upper().str.replace("-","").str.replace(" ","")
                        frota_limpa['Blindado'] = frota_limpa['Blindado'].fillna(False).astype(bool)
                        
                        frota_json_str = json.dumps(frota_limpa.to_dict('records'))
                        vei_prin = frota_limpa.iloc[0]['Modelo/Ano'] if not frota_limpa.empty else ""
                        pla_prin = frota_limpa.iloc[0]['Placa'] if not frota_limpa.empty else ""
                        
                        if not nome or not pla_prin: st.error("Nome e ao menos 1 Placa de Veículo são obrigatórios.")
                        else:
                            with st.spinner("Sincronizando edição..."):
                                dt_str_save = cad_data.strftime("%Y-%m-%d")
                                df_clientes.loc[df_clientes['id'].astype(str) == c_target, ['nome','cpf','tel','endereco','bairro','cidade','cep','plano_km','vei','pla','est','emp_name','status','veiculos_lista','data_cadastro']] = [nome, cpf, tel, end_in, bairro_in.upper(), cid_in.upper(), cep_in, plano_km, vei_prin, pla_prin, est, emp.upper(), status, frota_json_str, dt_str_save]
                                sucesso, erro = salvar_dados(df_clientes, FILE_CLIENTES)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EDIÇÃO DE CLIENTE", f"Editou os dados do cliente {nome}")
                                    st.success("Alterações salvas com sucesso."); st.session_state.aba_cli = "Listar"; time.sleep(1); st.rerun()
                                else:
                                    st.error(f"Erro ao salvar edição na nuvem: {erro}")

        elif opcao_cli == "Excluir":
            if df_clientes.empty: st.warning("Nenhum cliente cadastrado.")
            else:
                opcoes_cli = {str(r['id']): f"{str(r['nome']).upper()} | CPF: {str(r['cpf'])} | Empresa: {str(r['emp_name']).upper()}" for _, r in df_clientes.iterrows()}
                c_target_del = st.selectbox("Selecione o Cliente para Excluir:", options=[""] + list(opcoes_cli.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_cli[x])
                if c_target_del != "":
                    if "cli_del_confirm" not in st.session_state: st.session_state.cli_del_confirm = None
                    if st.session_state.cli_del_confirm != c_target_del:
                        if st.button("Excluir permanentemente"): st.session_state.cli_del_confirm = c_target_del; st.rerun()
                    if st.session_state.get("cli_del_confirm") == c_target_del:
                        st.error(f"Tem certeza absoluta que deseja excluir o cliente **{opcoes_cli[c_target_del]}**?")
                        col_sim, col_nao = st.columns(2)
                        if col_sim.button("Confirmar exclusão"):
                            with st.spinner("Apagando registro no Supabase..."):
                                cliente_apagado = df_clientes[df_clientes['id'].astype(str) == c_target_del].iloc[0]
                                detalhes_del = f"Apagou o cliente -> ID: {c_target_del} | Nome: {cliente_apagado['nome']} | CPF: {cliente_apagado.get('cpf','')} | Empresa: {cliente_apagado.get('emp_name','')}"
                                deletar_registro_banco(FILE_CLIENTES, "id", str(c_target_del))
                                df_clientes = df_clientes[df_clientes['id'].astype(str) != c_target_del]
                                registrar_atividade(st.session_state.user, "EXCLUSÃO CLIENTE", detalhes_del)
                                st.success("Cliente excluído permanentemente."); st.session_state.cli_del_confirm = None; st.session_state.aba_cli = "Listar"; time.sleep(1); st.rerun()
                        if col_nao.button("Cancelar"): st.session_state.cli_del_confirm = None; st.rerun()

    elif aba_selecionada == "Prestadores":
        st.markdown('<div class="section-title">Rede de Prestadores</div>', unsafe_allow_html=True)
        pendentes = df_prestadores[df_prestadores['homologado'] == 'Pendente']
        if not pendentes.empty:
            st.error(f"Existem {len(pendentes)} prestadores aguardando homologação.")
            for idx, p in pendentes.iterrows():
                pix_p_hom = ler_pix_prestador(p) or "Não informada"
                with st.expander(f"Solicitação de: {p['nome']} - {p['est']}"):
                    st.write(f"**Tipo:** {p['tipo']} | **Telefone:** {p['telefone']} | **Bairro/Cidade:** {p.get('bairro','N/D')} - {p.get('cidade','N/D')} | **Chave PIX:** `{pix_p_hom}`")
                    texto_zap = urllib.parse.quote(f"Olá *{str(p['nome']).upper()}*! \n\nSeu cadastro na rede de prestadores da *AD Rastreamento Veicular — Central de Assistência 24 Horas* foi analisado e *APROVADO*! ✅🚛\n\nA partir de agora você receberá nossos chamados de assistência 24h diretamente por aqui.\n\nSeja bem-vindo à nossa rede!")
                    link_w_aprov = f"https://api.whatsapp.com/send?phone=55{apenas_numeros_letras(p['telefone'])}&text={texto_zap}"
                    st.markdown(f'<a href="{link_w_aprov}" target="_blank" style="text-decoration: none;"><button style="background-color: #25D366; color: white; padding: 6px 12px; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; margin-bottom: 10px; font-size: 13px;">Avisar no WhatsApp</button></a>', unsafe_allow_html=True)
                    col_h1, col_h2 = st.columns(2)
                    if col_h1.button("Aprovar no Sistema", key=f"apr_{p['id']}"):
                        df_prestadores.loc[df_prestadores['id'] == p['id'], 'homologado'] = 'Aprovado'
                        sucesso, erro = salvar_dados(df_prestadores, FILE_PRESTADORES)
                        if sucesso: 
                            registrar_atividade(st.session_state.user, "APROVAÇÃO PRESTADOR", f"Aprovou o cadastro de {p['nome']}")
                            st.success("Prestador aprovado."); time.sleep(1); st.rerun()
                    if col_h2.button("Reprovar / Excluir", key=f"rep_{p['id']}"):
                        deletar_registro_banco(FILE_PRESTADORES, "id", str(p['id']))
                        df_prestadores = df_prestadores[df_prestadores['id'].astype(str) != str(p['id'])]
                        registrar_atividade(st.session_state.user, "REPROVAÇÃO PRESTADOR", f"Reprovou {p['nome']}")
                        st.info("Cadastro excluído."); time.sleep(1); st.rerun()
            st.write("---")
        
        if "aba_pre" not in st.session_state: st.session_state.aba_pre = "Listar"
        opcoes_radio_pre = ["Listar", "Incluir Novo", "Editar", "Excluir"]
        idx_radio_pre = opcoes_radio_pre.index(st.session_state.aba_pre) if st.session_state.aba_pre in opcoes_radio_pre else 0
        opcao_pre = st.radio("Ação Prestadores:", opcoes_radio_pre, horizontal=True, index=idx_radio_pre)
        st.session_state.aba_pre = opcao_pre
        
        if opcao_pre == "Listar":
            busca_pres_lista = st.text_input("Buscar Prestador (Nome, Tipo ou Cidade):")
            if df_prestadores.empty: st.info("Nenhum prestador cadastrado.")
            else: 
                df_view_pres = df_prestadores.copy()
                df_view_pres['chave_pix'] = df_view_pres.apply(ler_pix_prestador, axis=1)
                expandir_pastas_pre = False
                if busca_pres_lista: 
                    expandir_pastas_pre = True
                    df_view_pres = df_view_pres[df_view_pres['nome'].str.contains(busca_pres_lista, case=False, na=False) | df_view_pres['tipo'].str.contains(busca_pres_lista, case=False, na=False) | df_view_pres['cidade'].str.contains(busca_pres_lista, case=False, na=False) | df_view_pres['bairro'].str.contains(busca_pres_lista, case=False, na=False)]
                estados_na_lista = df_view_pres['est'].dropna().unique()
                if len(estados_na_lista) == 0: st.warning("Nenhum prestador encontrado.")
                else:
                    for est_sigla in sorted(estados_na_lista):
                        nome_est = str(est_sigla).upper() if str(est_sigla).strip() != "" else "SEM ESTADO VINCULADO"
                        with st.expander(f"Prestadores do Estado: {nome_est}", expanded=expandir_pastas_pre):
                            df_est_filtrada = df_view_pres[df_view_pres['est'] == est_sigla]
                            st.dataframe(df_est_filtrada[['nome','cpf','tipo','telefone','chave_pix','bairro','cidade','status','homologado']].style.map(colorir_status, subset=['status']), use_container_width=True)
        elif opcao_pre == "Incluir Novo":
            c1, c2 = st.columns(2)
            n_prest_in = c1.text_input("Nome do Guincho/Prestador:", value=st.session_state.get("pre_inc_nome", ""))
            st.session_state.pre_inc_nome = n_prest_in
            cpf_p_raw = c2.text_input("CPF/CNPJ do Prestador:", value=st.session_state.get("pre_inc_cpf", ""))
            st.session_state.pre_inc_cpf = cpf_p_raw
            t_prest_lista = c1.multiselect("Tipos de Serviço Prestado:", options=OPCOES_SERVICOS, default=["Guincho"])
            tel_p_raw = c2.text_input("Telefone de Contato (Com DDD):", value=st.session_state.get("pre_inc_tel", ""))
            st.session_state.pre_inc_tel = tel_p_raw
            pix_p_in = c1.text_input("Chave PIX para Pagamento:", value=st.session_state.get("pre_inc_pix", ""), placeholder="CPF, CNPJ, Celular ou E-mail")
            st.session_state.pre_inc_pix = pix_p_in
            end_p_in = c2.text_input("Endereço / Base:", value=st.session_state.get("pre_inc_end", ""))
            st.session_state.pre_inc_end = end_p_in
            bairro_p_in = c1.text_input("Bairro:", value=st.session_state.get("pre_inc_bairro", ""))
            st.session_state.pre_inc_bairro = bairro_p_in
            cid_p_in = c2.text_input("Cidade Base:", value=st.session_state.get("pre_inc_cid", ""))
            st.session_state.pre_inc_cid = cid_p_in
            cep_p_in = c1.text_input("CEP:", value=st.session_state.get("pre_inc_cep", ""))
            st.session_state.pre_inc_cep = cep_p_in
            est_p = c2.selectbox("Estado (UF) de Atuação:", options=ESTADOS_BR, index=ESTADOS_BR.index("RN"))
            stat_p = c1.selectbox("Status do Prestador:", ["Ativo", "Inativo"], index=0)
            if st.button("Salvar Novo Prestador"):
                cpf_p = apenas_numeros_letras(cpf_p_raw)
                t_prest = ", ".join(t_prest_lista)
                if not n_prest_in or not cpf_p: st.error("O Nome e o CPF/CNPJ do prestador são obrigatórios.")
                elif not t_prest_lista: st.error("Selecione ao menos um tipo de serviço prestado.")
                else:
                    with st.spinner("Salvando prestador no Supabase..."):
                        prox_p = int(df_prestadores['id'].astype(float).max() + 1) if not df_prestadores.empty else 1
                        frota_pix_str = empacotar_pix_prestador("", pix_p_in)
                        novo_p = pd.DataFrame([{'id': str(prox_p), 'nome': n_prest_in.upper(), 'cpf': cpf_p, 'tipo': t_prest, 'telefone': apenas_numeros_letras(tel_p_raw), 'endereco': end_p_in, 'bairro': bairro_p_in.upper(), 'cidade': cid_p_in.upper(), 'cep': cep_p_in, 'est': est_p, 'status': stat_p, 'homologado': 'Aprovado', 'senha': 'admin', 'frota': frota_pix_str}])
                        df_prestadores_temp = pd.concat([df_prestadores, novo_p], ignore_index=True)
                        sucesso, erro = salvar_dados(df_prestadores_temp, FILE_PRESTADORES)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "NOVO PRESTADOR", f"Cadastrou prestador {n_prest_in.upper()} ({t_prest})")
                            for k in ["pre_inc_nome", "pre_inc_cpf", "pre_inc_tel", "pre_inc_pix", "pre_inc_end", "pre_inc_bairro", "pre_inc_cid", "pre_inc_cep"]: st.session_state[k] = ""
                            st.success("Prestador cadastrado com sucesso."); st.session_state.aba_pre = "Listar"; time.sleep(1); st.rerun()
                        else:
                            st.error(f"Erro na nuvem: {erro}")
        elif opcao_pre == "Editar":
            if df_prestadores.empty: st.warning("Nenhum prestador cadastrado.")
            else:
                opcoes_pre = {str(r['id']): f"{str(r['nome']).upper()} | Cidade: {str(r['cidade']).upper()} | Tipo: {str(r['tipo'])}" for _, r in df_prestadores.iterrows()}
                p_target = st.selectbox("Selecione o Prestador para Editar:", options=[""] + list(opcoes_pre.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_pre[x])
                if p_target != "":
                    dados_p_ant = df_prestadores[df_prestadores['id'].astype(str) == p_target].iloc[0]
                    c1, c2 = st.columns(2)
                    n_prest_in = c1.text_input("Nome do Guincho/Prestador:", value=dados_p_ant['nome'])
                    cpf_p_raw = c2.text_input("CPF/CNPJ do Prestador:", value=dados_p_ant.get('cpf',''))
                    servicos_atuais = [s for s in [x.strip() for x in str(dados_p_ant.get('tipo', '')).split(',')] if s in OPCOES_SERVICOS]
                    if not servicos_atuais: servicos_atuais = ["Guincho"]
                    t_prest_lista = c1.multiselect("Tipos de Serviço Prestado:", options=OPCOES_SERVICOS, default=servicos_atuais)
                    tel_p_raw = c2.text_input("Telefone de Contato (Com DDD):", value=dados_p_ant['telefone'])
                    pix_p_in = c1.text_input("Chave PIX para Pagamento:", value=ler_pix_prestador(dados_p_ant), placeholder="CPF, CNPJ, Celular ou E-mail")
                    end_p_in = c2.text_input("Endereço / Base:", value=dados_p_ant.get('endereco',''))
                    bairro_p_in = c1.text_input("Bairro:", value=dados_p_ant.get('bairro',''))
                    cid_p_in = c2.text_input("Cidade Base:", value=dados_p_ant.get('cidade',''))
                    cep_p_in = c1.text_input("CEP:", value=dados_p_ant.get('cep',''))
                    idx_est_p = ESTADOS_BR.index(str(dados_p_ant['est']).upper()) if str(dados_p_ant['est']).upper() in ESTADOS_BR else ESTADOS_BR.index("RN")
                    est_p = c2.selectbox("Estado (UF) de Atuação:", options=ESTADOS_BR, index=idx_est_p)
                    stat_p = c1.selectbox("Status do Prestador:", ["Ativo", "Inativo"], index=["Ativo", "Inativo"].index(str(dados_p_ant['status'])))
                    
                    if st.button("Salvar Alterações"):
                        cpf_p = apenas_numeros_letras(cpf_p_raw)
                        t_prest = ", ".join(t_prest_lista)
                        if not n_prest_in or not cpf_p: st.error("O Nome e o CPF/CNPJ do prestador são obrigatórios.")
                        elif not t_prest_lista: st.error("Selecione ao menos um tipo de serviço prestado.")
                        else:
                            with st.spinner("Atualizando prestador no Supabase..."):
                                frota_pix_upd = empacotar_pix_prestador(dados_p_ant.get('frota', ''), pix_p_in)
                                df_prestadores.loc[df_prestadores['id'].astype(str) == p_target, ['nome','cpf','tipo','telefone','endereco','bairro','cidade','cep','est','status','frota']] = [n_prest_in.upper(), cpf_p, t_prest, apenas_numeros_letras(tel_p_raw), end_p_in, bairro_p_in.upper(), cid_p_in.upper(), cep_p_in, est_p, stat_p, frota_pix_upd]
                                sucesso, erro = salvar_dados(df_prestadores, FILE_PRESTADORES)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EDIÇÃO PRESTADOR", f"Editou o prestador {n_prest_in.upper()}")
                                    st.success("Prestador atualizado com sucesso."); st.session_state.aba_pre = "Listar"; time.sleep(1); st.rerun()
                                else: st.error(f"Erro na nuvem: {erro}")
        elif opcao_pre == "Excluir":
            if df_prestadores.empty: st.warning("Nenhum prestador cadastrado.")
            else:
                opcoes_pre = {str(r['id']): f"{str(r['nome']).upper()} | Cidade: {str(r['cidade']).upper()} | Tipo: {str(r['tipo'])}" for _, r in df_prestadores.iterrows()}
                p_target_del = st.selectbox("Selecione o Prestador para Excluir:", options=[""] + list(opcoes_pre.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_pre[x])
                if p_target_del != "":
                    if "pre_del_confirm" not in st.session_state: st.session_state.pre_del_confirm = None
                    if st.session_state.pre_del_confirm != p_target_del:
                        if st.button("Excluir permanentemente"): st.session_state.pre_del_confirm = p_target_del; st.rerun()
                    if st.session_state.get("pre_del_confirm") == p_target_del:
                        st.error(f"Tem certeza que deseja excluir o prestador **{opcoes_pre[p_target_del]}**?")
                        col_sim, col_nao = st.columns(2)
                        if col_sim.button("Confirmar exclusão"):
                            with st.spinner("Excluindo prestador..."):
                                pre_apagado = df_prestadores[df_prestadores['id'].astype(str) == p_target_del].iloc[0]
                                detalhes_pre = f"Apagou prestador -> ID: {p_target_del} | Nome: {pre_apagado['nome']} | Tipo: {pre_apagado.get('tipo','')}"
                                deletar_registro_banco(FILE_PRESTADORES, "id", str(p_target_del))
                                df_prestadores = df_prestadores[df_prestadores['id'].astype(str) != p_target_del]
                                registrar_atividade(st.session_state.user, "EXCLUSÃO PRESTADOR", detalhes_pre)
                                st.success("Prestador excluído permanentemente."); st.session_state.pre_del_confirm = None; st.session_state.aba_pre = "Listar"; time.sleep(1); st.rerun()
                        if col_nao.button("Cancelar"): st.session_state.pre_del_confirm = None; st.rerun()
                # ===================================================================================
# INTERFACE 1: ADMIN MASTER (PARTE 5 - NPS + FINANCEIRO 360º + AUDITORIA + RELATÓRIOS ORDENADOS + DADOS)
# ===================================================================================
if st.session_state.perfil == "Admin":
    if aba_selecionada == "Satisfação (NPS)":
        st.markdown('<div class="section-title">Pesquisa de Satisfação (NPS)</div>', unsafe_allow_html=True)
        st.write("Acompanhe em tempo real a qualidade do atendimento da Central de Assistência 24 Horas e dos prestadores parceiros.")
        
        if df_nps.empty:
            st.info("Nenhuma avaliação recebida ainda. Os dados aparecerão aqui assim que os clientes responderem.")
        else:
            total_resp = len(df_nps)
            promotores = len(df_nps[df_nps['status_nps'] == 'Promotor'])
            detratores = len(df_nps[df_nps['status_nps'] == 'Detrator'])
            nps_score = ((promotores - detratores) / total_resp) * 100 if total_resp > 0 else 0
            
            try: media_central = df_nps['nota_central'].astype(float).mean()
            except: media_central = 0.0
            try: media_guincho = df_nps['nota_guincho'].astype(float).mean()
            except: media_guincho = 0.0
            
            cor_nps = COR_VERDE_TXT if nps_score >= 75 else "#F59E0B" if nps_score >= 50 else COR_VERM_TXT
            
            st.markdown("---")
            c_nps1, c_nps2, c_nps3 = st.columns(3)
            c_nps1.markdown(f'<div class="metric-card" style="border-top: 4px solid {cor_nps};"><div class="metric-title">Score NPS Global</div><div class="metric-value" style="color: {cor_nps}; font-size: 30px;">{nps_score:.1f}</div><div class="metric-sub">Total de {total_resp} avaliações</div></div>', unsafe_allow_html=True)
            c_nps2.markdown(f'<div class="metric-card"><div class="metric-title">Média da Central (1 a 5)</div><div class="metric-value" style="color: {COR_ROXO_DEST}; font-size: 30px;">{media_central:.1f} / 5</div></div>', unsafe_allow_html=True)
            c_nps3.markdown(f'<div class="metric-card"><div class="metric-title">Média dos Prestadores (1 a 5)</div><div class="metric-value" style="color: {COR_ROXO_DEST}; font-size: 30px;">{media_guincho:.1f} / 5</div></div>', unsafe_allow_html=True)
            
            st.markdown("##### Últimas Avaliações Recebidas")
            def cor_linha_nps(val):
                if val == 'Detrator': return 'background-color: #ffebee; color: #c62828; font-weight: bold;'
                if val == 'Promotor': return 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold;'
                return 'background-color: #fff8e1; color: #f57f17; font-weight: bold;'
            
            df_nps_exibicao = df_nps[['data_hora', 'id_os', 'status_nps', 'nota_nps', 'nota_central', 'nota_guincho', 'comentario']].sort_values(by='data_hora', ascending=False)
            st.dataframe(df_nps_exibicao.style.map(cor_linha_nps, subset=['status_nps']), use_container_width=True)

    elif aba_selecionada == "Financeiro":
        st.markdown('<div class="section-title">Financeiro — Receber, Particular, Pagar Prestadores e Lucro Líquido</div>', unsafe_allow_html=True)

        mes_atual_ref, mes_anterior_ref = obter_meses_referencia()
        if "fin_admin_mes_sel" not in st.session_state:
            st.session_state.fin_admin_mes_sel = mes_atual_ref

        c_nav_f1, c_nav_f2, c_nav_f3, c_nav_f4 = st.columns([1.3, 1.3, 1.6, 1.0])
        with c_nav_f1:
            st.write("")
            if st.button(f"Mês Atual ({mes_atual_ref})", key="btn_fin_adm_atual", use_container_width=True):
                st.session_state.fin_admin_mes_sel = mes_atual_ref
                st.rerun()
        with c_nav_f2:
            st.write("")
            if st.button(f"Mês Anterior ({mes_anterior_ref})", key="btn_fin_adm_ant", use_container_width=True):
                st.session_state.fin_admin_mes_sel = mes_anterior_ref
                st.rerun()
        with c_nav_f3:
            mes_digitado_adm = st.text_input("Buscar outro mês (MM/AAAA):", placeholder="Ex: 09/2026", key="inp_fin_adm_mes")
        with c_nav_f4:
            st.write("")
            if st.button("Buscar Mês", key="btn_fin_adm_buscar", use_container_width=True):
                mes_norm = normalizar_mes_ano(mes_digitado_adm)
                if mes_norm:
                    st.session_state.fin_admin_mes_sel = mes_norm
                    st.rerun()
                else:
                    st.error("Formato inválido. Digite MM/AAAA (ex: 09/2026).")

        mes_filtro = st.session_state.fin_admin_mes_sel
        rotulo_comp = "Mês Atual" if mes_filtro == mes_atual_ref else "Mês Anterior" if mes_filtro == mes_anterior_ref else "Competência Histórica"
        st.markdown(f'<div class="info-box" style="padding:10px 16px;"><b>Competência Ativa:</b> {mes_filtro} &nbsp;({rotulo_comp})</div>', unsafe_allow_html=True)

        try:
            mes_s, ano_s = mes_filtro.split('/')
        except:
            hoje_fb = obter_hora_brasilia()
            mes_s, ano_s = f"{hoje_fb.month:02d}", str(hoje_fb.year)

        empresas_ativas = df_empresas[df_empresas['status'].str.upper() == 'ATIVO']
        df_financeiro, df_fin_mes = sincronizar_financeiro_competencia(mes_filtro, df_financeiro, df_empresas, df_clientes, df_os)
        df_custos_mes = extrair_custos_os_df(df_os, df_prestadores, mes_filtro)

        tab_rec, tab_part, tab_pag, tab_dre = st.tabs([
            "Contas a Receber (Empresas)",
            "Particular",
            "Contas a Pagar (Prestadores)",
            "Lucro Líquido (DRE)"
        ])

        # =====================================================================
        # ABA 1: CONTAS A RECEBER (EMPRESAS PARCEIRAS)
        # =====================================================================
        with tab_rec:
            if empresas_ativas.empty and df_financeiro.empty:
                st.warning("Nenhuma empresa ativa cadastrada para gerar o financeiro.")
            else:
                lista_emp_fin_disponiveis = sorted(df_fin_mes['empresa'].str.upper().unique().tolist()) if not df_fin_mes.empty else []
                emp_consulta_ind = st.selectbox(
                    "Consultar Empresa Individualmente (ou visualizar Todas):",
                    ["Todas as Empresas"] + lista_emp_fin_disponiveis,
                    key="sel_fin_emp_individual"
                )

                if emp_consulta_ind != "Todas as Empresas":
                    df_fin_ind = df_fin_mes[df_fin_mes['empresa'].str.upper() == emp_consulta_ind.upper()]
                    if not df_fin_ind.empty:
                        r_ind = df_fin_ind.iloc[0]
                        vf_ind = formatar_moeda_float(r_ind['valor_faturado'])
                        vp_ind = formatar_moeda_float(r_ind['valor_pago'])
                        saldo_ind = max(0.0, vf_ind - vp_ind)
                        st_ind = str(r_ind.get('status', 'Pendente')).strip()
                        dados_emp_ind = df_empresas[df_empresas['nome'].str.upper() == emp_consulta_ind.upper()]
                        modo_ind = str(dados_emp_ind.iloc[0].get('modo_faturamento', 'Tradicional')).strip() if not dados_emp_ind.empty else 'Tradicional'
                        dados_fat_ind = calcular_fatura_parceiro(emp_consulta_ind, mes_s, ano_s, df_clientes, df_os, df_empresas)

                        st.markdown(f"""
                            <div class="dash-box" style="border: 2px solid #6A1B9A; border-left: 6px solid #D32F2F;">
                                <div class="dash-box-title">
                                    <span>Ficha Financeira Individual — {emp_consulta_ind} ({mes_filtro})</span>
                                    <span class="service-badge {'badge-green' if st_ind == 'Pago' else 'badge-red' if st_ind == 'Atrasado' else 'badge-purple'}">{st_ind.upper()}</span>
                                </div>
                                <p style="margin:4px 0; font-size:13.5px;"><strong>Modalidade:</strong> {modo_ind} &nbsp;|&nbsp; <strong>Veículos Ativos:</strong> {dados_fat_ind['total_v']} &nbsp;|&nbsp; <strong>Guinchos no Ciclo:</strong> {dados_fat_ind['total_os']}</p>
                                <p style="margin:4px 0; font-size:13px; color:{COR_TEXTO_SEC};"><strong>Período do Ciclo:</strong> {dados_fat_ind['dt_inicio'].strftime('%d/%m/%Y')} a {dados_fat_ind['dt_fim'].strftime('%d/%m/%Y')} (Vencimento dia {dados_fat_ind['vencimento_dia']})</p>
                            </div>
                        """, unsafe_allow_html=True)

                        ci1, ci2, ci3 = st.columns(3)
                        ci1.markdown(f'<div class="metric-card"><div class="metric-title">Valor Cobrado ({mes_filtro})</div><div class="metric-value" style="color: {COR_ROXO_DEST};">R$ {vf_ind:.2f}</div></div>', unsafe_allow_html=True)
                        ci2.markdown(f'<div class="metric-card green-accent"><div class="metric-title">Valor Pago</div><div class="metric-value val-pago">R$ {vp_ind:.2f}</div></div>', unsafe_allow_html=True)
                        ci3.markdown(f'<div class="metric-card red-accent"><div class="metric-title">Saldo em Aberto</div><div class="metric-value val-atrasado">R$ {saldo_ind:.2f}</div></div>', unsafe_allow_html=True)

                        df_hist_ind = df_financeiro[df_financeiro['empresa'].str.upper() == emp_consulta_ind.upper()].copy()
                        if not df_hist_ind.empty:
                            df_hist_ind['ord_key'] = df_hist_ind['mes_ano'].apply(mes_ano_para_tupla)
                            df_hist_ind = df_hist_ind.sort_values(by='ord_key', ascending=False).drop(columns=['ord_key'])
                            df_hist_ind['diferenca'] = df_hist_ind.apply(lambda row: f"R$ {max(0.0, formatar_moeda_float(row['valor_faturado']) - formatar_moeda_float(row['valor_pago'])):.2f}", axis=1)
                            with st.expander(f"Histórico Completo de Cobranças de {emp_consulta_ind} (Todos os Meses)", expanded=True):
                                st.dataframe(
                                    df_hist_ind[['mes_ano', 'valor_faturado', 'valor_pago', 'diferenca', 'status']].rename(columns={
                                        'mes_ano': 'Competência', 'valor_faturado': 'Valor Cobrado (R$)', 'valor_pago': 'Valor Pago (R$)', 'diferenca': 'Em Aberto', 'status': 'Status'
                                    }).style.map(formatar_status_financeiro, subset=['Status']),
                                    use_container_width=True
                                )

                        if modo_ind != 'Tradicional':
                            st.markdown(gerar_pdf_extrato_detalhado(emp_consulta_ind, mes_s, ano_s, df_clientes, df_os, df_empresas), unsafe_allow_html=True)

                df_exibir_fin = df_fin_mes.copy() if emp_consulta_ind == "Todas as Empresas" else df_fin_mes[df_fin_mes['empresa'].str.upper() == emp_consulta_ind.upper()].copy()

                total_faturado_mes, total_recebido_mes, taxas_exibicao = 0.0, 0.0, []
                for idx, r_fin in df_exibir_fin.iterrows():
                    emp_name = r_fin['empresa']
                    dados_emp_base = df_empresas[df_empresas['nome'].str.upper() == emp_name.upper()]
                    if not dados_emp_base.empty:
                        modo_fat = str(dados_emp_base.iloc[0].get('modo_faturamento', 'Tradicional')).strip()
                        dados_fatura = calcular_fatura_parceiro(emp_name, mes_s, ano_s, df_clientes, df_os, df_empresas)
                        if modo_fat == "Performance (Escalonado)": taxas_exibicao.append(f"{dados_fatura['taxa']:.1f}%")
                        elif "Frota Pequena" in modo_fat or "Até 40" in modo_fat: taxas_exibicao.append("Plano Fixo")
                        else: taxas_exibicao.append("Manual")
                    else:
                        taxas_exibicao.append("Histórico")

                    total_faturado_mes += formatar_moeda_float(r_fin['valor_faturado'])
                    total_recebido_mes += formatar_moeda_float(r_fin['valor_pago'])

                inadimplencia = max(0.0, total_faturado_mes - total_recebido_mes)

                if emp_consulta_ind == "Todas as Empresas":
                    col_d1, col_d2, col_d3 = st.columns(3)
                    col_d1.markdown(f'<div class="metric-card"><div class="metric-title">Faturamento Total ({mes_filtro})</div><div class="metric-value" style="color: {COR_ROXO_DEST};">R$ {total_faturado_mes:.2f}</div></div>', unsafe_allow_html=True)
                    col_d2.markdown(f'<div class="metric-card green-accent"><div class="metric-title">Faturas Pagas</div><div class="metric-value val-pago">R$ {total_recebido_mes:.2f}</div></div>', unsafe_allow_html=True)
                    col_d3.markdown(f'<div class="metric-card red-accent"><div class="metric-title">Pendente (A Receber)</div><div class="metric-value val-atrasado">R$ {inadimplencia:.2f}</div></div>', unsafe_allow_html=True)

                st.markdown(f"##### Lançamentos da Competência {mes_filtro}")
                if df_exibir_fin.empty:
                    st.info("Nenhum lançamento encontrado para esta competência.")
                else:
                    df_view_fin = df_exibir_fin.copy()
                    df_view_fin['diferenca'] = [f"R$ {max(0.0, formatar_moeda_float(r['valor_faturado']) - formatar_moeda_float(r['valor_pago'])):.2f}" for _, r in df_view_fin.iterrows()]
                    df_view_fin['taxa_de_uso'] = taxas_exibicao
                    st.dataframe(df_view_fin[['empresa', 'taxa_de_uso', 'valor_faturado', 'valor_pago', 'diferenca', 'status']].style.map(formatar_status_financeiro, subset=['status']), use_container_width=True)
                
                if emp_consulta_ind == "Todas as Empresas":
                    st.write("---")
                    st.markdown("##### Emitir Extrato Detalhado por Empresa (PDF/HTML)")
                    empresas_escalonadas = empresas_ativas[empresas_ativas['modo_faturamento'] != 'Tradicional']['nome'].str.upper().tolist()
                    if not empresas_escalonadas: st.info("Nenhuma empresa ativa cadastrada nos modos de faturamento automáticos.")
                    else:
                        emp_pdf_sel = st.selectbox("Selecione a Empresa (Modos Automáticos) para Gerar o Extrato:", empresas_escalonadas)
                        if emp_pdf_sel:
                            st.markdown(gerar_pdf_extrato_detalhado(emp_pdf_sel, mes_s, ano_s, df_clientes, df_os, df_empresas), unsafe_allow_html=True)

                st.write("---")
                st.markdown("##### Editar Lançamento / Dar Baixa (Empresa Parceira)")
                if not df_fin_mes.empty:
                    lista_empresas_fin = df_fin_mes['empresa'].tolist()
                    idx_edit_padrao = lista_empresas_fin.index(emp_consulta_ind) if emp_consulta_ind in lista_empresas_fin else 0
                    emp_edit = st.selectbox("Selecione a Empresa para dar baixa ou ajustar:", lista_empresas_fin, index=idx_edit_padrao)
                    if emp_edit:
                        row_edit = df_fin_mes[df_fin_mes['empresa'] == emp_edit].iloc[0]
                        dados_emp_base_edit = df_empresas[df_empresas['nome'].str.upper() == emp_edit.upper()]
                        modo_fat_edit = str(dados_emp_base_edit.iloc[0].get('modo_faturamento', 'Tradicional')).strip() if not dados_emp_base_edit.empty else 'Tradicional'
                        with st.form("form_financeiro"):
                            st.write(f"**Empresa:** {emp_edit} | **Competência:** {mes_filtro} | **Plano:** {modo_fat_edit}")
                            c_f1, c_f2, c_f3 = st.columns(3)
                            val_fat_final = c_f1.text_input("Valor Cobrado da Fatura (R$):", value=str(row_edit['valor_faturado']))
                            val_pago_final = c_f2.text_input("Valor Pago pelo Cliente (R$):", value=str(row_edit['valor_pago']))
                            status_op_fin = ["Pendente", "Pago", "Atrasado"]
                            idx_st_fin = status_op_fin.index(row_edit['status']) if row_edit['status'] in status_op_fin else 0
                            status_final = c_f3.selectbox("Status:", status_op_fin, index=idx_st_fin)
                            
                            if st.form_submit_button("Salvar Edição Financeira"):
                                with st.spinner("Atualizando registros financeiros..."):
                                    vf_limpo = f"{formatar_moeda_float(val_fat_final):.2f}"
                                    vp_limpo = f"{formatar_moeda_float(val_pago_final):.2f}"
                                    df_financeiro.loc[df_financeiro['id'] == row_edit['id'], ['valor_faturado', 'valor_pago', 'status']] = [vf_limpo, vp_limpo, status_final]
                                    sucesso, erro = salvar_dados(df_financeiro, FILE_FINANCEIRO)
                                    if sucesso:
                                        registrar_atividade(st.session_state.user, "BAIXA FINANCEIRA", f"Editou o faturamento de {emp_edit} ({mes_filtro}) - Cobrado: R$ {vf_limpo} | Pago: R$ {vp_limpo} | Status: {status_final}")
                                        st.success("Registro atualizado e salvo com sucesso."); time.sleep(1); st.rerun()
                                    else: st.error(f"Falha na nuvem: {erro}")

        # =====================================================================
        # ABA 2: PARTICULAR (ATENDIMENTOS AVULSOS E OS MARCADAS COMO PARTICULAR)
        # =====================================================================
        with tab_part:
            st.markdown(f"##### Controle de Atendimentos Particulares ({mes_filtro})")
            st.caption("Agrupa automaticamente todos os chamados abertos como Atendimento Avulso (Particular) e qualquer OS marcada com status 'Particular' em Contas a Pagar.")

            if df_custos_mes.empty:
                df_part_mes = pd.DataFrame()
            else:
                df_part_mes = df_custos_mes[
                    (df_custos_mes['eh_particular'] == True) |
                    (df_custos_mes['status_pgto'] == 'Particular')
                ].copy()

            if df_part_mes.empty:
                st.info(f"Nenhum atendimento particular registrado na competência {mes_filtro}.")
            else:
                tot_part_cob = df_part_mes['valor_particular_cobrado'].sum()
                tot_part_rec = df_part_mes['valor_particular_pago'].sum()
                tot_part_custo = df_part_mes['custo_total'].sum()
                tot_part_lucro = tot_part_cob - tot_part_custo

                p1, p2, p3, p4 = st.columns(4)
                p1.markdown(f'<div class="metric-card"><div class="metric-title">Total Cobrado (Particular)</div><div class="metric-value" style="color: {COR_ROXO_DEST};">R$ {tot_part_cob:.2f}</div></div>', unsafe_allow_html=True)
                p2.markdown(f'<div class="metric-card green-accent"><div class="metric-title">Recebido (Caixa)</div><div class="metric-value val-pago">R$ {tot_part_rec:.2f}</div></div>', unsafe_allow_html=True)
                p3.markdown(f'<div class="metric-card red-accent"><div class="metric-title">Custo Prestador</div><div class="metric-value val-atrasado">R$ {tot_part_custo:.2f}</div></div>', unsafe_allow_html=True)
                cls_lp = "val-pago" if tot_part_lucro >= 0 else "val-atrasado"
                p4.markdown(f'<div class="metric-card green-accent"><div class="metric-title">Lucro Particular</div><div class="metric-value {cls_lp}">R$ {tot_part_lucro:.2f}</div></div>', unsafe_allow_html=True)

                df_part_tbl = df_part_mes[['id_os', 'data_hora', 'cliente_nome', 'placa', 'servico', 'prestador', 'valor_particular_cobrado', 'valor_particular_pago', 'custo_total', 'status_particular']].copy()
                df_part_tbl['lucro'] = df_part_tbl['valor_particular_cobrado'] - df_part_tbl['custo_total']
                for col_pm in ['valor_particular_cobrado', 'valor_particular_pago', 'custo_total', 'lucro']:
                    df_part_tbl[col_pm] = df_part_tbl[col_pm].apply(lambda x: f"R$ {x:.2f}")
                df_part_tbl.columns = ['OS', 'Data/Hora', 'Cliente', 'Placa', 'Serviço', 'Prestador', 'Valor Cobrado', 'Valor Recebido', 'Custo Prestador', 'Status Receb.', 'Lucro']
                st.dataframe(df_part_tbl[['OS', 'Data/Hora', 'Cliente', 'Placa', 'Serviço', 'Prestador', 'Valor Cobrado', 'Valor Recebido', 'Custo Prestador', 'Lucro', 'Status Receb.']].style.map(formatar_status_financeiro, subset=['Status Receb.']), use_container_width=True)

                st.write("---")
                st.markdown("##### Editar Cobrança / Dar Baixa em Atendimento Particular")
                opcoes_part_os = {
                    r['id_os']: f"OS #{r['id_os']} | {r['data_hora'][:10]} | {r['cliente_nome']} ({r['placa']}) | Cobrado: R$ {r['valor_particular_cobrado']:.2f} ({r['status_particular']})"
                    for _, r in df_part_mes.iterrows()
                }
                os_part_sel = st.selectbox("Selecione o atendimento particular:", [""] + list(opcoes_part_os.keys()), format_func=lambda x: "Selecione uma OS..." if x == "" else opcoes_part_os[x], key="sel_os_part_fin")
                if os_part_sel:
                    r_pt = df_part_mes[df_part_mes['id_os'] == os_part_sel].iloc[0]
                    row_os_pt = df_os[df_os['id'].astype(str) == str(os_part_sel)].iloc[0]

                    with st.form(f"form_fin_part_{os_part_sel}"):
                        st.write(f"**OS #{os_part_sel}** | **Cliente:** {r_pt['cliente_nome']} | **Placa:** {r_pt['placa']} | **Prestador:** {r_pt['prestador']}")
                        pp1, pp2, pp3 = st.columns(3)
                        v_cob_pt = pp1.number_input("Valor Cobrado do Particular (R$):", min_value=0.0, value=float(r_pt['valor_particular_cobrado']), step=10.0, format="%.2f")
                        v_rec_pt = pp2.number_input("Valor Recebido (R$):", min_value=0.0, value=float(r_pt['valor_particular_pago']), step=10.0, format="%.2f")
                        st_rec_pt = pp3.selectbox("Status Recebimento:", ["Pendente", "Pago"], index=1 if r_pt['status_particular'] == 'Pago' else 0)

                        pp4, pp5 = st.columns(2)
                        v_custo_pt = pp4.number_input("Custo do Prestador nesta OS (R$):", min_value=0.0, value=float(r_pt['custo_total']), step=10.0, format="%.2f")
                        obs_pt_in = pp5.text_input("Observações:", value=r_pt['obs_particular'], placeholder="Ex: Recebido via PIX")

                        if st.form_submit_button("Salvar Atendimento Particular", use_container_width=True):
                            with st.spinner("Salvando lançamento particular no Supabase..."):
                                novos_pt_meta = {
                                    'valor_particular_pago': f"{v_rec_pt:.2f}",
                                    'status_pgto_particular': st_rec_pt,
                                    'obs_particular': obs_pt_in.strip(),
                                    'status_pgto_prestador': 'Particular'
                                }
                                if abs(v_custo_pt - float(r_pt['custo_total'])) > 0.009:
                                    novos_pt_meta['custo_saida'] = f"{v_custo_pt:.2f}"
                                    novos_pt_meta['custo_km_exc'] = "0.00"
                                    novos_pt_meta['custo_pedagio'] = "0.00"
                                    novos_pt_meta['custo_total'] = f"{v_custo_pt:.2f}"

                                meta_pt_upd = mesclar_meta_os(row_os_pt.get('fotos_vistoria', ''), novos_pt_meta)
                                df_os.loc[df_os['id'].astype(str) == str(os_part_sel), ['valor_cobrado', 'fotos_vistoria']] = [f"{v_cob_pt:.2f}", meta_pt_upd]
                                ok_pt, err_pt = salvar_dados(df_os, FILE_OS)
                                if ok_pt:
                                    registrar_atividade(st.session_state.user, "FINANCEIRO PARTICULAR", f"OS #{os_part_sel} - Cobrado: R$ {v_cob_pt:.2f} | Recebido: R$ {v_rec_pt:.2f} | Status: {st_rec_pt}")
                                    st.success(f"Atendimento particular OS #{os_part_sel} atualizado com sucesso.")
                                    time.sleep(1); st.rerun()
                                else:
                                    st.error(f"Erro ao salvar: {err_pt}")

        # =====================================================================
        # ABA 3: CONTAS A PAGAR (PRESTADORES & CUSTOS POR OS — PIX INTELIGENTE)
        # =====================================================================
        with tab_pag:
            st.markdown(f"##### Custos Operacionais por OS e Fila de Pagamentos ({mes_filtro})")
            if df_custos_mes.empty:
                st.info(f"Nenhuma OS registrada na competência {mes_filtro}.")
            else:
                tot_custo_os = df_custos_mes['custo_total'].sum()
                tot_pago_prest = df_custos_mes[df_custos_mes['status_pgto'] == 'Pago']['custo_total'].sum()
                tot_pagar_prest = df_custos_mes[df_custos_mes['status_pgto'] == 'A Pagar']['custo_total'].sum()
                qtd_part_pg = len(df_custos_mes[df_custos_mes['status_pgto'] == 'Particular'])

                cp1, cp2, cp3, cp4 = st.columns(4)
                cp1.markdown(f'<div class="metric-card"><div class="metric-title">Custo Total OS ({mes_filtro})</div><div class="metric-value" style="color: {COR_ROXO_DEST};">R$ {tot_custo_os:.2f}</div></div>', unsafe_allow_html=True)
                cp2.markdown(f'<div class="metric-card green-accent"><div class="metric-title">Pago a Prestadores</div><div class="metric-value val-pago">R$ {tot_pago_prest:.2f}</div></div>', unsafe_allow_html=True)
                cp3.markdown(f'<div class="metric-card red-accent"><div class="metric-title">A Pagar (Pendente)</div><div class="metric-value val-atrasado">R$ {tot_pagar_prest:.2f}</div></div>', unsafe_allow_html=True)
                cp4.markdown(f'<div class="metric-card"><div class="metric-title">OS em Particular</div><div class="metric-value" style="color: {COR_ROXO_TXT};">{qtd_part_pg}</div></div>', unsafe_allow_html=True)

                filtro_pg_prest = st.radio("Filtrar Fila de Pagamentos:", ["Todas as OS", "A Pagar (Com Valor)", "Pago", "Particular", "Sem Custo Lançado"], horizontal=True, key="rad_filtro_pg_prest")
                df_pag_vis = df_custos_mes.copy()
                if filtro_pg_prest == "A Pagar (Com Valor)":
                    df_pag_vis = df_pag_vis[(df_pag_vis['status_pgto'] == 'A Pagar') & (df_pag_vis['custo_total'] > 0)]
                elif filtro_pg_prest == "Pago":
                    df_pag_vis = df_pag_vis[df_pag_vis['status_pgto'] == 'Pago']
                elif filtro_pg_prest == "Particular":
                    df_pag_vis = df_pag_vis[df_pag_vis['status_pgto'] == 'Particular']
                elif filtro_pg_prest == "Sem Custo Lançado":
                    df_pag_vis = df_pag_vis[df_pag_vis['custo_total'] == 0]

                if df_pag_vis.empty:
                    st.info("Nenhum registro para o filtro selecionado.")
                else:
                    df_pag_tbl = df_pag_vis[['id_os', 'data_hora', 'empresa', 'placa', 'servico', 'prestador', 'chave_pix', 'custo_saida', 'custo_km_exc', 'custo_pedagio', 'custo_total', 'status_pgto', 'data_pgto_prest']].copy()
                    for col_m in ['custo_saida', 'custo_km_exc', 'custo_pedagio', 'custo_total']:
                        df_pag_tbl[col_m] = df_pag_tbl[col_m].apply(lambda x: f"R$ {x:.2f}")
                    df_pag_tbl.columns = ['OS', 'Data/Hora', 'Empresa', 'Placa', 'Serviço', 'Prestador', 'Chave PIX', 'Saída', 'KM Exc.', 'Pedágio', 'Total', 'Status Pgto', 'Data Pgto']
                    st.dataframe(df_pag_tbl.style.map(formatar_status_financeiro, subset=['Status Pgto']), use_container_width=True)

                st.write("---")
                st.markdown("##### Lançar Custo da OS ou Dar Baixa no Pagamento do Prestador")
                opcoes_os_pag = {
                    r['id_os']: f"OS #{r['id_os']} | {r['data_hora'][:10]} | {r['placa']} | {r['prestador']} | Total: R$ {r['custo_total']:.2f} ({r['status_pgto']})"
                    for _, r in df_custos_mes.iterrows()
                }
                os_pag_sel = st.selectbox("Selecione a OS para lançar valores ou alterar status:", [""] + list(opcoes_os_pag.keys()), format_func=lambda x: "Selecione uma OS..." if x == "" else opcoes_os_pag[x], key="sel_os_custo_fin")
                if os_pag_sel:
                    r_p_sel = df_custos_mes[df_custos_mes['id_os'] == os_pag_sel].iloc[0]
                    row_os_orig = df_os[df_os['id'].astype(str) == str(os_pag_sel)].iloc[0]
                    pix_ja_cadastrado = str(r_p_sel.get('pix_cadastrado', '')).strip()
                    pix_da_os = "" if r_p_sel['chave_pix'] == "Não cadastrada" else str(r_p_sel['chave_pix']).strip()
                    pix_existente_final = pix_ja_cadastrado or pix_da_os
                    prest_id_alvo = str(r_p_sel.get('prestador_id', '')).strip()

                    with st.form(f"form_fin_pg_prest_{os_pag_sel}"):
                        st.write(f"**OS #{os_pag_sel}** | **Empresa:** {r_p_sel['empresa']} | **Prestador:** {r_p_sel['prestador']}")
                        fp1, fp2, fp3 = st.columns(3)
                        v_s_fin = fp1.number_input("Valor Saída / Base (R$):", min_value=0.0, value=float(r_p_sel['custo_saida']), step=10.0, format="%.2f")
                        v_k_fin = fp2.number_input("KM Excedente (R$):", min_value=0.0, value=float(r_p_sel['custo_km_exc']), step=5.0, format="%.2f")
                        v_p_fin = fp3.number_input("Pedágio / Extras (R$):", min_value=0.0, value=float(r_p_sel['custo_pedagio']), step=5.0, format="%.2f")

                        fp4, fp5 = st.columns([2, 1])
                        if pix_existente_final:
                            fp4.markdown(f'<div class="info-box" style="padding:8px 12px; margin:0;"><b>Chave PIX registrada:</b> {pix_existente_final}</div>', unsafe_allow_html=True)
                            pix_fin_in = pix_existente_final
                        else:
                            pix_fin_in = fp4.text_input("Chave PIX do Prestador (salva automaticamente para próximos atendimentos):", value="", placeholder="CPF, CNPJ, E-mail ou Celular")

                        opcoes_st_fin_pg = ["A Pagar", "Pago", "Particular"]
                        idx_st_fin_pg = opcoes_st_fin_pg.index(r_p_sel['status_pgto']) if r_p_sel['status_pgto'] in opcoes_st_fin_pg else 0
                        st_fin_pg = fp5.selectbox("Status Pagamento:", opcoes_st_fin_pg, index=idx_st_fin_pg)
                        obs_fin_c = st.text_input("Observações do Pagamento:", value=r_p_sel['obs_custo'])

                        if st.form_submit_button("Salvar Custo / Baixa do Prestador", use_container_width=True):
                            with st.spinner("Salvando custo e pagamento no Supabase..."):
                                tot_novo = round(v_s_fin + v_k_fin + v_p_fin, 2)
                                pix_limpo_save = pix_fin_in.strip()

                                if prest_id_alvo and not pix_ja_cadastrado and pix_limpo_save:
                                    row_pr_cad = df_prestadores[df_prestadores['id'].astype(str) == prest_id_alvo].iloc[0]
                                    df_prestadores.loc[df_prestadores['id'].astype(str) == prest_id_alvo, 'frota'] = empacotar_pix_prestador(row_pr_cad.get('frota', ''), pix_limpo_save)
                                    salvar_dados(df_prestadores, FILE_PRESTADORES)

                                novos_dados_c = {
                                    'custo_saida': f"{v_s_fin:.2f}",
                                    'custo_km_exc': f"{v_k_fin:.2f}",
                                    'custo_pedagio': f"{v_p_fin:.2f}",
                                    'custo_total': f"{tot_novo:.2f}",
                                    'pix_prestador_os': pix_limpo_save,
                                    'status_pgto_prestador': st_fin_pg,
                                    'obs_custo': obs_fin_c.strip(),
                                    'data_pgto_prestador': (r_p_sel['data_pgto_prest'] or obter_hora_brasilia().strftime("%d/%m/%Y %H:%M")) if st_fin_pg == "Pago" else ""
                                }
                                meta_nova = mesclar_meta_os(row_os_orig.get('fotos_vistoria', ''), novos_dados_c)
                                df_os.loc[df_os['id'].astype(str) == str(os_pag_sel), 'fotos_vistoria'] = meta_nova
                                ok_p, err_p = salvar_dados(df_os, FILE_OS)
                                if ok_p:
                                    registrar_atividade(st.session_state.user, "PAGAMENTO PRESTADOR", f"OS #{os_pag_sel} ({r_p_sel['prestador']}) - Custo: R$ {tot_novo:.2f} | Status: {st_fin_pg}")
                                    st.success(f"OS #{os_pag_sel} atualizada ({st_fin_pg} - R$ {tot_novo:.2f}).")
                                    time.sleep(1); st.rerun()
                                else:
                                    st.error(f"Erro ao salvar: {err_p}")

        # =====================================================================
        # ABA 4: LUCRO LÍQUIDO POR EMPRESA PARCEIRA E PARTICULAR (DRE)
        # =====================================================================
        with tab_dre:
            st.markdown(f"##### Resultado Operacional / Lucro Líquido ({mes_filtro})")
            st.caption("Cruza a Receita (Faturas das Empresas + Atendimentos Particulares) menos o Custo pago aos prestadores na competência.")

            empresas_dre = set()
            if not df_fin_mes.empty:
                empresas_dre.update(df_fin_mes['empresa'].str.upper().tolist())

            df_custos_empresas = pd.DataFrame()
            df_custos_particulares = pd.DataFrame()
            if not df_custos_mes.empty:
                mask_part_dre = (df_custos_mes['eh_particular'] == True) | (df_custos_mes['status_pgto'] == 'Particular')
                df_custos_particulares = df_custos_mes[mask_part_dre].copy()
                df_custos_empresas = df_custos_mes[~mask_part_dre].copy()
                if not df_custos_empresas.empty:
                    empresas_dre.update(df_custos_empresas['empresa'].str.upper().tolist())

            m_int, y_int = int(mes_s), int(ano_s)
            extras_por_emp = {}
            for _, ro in df_os.iterrows():
                if str(ro.get('status_os', '')).upper() == 'CANCELADO':
                    continue
                if eh_os_particular(ro):
                    continue
                dt_ro = parse_dt_seguro(ro.get('data_hora', ''))
                if dt_ro and dt_ro.month == m_int and dt_ro.year == y_int:
                    v_ext = formatar_moeda_float(ro.get('valor_cobrado', 0.0))
                    if v_ext > 0:
                        emp_ro = str(ro.get('empresa', '')).upper()
                        extras_por_emp[emp_ro] = extras_por_emp.get(emp_ro, 0.0) + v_ext
                        empresas_dre.add(emp_ro)

            dre_rows = []
            for emp_d in sorted(empresas_dre):
                if not emp_d or 'PARTICULAR' in emp_d or 'AVULSO' in emp_d:
                    continue
                row_f_d = df_fin_mes[df_fin_mes['empresa'].str.upper() == emp_d] if not df_fin_mes.empty else pd.DataFrame()
                rec_mensal = formatar_moeda_float(row_f_d.iloc[0]['valor_faturado']) if not row_f_d.empty else 0.0
                rec_extras = extras_por_emp.get(emp_d, 0.0)
                rec_total = rec_mensal + rec_extras

                df_c_emp = df_custos_empresas[df_custos_empresas['empresa'].str.upper() == emp_d] if not df_custos_empresas.empty else pd.DataFrame()
                qtd_os_emp = len(df_c_emp)
                custo_emp = float(df_c_emp['custo_total'].sum()) if not df_c_emp.empty else 0.0

                lucro_emp = rec_total - custo_emp
                margem_emp = (lucro_emp / rec_total * 100.0) if rec_total > 0 else (-100.0 if custo_emp > 0 else 0.0)
                situacao = "Lucro" if lucro_emp > 0 else ("Prejuízo" if lucro_emp < 0 else "Neutro")

                dre_rows.append({
                    'Origem / Empresa': emp_d,
                    'OS no Mês': qtd_os_emp,
                    'Receita Fatura': rec_mensal,
                    'Extras / Particular': rec_extras,
                    'Receita Total': rec_total,
                    'Custo Prestadores': custo_emp,
                    'Lucro Líquido': lucro_emp,
                    'Margem (%)': round(margem_emp, 1),
                    'Situação': situacao
                })

            if not df_custos_particulares.empty:
                rec_part_dre = float(df_custos_particulares['valor_particular_cobrado'].sum())
                custo_part_dre = float(df_custos_particulares['custo_total'].sum())
                lucro_part_dre = rec_part_dre - custo_part_dre
                margem_part_dre = (lucro_part_dre / rec_part_dre * 100.0) if rec_part_dre > 0 else (-100.0 if custo_part_dre > 0 else 0.0)
                sit_part_dre = "Lucro" if lucro_part_dre > 0 else ("Prejuízo" if lucro_part_dre < 0 else "Neutro")
                dre_rows.append({
                    'Origem / Empresa': 'ATENDIMENTOS PARTICULARES',
                    'OS no Mês': len(df_custos_particulares),
                    'Receita Fatura': 0.0,
                    'Extras / Particular': rec_part_dre,
                    'Receita Total': rec_part_dre,
                    'Custo Prestadores': custo_part_dre,
                    'Lucro Líquido': lucro_part_dre,
                    'Margem (%)': round(margem_part_dre, 1),
                    'Situação': sit_part_dre
                })

            if not dre_rows:
                st.info(f"Sem dados financeiros suficientes na competência {mes_filtro}.")
            else:
                df_dre = pd.DataFrame(dre_rows).sort_values(by='Lucro Líquido', ascending=False)
                tot_rec_dre = df_dre['Receita Total'].sum()
                tot_custo_dre = df_dre['Custo Prestadores'].sum()
                tot_lucro_dre = df_dre['Lucro Líquido'].sum()
                margem_global = (tot_lucro_dre / tot_rec_dre * 100.0) if tot_rec_dre > 0 else 0.0

                d1, d2, d3, d4 = st.columns(4)
                d1.markdown(f'<div class="metric-card"><div class="metric-title">Receita Total ({mes_filtro})</div><div class="metric-value" style="color: {COR_ROXO_DEST};">R$ {tot_rec_dre:.2f}</div></div>', unsafe_allow_html=True)
                d2.markdown(f'<div class="metric-card red-accent"><div class="metric-title">Custos Prestadores</div><div class="metric-value val-atrasado">R$ {tot_custo_dre:.2f}</div></div>', unsafe_allow_html=True)
                cls_luc = "val-pago" if tot_lucro_dre >= 0 else "val-atrasado"
                d3.markdown(f'<div class="metric-card green-accent"><div class="metric-title">Lucro Líquido Global</div><div class="metric-value {cls_luc}">R$ {tot_lucro_dre:.2f}</div></div>', unsafe_allow_html=True)
                d4.markdown(f'<div class="metric-card"><div class="metric-title">Margem Líquida</div><div class="metric-value {cls_luc}">{margem_global:.1f}%</div></div>', unsafe_allow_html=True)

                cor_txt_dre = "#F8FAFC" if is_dark else "#0F172A"
                cor_grd_dre = "#334155" if is_dark else "#CBD5E1"
                fig_dre = go.Figure()
                fig_dre.add_trace(go.Bar(name='Receita Total (R$)', x=df_dre['Origem / Empresa'], y=df_dre['Receita Total'], marker_color='#6A1B9A'))
                fig_dre.add_trace(go.Bar(name='Custo Prestadores (R$)', x=df_dre['Origem / Empresa'], y=df_dre['Custo Prestadores'], marker_color='#D32F2F'))
                fig_dre.add_trace(go.Bar(name='Lucro Líquido (R$)', x=df_dre['Origem / Empresa'], y=df_dre['Lucro Líquido'], marker_color='#2E7D32'))
                fig_dre.update_layout(
                    barmode='group',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=cor_txt_dre),
                    height=310,
                    margin=dict(t=20, b=20, l=15, r=15),
                    legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
                    yaxis=dict(showgrid=True, gridcolor=cor_grd_dre, title="Valor (R$)"),
                    xaxis=dict(showgrid=False)
                )
                st.plotly_chart(fig_dre, use_container_width=True)

                df_dre_vis = df_dre.copy()
                for c_v in ['Receita Fatura', 'Extras / Particular', 'Receita Total', 'Custo Prestadores', 'Lucro Líquido']:
                    df_dre_vis[c_v] = df_dre_vis[c_v].apply(lambda x: f"R$ {x:.2f}")
                df_dre_vis['Margem (%)'] = df_dre_vis['Margem (%)'].apply(lambda x: f"{x:.1f}%")
                st.dataframe(
                    df_dre_vis[['Origem / Empresa', 'OS no Mês', 'Receita Fatura', 'Extras / Particular', 'Receita Total', 'Custo Prestadores', 'Lucro Líquido', 'Margem (%)', 'Situação']].style.map(formatar_status_financeiro, subset=['Situação']),
                    use_container_width=True
                )

    elif aba_selecionada == "Auditoria":
        st.markdown('<div class="section-title">Auditoria e Logs</div>', unsafe_allow_html=True)
        if df_logs.empty: st.info("Nenhuma atividade registrada ainda.")
        else:
            df_logs_exibicao = df_logs.copy().sort_values(by='data_hora', ascending=False)
            busca_log = st.text_input("Buscar no registro:")
            if busca_log: df_logs_exibicao = df_logs_exibicao[df_logs_exibicao['usuario'].str.contains(busca_log, case=False, na=False) | df_logs_exibicao['detalhes'].str.contains(busca_log, case=False, na=False) | df_logs_exibicao['acao'].str.contains(busca_log, case=False, na=False)]
            st.write("---")
            df_logs_exibicao['idx_temp'] = df_logs_exibicao.index
            opcoes_log = {str(i): f"{r['data_hora']} - {r['usuario']} - {r['acao']}" for i, r in df_logs_exibicao.iterrows()}
            log_selecionado = st.selectbox("Selecione um registro para visualizar ou excluir:", options=[""] + list(opcoes_log.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_log[x])
            if log_selecionado != "":
                detalhe_row = df_logs_exibicao.loc[int(log_selecionado)]
                st.markdown(f"""
                <div style="background-color: {COR_BG_CARD}; color: {COR_TEXTO}; padding: 14px; border-radius: 8px; border: 1px solid {COR_BORDA}; border-left: 5px solid #6A1B9A; margin-bottom: 12px; font-size: 13px; box-shadow: 0 2px 6px rgba(0,0,0,0.06);">
                    <p style="margin-bottom:4px;"><strong>Data/Hora:</strong> {detalhe_row['data_hora']}</p>
                    <p style="margin-bottom:4px;"><strong>Usuário:</strong> {detalhe_row['usuario']}</p>
                    <p style="margin-bottom:4px;"><strong>Ação:</strong> {detalhe_row['acao']}</p>
                    <p style="margin-bottom:4px;"><strong>Detalhes Completos:</strong> {detalhe_row['detalhes']}</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Excluir este registro selecionado"):
                    with st.spinner("Removendo registro..."):
                        log_id = detalhe_row.get('id')
                        if log_id: deletar_registro_banco(FILE_LOGS, "id", str(log_id))
                        df_logs = df_logs.drop(int(log_selecionado))
                        st.success("Registro removido com sucesso."); time.sleep(1); st.rerun()
            st.write("---")
            st.dataframe(df_logs_exibicao.drop(columns=['idx_temp']), use_container_width=True)
            st.write("---")
            if "confirmar_limpeza_total" not in st.session_state: st.session_state.confirmar_limpeza_total = False
            if not st.session_state.confirmar_limpeza_total:
                if st.button("LIMPAR TODO O HISTÓRICO"): st.session_state.confirmar_limpeza_total = True; st.rerun()
            if st.session_state.confirmar_limpeza_total:
                st.warning("Tem certeza? Isso apagará todos os logs de forma irreversível.")
                c1, c2 = st.columns(2)
                if c1.button("Confirmar exclusão total"):
                    try: supabase.table(FILE_LOGS).delete().neq("id", 0).execute()
                    except: pass
                    df_logs = pd.DataFrame(columns=col_logs)
                    st.session_state.confirmar_limpeza_total = False; st.rerun()
                if c2.button("Cancelar"): st.session_state.confirmar_limpeza_total = False; st.rerun()

    elif aba_selecionada == "Relatórios & PDF":
        st.markdown('<div class="section-title">Chamados e Relatórios (Mais Recentes Primeiro)</div>', unsafe_allow_html=True)
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
                                st.success("OS atualizada com sucesso."); time.sleep(1.5); st.rerun()
                            else: st.error(f"Erro na nuvem: {erro}")
                
                if "os_del_confirm" not in st.session_state: st.session_state.os_del_confirm = None
                if st.session_state.os_del_confirm != os_id_edit:
                    if st.button("Excluir esta OS permanentemente", key=f"btn_del_os_{os_id_edit}"): st.session_state.os_del_confirm = os_id_edit; st.rerun()
                if st.session_state.get("os_del_confirm") == os_id_edit:
                    st.error(f"Atenção: deseja realmente excluir a OS {os_id_edit}?")
                    col_s, col_n = st.columns(2)
                    if col_s.button("Confirmar exclusão da OS", key=f"btn_sim_del_os_{os_id_edit}"):
                        with st.spinner("Excluindo..."):
                            os_apagada = df_os[df_os['id'].astype(str) == str(os_id_edit)].iloc[0]
                            detalhes_exclusao_os = f"Apagou OS ID: {os_id_edit} | Cliente: {os_apagada['cliente_nome']} | Placa: {os_apagada['placa']} | Empresa: {os_apagada['empresa']}"
                            deletar_registro_banco(FILE_OS, "id", str(os_id_edit))
                            df_os = df_os[df_os['id'].astype(str) != str(os_id_edit)]
                            registrar_atividade(st.session_state.user, "EXCLUSÃO OS", detalhes_exclusao_os)
                            st.success("OS excluída."); st.session_state.os_del_confirm = None; time.sleep(1.5); st.rerun()
                    if col_n.button("Cancelar", key=f"btn_nao_del_os_{os_id_edit}"): st.session_state.os_del_confirm = None; st.rerun()
            else: st.warning("Nenhuma OS encontrada com esse ID.")

        st.write("---")
        st.markdown("##### Histórico e Gerar Extrato (OS Finalizadas — Mais Recentes Primeiro)")
        df_fechadas = ordenar_os_recentes(df_os[df_os['status_os'].str.upper() == 'ENCERRADO'])
        if df_fechadas.empty: st.info("Nenhum chamado foi finalizado ainda.")
        else:
            busca_os_relatorio = st.text_input("Filtrar por Placa ou Nome do cliente (ou deixe em branco para listar os mais recentes):")
            df_filtrado_fechadas = df_fechadas.copy()
            if busca_os_relatorio:
                df_filtrado_fechadas = df_filtrado_fechadas[
                    df_filtrado_fechadas['cliente_nome'].str.contains(busca_os_relatorio, case=False, na=False) |
                    df_filtrado_fechadas['placa'].str.contains(busca_os_relatorio, case=False, na=False) |
                    df_filtrado_fechadas['id'].astype(str).str.contains(busca_os_relatorio, case=False, na=False)
                ]
            if df_filtrado_fechadas.empty:
                st.warning("Nenhum acionamento finalizado encontrado.")
            else:
                lista_os_dele = [f"Chamado Nº: {r['id']} | Data: {str(r['data_hora'])[:16]} | Placa: {r.get('placa', 'N/D')} | {r['cliente_nome']} | {r['tipo_servico']}" for _, r in df_filtrado_fechadas.iterrows()]
                os_escolhida_str = st.selectbox("Selecione o acionamento para gerar o extrato:", options=lista_os_dele)
                os_alvo_id = os_escolhida_str.split("|")[0].replace("Chamado Nº:", "").strip()
                df_os_unica = df_os[df_os['id'].astype(str) == os_alvo_id]
                st.markdown(exportar_pdf_html_oficial(df_os_unica, df_clientes, f"relatorio_os_{os_alvo_id}"), unsafe_allow_html=True)
        
        st.write("---")
        st.markdown("##### Tabela Geral de Chamados (Do Mais Recente para o Mais Antigo)")
        df_os_tabela_geral = ordenar_os_recentes(df_os)
        colunas_vis_geral = [c for c in ['id', 'data_hora', 'status_os', 'empresa', 'cliente_nome', 'placa', 'tipo_servico', 'motivo', 'prestador', 'motorista_nome', 'valor_cobrado', 'localizacao', 'destino'] if c in df_os_tabela_geral.columns]
        st.dataframe(df_os_tabela_geral[colunas_vis_geral], use_container_width=True)

    elif aba_selecionada == "Dados":
        st.markdown('<div class="section-title">Backup e Restauração</div>', unsafe_allow_html=True)
        st.info("Exporte seus dados sincronizados diretamente da nuvem Supabase.")
        c_b1, c_b2 = st.columns(2)
        with c_b1:
            st.markdown("##### 1. Baixar Dados Atuais")
            if not df_clientes.empty: st.download_button("Baixar Clientes (.csv)", df_clientes.to_csv(index=False).encode('utf-8'), file_name="banco_clientes.csv", use_container_width=True)
            if not df_empresas.empty: st.download_button("Baixar Empresas (.csv)", df_empresas.to_csv(index=False).encode('utf-8'), file_name="banco_empresas.csv", use_container_width=True)
            if not df_prestadores.empty: st.download_button("Baixar Prestadores (.csv)", df_prestadores.to_csv(index=False).encode('utf-8'), file_name="banco_prestadores.csv", use_container_width=True)
            if not df_os.empty: st.download_button("Baixar Atendimentos / OS (.csv)", ordenar_os_recentes(df_os).to_csv(index=False).encode('utf-8'), file_name="banco_os.csv", use_container_width=True)
            if not df_financeiro.empty: st.download_button("Baixar Financeiro (.csv)", df_financeiro.to_csv(index=False).encode('utf-8'), file_name="banco_financeiro.csv", use_container_width=True)
            if not df_nps.empty: st.download_button("Baixar Avaliações NPS (.csv)", df_nps.to_csv(index=False).encode('utf-8'), file_name="banco_nps.csv", use_container_width=True)
        with c_b2:
            st.markdown("##### 2. Restaurar Sistema (Supabase)")
            uploaded_file = st.file_uploader("Selecione o arquivo CSV de backup para restaurar", type=['csv'])
            if uploaded_file is not None:
                if st.button(f"Restaurar dados de: {uploaded_file.name}"):
                    mapa_arquivos = {
                        "banco_clientes.csv": FILE_CLIENTES, "banco_empresas.csv": FILE_EMPRESAS,
                        "banco_prestadores.csv": FILE_PRESTADORES, "banco_os.csv": FILE_OS,
                        "banco_financeiro.csv": FILE_FINANCEIRO, "banco_nps.csv": FILE_NPS
                    }
                    nome_arq = uploaded_file.name
                    if nome_arq in mapa_arquivos:
                        try:
                            df_restaurado = pd.read_csv(uploaded_file, dtype=str)
                            sucesso, erro = salvar_dados(df_restaurado, mapa_arquivos[nome_arq])
                            if sucesso:
                                registrar_atividade(st.session_state.user, "RESTAURAÇÃO", f"Restaurou backup para a tabela {mapa_arquivos[nome_arq]}")
                                st.success(f"Tabela {mapa_arquivos[nome_arq]} restaurada com sucesso."); time.sleep(2); st.rerun()
                            else: st.error(f"Erro ao restaurar: {erro}")
                        except Exception as e: st.error(f"Erro ao ler arquivo: {e}")
                    else: st.error("Nome de arquivo não reconhecido. Use os nomes originais gerados pelo sistema (ex: banco_clientes.csv).")

# ===================================================================================
# INTERFACE 2: PARCEIROS (CENTRAL DE ASSISTÊNCIA 24 HORAS — MENU MINIMALISTA + 200KM)
# ===================================================================================
if st.session_state.perfil == "Parceiro":
    opcoes_parc = ["Dashboard", "Cadastro de Clientes", "Histórico de Chamados", "Meu Financeiro", "Auditoria"]
    aba_atual_parc = st.query_params.get("nav", opcoes_parc[0])
    if aba_atual_parc not in opcoes_parc: aba_atual_parc = opcoes_parc[0]
    
    with st.sidebar:
        st.markdown("""
            <div class="sidebar-brand-box">
                <div class="sidebar-brand-title">AD ASSISTÊNCIA 24H</div>
                <div class="sidebar-brand-sub">Portal do Parceiro</div>
            </div>
        """, unsafe_allow_html=True)
        aba_selecionada = st.radio("Navegação do Parceiro:", opcoes_parc, index=opcoes_parc.index(aba_atual_parc), label_visibility="collapsed")
    
    if aba_selecionada != aba_atual_parc:
        st.query_params["nav"] = aba_selecionada
        st.rerun()
    
    if aba_selecionada == "Dashboard":
        renderizar_dashboard(st.session_state.empresa_vinculada, eh_admin=False)
    
    elif aba_selecionada == "Cadastro de Clientes":
        st.markdown('<div class="section-title">Gestão de Clientes</div>', unsafe_allow_html=True)
        df_filtrado_p = df_clientes[df_clientes['emp_name'].str.lower() == st.session_state.empresa_vinculada.lower()]
        dados_emp_base_p0 = df_empresas[df_empresas['nome'].str.upper() == st.session_state.empresa_vinculada.upper()]
        dia_v_p0 = str(dados_emp_base_p0.iloc[0].get('dia_vencimento', '30')).strip() if not dados_emp_base_p0.empty else "30"

        mes_atual_taxa_p, ano_atual_taxa_p = obter_mes_ano_vigente(dia_v_p0)
        dados_fat_resumo = calcular_fatura_parceiro(st.session_state.empresa_vinculada, mes_atual_taxa_p, ano_atual_taxa_p, df_clientes, df_os, df_empresas)

        st.markdown(f'<div class="info-box" style="padding:10px;">{gerar_texto_resumo_plano(dados_fat_resumo)}</div>', unsafe_allow_html=True)
        st.write("---")
        
        if "aba_part" not in st.session_state: st.session_state.aba_part = "Visualizar"
        opcoes_radio_part = ["Visualizar", "Incluir Novo", "Editar Cliente", "Excluir Cliente"]
        idx_radio_part = opcoes_radio_part.index(st.session_state.aba_part) if st.session_state.aba_part in opcoes_radio_part else 0
        op_part = st.radio("Ação Parceiro:", opcoes_radio_part, horizontal=True, index=idx_radio_part)
        st.session_state.aba_part = op_part
        
        if op_part == "Visualizar":
            busca_cli_part = st.text_input("Buscar Cliente (Nome, Placa ou CPF):")
            df_view_cli_part = df_filtrado_p.copy()
            if busca_cli_part:
                df_view_cli_part = df_view_cli_part[df_view_cli_part['nome'].str.contains(busca_cli_part, case=False, na=False) | df_view_cli_part['pla'].str.contains(busca_cli_part, case=False, na=False) | df_view_cli_part['cpf'].str.contains(busca_cli_part, case=False, na=False) | df_view_cli_part['veiculos_lista'].str.lower().str.contains(busca_cli_part.lower(), na=False)]
            
            if df_view_cli_part.empty: st.info("Nenhum cliente encontrado.")
            else: 
                def formatar_historico_p(c_id):
                    if df_os.empty: return "Nenhum Serviço Solicitado"
                    c_id_str = str(c_id).strip()
                    if not c_id_str or c_id_str.lower() == 'nan': return "Nenhum Serviço Solicitado"
                    os_cli = ordenar_os_recentes(df_os[df_os['cliente_id'].astype(str).str.strip() == c_id_str])
                    if os_cli.empty: return "Nenhum Serviço Solicitado"
                    res = []
                    for _, r in os_cli.iterrows():
                        try: d_str = datetime.strptime(str(r['data_hora']), "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
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
                cli_sel_part = st.selectbox("Selecione um cliente para ver a Ficha Completa:", cli_opcoes_part, index=idx_sel_part, key=widget_key_part)
                st.session_state.sel_det_part = cli_sel_part
                
                if cli_sel_part != "":
                    cli_data_p = df_view_cli_part[df_view_cli_part['nome'] == cli_sel_part].iloc[0]
                    dt_cad_cliente = str(cli_data_p.get('data_cadastro', ''))
                    inicio_cli, fim_cli = obter_ciclo_contrato_anual(dt_cad_cliente)
                    
                    st.markdown(f"### Ficha do Cliente: {cli_data_p['nome']}")
                    c1, c2 = st.columns(2)
                    c1.write(f"**CPF:** {cli_data_p['cpf']}"); c1.write(f"**Telefone:** {cli_data_p['tel']}"); c1.write(f"**Plano Contratado:** {cli_data_p.get('plano_km', 'N/D')}")
                    c2.write(f"**Endereço:** {cli_data_p.get('endereco', 'N/D')}, {cli_data_p.get('bairro', 'N/D')} - {cli_data_p.get('cidade', 'N/D')}/{cli_data_p.get('est', 'N/D')}")
                    c2.write(f"**Status:** {cli_data_p['status']}"); c2.write(f"**Data de Cadastro:** {dt_cad_cliente}")
                    st.write("**Frota Cadastrada:**")
                    try: st.table(pd.DataFrame(json.loads(cli_data_p['veiculos_lista'])))
                    except: st.write(f"{cli_data_p.get('vei', '')} - Placa: {cli_data_p.get('pla', '')}")
                    st.write("---")
                    
                    lista_frota_ficha = []
                    if pd.notna(cli_data_p.get('veiculos_lista')) and cli_data_p['veiculos_lista']:
                        try:
                            for v in json.loads(cli_data_p['veiculos_lista']):
                                if v.get('Placa'): lista_frota_ficha.append(str(v.get('Placa')).upper().strip())
                        except: pass 
                    if not lista_frota_ficha:
                        if pd.notna(cli_data_p.get('pla')) and str(cli_data_p['pla']).strip(): lista_frota_ficha.append(str(cli_data_p['pla']).upper().strip())
                        if pd.notna(cli_data_p.get('pla_2')) and str(cli_data_p['pla_2']).strip(): lista_frota_ficha.append(str(cli_data_p['pla_2']).upper().strip())
                    
                    if lista_frota_ficha:
                        placa_sel_ficha = st.selectbox("Selecione a Placa para ver o Saldo Operacional:", lista_frota_ficha, key=f"sel_placa_part_{cli_sel_part}")
                        st.write(f"**Saldo de Limites da Placa {placa_sel_ficha} ({inicio_cli.strftime('%d/%m/%Y')} a {fim_cli.strftime('%d/%m/%Y')}):**")
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
                    
                    st.write("---")
                    st.write("**Histórico Completo de Atendimentos (Mais Recentes Primeiro):**")
                    if df_os.empty: st.info("Nenhum acionamento.")
                    else:
                        os_cli_p = ordenar_os_recentes(df_os[df_os['cliente_id'].astype(str).str.strip() == str(cli_data_p['id']).strip()])
                        if os_cli_p.empty: st.info("Nenhum acionamento.")
                        else: st.dataframe(os_cli_p[['id', 'data_hora', 'tipo_servico', 'placa', 'prestador', 'status_os']], use_container_width=True)
                            
                    if st.button("Fechar Ficha do Cliente", key="btn_close_part"):
                        st.session_state.sel_det_part = ""
                        if widget_key_part in st.session_state: del st.session_state[widget_key_part]
                        st.rerun()
        
        elif op_part == "Incluir Novo":
            c1, c2, c3 = st.columns([2, 2, 1])
            p_nome_in = c1.text_input("Nome Completo:", value=st.session_state.get("part_inc_nome", "")); st.session_state.part_inc_nome = p_nome_in
            p_cpf_raw = c2.text_input("CPF:", value=st.session_state.get("part_inc_cpf", "")); st.session_state.part_inc_cpf = p_cpf_raw
            p_tel_raw = c3.text_input("Telefone:", value=st.session_state.get("part_inc_tel", "")); st.session_state.part_inc_tel = p_tel_raw
            p_end_in = c1.text_input("Endereço Completo:", value=st.session_state.get("part_inc_end", "")); st.session_state.part_inc_end = p_end_in
            p_bairro_in = c2.text_input("Bairro:", value=st.session_state.get("part_inc_bairro", "")); st.session_state.part_inc_bairro = p_bairro_in
            p_cid_in = c3.text_input("Cidade:", value=st.session_state.get("part_inc_cid", "")); st.session_state.part_inc_cid = p_cid_in
            p_cep_in = c1.text_input("CEP:", value=st.session_state.get("part_inc_cep", "")); st.session_state.part_inc_cep = p_cep_in
            cad_data = c2.date_input("Data de Cadastro (Início do Contrato):", value=datetime.now())
            
            st.write("---"); st.write("**Frota do Cliente (Tabela Interativa)**")
            df_frota_editavel_p = pd.DataFrame([{"Tipo": "Carro", "Modelo/Ano": "", "Placa": "", "Blindado": False}])
            frota_editada_p = st.data_editor(df_frota_editavel_p, column_config=FROTA_COL_CONFIG, num_rows="dynamic", use_container_width=True)
            st.write("---")
            
            modo_fat_parceiro = "Tradicional"
            if not df_empresas.empty:
                dados_emp_parc = df_empresas[df_empresas['nome'].str.upper() == st.session_state.empresa_vinculada.upper()]
                if not dados_emp_parc.empty: modo_fat_parceiro = dados_emp_parc.iloc[0].get('modo_faturamento', 'Tradicional')
            
            opcoes_km_parc, msg_km_parc = obter_opcoes_km_plano(modo_fat_parceiro)
            if msg_km_parc:
                st.info(msg_km_parc)

            col_pb1, col_pb2, col_pb3 = st.columns(3)
            uf_padrao_parceiro = "RN"
            if not df_empresas.empty:
                emp_dados = df_empresas[df_empresas['nome'].str.upper() == st.session_state.empresa_vinculada.upper()]
                if not emp_dados.empty: uf_padrao_parceiro = str(emp_dados.iloc[0].get('est', 'RN')).upper()
            idx_uf_parceiro = ESTADOS_BR.index(uf_padrao_parceiro) if uf_padrao_parceiro in ESTADOS_BR else ESTADOS_BR.index("RN")

            p_est = col_pb1.selectbox("UF do Veículo:", options=ESTADOS_BR, index=idx_uf_parceiro)
            p_plano_km = col_pb2.selectbox("Plano Contratado (KM):", options=opcoes_km_parc, index=0)
            p_stat = col_pb3.selectbox("Status do Serviço:", ["Ativo", "Inativo"], index=0)
            
            if st.button("Salvar Novo Registro"):
                p_cpf = apenas_numeros_letras(p_cpf_raw)
                frota_limpa_p = frota_editada_p.dropna(subset=['Placa', 'Modelo/Ano'], how='any')
                frota_limpa_p = frota_limpa_p[frota_limpa_p['Placa'].astype(str).str.strip() != ""]
                frota_limpa_p['Placa'] = frota_limpa_p['Placa'].astype(str).str.upper().str.replace("-","").str.replace(" ","")
                frota_limpa_p['Blindado'] = frota_limpa_p['Blindado'].fillna(False).astype(bool)
                
                frota_json_str_p = json.dumps(frota_limpa_p.to_dict('records'))
                vei_prin_p = frota_limpa_p.iloc[0]['Modelo/Ano'] if not frota_limpa_p.empty else ""
                pla_prin_p = frota_limpa_p.iloc[0]['Placa'] if not frota_limpa_p.empty else ""
                
                if not p_nome_in or not pla_prin_p: st.error("Nome e ao menos 1 Placa são obrigatórios.")
                else:
                    with st.spinner("Salvando no Supabase..."):
                        prox_id = int(df_clientes['id'].astype(float).max() + 1) if not df_clientes.empty else 1
                        dt_str_save = cad_data.strftime("%Y-%m-%d")
                        novo_reg = pd.DataFrame([{'id': str(prox_id), 'nome': p_nome_in.upper(), 'cpf': p_cpf, 'tel': apenas_numeros_letras(p_tel_raw), 'endereco': p_end_in, 'bairro': p_bairro_in.upper(), 'cidade': p_cid_in.upper(), 'cep': p_cep_in, 'plano_km': p_plano_km, 'vei': vei_prin_p, 'pla': pla_prin_p, 'est': p_est, 'emp_name': st.session_state.empresa_vinculada.upper(), 'status': p_stat, 'veiculos_lista': frota_json_str_p, 'data_cadastro': dt_str_save}])
                        df_clientes_temp = pd.concat([df_clientes, novo_reg], ignore_index=True)
                        sucesso, erro = salvar_dados(df_clientes_temp, FILE_CLIENTES)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "NOVO CLIENTE PARCEIRO", f"Cadastrou o cliente {p_nome_in.upper()}")
                            st.success("Registro salvo com sucesso.")
                            for k in ["part_inc_nome", "part_inc_cpf", "part_inc_tel", "part_inc_end", "part_inc_bairro", "part_inc_cid", "part_inc_cep"]: st.session_state[k] = ""
                            st.session_state.aba_part = "Visualizar"; time.sleep(1); st.rerun()
                        else: st.error("Falha ao salvar no banco.")

        elif op_part == "Editar Cliente":
            if df_filtrado_p.empty: st.warning("Nenhum cliente cadastrado para editar.")
            else:
                opcoes_dict_p = {str(r['id']): f"{str(r['nome']).upper()} | CPF: {str(r['cpf'])}" for _, r in df_filtrado_p.iterrows()}
                part_target = st.selectbox("Selecione o cliente para Editar:", options=[""] + list(opcoes_dict_p.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_dict_p[x])
                if part_target != "":
                    dados_part_ant = df_filtrado_p[df_filtrado_p['id'].astype(str) == part_target].iloc[0]
                    c1, c2, c3 = st.columns([2, 2, 1])
                    p_nome_in = c1.text_input("Nome Completo:", value=dados_part_ant['nome'])
                    p_cpf_raw = c2.text_input("CPF:", value=dados_part_ant['cpf'])
                    p_tel_raw = c3.text_input("Telefone:", value=dados_part_ant['tel'])
                    p_end_in = c1.text_input("Endereço Completo:", value=dados_part_ant.get('endereco', ''))
                    p_bairro_in = c2.text_input("Bairro:", value=dados_part_ant.get('bairro', ''))
                    p_cid_in = c3.text_input("Cidade:", value=dados_part_ant.get('cidade', ''))
                    p_cep_in = c1.text_input("CEP:", value=dados_part_ant.get('cep', ''))
                    try: val_data_cad = datetime.strptime(str(dados_part_ant.get('data_cadastro', ''))[:10], "%Y-%m-%d").date()
                    except: val_data_cad = datetime.now().date()
                    cad_data = c2.date_input("Data de Cadastro (Início do Contrato):", value=val_data_cad)
                    
                    st.write("---"); st.write("**Frota do Cliente**")
                    frota_inicial_p = []
                    if pd.notna(dados_part_ant.get('veiculos_lista')) and dados_part_ant['veiculos_lista']:
                        try: frota_inicial_p = json.loads(dados_part_ant['veiculos_lista'])
                        except: pass
                    if not frota_inicial_p:
                        if pd.notna(dados_part_ant.get('vei')) and dados_part_ant['vei'] != 'nan': frota_inicial_p.append({"Tipo": "Carro", "Modelo/Ano": dados_part_ant['vei'], "Placa": str(dados_part_ant['pla']).upper(), "Blindado": False})
                        if pd.notna(dados_part_ant.get('vei_2')) and dados_part_ant['vei_2'] != 'nan' and dados_part_ant['vei_2']: frota_inicial_p.append({"Tipo": "Carro", "Modelo/Ano": dados_part_ant['vei_2'], "Placa": str(dados_part_ant['pla_2']).upper(), "Blindado": False})
                    if not frota_inicial_p: frota_inicial_p = [{"Tipo": "Carro", "Modelo/Ano": "", "Placa": "", "Blindado": False}]
                    for item in frota_inicial_p:
                        if "Tipo" not in item: item["Tipo"] = "Carro"
                        if "Blindado" not in item: item["Blindado"] = False

                    frota_editada_p = st.data_editor(pd.DataFrame(frota_inicial_p), column_config=FROTA_COL_CONFIG, num_rows="dynamic", use_container_width=True)
                    st.write("---")
                    
                    modo_fat_parceiro = "Tradicional"
                    if not df_empresas.empty:
                        dados_emp_parc = df_empresas[df_empresas['nome'].str.upper() == st.session_state.empresa_vinculada.upper()]
                        if not dados_emp_parc.empty: modo_fat_parceiro = dados_emp_parc.iloc[0].get('modo_faturamento', 'Tradicional')
                    
                    opcoes_km_parc, msg_km_parc = obter_opcoes_km_plano(modo_fat_parceiro)
                    if msg_km_parc:
                        st.info(msg_km_parc)

                    plano_atual_part = str(dados_part_ant.get('plano_km', '50km')).strip()
                    opcoes_km_parc_edit = list(opcoes_km_parc)
                    if plano_atual_part and plano_atual_part not in opcoes_km_parc_edit:
                        opcoes_km_parc_edit.append(plano_atual_part)

                    col_pb1, col_pb2, col_pb3 = st.columns(3)
                    idx_est_part = ESTADOS_BR.index(str(dados_part_ant['est']).upper()) if str(dados_part_ant['est']).upper() in ESTADOS_BR else ESTADOS_BR.index("RN")
                    p_est = col_pb1.selectbox("UF do Veículo:", options=ESTADOS_BR, index=idx_est_part)
                    idx_plano_p = opcoes_km_parc_edit.index(plano_atual_part) if plano_atual_part in opcoes_km_parc_edit else 0
                    p_plano_km = col_pb2.selectbox("Plano Contratado (KM):", options=opcoes_km_parc_edit, index=idx_plano_p)
                    p_stat = col_pb3.selectbox("Status do Serviço:", ["Ativo", "Inativo"], index=["Ativo", "Inativo"].index(str(dados_part_ant['status'])))
                    
                    if st.button("Salvar Alterações"):
                        p_cpf = apenas_numeros_letras(p_cpf_raw)
                        frota_limpa_p = frota_editada_p.dropna(subset=['Placa', 'Modelo/Ano'], how='any')
                        frota_limpa_p = frota_limpa_p[frota_limpa_p['Placa'].astype(str).str.strip() != ""]
                        frota_limpa_p['Placa'] = frota_limpa_p['Placa'].astype(str).str.upper().str.replace("-","").str.replace(" ","")
                        frota_limpa_p['Blindado'] = frota_limpa_p['Blindado'].fillna(False).astype(bool)
                        
                        frota_json_str_p = json.dumps(frota_limpa_p.to_dict('records'))
                        vei_prin_p = frota_limpa_p.iloc[0]['Modelo/Ano'] if not frota_limpa_p.empty else ""
                        pla_prin_p = frota_limpa_p.iloc[0]['Placa'] if not frota_limpa_p.empty else ""
                        
                        if not p_nome_in or not pla_prin_p: st.error("Nome e ao menos 1 Placa são obrigatórios.")
                        else:
                            with st.spinner("Atualizando cadastro na nuvem..."):
                                dt_str_save = cad_data.strftime("%Y-%m-%d")
                                df_clientes.loc[df_clientes['id'].astype(str) == part_target, ['nome','cpf','tel','endereco','bairro','cidade','cep','plano_km','vei','pla','est','status','veiculos_lista','data_cadastro']] = [p_nome_in.upper(), p_cpf, apenas_numeros_letras(p_tel_raw), p_end_in, p_bairro_in.upper(), p_cid_in.upper(), p_cep_in, p_plano_km, vei_prin_p, pla_prin_p, p_est, p_stat, frota_json_str_p, dt_str_save]
                                sucesso, erro = salvar_dados(df_clientes, FILE_CLIENTES)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EDIÇÃO CLIENTE PARCEIRO", f"Editou o cliente {p_nome_in.upper()}")
                                    st.success("Registro atualizado com sucesso."); st.session_state.aba_part = "Visualizar"; time.sleep(1); st.rerun()
                                else: st.error("Falha de comunicação com a nuvem.")

        elif op_part == "Excluir Cliente":
            if df_filtrado_p.empty: st.warning("Nenhum cliente cadastrado.")
            else:
                opcoes_dict_p = {str(r['id']): f"{str(r['nome']).upper()} | CPF: {str(r['cpf'])}" for _, r in df_filtrado_p.iterrows()}
                part_target_del = st.selectbox("Selecione o cliente para Excluir:", options=[""] + list(opcoes_dict_p.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_dict_p[x])
                if part_target_del != "":
                    if "part_del_confirm" not in st.session_state: st.session_state.part_del_confirm = None
                    if st.session_state.part_del_confirm != part_target_del:
                        if st.button("Excluir permanentemente"): st.session_state.part_del_confirm = part_target_del; st.rerun()
                    if st.session_state.get("part_del_confirm") == part_target_del:
                        st.error(f"Tem certeza que deseja excluir permanentemente o cliente **{opcoes_dict_p[part_target_del]}**?")
                        col_sim, col_nao = st.columns(2)
                        if col_sim.button("Confirmar exclusão"):
                            with st.spinner("Excluindo registro no Supabase..."):
                                cli_p_apagado = df_clientes[df_clientes['id'].astype(str) == part_target_del].iloc[0]
                                detalhes_del_p = f"Apagou o cliente -> ID: {part_target_del} | Nome: {cli_p_apagado['nome']} | CPF: {cli_p_apagado.get('cpf','')} | Placa Principal: {cli_p_apagado.get('pla','')}"
                                deletar_registro_banco(FILE_CLIENTES, "id", str(part_target_del))
                                df_clientes = df_clientes[df_clientes['id'].astype(str) != part_target_del]
                                registrar_atividade(st.session_state.user, "EXCLUSÃO CLIENTE PARCEIRO", detalhes_del_p)
                                st.success("Cliente excluído permanentemente."); st.session_state.part_del_confirm = None; st.session_state.aba_part = "Visualizar"; time.sleep(1); st.rerun()
                        if col_nao.button("Cancelar"): st.session_state.part_del_confirm = None; st.rerun()

    elif aba_selecionada == "Histórico de Chamados":
        st.markdown('<div class="section-title">Histórico de Chamados (Mais Recentes Primeiro)</div>', unsafe_allow_html=True)
        df_os_parceiro = ordenar_os_recentes(df_os[df_os['empresa'].str.lower() == st.session_state.empresa_vinculada.lower()])
        if df_os_parceiro.empty: st.info("Nenhum acionamento registrado para sua empresa.")
        else:
            colunas_vis_parc = [c for c in ['id', 'data_hora', 'status_os', 'cliente_nome', 'placa', 'tipo_servico', 'motivo', 'localizacao', 'destino', 'prestador'] if c in df_os_parceiro.columns]
            st.dataframe(df_os_parceiro[colunas_vis_parc], use_container_width=True)

    elif aba_selecionada == "Meu Financeiro":
        st.markdown('<div class="section-title">Gestão Financeira</div>', unsafe_allow_html=True)
        st.write("Confira as faturas do **Mês Atual**, **Mês Anterior** ou busque qualquer competência (ex.: `09/2026`).")
        
        dados_emp_base_p = df_empresas[df_empresas['nome'].str.upper() == st.session_state.empresa_vinculada.upper()]
        modo_fat_p = str(dados_emp_base_p.iloc[0].get('modo_faturamento', 'Tradicional')).strip() if not dados_emp_base_p.empty else "Tradicional"

        mes_atual_ref_p, mes_anterior_ref_p = obter_meses_referencia()
        if "fin_parc_mes_sel" not in st.session_state:
            st.session_state.fin_parc_mes_sel = mes_atual_ref_p

        cp1, cp2, cp3, cp4 = st.columns([1.3, 1.3, 1.6, 1.0])
        with cp1:
            st.write("")
            if st.button(f"Mês Atual ({mes_atual_ref_p})", key="btn_fin_parc_atual", use_container_width=True):
                st.session_state.fin_parc_mes_sel = mes_atual_ref_p; st.rerun()
        with cp2:
            st.write("")
            if st.button(f"Mês Anterior ({mes_anterior_ref_p})", key="btn_fin_parc_ant", use_container_width=True):
                st.session_state.fin_parc_mes_sel = mes_anterior_ref_p; st.rerun()
        with cp3:
            mes_digitado_p = st.text_input("Buscar outro mês (MM/AAAA):", placeholder="Ex: 09/2026", key="inp_fin_parc_mes")
        with cp4:
            st.write("")
            if st.button("Buscar Mês", key="btn_fin_parc_buscar", use_container_width=True):
                mes_norm_p = normalizar_mes_ano(mes_digitado_p)
                if mes_norm_p:
                    st.session_state.fin_parc_mes_sel = mes_norm_p; st.rerun()
                else: st.error("Formato inválido. Digite MM/AAAA (ex: 09/2026).")

        mes_filtro_p = st.session_state.fin_parc_mes_sel
        rotulo_comp_p = "Mês Atual" if mes_filtro_p == mes_atual_ref_p else "Mês Anterior" if mes_filtro_p == mes_anterior_ref_p else "Competência Histórica"
        st.markdown(f'<div class="info-box" style="padding:10px 16px;"><b>Competência Selecionada:</b> {mes_filtro_p} &nbsp;({rotulo_comp_p})</div>', unsafe_allow_html=True)

        df_financeiro, _ = sincronizar_financeiro_competencia(mes_filtro_p, df_financeiro, df_empresas, df_clientes, df_os)
        df_fin_parc = df_financeiro[(df_financeiro['mes_ano'] == mes_filtro_p) & (df_financeiro['empresa'].str.upper() == st.session_state.empresa_vinculada.upper())]
        
        if df_fin_parc.empty:
            st.info(f"Nenhum faturamento gerado ou disponível para visualização na competência {mes_filtro_p}.")
        else:
            row_fin = df_fin_parc.iloc[0]
            v_fat = f"{formatar_moeda_float(row_fin.get('valor_faturado', '0.00')):.2f}"
            v_pag = f"{formatar_moeda_float(row_fin.get('valor_pago', '0.00')):.2f}"
            status_f = str(row_fin.get('status', 'Pendente')).strip()
                
            st.markdown("---")
            c_f1, c_f2, c_f3 = st.columns(3)
            c_f1.markdown(f'<div class="metric-card"><div class="metric-title">Sua Fatura ({mes_filtro_p})</div><div class="metric-value" style="color: {COR_ROXO_DEST};">R$ {v_fat}</div></div>', unsafe_allow_html=True)
            c_f2.markdown(f'<div class="metric-card green-accent"><div class="metric-title">Valor Constado como Pago</div><div class="metric-value val-pago">R$ {v_pag}</div></div>', unsafe_allow_html=True)
            
            cor_borda = "#4CAF50" if status_f == "Pago" else "#D32F2F" if status_f == "Atrasado" else "#f57f17"
            bg_cor = ("#0F2E1D" if is_dark else "#e8f5e9") if status_f == "Pago" else ("#3B1318" if is_dark else "#ffebee") if status_f == "Atrasado" else ("#3B2A0A" if is_dark else "#fff8e1")
            c_f3.markdown(f'<div class="metric-card" style="border-top: 4px solid {cor_borda}; background-color: {bg_cor};"><div class="metric-title">Status no Sistema Central</div><div class="metric-value" style="color: {cor_borda}; font-size: 24px;">{status_f.upper()}</div></div>', unsafe_allow_html=True)

            df_hist_parc = df_financeiro[df_financeiro['empresa'].str.upper() == st.session_state.empresa_vinculada.upper()].copy()
            if not df_hist_parc.empty:
                df_hist_parc['ord_key'] = df_hist_parc['mes_ano'].apply(mes_ano_para_tupla)
                df_hist_parc = df_hist_parc.sort_values(by='ord_key', ascending=False).drop(columns=['ord_key'])
                df_hist_parc['diferenca'] = df_hist_parc.apply(lambda row: f"R$ {max(0.0, formatar_moeda_float(row['valor_faturado']) - formatar_moeda_float(row['valor_pago'])):.2f}", axis=1)
                with st.expander("Meu Histórico Completo de Faturas (Todos os Meses)"):
                    st.dataframe(
                        df_hist_parc[['mes_ano', 'valor_faturado', 'valor_pago', 'diferenca', 'status']].rename(columns={
                            'mes_ano': 'Competência', 'valor_faturado': 'Valor Cobrado (R$)', 'valor_pago': 'Valor Pago (R$)', 'diferenca': 'Em Aberto', 'status': 'Status'
                        }).style.map(formatar_status_financeiro, subset=['Status']),
                        use_container_width=True
                    )

            if modo_fat_p != 'Tradicional':
                st.write("---")
                try: mes_sp, ano_sp = mes_filtro_p.split('/')
                except: mes_sp, ano_sp = datetime.now().month, datetime.now().year
                
                with st.expander("Detalhar Fatura no Aplicativo"):
                    st.markdown(f"**Empresa:** {st.session_state.empresa_vinculada.upper()} | **Período de Referência:** {mes_filtro_p}")
                    dados_det = calcular_fatura_parceiro(st.session_state.empresa_vinculada, mes_sp, ano_sp, df_clientes, df_os, df_empresas)
                    st.write(f"- **Ciclo de Apuração:** {dados_det['dt_inicio'].strftime('%d/%m/%Y')} até {dados_det['dt_fim'].strftime('%d/%m/%Y')}")
                    st.write(f"- **Plano Contratado:** {dados_det['modo_fat']}")
                    st.write(f"- **Total Exato de Veículos na Base (Ativos):** {dados_det['total_v']}")
                    st.write(f"- **Total de Chamados Ordinários Encerrados no Ciclo:** {dados_det['total_os']}")
                    if dados_det['modo_fat'] == "Performance (Escalonado)":
                        st.write(f"- **Taxa de Acionamento Atingida:** {dados_det['taxa']:.1f}% (Faixa: {dados_det['faixa']})")
                    st.write(f"- **Valor Final Calculado:** R$ {dados_det['fatura_total']:.2f}")
                    st.info("Clique no botão abaixo para baixar o relatório completo com todas as placas cobradas.")

                st.write("")
                st.markdown(gerar_pdf_extrato_detalhado(st.session_state.empresa_vinculada, mes_sp, ano_sp, df_clientes, df_os, df_empresas), unsafe_allow_html=True)

    elif aba_selecionada == "Auditoria":
        st.markdown('<div class="section-title">Auditoria de Eventos</div>', unsafe_allow_html=True)
        st.write("Verifique com transparência as ações realizadas no sistema que envolvem a sua empresa.")
        
        empresa_upper = st.session_state.empresa_vinculada.upper()
        user_upper = st.session_state.user.upper()
        
        df_logs_parc = df_logs[
            (df_logs['usuario'].str.upper() == user_upper) | 
            (df_logs['detalhes'].str.upper().str.contains(empresa_upper, na=False))
        ].copy()
        
        if df_logs_parc.empty:
            st.info("Nenhuma atividade registrada por sua empresa ou central ainda.")
        else:
            df_logs_parc = df_logs_parc.sort_values(by='data_hora', ascending=False)
            busca_log_p = st.text_input("Buscar no registro (ex: placa, nome):")
            if busca_log_p:
                df_logs_parc = df_logs_parc[df_logs_parc['detalhes'].str.contains(busca_log_p, case=False, na=False) | df_logs_parc['acao'].str.contains(busca_log_p, case=False, na=False)]
            
            st.write("---")
            opcoes_log_p = {str(i): f"{r['data_hora']} - {r['acao']}" for i, r in df_logs_parc.iterrows()}
            log_sel_p = st.selectbox("Selecione um registro para ver os detalhes completos:", options=[""] + list(opcoes_log_p.keys()), format_func=lambda x: "Selecione..." if x == "" else opcoes_log_p[x])
            
            if log_sel_p != "":
                detalhe_row = df_logs_parc.loc[int(log_sel_p)]
                st.markdown(f"""
                <div style="background-color: {COR_BG_CARD}; color: {COR_TEXTO}; padding: 14px; border-radius: 8px; border: 1px solid {COR_BORDA}; border-left: 5px solid #6A1B9A; margin-bottom: 12px; font-size: 13px; box-shadow: 0 2px 6px rgba(0,0,0,0.06);">
                    <p style="margin-bottom:4px;"><strong>Data/Hora:</strong> {detalhe_row['data_hora']}</p>
                    <p style="margin-bottom:4px;"><strong>Feito por:</strong> {detalhe_row['usuario']}</p>
                    <p style="margin-bottom:4px;"><strong>Ação:</strong> {detalhe_row['acao']}</p>
                    <p style="margin-bottom:4px;"><strong>Detalhes Completos:</strong> {detalhe_row['detalhes']}</p>
                </div>
                """, unsafe_allow_html=True)
                
            st.write("---")
            st.dataframe(df_logs_parc[['data_hora', 'acao', 'detalhes']], use_container_width=True)
