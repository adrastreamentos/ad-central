# ... (Mantenha todo o código anterior exatamente igual até a linha do Prestador) ...

    # ABA: PRESTADORES (SUBSTITUA APENAS ESTE BLOCO NO SEU CÓDIGO)
    with menu[4]:
        st.subheader("🔧 Gerenciamento de Prestadores (Guinchos)")
        modo_p = st.checkbox("Editar existente")
        dados_p = None
        if modo_p and not df_p.empty:
            sel_p = st.selectbox("Selecione:", [f"{r['id']} - {r['nome']}" for _, r in df_p.iterrows()])
            dados_p = df_p[df_p['id'].astype(str) == sel_p.split(" - ")[0]].iloc[0]
            
        n_p = st.text_input("Nome:", value=str(dados_p['nome']) if dados_p is not None else "")
        
        # MELHORIA: Multiselect mantendo "Guincho" padrão
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
