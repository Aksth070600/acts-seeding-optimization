#!/usr/bin/env python3
import csv
import re
import sys
from pathlib import Path


class SeedSpacepointParser:
    TRACK_PATTERN = re.compile(
        r"Created\s+(?P<track_seeds>\d+)\s+track seeds from\s+(?P<spacepoints>\d+)\s+space points"
    )

    def __init__(self, input_filepath: str, output_filepath: str):
        self.input_filepath = Path(input_filepath)
        self.output_filepath = Path(output_filepath)

    def parse(self):
        rows = []
        event_index = 0
        with self.input_filepath.open("r", encoding="utf-8", errors="replace") as f:
            for line_number, line in enumerate(f, start=1):
                track_match = self.TRACK_PATTERN.search(line)
                if track_match:
                    rows.append({
                        "event_index": event_index,
                        "track_seeds": int(track_match.group("track_seeds")),
                        "spacepoints": int(track_match.group("spacepoints")),
                        "source_line": line_number,
                    })
                    event_index += 1
        return rows

    def write_csv(self, rows):
        self.output_filepath.parent.mkdir(parents=True, exist_ok=True)
        total_events = len(rows)
        avg_track_seeds = (
            sum(row["track_seeds"] for row in rows) / total_events
            if total_events > 0 else None
        )
        avg_spacepoints = (
            sum(row["spacepoints"] for row in rows) / total_events
            if total_events > 0 else None
        )
        with self.output_filepath.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "EVENT_INDEX",
                "TRACK_SEEDS",
                "SPACEPOINTS",
                "TOTAL_EVENTS",
                "AVG_TRACK_SEEDS",
                "AVG_SPACEPOINTS",
                "SOURCE_LINE",
            ])
            for row in rows:
                writer.writerow([
                    row["event_index"],
                    row["track_seeds"],
                    row["spacepoints"],
                    total_events,
                    avg_track_seeds,
                    avg_spacepoints,
                    row["source_line"],
                ])

    def run(self):
        rows = self.parse()
        self.write_csv(rows)


def main():
    if len(sys.argv) != 3:
        print("Usage: python WorkloadParser.py <input_file> <output_csv_file>")
        sys.exit(1)
    parser = SeedSpacepointParser(sys.argv[1], sys.argv[2])
    parser.run()


if __name__ == "__main__":
    main()
