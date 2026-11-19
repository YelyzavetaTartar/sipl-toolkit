# Документація CLI `sipl`

## Команди

- `sipl check <file> [--json]` — перевірка синтаксичної коректності SIPL-програми.
- `sipl parse <file> [--json]` — побудова типізованого AST з `SourceSpan`.
- `sipl run <file> [--var X=5 ...] [--state '{"X": 5}'] [--state-file state.json] [--max-steps 10000] [--json]` — виконання програми.
- `sipl trace <file> [--var X=5 ...] [--max-steps 10000] [--json]` — виконання програми з виводом повної подієвої траси.
- `sipl tree <file> [--format text|json|dot|svg] [-o out.svg] [--json]` — візуалізація дерева синтаксичного виводу.
- `sipl sem <file> [--style course|ascii] [--steps] [--json]` — побудова семантичного терму в нотації курсу.

## Коди завершення (Exit Codes)

| Код | Значення |
| :---: | :--- |
| `0` | Успішне виконання |
| `2` | Некоректні аргументи CLI (`argparse`) |
| `3` | Синтаксична помилка (`SiplSyntaxError`) |
| `4` | Помилка часу виконання (`UndefinedVariableError`, `StepLimitExceededError`) |
| `5` | Помилка вводу-виводу або формату вхідного стану (`--state`, відсутній файл) |

## Стабільна JSON-схема (`--json`)

Успіх (`stdout`):

```json
{
  "ok": true,
  "command": "run",
  "data": {}
}
```

Помилка (`stderr`):

```json
{
  "ok": false,
  "command": "run",
  "error": {
    "kind": "UndefinedVariableError",
    "message": "Undefined variable 'X'"
  }
}
```