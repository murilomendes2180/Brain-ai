# Brain AI

Um projeto experimental de memória persistente para trabalhar com repositórios usando o Codex, integrado ao Obsidian e acompanhado por uma visualização 3D navegável.

O Brain AI reúne um núcleo em Python que estuda projetos e mantém perfis e memórias locais e um plugin do Obsidian que transforma perfis sincronizados em uma rede 3D animada. A visualização permite explorar o conhecimento e abrir as notas de origem.

> O Brain AI não treina nem altera o modelo do Codex. Os perfis são gerados por sessões do Codex e devem ser revisados: podem conter fatos, inferências ou pontos não confirmados.

## Componentes

| Parte | Caminho | Função |
| --- | --- | --- |
| Núcleo do Brain | [codex-brain-project-study](./codex-brain-project-study/) | Estudar repositórios com o Codex, manter perfis e memórias locais e sincronizar conteúdo escolhido com um cofre do Obsidian. |
| Plugin 3D | [codex-brain-3d-fonte/codex-brain-3d-fonte](./codex-brain-3d-fonte/codex-brain-3d-fonte/) | Exibir perfis sincronizados como uma rede navegável, com seções e links reais entre notas. |

## Como funciona

1. O núcleo recebe o caminho de um repositório e solicita ao Codex um estudo. O comando study usa sandbox somente leitura no projeto-alvo; run usa workspace-write e pode alterar arquivos.
2. O Brain guarda perfis, memórias e registros na pasta local .brain/. Essa pasta pertence à instalação e não deve ser publicada.
3. O sincronizador exporta os perfis escolhidos para uma pasta do cofre Obsidian.
4. O plugin lê as notas de perfil configuradas no cofre e apresenta títulos, seções e links em 3D.

A animação é visual: não indica processamento nem aprendizado ao vivo. A posição dos nós não representa semelhança semântica. Consulte os READMEs dos componentes para instalação, comandos e limitações.

## Início rápido

### Núcleo

Requisitos declarados: Python 3.11+ e Codex CLI instalado e autenticado.

No PowerShell:

    cd codex-brain-project-study
    python brain.py init
    python brain.py study --project "C:/path/to/your/project"
    python sync_obsidian.py --project "C:/path/to/your/project" --vault "C:/path/to/your/ObsidianVault" --folder "Projetos"

O comando study lê o projeto-alvo e grava dados na instalação local do Brain. Revise permissões e resultados antes de sincronizar.

### Plugin do Obsidian

Veja o [README do plugin](./codex-brain-3d-fonte/codex-brain-3d-fonte/README.md) para instalação no Obsidian desktop, configuração da pasta de perfis e comandos. O manifesto declara versão mínima 1.6.0. A validação no Obsidian real ainda precisa ser feita localmente.

## Desenvolvimento e testes

O núcleo usa a biblioteca padrão do Python e inclui testes:

    cd codex-brain-project-study
    python -B -m unittest discover -s tests -v

O plugin requer Node.js 20+ para testes e build. Segundo seu README, não precisa de npm install:

    cd codex-brain-3d-fonte/codex-brain-3d-fonte
    npm test
    node scripts/build.js

Os testes do plugin simulam APIs do Obsidian/DOM; não substituem testes no aplicativo. Consulte [VALIDACAO.md](./codex-brain-3d-fonte/codex-brain-3d-fonte/VALIDACAO.md).

## Privacidade

Este repositório contém código e documentação, não um cofre pessoal. Não publique .brain/, bancos de dados, perfis privados, notas do Obsidian, logs, credenciais ou caminhos locais. Os dados gerados podem conter informações pessoais e conclusões não verificadas.

Uma revisão do histórico alcançável pela branch main não encontrou a pasta do cofre pessoal. Os commits antigos, porém, ainda fazem parte do histórico. Reescrever a branch os remove do histórico publicado, mas clones e forks podem continuar com cópias anteriores. Referências em cache do GitHub exigem tratamento separado.

## Estado e contribuições

O projeto está em desenvolvimento. Instalação, funcionamento visual, integração com o Obsidian e automação no Windows precisam ser validados nos ambientes correspondentes. Ao relatar problemas, inclua passos para reproduzir e remova dados pessoais dos logs. Não envie seu cofre, banco local, tokens ou credenciais.

## Licença

Este projeto está licenciado sob a [MIT License](./LICENSE).
