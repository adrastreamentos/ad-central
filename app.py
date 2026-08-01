def fix_code():
    code = """
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
import calendar
from streamlit_drawable_canvas import st_canvas
import streamlit.components.v1 as components

st.set_page_config(page_title="Central 24h - AD Rastreamento", layout="wide", page_icon="🔒")

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

# ===================================================================================
# ESTILIZAÇÃO CSS
# ===================================================================================
st.markdown(\"\"\"
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-thumb { background: #d1c4e9; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #7B2CBF; }
    .main-title { font-size: 38px; font-weight: 900; background: -webkit-linear-gradient(45deg, #7B2CBF, #E53935); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin-bottom: 5px; }
    .subtitle { font-size: 16px; color: #666; text-align: center; margin-bottom: 35px; font-weight: 600; text-transform: uppercase; letter-spacing: 2px; }
    .stTabs [data-baseweb="tab"] { font-size: 15px; font-weight: 600; background-color: #f8f9fa; border: 1px solid #e0e0e0; color: #555; }
    .stTabs [aria-selected="true"] { background-color: #7B2CBF; color: white !important; }
    div.stButton > button:first-child { background-color: #7B2CBF; color: white; border-radius: 8px; font-weight: 700; }
    div.stButton > button:first-child:hover { background-color: #E53935; color: white; }
    .alert-box { padding: 16px; border-radius: 8px; margin: 15px 0; border-left: 6px solid; font-weight: 500; font-size: 15px; }
    .alert-danger { background-color: #ffebee; color: #c62828; border-color: #E53935; }
    .alert-success { background-color: #e8f5e9; color: #2e7d32; border-color: #4CAF50; }
    .info-box { background-color: #f3e5f5; color: #4a148c; border-color: #7B2CBF; padding: 16px; border-radius: 8px; margin: 15px 0; border-left: 6px solid; font-weight: 600; line-height: 1.6; }
    .metric-card { background-color: #ffffff; border-radius: 12px; padding: 25px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.06); margin-bottom: 20px; border: 1px solid #f0f0f0; }
    .metric-value { font-size: 32px; font-weight: 800; margin-top: 12px; }
    .val-pago { color: #2e7d32; } .val-atrasado { color: #E53935; }
    </style>
\"\"\", unsafe_allow_html=True)

# ===================================================================================
# FUNÇÕES GLOBAIS
# ===================================================================================
def obter_hora_brasilia(): return datetime.now(timezone(timedelta(hours=-3)))
def obter_hora_str(): return obter_hora_brasilia().strftime("%Y-%m-%d %H:%M:%S")
def apenas_numeros_letras(texto): return "".join(caractere for caractere in str(texto) if caractere.isalnum()).strip().lower()

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
                    return f"{rua}, Bairro {bairro}, {cidade}-{uf} | Número/Ref: "
        except: pass
    return None

def salvar_no_github(caminho_local):
    token = st.secrets.get("GITHUB_TOKEN", None)
    repo = "adrastreamentos/ad-central"
    if not token: return False, "Token ausente"
    url = f"https://api.github.com/repos/{repo}/contents/{caminho_local.replace(os.sep, '/')}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    for _ in range(3):
        try:
            res = requests.get(url, headers=headers)
            sha = res.json().get("sha", None) if res.status_code == 200 else None
            with open(caminho_local, "rb") as f: content = base64.b64encode(f.read()).decode("utf-8")
            data = {"message": f"🔥 Auto-salvamento: {caminho_local}", "content": content, "branch": "main"}
            if sha: data["sha"] = sha
            res_put = requests.put(url, headers=headers, json=data)
            if res_put.status_code in [200, 201]: return True, "Sucesso"
            else: time.sleep(2)
        except: time.sleep(2)
    return False, "Falha de conexão."

def salvar_dados(df, caminho):
    df.to_csv(caminho, index=False)
    return salvar_no_github(caminho)

def carregar_dados(caminho, col_obr):
    try:
        df = pd.read_csv(caminho, dtype=str)
        df.columns = df.columns.str.strip().str.lower()
        for col in col_obr:
            if col not in df.columns: 
                df[col] = datetime.now().strftime("%Y-%m-%d") if col == 'data_cadastro' else "" 
        for col in df.columns: df[col] = df[col].fillna("").astype(str).str.strip().str.replace(r'\\.0$', '', regex=True)
        return df
    except: return pd.DataFrame(columns=col_obr)

def registrar_atividade(usuario, acao, detalhes):
    global df_logs
    novo_log = pd.DataFrame([{'data_hora': obter_hora_str(), 'usuario': usuario, 'acao': acao, 'detalhes': detalhes}])
    df_logs = pd.concat([df_logs, novo_log], ignore_index=True)
    df_logs.to_csv(FILE_LOGS, index=False)
    salvar_no_github(FILE_LOGS)

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
    tb_precos = {
        "Enquadramento Base (Até 3%)":   {"50km": 6.90,   "100km": 8.90,   "200km": 11.20,  "Sem Limite": 11.20},
        "Enquadramento 3% a 5%":         {"50km": 9.10,   "100km": 13.15,  "200km": 17.20,  "Sem Limite": 17.20},
        "Enquadramento 5% a 7%":         {"50km": 11.80,  "100km": 17.20,  "200km": 22.60,  "Sem Limite": 22.60},
        "Enquadramento 7% a 10%":        {"50km": 14.50,  "100km": 21.25,  "200km": 28.00,  "Sem Limite": 28.00},
        "Enquadramento 10% a 13%":       {"50km": 24.00,  "100km": 35.80,  "200km": 47.60,  "Sem Limite": 47.60},
        "Enquadramento 13% a 17%":       {"50km": 33.50,  "100km": 50.40,  "200km": 67.20,  "Sem Limite": 67.20},
        "Enquadramento 17% a 20%":       {"50km": 50.00,  "100km": 74.00,  "200km": 98.00,  "Sem Limite": 98.00},
        "Enquadramento 20% a 30%":       {"50km": 68.00,  "100km": 102.00, "200km": 135.00, "Sem Limite": 135.00},
        "Enquadramento 30% a 40%":       {"50km": 86.00,  "100km": 130.00, "200km": 172.00, "Sem Limite": 172.00},
        "Enquadramento 40% a 50%":       {"50km": 104.00, "100km": 158.00, "200km": 209.00, "Sem Limite": 209.00},
        "Enquadramento 50% a 60%":       {"50km": 122.00, "100km": 186.00, "200km": 246.00, "Sem Limite": 246.00},
        "Enquadramento 60% a 70%":       {"50km": 140.00, "100km": 214.00, "200km": 283.00, "Sem Limite": 283.00},
        "Enquadramento Teto (> 70%)":    {"50km": 158.00, "100km": 242.00, "200km": 320.00, "Sem Limite": 320.00},
    }
    
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
    
    dia_venc_str, modo_fat_calc = '30', "Tradicional"
    emp_dados_fat = df_empresas_atuais[df_empresas_atuais['nome'].str.upper() == nome_empresa.upper()]
    if not emp_dados_fat.empty:
        dia_venc_str = str(emp_dados_fat.iloc[0].get('dia_vencimento', '30')).strip()
        modo_fat_calc = str(emp_dados_fat.iloc[0].get('modo_faturamento', 'Tradicional')).strip()
        if not dia_venc_str or dia_venc_str == 'nan': dia_venc_str = '30'

    dt_inicio, dt_fim = calcular_datas_ciclo(mes, ano, dia_venc_str)
    
    df_os_temp = df_os_atuais.copy()
    df_os_temp['data_hora'] = pd.to_datetime(df_os_temp['data_hora'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    os_filtro = df_os_temp[(df_os_temp['empresa'].str.upper() == nome_empresa.upper()) & 
                           (df_os_temp['status_os'].str.upper() == 'ENCERRADO') & 
                           (df_os_temp['data_hora'] >= dt_inicio) & 
                           (df_os_temp['data_hora'] <= dt_fim)]
                           
    total_os = len(os_filtro)
    taxa = (total_os / total_v * 100) if total_v > 0 else 0.0
    
    if taxa == 0.0: faixa = "Enquadramento Base (Até 3%)"
    elif taxa <= 3.0: faixa = "Enquadramento Base (Até 3%)"
    elif taxa <= 5.0: faixa = "Enquadramento 3% a 5%"
    elif taxa <= 7.0: faixa = "Enquadramento 5% a 7%"
    elif taxa <= 10.0: faixa = "Enquadramento 7% a 10%"
    elif taxa <= 13.0: faixa = "Enquadramento 10% a 13%"
    elif taxa <= 17.0: faixa = "Enquadramento 13% a 17%"
    elif taxa <= 20.0: faixa = "Enquadramento 17% a 20%"
    elif taxa <= 30.0: faixa = "Enquadramento 20% a 30%"
    elif taxa <= 40.0: faixa = "Enquadramento 30% a 40%"
    elif taxa <= 50.0: faixa = "Enquadramento 40% a 50%"
    elif taxa <= 60.0: faixa = "Enquadramento 50% a 60%"
    elif taxa <= 70.0: faixa = "Enquadramento 60% a 70%"
    else: faixa = "Enquadramento Teto (> 70%)"

    fatura_total, soma_adicionais, soma_excedentes, valor_base = 0.0, 0.0, 0.0, 0.0
    qtd_exc_50, qtd_exc_100 = 0, 0
    total_ac, acionamentos_isentos = 0, 0
    
    if modo_fat_calc == "Performance (Escalonado)":
        if total_v > 0:
            valor_base = 300.00
            fatura_total = valor_base 
            if total_v <= 20:
                adic_50 = tb_precos[faixa]['50km'] - tb_precos["Enquadramento Base (Até 3%)"]['50km']
                adic_100 = tb_precos[faixa]['100km'] - tb_precos["Enquadramento Base (Até 3%)"]['100km']
                adic_200 = tb_precos[faixa]['200km'] - tb_precos["Enquadramento Base (Até 3%)"]['200km']

                qtd_os_50 = sum(1 for _, o in os_filtro.iterrows() if '50' in str(o.get('plano_km', '')).strip())
                qtd_os_100 = sum(1 for _, o in os_filtro.iterrows() if '100' in str(o.get('plano_km', '')).strip())

                qtd_veic_50 = sum(1 for v in lista_veiculos_emp if v['plano'] == '50km')
                qtd_veic_100 = sum(1 for v in lista_veiculos_emp if v['plano'] == '100km')
                qtd_veic_200 = sum(1 for v in lista_veiculos_emp if v['plano'] in ['200km', 'Sem Limite'])

                cobrancas_50 = min(qtd_os_50, qtd_veic_50)
                cobrancas_100 = min(qtd_os_100, qtd_veic_100)

                soma_adicionais += (cobrancas_50 * adic_50)
                soma_adicionais += (cobrancas_100 * adic_100)
                soma_adicionais += (qtd_veic_200 * adic_200)

                fatura_total += soma_adicionais
            else:
                primeiros_20 = lista_veiculos_emp[:20]
                excedentes = lista_veiculos_emp[20:]
                for v in primeiros_20:
                    p_km = v['plano']
                    adicional = max(0.0, tb_precos[faixa].get(p_km, tb_precos[faixa]["50km"]) - tb_precos["Enquadramento Base (Até 3%)"].get(p_km, tb_precos["Enquadramento Base (Até 3%)"]["50km"]))
                    soma_adicionais += adicional
                    v['tipo_cobranca'] = 'Composição do Piso Base'
                    v['valor_cobrado'] = adicional
                for v in excedentes:
                    p_km = v['plano']
                    val_cheio = tb_precos[faixa].get(p_km, tb_precos[faixa]["50km"])
                    soma_excedentes += val_cheio
                    v['tipo_cobranca'] = 'Excedente (Valor Integral da Tabela)'
                    v['valor_cobrado'] = val_cheio
                fatura_total += (soma_adicionais + soma_excedentes)

    elif "Frota Pequena" in modo_fat_calc or "Até 40 Veículos" in modo_fat_calc:
        if "Frota Pequena" in modo_fat_calc:
            valor_base, acionamentos_isentos, taxa_50, taxa_100 = 300.00, 2, 50.00, 85.00
        elif "Opção A" in modo_fat_calc:
            valor_base, acionamentos_isentos, taxa_50, taxa_100 = 500.00, 2, 50.00, 85.00
        elif "Opção B" in modo_fat_calc:
            valor_base, acionamentos_isentos, taxa_50, taxa_100 = 500.00, 4, 80.00, 130.00

        if total_v > 0: fatura_total = valor_base
        
        acionamentos_50 = sum(1 for _, o in os_filtro.iterrows() if '50' in str(o.get('plano_km', '50km')).strip())
        acionamentos_100 = len(os_filtro) - acionamentos_50
        total_ac = acionamentos_50 + acionamentos_100
        
        if total_ac > acionamentos_isentos:
            isentos_restantes = acionamentos_isentos
            if acionamentos_50 >= isentos_restantes:
                pagantes_50 = acionamentos_50 - isentos_restantes
                pagantes_100 = acionamentos_100
            else:
                isentos_restantes -= acionamentos_50
                pagantes_50 = 0
                pagantes_100 = acionamentos_100 - isentos_restantes
                
            valor_exc_50 = pagantes_50 * taxa_50
            valor_exc_100 = pagantes_100 * taxa_100
            soma_excedentes = valor_exc_50 + valor_exc_100
            fatura_total += soma_excedentes
            qtd_exc_50, qtd_exc_100 = pagantes_50, pagantes_100
            
        for v in lista_veiculos_emp:
            v['tipo_cobranca'] = 'Incluso no Pacote (Plano Fixo)'
            v['valor_cobrado'] = 0.0
    else:
        valor_base, fatura_total = 0.0, 0.0
        for v in lista_veiculos_emp:
            v['tipo_cobranca'] = 'Tradicional / Manual'
            v['valor_cobrado'] = 0.0
            
    return {
        'fatura_total': fatura_total, 'total_v': total_v, 'total_os': total_os,
        'taxa': taxa, 'faixa': faixa, 'veiculos': lista_veiculos_emp,
        'valor_base': valor_base, 'soma_adicionais': soma_adicionais, 'soma_excedentes': soma_excedentes,
        'dt_inicio': dt_inicio, 'dt_fim': dt_fim, 'vencimento_dia': dia_venc_str,
        'modo_fat': modo_fat_calc, 'qtd_exc_50': qtd_exc_50, 'qtd_exc_100': qtd_exc_100,
        'total_ac': total_ac, 'acionamentos_isentos': acionamentos_isentos
    }

def gerar_texto_resumo_plano(dados_fat):
    modo = dados_fat.get('modo_fat', 'Tradicional')
    tot_v = dados_fat.get('total_v', 0)
    taxa = dados_fat.get('taxa', 0.0)
    faixa = dados_fat.get('faixa', 'Enquadramento Base (Até 3%)')
    fat_tot = dados_fat.get('fatura_total', 0.0)
    base = dados_fat.get('valor_base', 0.0)
    exc = dados_fat.get('soma_excedentes', 0.0)
    dt_ini = dados_fat['dt_inicio'].strftime('%d/%m/%Y')
    dt_fim = dados_fat['dt_fim'].strftime('%d/%m/%Y')
    
    periodo_str = f"📅 <b>Ciclo Vigente:</b> {dt_ini} a {dt_fim} (Fechamento: {dt_fim[:5]})"
    
    if modo == "Performance (Escalonado)":
        texto = f"{periodo_str}<br>📊 <b>Plano Ativo:</b> {modo}<br>🚗 <b>Frota Apurada:</b> {tot_v} veículos ativos.<br>"
        if taxa == 0.0:
            texto += f"🎯 <b style='color:#2e7d32;'>Taxa de Acionamento: 0.0% (Mês zerado)</b><br>"
        else:
            texto += f"🎯 <b>Taxa de Acionamento:</b> {taxa:.1f}%<br>"
            
        texto += f"📈 <b>Enquadramento Comercial:</b> {faixa}<br>"
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
            texto += f"💰 <b>Fatura Atualizada: R$ {fat_tot:.2f}</b> <span style='color:#E53935; font-size:14px;'>(R$ {base:.2f} Fixo + Adicional: R$ {exc:.2f} de {' e '.join(detalhe_exc)})</span>"
        else:
            texto += f"💰 <b>Fatura Atual: R$ {fat_tot:.2f}</b> <span style='color:#2e7d32; font-size:14px;'>(Uso operando perfeitamente dentro da franquia gratuita do pacote)</span>"
        return texto
    else:
        return f"{periodo_str}<br>📊 <b>Plano Ativo:</b> {modo}<br>🚗 <b>Base Apurada:</b> {tot_v} veículos | <b>Taxa de Acionamento (Informativa):</b> {taxa:.1f}%<br>💰 <b>Faturamento:</b> Lançamento Manual gerido pela Central"

def gerar_pdf_extrato_detalhado(nome_empresa, mes, ano, df_clientes_atuais, df_os_atuais, df_empresas_atuais):
    dados_fat = calcular_fatura_parceiro(nome_empresa, mes, ano, df_clientes_atuais, df_os_atuais, df_empresas_atuais)
    df_os_temp = df_os_atuais.copy()
    df_os_temp['data_hora'] = pd.to_datetime(df_os_temp['data_hora'], errors='coerce')
    os_mes = df_os_temp[(df_os_temp['empresa'].str.upper() == nome_empresa.upper()) & (df_os_temp['status_os'].str.upper() == 'ENCERRADO') & (df_os_temp['data_hora'] >= dados_fat['dt_inicio']) & (df_os_temp['data_hora'] <= dados_fat['dt_fim'])].sort_values(by='data_hora')

    linhas_os_html = ""
    if os_mes.empty: linhas_os_html = "<tr><td colspan='6' style='text-align: center; padding: 10px; color: #666;'>Nenhum acionamento registrado neste ciclo.</td></tr>"
    else:
        for _, r in os_mes.iterrows():
            linhas_os_html += f"<tr><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{r['id']}</td><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{str(r['data_hora'])[:16]}</td><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px; font-weight: bold;'>{r['placa']}</td><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{r['cliente_nome']}</td><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{r['tipo_servico']}</td><td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{r['localizacao']} ➔ {r['destino']}</td></tr>"

    linhas_veiculos_html = ""
    for idx_v, v in enumerate(dados_fat['veiculos']):
        linhas_veiculos_html += f"<tr><td style='border: 1px solid #ddd; padding: 6px; font-size: 11px;'>{idx_v + 1}</td><td style='border: 1px solid #ddd; padding: 6px; font-size: 11px; font-weight: bold;'>{v['placa']}</td><td style='border: 1px solid #ddd; padding: 6px; font-size: 11px;'>{v['cliente']}</td><td style='border: 1px solid #ddd; padding: 6px; font-size: 11px;'>{v['plano']}</td><td style='border: 1px solid #ddd; padding: 6px; font-size: 11px;'>{v['tipo_cobranca']}</td></tr>"

    str_inicio = dados_fat['dt_inicio'].strftime('%d/%m/%Y')
    str_fim = dados_fat['dt_fim'].strftime('%d/%m/%Y')
    timestamp_arquivo = int(time.time())
    modo_pdf = dados_fat.get('modo_fat', 'Tradicional')

    if modo_pdf == "Performance (Escalonado)":
        secao_tabela = f\"\"\"<div style="margin-bottom: 20px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #7B2CBF;">3. TABELA DE REFERÊNCIA (AMOSTRAGEM)</h3><p style="margin: 4px 0 10px 0; font-size: 12px; color: #666;">A tarifa mensal baseia-se na % de uso. Enquadramento atual de fechamento do cliente: <b>{dados_fat['faixa']}</b>.</p></div>\"\"\"
        secao_memoria = f\"\"\"<div style="margin-bottom: 20px; background-color: #f3e5f5; padding: 15px; border-radius: 6px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #7B2CBF;">4. MEMÓRIA DE CÁLCULO FINANCEIRO DETALHADA</h3><p style="margin: 4px 0; font-size: 13px;">(+) Franquia / Piso Mínimo Operacional (Base de até 20 veículos): <strong>R$ {dados_fat['valor_base']:.2f}</strong></p><p style="margin: 4px 0; font-size: 13px;">(+) Adicional de Risco Aplicado (Regra Suavizada para <=20): <strong>R$ {dados_fat['soma_adicionais']:.2f}</strong></p><p style="margin: 4px 0; font-size: 13px;">(+) Cobrança de Veículos Excedentes (A partir do 21º): <strong>R$ {dados_fat['soma_excedentes']:.2f}</strong></p><hr style="border: 0; border-top: 1px solid #ccc; margin: 10px 0;"><p style="margin: 8px 0; font-size: 18px; color: #7B2CBF; text-align: right;"><strong>VALOR TOTAL DA FATURA: R$ {dados_fat['fatura_total']:.2f}</strong></p></div>\"\"\"
    elif "Frota Pequena" in modo_pdf or "Até 40 Veículos" in modo_pdf:
        franquia_qtd = f"{dados_fat.get('acionamentos_isentos', 2)} guinchos"
        uso_qtd = f"{dados_fat.get('total_ac', 0)} de {dados_fat.get('acionamentos_isentos', 2)}"
        secao_tabela = f\"\"\"<div style="margin-bottom: 20px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #7B2CBF;">3. INFORMAÇÕES DO PACOTE CONTRATADO</h3><p style="margin: 4px 0 10px 0; font-size: 13px;"><strong>Plano:</strong> {modo_pdf}</p><p style="margin: 4px 0 10px 0; font-size: 13px;"><strong>Franquia Inclusa:</strong> {franquia_qtd} mensais (Planos 50km ou 100km).</p><p style="margin: 4px 0 10px 0; font-size: 13px;"><strong>Consumo no Ciclo:</strong> {uso_qtd} utilizados.</p></div>\"\"\"
        secao_memoria = f\"\"\"<div style="margin-bottom: 20px; background-color: #f3e5f5; padding: 15px; border-radius: 6px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #7B2CBF;">4. MEMÓRIA DE CÁLCULO FINANCEIRO DETALHADA</h3><p style="margin: 4px 0; font-size: 13px;">(+) Base do Pacote Mensal Fixo: <strong>R$ {dados_fat['valor_base']:.2f}</strong></p><p style="margin: 4px 0; font-size: 13px;">(+) Adicional de Acionamentos Excedentes (Fora da Franquia): <strong>R$ {dados_fat['soma_excedentes']:.2f}</strong></p><hr style="border: 0; border-top: 1px solid #ccc; margin: 10px 0;"><p style="margin: 8px 0; font-size: 18px; color: #7B2CBF; text-align: right;"><strong>VALOR TOTAL DA FATURA: R$ {dados_fat['fatura_total']:.2f}</strong></p></div>\"\"\"
    else:
        secao_tabela = ""
        secao_memoria = f\"\"\"<div style="margin-bottom: 20px; background-color: #f3e5f5; padding: 15px; border-radius: 6px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #7B2CBF;">4. MEMÓRIA DE CÁLCULO FINANCEIRO</h3><p style="margin: 4px 0; font-size: 13px;">Este cliente opera no modo Tradicional. O valor faturado é gerido manualmente.</p></div>\"\"\"

    html_content = f\"\"\"<html><head><meta charset='utf-8'></head><body style="font-family: Arial, sans-serif; max-width: 850px; margin: 0 auto; padding: 20px; color: #333;"><div style="text-align: center; margin-bottom: 20px;"><h2 style="margin: 0; color: #7B2CBF; font-size: 24px;">AD RASTREAMENTO VEICULAR</h2><p style="margin: 5px 0; font-size: 14px; color: #555; text-transform: uppercase; font-weight: bold;">Extrato Detalhado de Faturamento e Auditoria</p><p style="margin: 3px 0; font-size: 13px; color: #777;">Empresa: <strong>{nome_empresa.upper()}</strong> | Competência Mês: {mes}/{ano}</p></div><hr style="border: 0; border-top: 2px solid #7B2CBF; margin-bottom: 20px;"><div style="margin-bottom: 20px; background-color: #f8f9fa; padding: 15px; border-radius: 6px; border: 1px solid #eee;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #7B2CBF;">1. RESUMO OPERACIONAL DO CICLO</h3><p style="margin: 4px 0; font-size: 13px;"><strong>Período de Apuração:</strong> {str_inicio} até {str_fim} (Vencimento dia {dados_fat['vencimento_dia']})</p><p style="margin: 4px 0; font-size: 13px;"><strong>Total Exato de Veículos na Base (Ativos):</strong> {dados_fat['total_v']} veículos</p><p style="margin: 4px 0; font-size: 13px;"><strong>Total de Acionamentos (OS Encerradas no Ciclo):</strong> {dados_fat['total_os']} atendimentos</p><p style="margin: 4px 0; font-size: 13px;"><strong>Modo Comercial Aplicado:</strong> {modo_pdf}</p></div><div style="margin-bottom: 20px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #7B2CBF;">2. HISTÓRICO DE ATENDIMENTOS DO CICLO</h3><table style="width: 100%; border-collapse: collapse;"><thead><tr style="background-color: #7B2CBF; color: white;"><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">OS</th><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">Data/Hora</th><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">Placa</th><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">Cliente</th><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">Serviço</th><th style="border: 1px solid #ddd; padding: 8px; font-size: 12px;">Trajeto (Origem ➔ Destino)</th></tr></thead><tbody>{linhas_os_html}</tbody></table></div>{secao_tabela}{secao_memoria}<div style="margin-bottom: 20px;"><h3 style="margin: 0 0 10px 0; font-size: 15px; color: #7B2CBF;">5. ANEXO DE AUDITORIA: RELAÇÃO DE TODAS AS PLACAS</h3><p style="margin: 4px 0 10px 0; font-size: 11px; color: #666;">Abaixo constam rigorosamente todos os {dados_fat['total_v']} veículos lidos no banco de dados com status ativo para gerar esta fatura.</p><table style="width: 100%; border-collapse: collapse; font-size: 11px;"><thead><tr style="background-color: #e0e0e0; color: #333;"><th style="border: 1px solid #ddd; padding: 6px;">#</th><th style="border: 1px solid #ddd; padding: 6px;">Placa Identificada</th><th style="border: 1px solid #ddd; padding: 6px;">Nome do Cliente Cadastrado</th><th style="border: 1px solid #ddd; padding: 6px;">Plano (KM)</th><th style="border: 1px solid #ddd; padding: 6px;">Enquadramento de Cobrança</th></tr></thead><tbody>{linhas_veiculos_html}</tbody></table></div></body></html>\"\"\"
    b64 = base64.b64encode(html_content.encode('utf-8')).decode()
    return f'<a href="data:text/html;base64,{b64}" download="Extrato_Auditavel_{nome_empresa}_{mes}_{ano}_{timestamp_arquivo}.html" style="text-decoration: none;"><button style="background-color: #7B2CBF; color: white; padding: 12px 24px; border: none; border-radius: 6px; font-size: 15px; font-weight: bold; cursor: pointer;">📄 Baixar Extrato Oficial e Auditável (PDF)</button></a>'

# ===================================================================================
# CARREGAMENTO DOS BANCOS DE DADOS
# ===================================================================================
FOLDER = "AD_Assistencia"
os.makedirs(FOLDER, exist_ok=True)
FILE_CLIENTES = os.path.join(FOLDER, "banco_clientes.csv")
FILE_EMPRESAS = os.path.join(FOLDER, "banco_empresas.csv")
FILE_PRESTADORES = os.path.join(FOLDER, "banco_prestadores.csv")
FILE_OS = os.path.join(FOLDER, "banco_os.csv")
FILE_LOGS = os.path.join(FOLDER, "banco_logs.csv")
FILE_FINANCEIRO = os.path.join(FOLDER, "banco_financeiro.csv")
FILE_LOC = os.path.join(FOLDER, "banco_loc.csv")

col_cli = ['id','nome','cpf','tel','endereco','cidade','cep','plano_km','est','emp_name','status','vei','pla','vei_2','pla_2','veiculos_lista', 'data_cadastro']
col_emp = ['cnpj','nome','responsavel','telefone','email','est','status', 'modo_faturamento', 'dia_vencimento']
col_pre = ['id','nome','cpf','tipo','telefone','endereco','cidade','cep','est','status','homologado','senha','frota']
col_os = ['id','data_hora','cliente_id','cliente_nome','placa','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os','veiculo_desc','plano_km','valor_cobrado']
col_fin = ['id', 'mes_ano', 'empresa', 'valor_faturado', 'valor_pago', 'status']
col_logs = ['data_hora', 'usuario', 'acao', 'detalhes']
col_loc = ['placa', 'data_hora', 'link_maps']

if not os.path.exists(FILE_CLIENTES): pd.DataFrame(columns=col_cli).to_csv(FILE_CLIENTES, index=False)
if not os.path.exists(FILE_EMPRESAS): pd.DataFrame(columns=col_emp).to_csv(FILE_EMPRESAS, index=False)
if not os.path.exists(FILE_PRESTADORES): pd.DataFrame(columns=col_pre).to_csv(FILE_PRESTADORES, index=False)
if not os.path.exists(FILE_OS): pd.DataFrame(columns=col_os).to_csv(FILE_OS, index=False)
if not os.path.exists(FILE_FINANCEIRO): pd.DataFrame(columns=col_fin).to_csv(FILE_FINANCEIRO, index=False)
if not os.path.exists(FILE_LOGS): pd.DataFrame(columns=col_logs).to_csv(FILE_LOGS, index=False)
if not os.path.exists(FILE_LOC): pd.DataFrame(columns=col_loc).to_csv(FILE_LOC, index=False)

df_clientes = carregar_dados(FILE_CLIENTES, col_cli)
df_empresas = carregar_dados(FILE_EMPRESAS, col_emp)
df_prestadores = carregar_dados(FILE_PRESTADORES, col_pre)
df_os = carregar_dados(FILE_OS, col_os)
df_financeiro = carregar_dados(FILE_FINANCEIRO, col_fin)
df_logs = carregar_dados(FILE_LOGS, col_logs)
df_loc = carregar_dados(FILE_LOC, col_loc)

# ===================================================================================
# PORTAL DO CLIENTE (CAPTURA DE GPS SEM APP) - RODA ANTES DO LOGIN
# ===================================================================================
portal_atual = st.query_params.get("portal", "")
if portal_atual == "cliente":
    st.markdown('<div class="main-title">AD Rastreamento</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Assistência 24h - Resgate</div>', unsafe_allow_html=True)
    placa_param = st.query_params.get("placa", "N/D")
    
    html_code = f\"\"\"
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    body {{ font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #f8f9fa; }}
    .btn {{ background-color: #E53935; color: white; padding: 20px; font-size: 18px; border: none; border-radius: 8px; cursor: pointer; width: 100%; max-width: 300px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.2); margin-top: 20px; }}
    .btn:active {{ background-color: #b71c1c; }}
    #msg {{ margin-top: 20px; font-size: 16px; color: #555; font-weight: bold; }}
    </style>
    </head>
    <body>
    <h3 style="color: #7B2CBF; margin-top:0;">Localização de Emergência</h3>
    <p>Precisamos saber onde você está para enviar o guincho exato até o veículo placa <b>{placa_param}</b>.</p>
    <button class="btn" onclick="getLocation()">📍 ENVIAR MINHA LOCALIZAÇÃO</button>
    <p id="msg"></p>
    <script>
    function getLocation() {{
        document.getElementById("msg").innerHTML = "Aguardando GPS... Clique em 'Permitir' se o seu celular pedir.";
        if (navigator.geolocation) {{
            navigator.geolocation.getCurrentPosition(showPosition, showError, {{enableHighAccuracy: true}});
        }} else {{
            document.getElementById("msg").innerHTML = "Seu navegador não suporta GPS.";
        }}
    }}
    function showPosition(position) {{
        var lat = position.coords.latitude;
        var lon = position.coords.longitude;
        document.getElementById("msg").innerHTML = "Sinal capturado! Enviando para a Central... 🚀";
        window.parent.location.href = "?portal=cliente_salvo&placa={placa_param}&lat=" + lat + "&lon=" + lon;
    }}
    function showError(error) {{
        switch(error.code) {{
            case error.PERMISSION_DENIED:
                document.getElementById("msg").innerHTML = "Você negou o acesso ao GPS. Libere a permissão e tente novamente.";
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
    \"\"\"
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
        novo_loc = pd.DataFrame([{'placa': placa_cliente, 'data_hora': obter_hora_str(), 'link_maps': link_maps}])
        df_loc = pd.concat([df_loc, novo_loc], ignore_index=True)
        salvar_dados(df_loc, FILE_LOC)
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
    elif sess_param and sess_param.startswith("prest_"):
        nome_prest = urllib.parse.unquote(sess_param.split("prest_")[1])
        st.session_state.update({"logado": True, "user": nome_prest.upper(), "perfil": "Prestador", "empresa_vinculada": ""})

if not st.session_state.logado:
    st.markdown('<div class="main-title">AD Rastreamento Veicular <span style="font-size: 16px; color: #ccc;">🚀 v8.6.1</span></div>', unsafe_allow_html=True)
    col_esp1, col_meio, col_esp2 = st.columns([1, 2, 1])
    with col_meio:
        if portal_atual == "prestador":
            st.markdown('<div class="subtitle">🚛 Portal Exclusivo do Prestador</div>', unsafe_allow_html=True)
            tab_login, tab_cadastro = st.tabs(["🔐 Entrar", "📝 Quero me Cadastrar"])
            with tab_login:
                usuario_input = apenas_numeros_letras(st.text_input("Seu Nome (Usuário):"))
                senha_input = apenas_numeros_letras(st.text_input("Sua Senha (ou CPF):", type="password"))
                if st.button("Acessar Meu Painel", use_container_width=True, key="btn_login_prest"):
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
col_user, col_logout = st.columns([5, 1])
with col_user: st.write(f"**Central AD 24h | Operador:** `{st.session_state.user}`")
with col_logout:
    if st.button("Sair / Logoff", key="btn_logout_master"):
        st.session_state.logado = False
        st.query_params.clear()
        st.rerun()

# ===================================================================================
# INTERFACE 1: ADMIN MASTER
# ===================================================================================
if st.session_state.perfil == "Admin":
    menu = st.tabs(["📋 Nova OS", "📊 Relatórios & PDF", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores", "💾 Backup", "🕵️ Auditoria", "💰 Financeiro"])
    
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
                                        if v.get('Placa'): lista_frota_opcoes.append(f"{v.get('Modelo/Ano', 'Veículo')} - Placa: {v.get('Placa')}")
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
                                    elif "ELÉTRICA" in serv or "ELETRICA" in serv: uso_atual["PANE ELÉTRICA"] += 1
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
                                    if cliente_inativo: st.markdown('<div class="alert-box alert-danger" style="font-size: 16px; text-align: center;">🚫 ALERTA: CLIENTE INATIVO 🚫<br><span style="font-size: 14px; font-weight: normal;">Possível inadimplência ou cancelamento.</span></div>', unsafe_allow_html=True)
                                    if bloqueio_60: st.markdown(f'<div class="alert-box alert-danger" style="font-size: 16px; text-align: center;">🚫 ALERTA: REGRA DOS 60 DIAS ATIVA 🚫<br><span style="font-size: 14px; font-weight: bold;">{msg_bloqueio_60}</span></div>', unsafe_allow_html=True)
                                    if limite_excedido: st.markdown(f'<div class="alert-box alert-danger" style="font-size: 16px; text-align: center;">🚫 ALERTA: LIMITE ANUAL ESTOURADO 🚫<br><span style="font-size: 14px; font-weight: bold;">Esta placa já utilizou o limite máximo de {tipo_servico} no ciclo de contrato atual.</span></div>', unsafe_allow_html=True)
                                        
                                    liberar_excecao = st.checkbox("⚠️ Ciente dos bloqueios acima: Liberar Atendimento por Exceção")
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
            veiculo_avulso, placa_avulso = col_av1.text_input("Veículo (Modelo/Ano/Cor):"), col_av2.text_input("Placa do Veículo:")
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
            st.subheader("🛠️ Destino e Acionamento do Prestador")
            
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
            
            st.markdown("##### 📍 Endereços de Origem e Destino")
            st.info("Caso o cliente não saiba explicar onde está, use o botão verde abaixo para enviar o link de captura de GPS. Quando ele clicar, o endereço de origem será preenchido sozinho.")
            link_captura = f"https://ad-central-mrssupqbb9ux69bi4qgisa.streamlit.app/?portal=cliente&placa={placa_alvo}"
            col_loc1, col_loc2 = st.columns([1, 1])
            texto_zap_loc = f"Olá! Aqui é da *Central AD Assistência 24h*.\\n\\nPara despacharmos o seu socorro rápido, precisamos da sua localização exata. Por favor, clique no link abaixo, permita o uso do GPS e aperte no botão 'ENVIAR MINHA LOCALIZAÇÃO':\\n\\n{link_captura}"
            link_w_loc = f"https://api.whatsapp.com/send?phone=55{tel_envio_link}&text={urllib.parse.quote(texto_zap_loc)}"
            
            with col_loc1:
                st.markdown(f'<a href="{link_w_loc}" target="_blank"><button style="background-color: #25D366; color: white; padding: 10px; width: 100%; border: none; border-radius: 5px; font-weight: bold; cursor: pointer;">📲 1. Enviar Link no WhatsApp do Cliente</button></a>', unsafe_allow_html=True)
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
            c_orig1, c_orig2 = st.columns([1, 4])
            cep_orig = c_orig1.text_input("CEP Origem (Opcional):", placeholder="Somente números")
            if c_orig1.button("🔍 Buscar Origem", use_container_width=True, key="btn_cep_orig_admin"):
                end_orig = buscar_endereco_por_cep(cep_orig)
                if end_orig:
                    st.session_state.os_loc_val = end_orig
                    st.rerun()
                else: st.error("CEP inválido ou não encontrado.")
            localizacao = c_orig2.text_input("Endereço de Origem Completo (Onde pegar o veículo):", value=st.session_state.os_loc_val)
            st.session_state.os_loc_val = localizacao

            c_dest1, c_dest2 = st.columns([1, 4])
            cep_dest = c_dest1.text_input("CEP Destino (Opcional):", placeholder="Somente números")
            if c_dest1.button("🔍 Buscar Destino", use_container_width=True, key="btn_cep_dest_admin"):
                end_dest = buscar_endereco_por_cep(cep_dest)
                if end_dest:
                    st.session_state.os_dest_val = end_dest
                    st.rerun()
                else: st.error("CEP inválido ou não encontrado.")
            destino = c_dest2.text_input("Endereço de Destino Completo (Onde deixar o veículo):", value=st.session_state.os_dest_val)
            st.session_state.os_dest_val = destino
            
            obs = st.text_area("Observações Extras para o Guincheiro:", value=st.session_state.os_obs_val)
            st.session_state.os_obs_val = obs
            st.write("---")
            
            if is_excecao_flag:
                emp_match = df_empresas[df_empresas['nome'].str.upper() == empresa_os.upper()]
                resp_empresa = emp_match.iloc[0].get('responsavel', 'Responsável') if not emp_match.empty else 'Responsável'
                tel_responsavel = apenas_numeros_letras(emp_match.iloc[0].get('telefone', '')) if not emp_match.empty else ''
                if not tel_responsavel: tel_responsavel = tel_envio_link

                texto_pix = (f"🚨 *ATENDIMENTO DE EXCEÇÃO - AD RASTREAMENTO* 🚨\\n\\nOlá *{resp_empresa}* (Empresa: *{empresa_os}*),\\n\\nO acionamento de exceção para o veículo *{veiculo_desc_alvo}* - Placa: *{placa_alvo}* foi autorizado.\\n\\n📋 *Detalhes completos do Atendimento:*\\n• Serviço: {tipo_servico} ({motivo_servico})\\n• Onde pegar (Origem): {localizacao if localizacao else 'A informar'}\\n• Onde deixar (Destino): {destino if destino else 'A informar'}\\n• Motivo da Exceção: Limite Anual ou Carência de 60 dias atingida\\n\\n💰 *Valor do Serviço Extra:* R$ {valor_excecao_val}\\n\\n⚠️ *Atenção:* O deslocamento do prestador será iniciado *somente após o envio do comprovante* de pagamento.\\n\\n📲 *DADOS PARA PAGAMENTO (PIX):*\\nChave PIX (CNPJ): *55496449000184*\\nNome: *AD Rastreamento Veicular LTDA*\\n\\nEnvie o comprovante nesta conversa para despacharmos o socorro imediatamente!")
                link_w_pix = f"https://api.whatsapp.com/send?phone=55{tel_responsavel}&text={urllib.parse.quote(texto_pix)}"
                if not tel_responsavel: st.warning("⚠️ Atenção: Nenhum telefone cadastrado para a empresa ou cliente. Cadastre no perfil para enviar direto.")
                st.markdown(f'<a href="{link_w_pix}" target="_blank" style="text-decoration: none;"><button style="background-color: #00bfa5; color: white; padding: 10px 20px; border: none; border-radius: 6px; font-weight: bold; margin-bottom: 5px; width: 100%;">💬 PASSO EXTRA: Enviar Cobrança PIX para o Responsável ({resp_empresa})</button></a>', unsafe_allow_html=True)

            texto_btn_os = "🚀 Finalizar e Gerar OS do Guincho"
            if st.button(texto_btn_os, type="primary", key="btn_gerar_os_admin"):
                if not prestador_final or not tel_prestador_final: st.error("Identifique o Nome e o Telefone do prestador.")
                elif not localizacao: st.error("O Endereço de Origem é obrigatório!")
                else:
                    with st.spinner("Registrando OS e sincronizando com a nuvem..."):
                        nova_id = int(df_os['id'].astype(float).max() + 1) if not df_os.empty else 1
                        nova_os = pd.DataFrame([{'id': str(nova_id), 'data_hora': obter_hora_str(), 'cliente_id': str(cliente_id_os), 'cliente_nome': str(cliente_nome_os).upper(), 'placa': placa_alvo, 'veiculo_desc': str(veiculo_desc_alvo).upper(), 'empresa': empresa_os, 'tipo_servico': tipo_servico, 'motivo': motivo_servico, 'prestador': f"{prestador_final} | Telefone/Zap: {tel_prestador_final}", 'localizacao': localizacao, 'destino': destino, 'obs': obs, 'status_os': "EM ATENDIMENTO", 'plano_km': plano_km_os, 'valor_cobrado': valor_cobrado_os}])
                        df_os_temp = pd.concat([df_os, nova_os], ignore_index=True)
                        sucesso, erro = salvar_dados(df_os_temp, FILE_OS)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "NOVA OS", f"Abriu chamado {nova_id} para a placa {placa_alvo}")
                            st.success(f"✅ Chamado Nº {nova_id} Aberto! Redirecionando...")
                            for k in ["os_busca_val", "os_cli_val", "os_loc_val", "os_dest_val", "os_obs_val"]: st.session_state[k] = ""
                            time.sleep(1.5); st.rerun()
                        else: st.error(f"⚠️ Erro ao salvar OS na nuvem: {erro}")

    with menu[1]:
        st.subheader("📊 Gestão de Chamados e Relatórios")
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
                                st.success("✅ OS atualizada com sucesso! O cálculo de acionamento foi reajustado."); time.sleep(1.5); st.rerun()
                            else: st.error(f"Erro na nuvem: {erro}")
                
                if "os_del_confirm" not in st.session_state: st.session_state.os_del_confirm = None
                if st.session_state.os_del_confirm != os_id_edit:
                    if st.button("🗑️ Excluir esta OS permanentemente", key="btn_del_os"): st.session_state.os_del_confirm = os_id_edit; st.rerun()
                if st.session_state.get("os_del_confirm") == os_id_edit:
                    st.error(f"⚠️ Atenção: Deseja realmente excluir a OS {os_id_edit}?")
                    col_s, col_n = st.columns(2)
                    if col_s.button("✅ Sim, excluir OS", key="btn_sim_del_os"):
                        with st.spinner("Excluindo..."):
                            os_apagada = df_os[df_os['id'].astype(str) == str(os_id_edit)].iloc[0]
                            detalhes_exclusao_os = f"Apagou OS ID: {os_id_edit} | Cliente: {os_apagada['cliente_nome']} | Placa: {os_apagada['placa']} | Empresa: {os_apagada['empresa']}"
                            df_os = df_os[df_os['id'].astype(str) != str(os_id_edit)]
                            sucesso, erro = salvar_dados(df_os, FILE_OS)
                            if sucesso:
                                registrar_atividade(st.session_state.user, "EXCLUSÃO OS", detalhes_exclusao_os)
                                st.success("🗑️ OS excluída! Taxa de acionamento atualizada."); st.session_state.os_del_confirm = None; time.sleep(1.5); st.rerun()
                            else: st.error(f"Erro: {erro}")
                    if col_n.button("❌ Não, cancelar", key="btn_nao_del_os"): st.session_state.os_del_confirm = None; st.rerun()
            else: st.warning("Nenhuma OS encontrada com esse ID.")

        st.write("---")
        visao_relatorio = st.radio("Escolha a Visão:", ["🚨 OS em Andamento (Gerenciar)", "✅ Histórico e Gerar PDF (Finalizadas)", "Tabela Geral"], horizontal=True)
        if visao_relatorio == "🚨 OS em Andamento (Gerenciar)":
            df_abertas = df_os[~df_os['status_os'].str.upper().isin(['ENCERRADO', 'CANCELADO'])]
            if df_abertas.empty: st.success("Nenhum chamado pendente no momento!")
            else:
                lista_abertas = [f"OS Nº: {r['id']} | Status: {r['status_os']} | Placa: {r.get('placa','N/D')}" for _, r in df_abertas.iterrows()]
                os_sel_str = st.selectbox("Selecione o chamado para Gerenciar / Dar Baixa:", lista_abertas)
                os_id_alvo = os_sel_str.split("|")[0].replace("OS Nº:", "").strip()
                row_os = df_abertas[df_abertas['id'].astype(str) == os_id_alvo].iloc[0]
                status_dessa_os = str(row_os['status_os']).upper()
                prestador_info = str(row_os['prestador'])
                prestador_nome_puro = prestador_info.split(" | ")[0].strip()
                tel_prestador_final = prestador_info.split("Telefone/Zap: ")[1].strip() if "Telefone/Zap: " in prestador_info else ""
                cli_id_os = str(row_os['cliente_id'])
                df_cli_orig = df_clientes[df_clientes['id'].astype(str) == cli_id_os]
                tel_cliente_os = df_cli_orig.iloc[0]['tel'] if not df_cli_orig.empty else ""
                
                if status_dessa_os == 'FINALIZADO PELO PRESTADOR': st.markdown('<div class="alert-box alert-success">🏁 O PRESTADOR CHEGOU AO DESTINO E FINALIZOU NO APLICATIVO!</div>', unsafe_allow_html=True)
                elif status_dessa_os == 'EM ROTA (VISTORIA OK)': st.markdown('<div class="alert-box alert-info">📸 Vistoria de Entrada Concluída! O prestador já anexou as fotos e a assinatura.</div>', unsafe_allow_html=True)
                else: st.markdown('<div class="alert-box alert-danger">⏳ Aguardando Vistoria de Entrada pelo Prestador...</div>', unsafe_allow_html=True)
                
                link_app_prestador = f"https://ad-central-mrssupqbb9ux69bi4qgisa.streamlit.app/?portal=prestador&session=prest_{urllib.parse.quote(prestador_nome_puro)}"
                texto_whatsapp = (f"*{str(row_os['empresa']).upper()} - ASSISTÊNCIA 24H*\\n-----------------------------------------\\n*Chamado Nº:* {row_os['id']}\\n*Data/Hora:* {row_os['data_hora']}\\n*Plano KM:* {row_os.get('plano_km', 'N/D')}\\n*Valor Particular:* R$ {row_os.get('valor_cobrado', '0,00')}\\n*Serviço:* {row_os['tipo_servico']} | *Motivo:* {row_os['motivo']}\\n\\n*Cliente:* {str(row_os['cliente_nome']).upper()}\\n*Telefone do Cliente:* {tel_cliente_os}\\n\\n*Veículo:* {row_os.get('veiculo_desc', 'N/D')} - Placa: {row_os.get('placa', 'N/D')}\\n\\n*Origem:* {row_os['localizacao']}\\n*Destino:* {row_os['destino']}\\n\\n*Obs:* {row_os['obs']}\\n\\n🔗 *Acesse seu painel para Vistoria:* {link_app_prestador}")
                link_w = f"https://api.whatsapp.com/send?phone=55{tel_prestador_final}&text={urllib.parse.quote(texto_whatsapp)}"
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1: st.markdown(f'<a href="{link_w}" target="_blank"><button style="background-color: #25D366; color: white; padding: 10px 20px; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; width: 100%;">📲 Enviar OS para o Prestador</button></a>', unsafe_allow_html=True)
                with col_btn2:
                    texto_botao = "🔒 Confirmar Entrega e Dar Baixa Definitiva (Encerrar OS)" if status_dessa_os == 'FINALIZADO PELO PRESTADOR' else "🔒 Forçar Encerramento da OS Manualmente"
                    if st.button(texto_botao, key="btn_encerrar_os"):
                        with st.spinner("Encerrando OS..."):
                            df_os.loc[df_os['id'].astype(str) == os_id_alvo, 'status_os'] = "ENCERRADO"
                            sucesso, erro = salvar_dados(df_os, FILE_OS)
                            if sucesso:
                                registrar_atividade(st.session_state.user, "ENCERRAMENTO OS", f"Finalizou o chamado {os_id_alvo}")
                                st.success(f"🎉 Chamado Nº {os_id_alvo} Encerrado com sucesso!"); time.sleep(1.5); st.rerun()
                            else: st.error(f"Erro na nuvem: {erro}")
        elif visao_relatorio == "✅ Histórico e Gerar PDF (Finalizadas)":
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
        else: st.dataframe(df_os, use_container_width=True)

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
                                c2.write(f"**Endereço:** {cli_data.get('endereco', 'N/D')} - {cli_data.get('cidade', 'N/D')}/{cli_data.get('est', 'N/D')}"); c2.write(f"**Status:** {'🟢 Ativo' if cli_data['status'] == 'Ativo' else '🔴 Inativo'}")
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
                                    st.session_state[key_sel_admin] = ""; st.rerun()

        elif opcao_cli == "Incluir Novo":
            c1, c2 = st.columns(2)
            nome_in = c1.text_input("Nome Completo:", value=st.session_state.get("cli_inc_nome", ""))
            st.session_state.cli_inc_nome = nome_in
            cpf_raw = c2.text_input("CPF/CNPJ:", value=st.session_state.get("cli_inc_cpf", ""))
            st.session_state.cli_inc_cpf = cpf_raw
            tel_raw = c1.text_input("Telefone de Contato:", value=st.session_state.get("cli_inc_tel", ""))
            st.session_state.cli_inc_tel = tel_raw
            end_in = c2.text_input("Endereço Completo:", value=st.session_state.get("cli_inc_end", ""))
            st.session_state.cli_inc_end = end_in
            cid_in = c1.text_input("Cidade:", value=st.session_state.get("cli_inc_cid", ""))
            st.session_state.cli_inc_cid = cid_in
            cep_in = c2.text_input("CEP:", value=st.session_state.get("cli_inc_cep", ""))
            st.session_state.cli_inc_cep = cep_in
            cad_data = c1.date_input("Data de Cadastro (Início do Contrato):", value=datetime.now())
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
                        dt_str_save = cad_data.strftime("%Y-%m-%d")
                        novo = pd.DataFrame([{'id': str(prox), 'nome': nome, 'cpf': cpf, 'tel': tel, 'endereco': end_in, 'cidade': cid_in.upper(), 'cep': cep_in, 'plano_km': plano_km, 'vei': vei_prin, 'pla': pla_prin, 'est': est, 'emp_name': emp.upper(), 'status': status, 'veiculos_lista': frota_json_str, 'data_cadastro': dt_str_save}])
                        df_clientes_temp = pd.concat([df_clientes, novo], ignore_index=True)
                        sucesso, erro = salvar_dados(df_clientes_temp, FILE_CLIENTES)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "NOVO CLIENTE", f"Cadastrou {nome} para a empresa {emp}")
                            st.success("✅ Cliente cadastrado com sucesso!")
                            for k in ["cli_inc_nome", "cli_inc_cpf", "cli_inc_tel", "cli_inc_end", "cli_inc_cid", "cli_inc_cep"]: st.session_state[k] = ""
                            st.session_state.aba_cli = "Listar"
                            time.sleep(1); st.rerun()
                        else:
                            st.error(f"⚠️ Erro ao salvar cliente na nuvem: {erro}")
                        
        elif opcao_cli == "Importação em Lote":
            lista_empresas_disponiveis = [str(e['nome']).upper() for _, e in df_empresas.iterrows()] if not df_empresas.empty else ["NENHUMA EMPRESA CADASTRADA"]
            empresa_selecionada = st.selectbox("Selecione a Empresa Vinculada para esta importação:", options=lista_empresas_disponiveis)
            arquivo_csv_upload = st.file_uploader("Selecione o arquivo CSV da frota do parceiro", type=["csv"])
            if arquivo_csv_upload is not None:
                if st.button("Iniciar Importação e Salvar no GitHub"):
                    st.info("Atenção: A função de importação necessita da biblioteca pandas.")
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
                    try: val_data_cad = datetime.strptime(str(dados_ant.get('data_cadastro', ''))[:10], "%Y-%m-%d").date()
                    except: val_data_cad = datetime.now().date()
                    cad_data = c1.date_input("Data de Cadastro (Início do Contrato):", value=val_data_cad)
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
                                dt_str_save = cad_data.strftime("%Y-%m-%d")
                                df_clientes.loc[df_clientes['id'].astype(str) == c_target, ['nome','cpf','tel','endereco','cidade','cep','plano_km','vei','pla','est','emp_name','status','veiculos_lista','data_cadastro']] = [nome, cpf, tel, end_in, cid_in.upper(), cep_in, plano_km, vei_prin, pla_prin, est, emp.upper(), status, frota_json_str, dt_str_save]
                                sucesso, erro = salvar_dados(df_clientes, FILE_CLIENTES)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EDIÇÃO DE CLIENTE", f"Editou os dados do cliente {nome}")
                                    st.success("✅ Alterações salvas com sucesso!"); st.session_state.aba_cli = "Listar"; time.sleep(1); st.rerun()
                                else:
                                    st.error(f"⚠️ Erro ao salvar edição na nuvem: {erro}")

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
                                cliente_apagado = df_clientes[df_clientes['id'].astype(str) == c_target_del].iloc[0]
                                detalhes_del = f"Apagou o cliente -> ID: {c_target_del} | Nome: {cliente_apagado['nome']} | CPF: {cliente_apagado.get('cpf','')} | Empresa: {cliente_apagado.get('emp_name','')}"
                                df_clientes = df_clientes[df_clientes['id'].astype(str) != c_target_del]
                                sucesso, erro = salvar_dados(df_clientes, FILE_CLIENTES)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EXCLUSÃO CLIENTE", detalhes_del)
                                    st.success("🗑️ Cliente excluído permanentemente!"); st.session_state.cli_del_confirm = None; st.session_state.aba_cli = "Listar"; time.sleep(1); st.rerun()
                                else: st.error(f"Falha na nuvem: {erro}")
                        if col_nao.button("❌ Não, cancelar"): st.session_state.cli_del_confirm = None; st.rerun()

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
            
            c_v1, c_v2, c_v3 = st.columns(3)
            stat_e = c_v1.selectbox("Status Parceria:", ["Ativo", "Inativo"], index=0)
            modo_fat_e = c_v2.selectbox("Modo de Faturamento:", MODOS_FATURAMENTO, index=0)
            dia_v_e = c_v3.selectbox("Dia do Vencimento:", OPCOES_DIAS_VENC, index=OPCOES_DIAS_VENC.index("30"))

            if st.button("Salvar Nova Empresa"):
                cnpj = apenas_numeros_letras(cnpj_raw)
                if not cnpj or not n_emp_in: st.error("CNPJ e Nome da Empresa são obrigatórios.")
                else:
                    with st.spinner("Salvando empresa..."):
                        novo_e = pd.DataFrame([{'cnpj': cnpj, 'nome': n_emp_in.upper(), 'responsavel': resp_in.upper(), 'telefone': apenas_numeros_letras(tel_e_raw), 'email': mail_in, 'est': est_e, 'status': stat_e, 'modo_faturamento': modo_fat_e, 'dia_vencimento': dia_v_e}])
                        df_empresas_temp = pd.concat([df_empresas, novo_e], ignore_index=True)
                        sucesso, erro = salvar_dados(df_empresas_temp, FILE_EMPRESAS)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "NOVA EMPRESA", f"Cadastrou a empresa {n_emp_in.upper()} (CNPJ: {cnpj})")
                            st.success("✅ Empresa cadastrada com sucesso!"); st.session_state.aba_emp = "Listar"; time.sleep(1); st.rerun()
                        else:
                            st.error(f"Erro na nuvem: {erro}")
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
                    
                    c_v1, c_v2, c_v3 = st.columns(3)
                    stat_e = c_v1.selectbox("Status Parceria:", ["Ativo", "Inativo"], index=["Ativo", "Inativo"].index(str(dados_e_ant['status'])))
                    idx_modo_fat = MODOS_FATURAMENTO.index(str(dados_e_ant.get('modo_faturamento', 'Tradicional'))) if str(dados_e_ant.get('modo_faturamento', 'Tradicional')) in MODOS_FATURAMENTO else 0
                    modo_fat_e = c_v2.selectbox("Modo de Faturamento:", MODOS_FATURAMENTO, index=idx_modo_fat)
                    
                    venc_ant = str(dados_e_ant.get('dia_vencimento', '30')).strip()
                    if not venc_ant or venc_ant == 'nan': venc_ant = "30"
                    idx_venc = OPCOES_DIAS_VENC.index(venc_ant) if venc_ant in OPCOES_DIAS_VENC else OPCOES_DIAS_VENC.index("30")
                    dia_v_e = c_v3.selectbox("Dia do Vencimento:", OPCOES_DIAS_VENC, index=idx_venc)

                    if st.button("Salvar Alterações"):
                        cnpj = apenas_numeros_letras(cnpj_raw)
                        if not cnpj or not n_emp_in: st.error("CNPJ e Nome da Empresa são obrigatórios.")
                        else:
                            with st.spinner("Atualizando dados da empresa..."):
                                df_empresas.loc[df_empresas['cnpj'] == e_target, ['cnpj', 'nome','responsavel','telefone','email','est','status', 'modo_faturamento', 'dia_vencimento']] = [cnpj, n_emp_in.upper(), resp_in.upper(), apenas_numeros_letras(tel_e_raw), mail_in, est_e, stat_e, modo_fat_e, dia_v_e]
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
                                emp_apagada = df_empresas[df_empresas['cnpj'] == e_target_del].iloc[0]
                                detalhes_emp = f"Apagou a empresa -> CNPJ: {e_target_del} | Nome: {emp_apagada['nome']} | Resp: {emp_apagada.get('responsavel', '')}"
                                df_empresas = df_empresas[df_empresas['cnpj'] != e_target_del]
                                sucesso, erro = salvar_dados(df_empresas, FILE_EMPRESAS)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EXCLUSÃO EMPRESA", detalhes_emp)
                                    st.success("🗑️ Empresa excluída permanentemente!"); st.session_state.emp_del_confirm = None; st.session_state.aba_emp = "Listar"; time.sleep(1); st.rerun()
                                else: st.error(f"Falha na nuvem: {erro}")
                        if col_nao.button("❌ Não, cancelar"): st.session_state.emp_del_confirm = None; st.rerun()

    with menu[4]:
        st.subheader("🔧 Gerenciamento de Prestadores (Guinchos e Endereço)")
        pendentes = df_prestadores[df_prestadores['homologado'] == 'Pendente']
        if not pendentes.empty:
            st.error(f"⚠️ Existem {len(pendentes)} prestadores aguardando homologação.")
            for idx, p in pendentes.iterrows():
                with st.expander(f"Solicitação de: {p['nome']} - {p['est']}"):
                    st.write(f"**Tipo:** {p['tipo']} | **Telefone:** {p['telefone']} | **Cidade:** {p.get('cidade','N/D')}")
                    texto_zap = urllib.parse.quote(f"Olá *{str(p['nome']).upper()}*! \n\nSeu cadastro na plataforma de prestadores da *AD Rastreamento Veicular* foi analisado e *APROVADO*! ✅🚛\n\nVocê já pode acessar o seu painel exclusivo clicando no link direto de serviços que enviaremos a cada chamado.\n\nSeja bem-vindo à nossa rede 24h!")
                    link_w_aprov = f"https://api.whatsapp.com/send?phone=55{apenas_numeros_letras(p['telefone'])}&text={texto_zap}"
                    st.markdown(f'<a href="{link_w_aprov}" target="_blank" style="text-decoration: none;"><button style="background-color: #25D366; color: white; padding: 6px 12px; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; margin-bottom: 10px;">📲 Avisar no WhatsApp</button></a>', unsafe_allow_html=True)
                    col_h1, col_h2 = st.columns(2)
                    if col_h1.button("✅ Aprovar no Sistema", key=f"apr_{p['id']}"):
                        df_prestadores.loc[df_prestadores['id'] == p['id'], 'homologado'] = 'Aprovado'
                        sucesso, erro = salvar_dados(df_prestadores, FILE_PRESTADORES)
                        if sucesso: 
                            registrar_atividade(st.session_state.user, "APROVAÇÃO PRESTADOR", f"Aprovou o cadastro de {p['nome']}")
                            st.success("Aprovado!"); time.sleep(1); st.rerun()
                    if col_h2.button("❌ Reprovar/Excluir", key=f"rep_{p['id']}"):
                        df_prestadores = df_prestadores[df_prestadores['id'].astype(str) != str(p['id'])]
                        sucesso, erro = salvar_dados(df_prestadores, FILE_PRESTADORES)
                        if sucesso: 
                            registrar_atividade(st.session_state.user, "REPROVAÇÃO PRESTADOR", f"Reprovou {p['nome']}")
                            st.info("Cadastro excluído."); time.sleep(1); st.rerun()
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
            if df_prestadores.empty: st.warning("Nenhuma prestador cadastrado.")
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
                                pre_apagado = df_prestadores[df_prestadores['id'].astype(str) == p_target_del].iloc[0]
                                detalhes_pre = f"Apagou prestador -> ID: {p_target_del} | Nome: {pre_apagado['nome']} | Tipo: {pre_apagado.get('tipo','')}"
                                df_prestadores = df_prestadores[df_prestadores['id'].astype(str) != p_target_del]
                                sucesso, erro = salvar_dados(df_prestadores, FILE_PRESTADORES)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EXCLUSÃO PRESTADOR", detalhes_pre)
                                    st.success("🗑️ Prestador excluído permanentemente!"); st.session_state.pre_del_confirm = None; st.session_state.aba_pre = "Listar"; time.sleep(1); st.rerun()
                                else: st.error(f"Falha na nuvem: {erro}")
                        if col_nao.button("❌ Não, cancelar"): st.session_state.pre_del_confirm = None; st.rerun()

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

    with menu[6]:
        st.subheader("🕵️ Painel de Auditoria e Registro de Atividades")
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

    with menu[7]:
        st.subheader("💰 Gestão Financeira - Controle de Recebimentos")
        st.write("Visão unificada do seu contas a receber. As empresas ativas aparecem automaticamente aqui e a taxa de acionamento é atualizada em tempo real.")
        
        opcoes_meses_admin = get_ultimos_3_meses()
        escolha_mes_admin = st.selectbox("Selecione o Mês/Ano de Referência:", opcoes_meses_admin + ["Outro (Buscar por data)"], key="mes_admin_fin")
        if escolha_mes_admin == "Outro (Buscar por data)":
            data_busca_admin = st.date_input("Escolha uma data para filtrar o mês/ano:")
            mes_filtro = data_busca_admin.strftime("%m/%Y")
        else: mes_filtro = escolha_mes_admin

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
                    dados_fatura = calcular_fatura_parceiro(emp_name, mes_s, ano_s, df_clientes, df_os, df_empresas)
                    
                    if modo_fat == "Performance (Escalonado)":
                        if dados_fatura['taxa'] == 0.0: taxas_exibicao.append("0.0%")
                        else: taxas_exibicao.append(f"{dados_fatura['taxa']:.1f}%")
                    elif "Frota Pequena" in modo_fat or "Até 40" in modo_fat: taxas_exibicao.append("Plano Fixo")
                    else: taxas_exibicao.append("Manual")
                    
                    if modo_fat != 'Tradicional':
                        if str(r_fin.get('status', '')).strip() != 'Pago':
                            df_fin_mes.at[idx, 'valor_faturado'] = f"{dados_fatura['fatura_total']:.2f}"
                            df_financeiro.loc[df_financeiro['id'] == r_fin['id'], 'valor_faturado'] = f"{dados_fatura['fatura_total']:.2f}"
                else: taxas_exibicao.append("0.0%")
                try: total_faturado_mes += float(str(df_fin_mes.at[idx, 'valor_faturado']).replace(',', '.'))
                except: pass
                try: total_recebido_mes += float(str(df_fin_mes.at[idx, 'valor_pago']).replace(',', '.'))
                except: pass
            
            inadimplencia = total_faturado_mes - total_recebido_mes if total_faturado_mes > total_recebido_mes else 0.0
            
            st.markdown("---")
            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1: st.markdown(f'<div class="metric-card"><div style="color: #666; font-size: 16px;">Faturamento Estimado (Ciclo Atual)</div><div class="metric-value" style="color: #1976D2;">R$ {total_faturado_mes:.2f}</div></div>', unsafe_allow_html=True)
            with col_d2: st.markdown(f'<div class="metric-card"><div style="color: #666; font-size: 16px;">Faturas Pagas / Caixa</div><div class="metric-value val-pago">R$ {total_recebido_mes:.2f}</div></div>', unsafe_allow_html=True)
            with col_d3: st.markdown(f'<div class="metric-card"><div style="color: #666; font-size: 16px;">Faturas Pendentes (A Receber)</div><div class="metric-value val-atrasado">R$ {inadimplencia:.2f}</div></div>', unsafe_allow_html=True)
            
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
            st.markdown("### 🖨️ Emitir Extrato Detalhado por Empresa (PDF)")
            empresas_escalonadas = empresas_ativas[empresas_ativas['modo_faturamento'] != 'Tradicional']['nome'].str.upper().tolist()
            if not empresas_escalonadas: st.info("Nenhuma empresa ativa cadastrada nos modos de faturamento automáticos.")
            else:
                emp_pdf_sel = st.selectbox("Selecione a Empresa (Modos Automáticos) para Gerar o Extrato Detalhado:", empresas_escalonadas)
                if emp_pdf_sel:
                    try: mes_p, ano_p = mes_filtro.split('/')
                    except: mes_p, ano_p = datetime.now().month, datetime.now().year
                    st.markdown(gerar_pdf_extrato_detalhado(emp_pdf_sel, mes_p, ano_p, df_clientes, df_os, df_empresas), unsafe_allow_html=True)

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
                    
                    if modo_fat_edit != 'Tradicional':
                        v_fat_atual = str(row_edit['valor_faturado'])
                        c_f1.text_input("Valor Calculado pelo Sistema (R$):", value=v_fat_atual, disabled=True)
                        val_fat_final = v_fat_atual
                    else:
                        v_fat_atual = str(row_edit['valor_faturado'])
                        val_fat_final = c_f1.text_input("Valor da Fatura Manual (R$):", value=v_fat_atual)
                    
                    val_pago_final = c_f2.text_input("Valor Pago pelo Cliente (R$):", value=str(row_edit['valor_pago']))
                    status_final = c_f3.selectbox("Status:", ["Pendente", "Pago", "Atrasado"], index=["Pendente", "Pago", "Atrasado"].index(row_edit['status']))
                    
                    if st.form_submit_button("Salvar Edição Financeira"):
                        with st.spinner("Atualizando registros financeiros..."):
                            df_financeiro.loc[df_financeiro['id'] == row_edit['id'], ['valor_faturado', 'valor_pago', 'status']] = [val_fat_final, val_pago_final, status_final]
                            sucesso, erro = salvar_dados(df_financeiro, FILE_FINANCEIRO)
                            if sucesso:
                                registrar_atividade(st.session_state.user, "BAIXA FINANCEIRA", f"Editou o faturamento de {emp_edit} ({mes_filtro}) para status {status_final}")
                                st.success("✅ Registro atualizado com sucesso!"); time.sleep(1); st.rerun()
                            else: st.error(f"Falha na nuvem: {erro}")

# ===================================================================================
# INTERFACE 2: PARCEIROS
# ===================================================================================
elif st.session_state.perfil == "Parceiro":
    menu_parceiro = st.tabs(["👥 Cadastro de Clientes", "📋 Histórico de Chamados", "💰 Meu Financeiro", "🕵️ Auditoria"])
    
    with menu_parceiro[0]:
        df_filtrado_p = df_clientes[df_clientes['emp_name'].str.lower() == st.session_state.empresa_vinculada.lower()]
        dados_emp_base_p0 = df_empresas[df_empresas['nome'].str.upper() == st.session_state.empresa_vinculada.upper()]
        dia_v_p0 = "30"
        if not dados_emp_base_p0.empty:
            dia_v_p0 = str(dados_emp_base_p0.iloc[0].get('dia_vencimento', '30')).strip()

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
                    dt_cad_cliente = str(cli_data_p.get('data_cadastro', ''))
                    inicio_cli, fim_cli = obter_ciclo_contrato_anual(dt_cad_cliente)
                    
                    st.markdown(f"### 📋 Ficha do Cliente: {cli_data_p['nome']}")
                    c1, c2 = st.columns(2)
                    c1.write(f"**CPF:** {cli_data_p['cpf']}")
                    c1.write(f"**Telefone:** {cli_data_p['tel']}")
                    c1.write(f"**Plano Contratado:** {cli_data_p.get('plano_km', 'N/D')}")
                    c2.write(f"**Endereço:** {cli_data_p.get('endereco', 'N/D')} - {cli_data_p.get('cidade', 'N/D')}/{cli_data_p.get('est', 'N/D')}")
                    c2.write(f"**Status:** {'🟢 Ativo' if cli_data_p['status'] == 'Ativo' else '🔴 Inativo'}")
                    c2.write(f"**Data de Cadastro:** {dt_cad_cliente}")
                    st.write("**🚗 Frota Cadastrada:**")
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
                    
                    if not lista_frota_ficha:
                        st.warning("Nenhum veículo válido cadastrado para exibir saldos.")
                    else:
                        placa_sel_ficha = st.selectbox("🚗 Selecione a Placa para ver o Saldo Operacional no Ano:", lista_frota_ficha, key=f"sel_placa_part_{cli_sel_part}")
                        st.write(f"**📊 Saldo de Limites da Placa {placa_sel_ficha} no Ano de Contrato ({inicio_cli.strftime('%d/%m/%Y')} a {fim_cli.strftime('%d/%m/%Y')}):**")
                        
                        uso_atual_f = {"GUINCHO": 0, "PANE SECA": 0, "PANE ELÉTRICA": 0, "BORRACHEIRO": 0, "CHAVEIRO": 0}
                        if not df_os.empty:
                            df_os_copy = df_os.copy()
                            df_os_copy['data_hora'] = pd.to_datetime(df_os_copy['data_hora'], errors='coerce')
                            placa_limpa_f = apenas_numeros_letras(placa_sel_ficha).upper()
                            os_placa_f = df_os_copy[
                                (df_os_copy['placa'].astype(str).apply(lambda x: apenas_numeros_letras(x).upper()) == placa_limpa_f) & 
                                (~df_os_copy['status_os'].str.upper().isin(['CANCELADO'])) &
                                (df_os_copy['data_hora'] >= inicio_cli) &
                                (df_os_copy['data_hora'] <= fim_cli)
                            ]
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
            c1, c2 = st.columns(2)
            p_nome_in = c1.text_input("Nome Completo:", value=st.session_state.get("part_inc_nome", ""))
            st.session_state.part_inc_nome = p_nome_in
            p_cpf_raw = c2.text_input("CPF:", value=st.session_state.get("part_inc_cpf", ""))
            st.session_state.part_inc_cpf = p_cpf_raw
            p_tel_raw = c1.text_input("Telefone:", value=st.session_state.get("part_inc_tel", ""))
            st.session_state.part_inc_tel = p_tel_raw
            p_end_in = c2.text_input("Endereço Completo:", value=st.session_state.get("part_inc_end", ""))
            st.session_state.part_inc_end = p_end_in
            p_cid_in = c1.text_input("Cidade:", value=st.session_state.get("part_inc_cid", ""))
            st.session_state.part_inc_cid = p_cid_in
            p_cep_in = c2.text_input("CEP:", value=st.session_state.get("part_inc_cep", ""))
            st.session_state.part_inc_cep = p_cep_in
            
            cad_data = c1.date_input("Data de Cadastro (Início do Contrato):", value=datetime.now())
            
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
                        dt_str_save = cad_data.strftime("%Y-%m-%d")
                        novo_reg = pd.DataFrame([{'id': str(prox_id), 'nome': p_nome_in.upper(), 'cpf': p_cpf, 'tel': apenas_numeros_letras(p_tel_raw), 'endereco': p_end_in, 'cidade': p_cid_in.upper(), 'cep': p_cep_in, 'plano_km': p_plano_km, 'vei': vei_prin_p, 'pla': pla_prin_p, 'est': p_est, 'emp_name': st.session_state.empresa_vinculada.upper(), 'status': p_stat, 'veiculos_lista': frota_json_str_p, 'data_cadastro': dt_str_save}])
                        df_clientes_temp = pd.concat([df_clientes, novo_reg], ignore_index=True)
                        sucesso, erro = salvar_dados(df_clientes_temp, FILE_CLIENTES)
                        if sucesso:
                            registrar_atividade(st.session_state.user, "NOVO CLIENTE PARCEIRO", f"Cadastrou o cliente {p_nome_in.upper()}")
                            st.success("✅ Registro salvo com sucesso!")
                            for k in ["part_inc_nome", "part_inc_cpf", "part_inc_tel", "part_inc_end", "part_inc_cid", "part_inc_cep"]: st.session_state[k] = ""
                            st.session_state.aba_part = "Visualizar"; time.sleep(1); st.rerun()
                        else:
                            st.error("⚠️ Atenção: Instabilidade na Conexão com a Nuvem.")

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
                    
                    try: val_data_cad = datetime.strptime(str(dados_part_ant.get('data_cadastro', ''))[:10], "%Y-%m-%d").date()
                    except: val_data_cad = datetime.now().date()
                    cad_data = c1.date_input("Data de Cadastro (Início do Contrato):", value=val_data_cad)
                    
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
                                dt_str_save = cad_data.strftime("%Y-%m-%d")
                                df_clientes.loc[df_clientes['id'].astype(str) == part_target, ['nome','cpf','tel','endereco','cidade','cep','plano_km','vei','pla','est','status','veiculos_lista','data_cadastro']] = [p_nome_in.upper(), p_cpf, apenas_numeros_letras(p_tel_raw), p_end_in, p_cid_in.upper(), p_cep_in, p_plano_km, vei_prin_p, pla_prin_p, p_est, p_stat, frota_json_str_p, dt_str_save]
                                sucesso, erro = salvar_dados(df_clientes, FILE_CLIENTES)
                                if sucesso:
                                    registrar_atividade(st.session_state.user, "EDIÇÃO CLIENTE PARCEIRO", f"Editou o cliente {p_nome_in.upper()}")
                                    st.success("✅ Registro atualizado com sucesso!"); st.session_state.aba_part = "Visualizar"; time.sleep(1); st.rerun()
                                else:
                                    st.error("⚠️ Atenção: Falha de comunicação com a nuvem.")

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

    with menu_parceiro[2]:
        st.subheader("💰 Gestão Financeira (Meu Faturamento)")
        st.write("Confira as faturas, o status dos pagamentos e o extrato detalhado da sua empresa.")
        
        dados_emp_base_p = df_empresas[df_empresas['nome'].str.upper() == st.session_state.empresa_vinculada.upper()]
        modo_fat_p = "Tradicional"
        if not dados_emp_base_p.empty:
            modo_fat_p = str(dados_emp_base_p.iloc[0].get('modo_faturamento', 'Tradicional')).strip()

        opcoes_meses_p = get_ultimos_3_meses()
        escolha_mes_p = st.selectbox("Mês de Referência:", opcoes_meses_p + ["Outro (Buscar por data)"], key="mes_parc")
        if escolha_mes_p == "Outro (Buscar por data)":
            data_busca_p = st.date_input("Data de referência:", key="data_parc")
            mes_filtro_p = data_busca_p.strftime("%m/%Y")
        else: mes_filtro_p = escolha_mes_p
            
        df_fin_parc = df_financeiro[(df_financeiro['mes_ano'] == mes_filtro_p) & (df_financeiro['empresa'].str.upper() == st.session_state.empresa_vinculada.upper())]
        
        if df_fin_parc.empty:
            st.info("Nenhum faturamento gerado ou disponível para visualização neste ciclo ainda.")
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

            if modo_fat_p != 'Tradicional':
                st.write("---")
                try: mes_sp, ano_sp = mes_filtro_p.split('/')
                except: mes_sp, ano_sp = datetime.now().month, datetime.now().year
                
                with st.expander("🔍 Detalhar Fatura no Aplicativo"):
                    st.markdown(f"**Empresa:** {st.session_state.empresa_vinculada.upper()} | **Período de Referência:** {mes_filtro_p}")
                    dados_det = calcular_fatura_parceiro(st.session_state.empresa_vinculada, mes_sp, ano_sp, df_clientes, df_os, df_empresas)
                    st.write(f"- **Ciclo de Apuração:** {dados_det['dt_inicio'].strftime('%d/%m/%Y')} até {dados_det['dt_fim'].strftime('%d/%m/%Y')}")
                    st.write(f"- **Plano Contratado:** {dados_det['modo_fat']}")
                    st.write(f"- **Total Exato de Veículos na Base (Ativos):** {dados_det['total_v']}")
                    st.write(f"- **Total de Chamados Encerrados no Ciclo:** {dados_det['total_os']}")
                    if dados_det['modo_fat'] == "Performance (Escalonado)":
                        if dados_det['taxa'] == 0.0: st.write(f"- **Taxa de Acionamento Atingida:** 0.0% (Faixa: {dados_det['faixa']})")
                        else: st.write(f"- **Taxa de Acionamento Atingida:** {dados_det['taxa']:.1f}% (Faixa: {dados_det['faixa']})")
                    st.write(f"- **Valor Final Calculado:** R$ {dados_det['fatura_total']:.2f}")
                    st.info("💡 Clique no botão de PDF abaixo para baixar o relatório completo contendo a auditoria com todas as placas cobradas.")

                st.write("")
                st.markdown(gerar_pdf_extrato_detalhado(st.session_state.empresa_vinculada, mes_sp, ano_sp, df_clientes, df_os, df_empresas), unsafe_allow_html=True)

    with menu_parceiro[3]:
        st.subheader("🕵️ Auditoria e Histórico de Atividades")
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
            busca_log_p = st.text_input("🔍 Buscar no seu registro (ex: placa, nome):")
            if busca_log_p:
                df_logs_parc = df_logs_parc[df_logs_parc['detalhes'].str.contains(busca_log_p, case=False, na=False) | df_logs_parc['acao'].str.contains(busca_log_p, case=False, na=False)]
            
            st.write("---")
            opcoes_log_p = {str(i): f"{r['data_hora']} - {r['acao']}" for i, r in df_logs_parc.iterrows()}
            log_sel_p = st.selectbox("Selecione um registro para ver os Detalhes Completos:", options=[""] + list(opcoes_log_p.keys()), format_func=lambda x: "Selecione para ver o detalhamento..." if x == "" else opcoes_log_p[x])
            
            if log_sel_p != "":
                detalhe_row = df_logs_parc.loc[int(log_sel_p)]
                
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #7B2CBF; margin-bottom: 15px;">
                    <p style="margin-bottom:5px;"><strong>🕒 Data/Hora:</strong> {detalhe_row['data_hora']}</p>
                    <p style="margin-bottom:5px;"><strong>👤 Feito por:</strong> {detalhe_row['usuario']}</p>
                    <p style="margin-bottom:5px;"><strong>⚙️ Ação:</strong> {detalhe_row['acao']}</p>
                    <p style="margin-bottom:5px;"><strong>📝 Detalhes Completos do Evento:</strong> {detalhe_row['detalhes']}</p>
                </div>
                """, unsafe_allow_html=True)
                
            st.write("---")
            st.dataframe(df_logs_parc[['data_hora', 'acao', 'detalhes']], use_container_width=True)

