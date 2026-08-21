# PROJECT HANDOFF

## 1. Visão geral

JARVIS é um protótipo local-first do produto RANKBRUM ONE AI. Ele organiza um cofre de conhecimento, responde por texto com ferramentas determinísticas e apresenta as informações em uma interface de comando com grafo interativo.

O problema atual é transformar arquivos e memórias dispersos em uma superfície única para busca, briefing, planejamento e registro explícito de memórias. O público inicial é Renan Brum e, no futuro, operadores e clientes da RankBrum.AI. O objetivo do MVP é validar a experiência local com dados demo, texto, grafo e voz, mantendo dados e credenciais sob controle do usuário.

Estado atual: texto, ferramentas, memória, API local e grafo estão implementados. A integração de voz foi iniciada somente pelos testes RED e ainda não funciona.

## 2. Stack utilizada

| Camada | Tecnologia atual |
| --- | --- |
| Frontend | HTML5, CSS3 e JavaScript vanilla; Canvas 2D para o grafo |
| Backend | Python 3, somente biblioteca padrão |
| Servidor/framework | `http.server.ThreadingHTTPServer`; não há framework web |
| Testes | `unittest` no Python e scripts `.mjs` executados pelo Node.js |
| Persistência | JSON demo, índice em memória e memórias Markdown locais |
| Banco de dados | Nenhum |
| ORM | Nenhum |
| Autenticação | Nenhuma; o limite atual é execução apenas em loopback com validação de Host/Origin |
| Hospedagem | Nenhuma configuração de deploy; aplicação local |
| Serviços externos | ElevenLabs planejado, mas ainda não implementado; abstração de LLM sem provedor concreto |
| Dependências de runtime | Nenhum pacote de terceiros |

## 3. Estrutura do projeto

```text
agent/                  núcleo Python: agente, roteamento, ferramentas, segurança, memória e API
config/                 configurações versionadas, perfil do usuário e fontes locais
data/                   gerador e fixture determinística do modo demo
docs/superpowers/       especificação aprovada e plano de implementação original
memory/                 destino de memórias Markdown geradas em runtime; conteúdo ignorado pelo Git
tests/                  testes Python, contratos de UI e testes de runtime JavaScript
ui/                     shell visual, reator de estado e grafo Canvas
run.py                  bootstrap e CLI do servidor local
.env.example            nomes das configurações de ambiente, sem valores
HANDOFF.md              fonte oficial do estado e da continuidade do projeto
TODO.md                 fila de trabalho atual
README.md               entrada rápida para desenvolvimento local
```

Arquivos centrais:

- `agent/main.py`: despachante HTTP, contratos JSON, arquivos estáticos e construção da aplicação.
- `agent/agent.py`: conversa, histórico limitado e chamada das ferramentas.
- `agent/data.py` e `agent/security.py`: modo demo, fontes reais e fronteiras de leitura.
- `agent/vault.py`: índice em memória, busca e grafo.
- `agent/tools.py`: `search_brain`, `brief_me`, `plan_day` e `remember`.
- `agent/memory.py`: gravação confirmada e exclusiva em `memory/`.
- `ui/app.js`, `ui/reactor.js` e `ui/graph.js`: aplicação textual, estados visuais e grafo.
- `docs/superpowers/specs/2026-08-21-jarvis-mvp-design.md`: desenho aprovado.
- `docs/superpowers/plans/2026-08-21-jarvis-mvp.md`: sequência original das tarefas 1 a 14. As checkboxes desse plano são estáticas; use o código, o Git e este handoff para medir progresso.

## 4. Funcionalidades concluídas

- [x] Bootstrap local seguro, carregamento opcional de `.env` e endpoint de status.
- [x] Modo demo determinístico com dados e relações sintéticas.
- [x] Gateway read-only para fontes `.md`, `.txt` e `.pdf`, com contenção de caminho, limite de tamanho e bloqueio de symlinks inseguros.
- [x] Memória explícita em Markdown, condicionada à confirmação do usuário e restrita à raiz `memory/`.
- [x] Indexação em memória, busca textual, wikilinks, relações e IDs de nó estáveis.
- [x] Ferramentas determinísticas `search_brain`, `brief_me`, `plan_day` e `remember`.
- [x] Motor de conversa em modo limitado, roteamento de intenção, histórico de dez turnos e follow-up simples.
- [x] API HTTP local com envelopes JSON de sucesso/erro e serviço de arquivos estáticos.
- [x] Interface textual responsiva com estados, ações rápidas, confirmação de memória e caminhos de recuperação.
- [x] Grafo Canvas interativo com zoom, arrasto, filtros, seleção, teclado, caminho entre nós e algoritmos testados com 1.000 nós/1.600 arestas.
- [x] Fronteira local: bind em loopback e validação de Host/Origin.
- [x] Os 37 testes Python não bloqueados pelos imports de voz e os dois testes de runtime JavaScript passam no estado deste handoff.

