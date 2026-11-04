# ADON AI — Context Efficiency Core v1.0.1

**Correção Windows:** v1.0.1 fecha conexões SQLite após cada operação `with connect(...)`; veja `CHANGELOG.md`.

**Projeto:** arquitetura de referência + núcleo local executável para Session Handoff 3.0. **Status:** núcleo local operacional; o conector GitHub é opcional e fornecido pelo agente/host, não pelo pacote ADON. O pacote não substitui os módulos do Adon AI nem pressupõe acesso ao seu código.

## Incluído e implementado

- CLI Python 3.10+ sem pacotes Python externos, executa em Windows/macOS/Linux.
- SQLite como registro canônico por projeto para eventos, decisões, restrições versionadas, checkpoints e métricas.
- Handoff determinístico (`checkpoint-save` → `restore`) gerando `CHECKPOINT.md` com referência e hash de payload.
- Busca local lexical por projeto, exibição de eventos e regras obrigatórias recuperáveis.
- Referências a arquivos com SHA-256 opcional sobre bytes locais (sem copiar conteúdo).
- O comando `source-verify` recalcula o hash de um arquivo registrado; exibição e recuperação de checkpoints validam a integridade do payload.
- Outbox Graphiti offline opt-in; não envia dados nem finge integração ativa.
- Medição de tokens separando entrada não armazenada em cache, leitura do cache, gravação e saída.
- Benchmark A/B pareado que acompanha pass/fail de qualidade e custos **fornecidos**, sem inventar preços.
- Políticas determinísticas **consultivas** para continuar/compactar/checkpoint e roteamento por classe de tarefa.
- Skills copiáveis para Claude Code e Codex, com contratos e plano de expansão.
- Fluxo de trabalho GitHub orientado pela skill, usando conector nativo disponível para busca e leitura seletiva; o ADON não mantém índice nem envia o banco local.

## Ainda NÃO implementado

- Integração com servidores Graphiti, Esdras/MinerU, RAGFlow/PageIndex, CAG remoto ou APIs OpenAI/Anthropic.
- Servidor MCP ou cliente GitHub próprio dentro do pacote; o fluxo GitHub usa o conector fornecido pelo host ou um clone local.
- Captura automática de logs do Claude Code/Codex, dashboard gráfico, roteamento real de modelos ou compactação autônoma.
- Autorização multiusuário, criptografia de banco, API HTTP, autenticação, backup assinado ou validação jurídico-probatória de conteúdo.
- Garantias de economia de tokens. Os exemplos do ZIP são **sintéticos**.

## Preparação do ambiente (Windows / PowerShell)

1. Extraia o ZIP em uma pasta local, por exemplo `C:\Adon\adon-context-efficiency-v1`, e abra PowerShell nessa pasta.
2. Execute `py -3 -m adon_context --help`, depois `py -3 -m unittest discover -s tests -v`.
3. Para um ensaio sem alterar seus dados, defina um banco de teste e execute:

```powershell
py -3 -m adon_context --db .\teste.sqlite3 init --project adon-ai
py -3 -m adon_context --db .\teste.sqlite3 constraint-set --project adon-ai --key protecao-fontes --text "Preservar referencias originais" --source-ref "decision:001"
py -3 -m adon_context --db .\teste.sqlite3 checkpoint-save --file examples\checkpoint.json
py -3 -m adon_context --db .\teste.sqlite3 restore --project adon-ai --out .\CHECKPOINT.md
py -3 -m adon_context --db .\teste.sqlite3 source-verify --project adon-ai --id SOURCE_ID
py -3 -m adon_context benchmark --file examples\benchmark.synthetic.json
```

Python deve ser 3.10+. O executável `py -3` seleciona a instalação Python 3 padrão; se ela for antiga, use `py -3.12` (se instalado).

On macOS/Linux use `python3 -m adon_context ...`.

## Skills

To expose to Claude Code or Codex, copy the **entire package folder** into the destination skill folder (or preserve the package in a stable location and copy `SKILL.md` with a documented executable path):

- Claude Code: `%USERPROFILE%\.claude\skills\adon-context-efficiency\SKILL.md`
- Codex: `%USERPROFILE%\.agents\skills\adon-context-efficiency\SKILL.md`

Não duplique bancos SQLite entre clientes. As duas skills podem usar o **mesmo** banco local com permissões adequadas, IDs de projeto e backups. A descoberta varia por versão do agente; confirme-a na documentação instalada antes de depender da descoberta automática. No Windows, execute `py -3 -m adon_context` dentro da pasta da skill; não execute `adon_context\__main__.py` diretamente.

## Operational safety

The SQLite file contains possibly sensitive summaries and references. Restrict the directory to the user, enable full-disk encryption and avoid putting privileged case files in source descriptions. Local file paths and hashes are stored in the DB; the tool never uploads anything.

`sha256` values identify content, but a SHA alone is not proof of secure storage or a tamper-evident audit trail. The SQLite MVP is a local convenience store, not evidence vault.

`CHECKPOINT.md` is generated output. It can become stale if the Git tree, data sources or permissions changed; verify before using. No automatic cleanup, deletion or model invocations occur.

## Measurement

The JSON `usage.synthetic.json` and `benchmark.synthetic.json` illustrate the schema. `input_uncached`, `cache_read`, `cache_write` must be disjoint normalized counters. Unknown price is `null`. Report subscription cost separately from billed API amounts. A/B savings count cached tokens in totals, and a quality regression prevents an acceptable savings claim.

Detailed interfaces and gating criteria are in `references/`.
