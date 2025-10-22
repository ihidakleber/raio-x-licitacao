import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px

st.set_page_config(layout="wide")

st.title("Raio-X de Itens de Compra do Governo")
st.markdown("""
**Passo 1:** Insira os filtros e clique em "Analisar Preços" para buscar os dados.
**Passo 2:** Use o filtro de unidades que aparecerá para refinar sua seleção.
**Passo 3:** Prossiga com a análise e a remoção iterativa de outliers.
""")

REGIOES = {
    "NORTE": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "NORDESTE": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "CENTRO-OESTE": ["DF", "GO", "MT", "MS"],
    "SUDESTE": ["ES", "MG", "RJ", "SP"],
    "SUL": ["PR", "RS", "SC"]
}
ESTADOS = sorted([estado for sublist in REGIOES.values() for estado in sublist])

col1, col2 = st.columns(2)
with col1:
    catmat_input = st.text_area("Códigos CATMAT (separados por vírgula)", "459670")
    localidades_selecionadas = st.multiselect(
        "Filtro de Localidade",
        options=sorted(list(REGIOES.keys()) + ESTADOS),
        default=["SUDESTE", "NORDESTE", "NORTE"]
    )
with col2:
    data_inicio = st.date_input("Data de Início", datetime(2023, 1, 1))
    data_fim = st.date_input("Data de Fim", datetime.now())

@st.cache_data(ttl=3600)
def buscar_dados_completos(catmat_list, estados_para_buscar, data_inicio, data_fim):
    todos_os_itens = []
    
    def buscar_dados_item(codigo_item, estado):
        resultados_finais = []
        pagina_atual = 1
        total_paginas = 1
        while pagina_atual <= total_paginas:
            url = f"https://dadosabertos.compras.gov.br/modulo-pesquisa-preco/1_consultarMaterial"
            params = {"codigoItemCatalogo": codigo_item, "estado": estado, "pagina": pagina_atual, "tamanhoPagina": 500}
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                if pagina_atual == 1: total_paginas = data.get('totalPaginas', 0)
                resultados_finais.extend(data.get('resultado', []))
                pagina_atual += 1
            except requests.exceptions.RequestException as e:
                st.error(f"Erro na chamada à API para CATMAT {codigo_item}: {e}")
                return []
        return resultados_finais

    for catmat in catmat_list:
        for estado in sorted(list(estados_para_buscar)):
            dados_item = buscar_dados_item(catmat, estado)
            todos_os_itens.extend(dados_item)
    
    if not todos_os_itens: return pd.DataFrame()

    df_bruto = pd.DataFrame(todos_os_itens)
    df_bruto['dataResultado'] = pd.to_datetime(df_bruto['dataResultado'])
    df_filtrado = df_bruto[
        (df_bruto['dataResultado'].dt.date >= data_inicio) &
        (df_bruto['dataResultado'].dt.date <= data_fim)
    ].copy()
    return df_filtrado

def perform_outlier_iteration(df_calc, df_history, iteration_num):
    if len(df_calc) < 2: return df_calc, df_history

    media = df_calc['precoUnitario'].mean()
    desvio_padrao = df_calc['precoUnitario'].std()
    
    limite_superior = media + (1 * desvio_padrao)
    limite_inferior = max(0, media - (1 * desvio_padrao))

    outliers_indices = df_calc[
        (df_calc['precoUnitario'] < limite_inferior) | 
        (df_calc['precoUnitario'] > limite_superior)
    ].index

    for idx in outliers_indices:
        preco = df_history.loc[idx, 'precoUnitario']
        status = "Abaixo" if preco < limite_inferior else "Acima"
        if df_history.loc[idx, 'Status'] == 'Dentro':
            df_history.loc[idx, 'Status'] = status
            df_history.loc[idx, 'Iteração Outlier'] = iteration_num
            
    df_next_calc = df_calc.drop(outliers_indices)
    return df_next_calc, df_history

def criar_unidade_descritiva(row):
    componentes = []
    if pd.notna(row.get('nomeUnidadeFornecimento')) and str(row.get('nomeUnidadeFornecimento')).strip():
        componentes.append(str(row.get('nomeUnidadeFornecimento')).strip().upper())
    
    capacidade = row.get('capacidadeUnidadeFornecimento')
    if pd.notna(capacidade) and isinstance(capacidade, (int, float)) and capacidade > 0:
        componentes.append(str(int(capacidade)))

    unidade_final = None
    if pd.notna(row.get('nomeUnidadeMedida')) and str(row.get('nomeUnidadeMedida')).strip():
        unidade_final = str(row.get('nomeUnidadeMedida')).strip().upper()
    elif pd.notna(row.get('siglaUnidadeMedida')) and str(row.get('siglaUnidadeMedida')).strip():
        unidade_final = str(row.get('siglaUnidadeMedida')).strip().upper()
    
    if unidade_final: componentes.append(unidade_final)
    return " ".join(componentes)

