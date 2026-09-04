"""
sppb_score.py

Implementa a lógica oficial de pontuação da Short Physical Performance
Battery (SPPB), conforme o protocolo original (Guralnik et al., 1994)
e a síntese de classificação de risco de mortalidade descrita em:

de Fátima Ribeiro Silva et al. (2021). Int. J. Environ. Res. Public
Health, 18, 10612.

A pontuação NÃO é uma soma independente de 3 campos: os testes de
equilíbrio e de sentar-levantar têm regras de interrupção antecipada
(early stopping) que precisam ser respeitadas para o escore ficar
clinicamente correto.
"""

from dataclasses import dataclass
from typing import Optional, Literal

MotivoNaoRealizacao = Literal[
    "tentou_mas_incapaz",
    "incapaz_sem_ajuda",
    "inseguro_avaliador",
    "inseguro_paciente",
    "nao_compreendeu",
    "outro",
    "recusou",
]


# ---------------------------------------------------------------------
# 1. TESTES DE EQUILÍBRIO
# ---------------------------------------------------------------------

@dataclass
class ResultadoEquilibrio:
    pontos: int
    detalhe: str


def pontuar_equilibrio(
    pes_juntos_segurou_10s: bool,
    semi_tandem_segurou_10s: Optional[bool] = None,
    tandem_segundos: Optional[float] = None,
) -> ResultadoEquilibrio:
    """
    Aplica a lógica em cascata do protocolo:
      - Pés juntos: 10s -> 1pt. Se falhar -> ENCERRA (0pt total).
      - Semi-tandem: 10s -> +1pt. Se falhar -> ENCERRA (mantém o que já tinha).
      - Tandem: 10s -> +2pt | 3-9,99s -> +1pt | <3s -> +0pt.

    Os parâmetros posteriores só devem ser fornecidos se o teste
    anterior foi bem-sucedido (a UI deve impedir preenchimento fora
    de ordem, mas a função também protege contra isso).
    """
    if not pes_juntos_segurou_10s:
        return ResultadoEquilibrio(0, "Encerrado no teste pés juntos (0 pts)")

    pontos = 1

    if semi_tandem_segurou_10s is None:
        return ResultadoEquilibrio(pontos, "Pés juntos OK; semi-tandem não registrado")

    if not semi_tandem_segurou_10s:
        return ResultadoEquilibrio(pontos, "Encerrado no semi-tandem (1 pt)")

    pontos += 1

    if tandem_segundos is None:
        return ResultadoEquilibrio(pontos, "Semi-tandem OK; tandem não registrado")

    if tandem_segundos >= 10:
        pontos += 2
        detalhe = "Completou tandem 10s (4 pts)"
    elif 3 <= tandem_segundos < 10:
        pontos += 1
        detalhe = "Tandem 3-9,99s (3 pts)"
    else:
        detalhe = "Tandem <3s (2 pts)"

    return ResultadoEquilibrio(pontos, detalhe)


# ---------------------------------------------------------------------
# 2. TESTE DE MARCHA (4 metros OU 3 metros)
# ---------------------------------------------------------------------

@dataclass
class ResultadoMarcha:
    pontos: int
    tempo_usado: Optional[float]
    detalhe: str


_CORTES_4M = [(4.82, 4), (6.20, 3), (8.70, 2), (float("inf"), 1)]
_CORTES_3M = [(3.62, 4), (4.65, 3), (6.52, 2), (float("inf"), 1)]


def pontuar_marcha(
    comprimento_percurso: Literal["3m", "4m"],
    tempo_tentativa_1: Optional[float],
    tempo_tentativa_2: Optional[float],
    incapaz: bool = False,
) -> ResultadoMarcha:
    """
    Registra a MELHOR (menor) das duas tentativas e aplica a tabela
    de corte correspondente ao comprimento do percurso usado.
    """
    if incapaz:
        return ResultadoMarcha(0, None, "Incapaz de realizar (0 pts)")

    tempos_validos = [t for t in (tempo_tentativa_1, tempo_tentativa_2) if t is not None]
    if not tempos_validos:
        return ResultadoMarcha(0, None, "Nenhum tempo registrado")

    melhor_tempo = min(tempos_validos)
    cortes = _CORTES_4M if comprimento_percurso == "4m" else _CORTES_3M

    for limite, pontos in cortes:
        if melhor_tempo < limite:
            return ResultadoMarcha(
                pontos, melhor_tempo, f"Tempo {melhor_tempo:.2f}s ({comprimento_percurso})"
            )

    # segurança: nunca deve chegar aqui pois o último limite é infinito
    return ResultadoMarcha(1, melhor_tempo, "Tempo acima de todos os cortes (1 pt)")


