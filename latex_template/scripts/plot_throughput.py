import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from pathlib import Path

matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

batch_sizes = np.array([1, 5, 10, 20, 50, 100, 200])
throughput = np.array([4.8, 16.2, 24.7, 33.5, 41.6, 44.1, 45.3])

fig, ax = plt.subplots(figsize=(8.4, 4.8))

line_color = '#2563EB'
fill_color = '#93C5FD'
point_color = '#1D4ED8'

ax.plot(
    batch_sizes,
    throughput,
    color=line_color,
    linewidth=2.6,
    marker='o',
    markersize=7,
    markerfacecolor='white',
    markeredgecolor=point_color,
    markeredgewidth=2,
)
ax.fill_between(batch_sizes, throughput, 0, color=fill_color, alpha=0.24)

ax.axvspan(1, 50, color='#DCFCE7', alpha=0.35)
ax.axvspan(100, 200, color='#FEF3C7', alpha=0.35)
ax.axhline(50, color='#EF4444', linestyle='--', linewidth=1.5, alpha=0.8)

ax.annotate(
    '线性增长区间\n1→50条/批',
    xy=(25, 34),
    xytext=(30, 15),
    fontsize=10,
    ha='center',
    color='#166534',
    arrowprops=dict(arrowstyle='->', color='#16A34A', lw=1.2),
    bbox=dict(boxstyle='round,pad=0.28', fc='white', ec='#86EFAC', alpha=0.95),
)

ax.annotate(
    '吞吐趋于饱和\n45.3条/秒',
    xy=(200, 45.3),
    xytext=(140, 31),
    fontsize=10,
    ha='center',
    color='#92400E',
    arrowprops=dict(arrowstyle='->', color='#F59E0B', lw=1.2),
    bbox=dict(boxstyle='round,pad=0.28', fc='white', ec='#FCD34D', alpha=0.95),
)

ax.text(
    78,
    50.8,
    '原型系统综合写入吞吐上限约50条/秒',
    fontsize=9.5,
    color='#B91C1C',
    va='bottom',
)

for x, y in zip(batch_sizes, throughput):
    ax.text(x, y + 1.3, f'{y:.1f}', ha='center', va='bottom', fontsize=9, color='#111827')

ax.set_title('不同批量大小下的写入吞吐量曲线', fontsize=15, fontweight='bold', pad=14)
ax.set_xlabel('批量大小（条/批）', fontsize=12)
ax.set_ylabel('写入吞吐量（条/秒）', fontsize=12)
ax.set_xlim(0, 210)
ax.set_ylim(0, 58)
ax.set_xticks(batch_sizes)
ax.set_yticks(np.arange(0, 59, 10))
ax.grid(axis='y', linestyle='--', alpha=0.32)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

fig.tight_layout()

out_path = Path(__file__).resolve().parents[1] / 'figure' / 'exp_throughput.png'
fig.savefig(out_path, dpi=300, bbox_inches='tight')
plt.close(fig)
print(f'Saved to {out_path}')
