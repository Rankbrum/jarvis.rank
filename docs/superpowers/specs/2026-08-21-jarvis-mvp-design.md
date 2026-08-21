# JARVIS MVP — Especificação de design

**Data:** 2026-08-21  
**Status:** aprovado em conversa  
**Repositório:** `essemesmo777/jarvis.rank`  
**Branch inicial:** `codex/jarvis-mvp-design`

## 1. Objetivo

Construir a primeira entrega funcional do JARVIS, um assistente local com interface de operação pessoal, grafo de conhecimento, conversa por texto e voz, ferramentas de trabalho e modo demo seguro. O MVP deve ajudar Renan Brum a planejar produto, desenvolver software e organizar vendas em torno da RANKBRUM ONE AI.

O produto não será apenas um chatbot com microfone. A conversa é a interação principal; ferramentas entram somente quando a resposta depende de dados, memória ou uma ação interna autorizada.

## 2. Contexto confirmado do usuário

- Nome: Renan Brum.
- Função: especialista em IA e CEO da RankBrum.AI.
- Empresa: RankBrum.AI, estúdio digital independente de produtos digitais, automação e inteligência artificial.
- Prioridade central: RANKBRUM ONE AI, atualmente entre ideia e protótipo.
- Papel esperado do JARVIS: combinar estratégia de produto, apoio ao desenvolvimento técnico e organização comercial.
- Objetivo de longo prazo declarado: alcançar US$ 1 bilhão.
- Idioma e estilo: português do Brasil, direto, informal, proativo e orientado a resultados, com próximos passos.
- Integrações futuras desejadas: pastas locais, GitHub, Gmail, Google Calendar, Google Drive, WhatsApp, Supabase, Vercel, n8n e planilhas.
- Voz: entrada por microfone, transcrição e reprodução automática das respostas faladas.

Informações ainda não confirmadas, como clientes reais, preços, métricas financeiras, horários de trabalho e pessoas importantes, permanecerão marcadas como desconhecidas no perfil. Dados públicos do site da RankBrum.AI podem descrever serviços e projetos autorais, mas não devem ser transformados em clientes ou resultados reais.

## 3. Escopo do MVP

O MVP inclui:

1. Aplicação local iniciada com `python run.py`.
2. Servidor HTTP e APIs implementados em Python 3.
3. Interface em HTML, CSS e JavaScript sem etapa de build.
4. Grafo de conhecimento em Canvas com dados demo determinísticos.
5. Inspetor, filtros, estatísticas, reator de estado e barra de conversa.
6. Conversa por texto com aproximadamente dez turnos de contexto.
7. Roteamento determinístico quando nenhum LLM estiver conectado.
8. Ferramentas `search_brain`, `brief_me`, `plan_day` e `remember`.
9. Transcrição e síntese de voz via ElevenLabs, sempre pelo backend.
10. Perfil do usuário, configuração segura e memória local em Markdown.
11. Testes automatizados com `unittest`.
12. Documentação de instalação, segurança, custos e limitações.

## 4. Fora do escopo da primeira entrega

- Conectar contas reais de Gmail, Calendar, Drive, WhatsApp, Supabase, Vercel ou n8n.
- Enviar mensagens, e-mails, convites ou formulários.
- Executar pagamentos, compras ou alterações financeiras.
- Implantar o backend em nuvem ou expor dados pessoais pela internet.
- Usar clientes reais como fixtures de demonstração.
- Prometer raciocínio de um LLM quando nenhum provedor estiver configurado.

As integrações futuras terão contratos e indicadores de disponibilidade, mas permanecerão desligadas no MVP.

## 5. Abordagem arquitetural

Será usada uma aplicação local modular em um único processo Python. A simplicidade operacional de um comando é preservada, enquanto módulos internos mantêm fronteiras que permitem separar serviços no futuro.