# ---------------------------------------------------------------------
# 3. TESTE DE SENTAR-LEVANTAR (chair stand)
# ---------------------------------------------------------------------

@dataclass
class ResultadoSentarLevantar:
    pontos: int
    detalhe: str


def pontuar_sentar_levantar(
    conseguiu_pre_teste_sem_bracos: bool,
    tempo_5_repeticoes: Optional[float] = None,
    incapaz_ou_excedeu_60s: bool = False,
) -> ResultadoSentarLevantar:
    """
    Pré-teste: 1 repetição sem usar os braços.
      - Se NÃO conseguir -> encerra com 0 pontos (não faz as 5 repetições).
    Se conseguir, aplica-se o teste cronometrado de 5 repetições.
    """
    if not conseguiu_pre_teste_sem_bracos:
        return ResultadoSentarLevantar(0, "Não conseguiu levantar sem os braços (0 pts)")

    if incapaz_ou_excedeu_60s or tempo_5_repeticoes is None:
        return ResultadoSentarLevantar(0, "Incapaz de completar 5 repetições ou tempo >60s (0 pts)")

    t = tempo_5_repeticoes
    if t <= 11.19:
        return ResultadoSentarLevantar(4, f"{t:.2f}s (4 pts)")
    elif t <= 13.69:
        return ResultadoSentarLevantar(3, f"{t:.2f}s (3 pts)")
    elif t <= 16.69:
        return ResultadoSentarLevantar(2, f"{t:.2f}s (2 pts)")
    else:
        return ResultadoSentarLevantar(1, f"{t:.2f}s (1 pt)")


# ---------------------------------------------------------------------
# 4. ESCORE TOTAL E CLASSIFICAÇÃO DE RISCO
# ---------------------------------------------------------------------

@dataclass
class ResultadoSPPB:
    escore_equilibrio: int
    escore_marcha: int
    escore_forca: int
    escore_total: int
    classificacao: str
    alerta_mortalidade: str


def classificar_risco(escore_total: int) -> str:
    """Classificação em 4 faixas, conforme Figura 3 do artigo de revisão."""
    if escore_total <= 3:
        return "Muito baixo"
    elif escore_total <= 6:
        return "Baixo"
    elif escore_total <= 9:
        return "Intermediário"
    else:
        return "Alto"


def alerta_de_mortalidade(escore_total: int) -> str:
    """
    Baseado nas conclusões da revisão (de Fátima Ribeiro Silva et al., 2021):
      - Escore < 10: associado a maior risco de mortalidade por todas as causas
        (achado consistente na maioria dos estudos revisados).
      - Escore < 5: único ponto de corte formalmente validado com sensibilidade/
        especificidade (Corsonello et al., 2012 — idosos pós-alta hospitalar,
        AUC 0,66, sensibilidade 0,66, especificidade 0,62). Este ponto de corte
        foi derivado de uma população específica (pós-alta hospitalar) e pode
        não se generalizar a outros contextos.
    """
    if escore_total < 5:
        return (
            "Escore <5: em população pós-alta hospitalar, associado a maior risco "
            "de mortalidade em 1 ano (Corsonello et al., 2012). Atenção clínica reforçada."
        )
    elif escore_total < 10:
        return "Escore <10: associado a maior risco de mortalidade por todas as causas na literatura."
    else:
        return "Escore ≥10: associado a maior sobrevida na literatura."


def calcular_sppb(
    resultado_equilibrio: ResultadoEquilibrio,
    resultado_marcha: ResultadoMarcha,
    resultado_forca: ResultadoSentarLevantar,
) -> ResultadoSPPB:
    total = resultado_equilibrio.pontos + resultado_marcha.pontos + resultado_forca.pontos
    return ResultadoSPPB(
        escore_equilibrio=resultado_equilibrio.pontos,
        escore_marcha=resultado_marcha.pontos,
        escore_forca=resultado_forca.pontos,
        escore_total=total,
        classificacao=classificar_risco(total),
        alerta_mortalidade=alerta_de_mortalidade(total),
    )
