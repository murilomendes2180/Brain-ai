# Codex Brain 3D — plugin local do Obsidian

Versão inicial 0.1.0 para Obsidian desktop. Mostra uma rede com profundidade, rotação, conexões animadas e uma aba Painel. Cada ponto tem origem em um perfil sincronizado ou em uma seção desse perfil. Nenhum exemplo da demonstração é importado.

## Instalar no Windows

1. Extraia `codex-brain-3d-plugin.zip`.
2. Copie a pasta `codex-brain-3d` para a pasta de plugins do seu cofre. No caminho informado nesta conversa, o resultado deve ser:

```text
C:\Users\Murilo\Documents\Segundo-Cerebro-Obsidian\Segundo-Cerebro-Obsidian\.obsidian\plugins\codex-brain-3d\main.js
C:\Users\Murilo\Documents\Segundo-Cerebro-Obsidian\Segundo-Cerebro-Obsidian\.obsidian\plugins\codex-brain-3d\manifest.json
C:\Users\Murilo\Documents\Segundo-Cerebro-Obsidian\Segundo-Cerebro-Obsidian\.obsidian\plugins\codex-brain-3d\styles.css
```

3. Reabra o Obsidian. Em **Configurações → Plugins da comunidade**, ative **Codex Brain 3D**. Se estiver usando apenas plugins nativos, o modo restrito precisa estar desativado para carregar este plugin local.
4. Abra a paleta de comandos com `Ctrl+P` e execute **Codex Brain 3D: Abrir Codex Brain**.

Não precisa instalar Node, Python ou dependências para usar o plugin. A instalação não altera os scripts do Brain. Evite uma pasta extra duplicada: `plugins/codex-brain-3d/codex-brain-3d/` não é a estrutura correta.

## Levar os perfis para o mapa

O plugin lê, por padrão, os perfis em `Projetos`, identificados pelos metadados gerados por `sync_obsidian.py`. A instalação do plugin não executa estudos nem sincroniza projetos por conta própria.

Para sincronizar o perfil do Jarvis já estudado, use o sincronizador existente no seu PowerShell:

```powershell
cd "C:\Users\Murilo\Documents\codex-brain-project-study"
python sync_obsidian.py --project "C:\Users\Murilo\Documents\jarvis-main\jarvis-main" --vault "C:\Users\Murilo\Documents\Segundo-Cerebro-Obsidian\Segundo-Cerebro-Obsidian" --folder "Jarvis"
```

Isso depende de o perfil existir nesse caminho e de o processo ter permissão de gravação no cofre. A sincronização do Jarvis e a instalação deste plugin no seu PC ainda precisam ser verificadas localmente.

Se os perfis estiverem em outra pasta dentro do cofre, altere a pasta de origem nas configurações do plugin. Não use o caminho absoluto do Windows nessa opção: informe a pasta relativa ao cofre, como `Projetos`.

## Explorar

- Arraste a rede ou use os botões de direção para girar; `+` e `−` alteram o zoom.
- Clique em um ponto ou escolha um item na lista. **Abrir origem** abre a nota na linha correspondente, em outra aba.
- Se o trecho mudou e não puder ser localizado com segurança, use **Abrir perfil inteiro**.
- **Painel** mostra os projetos, a quantidade de seções e as datas disponíveis nas notas.
- **Pausar animação** para rotação e pulsos. A preferência do sistema por movimento reduzido é respeitada.
- São exibidos até 500 pontos. Em mapas maiores, use as páginas e a seleção de projeto para acessar todas as seções.

A animação é um efeito visual, não um indicador de processamento ou de aprendizado em tempo real. A posição dos pontos não mede semelhança entre assuntos. As cores ajudam a acompanhar os agrupamentos e são complementadas pelos tipos e pelos detalhes.

## O que a rede representa

**Perfil** é uma nota sincronizada existente. **Seção** é um título Markdown com conteúdo registrado abaixo dele. O conteúdo salvo pode conter afirmações, inferências ou perguntas; sua presença no mapa não comprova que tudo seja um fato confirmado.

Linhas tracejadas significam **contém**, ligando o perfil às suas seções. Linhas contínuas representam **links reais entre notas de perfil**; direção e quantidade aparecem nos detalhes. Links para notas fora do mapa podem ser abertos pelo detalhe. Links não resolvidos são listados como pendências e não criam pontos fictícios.

Esta versão lê os perfis já exportados. Memórias manuais que estejam apenas no SQLite do Brain não aparecem. Notas manuais do cofre também não são incluídas automaticamente. O plugin não infere relações semânticas nem treina um modelo de IA.

## Privacidade e funcionamento

O plugin não faz chamadas de rede, não executa comandos do sistema e não acessa arquivos externos ao cofre. A leitura de corpos de notas fica limitada aos perfis da pasta configurada. Preferências próprias são salvas pelo mecanismo de dados do plugin. Notas, perfis, histórico e banco do Brain não são reescritos pela visualização.

Se houver erro ou cache incompleto, a interface informa o estado e preserva o último mapa válido. Depois de uma sincronização, o índice acompanha os eventos do Obsidian e atualiza o mapa. Remover o plugin não remove suas notas.

## Desenvolver a partir do código-fonte

Requer Node.js 20+; os testes e o build usam somente recursos nativos. Para gerar os ZIPs, Python 3 com biblioteca padrão:

```text
npm test
node scripts/build.js
node --check dist/codex-brain-3d/main.js
python scripts/package.py
```

Não é necessário executar `npm install`. `src/` contém os módulos editáveis; `main.js` é gerado pelo build. Os testes usam fakes da API/DOM nas partes que dependem do Obsidian: isso não substitui o teste no aplicativo real.

O piso declarado no manifesto é Obsidian 1.6.0. A compatibilidade no aplicativo, a aparência final e os casos no Windows estão pendentes de validação local; consulte `VALIDACAO.md`.
