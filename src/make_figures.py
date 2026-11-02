"""The three README figures."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import assumptions as A  # noqa: E402

BLUE, ORANGE, AQUA, LIGHT_BLUE = "#2a78d6", "#eb6834", "#1baf7a", "#9ec5f4"
INK, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
BLUES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": MUTED, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
})


def _grid(ax, axis="y"):
    ax.grid(axis=axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _pct(share):
    value = share * 100
    return f"{value:.0f}%" if value >= 10 else f"{value:.1f}%"


def _stacked_costs(ax, x, rows, width):
    """Stack extra-driver, overtime and outside-carrier costs; return the totals."""
    extra = np.array([r.extra_driver_cost for r in rows]) / 1000
    overtime = np.array([r.overtime_cost for r in rows]) / 1000
    outside = np.array([r.outside_cost for r in rows]) / 1000
    ax.bar(x, extra, width=width, color=BLUE, label="Extra drivers")
    ax.bar(x, overtime, width=width, bottom=extra, color=AQUA, label="Overtime",
           edgecolor=SURFACE, linewidth=2)
    ax.bar(x, outside, width=width, bottom=extra + overtime, color=ORANGE,
           label="Outside carriers", edgecolor=SURFACE, linewidth=2)
    return extra + overtime + outside


def plot_fixed_buffers(fixed, path):
    """Left: yearly cost split. Right: weeks with a gap vs weeks still outsourced."""
    fig, (left, right) = plt.subplots(1, 2, figsize=(10.5, 4.4))
    x = fixed.fixed_buffer.to_numpy()
    rows = [r for _, r in fixed.iterrows()]

    totals = _stacked_costs(left, x, rows, 0.6)
    for xi, total in zip(x, totals):
        left.text(xi, total + 6, f"${total:,.0f}K", ha="center", fontsize=9, color=INK)
    left.set_title("Yearly cost on top of the plan")
    left.set_xlabel("Extra drivers kept all year")
    left.set_ylabel("Thousand $ per year")
    left.set_xticks(x)
    left.set_ylim(0, totals.max() * 1.3)
    left.legend(loc="upper left", fontsize=9, facecolor=SURFACE, edgecolor="none", framealpha=1)
    _grid(left)

    gap = fixed.gap_week_share.to_numpy() * 100
    out = fixed.outsourced_week_share.to_numpy() * 100
    w = 0.38
    right.bar(x - w / 2, gap, width=w, color=LIGHT_BLUE, label="Gap before overtime")
    right.bar(x + w / 2, out, width=w, color=BLUE, label="Still outsourced after overtime")
    for xi, g, o in zip(x, gap, out):
        right.text(xi - w / 2, g + 1, _pct(g / 100), ha="center", fontsize=8.5, color=MUTED)
        right.text(xi + w / 2, o + 1, _pct(o / 100), ha="center", fontsize=8.5, color=INK)
    right.axhline(A.SERVICE_TARGET * 100, color=MUTED, linestyle="--", linewidth=1)
    right.set_title(f"% of weeks (dashed = {A.SERVICE_TARGET:.0%} target)")
    right.set_xlabel("Extra drivers kept all year")
    right.set_ylabel("% of weeks")
    right.set_xticks(x)
    right.set_ylim(0, gap.max() * 1.25)
    right.legend(frameon=False, loc="upper right", fontsize=9)
    _grid(right)

    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _option_label(row):
    label = f"+{int(row.fixed_buffer)} all year"
    if row.peak_buffer:
        label += f"\n+{int(row.peak_buffer)} in periods 10-13"
    return label


def plot_fixed_vs_peak(options, best_fixed, best_any, path):
    """Compare a one-smaller all-year buffer, the best all-year option and the best mix."""
    rows = [best_fixed, best_any]
    if best_fixed.fixed_buffer > 0:
        one_less = options[(options.fixed_buffer == best_fixed.fixed_buffer - 1)
                           & (options.peak_buffer == 0)].iloc[0]
        rows = [one_less] + rows
    x = np.arange(len(rows))

    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    totals = _stacked_costs(ax, x, rows, 0.55)
    for xi, r, top in zip(x, rows, totals):
        met = "meets" if r.outsourced_week_share <= A.SERVICE_TARGET else "misses"
        ax.text(xi, top + 6, f"${top:,.0f}K\n{_pct(r.outsourced_week_share)} outsourced\n({met} target)",
                ha="center", fontsize=9, color=INK)
    ax.set_xticks(x, [_option_label(r) for r in rows])
    ax.set_ylabel("Total yearly cost, thousand $")
    ax.set_ylim(0, totals.max() * 1.45)
    ax.set_title(f"Getting under {A.SERVICE_TARGET:.0%} outsourced weeks (10% overtime cap)")
    ax.legend(loc="upper left", fontsize=9, facecolor=SURFACE, edgecolor="none", framealpha=1)
    _grid(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_sensitivity(sens, path):
    """One small heatmap per overtime cap: lowest-cost all-year buffer."""
    caps = sorted(sens.overtime_cap.unique())
    fig, axes = plt.subplots(1, len(caps), figsize=(12, 4.2), sharey=True)
    cmap = matplotlib.colors.ListedColormap(BLUES)
    for ax, cap in zip(axes, caps):
        part = sens[sens.overtime_cap == cap]
        table = part.pivot(index="absence_rate", columns="short_cost", values="best_buffer")
        ax.imshow(table.values, cmap=cmap, vmin=-0.5, vmax=len(BLUES) - 0.5, aspect="auto")
        for i in range(table.shape[0]):
            for j in range(table.shape[1]):
                value = int(table.values[i, j])
                ax.text(j, i, str(value), ha="center", va="center", fontsize=10,
                        color=INK if value < 3 else SURFACE)
        if cap == A.OVERTIME_CAP:
            i0 = list(table.index).index(A.ABSENCE_RATE)
            j0 = list(table.columns).index(A.SHORT_COST_PER_WEEK)
            ax.add_patch(plt.Rectangle((j0 - 0.5, i0 - 0.5), 1, 1, fill=False,
                                       edgecolor=ORANGE, linewidth=2.5))
        ax.set_xticks(range(table.shape[1]), [f"${c / 1000:g}K" for c in table.columns], fontsize=8.5)
        ax.set_yticks(range(table.shape[0]), [f"{r:.0%}" for r in table.index])
        ax.set_title(f"Overtime cap {cap:.0%}")
        ax.set_xlabel("Cost of one driver-week outsourced")
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(length=0)
    axes[0].set_ylabel("Weekly absence rate")
    fig.suptitle("Lowest-cost number of extra drivers (orange box = base case)",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