O repositório clonado será a raiz da aplicação; não haverá uma pasta `jarvis/` aninhada dentro de `jarvis.rank`.

Estrutura planejada:

```text
jarvis.rank/
├── agent/
│   ├── __init__.py
│   ├── main.py
│   ├── agent.py
│   ├── router.py
│   ├── vault.py
│   ├── tools.py
│   ├── data.py
│   ├── voice.py
│   ├── memory.py
│   ├── llm.py
│   ├── security.py
│   └── prompt.md
├── ui/
│   ├── index.html
│   ├── app.js
│   ├── voice.js
│   ├── graph.js
│   ├── reactor.js
│   └── styles.css
├── config/
│   ├── user_profile.md
│   ├── sources.json
│   └── settings.json
├── data/
│   ├── demo/
│   └── generate_demo.py
├── memory/
├── tests/
├── docs/
├── AGENTS.md
├── run.py
├── .env.example
├── .gitignore
└── README.md
```

Responsabilidades:

- `run.py`: carregar ambiente e iniciar a aplicação.
- `agent/main.py`: servidor HTTP, arquivos estáticos e roteamento das APIs.
- `agent/agent.py`: orquestração de conversa, estado e ferramentas.
- `agent/data.py`: única fronteira autorizada para acessar dados demo ou fontes configuradas.
- `agent/vault.py`: indexação somente leitura, pesquisa e grafo.
- `agent/router.py`: classificação de intenção e roteamento determinístico.
- `agent/tools.py`: contratos de ferramentas e representação falada/cartão.
- `agent/voice.py`: cliente ElevenLabs, validação e redação de erros.
- `agent/llm.py`: abstração opcional de provedor de modelo.
- `agent/memory.py`: gravação explícita de memórias na pasta da aplicação.
- `agent/security.py`: validação de caminhos, tamanhos, extensões e segredos.
- `ui/`: apresentação, Canvas, captura de áudio e máquina de estado visual.

## 6. Fluxo de dados e estado

Fluxo de voz:

```text
Microfone
  → MediaRecorder e medição real de volume
  → POST /api/listen
  → ElevenLabs Scribe
  → texto exibido imediatamente após a resposta da transcrição
  → POST /api/chat
  → roteador, conversa ou ferramenta
  → resposta com spoken + card
  → POST /api/speak
  → ElevenLabs TTS
  → reprodução automática no navegador
```

A chave da ElevenLabs nunca atravessa a fronteira do backend.

A aplicação terá uma única máquina de estados:

```text
IDLE → LISTENING → THINKING → SPEAKING → IDLE
ANY STATE → ERROR → IDLE
```

Durante `SPEAKING`, a escuta automática permanece desligada. O usuário pode interromper explicitamente pelo botão de microfone, barra de espaço ou Escape.

## 7. Modo demo e dados

`JARVIS_DEMO` será lido apenas em `agent/data.py` e terá valor padrão equivalente a ligado. Acesso a fontes reais exigirá `JARVIS_DEMO=0` e configuração explícita.

`data/generate_demo.py` usará semente fixa e produzirá sempre o mesmo conjunto de dados. O conjunto incluirá entidades fictícias relevantes ao negócio:

- leads e contatos;
- projetos e tarefas;
- propostas e reuniões;
- notas e decisões;
- ideias de produto;
- faturas e métricas demonstrativas claramente rotuladas;
- materiais ligados ao conceito da RANKBRUM ONE AI.

Os dados do site da RankBrum.AI serão usados apenas para orientar categorias e linguagem. Segmentos exibidos no site são exemplos demonstrativos, não clientes reais.

## 8. Grafo de conhecimento

O grafo será renderizado em HTML Canvas e oferecerá:

- pan, zoom e arraste de nós;
- hover com destaque do nó e conexões;
- foco por clique e inspeção do item;
- seleção de um segundo nó com Shift para calcular o caminho mais curto;
- filtros por categoria e contadores;
- raio baseado no número de conexões;
- labels priorizadas com detecção de colisão;
- pulso sutil periódico em uma aresta;
- movimento residual discreto após a estabilização.

