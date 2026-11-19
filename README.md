# SIPL Language Toolkit

[![CI](https://github.com/YelyzavetaTartar/sipl-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/YelyzavetaTartar/sipl-toolkit/actions/workflows/ci.yml)

Інструментарій для навчальної мови програмування **SIPL** (*SImple Programming Language*) у межах курсового проєкту з дисципліни «Теорія програмування».

## Обраний набір завдань (10.5 балів, підсумкова оцінка макс. 10.0)

- **CORE-01 (0.5):** Формальна специфікація SIPL (`sipl.lark`, БНФ курсу, ≥10 позитивних і ≥10 негативних тестів)
- **CORE-02 (1.5):** Парсер і типізований AST із позиціями `SourceSpan` та діагностикою синтаксичних помилок
- **CORE-03 (2.0):** Інтерпретатор SIPL (стан, `:=`, `;`, `if`, `while`, `begin/end`, `skip`, ліміт кроків, ≥80% покриття)
- **CORE-04 (1.0):** Подієва модель виконання та trace (`BeforeStatement`, `AfterStatement`, `VariableChanged`, `ConditionEvaluated`, `Terminated`)
- **CORE-05 (1.0):** CLI (`check`, `parse`, `run`, `trace`, `tree`, `sem`) зі структурованим JSON-режимом та стабільними кодами завершення
- **VIS-01 (1.5):** Візуалізація дерева синтаксичного виводу (`text`, `json`, `dot`, `svg`) із прив'язкою до `SourceSpan`
- **SEM-01 (2.0):** Автоматична побудова семантичного терму програми в нотації курсу (`sem_P`, `sem_S`, `sem_A`, `sem_B`) + golden tests
- **REL-01 (0.5):** CI (GitHub Actions: `ruff`, `mypy`, `pytest --cov`, `python -m build`)
- **REL-02 (0.5):** GitHub Release + SemVer (`v1.0.0`) + `CHANGELOG.md`

## Архітектура

```text
sipl-toolkit/
├── grammar/SIPL_BNF.md               # Специфікація БНФ та пріоритетів
├── src/sipl/
│   ├── grammar/sipl.lark             # Машинозчитувана граматика Lark
│   ├── ast.py                        # Типізовані AST-вузли + SourceSpan
│   ├── parser.py                     # Парсер + перетворення CST -> AST + діагностика
│   ├── interpreter/                  # Інтерпретатор і подієвий trace
│   ├── semantics/                    # Побудова семантичних термів курсу
│   ├── visualization/                # Експорт Parse Tree (text, json, dot, svg)
│   └── cli.py                        # CLI та стабільний JSON-інтерфейс
├── examples/                         # Приклади програм SIPL (power, gcd, factorial)
├── tests/                            # Модульні, golden та інтеграційні тести
└── docs/CLI.md                       # Документація команд та exit codes
```

## Встановлення (з чистого середовища)

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

pip install -e ".[dev]"
```

## Приклади запуску

```bash
# Перевірка синтаксису
sipl check examples/power.sipl

# Виконання програми
sipl run examples/power.sipl --var X=5 --var Y=2
sipl run examples/gcd.sipl --var M=8 --var N=16 --json

# Повна подієва траса виконання
sipl trace examples/power.sipl --var X=5 --var Y=2 --json

# Візуалізація дерева синтаксичного виводу
sipl tree examples/gcd.sipl --format text
sipl tree examples/gcd.sipl --format svg -o gcd_tree.svg

# Побудова семантичного терму в нотації курсу
sipl sem examples/gcd.sipl --steps
```

Детальніше про всі команди, формати JSON та коди завершення див. у [`docs/CLI.md`](docs/CLI.md).

## Тестування та перевірки якості

```bash
ruff check .
mypy src
pytest --cov=sipl --cov-report=term-missing
```