# Quality Acceptance

Este documento define como decidir se um run esta bom o suficiente para uso real e como comparar variantes de `CRF`.

## 1. Criterios de aceite do pipeline

Um run esta aprovado quando:

1. `cuts.json` existe e todos os MP4s referenciados existem.
2. todos os cortes finais ficam entre `15s` e `60s`.
3. nao ha cortes com `end_sec <= start_sec`.
4. os arquivos reproduzem sem erro em player comum.
5. o corte comeca e termina em trechos de fala completos.
6. o `viral_score` respeita o quality floor esperado.
7. o bloco `encoding` do `cuts.json` registra o preset e o `CRF` usados.

## 2. Criterios de aceite visual

Ao revisar alguns clips no player:

- o rosto nao fica excessivamente blocado ou borrado
- textos pequenos continuam legiveis
- movimentos rapidos nao quebram em macroblocos evidentes
- a transicao do hook continua clara nos primeiros segundos
- o audio permanece limpo e sincronizado

Se qualquer um desses pontos cair de forma perceptivel, o `CRF` escolhido esta agressivo demais.

## 3. Workflow de benchmark de CRF

Escolha um trecho representativo com fala, movimento e elementos visuais importantes:

```bash
python3 ./.agents/skills/video-cutter/scripts/benchmark_encoding.py \
  ./test/videoCurtoParaTeste4min.mp4 \
  102 \
  133 \
  ./output/benchmark_crf \
  --preset ultrafast \
  --crfs 23,28,32
```

O script gera:

- `benchmark.json` com metricas estruturadas
- `benchmark.md` com tabela de comparacao
- um MP4 por variante de `CRF`

## 4. Como decidir o CRF

Regra pratica:

- comece em `CRF 23` como baseline atual
- teste `CRF 28` para uma opcao intermediaria
- teste `CRF 32` como limite agressivo

Escolha recomendada:

- fique no menor arquivo que ainda preserve qualidade visual aceitavel
- se `CRF 28` nao introduzir degradacao visivel, ele vira um candidato forte
- se `CRF 32` mostrar artefatos em rosto, texto ou movimento, descarte

## 5. Resultado esperado desta sprint

Depois desta sprint, a decisao sobre encoding deixa de ser subjetiva e passa a ter:

- configuracao explicita no run
- registro no metadata
- benchmark reproduzivel
- checklist de aceite visual
