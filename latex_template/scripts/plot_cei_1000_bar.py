import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Patch
from pathlib import Path

matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

labels = ['覆盖率保持率 (%)', '总物理执行耗时 (s)', '崩溃检出数']
baseline = np.array([100.0, 1563.8, 312.0])
filtered = np.array([99.995, 1024.1, 298.0])

width = 0.34

fig, axes = plt.subplots(1, 3, figsize=(10.8, 4.2))
colors = ['#2563EB', '#10B981']
edge_color = '#1F2937'

for ax, label, base_value, filter_value in zip(axes, labels, baseline, filtered):
    bars = ax.bar(
        [-width / 2, width / 2],
        [base_value, filter_value],
        width=width,
        color=colors,
        edgecolor=edge_color,
        linewidth=0.8,
        alpha=0.92,
    )

    ax.set_title(label, fontsize=12, pad=10, fontweight='bold')
    ax.set_xticks([-width / 2, width / 2])
    ax.set_xticklabels(['基线组\n1000例', '筛选组\n600例'], fontsize=10)
    ax.grid(axis='y', linestyle='--', alpha=0.28)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    max_value = max(base_value, filter_value)
    min_value = min(base_value, filter_value)

    if '覆盖率' in label:
        ax.set_ylim(99.98, 100.005)
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.3f'))
        value_fmt = '{:.3f}%'
        reduction_text = '近乎无损\n-0.005%'
        text_y = 99.984
    elif '耗时' in label:
        ax.set_ylim(0, max_value * 1.22)
        value_fmt = '{:.1f}s'
        reduction_text = '耗时缩减\n-34.5%'
        text_y = max_value * 0.83
    else:
        ax.set_ylim(0, max_value * 1.22)
        value_fmt = '{:.0f}'
        reduction_text = '检出损失\n-4.5%'
        text_y = max_value * 0.83

    for bar, value in zip(bars, [base_value, filter_value]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.025,
            value_fmt.format(value),
            ha='center',
            va='bottom',
            fontsize=10,
            fontweight='bold',
        )

    ax.annotate(
        reduction_text,
        xy=(width / 2, filter_value),
        xytext=(0.38, text_y),
        textcoords='data',
        fontsize=9,
        color='#374151',
        ha='center',
        arrowprops=dict(arrowstyle='->', color='#6B7280', lw=1.1),
        bbox=dict(boxstyle='round,pad=0.25', fc='#F3F4F6', ec='#D1D5DB', alpha=0.95),
    )

fig.suptitle('千例规模 CEI 筛选前后关键指标对比', fontsize=15, fontweight='bold', y=1.02)
legend_handles = [
    Patch(facecolor=colors[0], edgecolor=edge_color, label='基线组（1000例）'),
    Patch(facecolor=colors[1], edgecolor=edge_color, label='筛选组（600例）'),
]
fig.legend(handles=legend_handles, loc='lower center', ncol=2, frameon=False, fontsize=11)
fig.tight_layout(rect=[0, 0.08, 1, 0.96])

out_path = Path(__file__).resolve().parents[1] / 'figure' / 'exp_cei_1000_bar.png'
fig.savefig(out_path, dpi=300, bbox_inches='tight')
plt.close(fig)
print(f'Saved to {out_path}')
