"""Módulo TaskAnalyzer — análise de tarefas e métricas de produtividade.

Implementa o contrato executável definido em ``specs/task_analyzer_spec.md``
(versão 1.1) sob as regras de governança de ``CONTEXT_RULES.md``.

O módulo é puro e determinístico: não persiste dados, não acessa rede, não lê
o relógio do sistema e não altera a lista recebida. A mesma entrada produz
sempre exatamente a mesma saída.

Interface pública:
    analyze_tasks: calcula as métricas agregadas de um conjunto de tarefas.
    TaskValidationError: exceção disparada para entradas inválidas.

Requer Python 3.11 ou superior.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Final

__all__ = ["analyze_tasks", "TaskValidationError"]

logger: Final[logging.Logger] = logging.getLogger(__name__)

PRIORIDADES: Final[tuple[str, ...]] = ("baixa", "media", "alta")
STATUS_VALIDOS: Final[tuple[str, ...]] = ("concluida", "pendente", "cancelada")

CASAS_DECIMAIS: Final[int] = 2
SEGUNDOS_POR_HORA: Final[float] = 3600.0


class TaskValidationError(Exception):
    """Disparada quando uma tarefa da entrada viola o contrato de interface.

    Cobre campo obrigatório ausente, tipo incorreto, identificador inválido ou
    duplicado, valor fora do domínio dos enums e datas temporalmente
    inconsistentes.
    """


@dataclass(frozen=True, slots=True)
class _Tarefa:
    """Representação interna e imutável de uma tarefa já validada.

    Attributes:
        id_tarefa: Identificador único da tarefa, maior que zero.
        data_criacao: Data e hora de criação, normalizada para UTC.
        data_inicio: Data e hora de início da execução em UTC, ou ``None``.
        data_conclusao: Data e hora de conclusão em UTC, ou ``None``.
        prazo: Data e hora limite para conclusão, em UTC.
        prioridade: Uma das prioridades de ``PRIORIDADES``.
        status: Um dos estados de ``STATUS_VALIDOS``.
    """

    id_tarefa: int
    data_criacao: datetime
    data_inicio: datetime | None
    data_conclusao: datetime | None
    prazo: datetime
    prioridade: str
    status: str


def _normalizar_utc(valor: datetime) -> datetime:
    """Converte um ``datetime`` para UTC.

    Valores sem fuso horário (naive) são assumidos como UTC, conforme a regra
    RN-06 da especificação.

    Args:
        valor: Data e hora a normalizar.

    Returns:
        O mesmo instante expresso em UTC.
    """
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _datetime_opcional(
    tarefa: dict[str, Any], campo: str, identificador: int
) -> datetime | None:
    """Extrai um campo de data opcional de uma tarefa bruta.

    Args:
        tarefa: Registro bruto da tarefa.
        campo: Nome do campo a extrair.
        identificador: Identificador da tarefa, usado na mensagem de erro.

    Returns:
        A data normalizada para UTC, ou ``None`` quando o campo não foi
        informado.

    Raises:
        TaskValidationError: Se o valor informado não for um ``datetime``.
    """
    valor = tarefa.get(campo)

    if valor is None:
        return None

    if not isinstance(valor, datetime):
        raise TaskValidationError(
            f"Tarefa {identificador}: {campo} inválido — "
            f"esperado datetime, recebido {type(valor).__name__}"
        )

    return _normalizar_utc(valor)


def _datetime_obrigatorio(
    tarefa: dict[str, Any], campo: str, identificador: int
) -> datetime:
    """Extrai um campo de data obrigatório de uma tarefa bruta.

    Args:
        tarefa: Registro bruto da tarefa.
        campo: Nome do campo a extrair.
        identificador: Identificador da tarefa, usado na mensagem de erro.

    Returns:
        A data normalizada para UTC.

    Raises:
        TaskValidationError: Se o campo estiver ausente ou não for um
            ``datetime``.
    """
    valor = _datetime_opcional(tarefa, campo, identificador)

    if valor is None:
        raise TaskValidationError(
            f"Tarefa {identificador}: {campo} inválido — campo obrigatório ausente"
        )

    return valor


def _validar_identificador(tarefa: dict[str, Any], vistos: set[int]) -> int:
    """Valida o identificador de uma tarefa.

    Args:
        tarefa: Registro bruto da tarefa.
        vistos: Identificadores já encontrados na mesma lista.

    Returns:
        O identificador validado.

    Raises:
        TaskValidationError: Se estiver ausente, não for inteiro, for menor ou
            igual a zero, ou já tiver aparecido na lista.
    """
    identificador = tarefa.get("id_tarefa")

    if identificador is None:
        raise TaskValidationError(
            "Tarefa sem identificador: id_tarefa inválido — campo obrigatório ausente"
        )

    if isinstance(identificador, bool) or not isinstance(identificador, int):
        raise TaskValidationError(
            f"Tarefa {identificador}: id_tarefa inválido — "
            f"esperado int, recebido {type(identificador).__name__}"
        )

    if identificador <= 0:
        raise TaskValidationError(
            f"Tarefa {identificador}: id_tarefa inválido — deve ser maior que zero"
        )

    if identificador in vistos:
        raise TaskValidationError(
            f"Tarefa {identificador}: id_tarefa inválido — identificador duplicado"
        )

    return identificador


def _validar_enum(
    tarefa: dict[str, Any], campo: str, dominio: tuple[str, ...], identificador: int
) -> str:
    """Valida um campo de enumeração de uma tarefa.

    Args:
        tarefa: Registro bruto da tarefa.
        campo: Nome do campo a validar.
        dominio: Valores aceitos para o campo.
        identificador: Identificador da tarefa, usado na mensagem de erro.

    Returns:
        O valor validado.

    Raises:
        TaskValidationError: Se o campo estiver ausente, não for ``str`` ou
            estiver fora do domínio.
    """
    valor = tarefa.get(campo)

    if valor is None:
        raise TaskValidationError(
            f"Tarefa {identificador}: {campo} inválido — campo obrigatório ausente"
        )

    if not isinstance(valor, str):
        raise TaskValidationError(
            f"Tarefa {identificador}: {campo} inválido — "
            f"esperado str, recebido {type(valor).__name__}"
        )

    if valor not in dominio:
        raise TaskValidationError(
            f"Tarefa {identificador}: {campo} inválido — "
            f"valor '{valor}' fora do domínio {list(dominio)}"
        )

    return valor


def _validar_coerencia_temporal(tarefa: _Tarefa) -> None:
    """Verifica a ordem cronológica das datas de uma tarefa.

    A ordem esperada é criação, início e conclusão. Qualquer inversão é
    inconsistência temporal.

    Args:
        tarefa: Tarefa já convertida e com datas normalizadas.

    Raises:
        TaskValidationError: Se alguma data estiver fora de ordem.
    """
    if tarefa.data_conclusao is not None and tarefa.data_conclusao < tarefa.data_criacao:
        raise TaskValidationError(
            f"Tarefa {tarefa.id_tarefa}: data_conclusao inválida — "
            "conclusão anterior à criação"
        )

    if tarefa.data_inicio is not None and tarefa.data_inicio < tarefa.data_criacao:
        raise TaskValidationError(
            f"Tarefa {tarefa.id_tarefa}: data_inicio inválida — "
            "início anterior à criação"
        )

    if (
        tarefa.data_inicio is not None
        and tarefa.data_conclusao is not None
        and tarefa.data_conclusao < tarefa.data_inicio
    ):
        raise TaskValidationError(
            f"Tarefa {tarefa.id_tarefa}: data_conclusao inválida — "
            "conclusão anterior ao início"
        )


def _validar_tarefa(tarefa: Any, vistos: set[int]) -> _Tarefa:
    """Valida um registro bruto e o converte na representação interna.

    Args:
        tarefa: Registro bruto, esperado como dicionário.
        vistos: Identificadores já encontrados na mesma lista.

    Returns:
        A tarefa validada e normalizada.

    Raises:
        TaskValidationError: Se o registro violar qualquer regra do contrato.
    """
    if not isinstance(tarefa, dict):
        raise TaskValidationError(
            f"Registro inválido — esperado dict, recebido {type(tarefa).__name__}"
        )

    identificador = _validar_identificador(tarefa, vistos)

    convertida = _Tarefa(
        id_tarefa=identificador,
        data_criacao=_datetime_obrigatorio(tarefa, "data_criacao", identificador),
        data_inicio=_datetime_opcional(tarefa, "data_inicio", identificador),
        data_conclusao=_datetime_opcional(tarefa, "data_conclusao", identificador),
        prazo=_datetime_obrigatorio(tarefa, "prazo", identificador),
        prioridade=_validar_enum(tarefa, "prioridade", PRIORIDADES, identificador),
        status=_validar_enum(tarefa, "status", STATUS_VALIDOS, identificador),
    )

    _validar_coerencia_temporal(convertida)
    return convertida


def _validar_entrada(tarefas: Any) -> list[_Tarefa]:
    """Valida a lista completa de tarefas recebida.

    Args:
        tarefas: Coleção bruta de tarefas.

    Returns:
        A lista de tarefas validadas, na ordem original.

    Raises:
        TaskValidationError: Se a entrada não for uma lista ou se qualquer
            registro violar o contrato.
    """
    if not isinstance(tarefas, list):
        raise TaskValidationError(
            f"Entrada inválida — esperado list, recebido {type(tarefas).__name__}"
        )

    vistos: set[int] = set()
    validadas: list[_Tarefa] = []

    for registro in tarefas:
        tarefa = _validar_tarefa(registro, vistos)
        vistos.add(tarefa.id_tarefa)
        validadas.append(tarefa)

    logger.debug("Entrada validada: %d tarefa(s)", len(validadas))
    return validadas


def _selecionar_concluidas(tarefas: list[_Tarefa]) -> list[tuple[_Tarefa, datetime]]:
    """Seleciona as tarefas que entram no cálculo de tempo e atraso.

    Uma tarefa entra na análise quando tem status ``concluida`` e data de
    conclusão informada, conforme a regra RN-01. A data de conclusão é
    devolvida junto da tarefa para dispensar verificações posteriores.

    Args:
        tarefas: Tarefas validadas do recorte analisado.

    Returns:
        Pares de tarefa e respectiva data de conclusão.
    """
    return [
        (tarefa, tarefa.data_conclusao)
        for tarefa in tarefas
        if tarefa.status == "concluida" and tarefa.data_conclusao is not None
    ]


def _tempo_conclusao_horas(data_criacao: datetime, data_conclusao: datetime) -> float:
    """Calcula o tempo de conclusão de uma tarefa, em horas.

    O tempo é medido da criação até a conclusão, conforme a regra RN-02 da
    especificação v1.1.

    Args:
        data_criacao: Data e hora de criação, em UTC.
        data_conclusao: Data e hora de conclusão, em UTC.

    Returns:
        O tempo decorrido em horas.
    """
    delta = data_conclusao - data_criacao
    return delta.total_seconds() / SEGUNDOS_POR_HORA


def _esta_atrasada(data_conclusao: datetime, prazo: datetime) -> bool:
    """Informa se a tarefa foi concluída após o prazo.

    Conclusão exatamente no prazo não é atraso, conforme a regra RN-03.

    Args:
        data_conclusao: Data e hora de conclusão, em UTC.
        prazo: Data e hora limite para conclusão, em UTC.

    Returns:
        ``True`` se a conclusão ocorreu depois do prazo.
    """
    return data_conclusao > prazo


def _media_segura(valores: list[float]) -> float:
    """Calcula a média de uma lista, devolvendo ``0.0`` quando ela é vazia.

    Implementa a prevenção de divisão por zero exigida pela regra RN-05.

    Args:
        valores: Valores a promediar.

    Returns:
        A média aritmética, ou ``0.0`` se não houver valores.
    """
    if not valores:
        return 0.0
    return sum(valores) / len(valores)


def _percentual_seguro(parte: int, total: int) -> float:
    """Calcula um percentual, devolvendo ``0.0`` quando o total é zero.

    Implementa a prevenção de divisão por zero exigida pela regra RN-05.

    Args:
        parte: Numerador da razão.
        total: Denominador da razão.

    Returns:
        O percentual correspondente, ou ``0.0`` se o total for zero.
    """
    if total == 0:
        return 0.0
    return (parte / total) * 100


def _calcular_indicadores(tarefas: list[_Tarefa]) -> dict[str, Any]:
    """Calcula o bloco de métricas para um conjunto de tarefas.

    Args:
        tarefas: Tarefas validadas que compõem o recorte analisado.

    Returns:
        Dicionário com os totais, o tempo médio de conclusão em horas e a taxa
        de atraso percentual, todos arredondados conforme a regra RN-07.
    """
    concluidas = _selecionar_concluidas(tarefas)
    pendentes = [t for t in tarefas if t.status == "pendente"]

    tempos = [
        _tempo_conclusao_horas(tarefa.data_criacao, conclusao)
        for tarefa, conclusao in concluidas
    ]
    atrasadas = sum(
        1 for tarefa, conclusao in concluidas if _esta_atrasada(conclusao, tarefa.prazo)
    )

    tempo_medio = _media_segura(tempos)
    taxa_atraso = _percentual_seguro(atrasadas, len(concluidas))

    return {
        "total_tarefas": len(tarefas),
        "total_concluidas": len(concluidas),
        "total_pendentes": len(pendentes),
        "tempo_medio_conclusao_horas": round(tempo_medio, CASAS_DECIMAIS),
        "taxa_atraso_percentual": round(taxa_atraso, CASAS_DECIMAIS),
    }


def analyze_tasks(tarefas: list[dict[str, Any]]) -> dict[str, Any]:
    """Analisa um conjunto de tarefas e devolve métricas de produtividade.

    Calcula totais, tempo médio de conclusão em horas e taxa de atraso
    percentual, no geral e agrupados por prioridade. Conjuntos sem tarefas
    concluídas produzem ``0.0`` nas médias e percentuais, sem disparar exceção.

    Args:
        tarefas: Lista de registros de tarefa. Cada registro deve conter
            ``id_tarefa`` (int maior que zero e único), ``data_criacao``
            (datetime), ``prazo`` (datetime), ``prioridade`` (``baixa``,
            ``media`` ou ``alta``) e ``status`` (``concluida``, ``pendente`` ou
            ``cancelada``). Os campos ``data_inicio`` e ``data_conclusao`` são
            opcionais. Datas sem fuso são interpretadas como UTC.

    Returns:
        Dicionário com as chaves ``total_tarefas``, ``total_concluidas``,
        ``total_pendentes``, ``tempo_medio_conclusao_horas``,
        ``taxa_atraso_percentual`` e ``indicadores_por_prioridade``. A última
        contém sempre as três prioridades, mesmo quando sem tarefas.

    Raises:
        TaskValidationError: Se a entrada não for uma lista, se algum registro
            tiver campo obrigatório ausente, tipo incorreto, identificador
            inválido ou duplicado, valor fora do domínio dos enums, ou datas
            temporalmente inconsistentes.

    Example:
        >>> from datetime import datetime
        >>> resultado = analyze_tasks([
        ...     {
        ...         "id_tarefa": 1,
        ...         "data_criacao": datetime(2026, 3, 1, 8, 0),
        ...         "data_inicio": datetime(2026, 3, 1, 8, 0),
        ...         "data_conclusao": datetime(2026, 3, 1, 10, 0),
        ...         "prazo": datetime(2026, 3, 1, 12, 0),
        ...         "prioridade": "alta",
        ...         "status": "concluida",
        ...     }
        ... ])
        >>> resultado["tempo_medio_conclusao_horas"]
        2.0
    """
    validadas = _validar_entrada(tarefas)

    resultado: dict[str, Any] = _calcular_indicadores(validadas)
    resultado["indicadores_por_prioridade"] = {
        prioridade: _calcular_indicadores(
            [t for t in validadas if t.prioridade == prioridade]
        )
        for prioridade in PRIORIDADES
    }

    logger.info(
        "Análise concluída: %d tarefa(s), %d concluída(s)",
        resultado["total_tarefas"],
        resultado["total_concluidas"],
    )
    return resultado
