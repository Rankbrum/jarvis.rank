# Task 7 report — núcleo conversacional em modo limitado

## RED

Antes da implementação, o teste novo foi executado com o runtime Python
bundled:

```text
python.exe -m unittest tests.test_agent -v
```

Resultado esperado: `ModuleNotFoundError: No module named 'agent.agent'`.

## Implementação

- `FallbackRouter` reconhece pedidos explícitos em português para busca,
  planejamento, briefing e memória.
- Só uma ordem direta de memória (por exemplo, `lembre que ...`) define
  `confirmed=True`; conversa comum permanece em modo limitado e não grava nada.
- `JarvisAgent` mantém os dez últimos turnos, recupera o segundo item do último
  resultado quando solicitado e retorna uma resposta determinística sem modelo.
- `LLMProvider` é uma abstração opcional; quando configurado, recebe o histórico
  como mensagens e sua resposta falada é limitada a 240 caracteres.
- `agent/prompt.md` registra idioma, postura, classificação de conhecimento,
  obrigação de fontes e guardrails.

## Verificação

Runtime:

```text
C:\Users\renan\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
```

Focada:

```text
python.exe -m unittest tests.test_agent tests.test_tools -v
```

Resultado: `Ran 9 tests ... OK`.

Completa:

```text
python.exe -m unittest discover -v
```

Resultado: `Ran 28 tests ... OK`.

Também foi executado `git diff --check` sem erros de espaço em branco.

## Arquivos

- `agent/router.py`
- `agent/llm.py`
- `agent/agent.py`
- `agent/prompt.md`
- `tests/test_agent.py`
- `.superpowers/sdd/2026-08-21-jarvis-mvp/task-7-report.md`

## Commit

`feat: add limited-mode conversation engine`

## Concerns

O roteamento é propositalmente heurístico e local. Nenhuma integração externa ou
ação implícita foi adicionada; pedidos não reconhecidos permanecem no modo
limitado até que um provedor de LLM seja configurado.

## Fix Round 1

- A memória agora só é roteada por um comando positivo direto no início da
  mensagem. Formas negadas, ambíguas e sem fato permanecem como conversa e não
  recebem confirmação de gravação.
- Quando há `LLMProvider`, o conteúdo de `agent/prompt.md` é enviado como a
  primeira mensagem `system`; assim, idioma, fontes e guardrails passam a afetar
  a execução do provedor.
- Os novos testes de regressão preservam a construção de `MemoryStore` com
  `application_root` e o diretório exato `<application_root>/memory`.

Verificação focada:

```text
C:\Users\renan\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_agent tests.test_tools -v
```

Resultado: `Ran 10 tests ... OK`.

Verificação completa:

```text
C:\Users\renan\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover -v
```

Resultado: `Ran 29 tests ... OK`.

Também foram executados `git diff --check` e `git diff --cached --check`, sem
erros de espaço em branco.

Commit: `fix: harden memory routing and load prompt`
