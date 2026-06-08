import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import os

# Configuração da Página
st.set_page_config(page_title="AD Rastreamento - Central 24h", layout="wide")

# Inicialização de arquivos e pastas
FOLDER = "AD_Assistencia"
os.makedirs(FOLDER, exist_ok=True)
FILE_CLIENTES = os.path.join(FOLDER, "banco_clientes.csv")
FILE_EMPRESAS = os.path.join(FOLDER, "banco_empresas.csv")
FILE_PRESTADORES = os.path.join(FOLDER, "banco_prestadores.csv")
FILE_OS = os.path.join(FOLDER, "banco_os.csv")

# Funções de Carregamento
def carregar_df(caminho, colunas):
    if not os.path.exists(caminho):
        pd.DataFrame(columns=colunas).to_csv(caminho, index=False)
    return pd.read_csv(caminho)

# Carregar dados iniciais
df_clientes = carregar_df(FILE_CLIENTES, ['id', 'nome', 'cpf', 'tel', 'marca', 'modelo', 'placa', 'estado', 'empresa', 'status'])
df_empresas = carregar_df(FILE_EMPRESAS, ['cnpj', 'nome', 'responsavel', 'tel', 'email', 'estado', 'status'])
df_prestadores = carregar_df(FILE_PRESTADORES, ['id', 'nome', 'tel', 'estado', 'status'])
df_os = carregar_df(FILE_OS, ['id', 'data', 'cliente_nome', 'empresa', 'tipo_servico', 'motivo', 'prestador', 'local', 'destino', 'obs', 'status'])

# --- MENU PRINCIPAL ---
menu = st.tabs(["📋 Nova OS", "📊 Relatórios", "👤 Clientes", "🏢 Empresas", "🔧 Prestadores"])

# 1. NOVA OS
with menu[0]:
    st.subheader("Iniciar Atendimento")
    busca = st.text_input("Buscar por Nome, Placa ou CPF")
    if busca:
        cli = df_clientes[df_clientes['nome'].str.contains(busca, case=False) | df_clientes['placa'].str.contains(busca, case=False)]
        if not cli.empty:
            c = cli.iloc[0]
            st.write(f"**Cliente:** {c['nome']} | **Veículo:** {c['marca']} {c['modelo']} | **Placa:** {c['placa']}")
            
            tipo = st.selectbox("Tipo de Serviço", ["Guincho", "Pane Seca", "Pane Elétrica", "Borracheiro", "Chaveiro"])
            motivo = st.selectbox("Motivo", ["Guincho", "Furto/Roubo", "Acidente", "Outros"])
            local = st.text_input("Localidade")
            destino = st.text_input("Destino")
            obs = st.text_area("Descrição da Situação")
            
            if st.button("Gerar Ordem de Serviço"):
                nova_os = pd.DataFrame([{'id': len(df_os)+1, 'data': datetime.now().strftime("%d/%m/%Y %H:%M"), 
                                        'cliente_nome': c['nome'], 'empresa': c['empresa'], 'tipo_servico': tipo, 
                                        'motivo': motivo, 'local': local, 'destino': destino, 'obs': obs, 'status': 'Em Atendimento'}])
                df_os = pd.concat([df_os, nova_os])
                df_os.to_csv(FILE_OS, index=False)
                st.success("OS Gerada com sucesso!")

# 2. RELATÓRIOS
with menu[1]:
    st.subheader("Relatórios de Atendimento")
    emp_f = st.selectbox("Filtrar por Empresa", ["Todos"] + df_empresas['nome'].unique().tolist())
    
    df_rel = df_os.copy()
    if emp_f != "Todos": df_rel = df_rel[df_rel['empresa'] == emp_f]
    
    cli_f = st.selectbox("Filtrar por Cliente", ["Todos"] + df_rel['cliente_nome'].unique().tolist())
    if cli_f != "Todos": df_rel = df_rel[df_rel['cliente_nome'] == cli_f]
    
    st.dataframe(df_rel)
    os_pdf = st.selectbox("Selecionar OS Individual para Detalhar", df_rel['id'].unique())
    if st.button("Exportar PDF"):
        st.write(f"Gerando PDF da OS: {os_pdf}")

# 3. CLIENTES (Cadastro Completo)
with menu[2]:
    st.subheader("Gerenciar Clientes")
    with st.form("form_cli"):
        nome = st.text_input("Nome Completo")
        cpf = st.text_input("CPF")
        tel = st.text_input("Telefone")
        marca = st.text_input("Marca do Veículo")
        modelo = st.text_input("Modelo")
        placa = st.text_input("Placa")
        estado = st.selectbox("Estado (UF)", ESTADOS_BR)
        empresa = st.selectbox("Empresa Pertencente", df_empresas['nome'].unique() if not df_empresas.empty else [])
        status = st.selectbox("Status", ["Ativo", "Inativo"])
        if st.form_submit_button("Salvar Cliente"):
            novo = pd.DataFrame([{'nome': nome, 'cpf': cpf, 'tel': tel, 'marca': marca, 'modelo': modelo, 'placa': placa, 'estado': estado, 'empresa': empresa, 'status': status}])
            df_clientes = pd.concat([df_clientes, novo])
            df_clientes.to_csv(FILE_CLIENTES, index=False)
            st.rerun()
    st.dataframe(df_clientes)

# 4. EMPRESAS (Cadastro Completo)
with menu[3]:
    st.subheader("Gerenciar Empresas")
    with st.form("form_emp"):
        nome_e = st.text_input("Nome da Empresa")
        cnpj = st.text_input("CNPJ")
        resp = st.text_input("Responsável")
        tel_e = st.text_input("Telefone")
        email = st.text_input("E-mail")
        uf_e = st.selectbox("Estado", ESTADOS_BR)
        status_e = st.selectbox("Status", ["Ativo", "Inativo"])
        if st.form_submit_button("Salvar Empresa"):
            novo_e = pd.DataFrame([{'cnpj': cnpj, 'nome': nome_e, 'responsavel': resp, 'tel': tel_e, 'email': email, 'estado': uf_e, 'status': status_e}])
            df_empresas = pd.concat([df_empresas, novo_e])
            df_empresas.to_csv(FILE_EMPRESAS, index=False)
            st.rerun()
    st.dataframe(df_empresas)

# 5. PRESTADORES
with menu[4]:
    st.subheader("Gerenciar Prestadores")
    with st.form("form_prest"):
        nome_p = st.text_input("Nome do Prestador")
        tel_p = st.text_input("Telefone")
        uf_p = st.selectbox("Estado de Atuação", ESTADOS_BR)
        status_p = st.selectbox("Status", ["Ativo", "Inativo"])
        if st.form_submit_button("Salvar Prestador"):
            novo_p = pd.DataFrame([{'nome': nome_p, 'tel': tel_p, 'estado': uf_p, 'status': status_p}])
            df_prestadores = pd.concat([df_prestadores, novo_p])
            df_prestadores.to_csv(FILE_PRESTADORES, index=False)
            st.rerun()
    st.dataframe(df_prestadores)