# ===================================================================================
# INTERFACE 3: PRESTADOR (GUINCHO)
# ===================================================================================
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
                    
                    if passo < 5: 
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
                                
                    elif passo == 5: 
                        st.markdown(f"#### ✍️ Etapa Atual: {nomes_exibicao[passo]}")
                        st.info("Peça para o cliente assinar no quadro abaixo com o dedo. (Pode virar o celular de lado para ter mais espaço).")
                        canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 0.3)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=250, drawing_mode="freedraw", key=f"canvas_{os_row['id']}")
                        
                        if st.button("Salvar Assinatura e Concluir Vistoria", type="primary"):
                            if canvas_result.image_data is not None:
                                with st.spinner("Salvando assinatura e avisando a central..."):
                                    img = Image.fromarray((canvas_result.image_data).astype(np.uint8))
                                    img = img.convert("RGB") 
                                    img.save(os.path.join(vistoria_path, "Assinatura.jpg"))
                                    df_os.loc[df_os['id'] == os_row['id'], 'status_os'] = 'EM ROTA (VISTORIA OK)'
                                    salvar_dados(df_os, FILE_OS)
                                    st.session_state.passo_vistoria += 1
                                    st.rerun()
                            else: st.error("Peça ao cliente para assinar antes de salvar.")
                        if st.button("🔄 Voltar para a última foto", key=f"btn_voltar_ass"):
                            st.session_state.passo_vistoria = 4; st.rerun()
                
                else:
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
"""
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(code)
    
    # We should run a quick syntax check to be absolutely sure.
    import ast
    try:
        ast.parse(code)
        print("Syntax check passed!")
    except SyntaxError as e:
        print(f"SyntaxError detected: {e}")

fix_code()
