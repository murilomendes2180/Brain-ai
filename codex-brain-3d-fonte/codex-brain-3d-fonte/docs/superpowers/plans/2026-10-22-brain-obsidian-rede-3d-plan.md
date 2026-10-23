# Codex Brain — Rede 3D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar um plugin local do Obsidian que mostre os perfis sincronizados do Brain e suas seções em uma rede 3D animada, com origem navegável e painel complementar.

**Architecture:** Um leitor do vault produz registros normalizados; um modelo puro cria pontos, relações e páginas; uma visualização Canvas projeta coordenadas 3D e mostra os detalhes. O plugin registra a visualização, acompanha mudanças e salva somente suas próprias preferências. Os scripts Python e o banco do Brain permanecem fora da implementação.

**Tech Stack:** JavaScript CommonJS com contratos JSDoc; Canvas 2D com projeção espacial 3D; API pública do Obsidian; Node.js 20+ para desenvolvimento, testes nativos `node:test` e empacotamento sem instalar dependências. Alvo declarado: Obsidian desktop 1.6.0+, a confirmar em execução real antes de declarar compatibilidade validada.

**Spec:** `docs/superpowers/specs/2026-10-22-brain-obsidian-rede-3d-design.md`, aprovada na conversa.

## Global Constraints

- “Exibir até 500 pontos por vez, contando perfis e seções.”
- “A aba Painel continuará como complemento.”
- “Padrão de origem: notas Markdown sob `Projetos` com os metadados da integração. A pasta pode ser configurada.”
- “Memórias manuais presentes apenas no SQLite ficarão fora desta primeira versão”.
- “A primeira versão não infere relações semânticas por palavras iguais, proximidade no espaço ou avaliação de IA.”
- “sem dependência de CDN, servidor ou WebGL”.
- “Não instalar dependências na pasta do Brain nem substituir scripts ou memórias para entregar o plugin.”
- “Textos e cores acompanham o tema do Obsidian, preservando contraste.”
- “não declarar validação no Windows sem executá-la.”
- Nome do plugin/pasta: `codex-brain-3d`; comando: `Abrir Codex Brain`; abas: `Rede 3D` e `Painel`; ação: `Abrir origem`.
- Nenhuma escrita nas notas, acesso ao SQLite, execução de shell ou requisição de rede pelo plugin. Preferências próprias via `Plugin.saveData`.

## Review Focus

1. Perfis com CRLF, emojis, acentos e títulos repetidos devem abrir a origem correta, sem misturar offsets e linhas — testes nas tarefas 1 e 3.
2. Mais de 500 perfis, além de projetos com muitas seções, devem continuar totalmente navegáveis sem exceder o limite — tarefa 1.
3. Cache atrasado, arquivo alterado durante leitura e resultados assíncronos fora de ordem devem manter o último mapa válido com estado explícito — tarefa 2.
4. Texto de nota com HTML ou nomes de projeto iguais deve aparecer como texto e manter identidades distintas por caminho — tarefas 1 e 3.
5. A visualização fechada, aba inativa ou plugin desativado não deve manter animações, temporizadores, observadores ou atualizações tardias — tarefas 2 a 4.

---

## Estrutura e contratos compartilhados

Arquivos novos, na raiz deste projeto isolado:

| Arquivo | Responsabilidade |
| --- | --- |
| `src/model.js` | Contratos JSDoc, seções, nós, relações e paginação |
| `src/indexer.js` | Leitura limitada do vault e coordenação de revisões |
| `src/scene.js` | Posições determinísticas e projeção 3D, sem DOM |
| `src/renderer.js` | Desenho Canvas, seleção espacial e ciclo de animação |
| `src/view.js` | `ItemView`, controles, detalhes, navegação e painel |
| `src/main.js` | Registro do plugin, eventos e preferências |
| `styles.css`, `manifest.json` | Aparência escopada e identificação do plugin |
| `scripts/build.js` | Geração determinística de `main.js` sem dependências |
| `scripts/package.py` | ZIP do plugin e ZIP do código-fonte com biblioteca padrão |
| `tests/*.test.js`, `tests/helpers/*` | Casos de modelo e fakes da API/DOM necessários aos testes |
| `README.md`, `VALIDACAO.md`, `package.json` | Instalação, resultados reais e comandos de desenvolvimento |

Contratos definidos em `src/model.js` e usados pelos demais módulos. Em `Heading`, `endOffset` é o fim da linha do título; em `GraphNode`, é o fim do trecho representado:

