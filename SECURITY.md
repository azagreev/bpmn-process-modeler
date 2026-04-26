# Security Policy / Политика безопасности

## Supported Versions

| Version | Supported |
|---|---|
| v2.0.x | Yes |
| v1.1.x | No (use v2.0) |
| v1.0.x | No |

## Поддерживаемые версии

| Версия | Поддержка |
|---|---|
| v2.0.x | Да |
| v1.1.x | Нет (используйте v2.0) |
| v1.0.x | Нет |

## Reporting a Vulnerability

Please do NOT open a public GitHub Issue for security vulnerabilities.

Contact: **Telegram @zagreev** or email a.zagreev@gmail.com.

Please include:
- Skill version or commit SHA.
- Minimum reproducible input.
- Expected vs actual behavior.
- Impact assessment (data leak / injection / denial of service).

Response SLA: acknowledgment within 5 business days, fix or mitigation plan within 30 days.

## Сообщение об уязвимости

Пожалуйста, НЕ открывайте публичный GitHub Issue для сообщений об уязвимостях безопасности.

Контакт: **Telegram @zagreev** или email `a.zagreev@gmail.com`.

Пожалуйста, укажите:
- Версию skill или SHA коммита.
- Минимальный воспроизводимый ввод.
- Ожидаемое и фактическое поведение.
- Оценку влияния (утечка данных / инъекция / отказ в обслуживании).

SLA по ответу: подтверждение в течение 5 рабочих дней, исправление или план смягчения в течение 30 дней.

## Threat Model

This skill processes user-provided process descriptions and generates BPMN/Excel files. Relevant threat classes:
- **Prompt injection** inside process descriptions.
- **MCP tampering** if Camunda MCP returns malicious documentation.
- **Excel formula injection** if process descriptions contain spreadsheet formulas.

## Модель угроз

Этот skill обрабатывает пользовательские описания процессов и генерирует файлы BPMN/Excel. Актуальные классы угроз:
- **Prompt injection** внутри описаний процессов.
- **MCP tampering**, если Camunda MCP возвращает вредоносную документацию.
- **Excel formula injection**, если в описаниях процессов содержатся формулы для таблиц.

## Out of Scope

- Claude model behavior itself (report to Anthropic).
- claude.ai sandbox security (report to Anthropic).

## Вне области ответственности

- Поведение самой модели Claude (сообщайте в Anthropic).
- Безопасность песочницы claude.ai (сообщайте в Anthropic).
