# Validação — Codex Brain 3D 0.1.0

Ambiente de desenvolvimento: Linux, Node.js 24.19.0. Nenhuma dependência instalada. O plugin é destinado ao Obsidian desktop; seu piso declarado 1.6.0 é um alvo ainda não validado em runtime.

## Executado

- Testes automatizados com `node --test tests/*.test.js`: 38 testes aprovados na primeira verificação completa.
- Modelo real exercitado: seções, texto CRLF/Unicode, títulos repetidos, relações direcionadas, links ausentes e paginação (501 perfis, 1.001 seções).
- Leitor/atualização: pasta e propriedade da nota, metadados, cache pendente, mtime divergente, erro de leitura, leituras fora de ordem, renomeação/exclusão e descarte.
- Interações em simulação de DOM/Canvas: seleção e origem, texto tratado como texto, rotação por botões, zoom, pausa, mudança de aba, observadores e páginas.
- Plugin com API simulada: registro, eventos, preferências e encerramento. Os fakes rejeitam escritas nas notas.
- Build determinístico e carregamento da classe do plugin com API simulada; manifesto conferido.

## Revisão final e correções

Uma revisão independente identificou cinco problemas importantes. Cada um recebeu teste de regressão que falhou antes da correção:

1. Metadados antigos após edição: agora o plugin invalida o índice do arquivo, exige os dados correspondentes do evento de cache e aguarda a resolução dos links; o mesmo controle é usado na abertura da origem. Renomeação/exclusão também foram exercitadas. Alterações de arquivos binários não bloqueiam o índice de notas.
2. Navegação pendente após fechar/trocar seleção: a abertura da origem confere o identificador da navegação imediatamente antes de abrir a aba.
3. Enquadramento de mapas grandes: os três eixos são normalizados antes da perspectiva; pontos atrás da câmera não são desenhados. Testado com 500 perfis e múltiplas rotações.
4. Painel estreito em janela larga: o leiaute passa a responder à largura da própria visualização, com teste de 400px em janela simulada de 1.400px.
5. Acúmulo de botões e eventos removidos: os eventos temporários são descartados a cada reconstrução de detalhe/painel; teste de 100 atualizações mantém os registros limitados.

**Resultado final:** 47 testes aprovados, zero falhas, em `npm test`. Build e checagem de sintaxe do pacote aprovados. Os dois ZIPs passaram no teste de integridade; os arquivos do ZIP do plugin foram comparados byte a byte com o build.

Não houve achados menores adiados. A primeira tentativa de revisão foi interrompida por indisponibilidade do modelo; outro revisor independente concluiu a avaliação. A revisão não substitui o teste no aplicativo real.

**Decisão de processo:** auxiliares da skill para registrar etapas e seu modelo de revisão não estavam disponíveis no provedor. Etapas, decisões e resultados foram acompanhados manualmente. O custo é menor automação desse registro; o produto e seus testes não dependem desses auxiliares.

## Não executado

- Instalação e ativação no Windows de Murilo.
- Carregamento no Obsidian real, inclusive na versão mínima 1.6.0.
- Inspeção visual em navegador real/Obsidian, temas claro/escuro, uso em painéis estreitos e desempenho com cofres grandes.
- Confirmação da sincronização atual de Jarvis ou de qualquer outro projeto no PC.

Nenhum dado privado da memória local do usuário foi incluído nos pacotes. Fixtures sintéticas existem somente nos testes do ZIP de código-fonte.
