# Shortcutter

Pipeline local para transformar um video longo em cortes curtos prontos para publicacao. O projeto usa:

- `faster-whisper` para transcricao local
- Gemini Flash para selecionar os melhores cortes
- `ffmpeg` para renderizar os MP4s finais

O fluxo principal vive em [run.sh](./.agents/skills/video-cutter/scripts/run.sh).

## Requisitos

### Sistema

- Ubuntu/WSL com `bash`
- `python3`
- `ffmpeg` e `ffprobe`
- `bc`

Instalacao no Ubuntu:

```bash
sudo apt update
sudo apt install -y ffmpeg bc python3 python3-pip
```

### Python

Instale as dependencias com:

```bash
python3 -m pip install --user --break-system-packages -r requirements.txt
```

### Variaveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```bash
GEMINI_API_KEY=sua_chave_aqui
```

## Bootstrap no WSL

Se o checkout vier do Windows e os scripts perderem permissao de execucao ou LF, rode:

```bash
./.agents/skills/video-cutter/scripts/bootstrap_wsl.sh
```

Esse script:

- normaliza CRLF para LF nos scripts e docs principais
- reaplica permissao de execucao aos scripts `.sh`

## Como usar

### Override de encoding

O pipeline aceita override por variaveis de ambiente:

```bash
SHORTCUTTER_FFMPEG_PRESET=ultrafast \
SHORTCUTTER_FFMPEG_CRF=28 \
./.agents/skills/video-cutter/scripts/run.sh ./video.mp4
```

Defaults atuais:

- `SHORTCUTTER_FFMPEG_PRESET=ultrafast`
- `SHORTCUTTER_FFMPEG_CRF=23`
- `SHORTCUTTER_VIDEO_CODEC=libx264`
- `SHORTCUTTER_AUDIO_CODEC=aac`
- `SHORTCUTTER_PIX_FMT=yuv420p`

### Execucao padrao

```bash
./.agents/skills/video-cutter/scripts/run.sh ./video.mp4
```

### Com diretorio customizado

```bash
./.agents/skills/video-cutter/scripts/run.sh ./video.mp4 ./output/meu-teste
```

### Modo conservador

```bash
./.agents/skills/video-cutter/scripts/run.sh ./video.mp4 ./output/meu-teste conservative
```

## Validacao automatica

### Testes locais sem API

Esses testes cobrem as etapas deterministicas do pipeline sem chamar Gemini nem renderizar video:

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

### Checagens rapidas do shell e Python

```bash
bash -n ./.agents/skills/video-cutter/scripts/run.sh
python3 -m py_compile ./.agents/skills/video-cutter/scripts/*.py
```

### Validacao estrutural do output

Depois de um run completo:

```bash
python3 ./.agents/skills/video-cutter/scripts/validate_cuts.py ./output/YYYYMMDD_HHMM
```

### Benchmark de CRF

Para comparar tamanho e tempo entre variantes de `CRF` em um mesmo trecho:

```bash
python3 ./.agents/skills/video-cutter/scripts/benchmark_encoding.py \
  ./test/videoCurtoParaTeste4min.mp4 \
  102 \
  133 \
  ./output/benchmark_crf \
  --preset ultrafast \
  --crfs 23,28,32
```

Os criterios de aceite estao em [QUALITY_ACCEPTANCE.md](./QUALITY_ACCEPTANCE.md).

## Smoke test recomendado

Use o video curto incluido no ambiente para um teste de ponta a ponta:

```bash
./.agents/skills/video-cutter/scripts/run.sh ./test/videoCurtoParaTeste4min.mp4 ./output/smoke aggressive
./.agents/skills/video-cutter/scripts/run.sh ./test/videoCurtoParaTeste4min.mp4 ./output/smoke_conservative conservative
```

Depois valide o output:

```bash
python3 ./.agents/skills/video-cutter/scripts/validate_cuts.py ./output/smoke/YYYYMMDD_HHMM
```

## Estrutura relevante

```text
.
├── .agents/skills/video-cutter/
│   ├── SKILL.md
│   └── scripts/
│       ├── run.sh
│       ├── bootstrap_wsl.sh
│       ├── analyze_adaptive.py
│       ├── validate_cuts.py
│       └── ...
├── tests/
│   ├── fixtures/
│   └── test_*.py
├── CONTEXT.md
├── PLANO.md
├── QUALITY_ACCEPTANCE.md
├── TESTING.md
└── requirements.txt
```

## Troubleshooting

### `faster-whisper nao instalado`

```bash
python3 -m pip install --user --break-system-packages -r requirements.txt
```

### `ffprobe nao encontrado`

```bash
sudo apt install -y ffmpeg
```

### Scripts nao executam no WSL

```bash
./.agents/skills/video-cutter/scripts/bootstrap_wsl.sh
```

### Quota ou indisponibilidade do Gemini

O pipeline ja tenta fallback entre modelos Flash e retry para `503`. Se mesmo assim falhar, rode novamente depois de alguns minutos.