## 5. Funcionalidades parcialmente concluídas

- [~] Backend de voz ElevenLabs

  - Já existe: nomes de variáveis no status, botões visuais e testes RED para transporte, transcrição, TTS, validação e redação de segredos.
  - Falta: `agent/voice.py`, instanciação do cliente, `MAX_AUDIO_BODY`, rotas `/api/listen` e `/api/speak` e tratamento dos erros do provedor.
  - Arquivos: `tests/test_voice.py`, `tests/test_api.py`, `agent/main.py` e futuro `agent/voice.py`.

- [~] Integração com LLM

  - Já existe: protocolo em `agent/llm.py`, campo de status e suporte opcional no agente.
  - Falta: cliente/provedor concreto e conexão no `build_application`.
  - Arquivos: `agent/llm.py`, `agent/agent.py` e `agent/main.py`.

- [~] Fontes locais reais

  - Já existe: leitura segura e read-only baseada em `config/sources.json` quando `JARVIS_DEMO` está desativado.
  - Falta: cadastrar diretórios autorizados. O arquivo atual possui lista vazia.
  - Arquivos: `config/sources.json`, `agent/data.py` e `agent/security.py`.

- [~] Suporte a PDF

  - Já existe: descoberta segura e metadados do arquivo.
  - Falta: extração/indexação do texto interno.
  - Arquivos: `agent/data.py` e `agent/vault.py`.

## 6. Funcionalidades pendentes

### P0 — Crítico

- [ ] Revogar a chave ElevenLabs que foi compartilhada fora do repositório e configurar uma nova apenas no `.env` local.
- [ ] Concluir a Tarefa 11: cliente ElevenLabs server-side e rotas de voz, fazendo os testes RED atuais passarem sem usar uma chave real nos testes.
- [ ] Concluir a Tarefa 12: captura de microfone, detecção de silêncio, transcrição, reprodução de TTS e barge-in no navegador.
- [ ] Executar a verificação integral da Tarefa 13 depois que voz estiver implementada.

### P1 — Importante

- [ ] Conectar uma implementação real de LLM ou fazer o status representar explicitamente que só o endpoint foi configurado.
- [ ] Padronizar `HEAD` e `OPTIONS` com o contrato da API e adicionar os testes de método ausentes.
- [ ] Corrigir contraste dos textos de baixa ênfase e revisar acessibilidade visual.
- [ ] Tratar `pointerleave`/`lostpointercapture` no grafo e sincronizar filtros com a navegação semântica por teclado.
- [ ] Ampliar regressões para fixture demo versionada, metadados de memória e IDs estáveis calculados.

### P2 — Melhoria futura

- [ ] Extrair texto completo de PDFs com uma dependência avaliada e isolada.
- [ ] Avaliar autenticação e persistência em banco antes de qualquer exposição em rede ou multiusuário.
- [ ] Planejar, separadamente, integrações futuras registradas no perfil: GitHub, Gmail, Google Calendar, Google Drive, WhatsApp, Supabase, Vercel, n8n e planilhas.
- [ ] Definir pipeline de hospedagem somente quando os limites de autenticação, segredos e dados estiverem aprovados.

## 7. Última tarefa em desenvolvimento

A Tarefa 11, "Cliente ElevenLabs server-side", era a tarefa ativa. O desenvolvimento foi interrompido no primeiro ciclo de TDD, antes da implementação de produção.

O que foi feito:

- `tests/test_voice.py` foi criado com cinco testes para transcrição `scribe_v1`, TTS `eleven_multilingual_v2`, formato MP3, quoting do voice ID, payloads inválidos e redação de dados sensíveis.
- `tests/test_api.py` recebeu testes para degradação sem configuração, tipos de áudio, limite do corpo e validação de texto.
- Um literal do teste foi ajustado para codificar JSON UTF-8 corretamente; isso não implementa a funcionalidade.

O que falta:

