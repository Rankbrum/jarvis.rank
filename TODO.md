# TODO

## EM ANDAMENTO

- [ ] Concluir a Tarefa 11, cliente ElevenLabs server-side.
  - [x] Escrever testes RED do cliente e das rotas.
  - [ ] Criar `agent/voice.py` com transporte injetável, STT e TTS.
  - [ ] Integrar `/api/listen` e `/api/speak` em `agent/main.py`.
  - [ ] Fazer os testes RED passarem sem credenciais reais.

## PRÓXIMAS TAREFAS

- [ ] Revogar a chave ElevenLabs compartilhada anteriormente e criar outra somente no `.env` local.
- [ ] Implementar a Tarefa 12: captura de microfone, silêncio, transcrição, TTS e barge-in no navegador.
- [ ] Executar a verificação integral e os guardrails da Tarefa 13.
- [ ] Padronizar `HEAD` e `OPTIONS` e ampliar os testes de métodos HTTP.
- [ ] Corrigir contraste baixo e os estados de ponteiro/teclado do grafo.
- [ ] Tornar o status de LLM fiel à existência de um cliente realmente conectado.

## FUTURO

- [ ] Extrair e indexar texto completo de PDFs.
- [ ] Avaliar autenticação e banco antes de uso remoto ou multiusuário.
- [ ] Especificar integrações futuras: GitHub, Gmail, Google Calendar, Google Drive, WhatsApp, Supabase, Vercel, n8n e planilhas.
- [ ] Definir hospedagem e CI/CD depois da revisão de segurança.

## CONCLUÍDO

- [x] Bootstrap local seguro e status.
- [x] Dataset demo determinístico e gateway de dados.
- [x] Limites de segurança para arquivos e fontes.
- [x] Memória explícita em Markdown.
- [x] Indexador, busca e grafo de conhecimento.
- [x] Ferramentas de busca, briefing, plano e memória.
- [x] Motor de conversa em modo limitado.
- [x] API HTTP local e arquivos estáticos.
- [x] Interface textual, reator visual e recuperação de erros.
- [x] Grafo Canvas interativo e escalável.
- [x] Documentação de handoff e modelo de ambiente sem segredos.
