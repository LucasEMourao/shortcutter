#!/usr/bin/env python3
"""
validate_cuts.py - Valida cuts.json contra os clips gerados.

Modo padrão (sem API): verifica estrutura, durações, arquivos, overlaps.
Modo --verify-content: usa Gemini API para verificar se o conteúdo transcrito
bate com o áudio real (consome ~1 requisição por corte).

Uso:
  python3 validate_cuts.py <pasta_output>
  python3 validate_cuts.py ./output/20260330_1913
  python3 validate_cuts.py ./output/20260330_1913 --verify-content
  python3 validate_cuts.py ./output/20260330_1913 --verify-content --api-key KEY
  python3 validate_cuts.py ./output/20260330_1913
"""

import json
import os
import sys
import re
import subprocess
from pathlib import Path


def get_clip_duration(filepath):
    """Obtém duração real do MP4 via ffprobe."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', filepath],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except Exception:
        return None


def get_clip_size(filepath):
    """Obtém tamanho do arquivo em bytes."""
    try:
        return os.path.getsize(filepath)
    except Exception:
        return None


def validate_cuts(output_dir):
    """Valida todos os cortes em um diretório de output."""
    output_path = Path(output_dir)
    cuts_file = output_path / 'cuts.json'

    if not cuts_file.exists():
        print(f"❌ cuts.json não encontrado em {output_dir}")
        return False

    with open(cuts_file) as f:
        data = json.load(f)

    cuts = data.get('cuts', [])
    video_name = data.get('input_video', 'unknown')
    video_duration = None

    errors = []
    warnings = []
    results = []

    print(f"═══════════════════════════════════════════════")
    print(f"  VALIDAÇÃO DE CORTES")
    print(f"═══════════════════════════════════════════════")
    print(f"📁 Pasta: {output_dir}")
    print(f"🎬 Vídeo: {video_name}")
    print(f"🤖 Modelo: {data.get('model', '?')}")
    print(f"📊 Cortes: {len(cuts)}")
    print()

    if not cuts:
        errors.append("Nenhum corte encontrado no JSON")
        _print_results(errors, warnings, results)
        return False

    # 1. Verificar ordenação cronológica
    for i in range(len(cuts) - 1):
        if cuts[i]['start_sec'] > cuts[i + 1]['start_sec']:
            warnings.append(
                f"Cortes fora de ordem cronológica: Cut {cuts[i]['id']} "
                f"({cuts[i]['start_sec']}s) vem antes de Cut {cuts[i+1]['id']} "
                f"({cuts[i+1]['start_sec']}s)"
            )
            break

    # 2. Verificar sobreposições
    for i in range(len(cuts) - 1):
        if cuts[i]['end_sec'] > cuts[i + 1]['start_sec'] + 0.5:
            errors.append(
                f"SOBREPOSIÇÃO: Cut {cuts[i]['id']} ({cuts[i]['end_sec']}s) "
                f"sobrepõe Cut {cuts[i+1]['id']} ({cuts[i+1]['start_sec']}s) "
                f"por {cuts[i]['end_sec'] - cuts[i+1]['start_sec']:.1f}s"
            )

    # 3. Validar cada corte
    for cut in cuts:
        cid = cut['id']
        start = cut['start_sec']
        end = cut['end_sec']
        dur_json = end - start
        content = cut.get('content', '')
        filename = cut.get('filename', '')
        filepath = output_path / filename if filename else None

        cut_result = {
            'id': cid,
            'start': start,
            'end': end,
            'duration_json': dur_json,
            'filename': filename,
            'checks': []
        }

        # 3a. Duração no range
        if dur_json < 15:
            errors.append(f"Cut {cid}: duração {dur_json:.1f}s < 15s mínimo")
        elif dur_json > 60:
            errors.append(f"Cut {cid}: duração {dur_json:.1f}s > 60s máximo")
        else:
            cut_result['checks'].append('✓ Duração OK')

        # 3b. Timestamps válidos
        if start < 0:
            errors.append(f"Cut {cid}: start_sec {start} < 0")
        if end <= start:
            errors.append(f"Cut {cid}: end_sec {end} <= start_sec {start}")

        # 3c. Arquivo existe
        if filepath and filepath.exists():
            cut_result['checks'].append('✓ Arquivo existe')

            # 3d. Duração real do clip vs JSON
            real_dur = get_clip_duration(str(filepath))
            if real_dur:
                cut_result['duration_real'] = real_dur
                diff = abs(real_dur - dur_json)
                if diff > 3.0:
                    errors.append(
                        f"Cut {cid}: duração real ({real_dur:.1f}s) difere "
                        f"da JSON ({dur_json:.1f}s) por {diff:.1f}s"
                    )
                elif diff > 1.0:
                    warnings.append(
                        f"Cut {cid}: duração real ({real_dur:.1f}s) difere "
                        f"da JSON ({dur_json:.1f}s) por {diff:.1f}s"
                    )
                else:
                    cut_result['checks'].append(f'✓ Duração real={real_dur:.1f}s ≈ JSON={dur_json:.1f}s')

            # 3e. Tamanho do arquivo
            size = get_clip_size(str(filepath))
            if size:
                size_mb = size / (1024 * 1024)
                cut_result['size_mb'] = size_mb
                if size == 0:
                    errors.append(f"Cut {cid}: arquivo vazio (0 bytes)")
                elif size_mb < 0.1:
                    warnings.append(f"Cut {cid}: arquivo muito pequeno ({size_mb:.1f}MB)")
                else:
                    cut_result['checks'].append(f'✓ Tamanho {size_mb:.1f}MB')
        elif filepath:
            errors.append(f"Cut {cid}: arquivo não encontrado: {filename}")

        # 3f. Filename bate com timestamps
        if filename:
            m = re.match(r'cut_(\d+)_(\d+)-(\d+)s\.mp4', filename)
            if m:
                fn_id = int(m.group(1))
                fn_start = int(m.group(2))
                fn_end = int(m.group(3))
                if fn_id != cid:
                    errors.append(
                        f"Cut {cid}: filename usa índice {fn_id:02d}, esperado {cid:02d}"
                    )
                if abs(fn_start - start) > 1 or abs(fn_end - end) > 1:
                    warnings.append(
                        f"Cut {cid}: filename ({fn_start}-{fn_end}) "
                        f"não bate exatamente com JSON ({start:.0f}-{end:.0f})"
                    )
                else:
                    cut_result['checks'].append('✓ Filename OK')

        # 3g. Análise textual básica do content
        if content:
            word_count = len(content.split())
            cut_result['word_count'] = word_count
            # Estimativa: ~3 palavras por segundo em português
            expected_words = dur_json * 3
            if word_count < expected_words * 0.3:
                warnings.append(
                    f"Cut {cid}: content tem {word_count} palavras, "
                    f"esperado ~{int(expected_words)} para {dur_json:.0f}s"
                )
            elif word_count > expected_words * 3:
                warnings.append(
                    f"Cut {cid}: content tem {word_count} palavras, "
                    f"muito para {dur_json:.0f}s (esperado ~{int(expected_words)})"
                )
            else:
                cut_result['checks'].append(f'✓ Texto plausível ({word_count} palavras)')

        results.append(cut_result)

    # 4. Verificar gaps entre cortes
    gaps = []
    for i in range(len(cuts) - 1):
        gap = cuts[i + 1]['start_sec'] - cuts[i]['end_sec']
        gaps.append((cuts[i]['id'], cuts[i + 1]['id'], gap))

    # 5. Verificar se há conteúdo de patrocínio (comum em vídeos)
    all_content = ' '.join(c.get('content', '') for c in cuts)
    sponsor_keywords = ['alura', 'patrocin', 'desconto', 'cupom', 'link na descrição']
    found_sponsors = [kw for kw in sponsor_keywords if kw.lower() in all_content.lower()]
    if found_sponsors:
        warnings.append(f"Possível conteúdo de patrocínio detectado: {', '.join(found_sponsors)}")

    # Imprimir resultados
    print("─── Cortes ───")
    for r in results:
        print(f"\n  Cut {r['id']} [{r['start']:.1f}s - {r['end']:.1f}s] ({r['duration_json']:.1f}s)")
        for check in r['checks']:
            print(f"    {check}")

    if gaps:
        print(f"\n─── Gaps entre cortes ───")
        for c1, c2, gap in gaps:
            label = "✓" if gap > 2 else "⚠️"
            print(f"  {label} Cut {c1}→{c2}: {gap:.1f}s")

    if found_sponsors:
        print(f"\n─── Conteúdo suspeito ───")
        print(f"  ⚠️ Possível patrocínio: {', '.join(found_sponsors)}")

    _print_results(errors, warnings, results)
    return len(errors) == 0


def _print_results(errors, warnings, results):
    print()
    if errors:
        print(f"❌ ERROS ({len(errors)}):")
        for e in errors:
            print(f"  • {e}")
    if warnings:
        print(f"⚠️  AVISOS ({len(warnings)}):")
        for w in warnings:
            print(f"  • {w}")
    if not errors and not warnings:
        print("✅ Todos os cortes passaram na validação!")

    print()


def verify_content_with_gemini(output_dir, api_key):
    """Verifica se o conteúdo transcrito no JSON bate com o áudio real dos clips."""
    import tempfile
    import time
    import urllib.request
    import json as json_mod

    output_path = Path(output_dir)
    cuts_file = output_path / 'cuts.json'

    with open(cuts_file) as f:
        data = json.load(f)

    cuts = data.get('cuts', [])
    model = data.get('model', 'gemini-3-flash-preview')

    mismatches = []
    matches = []

    for cut in cuts:
        cid = cut['id']
        filename = cut.get('filename', '')
        content = cut.get('content', '')
        filepath = output_path / filename

        if not filepath.exists():
            print(f"  Cut {cid}: arquivo não encontrado, pulando")
            continue

        # Extrair primeiros 8s do clip como WAV
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_path = tmp.name

        subprocess.run(
            ['ffmpeg', '-i', str(filepath), '-ss', '0', '-t', '8',
             '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
             tmp_path, '-y'],
            capture_output=True, timeout=30
        )

        try:
            # Upload do arquivo
            file_size = os.path.getsize(tmp_path)
            upload_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={api_key}"

            with open(tmp_path, 'rb') as f:
                audio_data = f.read()

            req = urllib.request.Request(
                upload_url,
                data=audio_data,
                headers={
                    'X-Goog-Upload-Command': 'start, upload, finalize',
                    'X-Goog-Upload-Header-Content-Length': str(file_size),
                    'Content-Type': 'audio/wav'
                },
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                upload_result = json_mod.loads(resp.read().decode())

            file_uri = upload_result['file']['uri']
            time.sleep(2)

            # Transcrever os primeiros 8s
            gen_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            prompt_text = (
                "Transcreva EXATAMENTE o que é dito nestes primeiros 8 segundos de áudio. "
                "Apenas o texto literal, sem comentários."
            )

            body = {
                "contents": [{"parts": [
                    {"file_data": {"mime_type": "audio/wav", "file_uri": file_uri}},
                    {"text": prompt_text}
                ]}],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "response_schema": {"type": "object", "properties": {"text": {"type": "string"}}}
                }
            }

            req2 = urllib.request.Request(
                gen_url,
                data=json_mod.dumps(body).encode(),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(req2, timeout=60) as resp:
                gen_result = json_mod.loads(resp.read().decode())

            actual_text = json_mod.loads(
                gen_result['candidates'][0]['content']['parts'][0]['text']
            )['text'].lower()

            # Comparar com os primeiros ~8s do content do JSON
            content_words = content.split()
            content_start = ' '.join(content_words[:20]).lower()

            # Verificar sobreposição de palavras
            actual_words = set(actual_text.split())
            json_words = set(content_start.split())
            common = actual_words & json_words
            # Remover stop words
            stop_words = {'o', 'a', 'de', 'e', 'que', 'em', 'um', 'uma', 'do', 'da',
                          'no', 'na', 'os', 'as', 'dos', 'das', 'com', 'por', 'para',
                          'se', 'não', 'mais', 'como', 'mas', 'foi', 'ao', 'ele',
                          'isso', 'tem', 'à', 'seu', 'sua', 'ou', 'ser', 'quando',
                          'muito', 'há', 'nos', 'já', 'está', 'eu', 'também', 'só',
                          'pelo', 'pela', 'até', 'isso', 'um', 'uns'}
            meaningful = common - stop_words
            total_meaningful = len((actual_words | json_words) - stop_words)

            if total_meaningful > 0:
                similarity = len(meaningful) / total_meaningful
            else:
                similarity = 0

            if similarity < 0.2:
                mismatches.append({
                    'id': cid,
                    'similarity': similarity,
                    'actual': actual_text[:100],
                    'json_start': content_start[:100]
                })
                print(f"  ❌ Cut {cid}: CONTEÚDO NÃO BATE (similaridade: {similarity:.0%})")
                print(f"     Áudio real: {actual_text[:80]}...")
                print(f"     JSON diz:   {content_start[:80]}...")
                print()
            else:
                matches.append({'id': cid, 'similarity': similarity})
                print(f"  ✓ Cut {cid}: conteúdo OK (similaridade: {similarity:.0%})")

            time.sleep(2)

        except Exception as e:
            print(f"  ⚠️ Cut {cid}: erro na verificação: {str(e)[:80]}")
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    print(f"\n─── Resumo ───")
    print(f"  ✓ Matches: {len(matches)}/{len(cuts)}")
    print(f"  ❌ Mismatches: {len(mismatches)}/{len(cuts)}")
    if mismatches:
        print(f"\n  Cortes com problema de conteúdo:")
        for m in mismatches:
            print(f"    Cut {m['id']} (similaridade: {m['similarity']:.0%})")
    print()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Validar cuts.json contra clips gerados')
    parser.add_argument('output_dir', help='Pasta de output (ex: ./output/20260330_1913)')
    parser.add_argument('--verify-content', action='store_true',
                        help='Verificar conteúdo real via Gemini API (consome quota)')
    parser.add_argument('--api-key', help='GEMINI_API_KEY (ou usar variável de ambiente)')
    args = parser.parse_args()

    success = validate_cuts(args.output_dir)
    
    if args.verify_content:
        api_key = args.api_key or os.environ.get('GEMINI_API_KEY', '')
        if not api_key:
            # Tentar ler do .env
            env_path = Path(__file__).parent.parent.parent.parent.parent / '.env'
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        if line.startswith('GEMINI_API_KEY='):
                            api_key = line.split('=', 1)[1].strip()
                            break
        
        if not api_key:
            print("❌ GEMINI_API_KEY não encontrada. Use --api-key ou defina a variável de ambiente.")
            sys.exit(1)
        
        print("\n═══════════════════════════════════════════════")
        print("  VERIFICAÇÃO DE CONTEÚDO (Gemini API)")
        print("═══════════════════════════════════════════════\n")
        
        verify_content_with_gemini(args.output_dir, api_key)
    
    sys.exit(0 if success else 1)
