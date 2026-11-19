# Changelog

Усі значущі зміни цього проєкту документуються у цьому файлі. Формат відповідає [Keep a Changelog](https://keepachangelog.com/uk/1.1.0/) та [SemVer](https://semver.org/).

## [1.0.0] - 2026-04-18

### Added
- **CORE-01:** Формальна граматика SIPL (`sipl.lark`), документація БНФ (`grammar/SIPL_BNF.md`), приклади (`examples/*.sipl`) та тести граматики.
- **CORE-02:** Типізований AST (`src/sipl/ast.py`) із `SourceSpan`, парсер (`src/sipl/parser.py`) та діагностика синтаксичних помилок.
- **CORE-03:** Інтерпретатор SIPL (`src/sipl/interpreter/engine.py`) з контролем невизначених змінних та лімітом кроків `max_steps`.
- **CORE-04:** Подієва модель виконання та trace (`BeforeStatement`, `AfterStatement`, `VariableChanged`, `ConditionEvaluated`, `Terminated`).
- **CORE-05:** CLI `sipl` (`check`, `parse`, `run`, `trace`, `tree`, `sem`) зі стабільними кодами завершення, `--json` схемою, документацією (`docs/CLI.md`) та інтеграційними тестами.
- **VIS-01:** Експорт дерева синтаксичного виводу (`src/sipl/visualization/parse_tree.py`) у форматах `text`, `json`, `dot`, `svg` із прив’язкою вузлів до `SourceSpan`.
- **SEM-01:** Автоматична побудова семантичного терму (`src/sipl/semantics/terms.py`) у нотації курсу (`sem_P`, `sem_S`, `sem_A`, `sem_B`) та golden tests.
- **REL-01 / REL-02:** GitHub Actions CI, SemVer реліз `v1.0.0` та артефакти збірки.