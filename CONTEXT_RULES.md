# CONTEXT_RULES.md — Governança de Contexto para Agentes de IA

> **Leia este arquivo integralmente antes de gerar qualquer linha de código.**
>
> Projeto: `sdd-task-analyzer` — módulo TaskAnalyzer.
> Fonte da verdade do comportamento: [`specs/task_analyzer_spec.md`](specs/task_analyzer_spec.md) (versão 1.1).
>
> Este arquivo define **como** o código deve ser escrito. A especificação define **o que** ele deve
> fazer. Em caso de conflito, a especificação prevalece e o conflito deve ser reportado ao humano
> em vez de resolvido por conta própria.

---

## 1. Diretrizes arquiteturais (obrigatórias)

| ID | Diretriz |
|---|---|
| DA-01 | Linguagem **Python 3.11+** como versão mínima obrigatória. |
| DA-02 | **Type hints** em 100% das funções, métodos, parâmetros e retornos. |
| DA-03 | Seguir **PEP 8** e as boas práticas de código limpo. |
| DA-04 | Docstrings no padrão **Google style** para módulo, classes, funções e parâmetros. |
| DA-05 | Funções pequenas, coesas e com um único propósito (**SRP**). |
| DA-06 | Tratamento de exceções **específico**, com mensagem que nomeia a tarefa, o campo e o motivo. |
| DA-07 | Logs estruturados com o módulo padrão `logging` — nunca `print`. |
| DA-08 | Nomes descritivos; termos do domínio em português (`taxa_atraso_percentual`). |
| DA-09 | Separar responsabilidades: validação, cálculo e composição da saída em funções distintas. |
| DA-10 | Módulo **puro e determinístico**: sem estado global, sem efeitos colaterais. |

## 2. Proibições explícitas

| ID | Proibição |
|---|---|
| PR-01 | **Não** usar bibliotecas externas. Apenas a biblioteca padrão em `src/`; `pytest` exclusivamente em `tests/`. |
| PR-02 | **Não** alterar, remover ou adaptar os cenários de teste. Se o código falha, corrige-se o código. |
| PR-03 | **Não** modificar a estrutura de pastas definida na especificação. |
| PR-04 | **Não** persistir dados em arquivos ou bancos. |
| PR-05 | **Não** alterar a assinatura das funções públicas sem nova versão da especificação. |
| PR-06 | **Não** gerar código sem os testes correspondentes. |
| PR-07 | **Não** inserir código duplicado, morto ou sem necessidade. |
| PR-08 | **Não** assumir comportamento não especificado. Na ausência de definição, **perguntar**. |
| PR-09 | **Não** acessar rede, sistema de arquivos, variáveis de ambiente ou relógio do sistema na lógica de cálculo. |
| PR-10 | **Não** usar `print`, `assert` como validação de produção, nem `except Exception: pass`. |

## 3. Regras de interação

| ID | Regra |
|---|---|
| RI-01 | Fornecer sempre o contexto completo antes da solicitação: este arquivo e a especificação. |
| RI-02 | Antes de gerar código, reformular o contrato com as próprias palavras e apontar ambiguidades. |
| RI-03 | Explicar escolhas de implementação quando houver mais de uma alternativa razoável. |
| RI-04 | Todo código gerado é lido integralmente por um humano antes de ser aceito. |
| RI-05 | Respostas que violem a seção 2 são rejeitadas e a rejeição é registrada. |
| RI-06 | Trabalhar em incrementos pequenos: uma função ou um cenário por solicitação, com teste. |
| RI-07 | Registrar toda alucinação detectada junto da regra que a preveniria. |

## 4. Resumo do contrato (referência rápida)

**Função pública:** `analyze_tasks(tarefas: list[dict[str, Any]]) -> dict[str, Any]`
**Exceção pública:** `TaskValidationError`

**Entradas** — `id_tarefa` (int > 0, único, não booleano), `data_criacao` (datetime, obrigatório),
`data_inicio` (datetime, opcional), `data_conclusao` (datetime, opcional), `prazo` (datetime,
obrigatório), `prioridade` (`baixa` | `media` | `alta`), `status` (`concluida` | `pendente` |
`cancelada`). Tudo em UTC.

**Saídas** — `total_tarefas`, `total_concluidas`, `total_pendentes`,
`tempo_medio_conclusao_horas`, `taxa_atraso_percentual`, `indicadores_por_prioridade`.

**Regras** — só concluída com data de conclusão entra no cálculo; tempo = conclusão menos criação,
em horas; atraso quando conclusão maior que prazo (igual ao prazo não é atraso); data fora de ordem
cronológica dispara `TaskValidationError`; sem concluídas, médias valem `0.0` e nenhuma exceção é
lançada; tudo em UTC; arredondamento de duas casas.

**Não existe campo `tipo`. Não invente.** As métricas são por prioridade e no geral.
