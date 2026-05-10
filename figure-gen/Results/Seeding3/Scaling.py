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
                "eventnr":     np.arange(len(per_event)),
                "walltime":    per_event,
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
            r"\begin{tabular}{lccc}",
            r"    \toprule",
            r"    Algorithm & $a$ & $b$ & $R^{2}$ \\",
            r"    \midrule",
        ]

        for method, (coeffs, r2) in fit_results.items():
            a, b = coeffs[0], coeffs[1]
            lines.append(
                f"    \\texttt{{{method}}}"
                f" & {self._fmt_latex_coeff(a)}"
                f" & {self._fmt_latex_coeff(b)}"
                f" & {r2:.4f} \\\\"
            )

        lines += [r"    \bottomrule", r"\end{tabular}"]
        output_file.write_text("\n".join(lines) + "\n")
        print(f"LaTeX table saved to {output_file}")

    def create_scaling_plot(self, data_seeding, data_seeding2, data_seeding3,
                            output_file='figures/Results/Seeding3/Scaling/ScalingComparison.pdf',
                            degree=1):
        output_path = Path(output_file)
        if output_path.suffix.lower() == '.png':
            output_path = output_path.with_suffix('.pdf')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        table_out = output_path.with_suffix('.tex')

        color_seeding  = '#1f77b4'
        color_seeding2 = '#ff7f0e'
        color_seeding3 = '#2ca02c'

        methods = [
            ("Seeding",  data_seeding,  color_seeding),
            ("Seeding2", data_seeding2, color_seeding2),
            ("Seeding3", data_seeding3, color_seeding3),
        ]

        fig, ax = plt.subplots(figsize=(8, 4))
        fit_results = {}
        all_x = []

        for label, raw_df, color in methods:
            df = self.calculate_per_event_time(raw_df)
            x  = df['spacepoints'].values
            y  = df['time_mean'].values

            coeffs, r2 = self.fit_regression(x, y, degree)

            ax.scatter(x, y, alpha=0.6, s=40, color=color,
                       label=label, zorder=3)

            x_line = np.linspace(x.min(), x.max(), 300)
            ax.plot(x_line, np.polyval(coeffs, x_line),
                    color=color, linewidth=1.5, linestyle='--')

            fit_results[label] = (coeffs, r2)
            all_x.append(x)
            print(f"  {self.format_equation(coeffs, label, r2)}")

        ax.set_xlabel(r'Space-point multiplicity ($N_{SP}$)')
        ax.set_ylabel('Execution time per event [ms]')
        ax.legend(loc='best', fontsize=9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        ax.xaxis.set_major_formatter(FuncFormatter(
            lambda v, _: f"{int(round(v / 1000))}k"
        ))

        all_x_concat = np.concatenate(all_x)
        xpad = (all_x_concat.max() - all_x_concat.min()) * 0.02
        ax.set_xlim(all_x_concat.min() - xpad, all_x_concat.max() + xpad)

        fig.tight_layout()
        fig.savefig(output_path)
        print(f"Plot saved to {output_path}")
        plt.close(fig)

        if degree == 1:
            self.save_latex_table(fit_results, table_out)

    def analyze(self, raw_dir, n_runs=None,
                output_file='figures/Results/Seeding3/Scaling/ScalingComparison.pdf',
                degree=1):
        raw_dir = Path(raw_dir)
        if n_runs is None:
            import sys as _sys
            _sys.path.insert(0, "data-gen")
            from workflow import default_runs as _default_runs
            n_runs = _default_runs()

        def _resolve(stem):
            suffixed = sorted(raw_dir.glob(f"{stem}_run*.csv"))
            if suffixed:
                return suffixed
            bare = raw_dir / f"{stem}.csv"
            return [bare] if bare.exists() else [raw_dir / f"{stem}_run1.csv"]

        def run_files(method):
            return (_resolve(f"{method}Timing"), _resolve(f"{method}Workload"))

        print("Reading Seeding...")
        data_seeding  = self.read_timing_data(*run_files("Seeding"))

        print("Reading Seeding2...")
        data_seeding2 = self.read_timing_data(*run_files("Seeding2"))

        print("Reading Seeding3...")
        data_seeding3 = self.read_timing_data(*run_files("Seeding3"))

        self.create_scaling_plot(data_seeding, data_seeding2, data_seeding3,
                                 output_file, degree)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze timing data and generate scaling plots'
    )
    parser.add_argument(
        '--raw-dir',
        default='raw-data/Results/Seeding3/Scaling',
        help='Directory containing timing and workload CSV files'
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
        default='figures/Results/Seeding3/Scaling/ScalingComparison.pdf',
        help='Output filename (PDF). Pass a .png to override format.'
    )
    parser.add_argument(
        '--degree',
        type=int,
        default=1,
        help='Degree of the polynomial regression line (default: 1)'
    )

    args = parser.parse_args()

    analyzer = TimingAnalyzer(output_dir=args.output_dir)
    analyzer.analyze(
        raw_dir     = args.raw_dir,
        n_runs      = args.n_runs,
        output_file = args.output_file,
        degree      = args.degree,
    )


if __name__ == '__main__':
    main()