if st.button("Analisar Preços"):
    st.session_state.clear()
    try:
        catmat_list = [int(c.strip()) for c in catmat_input.split(',') if c.strip()]
    except ValueError:
        st.error("Códigos CATMAT devem ser números inteiros."); st.stop()
    
    if not catmat_list: st.error("Por favor, insira pelo menos um código CATMAT válido."); st.stop()

    estados_para_buscar = set()
    for loc in localidades_selecionadas:
        if loc in REGIOES: estados_para_buscar.update(REGIOES[loc])
        elif loc in ESTADOS: estados_para_buscar.add(loc)
    if not estados_para_buscar: estados_para_buscar = [None]
    
    with st.spinner("Buscando e processando dados..."):
        df_raw = buscar_dados_completos(catmat_list, estados_para_buscar, data_inicio, data_fim)

    if df_raw.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
    else:
        df_raw['Unidade Descritiva'] = df_raw.apply(criar_unidade_descritiva, axis=1)
        st.session_state.df_raw_data = df_raw
        
        all_units = sorted(df_raw['Unidade Descritiva'].unique())
        st.session_state.all_units = all_units
        st.session_state.selected_units = all_units
        st.session_state.data_loaded = True

if st.session_state.get('data_loaded', False):
    df_raw = st.session_state.df_raw_data
    all_units = st.session_state.all_units

    with st.expander("Passo 2: Filtre as Unidades de Medida", expanded=True):
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Selecionar Todas", use_container_width=True):
                st.session_state.selected_units = all_units
                st.rerun()
            if st.button("Limpar Seleção", use_container_width=True):
                st.session_state.selected_units = []
                st.rerun()
        with col2:
            st.session_state.selected_units = st.multiselect(
                "Selecione as unidades que deseja analisar:",
                options=all_units,
                default=st.session_state.get('selected_units', all_units)
            )

    df_filtered_by_units = df_raw[df_raw['Unidade Descritiva'].isin(st.session_state.selected_units)].copy()
    
    if 'df_initial' not in st.session_state or not st.session_state.df_initial.equals(df_filtered_by_units):
        st.session_state.iteration = 0
        st.session_state.df_initial = df_filtered_by_units
        st.session_state.df_history = df_filtered_by_units.copy()
        st.session_state.df_history['Status'] = 'Dentro'
        st.session_state.df_history['Iteração Outlier'] = 0
        st.session_state.df_current_calc = df_filtered_by_units.copy()

    st.markdown("---")

    iteration = st.session_state.get('iteration', 0)
    if iteration == 0:
        button_label = "Remover Outliers (Iniciar Iteração 1)"
    else:
        button_label = f"Refazer Remoção (Iniciar Iteração {iteration + 1})"

    if st.button(button_label, disabled=(len(st.session_state.df_current_calc) < 2)):
        st.session_state.iteration += 1
        df_calc_next, df_history_next = perform_outlier_iteration(
            st.session_state.df_current_calc.copy(),
            st.session_state.df_history.copy(),
            st.session_state.iteration
        )
        st.session_state.df_current_calc = df_calc_next
        st.session_state.df_history = df_history_next
        st.rerun()

    df_initial = st.session_state.df_initial
    df_history = st.session_state.df_history
    df_current_calc = st.session_state.df_current_calc
    
    st.header("Resultados da Análise")
    if df_initial.empty:
        st.warning("Nenhum dado para exibir com as unidades selecionadas.")
    else:
        st.subheader("1. Resumo Estatístico Geral (Baseado nas unidades selecionadas)")
        descricao_geral = df_initial['precoUnitario'].describe()
        coef_variacao = (descricao_geral['std'] / descricao_geral['mean']) * 100 if descricao_geral['mean'] > 0 else 0
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Preço Mínimo", f"R$ {descricao_geral['min']:.2f}")
        c2.metric("Preço Médio", f"R$ {descricao_geral['mean']:.2f}")
        c3.metric("Preço Mediano", f"R$ {descricao_geral['50%']:.2f}")
        c4.metric("Preço Máximo", f"R$ {descricao_geral['max']:.2f}")
        c5.metric("Coef. de Variação", f"{coef_variacao:.2f}%")
        c6.metric("Total de Ocorrências", f"{int(descricao_geral['count'])}")

        if iteration > 0:
            st.subheader(f"2. Análise de Dispersão (Resultado da Iteração {iteration})")
            if not df_current_calc.empty and len(df_current_calc) > 1:
                descricao_normalidade = df_current_calc['precoUnitario'].describe()
                novo_coef_variacao = (descricao_normalidade['std'] / descricao_normalidade['mean']) * 100 if descricao_normalidade['mean'] > 0 else 0
                total_itens_original = len(df_initial)
                itens_dentro_agora = len(df_current_calc)
                percentual_dentro = (itens_dentro_agora / total_itens_original) * 100
                st.info(f"**{itens_dentro_agora} de {total_itens_original} itens ({percentual_dentro:.2f}%)** são considerados 'Dentro' nesta iteração.")
                st.write("Estatísticas recalculadas apenas para os itens 'Dentro':")
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Nova Média", f"R$ {descricao_normalidade['mean']:.2f}")
                c2.metric("Novo Mínimo", f"R$ {descricao_normalidade['min']:.2f}")
                c3.metric("Novo Máximo", f"R$ {descricao_normalidade['max']:.2f}")
                c4.metric("Novo Coef. Variação", f"{novo_coef_variacao:.2f}%")
                c5.metric("Contagem", f"{int(descricao_normalidade['count'])}")
            else:
                st.warning("Não há mais itens para analisar.")

        st.subheader(f"3. Painel Visual (Dados da Iteração {iteration})")
        df_visual = df_current_calc
        if not df_visual.empty:
            mapa_data = df_visual['estado'].value_counts().reset_index()
            mapa_data.columns = ['estado', 'contagem']
            fig_mapa = px.choropleth(mapa_data, geojson="https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson",
                                     featureidkey="properties.sigla", locations="estado", color="contagem", color_continuous_scale="Viridis",
                                     scope="south america", title="Distribuição de Itens por Estado", labels={'contagem': 'Número de Compras'})
            fig_mapa.update_geos(fitbounds="locations", visible=False)
            fig_mapa.update_layout(paper_bgcolor='rgba(0,0,0,0)', geo_bgcolor='rgba(0,0,0,0)')

            media_por_estado = df_visual.groupby('estado')['precoUnitario'].mean().sort_values(ascending=False).reset_index()
            fig_barras = px.bar(media_por_estado, x='estado', y='precoUnitario', title="Comparativo de Média de Preço por Estado",
                                labels={'precoUnitario': 'Preço Médio Unitário (R$)', 'estado': 'Estado'}, text_auto='.2f')
            fig_barras.update_traces(textposition='outside')
            fig_barras.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(fig_mapa, use_container_width=True)
            with c2: st.plotly_chart(fig_barras, use_container_width=True)
        else:
            st.info("Painel Visual não pode ser exibido pois não há dados 'Dentro' na iteração atual.")

        st.subheader("4. Lista Detalhada de Compras")
        df_history['Localidade'] = df_history['municipio'] + ' - ' + df_history['estado']
        base_url = "https://cnetmobile.estaleiro.serpro.gov.br/comprasnet-web/public/compras/acompanhamento-compra?compra="
        df_history['Link'] = base_url + df_history['idCompra'].astype(str)

        df_display = df_history[[
            'idCompra', 'Link', 'descricaoItem', 'Localidade', 'dataResultado', 
            'quantidade', 'Unidade Descritiva', 'precoUnitario', 'Status', 'Iteração Outlier'
        ]].rename(columns={
            'idCompra': 'ID Compra', 'descricaoItem': 'Descrição', 'dataResultado': 'Data',
            'quantidade': 'Qtd.', 'Unidade Descritiva': 'Unidade', 'precoUnitario': 'Valor Unitário'
        })
        
        st.dataframe(
            df_display.style.format({'Valor Unitário': 'R$ {:,.2f}', 'Data': '{:%d/%m/%Y}'})
            .apply(lambda x: ['background-color: #ffcccc' if v != 'Dentro' else '' for v in x], subset=['Status']),
            column_config={
                "Link": st.column_config.LinkColumn("Link da Compra", display_text="Acessar"),
                "Iteração Outlier": st.column_config.NumberColumn(format="%d")
            },
            use_container_width=True
        )
