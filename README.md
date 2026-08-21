# JARVIS — RANKBRUM ONE AI

Protótipo local-first de assistente de conhecimento da RankBrum.AI. O sistema indexa dados demo ou fontes locais autorizadas, oferece busca, briefing, planejamento e memória por texto, e apresenta o conhecimento em um grafo Canvas interativo.

O backend de voz ElevenLabs está no primeiro ciclo de TDD: os testes RED existem, mas transcrição e TTS ainda não estão implementados. Consulte [HANDOFF.md](HANDOFF.md) antes de continuar o desenvolvimento.

## Requisitos

- Python 3.11 ou superior.
- Node.js para executar os testes de runtime da interface.
- Git.

O runtime da aplicação usa somente a biblioteca padrão do Python. Não há `pip install`, `npm install`, build frontend, banco ou migrations.

## Configuração

O modo demo funciona sem credenciais. Para criar um arquivo local opcional no PowerShell:

```powershell
Copy-Item .env.example .env
```

Preencha apenas as variáveis necessárias. Se copiar o modelo, defina `JARVIS_DEMO` explicitamente: um valor vazio desativa o modo demo no código atual. `.env` é ignorado pelo Git. Nunca versionar chaves, tokens ou arquivos reais do usuário.

Para usar fontes locais em vez do demo:

1. Defina `JARVIS_DEMO` como desativado no ambiente local.
2. Cadastre somente raízes read-only autorizadas em `config/sources.json`.

O arquivo versionado de fontes vem vazio por segurança.

## Execução

Na raiz do repositório:

```powershell
python run.py --host 127.0.0.1 --port 8765
```

Abra [http://127.0.0.1:8765/](http://127.0.0.1:8765/).

O host aceito deve continuar em loopback (`127.0.0.1`, `localhost` ou `::1`). A aplicação não possui autenticação e não deve ser exposta na rede.

## Testes

Suíte completa:

```powershell
python -m unittest discover -s tests -v
```

No handoff atual, esse comando falha intencionalmente porque `agent.voice` e `MAX_AUDIO_BODY` são o próximo código a implementar.

Linha de base não bloqueada pelos imports RED de voz (não inclui `tests/test_api.py`, que atualmente importa esse contrato):

```powershell
python -m unittest -v tests.test_agent tests.test_bootstrap tests.test_data tests.test_memory tests.test_security tests.test_tools tests.test_ui_contract tests.test_ui_runtime tests.test_vault
```

Testes JavaScript:

```powershell
node --no-warnings tests/test_ui_runtime.mjs
node --no-warnings tests/test_graph_runtime.mjs
```

## Tecnologias e build

- Backend: Python e `ThreadingHTTPServer`.
- Frontend: HTML, CSS, JavaScript vanilla e Canvas 2D.
- Dados: JSON/Markdown e índice em memória.
- Testes: Python `unittest` e Node.js.
- Build: não existe etapa de build; os assets de `ui/` são servidos diretamente.
- Banco/autenticação/hospedagem: não implementados.

## Estrutura

- `agent/`: núcleo, API, segurança, ferramentas, índice e memória.
- `ui/`: interface textual, máquina visual e grafo.
- `data/`: fixture e gerador demo.
- `config/`: configurações, perfil e fontes autorizadas.
- `tests/`: testes Python e JavaScript.
- `docs/superpowers/`: especificação e plano originais.

## Documentação

- [HANDOFF.md](HANDOFF.md): estado oficial, arquitetura, APIs, problemas e ponto exato de continuidade.
- [TODO.md](TODO.md): fila priorizada.
- [Especificação aprovada](docs/superpowers/specs/2026-08-21-jarvis-mvp-design.md).
- [Plano de implementação](docs/superpowers/plans/2026-08-21-jarvis-mvp.md).

O GitHub, o código e `HANDOFF.md` são a fonte oficial da verdade.
