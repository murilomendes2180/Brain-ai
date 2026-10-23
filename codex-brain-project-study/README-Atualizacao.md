# Atualização do Codex Brain — 22/10/2026

Este ZIP atualiza a instalação existente. Não exclua a pasta do projeto e não substitua sua pasta `.brain`.

## Como aplicar no Windows

1. Guarde seu RAR original como cópia de segurança.
2. Aguarde terminar qualquer estudo manual ou tarefa automática em andamento. No Agendador, confira que a tarefa Codex Brain não está como `Running`/`Em execução`; pause-a durante a cópia se necessário e reative-a depois.
3. Extraia este ZIP em uma pasta temporária. Copie **o conteúdo** dele para:

   `C:\Users\Murilo\Documents\codex-brain-project-study`

   Aceite substituir apenas os arquivos com o mesmo nome. `brain.py`, `auto_brain.py`, `sync_obsidian.py` e o novo **`brain_io.py`** devem ficar juntos. Copie também `tests` e a documentação.
4. Não apague nem troque `.brain`, `.venv`, `auto_brain.json`, `AGENTS.md` ou seu cofre Obsidian. Eles não estão incluídos neste pacote.
5. Abra PowerShell na pasta da instalação e valide:

```powershell
Set-Location "C:\Users\Murilo\Documents\codex-brain-project-study"
python -B -m unittest discover -s tests -v
python -B -m unittest test_auto_brain -v
python -B auto_brain.py --once --dry-run
```

A primeira suíte contém 22 testes; a segunda contém 3. Os testes usam dados temporários e respostas simuladas do Codex. Não estudam o Alethe nem chamam sua conta.

6. Execute a verificação real:

```powershell
python -B auto_brain.py --once
$LASTEXITCODE
```

Essa verificação pode chamar o Codex se detectar mudanças, perfil ausente/vazio, perfil anterior com erro ou revisão periódica vencida. Para testar deliberadamente um novo estudo, use `python -B auto_brain.py --once --force`; isso consome uso do Codex.

Se a tarefa agendada já apontava para essa mesma pasta, não é preciso reinstalá-la: ela executará os scripts atualizados na próxima rodada. Este pacote não modifica seu nome nem seus horários.

## O que foi corrigido

- `study`, com ou sem `--refresh`, recebe o perfil anterior inteiro e até 15 memórias recentes, priorizando as do projeto sobre as globais. O prompt pede consolidação, evidências e identificação do conteúdo herdado que não foi revalidado.
- `run` recebe o perfil inteiro, sem o corte antigo de 14.000 caracteres.
- O prompt é enviado ao CLI pela entrada padrão (`-`), evitando colocar toda a memória na linha de comando do Windows.
- Resposta vazia, falha do processo e eventos JSON sem mensagem final não substituem um perfil válido.
- Antes de substituir um perfil diferente, `brain.py` salva o arquivo anterior e o registro SQLite em `.brain/projects/<chave>/history/<data-id>/`. Isso vale também para estudos manuais.
- Se esse backup falhar, a substituição é interrompida. Se uma gravação SQLite falhar após trocar o arquivo, o código tenta restaurar o arquivo anterior. Escritas de texto usam arquivos temporários e substituição atômica.
- Resultados concorrentes não sobrescrevem silenciosamente uma revisão que mudou durante o estudo.
- Falhas de estudo, sincronização, histórico, estado ou diário retornam código não zero ao Windows.
- A sincronização verifica a nota e o índice no destino: nota apagada, índice apagado, pasta ou cofre alterado voltam a ser sincronizados mesmo com perfil inalterado.
- Uma nota de mesmo nome sem identificação da integração, ou pertencente a outro projeto, é preservada e gera erro. Nesse caso, escolha outra pasta em `projects[].folder` ou mova sua nota manual.
- O modo `--dry-run` não escreve log, estado, perfil ou notas.
- O bloqueio entre execuções usa o sistema operacional. O arquivo `running.lock` pode continuar existindo sem haver execução ativa; sua mera existência deixou de indicar bloqueio.

## Códigos de saída da automação

| Código | Significado |
| --- | --- |
| 0 | Verificação concluída sem falhas detectadas; pode não ter ocorrido estudo novo. |
| 1 | Uma ou mais etapas falharam. Consulte o log. |
| 2 | Configuração inicial inválida ou arquivos obrigatórios ausentes. |
| 3 | Outra execução automática mantém o bloqueio; esta rodada foi ignorada. |

Para consultar os últimos eventos:

```powershell
Get-Content ".brain\auto\auto.log" -Tail 50
```

## Limites e recuperação

O fluxo continua sendo Brain → Obsidian. Notas manuais do cofre não são importadas automaticamente; use `brain.py remember` para registrar uma informação que deve entrar nos próximos estudos.

A consolidação é produzida por IA e exige conferência das evidências. A seleção das memórias é por projeto e recência, não por busca semântica. O comando `learn` continua produzindo propostas sobre falhas recorrentes, sem aplicar mudanças automaticamente.

O histórico local é preservado antes da troca; as notas de histórico e diferenças do Obsidian são exportadas depois. Se essa exportação falhar, o código de saída indica erro e a versão anterior continua no histórico local. A nota de diferenças pode precisar ser reconstruída a partir dessas versões.

Arquivo e SQLite não formam uma transação única do sistema de arquivos. Uma interrupção abrupta de energia/processo entre as duas gravações pode deixá-los divergentes; há cópia anterior em `history` para recuperação. Não apague `.brain` para resolver um erro. Preserve uma cópia e confira o arquivo `profile.md` e o registro `record.json` correspondente antes de restaurar.

O pacote foi testado em Linux com temporários, SQLite e sincronização reais; chamadas ao modelo foram simuladas. O Codex instalado, a autenticação, o bloqueio nativo do Windows e o Agendador precisam ser validados no seu PC.

## Referências do CLI

- [Entrada padrão e opções de `codex exec`](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
- [Modo não interativo, sandbox e saída JSON](https://learn.chatgpt.com/docs/non-interactive-mode)

As opções foram consultadas em 22/10/2026. O pacote não desativa o sandbox, não adiciona permissões nem instala dependências.
