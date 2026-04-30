import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / ".agents" / "skills" / "video-cutter" / "scripts"
FIXTURES_DIR = ROOT / "tests" / "fixtures"


def make_temp_dir():
    temp_root = Path(os.environ.get("SHORTCUTTER_TEST_TMP", tempfile.gettempdir()))
    temp_root.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=temp_root)


class PipelineStepTests(unittest.TestCase):
    maxDiff = None

    def run_script(self, script_name, *args):
        command = [sys.executable, str(SCRIPTS_DIR / script_name), *[str(arg) for arg in args]]
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"{script_name} falhou\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        return result

    def test_sanitize_transcription_normalizes_and_removes_invalid_segments(self):
        with make_temp_dir() as temp_dir:
            output_path = Path(temp_dir) / "sanitized.json"
            self.run_script(
                "sanitize_transcription.py",
                FIXTURES_DIR / "sanitize_input.json",
                "40",
                output_path
            )

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["sanitization"]["applied"])
            self.assertEqual(len(payload["transcription"]), 2)
            self.assertEqual(payload["transcription"][0]["end_sec"], 5.0)
            self.assertEqual(payload["transcription"][1]["end_sec"], 40.0)
            self.assertIn("1 segmentos removidos por timestamps invalidos", payload["sanitization"]["warnings"])

    def test_validate_analysis_cuts_respects_mode_minimum_duration(self):
        with make_temp_dir() as temp_dir:
            aggressive_output = Path(temp_dir) / "aggressive.json"
            conservative_output = Path(temp_dir) / "conservative.json"

            self.run_script(
                "validate_analysis_cuts.py",
                FIXTURES_DIR / "analysis_input.json",
                "120",
                "aggressive",
                aggressive_output
            )
            self.run_script(
                "validate_analysis_cuts.py",
                FIXTURES_DIR / "analysis_input.json",
                "120",
                "conservative",
                conservative_output
            )

            aggressive_cuts = json.loads(aggressive_output.read_text(encoding="utf-8"))
            conservative_cuts = json.loads(conservative_output.read_text(encoding="utf-8"))

            self.assertEqual([cut["id"] for cut in aggressive_cuts], [1, 2])
            self.assertEqual([cut["id"] for cut in conservative_cuts], [1])

    def test_apply_buffer_revalidates_and_renumbers_cuts(self):
        with make_temp_dir() as temp_dir:
            output_path = Path(temp_dir) / "final_cuts.json"
            self.run_script(
                "apply_buffer.py",
                FIXTURES_DIR / "buffer_transcription.json",
                FIXTURES_DIR / "buffer_valid_cuts.json",
                "80",
                "conservative",
                output_path
            )

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["cuts"]), 1)
            self.assertEqual(payload["cuts"][0]["id"], 1)
            self.assertEqual(payload["cuts"][0]["start_sec"], 19.0)
            self.assertEqual(payload["cuts"][0]["end_sec"], 40.0)
            self.assertEqual(payload["buffer_details"][0]["id"], 1)
            self.assertEqual(payload["buffer_details"][0]["final_duration"], 21.0)

    def test_generate_metadata_preserves_relative_output_and_failure_warnings(self):
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir) / "project"
            run_dir = project_dir / "output" / "run_001"
            run_dir.mkdir(parents=True, exist_ok=True)

            final_cuts_path = Path(temp_dir) / "final_cuts_with_files.json"
            analysis_path = Path(temp_dir) / "analysis.json"
            output_path = Path(temp_dir) / "cuts.json"

            final_cuts_path.write_text(
                (FIXTURES_DIR / "final_cuts_with_files.json").read_text(encoding="utf-8"),
                encoding="utf-8"
            )
            analysis_path.write_text(
                (FIXTURES_DIR / "analysis_for_metadata.json").read_text(encoding="utf-8"),
                encoding="utf-8"
            )

            self.run_script(
                "generate_metadata.py",
                final_cuts_path,
                analysis_path,
                "aggressive",
                run_dir,
                project_dir,
                "video.mp4",
                output_path
            )

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["output_dir"], "./output/run_001")
            self.assertEqual(payload["total_cuts"], 1)
            self.assertIn("warning existente", payload["quality_warnings"])
            self.assertIn("Falha ao gerar cut_02_40-70s.mp4: ffmpeg failed", payload["quality_warnings"])


if __name__ == "__main__":
    unittest.main()
