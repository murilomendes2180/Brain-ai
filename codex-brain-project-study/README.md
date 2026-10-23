# Codex Brain — memória de projetos e sincronização

Este pacote é uma atualização da instalação existente. Comece por **README-Atualizacao.md** para substituir os scripts preservando sua memória, configuração e cofre.

Requer Python 3.11+ e Codex CLI instalado e autenticado. Usa apenas a biblioteca padrão do Python. Os quatro módulos `brain.py`, `brain_io.py`, `auto_brain.py` e `sync_obsidian.py` precisam ficar juntos.

## Comandos

```powershell
python brain.py init
python brain.py study --project "D:\Projetos\ProjetoAlvo"
python brain.py study --project "D:\Projetos\ProjetoAlvo" --refresh
python brain.py knowledge --project "D:\Projetos\ProjetoAlvo"
python brain.py remember "decisao" "Descrição da decisão e sua evidência" --project "D:\Projetos\ProjetoAlvo"
python brain.py recall "decisao" --project "D:\Projetos\ProjetoAlvo"
python brain.py run "Explique o fluxo de autenticação, sem editar arquivos." --project "D:\Projetos\ProjetoAlvo"
python brain.py report
python brain.py learn
python brain.py proposals
```

`study` usa sandbox `read-only`, injeta conhecimento anterior e salva apenas uma resposta final não vazia de execução bem-sucedida. Antes de substituir um perfil diferente, preserva a versão anterior no histórico local. Isso ajuda a continuidade; não comprova que as novas conclusões estejam certas.

`run` injeta perfil e memórias e mantém o comportamento anterior de usar `workspace-write`: pode editar o projeto. Pedir somente leitura no texto não substitui o sandbox. Para um estudo tecnicamente solicitado como somente leitura, use `study`.

`recall` pesquisa a tabela de memórias; `knowledge` mostra o perfil. `learn` identifica falhas repetidas e registra propostas. Nenhum desses comandos treina o modelo nem altera automaticamente suas regras.

A memória fica em `.brain/brain.db`; perfis e cópias anteriores ficam em `.brain/projects/`. O caminho canônico identifica o projeto: mudar a pasta de um repositório cria outro identificador.

## Testes e automação

```powershell
python -B -m unittest discover -s tests -v
python -B -m unittest test_auto_brain -v
python -B auto_brain.py --once --dry-run
```

Veja **README-Automacao.md** e **README-Atualizacao.md** para os limites, códigos de saída e passos de atualização.
