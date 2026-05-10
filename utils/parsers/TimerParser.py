#!/usr/bin/env python3

import csv
import re
import sys
from pathlib import Path


class TimerParser:
    # Updated pattern: matches "TOTAL TIME:" instead of "TIME:"
    LINE_PATTERN = re.compile(
        r".*TIMER\s+NAME:\s*\"?(?P<name>[^,\"]+)\"?\s*,\s*TOTAL\s+TIME:\s*(?P<time>\d+)\s*(?:ns)?\s*,\s*COUNT:\s*(?P<count>\d+).*$"
    )

    def __init__(self, input_filepath: str, output_filepath: str):
        self.input_filepath = Path(input_filepath)
        self.output_filepath = Path(output_filepath)

    def parse(self):
        rows = []
        matched_lines = 0

        with self.input_filepath.open("r", encoding="utf-8", errors="replace") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                match = self.LINE_PATTERN.match(line)
                if not match:
                    # Only warn for lines that look like they should be timer lines
                    if "TIMER NAME:" in line and matched_lines == 0:
                        print(f"WARNING: Timer line not matched at line {line_number}: {line[:100]}")
                    continue

                matched_lines += 1
                name = match.group("name").strip()
                time_ns = int(match.group("time"))
                count = int(match.group("count"))
                average_time_ns = time_ns / count if count > 0 else 0.0

                rows.append({
                    "name": name,
                    "time_ns": time_ns,
                    "count": count,
                    "average_time_ns": average_time_ns,
                    "line_number": line_number,
                })

        return rows

    def write_csv(self, rows):
        self.output_filepath.parent.mkdir(parents=True, exist_ok=True)

        with self.output_filepath.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "NAME",
                "TIME_NS",
                "COUNT",
                "AVERAGE_TIME_NS",
                "SOURCE_LINE",
            ])

            for row in rows:
                writer.writerow([
                    row["name"],
                    row["time_ns"],
                    row["count"],
                    f"{row['average_time_ns']:.6f}",
                    row["line_number"],
                ])

    def run(self):
        rows = self.parse()

        if not rows:
            print("ERROR: No timer data found! Check file format and regex.")
            print("First few lines of file:")
            with self.input_filepath.open("r", encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f):
                    if i < 10:
                        print(f"  {i+1}: {repr(line[:100])}")
                    else:
                        break
        else:
            self.write_csv(rows)
            print(f"Successfully parsed {len(rows)} timer entries.")


def main():
    if len(sys.argv) != 3:
        print("Usage: python TimerParser.py <input_file> <output_csv_file>")
        sys.exit(1)

    parser = TimerParser(sys.argv[1], sys.argv[2])
    parser.run()


if __name__ == "__main__":
    main()
