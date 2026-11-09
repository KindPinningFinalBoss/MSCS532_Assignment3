"""
Draw the charts used in REPORT.md from the CSV files in results/.

Needs matplotlib (pip install matplotlib). The sorting and hashing code itself
does not need it. Run the benchmarks first:

    python benchmark_quicksort.py
    python benchmark_hashing.py
    python make_plots.py
"""

import csv
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS, FIGURES = "results", "figures"
os.makedirs(FIGURES, exist_ok=True)


def read(name):
    with open(os.path.join(RESULTS, name), newline="") as f:
        return list(csv.DictReader(f))


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, name), dpi=150)
    plt.close(fig)
    print("wrote", os.path.join(FIGURES, name))


def fig_quicksort_times():
    rows = read("quicksort_times.csv")
    dists = [("random", "Random"), ("sorted", "Already sorted"), ("reverse", "Reverse sorted"),
             ("repeated", "Repeated (10 distinct values)")]
    styles = {
        ("randomized", "lomuto"): ("tab:blue", "-", "o"),
        ("deterministic", "lomuto"): ("tab:red", "-", "s"),
        ("randomized", "three_way"): ("tab:blue", "--", "o"),
        ("deterministic", "three_way"): ("tab:red", "--", "s"),
    }
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True)
    for ax, (dist, title) in zip(axes.flat, dists):
        for (algo, scheme), (color, ls, marker) in styles.items():
            pts = sorted((int(r["n"]), float(r["median_seconds"])) for r in rows
                         if r["distribution"] == dist and r["algorithm"] == algo and r["partition"] == scheme)
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, linestyle=ls, marker=marker,
                    markersize=4, label=f"{algo}, {scheme.replace('_', '-')}")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_title(title)
        ax.grid(True, which="both", alpha=0.3)
    for ax in axes[1]:
        ax.set_xlabel("array size n")
    for ax in axes[:, 0]:
        ax.set_ylabel("seconds (median)")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Randomized vs deterministic Quicksort (log-log; a straight line of slope 2 means n²)")
    save(fig, "fig1_quicksort_times.png")


def fig_quicksort_scaling():
    rows = read("quicksort_scaling.csv")
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for dist in ("random", "sorted", "reverse", "repeated", "all_equal"):
        pts = sorted((int(r["n"]), float(r["us_per_n_log2_n"])) for r in rows if r["distribution"] == dist)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", markersize=4, label=dist.replace("_", " "))
    ax.set_xscale("log", base=2)
    ax.set_xlabel("array size n")
    ax.set_ylabel("microseconds per (n · log₂ n)")
    ax.set_title("Randomized Quicksort (three-way): time ÷ n log n stays flat")
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)
    ax.legend()
    save(fig, "fig2_quicksort_scaling.png")


def fig_quicksort_comparisons():
    rows = read("quicksort_comparisons.csv")
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ns = sorted({int(r["n"]) for r in rows})
    formula = [2 * (n + 1) * sum(1 / k for k in range(1, n + 1)) - 4 * n for n in ns]
    ax.plot(ns, formula, "k-", label="formula 2(n+1)Hₙ − 4n")
    for dist, marker in (("random", "o"), ("sorted", "^")):
        pts = sorted((int(r["n"]), float(r["mean_comparisons"])) for r in rows
                     if r["algorithm"] == "randomized" and r["input"] == dist)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker=marker, linestyle="none", markerfacecolor="none",
                markersize=9, label=f"randomized, {dist} input (mean of 20)")
    pts = sorted((int(r["n"]), float(r["mean_comparisons"])) for r in rows if r["algorithm"] == "deterministic")
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "rs-", markersize=4, label="deterministic, sorted input = n(n−1)/2")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("array size n")
    ax.set_ylabel("comparisons")
    ax.set_title("Counted comparisons vs the analysis (Lomuto partition)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)
    save(fig, "fig3_quicksort_comparisons.png")


def fig_hash_comparisons():
    rows = read("hash_load_factor.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    alphas = sorted({float(r["alpha"]) for r in rows})
    for ax, kind, title in ((axes[0], "random", "Random keys"),
                            (axes[1], "multiples_of_m", "Keys that are all multiples of m")):
        sub = {float(r["alpha"]): r for r in rows if r["keys"] == kind}
        ax.plot(alphas, [float(sub[a]["successful_theory"]) for a in alphas], "k-", label="theory: successful search")
        ax.plot(alphas, [float(sub[a]["unsuccessful_theory"]) for a in alphas], "k--", label="theory: unsuccessful search")
        ax.plot(alphas, [float(sub[a]["successful_mean"]) for a in alphas], "o", color="tab:blue", markersize=8,
                markerfacecolor="none", label="measured mean: successful")
        ax.plot(alphas, [float(sub[a]["unsuccessful_mean"]) for a in alphas], "s", color="tab:orange", markersize=8,
                markerfacecolor="none", label="measured mean: unsuccessful")
        if kind == "multiples_of_m":
            ax.plot(alphas, [float(sub[a]["successful_median"]) for a in alphas], "x", color="tab:green", markersize=8,
                    label="measured median table: successful")
            ax.plot(alphas, [float(sub[a]["successful_p95"]) for a in alphas], "^", color="tab:red", markersize=6,
                    label="95th-percentile table: successful")
        ax.set_xscale("log", base=2)
        ax.set_xlabel("load factor α = n / m")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7)
    axes[0].set_ylabel("key comparisons per search")
    save(fig, "fig4_hash_comparisons.png")


def fig_hash_scaling():
    rows = read("hash_scaling.csv")
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharex=True)
    for ax, col, title in zip(axes, ("insert_us", "search_us", "delete_us"), ("insert", "search", "delete")):
        for mode, label, color in (("resizing_on", "resizing on (doubles at load 1.0)", "tab:green"),
                                   ("fixed_table", "fixed 1,024 slots", "tab:red")):
            pts = sorted((int(r["n"]), float(r[col])) for r in rows if r["mode"] == mode)
            ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", color=color, label=label)
        ax.set_xscale("log", base=2)
        ax.set_title(f"{title}: microseconds per operation")
        ax.set_xlabel("items stored n")
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)
    axes[0].legend(fontsize=8)
    save(fig, "fig5_hash_scaling.png")


if __name__ == "__main__":
    fig_quicksort_times()
    fig_quicksort_scaling()
    fig_quicksort_comparisons()
    fig_hash_comparisons()
    fig_hash_scaling()