- `Heading = { title: string, level: number, startOffset: number, startLine: number, endOffset: number }`.
- `ProfileRecord = { path: string, project: string, sourcePath: string, syncedAt: string|null, mtime: number, text: string, headings: Heading[], resolved: {path:string,count:number}[], unresolved: {target:string,count:number}[] }`.
- `GraphNode = { id: string, kind: 'profile'|'section', label: string, project: string, profileId: string, path: string, startLine: number, startOffset: number, endOffset: number, text: string, syncedAt: string|null, mtime: number }`.
- `GraphEdge = { id: string, kind: 'contains'|'link', source: string, target: string, count: number }`.
- `Graph = { nodes: GraphNode[], edges: GraphEdge[], profiles: ProfileRecord[] }`.
- `GraphPage = { nodes: GraphNode[], edges: GraphEdge[], totalNodes: number, shownNodes: number, page: number, pageCount: number }`.
- `IndexState = { status: 'indexing'|'ready'|'stale'|'error', graph: Graph|null, message: string, revision: number }`.
- `Settings = { sourceFolder: string, motion: boolean }`, padrão `{sourceFolder:'Projetos',motion:true}`. Movimento reduzido prevalece até ativação explícita pelo usuário na sessão.

## Task 1: Modelo fiel às fontes e navegação do conjunto

**Files:** Create `src/model.js`, `tests/model.test.js`, `tests/fixtures/profiles.js`, `package.json`.

**Interfaces:** Consome `ProfileRecord[]`; produz `buildGraph(records): Graph` e `selectGraphPage(graph, {profileId: string|null, page: number}, limit=500): GraphPage`. Define os contratos acima. IDs usam caminho completo e offset/título codificados sem colisão.

- [ ] **Step 1: Escrever casos inicialmente falhos.** `two_profiles_have_only_real_sections` compara IDs, texto e duas relações `contains` com fixture de dois perfis/duas seções. `links_are_directed_and_resolved_only` exige uma relação A→B com `count=2`, nenhuma relação para pendência e preservação das pendências no registro. `crlf_unicode_duplicate_headings` exige IDs distintos e trechos/linhas corretos. `boilerplate_and_code_do_not_become_sections` usa headings vindos do cache sem incluir código/frontmatter e descarta seção vazia/aviso gerenciado. `path_is_identity` mantém separados dois projetos com o mesmo nome.
- [ ] **Step 2: Executar `node --test tests/model.test.js`.** Esperado: falha pela ausência do módulo/funções, documentada antes de implementar.
- [ ] **Step 3: Implementar `buildGraph` e `selectGraphPage`.** Usar limites de headings do cache e nível do título; seção termina no próximo título de nível igual ou menor. O corpo exibe seu trecho documental, mesmo que contenha subseções. Remover apenas o aviso padrão reconhecido. Não inventar seções nem usar correspondência de palavras para conexões.
- [ ] **Step 4: Acrescentar e executar `pagination_covers_every_node`.** Para 501 perfis sem seções, a união das páginas cobre 501 IDs, sem repetição; nenhuma página excede 500. Para um perfil com 1.001 seções, páginas de até 499 seções mantêm o perfil em todas e cobrem as 1.001 seções. Acima do limite global, a visão inicial pagina só perfis; a seleção de projeto pagina suas seções. Conexões só aparecem se ambos os pontos estiverem visíveis. Esperado: todos os testes passam.
- [ ] **Step 5: Commit.** `git add src/model.js tests/model.test.js tests/fixtures/profiles.js package.json`; `git commit -m "feat: model sourced Brain knowledge and graph pages"`.

## Task 2: Índice do vault com atualização consistente

**Files:** Create `src/indexer.js`, `tests/indexer.test.js`, `tests/helpers/fake-vault.js`.

**Interfaces:** Consome `buildGraph` da tarefa 1. Produz `readProfiles(app, sourceFolder): Promise<{records:ProfileRecord[],pending:boolean}>` e `createIndexController({read,onState,delayMs=150}): {refresh():Promise<void>,schedule():void,dispose():void}`. `onState` recebe `IndexState`; `read` chama `readProfiles`. Leitura com erro rejeita; cache incompleto retorna `pending:true`.

