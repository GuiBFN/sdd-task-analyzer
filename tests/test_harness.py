"""Test Harness do módulo TaskAnalyzer.

Suíte de validação automatizada derivada dos cenários de aceite da
especificação ``specs/task_analyzer_spec.md`` (versão 1.1).

Os testes são escritos a partir da especificação, nunca a partir do código
gerado. Se a implementação falhar um teste, corrige-se a implementação — nunca
o teste (regra PR-02 de ``CONTEXT_RULES.md``).

Rastreabilidade: cada teste declara no nome e na docstring a regra de negócio
ou o cenário de aceite que verifica.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from src.task_analyzer import TaskValidationError, analyze_tasks

# --------------------------------------------------------------------------- #
# Massa de teste de referência — Cenário 1 (todas as datas em UTC)
# --------------------------------------------------------------------------- #

UTC = timezone.utc


def _dt(dia: int, hora: int, minuto: int = 0) -> datetime:
    """Constrói um ``datetime`` em UTC em março de 2026.

    Args:
        dia: Dia do mês.
        hora: Hora do dia.
        minuto: Minuto da hora.

    Returns:
        A data e hora correspondente, com fuso UTC.
    """
    return datetime(2026, 3, dia, hora, minuto, tzinfo=UTC)


@pytest.fixture
def massa_cenario_1() -> list[dict[str, Any]]:
    """Massa de teste de referência do Cenário 1 da especificação.

    Returns:
        Cinco tarefas: três concluídas (duas de prioridade alta, uma média),
        uma pendente e uma cancelada.
    """
    return [
        {
            "id_tarefa": 1,
            "data_criacao": _dt(1, 8),
            "data_inicio": _dt(1, 8),
            "data_conclusao": _dt(1, 10),
            "prazo": _dt(1, 12),
            "prioridade": "alta",
            "status": "concluida",
        },
        {
            "id_tarefa": 2,
            "data_criacao": _dt(1, 8),
            "data_inicio": _dt(1, 8),
            "data_conclusao": _dt(1, 14),
            "prazo": _dt(1, 12),
            "prioridade": "alta",
            "status": "concluida",
        },
        {
            "id_tarefa": 3,
            "data_criacao": _dt(1, 8),
            "data_inicio": _dt(1, 8),
            "data_conclusao": _dt(1, 9),
            "prazo": _dt(1, 10),
            "prioridade": "media",
            "status": "concluida",
        },
        {
            "id_tarefa": 4,
            "data_criacao": _dt(1, 8),
            "data_inicio": _dt(1, 8),
            "data_conclusao": None,
            "prazo": _dt(2, 12),
            "prioridade": "baixa",
            "status": "pendente",
        },
        {
            "id_tarefa": 5,
            "data_criacao": _dt(1, 8),
            "data_inicio": None,
            "data_conclusao": None,
            "prazo": _dt(2, 12),
            "prioridade": "baixa",
            "status": "cancelada",
        },
    ]


def _tarefa_valida(**sobrescritas: Any) -> dict[str, Any]:
    """Cria uma tarefa válida, aplicando as sobrescritas informadas.

    Args:
        **sobrescritas: Campos a substituir na tarefa base.

    Returns:
        O registro de tarefa resultante.
    """
    base: dict[str, Any] = {
        "id_tarefa": 1,
        "data_criacao": _dt(1, 8),
        "data_inicio": _dt(1, 8),
        "data_conclusao": _dt(1, 10),
        "prazo": _dt(1, 12),
        "prioridade": "alta",
        "status": "concluida",
    }
    base.update(sobrescritas)
    return base


# --------------------------------------------------------------------------- #
# Cenário 1 — Sucesso: métricas corretas
# --------------------------------------------------------------------------- #


class TestCenario1Sucesso:
    """Cenário 1 — conjunto válido produz métricas corretas."""

    def test_total_tarefas(self, massa_cenario_1: list[dict[str, Any]]) -> None:
        """RN-08: total_tarefas conta todas as tarefas recebidas."""
        assert analyze_tasks(massa_cenario_1)["total_tarefas"] == 5

    def test_total_concluidas(self, massa_cenario_1: list[dict[str, Any]]) -> None:
        """RN-01: apenas tarefas com status concluida são contadas."""
        assert analyze_tasks(massa_cenario_1)["total_concluidas"] == 3

    def test_total_pendentes(self, massa_cenario_1: list[dict[str, Any]]) -> None:
        """RN-01: apenas tarefas com status pendente são contadas."""
        assert analyze_tasks(massa_cenario_1)["total_pendentes"] == 1

    def test_tempo_medio_conclusao_horas_geral(
        self, massa_cenario_1: list[dict[str, Any]]
    ) -> None:
        """RN-02: média de (2h + 6h + 1h) / 3 = 3.0 horas."""
        assert analyze_tasks(massa_cenario_1)["tempo_medio_conclusao_horas"] == 3.0

    def test_taxa_atraso_percentual_geral(
        self, massa_cenario_1: list[dict[str, Any]]
    ) -> None:
        """RN-03 e RN-07: 1 atrasada em 3 concluídas = 33.33 por cento."""
        assert analyze_tasks(massa_cenario_1)["taxa_atraso_percentual"] == 33.33

    @pytest.mark.parametrize(
        ("prioridade", "esperado"),
        [
            (
                "alta",
                {
                    "total_tarefas": 2,
                    "total_concluidas": 2,
                    "total_pendentes": 0,
                    "tempo_medio_conclusao_horas": 4.0,
                    "taxa_atraso_percentual": 50.0,
                },
            ),
            (
                "media",
                {
                    "total_tarefas": 1,
                    "total_concluidas": 1,
                    "total_pendentes": 0,
                    "tempo_medio_conclusao_horas": 1.0,
                    "taxa_atraso_percentual": 0.0,
                },
            ),
            (
                "baixa",
                {
                    "total_tarefas": 2,
                    "total_concluidas": 0,
                    "total_pendentes": 1,
                    "tempo_medio_conclusao_horas": 0.0,
                    "taxa_atraso_percentual": 0.0,
                },
            ),
        ],
    )
    def test_indicadores_por_prioridade(
        self,
        massa_cenario_1: list[dict[str, Any]],
        prioridade: str,
        esperado: dict[str, Any],
    ) -> None:
        """RN-09: métricas agrupadas por prioridade conferem com o contrato."""
        resultado = analyze_tasks(massa_cenario_1)
        assert resultado["indicadores_por_prioridade"][prioridade] == esperado

    def test_estrutura_da_saida(self, massa_cenario_1: list[dict[str, Any]]) -> None:
        """Contrato 1.3: a saída contém exatamente as chaves especificadas."""
        resultado = analyze_tasks(massa_cenario_1)
        assert set(resultado) == {
            "total_tarefas",
            "total_concluidas",
            "total_pendentes",
            "tempo_medio_conclusao_horas",
            "taxa_atraso_percentual",
            "indicadores_por_prioridade",
        }

    def test_todas_prioridades_presentes(
        self, massa_cenario_1: list[dict[str, Any]]
    ) -> None:
        """RN-10: as três prioridades aparecem sempre na saída."""
        resultado = analyze_tasks(massa_cenario_1)
        assert set(resultado["indicadores_por_prioridade"]) == {
            "baixa",
            "media",
            "alta",
        }


# --------------------------------------------------------------------------- #
# Cenário 2 — Exceção: entradas inválidas
# --------------------------------------------------------------------------- #


class TestCenario2Excecao:
    """Cenário 2 — entradas inválidas disparam TaskValidationError."""

    def test_conclusao_anterior_a_criacao(self) -> None:
        """Cenário 2: data_conclusao < data_criacao dispara a exceção."""
        tarefa = _tarefa_valida(
            data_criacao=_dt(1, 10), data_inicio=None, data_conclusao=_dt(1, 8)
        )
        with pytest.raises(TaskValidationError, match="anterior à criação"):
            analyze_tasks([tarefa])

    def test_inicio_anterior_a_criacao(self) -> None:
        """RN-04: data_inicio anterior à criação é inconsistência temporal."""
        tarefa = _tarefa_valida(data_criacao=_dt(1, 10), data_inicio=_dt(1, 8))
        with pytest.raises(TaskValidationError):
            analyze_tasks([tarefa])

    def test_conclusao_anterior_ao_inicio(self) -> None:
        """RN-04: data_conclusao anterior ao início é inconsistência temporal."""
        tarefa = _tarefa_valida(
            data_criacao=_dt(1, 7), data_inicio=_dt(1, 10), data_conclusao=_dt(1, 8)
        )
        with pytest.raises(TaskValidationError, match="anterior ao início"):
            analyze_tasks([tarefa])

    @pytest.mark.parametrize(
        "sobrescritas",
        [
            pytest.param({"prioridade": "urgente"}, id="prioridade-fora-do-dominio"),
            pytest.param({"status": "finalizada"}, id="status-fora-do-dominio"),
            pytest.param({"id_tarefa": 0}, id="id-zero"),
            pytest.param({"id_tarefa": -3}, id="id-negativo"),
            pytest.param({"id_tarefa": "1"}, id="id-nao-inteiro"),
            pytest.param({"prazo": None}, id="prazo-ausente"),
            pytest.param({"data_criacao": None}, id="data-criacao-ausente"),
            pytest.param({"data_criacao": "2026-03-01"}, id="data-como-string"),
            pytest.param({"prioridade": None}, id="prioridade-ausente"),
            pytest.param({"status": 1}, id="status-nao-string"),
        ],
    )
    def test_registro_malformado(self, sobrescritas: dict[str, Any]) -> None:
        """Contrato 1.4: registro malformado dispara TaskValidationError."""
        with pytest.raises(TaskValidationError):
            analyze_tasks([_tarefa_valida(**sobrescritas)])

    def test_identificador_ausente(self) -> None:
        """Contrato 1.1: id_tarefa é campo obrigatório."""
        tarefa = _tarefa_valida()
        del tarefa["id_tarefa"]
        with pytest.raises(TaskValidationError, match="sem identificador"):
            analyze_tasks([tarefa])

    def test_identificador_booleano_e_rejeitado(self) -> None:
        """Contrato 1.1: bool não é identificador válido, apesar de ser int."""
        with pytest.raises(TaskValidationError, match="esperado int"):
            analyze_tasks([_tarefa_valida(id_tarefa=True)])

    def test_identificador_duplicado(self) -> None:
        """Contrato 1.1: id_tarefa deve ser único na mesma lista."""
        tarefas = [_tarefa_valida(id_tarefa=7), _tarefa_valida(id_tarefa=7)]
        with pytest.raises(TaskValidationError, match="duplicado"):
            analyze_tasks(tarefas)

    def test_entrada_nao_e_lista(self) -> None:
        """Contrato 1.1: a entrada deve ser uma lista de tarefas."""
        with pytest.raises(TaskValidationError, match="esperado list"):
            analyze_tasks({"id_tarefa": 1})  # type: ignore[arg-type]

    def test_registro_nao_e_dicionario(self) -> None:
        """Contrato 1.1: cada registro deve ser um dicionário."""
        with pytest.raises(TaskValidationError, match="esperado dict"):
            analyze_tasks(["tarefa"])  # type: ignore[list-item]

    def test_mensagem_de_erro_identifica_a_tarefa(self) -> None:
        """DA-06: a mensagem de erro nomeia a tarefa e o campo problemático."""
        with pytest.raises(TaskValidationError) as erro:
            analyze_tasks([_tarefa_valida(id_tarefa=42, prioridade="urgente")])
        assert "42" in str(erro.value)
        assert "prioridade" in str(erro.value)


# --------------------------------------------------------------------------- #
# Casos de borda
# --------------------------------------------------------------------------- #


class TestCasosDeBorda:
    """Bordas do contrato: ausência de dados, limites e pureza."""

    def test_lista_vazia_retorna_zeros(self) -> None:
        """RN-05: lista vazia devolve zeros, sem disparar exceção."""
        resultado = analyze_tasks([])
        assert resultado["total_tarefas"] == 0
        assert resultado["total_concluidas"] == 0
        assert resultado["total_pendentes"] == 0
        assert resultado["tempo_medio_conclusao_horas"] == 0.0
        assert resultado["taxa_atraso_percentual"] == 0.0

    def test_lista_vazia_mantem_estrutura_por_prioridade(self) -> None:
        """RN-10: mesmo vazia, a saída traz as três prioridades zeradas."""
        indicadores = analyze_tasks([])["indicadores_por_prioridade"]
        assert set(indicadores) == {"baixa", "media", "alta"}
        for bloco in indicadores.values():
            assert bloco["tempo_medio_conclusao_horas"] == 0.0
            assert bloco["taxa_atraso_percentual"] == 0.0

    def test_apenas_pendentes_nao_dispara_excecao(self) -> None:
        """RN-05: conjunto só com pendentes devolve médias 0.0."""
        tarefas = [
            _tarefa_valida(
                id_tarefa=1, status="pendente", data_conclusao=None, prioridade="baixa"
            ),
            _tarefa_valida(
                id_tarefa=2, status="pendente", data_conclusao=None, prioridade="alta"
            ),
        ]
        resultado = analyze_tasks(tarefas)
        assert resultado["total_pendentes"] == 2
        assert resultado["total_concluidas"] == 0
        assert resultado["tempo_medio_conclusao_horas"] == 0.0
        assert resultado["taxa_atraso_percentual"] == 0.0

    def test_apenas_canceladas_nao_dispara_excecao(self) -> None:
        """RN-05: conjunto só com canceladas devolve médias 0.0."""
        tarefa = _tarefa_valida(status="cancelada", data_conclusao=None)
        resultado = analyze_tasks([tarefa])
        assert resultado["total_tarefas"] == 1
        assert resultado["tempo_medio_conclusao_horas"] == 0.0

    def test_conclusao_exatamente_no_prazo_nao_e_atraso(self) -> None:
        """RN-03: conclusão igual ao prazo não conta como atraso."""
        tarefa = _tarefa_valida(data_conclusao=_dt(1, 12), prazo=_dt(1, 12))
        assert analyze_tasks([tarefa])["taxa_atraso_percentual"] == 0.0

    def test_um_segundo_apos_o_prazo_e_atraso(self) -> None:
        """RN-03: qualquer instante após o prazo conta como atraso."""
        tarefa = _tarefa_valida(
            data_conclusao=_dt(1, 12) + timedelta(seconds=1), prazo=_dt(1, 12)
        )
        assert analyze_tasks([tarefa])["taxa_atraso_percentual"] == 100.0

    def test_arredondamento_em_duas_casas(self) -> None:
        """RN-07: tempos e percentuais são arredondados em duas casas."""
        tarefa = _tarefa_valida(
            data_criacao=_dt(1, 8), data_inicio=_dt(1, 8), data_conclusao=_dt(1, 8, 40)
        )
        assert analyze_tasks([tarefa])["tempo_medio_conclusao_horas"] == 0.67

    def test_tarefa_concluida_sem_data_conclusao_nao_entra_na_media(self) -> None:
        """RN-01: concluída sem data de conclusão não entra no cálculo."""
        tarefa = _tarefa_valida(data_conclusao=None)
        resultado = analyze_tasks([tarefa])
        assert resultado["total_concluidas"] == 0
        assert resultado["tempo_medio_conclusao_horas"] == 0.0

    def test_datas_sem_fuso_sao_tratadas_como_utc(self) -> None:
        """RN-06: datetime naive é interpretado como UTC."""
        tarefa = _tarefa_valida(
            data_criacao=datetime(2026, 3, 1, 8, 0),
            data_inicio=datetime(2026, 3, 1, 8, 0),
            data_conclusao=datetime(2026, 3, 1, 10, 0),
            prazo=datetime(2026, 3, 1, 12, 0),
        )
        assert analyze_tasks([tarefa])["tempo_medio_conclusao_horas"] == 2.0

    def test_datas_com_outro_fuso_sao_convertidas_para_utc(self) -> None:
        """RN-06: datetime com outro fuso é convertido antes do cálculo."""
        brasilia = timezone(timedelta(hours=-3))
        tarefa = _tarefa_valida(
            data_criacao=datetime(2026, 3, 1, 5, 0, tzinfo=brasilia),
            data_inicio=None,
            data_conclusao=datetime(2026, 3, 1, 7, 0, tzinfo=brasilia),
            prazo=datetime(2026, 3, 1, 9, 0, tzinfo=brasilia),
        )
        assert analyze_tasks([tarefa])["tempo_medio_conclusao_horas"] == 2.0

    def test_nao_modifica_a_lista_de_entrada(
        self, massa_cenario_1: list[dict[str, Any]]
    ) -> None:
        """RN-11: o módulo é puro e não altera a lista recebida."""
        original = copy.deepcopy(massa_cenario_1)
        analyze_tasks(massa_cenario_1)
        assert massa_cenario_1 == original

    def test_execucoes_repetidas_produzem_o_mesmo_resultado(
        self, massa_cenario_1: list[dict[str, Any]]
    ) -> None:
        """RN-11: a análise é determinística."""
        assert analyze_tasks(massa_cenario_1) == analyze_tasks(massa_cenario_1)
