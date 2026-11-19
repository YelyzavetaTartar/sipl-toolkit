# SIPL Language Toolkit

Інструментарій для навчальної мови програмування **SIPL** (*SImple Programming Language*) у межах курсового проєкту з дисципліни «Теорія програмування».

## Обраний набір завдань (10.5 балів, макс. оцінка 10.0)

- **CORE-01 (0.5):** Формальна специфікація SIPL (Lark/EBNF + лексика + ≥10 позитивних і ≥10 негативних тестів)
- **CORE-02 (1.5):** Парсер і типізоване AST із позиціями `SourceSpan` та діагностикою синтаксичних помилок
- **CORE-03 (2.0):** Інтерпретатор SIPL (стан, `:=`, `;`, `if`, `while`, `begin/end`, `skip`, ліміт кроків, ≥80% покриття)
- **CORE-04 (1.0):** Подієва модель виконання та trace (`BeforeStatement`, `AfterStatement`, зміна змінної, перевірка умови, завершення)
- **CORE-05 (1.0):** CLI (`parse`, `check`, `run`, `trace`) зі структурованим JSON-режимом та стабільними кодами завершення
- **VIS-01 (1.5):** Візуалізація дерева синтаксичного виводу (`text`, `json`, `dot`, `svg`) із прив'язкою до `SourceSpan`
- **SEM-01 (2.0):** Автоматична побудова семантичного терму програми в нотації курсу (`sem_P`, `sem_S`, `sem_A`, `sem_B`) + golden tests
- **REL-01 (0.5):** CI (GitHub Actions: lint, type-check, tests, build)
- **REL-02 (0.5):** GitHub Release + SemVer + `CHANGELOG.md`

## Встановлення (з чистого середовища)

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

pip install -e ".[dev]"
```

## Запуск тестів

```bash
pytest --cov=sipl --cov-report=term-missing
```