#!/usr/bin/env python3

import csv
import re
import sys
from pathlib import Path


class MetricsParser:
    METRIC_PATTERN = re.compile(
        r"""^\s*\d{2}:\d{2}:\d{2}\s+\S+\s+INFO\s+
            (?P<label>
                Efficiency\ with\ particles|
                Fake\ ratio\ with\ particles|
                Duplicate\ ratio\ with\ particles
            )
            \s+\(.*?\)\s*=\s*(?P<value>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*$""",
        re.VERBOSE,
    )

    PERF_FILE_PATTERN = re.compile(
        r"""Wrote\ performance\ plots\ to\ '([^']+)'"""
    )

    TRACKFINDING_STATS_START_PATTERN = re.compile(
        r"""TrackFindingAlgorithm statistics:"""
    )

    TRACKFINDING_STAT_LINE_PATTERN = re.compile(
        r"""^\s*\d{2}:\d{2}:\d{2}\s+\S+\s+INFO\s+-\s+
            (?P<key>[^:]+):\s*
            (?P<value>[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*$""",
        re.VERBOSE,
    )

    def __init__(self, input_filepath: str, output_filepath: str):
        self.input_filepath = Path(input_filepath)
        self.output_filepath = Path(output_filepath)

    def parse(self):
        text = self.input_filepath.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()

        result = self._empty_result()

        pending_metric_block = []
        in_trackfinding_stats = False

        for line in lines:
            metric_match = self.METRIC_PATTERN.match(line)
            if metric_match:
                pending_metric_block.append({
                    "label": metric_match.group("label").strip(),
                    "value": float(metric_match.group("value")),
                })
                continue

            perf_match = self.PERF_FILE_PATTERN.search(line)
            if perf_match:
                perf_target = perf_match.group(1)
                stage = self._infer_stage_from_perf_target(perf_target)

                if stage is not None and pending_metric_block:
                    self._assign_metrics_to_stage(
                        result=result,
                        stage=stage,
                        metric_block=pending_metric_block,
                    )
                    pending_metric_block = []
                else:
                    pending_metric_block = []
                continue

            if self.TRACKFINDING_STATS_START_PATTERN.search(line):
                in_trackfinding_stats = True
                continue

            if in_trackfinding_stats:
                stat_match = self.TRACKFINDING_STAT_LINE_PATTERN.match(line)
                if stat_match:
                    key = self._normalize_stat_key(stat_match.group("key"))
                    value = self._parse_numeric(stat_match.group("value"))
                    result["trackfinding_stats"][key] = value
                    continue
                else:
                    in_trackfinding_stats = False

        return result

    def write_csv(self, parsed_data):
        self.output_filepath.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "source_file",

            "seeding_particle_efficiency",
            "seeding_particle_fake_ratio",
            "seeding_particle_duplicate_ratio",

            "ckf_particle_efficiency",
            "ckf_particle_fake_ratio",
            "ckf_particle_duplicate_ratio",

            "ambi_particle_efficiency",
            "ambi_particle_fake_ratio",
            "ambi_particle_duplicate_ratio",

            "trackfinding_total_seeds",
            "trackfinding_deduplicated_seeds",
            "trackfinding_failed_seeds",
            "trackfinding_failed_smoothing",
            "trackfinding_failed_extrapolation",
            "trackfinding_failure_ratio_seeds",
            "trackfinding_found_tracks",
            "trackfinding_selected_tracks",
            "trackfinding_stopped_branches",
            "trackfinding_skipped_second_pass",
        ]

        row = {"source_file": str(self.input_filepath)}

        for stage in ("seeding", "ckf", "ambi"):
            stage_data = parsed_data["stages"][stage]
            row[f"{stage}_particle_efficiency"] = stage_data["particle_efficiency"]
            row[f"{stage}_particle_fake_ratio"] = stage_data["particle_fake_ratio"]
            row[f"{stage}_particle_duplicate_ratio"] = stage_data["particle_duplicate_ratio"]

        stats = parsed_data["trackfinding_stats"]
        row["trackfinding_total_seeds"] = stats.get("total_seeds")
        row["trackfinding_deduplicated_seeds"] = stats.get("deduplicated_seeds")
        row["trackfinding_failed_seeds"] = stats.get("failed_seeds")
        row["trackfinding_failed_smoothing"] = stats.get("failed_smoothing")
        row["trackfinding_failed_extrapolation"] = stats.get("failed_extrapolation")
        row["trackfinding_failure_ratio_seeds"] = stats.get("failure_ratio_seeds")
        row["trackfinding_found_tracks"] = stats.get("found_tracks")
        row["trackfinding_selected_tracks"] = stats.get("selected_tracks")
        row["trackfinding_stopped_branches"] = stats.get("stopped_branches")
        row["trackfinding_skipped_second_pass"] = stats.get("skipped_second_pass")

        with self.output_filepath.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(row)

    def run(self):
        parsed = self.parse()
        self.write_csv(parsed)

    @staticmethod
    def _empty_result():
        def empty_stage():
            return {
                "particle_efficiency": None,
                "particle_fake_ratio": None,
                "particle_duplicate_ratio": None,
            }

        return {
            "stages": {
                "seeding": empty_stage(),
                "ckf": empty_stage(),
                "ambi": empty_stage(),
            },
            "trackfinding_stats": {},
        }

    @staticmethod
    def _infer_stage_from_perf_target(perf_target: str):
        target = perf_target.lower()

        if "performance_seeding.root" in target:
            return "seeding"
        if "performance_finding_ckf.root" in target:
            return "ckf"
        if "performance_finding_ambi.root" in target:
            return "ambi"

        return None

    def _assign_metrics_to_stage(self, result, stage, metric_block):
        stage_data = result["stages"][stage]

        label_map = {
            "Efficiency with particles": "particle_efficiency",
            "Fake ratio with particles": "particle_fake_ratio",
            "Duplicate ratio with particles": "particle_duplicate_ratio",
        }

        for item in metric_block:
            mapped_key = label_map.get(item["label"])
            if mapped_key is not None:
                stage_data[mapped_key] = item["value"]

    @staticmethod
    def _normalize_stat_key(key: str):
        return key.strip().lower().replace(" ", "_").replace("-", "_")

    @staticmethod
    def _parse_numeric(value: str):
        if any(ch in value for ch in ".eE"):
            return float(value)
        return int(value)


def main():
    if len(sys.argv) != 3:
        print("Usage: python MetricsParser.py <input_file> <output_csv_file>")
        sys.exit(1)

    parser = MetricsParser(sys.argv[1], sys.argv[2])
    parser.run()


if __name__ == "__main__":
    main()
