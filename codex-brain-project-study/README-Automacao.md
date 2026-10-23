# Automação do Codex Brain

Mantenha seu `auto_brain.json` existente. A configuração continua usando `vault`, `projects` (com `path` e `folder`), `refresh_every_days`, `timeout_seconds`, `max_file_size_mb` e `ignore_dirs`.

A tarefa existente do Windows continua válida se apontar para a mesma pasta. Este pacote não a reinstala nem corrige seu nome com acentos; isso não é necessário para executar os scripts novos.

## Funcionamento

A cada verificação, compara uma impressão digital dos arquivos com o estado anterior. Ignora pastas de dependências/build e nomes comuns de credenciais. A lista de exclusão não identifica todos os segredos possíveis; não coloque credenciais em código-fonte.

Estuda quando o perfil falta/está vazio, quando o perfil registrado veio de uma execução com erro, quando os arquivos mudaram, quando a revisão periódica venceu ou quando você usa `--force`. Na primeira rodada com perfil válido e recente, pode apenas estabelecer a referência dos arquivos e sincronizar.

O estudo recebe conhecimento anterior. Perfis diferentes têm backup local antes da substituição. A exportação cria cópias e diferenças no Obsidian depois do estudo, atualiza as notas gerenciadas e preserva texto fora dos blocos do índice e diário.

A cada rodada também confere o destino: perfil e índice apagados ou destino alterado provocam nova sincronização, sem necessidade de estudar novamente. Falhas de sincronização são tentadas novamente. Uma nota conflitante é preservada e deve ser resolvida pelo usuário.

## Comandos

```powershell
python -B auto_brain.py --once --dry-run
python -B auto_brain.py --once
python -B auto_brain.py --once --force
```

`--dry-run` não grava arquivos nem chama o Codex. A verificação real pode consumir uso se houver motivo para estudar. `--force` solicita estudo em todos os projetos configurados.

## Arquivos

- `.brain/auto/state.json`: estado e impressão digital.
- `.brain/auto/auto.log`: log das verificações reais.
- `.brain/projects/<chave>/profile.md`: perfil atual.
- `.brain/projects/<chave>/history/<data-id>/`: arquivo/registro anterior, preservados antes da troca.
- `Projetos/<pasta>/Perfil do Codex Brain.md`: perfil gerenciado no cofre.
- `Projetos/<pasta>/Histórico Codex Brain/`: snapshots e diferenças exportados.
- `Sistemas/`: índice, diário e propostas gerenciadas.

Código 0 indica ausência de falhas detectadas nessa verificação, não aprendizagem nova. Código 1 indica falha; 2, configuração inicial inválida; 3, execução ignorada por bloqueio ativo.

Veja **README-Atualizacao.md** para instalar, testar, interpretar falhas e conhecer os limites de recuperação e validação no Windows.
