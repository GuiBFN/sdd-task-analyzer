# sdd-task-analyzer

Módulo **TaskAnalyzer** — análise de tarefas e métricas de produtividade, construído sob o
paradigma **SDD (Spec-Driven Development)**: a especificação técnica é o contrato, o assistente de
IA é a executora e o desenvolvedor é o arquiteto e o homologador.

[![CI](https://github.com/GuiBFN/sdd-task-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/GuiBFN/sdd-task-analyzer/actions/workflows/ci.yml)
![testes](https://img.shields.io/badge/pytest-41%20passed-brightgreen)
![cobertura](https://img.shields.io/badge/cobertura-100%25-brightgreen)
![python](https://img.shields.io/badge/python-3.11%2B-blue)

---

## O que o módulo faz

Recebe uma lista de tarefas já executadas e devolve métricas agregadas, no geral e por prioridade:

| Métrica | Significado |
|---|---|
| `total_tarefas` | Total de tarefas no recorte |
| `total_concluidas` | Tarefas concluídas com data de conclusão |
| `total_pendentes` | Tarefas pendentes |
| `tempo_medio_conclusao_horas` | Tempo médio entre criação e conclusão |
| `taxa_atraso_percentual` | Percentual de concluídas entregues após o prazo |

O módulo é **puro**: não persiste dados, não acessa rede, não lê o relógio do sistema e não altera
a lista recebida. A mesma entrada produz sempre a mesma saída.

## O que o módulo não faz

Persistência, interface gráfica, API HTTP, CLI, integração externa, criação ou execução de tarefas,
e qualquer inferência estatística além das métricas acima. Essa fronteira é parte do contrato: o
que não está especificado é comportamento proibido.

---

## Estrutura

```
sdd-task-analyzer/
├── .github/
│   └── workflows/
│       └── ci.yml             # Integração contínua (GitHub Actions)
├── README.md                  # Este arquivo
├── CONTEXT_RULES.md           # Regras de governança fornecidas ao assistente de IA
├── Dockerfile                 # Imagem python:3.11-slim, pytest como CMD
├── docker-compose.yml         # Execução da suíte isolada em um comando
├── .dockerignore
├── .gitignore
├── pytest.ini                 # Configuração do pytest (pythonpath e testpaths)
├── requirements.txt           # Dependências autorizadas
├── specs/
│   ├── task_analyzer_spec.md  # Especificação SDD v1.1 — fonte da verdade
│   ├── requirements.yaml      # Contrato v1.1 em formato legível por máquina
│   └── system_design_document.pdf  # Contrato v1.1 em PDF
├── tests/
│   └── test_harness.py        # Test Harness (pytest)
└── src/
    └── task_analyzer.py       # Implementação gerada via IA e homologada
```

---

## Como executar os testes

Requer **Python 3.11 ou superior**.

```bash
git clone https://github.com/GuiBFN/sdd-task-analyzer.git
cd sdd-task-analyzer

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
pytest
```

Para rodar com relatório de cobertura:

```bash
pytest --cov=src --cov-report=term-missing
```

### Execução via Docker

Reprodutibilidade idêntica em qualquer máquina, sem depender do Python local.
Requer Docker com o plugin Compose.

```bash
# Build da imagem
docker build -t sdd-task-analyzer .

# Executa a suíte (pytest é o CMD da imagem)
docker run --rm sdd-task-analyzer

# Ou, com Compose
docker compose run --rm testes
```

### Integração contínua

O workflow `.github/workflows/ci.yml` roda em `ubuntu-latest` com Python 3.11 a cada push
ou pull request em `main` e `develop`, executando `pytest tests/test_harness.py -v`.

### Status do build

| Item | Resultado |
|---|---|
| Testes | 41 passed, 0 failed |
| Cobertura de `src/task_analyzer.py` | 100% |
| Bibliotecas externas em `src/` | nenhuma (apenas biblioteca padrão) |
| Versão mínima do Python | 3.11 |

---

## Uso

```python
from datetime import datetime
from src.task_analyzer import analyze_tasks, TaskValidationError

tarefas = [
    {
        "id_tarefa": 1,
        "data_criacao": datetime(2026, 3, 1, 8, 0),
        "data_inicio": datetime(2026, 3, 1, 8, 0),
        "data_conclusao": datetime(2026, 3, 1, 10, 0),
        "prazo": datetime(2026, 3, 1, 12, 0),
        "prioridade": "alta",
        "status": "concluida",
    }
]

try:
    resultado = analyze_tasks(tarefas)
except TaskValidationError as erro:
    print(f"Entrada inválida: {erro}")
else:
    print(resultado["tempo_medio_conclusao_horas"])  # 2.0
```

---

## Como este projeto é construído

A especificação vem antes do código.

1. **Especificar** — `specs/task_analyzer_spec.md` define entradas, saídas, regras e cenários.
2. **Governar** — `CONTEXT_RULES.md` define as regras que o assistente de IA deve seguir.
3. **Testar antes** — `tests/test_harness.py` é escrito a partir da especificação, não do código.
4. **Gerar** — o código em `src/` é produzido pelo assistente de IA com os dois arquivos acima como contexto.
5. **Homologar** — revisão crítica humana antes de qualquer commit.

### Plano de homologação humana

Todo código gerado por IA passa por estes cinco passos, nesta ordem:

1. Execução completa do Test Harness. Falhou, volta.
2. Revisão de conformidade com o contrato e com as CONTEXT_RULES.
3. Análise de qualidade: legibilidade, tratamento de erros, ausência de duplicação e de código morto.
4. Testes manuais complementares em casos de borda.
5. Commit somente após aprovação nos quatro passos anteriores.

Qualquer um destes reprova o incremento: teste falhando, biblioteca não autorizada (PR-01), teste
alterado para acomodar o código (PR-02), comportamento não especificado (PR-08), ausência de type
hints ou docstrings (DA-02, DA-04).

---

## Versionamento

| Item | Convenção |
|---|---|
| Fluxo | `main` + `feature/*` |
| Commits | Conventional Commits (`feat:`, `test:`, `docs:`, `fix:`, `refactor:`) |
| Pull Requests | Toda feature entra em `main` por PR documentado |
| Revisão | Obrigatória antes do merge, seguindo o plano de homologação |

Branches do projeto:

- `feature/sdd-specification` — especificação e regras de contexto
- `feature/test-harness` — suíte de testes
- `feature/task-analyzer-impl` — implementação
- `feature/devops-ci-docker` — CI, Docker e artefatos de especificação da Fase 3
- `develop` — branch de integração (gatilho do CI)

---

## Fases do projeto

| Fase | Escopo | Status |
|---|---|---|
| 1 | Especificação executável, cenários de aceite, CONTEXT_RULES, desenho do repositório | Concluída |
| 2 | Geração de código via IA, Test Harness, versionamento e Pull Requests | Concluída |
| 3 | CI/CD com GitHub Actions | Concluída |
| 3 | Containerização com Docker | Concluída |
| 3 | Relatório de governança e ética, pitch em vídeo | Próxima |

---

## Autoria e governança

Especificação, regras de contexto, revisão crítica e homologação: **Guilherme Borges Furtado Neves**.
Geração de código: assistente de IA, sob as regras de `CONTEXT_RULES.md`.

A decisão final e a responsabilidade técnica são humanas. Nenhum código entra neste repositório sem
testes verdes e leitura humana integral.