- [ ] **Step 1: Escrever testes falhos.** `source_boundary_and_ownership` inclui somente Markdown sob `Projetos/`, sem aceitar `Projetos-outro/`, exigindo frontmatter `gerenciado_por === 'sync_obsidian.py'` e `caminho_origem` textual não vazio; ignora o índice e notas manuais. `metadata_maps_to_records` verifica títulos/posições do cache, datas reais e links resolvidos. `null_cache_is_pending` não produz mapa vazio como resultado final.
- [ ] **Step 2: Executar `node --test tests/indexer.test.js`.** Esperado: falha pela ausência das funções.
- [ ] **Step 3: Implementar leitor e controlador.** Usar `getMarkdownFiles`, `getFileCache` e `cachedRead`; consultar frontmatter antes de ler o corpo. Capturar mtime antes/depois da leitura, validar offsets e títulos contra o texto e tratar divergência como pendente. Normalizar pastas relativas ao vault; rejeitar `..`, caminho absoluto e configuração inválida. Ler links do cache público, sem chamadas a arquivos externos. Preservar o último gráfico completo em estado `indexing` ou `stale`; nunca publicar um mapa parcial como completo.
- [ ] **Step 4: Testar concorrência e falhas.** `newest_revision_wins` resolve duas leituras em ordem inversa e exige somente o resultado novo; `read_error_preserves_graph` mantém o mapa e informa desatualização; `rename_delete_rebuild` remove IDs antigos; `dispose_drops_late_results` não notifica após descarte; `coalesces_events` exige uma leitura por rajada; `mtime_or_heading_mismatch_is_pending` mantém o índice anterior. Executar `node --test tests/model.test.js tests/indexer.test.js`; esperado: PASS.
- [ ] **Step 5: Commit.** Adicionar apenas arquivos desta tarefa; mensagem `feat: index synchronized profiles and reject stale reads`.

## Task 3: Rede 3D, origem navegável e painel

**Files:** Create `src/scene.js`, `src/renderer.js`, `src/view.js`, `styles.css`, `tests/scene.test.js`, `tests/view.test.js`, `tests/helpers/fake-dom.js`, `tests/helpers/fake-obsidian.js`.

**Interfaces:** Consome os contratos e páginas da tarefa 1 e `IndexState` da tarefa 2. Produz `layoutNodes(nodes): Map<string,[number,number,number]>`, `projectPoint(point,camera,size): {x:number,y:number,depth:number}`, `createRenderer(canvas,{onSelect,reducedMotion}): {setPage(page):void,setSelection(id:string|null):void,setPaused(value):void,setVisible(value):void,rotate(dx,dy):void,zoom(delta):void,dispose():void}` e `BrainView extends ItemView`. Construtor `BrainView(leaf, services)` com `{getState:()=>IndexState,subscribe:(listener)=>()=>void,getSettings:()=>Settings,readLatest:()=>Promise<{records:ProfileRecord[],pending:boolean}>}`. `subscribe` retorna o cancelamento da assinatura. Exporta `openOrigin(app,node,readLatest): Promise<{opened:boolean,message:string}>`; `readLatest` tem o mesmo retorno de `readProfiles` e é fornecido pelo plugin. Cache pendente impede navegação por posição até resolução, com aviso e opção de abrir só a nota.

- [ ] **Step 1: Escrever testes falhos.** `layout_is_deterministic_and_finite`, `perspective_rotates_in_depth`, `selection_shows_exact_source`, `html_is_displayed_as_text` e `dashboard_uses_only_observed_counts_dates`. O cenário de integração usa dois perfis reais de fixture; nunca os 28 exemplos da prévia.
- [ ] **Step 2: Executar `node --test tests/scene.test.js tests/view.test.js`.** Esperado: falha por ausência dos módulos.
- [ ] **Step 3: Implementar cena e renderizador.** Posicionar perfis por caminho ordenado; seções ao redor do perfil. Canvas com perspectiva, arraste, clique, botões de zoom e de rotação horizontal/vertical acessíveis ao teclado. Rótulos sem sobreposição priorizam perfis/seleção. Relações `contains` tracejadas e links contínuos, com legenda textual e direção disponível nos detalhes. Pulsos/rotação são identificados como efeito visual. Sem renderização contínua quando pausado, oculto ou sem mapa.
- [ ] **Step 4: Implementar `BrainView` e `openOrigin`.** Duas abas, lista acessível, seleção de projeto/paginação quando necessárias, detalhes de origem/pendências/links externos ao mapa, estados de indexação/erro/vazio e painel com valores do modelo. Usar `textContent`, nunca HTML de notas. Antes de abrir, reler a origem: se mtime/posição mudaram, localizar novamente no índice atualizado; não escolher arbitrariamente entre títulos repetidos. Usar folha de nota separada e `openFile` com estado de linha para trecho inequívoco; para links reais de notas, `openLinkText`. Se o trecho desapareceu, avisar e oferecer abrir o perfil inteiro; arquivo excluído não deve ser recriado.
- [ ] **Step 5: Executar casos de comportamento e descarte.** `duplicate_heading_navigation_uses_line`, `changed_origin_does_not_open_stale_offset`, `missing_origin_is_not_created`, `panel_hides_animation`, `pause_and_reduced_motion_stop_frames`, `keyboard_rotation_and_zoom`, `all_pages_remain_accessible`, `close_disconnects_observers`. Testar seleção, pausa e mudança de aba em DOM simulado; a simulação não conta como teste real no Obsidian. Executar `node --test tests/*.test.js`; esperado: PASS.
- [ ] **Step 6: Commit.** Adicionar os arquivos desta tarefa; mensagem `feat: render interactive Brain network with source navigation`.

