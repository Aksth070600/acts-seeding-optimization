#!/usr/bin/env python3

import sys
sys.path.insert(0, "figure-gen")
import _common  # noqa: F401

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import argparse
from pathlib import Path
from scipy import stats

plt.rcParams["axes.labelsize"]  = 11
plt.rcParams["axes.titlesize"]  = 11
plt.rcParams["xtick.labelsize"] = 9
plt.rcParams["ytick.labelsize"] = 9
plt.rcParams["font.size"]       = 9


class TimingAnalyzer:
    def __init__(self, output_dir="figures"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def read_timing_data(self, timing_files, workload_files):
        frames = []
        for t_path, w_path in zip(timing_files, workload_files):
            cumulative = pd.read_csv(t_path)["TIME_NS"].to_numpy(dtype=float)
            per_event  = np.diff(cumulative, prepend=0.0) / 1e6   # ns → ms

            sp = (
                pd.read_csv(w_path, usecols=["EVENT_INDEX", "SPACEPOINTS"])
                .sort_values("EVENT_INDEX")["SPACEPOINTS"]
                .to_numpy(dtype=float)
            )

            frames.append(pd.DataFrame({
                "eventnr":    np.arange(len(per_event)),
                "walltime":   per_event,
                "spacepoints": sp,
            }))

        return pd.concat(frames, ignore_index=True)

    def calculate_per_event_time(self, df, time_column='walltime'):
        events = df.groupby(['eventnr', 'spacepoints']).agg({
            time_column: ['mean', 'std', 'count']
        }).reset_index()
        events.columns = ['eventnr', 'spacepoints', 'time_mean', 'time_std', 'count']
        return events

    def fit_regression(self, x, y, degree=1):
        coeffs = np.polyfit(x, y, degree)
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        return coeffs, r2

    def format_equation(self, coeffs, label, r2):
        superscripts = {2: '²', 3: '³', 4: '⁴'}
        terms = []
        for power, coef in enumerate(reversed(coeffs)):
            if power == 0:
                terms.append(f"{coef:.3e}")
            elif power == 1:
                terms.append(f"{coef:.3e} x")
            else:
                sup = superscripts.get(power, f'^{power}')
                terms.append(f"{coef:.3e} x{sup}")
        equation = " + ".join(reversed(terms))
        equation = equation.replace("+ -", "- ")
        return f"{label}: y = {equation}   (R²={r2:.4f})"

    @staticmethod
    def _fmt_latex_coeff(val: float) -> str:
        coeff, exp = f"{val:.3e}".split("e")
        return f"${coeff}\\times10^{{{int(exp)}}}$"

    def save_latex_table(self, fit_results: dict, output_file: Path) -> None:
        lines = [
            r"\begin{tabular}{llccc}",
            r"    \toprule",
            r"    Detector & Algorithm & $a$ & $b$ & $R^{2}$ \\",
        ]

        for detector, methods in fit_results.items():
            lines.append(r"    \midrule")
            for m_idx, (method, (coeffs, r2)) in enumerate(methods.items()):
                a, b    = coeffs[0], coeffs[1]
                det_col = detector if m_idx == 0 else ""
                lines.append(
                    f"    {det_col:<6} & \\texttt{{{method}}}"
                    f" & {self._fmt_latex_coeff(a)}"
                    f" & {self._fmt_latex_coeff(b)}"
                    f" & {r2:.4f} \\\\"
                )

        lines += [r"    \bottomrule", r"\end{tabular}"]
        output_file.write_text("\n".join(lines) + "\n")
        print(f"LaTeX table saved to {output_file}")

    def _draw_panel(self, ax, seed_data, seed2_data, detector_name, degree=1):
        color_seeding  = '#1f77b4'
        color_seeding2 = '#ff7f0e'

        x1 = seed_data['spacepoints'].values
        y1 = seed_data['time_mean'].values
        coeffs1, r2_1 = self.fit_regression(x1, y1, degree)

        x2 = seed2_data['spacepoints'].values
        y2 = seed2_data['time_mean'].values
        coeffs2, r2_2 = self.fit_regression(x2, y2, degree)

        label1, label2 = "Seeding", "Seeding2"

        ax.scatter(x1, y1, alpha=0.6, s=40, color=color_seeding,
                   label=label1, zorder=3)
        x1_line = np.linspace(x1.min(), x1.max(), 300)
        ax.plot(x1_line, np.polyval(coeffs1, x1_line),
                color=color_seeding, linewidth=1.5, linestyle='--')

        ax.scatter(x2, y2, alpha=0.6, s=40, color=color_seeding2,
                   label=label2, zorder=3)
        x2_line = np.linspace(x2.min(), x2.max(), 300)
        ax.plot(x2_line, np.polyval(coeffs2, x2_line),
                color=color_seeding2, linewidth=1.5, linestyle='--')

        ax.set_xlabel(r'Space-point multiplicity ($N_{SP}$)')
        ax.set_ylabel('Execution time per event [ms]')
        ax.set_title(f'{detector_name} detector')
        ax.legend(loc='best', fontsize=9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        ax.xaxis.set_major_formatter(FuncFormatter(
            lambda v, _: f"{int(round(v / 1000))}k"
        ))

        all_x = np.concatenate([x1, x2])
        xpad  = (all_x.max() - all_x.min()) * 0.02
        ax.set_xlim(all_x.min() - xpad, all_x.max() + xpad)

        print(f"\n  [{detector_name}] Degree-{degree} polynomial regression:")
        print(f"    {self.format_equation(coeffs1, 'Seeding ', r2_1)}")
        print(f"    {self.format_equation(coeffs2, 'Seeding2', r2_2)}")

        return {
            "Seeding":  (coeffs1, r2_1),
            "Seeding2": (coeffs2, r2_2),
        }

    def create_pixel_strip_plot(self, pixel_seeding, strip_seeding,
                                pixel_seeding2, strip_seeding2,
                                output_file='figures/Results/Baseline/Scaling/ScalingComparison.pdf',
                                degree=1):
        output_path = Path(output_file)
        if output_path.suffix.lower() == '.png':
            output_path = output_path.with_suffix('.pdf')
        table_out  = output_path.with_suffix('.tex')

        pixel_seed  = self.calculate_per_event_time(pixel_seeding)
        pixel_seed2 = self.calculate_per_event_time(pixel_seeding2)
        strip_seed  = self.calculate_per_event_time(strip_seeding)
        strip_seed2 = self.calculate_per_event_time(strip_seeding2)

        fig, (ax_pix, ax_str) = plt.subplots(1, 2, figsize=(8, 4))

        pixel_fits = self._draw_panel(ax_pix, pixel_seed, pixel_seed2, 'Pixel', degree)
        strip_fits = self._draw_panel(ax_str, strip_seed, strip_seed2, 'Strip', degree)

        fig.tight_layout()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path)
        plt.close(fig)
        print(f"Plot saved to {output_path}")

        if degree == 1:
            self.save_latex_table(
                {"Pixel": pixel_fits, "Strip": strip_fits},
                table_out,
            )

    def analyze_pixel_strip(self, raw_dir, methods_dir, n_runs=None,
                            output_file='figures/Results/Baseline/Scaling/ScalingComparison.png',
                            degree=1):
        raw_dir     = Path(raw_dir)
        methods_dir = Path(methods_dir)
        if n_runs is None:
            import sys as _sys
            _sys.path.insert(0, "data-gen")
            from workflow import default_runs as _default_runs
            n_runs = _default_runs()

        def _resolve(directory, stem):
            # Prefer _runN files if present; fall back to the bare CSV
            # written by data-gen scripts that hardcode Runs=1.
            suffixed = sorted(directory.glob(f"{stem}_run*.csv"))
            if suffixed:
                return suffixed
            bare = directory / f"{stem}.csv"
            return [bare] if bare.exists() else [directory / f"{stem}_run1.csv"]

        def s1_files(detector):
            return (_resolve(raw_dir, f"{detector}ScalingTiming"),
                    _resolve(raw_dir, f"{detector}ScalingWorkload"))

        def s2_files(detector):
            return (_resolve(methods_dir, f"{detector}Timing"),
                    _resolve(methods_dir, f"{detector}Workload"))

        print("Reading Pixel Seeding...")
        pixel_seeding  = self.read_timing_data(*s1_files("Pixel"))
        print("Reading Strip Seeding...")
        strip_seeding  = self.read_timing_data(*s1_files("Strip"))
        print("Reading Pixel Seeding2...")
        pixel_seeding2 = self.read_timing_data(*s2_files("Pixel"))
        print("Reading Strip Seeding2...")
        strip_seeding2 = self.read_timing_data(*s2_files("Strip"))

        self.create_pixel_strip_plot(pixel_seeding, strip_seeding,
                                     pixel_seeding2, strip_seeding2,
                                     output_file, degree)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze timing data and generate scaling plots'
    )
    parser.add_argument(
        '--raw-dir',
        default='raw-data/Results/Baseline/Scaling',
        help='Directory containing the S1 (Default) timing+workload CSVs'
    )
    parser.add_argument(
        '--methods-dir',
        default='raw-data/Methods',
        help='Directory containing the S2 (GridTriplet) timing+workload CSVs '
             '(produced by data-gen/Methods/Workload.py)'
    )
    import sys as _sys
    _sys.path.insert(0, "data-gen")
    from workflow import default_runs as _default_runs
    parser.add_argument(
        '--n-runs',
        type=int,
        default=_default_runs(),
        help='Number of runs to average over (default: configs/config.yaml runs)'
    )
    parser.add_argument(
        '--output-dir',
        default='figures',
        help='Output directory for plots (default: figures)'
    )
    parser.add_argument(
        '--output-file',
        default='figures/Results/Baseline/Scaling/ScalingComparison.pdf',
        help='Output filename for the combined 2-panel figure (PDF). Pass a '
             '.png to override format.'
    )
    parser.add_argument(
        '--degree',
        type=int,
        default=1,
        help='Degree of the polynomial regression line (default: 1)'
    )

    args = parser.parse_args()

    analyzer = TimingAnalyzer(output_dir=args.output_dir)
    analyzer.analyze_pixel_strip(
        raw_dir     = args.raw_dir,
        methods_dir = args.methods_dir,
        n_runs      = args.n_runs,
        output_file = args.output_file,
        degree      = args.degree,
    )


if __name__ == '__main__':
    main()
