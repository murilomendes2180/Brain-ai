# Codex Brain no Obsidian — rede de conhecimento 3D

Data: 22/10/2026. Estado: visual aprovado; integração proposta para revisão.

## Resultado esperado

Murilo quer explorar o conhecimento salvo pelo Codex Brain em uma rede parecida com o grafo de notas do print enviado: pontos luminosos, conexões discretas e agrupamentos por assunto/projeto. A rede terá profundidade, rotação e animação. A aba Painel continuará como complemento. O desenho anatômico de um cérebro não será necessário para esta versão.

A prévia aprovada demonstra a aparência e os controles; seus exemplos e relações ilustrativas não serão importados para a memória real.

## Base conferida

Na cópia de código compartilhada, `brain.py` guarda perfis completos e memórias em SQLite. `sync_obsidian.py` espelha cada perfil em `Projetos/<pasta>/Perfil do Codex Brain.md` e atualiza `Sistemas/Índice dos perfis do Codex Brain.md`. As notas geradas têm `gerenciado_por: sync_obsidian.py`, `caminho_origem` e `sincronizado_em`.

Não existe nesse código um catálogo estruturado de cada conceito aprendido. A sincronização atual também insere links para notas temáticas que podem não existir no vault. Esses links não comprovam que tais notas ou conhecimentos estejam presentes.

A sincronização do Jarvis no PC ainda não foi confirmada. O estudo foi relatado como concluído; isso não comprova a instalação ou a sincronização desta interface.

## Abordagem escolhida

Criar um plugin local do Obsidian, com uma visualização própria e duas abas: Rede 3D e Painel. Usar os perfis já sincronizados como fonte. Isso permite uma primeira integração sem alterar o banco, o comando de estudo ou o agendamento do Brain.

Alternativas consideradas: o grafo nativo oferece notas e links, mas não incorpora a experiência 3D aprovada; uma página externa exigiria uma ponte adicional para acompanhar o vault e abrir notas. O plugin mantém a navegação junto do conhecimento.

## O significado dos pontos

A rede distinguirá dois tipos de ponto:

- **Perfil:** uma nota gerada existente, identificada pelo caminho no vault e pelos metadados da integração.
- **Seção:** um título Markdown do perfil com conteúdo abaixo dele; representa um trecho registrado, não um conceito validado automaticamente.

O texto introdutório sem título permanece acessível no ponto do perfil. Títulos vazios não geram pontos. Código cercado por crases, frontmatter e o aviso padrão de sincronização não geram seções. Os limites das seções devem seguir os títulos reconhecidos pelo cache Markdown do Obsidian.

Cada ponto guardará tipo, título, projeto, caminho da nota, posição de origem no texto e, quando disponível, data de sincronização. Identificadores derivados do caminho e da posição/título distinguem títulos repetidos. Alterações de caminho ou estrutura provocam a reconstrução do índice; não há promessa de identidade permanente entre renomeações.

O detalhe dirá “registrado no perfil”, com origem e texto correspondente. A visualização não atribuirá confiança, certeza, porcentagem de aprendizado ou fato confirmado a um trecho só por estar salvo. Memórias manuais presentes apenas no SQLite ficarão fora desta primeira versão: sua inclusão exige exportação própria, que não existe no sincronizador atual.

## O significado das conexões

- **Contém:** liga um perfil às suas seções; é uma relação de organização, identificada como tal no detalhe.
- **Link de nota:** representa um link interno que o Obsidian resolveu entre perfis incluídos no mapa. Direção e quantidade vêm dos links reais.

A primeira versão não infere relações semânticas por palavras iguais, proximidade no espaço ou avaliação de IA. Links para notas inexistentes aparecem como pendências no detalhe do perfil, sem criar neurônios artificiais. Links resolvidos para notas fora do conjunto de perfis podem ser abertos pelo detalhe, mas não expandem automaticamente o mapa para todo o vault.

Agrupamento por projeto e posição no espaço são recursos de navegação; distância não mede semelhança ou qualidade do conhecimento. Cada tipo de relação terá descrição textual e estilo distinguível, sem depender apenas de cores.

## Uso dentro do Obsidian

Um comando “Abrir Codex Brain” abre a visualização. A rede oferece arrastar para girar, zoom, pausa e seleção por clique ou lista acessível. Selecionar revela a origem; o botão “Abrir origem” abre a nota e, quando possível, a seção na posição registrada. Se a origem mudou, o índice é atualizado; se não for mais possível localizar o trecho, o usuário pode abrir o perfil inteiro com aviso explícito.

A animação consiste em pulsos nas conexões e rotação suave, com pausa e respeito à preferência por movimento reduzido. Ela será identificada como efeito visual, sem indicar análise em execução. Ao trocar de aba ou fechar a visualização, o processamento de animação para.