1. Criar `agent/voice.py` com `ElevenLabsVoiceClient` e `ElevenLabsError`, usando transporte injetável e `urllib.request`.
2. Implementar multipart da transcrição, TTS e validação de respostas sem incluir segredo ou corpo não confiável em exceções/reprs.
3. Adicionar `MAX_AUDIO_BODY`, construir o cliente somente quando as duas variáveis ElevenLabs existirem e expor `/api/listen` e `/api/speak` em `agent/main.py`.
4. Preservar o comportamento degradado sem credencial e validar tipo/tamanho/schema antes de chamar o provedor.
5. Rodar toda a suíte. No handoff, ela falha intencionalmente com dois erros de importação: `MAX_AUDIO_BODY` e `agent.voice` ainda não existem.

Não use a chave compartilhada na conversa. Ela deve ser revogada, e uma chave nova deve permanecer apenas no `.env` local.

## 8. Banco de dados

Não existe banco de dados, ORM, schema, migration, seed de banco, permissão de banco ou RLS.

Os dados atuais são:

- `data/demo/jarvis_demo.json`: fixture sintética e determinística gerada por `data/generate_demo.py`.
- `config/sources.json`: lista de raízes locais read-only; vazia no estado atual.
- `VaultIndex`: índice reconstruído em memória durante o bootstrap.
- `memory/*.md`: memórias persistentes locais criadas somente com confirmação; ignoradas pelo Git.

Se um banco for introduzido, isso será uma mudança arquitetural nova e precisa de especificação de autenticação, tenancy, migrações e backup antes da implementação.

## 9. APIs

Todas as rotas atuais são locais e não usam autenticação. A proteção existente é o servidor em loopback com validação de Host/Origin.

| Método | Endpoint | Finalidade | Estado |
| --- | --- | --- | --- |
| GET | `/api/status` | Estado do modo demo, voz, modelo, documentos e assistente | Implementado |
| GET | `/api/graph` | Nós e arestas do cofre | Implementado |
| GET | `/api/node/{id}` | Detalhes e relações de um nó | Implementado |
| POST | `/api/chat` | Conversa textual e roteamento de ferramentas | Implementado |
| POST | `/api/search` | Busca no cofre | Implementado |
| POST | `/api/remember` | Gravação de memória com confirmação explícita | Implementado |
| POST | `/api/brief` | Briefing baseado no cofre | Implementado |
| POST | `/api/plan` | Plano curto de prioridades | Implementado |
| GET | `/` e assets de `ui/` | Interface web estática | Implementado |
| POST | `/api/listen` | Enviar áudio para transcrição ElevenLabs | Somente testes RED |
| POST | `/api/speak` | Gerar fala pela ElevenLabs | Somente testes RED |

Não existem endpoints de perfil, login, banco ou integrações externas. A ElevenLabs deve ser chamada somente pelo backend; a chave nunca deve chegar ao navegador.

## 10. Variáveis de ambiente

```env
JARVIS_DEMO=
JARVIS_LLM_ENDPOINT=
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
```

## 11. Como executar

Requisitos:

- Python 3.11 ou superior.
- Node.js somente para os testes de runtime JavaScript.
- Nenhuma instalação de pacote é necessária.

Na raiz do repositório:

```powershell
# Opcional: crie o arquivo local e defina JARVIS_DEMO explicitamente antes de iniciar.
Copy-Item .env.example .env

python run.py --host 127.0.0.1 --port 8765
```

Abra `http://127.0.0.1:8765/`. Sem `.env`, o sistema inicia em modo demo e a interface textual funciona; a voz permanece indisponível. Se o modelo for copiado, não deixe `JARVIS_DEMO` vazio: no código atual, vazio equivale a modo demo desativado.

Não existe etapa de build, migration ou seed de banco. A fixture demo já está versionada. Para regenerá-la de forma determinística:

```powershell
python data/generate_demo.py
```

## 12. Como testar

Suíte completa:

```powershell
python -m unittest discover -s tests -v
```

No ponto atual, o resultado esperado é falha por dois imports da Tarefa 11 ainda ausentes. Isso deve virar PASS quando o backend de voz for concluído.

Linha de base não bloqueada pelos imports de voz (ela não inclui `tests/test_api.py`, pois esse módulo agora importa o contrato RED da Tarefa 11):

```powershell
python -m unittest -v tests.test_agent tests.test_bootstrap tests.test_data tests.test_memory tests.test_security tests.test_tools tests.test_ui_contract tests.test_ui_runtime tests.test_vault
```

