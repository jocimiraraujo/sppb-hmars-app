"""
sheets_utils.py

Camada de armazenamento no Google Sheets, usando uma Service Account
do Google Cloud (não usa OAuth interativo — ideal para um app que
vários fisioterapeutas vão usar sem cada um logar na própria conta
Google).

CONFIGURAÇÃO NECESSÁRIA (feita uma única vez, fora do código):

1. No Google Cloud Console, crie um projeto e ative a API do
   Google Sheets e do Google Drive.
2. Crie uma "Service Account" e gere uma chave em formato JSON.
3. Compartilhe a planilha do Google Sheets com o e-mail da service
   account (algo como nome@projeto.iam.gserviceaccount.com), com
   permissão de Editor.
4. Salve o JSON da service account em local seguro. NO STREAMLIT
   CLOUD, isso vai em st.secrets (não em arquivo no repositório).
5. Defina o ID da planilha (está na URL, entre /d/ e /edit).
"""

from __future__ import annotations

import datetime
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CABECALHO = [
    "timestamp",
    "id_paciente",
    "data_avaliacao",
    "avaliador",
    "comprimento_percurso",
    "escore_equilibrio",
    "escore_marcha",
    "escore_forca",
    "escore_total",
    "classificacao",
    "alerta_mortalidade",
]


def conectar_planilha(credenciais_dict: dict, sheet_id: str, aba: str = "dados"):
    """
    Retorna o objeto Worksheet pronto para leitura/escrita.
    credenciais_dict: conteúdo do JSON da service account (dict, não string).
    sheet_id: ID da planilha (da URL do Google Sheets).
    aba: nome da aba/planilha interna a ser usada.
    """
    creds = Credentials.from_service_account_info(credenciais_dict, scopes=SCOPES)
    cliente = gspread.authorize(creds)
    planilha = cliente.open_by_key(sheet_id)

    try:
        aba_dados = planilha.worksheet(aba)
    except gspread.WorksheetNotFound:
        aba_dados = planilha.add_worksheet(title=aba, rows=1000, cols=len(CABECALHO))
        aba_dados.append_row(CABECALHO)

    # Garante que o cabeçalho existe mesmo se a aba já existia vazia
    primeira_linha = aba_dados.row_values(1)
    if primeira_linha != CABECALHO:
        aba_dados.insert_row(CABECALHO, index=1)

    return aba_dados


def salvar_avaliacao(
    worksheet,
    id_paciente: str,
    data_avaliacao: str,
    avaliador: str,
    comprimento_percurso: str,
    resultado_sppb: Any,
) -> None:
    """Acrescenta uma linha com os dados da avaliação ao final da planilha."""
    linha = [
        datetime.datetime.now().isoformat(timespec="seconds"),
        id_paciente,
        data_avaliacao,
        avaliador,
        comprimento_percurso,
        resultado_sppb.escore_equilibrio,
        resultado_sppb.escore_marcha,
        resultado_sppb.escore_forca,
        resultado_sppb.escore_total,
        resultado_sppb.classificacao,
        resultado_sppb.alerta_mortalidade,
    ]
    worksheet.append_row(linha, value_input_option="USER_ENTERED")


def carregar_historico(worksheet) -> list[dict]:
    """Retorna todas as avaliações já registradas, como lista de dicionários."""
    return worksheet.get_all_records()
