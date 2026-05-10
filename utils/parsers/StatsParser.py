#!/usr/bin/env python3

import csv
import re
import sys
from pathlib import Path


class StatsParser:
    LINE_PATTERN = re.compile(
        r"""^\s*STATS\s+NAME:\s*(?P<name>.+?)\s*,\s*
             TOTAL:\s*(?P<total>-?\d+)\s*,\s*
             COUNT:\s*(?P<count>\d+)\s*,\s*
             VALUE_COUNT:\s*\[(?P<value_count>.*)\]\s*$""",
        re.VERBOSE,
    )

    VALUE_PATTERN = re.compile(r"\s*(-?\d+)\s*:\s*(\d+)\s*")

    def __init__(self, input_filepath: str, output_filepath: str):
        self.input_filepath = Path(input_filepath)
        self.output_filepath = Path(output_filepath)

    def parse(self):
        rows = []

        with self.input_filepath.open("r", encoding="utf-8", errors="replace") as f:
            for line_number, line in enumerate(f, start=1):
                match = self.LINE_PATTERN.match(line)
                if not match:
                    continue

                name = match.group("name").strip()
                total = int(match.group("total"))
                count = int(match.group("count"))
                value_count_raw = match.group("value_count")

                value_count = self._parse_value_count(value_count_raw)

                rows.append({
                    "name": name,
                    "total": total,
                    "count": count,
                    "value_count": value_count,
                    "line_number": line_number,
                })

        return rows

    def _parse_value_count(self, raw: str):
        result = {}

        if not raw.strip():
            return result

        entries = raw.split(",")

        for entry in entries:
            match = self.VALUE_PATTERN.match(entry)
            if not match:
                continue

            value = int(match.group(1))
            count = int(match.group(2))
            result[value] = count

        return result

    def write_csv(self, rows):
        self.output_filepath.parent.mkdir(parents=True, exist_ok=True)

        with self.output_filepath.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            writer.writerow([
                "NAME",
                "TOTAL",
                "COUNT",
                "VALUE_COUNT",
                "SOURCE_LINE",
            ])

            for row in rows:
                writer.writerow([
                    row["name"],
                    row["total"],
                    row["count"],
                    self._format_value_count(row["value_count"]),
                    row["line_number"],
                ])

    @staticmethod
    def _format_value_count(value_count: dict):
        if not value_count:
            return ""

        return "; ".join(f"{v}:{c}" for v, c in sorted(value_count.items()))

    def run(self):
        rows = self.parse()
        self.write_csv(rows)


def main():
    if len(sys.argv) != 3:
        print("Usage: python StatsParser.py <input_file> <output_csv_file>")
        sys.exit(1)

    parser = StatsParser(sys.argv[1], sys.argv[2])
    parser.run()


if __name__ == "__main__":
    main()