## Task 4: Plugin carregável e pacote para Windows

**Files:** Create `src/main.js`, `manifest.json`, `scripts/build.js`, `scripts/package.py`, `README.md`, `VALIDACAO.md`, `tests/plugin.test.js`, `tests/build.test.js`; modify `package.json`.

**Interfaces:** Consome `BrainView`, `readProfiles` e `createIndexController`. Produz a classe padrão do plugin e pacote instalável `dist/codex-brain-3d/`. Build deixa `require('obsidian')` externo e reúne os módulos locais em funções CommonJS estáticas, sem `eval`, `new Function` ou importação remota.

- [ ] **Step 1: Escrever testes falhos.** `registers_command_view_settings`, `events_refresh_without_note_writes`, `unload_cleans_every_resource`, `invalid_settings_are_rejected`, `built_entry_loads_with_fake_obsidian` e `manifest_matches_package`. Fake do vault rejeita toda tentativa de escrita; fake do plugin permite `saveData` apenas das preferências.
- [ ] **Step 2: Executar `node --test tests/plugin.test.js tests/build.test.js`.** Esperado: FAIL antes da implementação.
- [ ] **Step 3: Implementar entrada e build.** Registrar tipo `codex-brain-3d`, comando `Abrir Codex Brain`, uma visualização reutilizável e configuração da pasta de origem/movimento. Inicializar em `onLayoutReady`; acompanhar vault `create`, `modify`, `rename`, `delete` e cache `changed`, `resolved`, com registro/descarte pelas APIs públicas. Manifest: `id:codex-brain-3d`, `name:Codex Brain 3D`, `version:0.1.0`, `minAppVersion:1.6.0`, `isDesktopOnly:true`. Evitar APIs posteriores ao piso declarado; `ItemView`, cache, navegação e eventos foram conferidos nas definições oficiais. Compilar com lista explícita dos módulos conhecidos e produzir saída determinística.
- [ ] **Step 4: Implementar empacotamento e instruções.** ZIP do plugin contém pasta `codex-brain-3d` com `main.js`, `manifest.json`, `styles.css`, `README.md` e `VALIDACAO.md`; ZIP do fonte inclui código, testes, scripts e documentos de projeto, sem dados do usuário. README orienta copiar para `<vault>/.obsidian/plugins/`, ativar o plugin local e usar o comando. Explica como sincronizar os perfis com o script existente, sem declarar que o Jarvis já está sincronizado. Documenta seções como trechos registrados, limite 500 e memórias SQLite ainda fora do mapa.
- [ ] **Step 5: Verificar entrega.** Executar `node --test tests/*.test.js`, `node scripts/build.js`, `node --check dist/codex-brain-3d/main.js`, `python3 scripts/package.py` e teste de integridade/leitura dos dois ZIPs. Comparar os arquivos empacotados com os gerados e registrar resultados em `VALIDACAO.md`. Testes do bundle executam a entrada com fake do Obsidian, sem instalar pacotes.
- [ ] **Step 6: Validação no aplicativo quando houver acesso.** Em vault descartável no Obsidian desktop, testar abertura, duas abas, origem duplicada, sincronização/rename/delete, tema claro/escuro, movimento reduzido, paginação e desativação. Registrar versão real do app/OS. Se este ambiente continuar sem Obsidian/Windows, marcar estes casos como **não executados** e compatibilidade 1.6.0 como **alvo não validado em runtime**; entregar o pacote com essa limitação explícita. Não apresentar mocks como validação no Windows.
- [ ] **Step 7: Commit e entrega.** Commit `feat: package local Obsidian Brain plugin`; salvar os dois ZIPs e apresentar links. A instalação no PC continua sendo uma etapa local do usuário/Codex local; não solicitar acesso remoto ou afirmar instalação concluída.

## Revisão do plano

Cobertura conferida: fontes e relações (tarefas 1–2), controles/painel/origem (3), eventos/escala/descarte (1–4), instalação e limites de validação (4). Não há mudança no esquema SQLite nem extração de conceitos por IA. A implementação só começa depois da revisão deste plano e da escolha do método de execução.

Recomendação de execução: direta nesta sessão. As quatro tarefas compartilham contratos pequenos e sequenciais; isso reduz transferências de contexto. Alternativa: agentes separados por tarefa, com revisão entre entregas. Nenhum agente foi iniciado para escrever este plano.
