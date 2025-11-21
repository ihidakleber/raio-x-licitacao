# Raio-X de Preços - Compras Governamentais

Este projeto é uma ferramenta interativa desenvolvida em Python para analisar o histórico de preços de materiais adquiridos pela administração pública. Utilizando a API de Dados Abertos do Governo Federal (`compras.gov.br`), o sistema permite identificar preços médios, variações regionais e remover outliers estatísticos para obter um "preço de referência" mais fidedigno.

## Funcionalidades

*   **Busca por CATMAT:** Consulta simultânea de múltiplos códigos do Catálogo de Materiais.
*   **Filtros Abrangentes:**
    *   **Geográfico:** Seleção por Estados, Regiões ou busca **Nacional** completa.
    *   **Temporal:** Padrão configurado para o último ano (D-365), totalmente ajustável.
*   **Padronização de Unidades:** Agrupa descrições de unidades (ex: "CX 12", "UN", "FRASCO") para evitar comparações errôneas entre embalagens diferentes.
*   **Detecção de Outliers:** Algoritmo iterativo que remove valores muito acima ou abaixo da média (baseado em desvio padrão) para limpar a base de cálculo.
*   **Visualização de Dados:**
    *   Mapas de calor (Choropleth) com distribuição de compras.
    *   Gráficos de barras comparativos por estado.
*   **Exportação/Consulta:** Tabela detalhada com links diretos para as notas de empenho/compras no portal oficial.

## Tecnologias Utilizadas

O projeto foi construído utilizando as seguintes bibliotecas:

*   **Streamlit:** Framework para criação da interface web interativa e dashboard.
*   **Pandas:** Manipulação, limpeza e filtragem dos dados tabulares.
*   **Requests:** Requisições HTTP para consumir a API do `compras.gov.br`.
*   **Plotly Express:** Geração de gráficos interativos e mapas geográficos.

## Instalação e Execução

Certifique-se de ter o Python instalado. Recomenda-se o uso de um ambiente virtual (`venv`).

1.  **Instale as dependências:**
    ```bash
    pip install streamlit pandas requests plotly
    ```

2.  **Execute a aplicação:**
    ```bash
    streamlit run app.py
    ```
    *Substitua `app.py` pelo nome do arquivo onde você salvou o código.*

## Como Usar

1.  **Painel (Filtros):**
    *   Insira os códigos **CATMAT** (ex: `459670`) separados por vírgula. *Dica: Insira códigos do mesmo produto para não enviesar a estatística.*
    *   Escolha a **Localidade** (Estados específicos, Regiões ou "NACIONAL").
    *   Ajuste o período de data (padrão: hoje até 1 ano atrás).
    *   Clique em **"Analisar Preços"**.

2.  **Passo 2 (Unidades de Medida):**
    *   Após a busca, o sistema mostrará as unidades encontradas (ex: "CAIXA 50", "UNIDADE").
    *   Selecione apenas as unidades comparáveis (ex: não misture "Caixa com 100" com "Unidade avulsa").

3.  **Análise e Outliers:**
    *   O sistema exibe a estatística inicial (Média, Mediana, Mínimo, Máximo, Coeficiente de Variação).
    *   Clique em **"Remover Outliers"** para refinar a análise. O sistema removerá itens fora do intervalo `Média ± 1 Desvio Padrão` e recalculará as métricas. Você pode repetir esse processo iterativamente.

4.  **Resultados:**
    *   Visualize a distribuição no mapa e o ranking de preços por estado.
    *   Consulte a tabela final, que contém o **Link da Compra** e o status de cada item (se foi considerado "Dentro" ou outlier "Acima/Abaixo").

## Observações Importantes

*   **Fonte de Dados:** Os dados são obtidos em tempo real da API `dadosabertos.compras.gov.br`. A disponibilidade depende do servidor do governo.
*   **Consistência:** A responsabilidade de inserir CATMATs que se referem ao mesmo objeto é do usuário. Misturar "Caneta" com "Computador" gerará dados inválidos.

---
*Desenvolvido para auxiliar na formação de preços de referência e auditoria de compras públicas.*
