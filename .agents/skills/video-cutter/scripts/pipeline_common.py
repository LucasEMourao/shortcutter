#!/usr/bin/env python3
"""Helpers shared by pipeline step scripts."""

import json
import os


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def to_display_path(path, project_dir):
    rel_path = os.path.relpath(path, project_dir)
    if not rel_path.startswith(".."):
        rel_path = rel_path.replace(os.sep, "/")
        return f"./{rel_path}" if rel_path != "." else "."
    return os.path.abspath(path).replace(os.sep, "/")


def get_mode_min_duration(mode, conservative_min_duration, default_min_duration):
    if mode == "conservative":
        return conservative_min_duration
    return default_min_duration


def get_cut_problems(cut, video_duration, min_duration, max_duration):
    start_sec = cut["start_sec"]
    end_sec = cut["end_sec"]
    duration = end_sec - start_sec
    problems = []

    if start_sec < 0:
        problems.append("start_sec < 0")
    if end_sec > video_duration:
        problems.append("end_sec > duracao do video")
    if end_sec <= start_sec:
        problems.append("end_sec <= start_sec")
    if duration < min_duration:
        problems.append(f"duracao < {int(min_duration)}s")
    if duration > max_duration:
        problems.append(f"duracao > {int(max_duration)}s")

    return problems
