# Testing Guide

Este projeto tem dois niveis de validacao:

- testes locais sem API para as etapas deterministicas
- smoke/manual testing para o pipeline completo

## 1. Baseline automatizada

Antes de gastar quota da API ou gerar novos clips, rode:

```bash
./.agents/skills/video-cutter/scripts/bootstrap_wsl.sh
bash -n ./.agents/skills/video-cutter/scripts/run.sh
python3 -m py_compile ./.agents/skills/video-cutter/scripts/*.py
python3 -m unittest discover -s tests -p "test_*.py"
```

O que isso cobre:

- normalizacao CRLF/LF no WSL
- permissao de execucao dos scripts `.sh`
- integridade sintatica do shell
- integridade sintatica dos scripts Python
- regras deterministicas de sanitizacao, validacao, buffer e metadata

## 1.1 Benchmark de encoding

Para comparar `CRF` em um trecho fixo:

```bash
python3 ./.agents/skills/video-cutter/scripts/benchmark_encoding.py \
  ./test/videoCurtoParaTeste4min.mp4 \
  102 \
  133 \
  ./output/benchmark_crf \
  --preset ultrafast \
  --crfs 23,28,32
```

Depois revise os arquivos gerados e use [QUALITY_ACCEPTANCE.md](./QUALITY_ACCEPTANCE.md) como checklist.

## 2. Smoke test do pipeline

Use o video curto para um run de ponta a ponta:

```bash
./.agents/skills/video-cutter/scripts/run.sh ./test/videoCurtoParaTeste4min.mp4 ./output/smoke aggressive
./.agents/skills/video-cutter/scripts/run.sh ./test/videoCurtoParaTeste4min.mp4 ./output/smoke_conservative conservative
```

Depois valide o output gerado:

```bash
python3 ./.agents/skills/video-cutter/scripts/validate_cuts.py ./output/smoke/YYYYMMDD_HHMM
python3 ./.agents/skills/video-cutter/scripts/validate_cuts.py ./output/smoke_conservative/YYYYMMDD_HHMM
```

## 3. Validacao estrutural manual

Confira se o diretorio de output contem:

- `cuts.json`
- clips MP4 no formato `cut_NN_INICIO-FIMs.mp4`

Exemplo:

```bash
ls -la ./output/YYYYMMDD_HHMM/
```

## 4. Validacao dos clips

### Duracao real

```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 ./output/YYYYMMDD_HHMM/cut_01_12-38s.mp4
```

A duracao deve ficar entre `15` e `60` segundos e bater com o `cuts.json` com tolerancia de aproximadamente `1s`.

### Integridade do arquivo

```bash
ffmpeg -v error -i ./output/YYYYMMDD_HHMM/cut_01_12-38s.mp4 -f null -
```

Se nao houver output, o clip esta estruturalmente valido.

## 5. Validacao de conteudo opcional

Esse modo usa API para conferir se a transcricao do corte parece coerente com o audio:

```bash
python3 ./.agents/skills/video-cutter/scripts/validate_cuts.py ./output/YYYYMMDD_HHMM --verify-content
```

Use apenas quando realmente precisar, porque isso consome requisicoes adicionais.

## 6. Criterios de aprovacao

Um run esta aprovado quando:

1. `cuts.json` existe e os MP4s referenciados existem
2. todos os cortes respeitam os limites do video original
3. todas as duracoes finais ficam entre `15s` e `60s`
4. nao ha sobreposicao invalida entre cortes
5. o nome dos arquivos bate com os timestamps do JSON
6. os clips reproduzem sem erro
7. o `viral_score` respeita o quality floor esperado

## 7. Troubleshooting

### `ffprobe nao encontrado`

```bash
sudo apt install -y ffmpeg
```

### `faster-whisper nao instalado`

```bash
python3 -m pip install --user --break-system-packages -r requirements.txt
```

### Script falha por CRLF ou permissao no WSL

```bash
./.agents/skills/video-cutter/scripts/bootstrap_wsl.sh
```

### Clips muito grandes

Agora isso pode ser comparado de forma reproduzivel com `benchmark_encoding.py`. O baseline atual continua sendo `preset ultrafast` com `CRF 23`.
