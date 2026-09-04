"""
app.py — App SPPB para fisioterapeutas

Fluxo:
  1. Fisioterapeuta preenche os dados brutos do teste (tempos, sim/não).
  2. O escore é calculado automaticamente pela lógica oficial do protocolo.
  3. O resultado é salvo no Google Sheets.
  4. Um dashboard mostra a evolução do paciente e a distribuição da coorte.

Execução local:
    streamlit run app.py

Configuração de credenciais (Streamlit Cloud):
    Em Settings > Secrets, defina:

    [gcp_service_account]
    type = "service_account"
    project_id = "..."
    private_key_id = "..."
    private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
    client_email = "...@....iam.gserviceaccount.com"
    client_id = "..."
    ...

    sheet_id = "ID_DA_SUA_PLANILHA_AQUI"
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from sppb_score import (
    calcular_sppb,
    pontuar_equilibrio,
    pontuar_marcha,
    pontuar_sentar_levantar,
)
from sheets_utils import carregar_historico, conectar_planilha, salvar_avaliacao

st.set_page_config(page_title="SPPB — Avaliação Física", layout="wide")


# ---------------------------------------------------------------------
# Conexão com Google Sheets (cacheada para não reconectar a cada clique)
# ---------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def obter_worksheet():
    credenciais = dict(st.secrets["gcp_service_account"])
    sheet_id = st.secrets["sheet_id"]
    return conectar_planilha(credenciais, sheet_id)


# ---------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------

st.title("Short Physical Performance Battery (SPPB)")

aba_aplicar, aba_dashboard = st.tabs(["Aplicar teste", "Dashboard"])


# =======================================================================
# ABA 1 — APLICAÇÃO DO TESTE
# =======================================================================

with aba_aplicar:
    st.subheader("Identificação")
    col1, col2, col3 = st.columns(3)
    with col1:
        id_paciente = st.text_input("ID do paciente (prontuário)", key="id_paciente")
    with col2:
        data_avaliacao = st.date_input("Data da avaliação")
    with col3:
        avaliador = st.text_input("Avaliador (iniciais)")

    st.divider()

    # --- 1. EQUILÍBRIO -------------------------------------------------
    st.subheader("1. Testes de equilíbrio")
    st.caption("Siga a ordem: pés juntos → semi-tandem → tandem. "
               "Se o paciente falhar em um teste, os campos seguintes ficam desabilitados.")

    pes_juntos_ok = st.radio(
        "A. Pés juntos — segurou 10 segundos?", ["Sim", "Não"], horizontal=True, key="pj"
    ) == "Sim"

    semi_tandem_ok = None
    tandem_segundos = None

    if pes_juntos_ok:
        semi_tandem_ok = st.radio(
            "B. Semi-tandem — segurou 10 segundos?", ["Sim", "Não"], horizontal=True, key="st"
        ) == "Sim"

        if semi_tandem_ok:
            tandem_segundos = st.number_input(
                "C. Tandem — tempo mantido (segundos, máx. 10)",
                min_value=0.0, max_value=10.0, step=0.1, key="td"
            )

    resultado_equilibrio = pontuar_equilibrio(pes_juntos_ok, semi_tandem_ok, tandem_segundos)
    st.info(f"Escore de equilíbrio: **{resultado_equilibrio.pontos}/4** — {resultado_equilibrio.detalhe}")

    st.divider()

    # --- 2. MARCHA -------------------------------------------------------
    st.subheader("2. Teste de velocidade de marcha")
    comprimento = st.radio("Comprimento do percurso", ["4m", "3m"], horizontal=True)
    marcha_incapaz = st.checkbox("Paciente incapaz de realizar o teste")

    tempo1 = tempo2 = None
    if not marcha_incapaz:
        colm1, colm2 = st.columns(2)
        with colm1:
            tempo1 = st.number_input("Tentativa 1 (segundos)", min_value=0.0, step=0.1, key="t1")
        with colm2:
            tempo2 = st.number_input("Tentativa 2 (segundos)", min_value=0.0, step=0.1, key="t2")

    resultado_marcha = pontuar_marcha(comprimento, tempo1 or None, tempo2 or None, marcha_incapaz)
    st.info(f"Escore de marcha: **{resultado_marcha.pontos}/4** — {resultado_marcha.detalhe}")

    st.divider()

    # --- 3. SENTAR-LEVANTAR ----------------------------------------------
    st.subheader("3. Teste de sentar-levantar (força)")
    pre_teste_ok = st.radio(
        "Pré-teste — conseguiu levantar 1x sem usar os braços?",
        ["Sim", "Não"], horizontal=True, key="pre"
    ) == "Sim"

    tempo_5rep = None
    incapaz_5rep = False
    if pre_teste_ok:
        incapaz_5rep = st.checkbox("Não completou as 5 repetições ou levou mais de 60s")
        if not incapaz_5rep:
            tempo_5rep = st.number_input(
                "Tempo para completar 5 repetições (segundos)", min_value=0.0, step=0.1, key="t5"
            )

    resultado_forca = pontuar_sentar_levantar(pre_teste_ok, tempo_5rep or None, incapaz_5rep)
    st.info(f"Escore de força: **{resultado_forca.pontos}/4** — {resultado_forca.detalhe}")

    st.divider()

    # --- RESULTADO FINAL ---------------------------------------------------
    resultado = calcular_sppb(resultado_equilibrio, resultado_marcha, resultado_forca)

    st.subheader("Resultado")
    colr1, colr2, colr3 = st.columns(3)
    colr1.metric("Escore total SPPB", f"{resultado.escore_total}/12")
    colr2.metric("Classificação", resultado.classificacao)
    colr3.metric("Equilíbrio / Marcha / Força",
                 f"{resultado.escore_equilibrio} / {resultado.escore_marcha} / {resultado.escore_forca}")

    if resultado.escore_total < 10:
        st.warning(resultado.alerta_mortalidade)
    else:
        st.success(resultado.alerta_mortalidade)

    st.divider()

    if st.button("💾 Salvar avaliação", type="primary"):
        if not id_paciente or not avaliador:
            st.error("Preencha o ID do paciente e o avaliador antes de salvar.")
        else:
            try:
                ws = obter_worksheet()
                salvar_avaliacao(
                    ws,
                    id_paciente=id_paciente,
                    data_avaliacao=str(data_avaliacao),
                    avaliador=avaliador,
                    comprimento_percurso=comprimento,
                    resultado_sppb=resultado,
                )
                st.success("Avaliação salva na planilha com sucesso.")
            except Exception as e:
                st.error(f"Erro ao salvar na planilha: {e}")


# =======================================================================
# ABA 2 — DASHBOARD
# =======================================================================

with aba_dashboard:
    st.subheader("Dashboard de avaliações")

    if st.button("🔄 Atualizar dados"):
        st.cache_data.clear()

    @st.cache_data(ttl=60, show_spinner="Carregando dados da planilha...")
    def carregar_dados():
        ws = obter_worksheet()
        registros = carregar_historico(ws)
        return pd.DataFrame(registros)

    try:
        df = carregar_dados()
    except Exception as e:
        st.error(f"Não foi possível carregar os dados: {e}")
        df = pd.DataFrame()

    if df.empty:
        st.info("Nenhuma avaliação registrada ainda.")
    else:
        df["data_avaliacao"] = pd.to_datetime(df["data_avaliacao"], errors="coerce")
        df["escore_total"] = pd.to_numeric(df["escore_total"], errors="coerce")

        colf1, colf2 = st.columns(2)
        with colf1:
            pacientes = ["Todos"] + sorted(df["id_paciente"].dropna().unique().tolist())
            filtro_paciente = st.selectbox("Filtrar por paciente", pacientes)
        with colf2:
            st.metric("Total de avaliações", len(df))

        df_filtrado = df if filtro_paciente == "Todos" else df[df["id_paciente"] == filtro_paciente]

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**Distribuição por classificação (coorte)**")
            contagem = df["classificacao"].value_counts().reset_index()
            contagem.columns = ["classificacao", "quantidade"]
            fig_pizza = px.pie(contagem, names="classificacao", values="quantidade",
                                color="classificacao",
                                color_discrete_map={
                                    "Muito baixo": "#d62728",
                                    "Baixo": "#ff7f0e",
                                    "Intermediário": "#1f77b4",
                                    "Alto": "#2ca02c",
                                })
            st.plotly_chart(fig_pizza, use_container_width=True)

        with col_b:
            st.markdown("**Evolução do escore ao longo do tempo**")
            if filtro_paciente != "Todos":
                fig_linha = px.line(
                    df_filtrado.sort_values("data_avaliacao"),
                    x="data_avaliacao", y="escore_total", markers=True,
                    range_y=[0, 12],
                )
                fig_linha.add_hline(y=10, line_dash="dash", line_color="orange",
                                     annotation_text="Corte de risco (<10)")
                fig_linha.add_hline(y=5, line_dash="dash", line_color="red",
                                     annotation_text="Corte crítico (<5)")
                st.plotly_chart(fig_linha, use_container_width=True)
            else:
                st.caption("Selecione um paciente específico para ver a evolução individual.")

        st.markdown("**Tabela de avaliações**")
        st.dataframe(df_filtrado.sort_values("timestamp", ascending=False), use_container_width=True)
