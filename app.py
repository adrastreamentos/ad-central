import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuração de Layout
st.set_page_config(page_title="Central 24h - AD Rastreamento Veicular", layout="wide", page_icon="🔒")

# Estilização
st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: #7B2CBF; text-align: center; margin-bottom: 5px; }
    .subtitle { font-size: 18px; color: #E53935; text-align: center; margin-bottom: 25px; font-weight: 500; }
    </style>
""", unsafe_allow_html=True)

# Definições de caminhos e dados
SERVICOS = ["Guincho", "Pane Seca", "Pane Elétrica", "Borracheiro", "Chaveiro"]
FOLDER = "AD_Assistencia"
os.makedirs(FOLDER, exist_ok=True)
FILE_CLIENTES = os.path.join(FOLDER, "banco_clientes.csv")
FILE_EMPRESAS = os.path.join(FOLDER, "banco_empresas.csv")
FILE_PRESTADORES = os.path.join(FOLDER, "banco_prestadores.csv")
FILE_OS = os.path.join(FOLDER, "banco_os.csv")

def carregar(f, cols):
    if not os.path.exists(f): return pd.DataFrame(columns=cols)
    return pd.read_csv(f)

# Inicialização dos DataFrames
df_c = carregar(FILE_CLIENTES, ['id','nome','cpf','tel','vei','pla','est','emp_name','status'])
df_e = carregar(FILE_EMPRESAS, ['cnpj','nome','responsavel','telefone','email','est','status'])
df_p = carregar(FILE_PRESTADORES, ['id','nome','tipo','telefone','est','status'])
df_os = carregar(FILE_OS, ['id','data_hora','cliente_id','cliente_nome','empresa','tipo_servico','motivo','prestador','localizacao','destino','obs','status_os','zap_enviado'])

if "logado" not in st.session_state: st.session_state.logado = False

# LOGIN
if not st.session_state.logado:
    st.markdown('<div class="main-title">AD Rastreamento Veicular</div>', unsafe_allow_html=True)
    user = st.text_input("Usuário:")
    pwd = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        if user == "AD Rastreamento" and pwd == "00000000000000":
            st.session_state.logado = True
            st.rerun()
        else: st.error("Dados incorretos")
    st.stop()

if st.sidebar.button("Sair"): st.session_state.logado = False; st.rerun()

menu = st.tabs(["📋 Nova OS", "📊 Relatórios", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores"])

with menu[0]:
    st.subheader("Nova OS")
    busca = st.text_input("Buscar Cliente:")
    if busca:
        filtro = df_c[df_c['nome'].str.contains(busca, case=False, na=False)]
        if not filtro.empty:
            sel = st.selectbox("Selecione o Cliente:", [f"{r['id']} - {r['nome']}" for _, r in filtro.iterrows()])
            c_id = sel.split(" - ")[0]
            cliente = df_c[df_c['id'].astype(str) == c_id].iloc[0]
            serv = st.selectbox("Serviço:", SERVICOS)
            motivo = st.selectbox("Motivo:", ["Acidente", "Furto", "Roubo", "Outros"])
            prest = st.text_input("Prestador:")
            loc = st.text_input("Origem:")
            dest = st.text_input("Destino:")
            obs = st.text_area("Obs:")
            if st.button("Gerar OS"):
                nova_id = int(df_os['id'].max() + 1) if not df_os.empty else 1
                nova_os = pd.DataFrame([{'id': nova_id, 'data_hora': datetime.now().strftime("%d/%m/%Y %H:%M"), 'cliente_id': c_id, 'cliente_nome': cliente['nome'], 'empresa': cliente['emp_name'], 'tipo_servico': serv, 'motivo': motivo, 'prestador': prest, 'localizacao': loc, 'destino': dest, 'obs': obs, 'status_os': "EM ATENDIMENTO", 'zap_enviado': "NÃO"}])
                df_os = pd.concat([df_os, nova_os], ignore_index=True)
                df_os.to_csv(FILE_OS, index=False)
                st.success("OS Gerada!")
                st.rerun()

with menu[1]:
    st.subheader("Relatórios e Despacho")
    for idx, row in df_os.sort_values(by='id', ascending=False).iterrows():
        if str(row['status_os']) == "EM ATENDIMENTO":
            col1, col2 = st.columns([3, 1])
            with col1: st.write(f"OS {row['id']} | {row['cliente_nome']} | {row['prestador']}")
            with col2:
                tel = "".join(filter(str.isdigit, str(row['prestador'])))
                link = f"https://api.whatsapp.com/send?phone=55{tel}&text=OS%20{row['id']}"
                st.markdown(f'<a href="{link}" target="_blank">📲 Despachar</a>', unsafe_allow_html=True)
                if st.button("Encerrar", key=f"enc_{row['id']}"):
                    df_os.loc[idx, 'status_os'] = "ENCERRADO"
                    df_os.to_csv(FILE_OS, index=False)
                    st.rerun()
            st.markdown("---")

with menu[2]:
    st.subheader("Gerenciamento de Clientes")
    modo = st.checkbox("Editar existente")
    dados = None
    if modo:
        sel = st.selectbox("Selecione:", [f"{r['id']} - {r['nome']}" for _, r in df_c.iterrows()])
        dados = df_c[df_c['id'].astype(str) == sel.split(" - ")[0]].iloc[0]
    n = st.text_input("Nome:", value=dados['nome'] if dados is not None else "")
    c = st.text_input("CPF:", value=dados['cpf'] if dados is not None else "")
    t = st.text_input("Tel:", value=dados['tel'] if dados is not None else "")
    v = st.text_input("Veículo:", value=dados['vei'] if dados is not None else "")
    p = st.text_input("Placa:", value=dados['pla'] if dados is not None else "")
    if st.button("Salvar Cliente"):
        if not modo:
            novo = pd.DataFrame([{'id': int(df_c['id'].max()+1) if not df_c.empty else 1, 'nome': n.upper(), 'cpf': c, 'tel': t, 'vei': v.upper(), 'pla': p.upper(), 'est': 'RN', 'emp_name': 'AD', 'status': 'Ativo'}])
            df_c = pd.concat([df_c, novo], ignore_index=True)
        else:
            df_c.loc[df_c['id'].astype(str) == str(dados['id']), ['nome','cpf','tel','vei','pla']] = [n.upper(), c, t, v.upper(), p.upper()]
        df_c.to_csv(FILE_CLIENTES, index=False)
        st.success("Salvo!")
        st.rerun()

with menu[3]:
    st.subheader("Empresas")
    modo_e = st.checkbox("Editar existente")
    dados_e = None
    if modo_e:
        sel_e = st.selectbox("Selecione:", [f"{r['cnpj']} - {r['nome']}" for _, r in df_e.iterrows()])
        dados_e = df_e[df_e['cnpj'].astype(str) == sel_e.split(" - ")[0]].iloc[0]
    cnpj = st.text_input("CNPJ:", value=str(dados_e['cnpj']) if dados_e is not None else "")
    n_e = st.text_input("Nome:", value=str(dados_e['nome']) if dados_e is not None else "")
    if st.button("Salvar Empresa"):
        if not modo_e:
            novo_e = pd.DataFrame([{'cnpj': cnpj, 'nome': n_e.upper(), 'responsavel': '', 'telefone': '', 'email': '', 'est': 'RN', 'status': 'Ativo'}])
            df_e = pd.concat([df_e, novo_e], ignore_index=True)
        else:
            df_e.loc[df_e['cnpj'].astype(str) == str(dados_e['cnpj']), ['nome']] = [n_e.upper()]
        df_e.to_csv(FILE_EMPRESAS, index=False)
        st.success("Salvo!")
        st.rerun()

with menu[4]:
    st.subheader("🔧 Gerenciamento de Prestadores")
    modo_p = st.checkbox("Editar existente")
    dados_p = None
    if modo_p and not df_p.empty:
        sel_p = st.selectbox("Selecione:", [f"{r['id']} - {r['nome']}" for _, r in df_p.iterrows()])
        dados_p = df_p[df_p['id'].astype(str) == sel_p.split(" - ")[0]].iloc[0]
        
    n_p = st.text_input("Nome:", value=str(dados_p['nome']) if dados_p is not None else "")
    
    # Lógica de serviços com multiselect
    servicos_atuais = [s.strip() for s in str(dados_p['tipo']).split(",")] if dados_p is not None else ["Guincho"]
    tipos_sel = st.multiselect("Serviços:", SERVICOS, default=servicos_atuais)
    
    if st.button("Salvar Prestador"):
        tipo_f = ", ".join(tipos_sel) if tipos_sel else "Guincho"
        if not modo_p:
            novo_p = pd.DataFrame([{'id': int(df_p['id'].max()+1) if not df_p.empty else 1, 'nome': n_p.upper(), 'tipo': tipo_f, 'telefone': '', 'est': 'RN', 'status': 'Ativo'}])
            df_p = pd.concat([df_p, novo_p], ignore_index=True)
        else:
            df_p.loc[df_p['id'].astype(str) == str(dados_p['id']), ['nome', 'tipo']] = [n_p.upper(), tipo_f]
        df_p.to_csv(FILE_PRESTADORES, index=False)
        st.success("Salvo!")
        st.rerun()
