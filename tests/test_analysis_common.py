import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / ".agents" / "skills" / "video-cutter" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from analysis_common import create_chunks, merge_cuts  # noqa: E402


class AnalysisCommonTests(unittest.TestCase):
    def test_create_chunks_preserves_overlap_between_chunks(self):
        transcription = {
            "transcription": [
                {"id": 1, "start_sec": 0.0, "end_sec": 10.0, "text": "A"},
                {"id": 2, "start_sec": 60.0, "end_sec": 70.0, "text": "B"},
                {"id": 3, "start_sec": 120.0, "end_sec": 130.0, "text": "C"},
                {"id": 4, "start_sec": 180.0, "end_sec": 190.0, "text": "D"},
                {"id": 5, "start_sec": 240.0, "end_sec": 250.0, "text": "E"},
                {"id": 6, "start_sec": 300.0, "end_sec": 310.0, "text": "F"}
            ]
        }

        chunks = create_chunks(transcription, 180, overlap_segments=2)

        self.assertEqual(len(chunks), 5)
        self.assertEqual(chunks[0]["segment_start_idx"], 0)
        self.assertEqual(chunks[0]["segment_end_idx"], 2)
        self.assertEqual(chunks[1]["segment_start_idx"], 1)
        self.assertEqual(chunks[1]["transcription"]["transcription"][0]["id"], 2)

    def test_merge_cuts_keeps_highest_scoring_overlapping_cut(self):
        cuts = [
            {
                "id": 1,
                "start_sec": 10.0,
                "end_sec": 40.0,
                "viral_score": 8.0
            },
            {
                "id": 2,
                "start_sec": 12.0,
                "end_sec": 38.0,
                "viral_score": 9.0
            },
            {
                "id": 3,
                "start_sec": 50.0,
                "end_sec": 70.0,
                "viral_score": 7.5
            }
        ]

        merged = merge_cuts(cuts)

        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["id"], 1)
        self.assertEqual(merged[0]["start_sec"], 12.0)
        self.assertEqual(merged[0]["viral_score"], 9.0)
        self.assertEqual(merged[1]["id"], 2)
        self.assertEqual(merged[1]["start_sec"], 50.0)


if __name__ == "__main__":
    unittest.main()
