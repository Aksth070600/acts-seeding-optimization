# utils/

Helpers used by the data-gen pipeline.

## Files

| File | Purpose |
| --- | --- |
| `CopyDir.sh` | Decodes a flattened `acts-overrides/<variant>/` directory back onto `ACTS/source/` — splits each filename on `_` to reconstruct the source path. Called by `DataGenWorkflow.copy_dir(...)`. |
| `parsers/TimerParser.py` | Reads `TIMER NAME: …, TOTAL TIME: …, COUNT: …` dumps from a log → CSV columns `NAME, TIME_NS, COUNT, …`. |
| `parsers/StatsParser.py` | Reads `STATS NAME: …, TOTAL: …, COUNT: …, VALUE_COUNT: […]` lines → CSV with summary stats and the value distribution. |
| `parsers/WorkloadParser.py` | Reads `Created <N> track seeds from <M> space points` lines → per-event CSV (`EVENT_INDEX, TRACK_SEEDS, SPACEPOINTS`). |
| `parsers/MetricsParser.py` | Reads ACTS efficiency / fake-ratio / duplicate-ratio summary lines → one-row CSV with `seeding_{particle,track}_{efficiency,fake_ratio,duplicate_ratio}`. |