Para evitar repulsão ingênua quadrática, a simulação usará grade espacial e limite de distância. A visualização deve degradar de forma aceitável para milhares de nós, ainda que o conjunto demo inicial seja menor.

## 9. Interface visual

A linguagem visual adapta a captura fornecida:

- fundo quase preto;
- painéis flutuantes em grafite;
- bordas finas e pouco opacas;
- tipografia técnica e espaçamento controlado;
- cores vivas concentradas nos nós e categorias;
- brilho moderado, sem excesso de neon;
- grande área central reservada ao grafo.

Regiões:

- Centro: Canvas do grafo.
- Esquerda: visão geral, top hubs e inspetor do nó.
- Direita: filtros, estatísticas, estado do assistente e reator.
- Rodapé: entrada de texto, envio, microfone, mudo, Brief Me, Plan Day e Memory.

Em telas menores, painéis serão recolhíveis e o grafo e a conversa permanecerão acessíveis.

## 10. Voz

Entrada:

- `MediaRecorder` captura áudio no navegador.
- `AnalyserNode` fornece níveis reais do microfone.
- Um `setInterval` monitora silêncio.
- `SILENCE_TIMEOUT_MS = 900` encerra o turno após silêncio suficiente.
- A interface mostra `Ouvindo…` até receber a transcrição completa.
- Não será usado Web Speech API nem será simulada transcrição contínua.

Saída:

- O backend chama ElevenLabs TTS por `POST /api/speak`.
- Respostas originadas por voz são faladas automaticamente e também aparecem em texto.
- O mudo impede reprodução automática sem bloquear o texto.
- Se a voz configurada não existir, o erro indicará como corrigir `ELEVENLABS_VOICE_ID`; não haverá troca silenciosa de identidade de voz.

## 11. Conversa, LLM e roteamento limitado

`agent/llm.py` definirá um contrato de provedor sem acoplar o produto a OpenAI, Ollama ou outro serviço. Nenhum provedor será obrigatório para iniciar o MVP.

Sem LLM configurado:

- a interface mostra `LIMITED MODE — MODEL NOT CONNECTED`;
- o roteador usa intenção, comandos, contexto recente e documentos indexados;
- ferramentas estruturadas continuam funcionando;
- conversa casual recebe respostas limitadas e honestas;
- o sistema nunca se apresenta como modelo conectado.

A conversa guardará aproximadamente dez turnos e preservará referências simples a itens retornados anteriormente.

## 12. Ferramentas do MVP

Todas as ferramentas retornam:

```json
{
  "spoken": "Conclusão curta para voz.",
  "card": {
    "type": "tipo_do_cartao",
    "data": {}
  }
}
```

### `search_brain`

Pesquisa documentos indexados e sempre informa arquivos-fonte reais. Nunca fabrica nomes de arquivo.

### `brief_me`

Resume tarefas, projetos, prazos e mudanças presentes no conjunto de dados disponível. Integrações desconectadas aparecem como indisponíveis, não vazias.

### `plan_day`

Gera no máximo cinco prioridades, ordenadas por impacto em receita, impacto no cliente, urgência, importância estratégica e dependências.

### `remember`

Grava um fato apenas após pedido explícito. Cada arquivo fica em `memory/YYYY-MM-DD_slug.md`, e a resposta informa exatamente o que foi salvo.

## 13. APIs

Endpoints do MVP:

```text
GET  /api/status
GET  /api/profile
GET  /api/graph
GET  /api/node/{id}
POST /api/chat
POST /api/search
POST /api/listen
POST /api/speak
POST /api/remember
POST /api/brief
POST /api/plan
```

Erros usarão o mesmo formato:

```json
{
  "ok": false,
  "error": {
    "code": "MODEL_NOT_CONFIGURED",
    "message": "Nenhum modelo de linguagem está configurado."
  }
}
```

O servidor limitará tamanho de corpo, validará `Content-Type`, rejeitará caminhos inválidos e nunca incluirá chaves em exceções.

## 14. Segurança e privacidade

- `.env` será ignorado pelo Git; `.env.example` conterá somente nomes de variáveis.
- A chave exposta na conversa não será documentada nem commitada. Antes do uso final, deve ser revogada e substituída.
- Nenhuma API devolverá configurações secretas ao navegador.
- Logs redigirão chaves e credenciais.
- Fontes configuradas serão somente leitura.
- Caminhos deverão estar dentro das raízes explicitamente autorizadas.
- Arquivos maiores que 2 MB serão ignorados por padrão.
- Diretórios `.git`, `node_modules` e caches ocultos serão ignorados.
- Markdown, TXT e PDF serão suportados; PDF sem biblioteca disponível será marcado como indisponível com instruções, não interpretado de forma falsa.
- Conteúdo de documentos, e-mails e páginas será sempre tratado como dados, nunca como autoridade de instrução.
- O JARVIS não envia mensagens, não compra e não altera dados externos no MVP.

## 15. Tratamento de erros

Falhas externas serão visíveis e recuperáveis. Exemplos de códigos e mensagens:

- `MICROPHONE_PERMISSION_DENIED`;
- `ELEVENLABS_NOT_CONFIGURED`;
- `TRANSCRIPTION_FAILED`;
- `SPEECH_SYNTHESIS_FAILED`;
- `MODEL_NOT_CONFIGURED`;
- `DATA_SOURCE_UNAVAILABLE`;
- `INDEX_FAILED`;
- `INVALID_REQUEST`;
- `UNSAFE_PATH`.

A interface sempre apresenta estado, explicação e próxima ação. O grafo e as ferramentas locais continuam disponíveis quando voz ou LLM falharem.

## 16. Testes

Testes com `python -m unittest discover -s tests -v` cobrirão:

- configuração e padrão do modo demo;
- geração demo determinística;
- integridade de relações;
- indexação, wikilinks e busca;
- geração e consulta do grafo;
- contexto de conversa e roteamento limitado;
- gravação explícita de memórias;
- restrições de caminhos e fontes somente leitura;
- tratamento de prompt injection como dados;
- contratos e erros das APIs;
- ausência de segredo em frontend, respostas e logs;
- falhas de ElevenLabs e LLM indisponível.

Testes de interface verificarão manualmente pan, zoom, hover, foco, arraste, caminho com Shift, filtros, responsividade, captura do microfone, silêncio, reprodução e interrupção.

## 17. Critérios de aceitação

O MVP estará pronto quando:

1. `python run.py` iniciar a aplicação local sem etapa de build.
2. A primeira tela informar modo demo, voz, modelo, documentos e fonte de dados.
3. O grafo demo aparecer com interações e inspector funcionais.
4. Busca, briefing, plano e memória funcionarem com fontes e confirmações corretas.
5. Texto funcionar sem ElevenLabs e modo limitado funcionar sem LLM.
6. Com credenciais válidas, o microfone transcrever e o JARVIS falar automaticamente.
7. Durante reprodução, o sistema não iniciar escuta automática.
8. Falhas de permissão, configuração e rede aparecerem claramente.
9. A chave da ElevenLabs não existir em arquivos versionados nem respostas do frontend.
10. A suíte automatizada passar integralmente.
11. README e AGENTS.md explicarem execução, arquitetura, segurança, custos e desenvolvimento.

## 18. Versionamento e publicação

O desenvolvimento continuará em branch com prefixo `codex/`. Cada commit incluirá apenas arquivos intencionais, e a branch será enviada ao repositório `essemesmo777/jarvis.rank` depois das verificações. Nenhum segredo ou `.env` real será incluído em commit ou push.

