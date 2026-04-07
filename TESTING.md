# Manual Testing Guide for Video Cutter Skill

Este guia explica como testar manualmente os resultados gerados pela skill video-cutter para validar a qualidade dos cortes.

## 📋 Pré-requisitos

Antes de iniciar os testes manuais, certifique-se de que:
1. A skill foi executada com sucesso: `./.agents/skills/video-cutter/scripts/run.sh ./video.mp4`
2. Existe um diretório de output em `./output/YYYYMMDD_HHMM/`
3. O diretório contém o arquivo `cuts.json` e os clips MP4

## 🔍 Etapas de Teste Manual

### 1. Verificação Estrutural Básica

Verifique se o diretório de output contém:
- `cuts.json` - arquivo de metadados principal
- Clips MP4 nomeados no padrão: `cut_NN_INICIO-FIMs.mp4`

```bash
ls -la ./output/YYYYMMDD_HHMM/
```

### 2. Validação do cuts.json

Abra o arquivo `cuts.json` e verifique:

#### Campos obrigatórios:
- `input_video`: nome do vídeo original
- `output_dir`: caminho do diretório de output
- `generated_at`: timestamp de geração
- `model`: modelo de IA usado para análise
- `mode`: agressivo ou conservative
- `cuts`: array de objetos de corte

#### Estrutura de cada corte:
```json
{
  "filename": "cut_01_12-38s.mp4",
  "path": "./output/20260407_1517/cut_01_12-38s.mp4",
  "start_sec": 12.5,
  "end_sec": 38.2,
  "duration": 25.7,
  "hook_type": "pattern_interrupt",
  "hook_power": 9,
  "retention_potential": 8,
  "shareability": 7,
  "viral_score": 8.1,
  "content": "Transcrição do segmento...",
  "reason": "Por que este corte funciona..."
}
```

### 3. Validação dos Clips MP4

Para cada clip MP4, verifique:

#### Nome do arquivo bate com timestamps:
- Formato esperado: `cut_NN_INICIO-FIMs.mp4`
- INICIO e FIM devem corresponder (aproximadamente) a `start_sec` e `end_sec` do JSON

#### Duração do clip:
Use o comando abaixo para verificar a duração real:
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 ./output/YYYYMMDD_HHMM/cut_01_12-38s.mp4
```

A duração deve estar entre 15-60 segundos e corresponder ao campo `duration` no JSON (±1 segundo devido ao buffer).

#### Arquivo não está corrompido:
```bash
ffmpeg -v error -i ./output/YYYYMMDD_HHMM/cut_01_12-38s.mp4 -f null -
```
Se não houver output, o arquivo está OK.

### 4. Verificação de Buffer Inteligente

Verifique se o buffer foi aplicado corretamente olhando para:
- Gaps entre cortes consecutivos (devem ser ≥ 0s após correção de sobreposição)
- Extensão de cortes para evitar cortes no meio de frases

### 5. Teste de Reprodução

Reproduza alguns clips para verificar qualidade audiovisual:
- O áudio está claro e sincronizado?
- O vídeo começa e termina em pontos de fala completa?
- Não há cortes abruptos no meio de palavras/frases?

### 6. Validação de Conteúdo (Opcional - consome API)

Para validar se o conteúdo transcrito corresponde ao áudio real:
```bash
python3 ./.agents/skills/video-cutter/scripts/validate_cuts.py ./output/YYYYMMDD_HHMM/ --verify-content
```

> ⚠️ Atenção: Este teste consome aproximadamente 1 requisição API por corte.

## 📊 Critérios de Aceitação

Um teste é considerado aprovado se:

1. **Estrutura**: cuts.json válido e clips MP4 presentes
2. **Timestamps**: Todos os cortes respeitam os limites do vídeo original
3. **Duração**: 15s ≤ duração ≤ 60s para todos os clips
4. **Sobreposição**: Nenhum corte sobrepõe outro (após aplicação do buffer)
5. **Buffer**: Gaps entre cortes são razoáveis (0-4s típico)
6. **Nomeclatura**: Nome dos arquivos bate com timestamps do JSON
7. **Reprodução**: Clips podem ser reproduzidos sem erros
8. **Qualidade**: viral_score ≥ 7.5 para todos os cortes (quality floor)

## 🐛 Troubleshooting Common Issues

### Problema: "ffprobe não encontrado"
**Solução:** `sudo apt install ffmpeg`

### Problema: Clips muito grandes
**Nota:** É esperado com preset ultrafast - trade-off entre velocidade/tamanho
Para reduzir tamanho, modifique CRF em helper.sh (valor maior = qualidade menor)

### Problema: Sobreposição entre cortes
**Verificar:** Se o buffer inteligente foi aplicado corretamente no passo 7
**Solução:** Pode indicar problema na ordenação ou correção de sobreposição

### Problema: Clips muito pequenos (<15s)
**Verificar:** Se o quality floor ou validação de duração está funcionando
**Solução:** Re-executar com análise mais rigorosa

## 📞 Próximos Passos

Após validar manualmente os resultados:
1. Anote quaisquer problemas encontrados
2. Sugira melhorias se necessário
3. Estamos prontos para passar para a próxima etapa de desenvolvimento

---
*Este guia deve ser usado em conjunto com os scripts de validação automática existentes:*
- `./.agents/skills/video-cutter/scripts/validate_cuts.py` (validação estrutural)
- `./.agents/skills/video-cutter/scripts/helper.sh` (funções FFmpeg úteis)