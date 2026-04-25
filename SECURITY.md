# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| v2.0.x | Yes |
| v1.1.x | No (use v2.0) |
| v1.0.x | No |

## Reporting a Vulnerability

Please do NOT open a public GitHub Issue for security vulnerabilities.

Contact: **Telegram @zagreev** or email a.zagreev@gmail.com.

Please include:
- Skill version or commit SHA.
- Minimum reproducible input.
- Expected vs actual behavior.
- Impact assessment (data leak / injection / denial of service).

Response SLA: acknowledgment within 5 business days, fix or mitigation plan within 30 days.

## Threat Model

This skill processes user-provided process descriptions and generates BPMN/Excel files. Relevant threat classes:
- **Prompt injection** inside process descriptions.
- **MCP tampering** if Camunda MCP returns malicious documentation.
- **Excel formula injection** if process descriptions contain spreadsheet formulas.

## Out of Scope

- Claude model behavior itself (report to Anthropic).
- claude.ai sandbox security (report to Anthropic).