A aba Painel apresenta somente valores disponíveis: perfis encontrados, seções indexadas, nomes dos projetos e datas de sincronização. Ausências aparecem como “não disponível”. O plugin não consegue determinar se há um estudo em andamento só observando as notas exportadas.

## Componentes e atualização

O leitor usa as APIs do vault e do cache de metadados. O modelo da rede fica separado da renderização, permitindo validar nós e relações sem abrir o Obsidian. A visualização usa `ItemView`, registrada pelo plugin, e navegação pela API pública do workspace.

O renderizador inicial usará coordenadas 3D projetadas em Canvas, como a prévia: rotação e perspectiva reais no cálculo espacial, sem dependência de CDN, servidor ou WebGL. O leiaute agrupa seções ao redor dos seus perfis com posições determinísticas. Não haverá promessa de simulação física ou desempenho em dezenas de milhares de pontos nesta versão.

Eventos de criação, alteração, renomeação, exclusão e resolução de metadados atualizam o índice com consolidação de eventos. Apenas a revisão mais recente pode substituir o mapa. Enquanto o cache estiver incompleto, a interface informa “indexando”; erro de leitura preserva o último mapa válido com aviso de desatualização, sem apresentar a falha como ausência de conhecimento.

Padrão de origem: notas Markdown sob `Projetos` com os metadados da integração. A pasta pode ser configurada. A leitura do conteúdo fica limitada aos perfis selecionados; o plugin não varre arquivos externos ao vault, não lê o SQLite diretamente e não executa comandos do sistema.

## Escala e acessibilidade

Exibir até 500 pontos por vez, contando perfis e seções. Se o conjunto ultrapassar o limite, começar pelos perfis e permitir selecionar um projeto; mostrar o total indexado e o total exibido. Um projeto que também exceda o limite terá paginação das seções em ordem textual, mantendo o ponto do perfil. A lista selecionável corresponde ao subconjunto exibido. Não ocultar truncamento.

Suprimir rótulos sobrepostos, priorizando seleção e perfis; o título completo continua disponível no detalhe e na lista. Disponibilizar rotação por controles de teclado, além do arraste, e zoom por botões. Os efeitos respeitam movimento reduzido. Textos e cores acompanham o tema do Obsidian, preservando contraste.

## Entrega e limites

Entregar código-fonte, `main.js`, `manifest.json`, `styles.css` e instruções para o Obsidian desktop no Windows. A versão mínima suportada deve ser definida no plano a partir das APIs efetivamente usadas e validada antes do pacote final. Não instalar dependências na pasta do Brain nem substituir scripts ou memórias para entregar o plugin.

O pacote será instalado em `<vault>/.obsidian/plugins/codex-brain-3d/`. A instalação e a ativação no PC serão etapas locais, pois este ambiente não tem acesso ao Windows de Murilo. O plugin pode salvar suas preferências em sua própria pasta; visualizar o mapa não reescreve notas, perfis ou histórico.

## Critérios de aceitação

1. Em um vault de teste com dois perfis, os pontos correspondem exatamente aos perfis e às seções existentes, sem importar dados da demonstração.
2. Selecionar uma seção permite abrir seu texto de origem; títulos iguais em arquivos diferentes permanecem distintos.
3. Relações de organização e links reais são distinguíveis. Links inexistentes não geram pontos.
4. Uma sincronização posterior atualiza o mapa sem reiniciar o plugin; renomeações e exclusões não deixam pontos fantasmas.
5. Falhas e ausência de perfis têm estados explícitos; as datas exibidas vêm dos metadados reais.
6. Pausa, zoom, rotação, teclado e as duas abas funcionam. Animação e observadores são descartados ao fechar/desativar o plugin.
7. O limite de pontos é informado e permite navegar pelo conjunto completo em partes.
8. Testes de modelo cobrem títulos repetidos, frontmatter, blocos de código, cache parcial e links não resolvidos. A validação no Obsidian desktop será registrada separadamente dos testes automatizados; não declarar validação no Windows sem executá-la.

## Referências técnicas

- Código compartilhado e revisado: `brain.py` e `sync_obsidian.py`.
- API oficial do Obsidian: https://raw.githubusercontent.com/obsidianmd/obsidian-api/master/obsidian.d.ts — `ItemView`, `Plugin.registerView`, `MetadataCache`, `Workspace.openLinkText`.
- Referência visual: print `imagem_2026-10-22_160638387.png` e prévia aprovada na conversa.

## Revisão

Aprovação solicitada para esta integração inicial: perfis e suas seções como fontes, relações documentais explícitas e plugin local com Rede 3D e Painel. Após a revisão deste documento, o próximo artefato é o plano de implementação.