Runtime da interface e do grafo:

```powershell
node --no-warnings tests/test_ui_runtime.mjs
node --no-warnings tests/test_graph_runtime.mjs
```

Não há comandos de lint ou build configurados.

## 13. Problemas conhecidos

1. **Voz não implementada — P0.** Os botões existem, mas não capturam áudio nem reproduzem TTS. A suíte completa falha nos imports deliberadamente escritos antes da implementação. Arquivos: `tests/test_voice.py`, `tests/test_api.py`, `agent/main.py`, `ui/index.html`.
2. **Status de LLM pode sugerir conexão inexistente — P1.** `JARVIS_LLM_ENDPOINT` altera o campo de status, mas `build_application` não cria cliente concreto. Arquivos: `agent/main.py`, `agent/llm.py`.
3. **Contrato de métodos HTTP incompleto — P1.** `HEAD` e `OPTIONS` não têm comportamento JSON consistente com GET/erros. Arquivo: `agent/main.py`.
4. **Contraste visual baixo — P1.** Alguns textos `--dim`, guias de gesto e rótulos de status ficam abaixo do contraste desejável. Arquivo: `ui/styles.css`.
5. **Estados de ponteiro/teclado do grafo — P1.** Faltam caminhos explícitos para `pointerleave`/`lostpointercapture`; filtros visuais podem deixar a seleção semântica apontar para nó oculto; algumas interações acordam a física sem necessidade. Arquivo: `ui/graph.js`.
6. **Lacunas de regressão — P1.** O teste de dados regenera seu próprio dataset e não inspeciona exclusivamente a fixture versionada; testes de memória não cobrem todos os metadados e o callback de data é consultado duas vezes. Arquivos: `tests/test_data.py`, `tests/test_memory.py`, `agent/memory.py`.
7. **PDF somente por metadados — P2.** Conteúdo textual interno não é extraído. Arquivos: `agent/data.py`, `agent/vault.py`.
8. **Modo real sem fontes cadastradas — configuração.** `JARVIS_DEMO=0` produz um cofre vazio enquanto `config/sources.json` permanecer sem raízes autorizadas.

## 14. Decisões arquiteturais

- **Local-first e loopback-only:** não expor o servidor em LAN/Internet sem autenticação, autorização e uma nova revisão de segurança.
- **Biblioteca padrão no MVP:** backend sem dependências externas para bootstrap simples. Não trocar stack ou introduzir framework apenas por preferência.
- **Modo demo como padrão:** dados sintéticos e determinísticos evitam misturar arquivos reais em desenvolvimento/testes.
- **Fontes reais read-only:** raízes devem ser explicitamente autorizadas; caminhos resolvidos, tamanho, extensão e symlinks passam pela fronteira de segurança.
- **Memória exige confirmação:** o agente só escreve em `<raiz-do-app>/memory` e usa criação exclusiva para não sobrescrever conteúdo.
- **Índice efêmero:** o grafo é reconstruído no bootstrap a partir das fontes; não existe banco oculto.
- **Ferramentas determinísticas antes de LLM:** busca, brief, plano e memória devem continuar funcionando mesmo sem modelo externo.
- **Segredos somente no servidor:** valores ficam em `.env`/ambiente local e nunca em Git, JSON de resposta, UI, logs ou exceções.
- **Canvas para escala:** o grafo não deve ser refeito em centenas de elementos DOM sem medir impacto; os algoritmos atuais têm testes de estresse.
- **Documentos e Git como verdade:** este arquivo, o código e o histórico substituem suposições baseadas nas checkboxes não atualizadas do plano original.

## 15. Próximo passo recomendado

Continue exatamente pela Tarefa 11:

1. Leia `tests/test_voice.py`, os dois testes de voz em `tests/test_api.py` e a Tarefa 11 em `docs/superpowers/plans/2026-08-21-jarvis-mvp.md`.
2. Implemente o menor `agent/voice.py` que satisfaça os testes, com transporte injetável, validação estrita e erros sem dados do provedor.
3. Integre o cliente e as duas rotas em `agent/main.py`, mantendo funcionamento degradado quando a configuração estiver ausente.
4. Execute a suíte completa e preserve todos os testes anteriores.
5. Somente depois inicie a Tarefa 12 em `ui/voice.js`.

Não configure nem teste com a chave exposta anteriormente. Peça que ela seja revogada e use apenas sentinelas/fakes nos testes.
