# Roadmap

## Implementado no starter v3
- Perfil do projeto gerado por `study` com Codex em sandbox somente leitura.
- Perfil salvo no banco central e em arquivo Markdown dentro de `.brain/projects/`.
- Recuperação do perfil em `knowledge` e injeção do perfil correto em `run`.
- Memórias globais e memórias vinculadas a projeto.
- Trace JSONL e métricas básicas.
- Propostas sem promoção automática.

## Próximas etapas recomendadas
1. Implementar agentes especializados reais usando recursos multiagente nativos disponíveis na versão instalada do Codex.
2. Criar um conjunto de benchmarks por linguagem/framework para avaliar a qualidade dos perfis.
3. Capturar métricas de tokens/custo só quando suportadas pelos eventos reais da CLI.
4. Validar alterações de memória com evidências, histórico e reversão.
5. Criar teste diferencial antes/depois e medir regressões.
