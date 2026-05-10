import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'SimHei'
matplotlib.rcParams['axes.unicode_minus'] = False

# --- 数据点 ---
prune_pct = np.array([0, 10, 20, 30, 40, 50, 60, 70, 80, 90])

# 覆盖率：前段缓降，60%后加速下降
coverage_pct = np.array([100.0, 99.5, 98.7, 97.9, 96.8, 93.4, 88.1, 81.2, 63.5, 38.7])

# 耗时：前段陡降，后段趋缓
time_sec = np.array([487.3, 421.6, 348.2, 267.5, 194.9, 153.2, 118.7, 89.4, 61.2, 28.5])

# 插值平滑
from scipy.interpolate import make_interp_spline
x_smooth = np.linspace(0, 90, 300)
cov_spline = make_interp_spline(prune_pct, coverage_pct, k=3)
time_spline = make_interp_spline(prune_pct, time_sec, k=3)
cov_smooth = cov_spline(x_smooth)
time_smooth = time_spline(x_smooth)

# --- 绘图 ---
fig, ax1 = plt.subplots(figsize=(8, 4.8))

color_cov = '#2563EB'
color_time = '#DC2626'

# 左轴：覆盖率
ax1.set_xlabel('剔除百分位 (%)', fontsize=13)
ax1.set_ylabel('累计边覆盖率 (%)', color=color_cov, fontsize=13)
line1, = ax1.plot(x_smooth, cov_smooth, color=color_cov, linewidth=2.2, label='累计边覆盖率')
ax1.scatter(prune_pct, coverage_pct, color=color_cov, s=40, zorder=5, edgecolors='white', linewidths=0.8)
ax1.tick_params(axis='y', labelcolor=color_cov)
ax1.set_ylim(25, 105)
ax1.set_xlim(-2, 92)

# 右轴：耗时
ax2 = ax1.twinx()
ax2.set_ylabel('累计执行耗时 (s)', color=color_time, fontsize=13)
line2, = ax2.plot(x_smooth, time_smooth, color=color_time, linewidth=2.2, linestyle='--', label='累计执行耗时')
ax2.scatter(prune_pct, time_sec, color=color_time, s=40, zorder=5, marker='s', edgecolors='white', linewidths=0.8)
ax2.tick_params(axis='y', labelcolor=color_time)
ax2.set_ylim(0, 540)

# 标注40%工作点
ax1.axvline(x=40, color='#6B7280', linestyle=':', linewidth=1.2, alpha=0.7)
ax1.annotate('推荐工作点\n(剔除40%)',
             xy=(40, 96.8), xytext=(54, 99),
             fontsize=10, color='#374151',
             arrowprops=dict(arrowstyle='->', color='#6B7280', lw=1.2),
             bbox=dict(boxstyle='round,pad=0.3', fc='#F3F4F6', ec='#D1D5DB', alpha=0.9))

# 标注关键数值
ax1.annotate('96.8%', xy=(40, 96.8), xytext=(28, 91),
             fontsize=9, color=color_cov, fontweight='bold',
             arrowprops=dict(arrowstyle='->', color=color_cov, lw=0.8))
ax2.annotate('194.9s', xy=(40, 194.9), xytext=(50, 260),
             fontsize=9, color=color_time, fontweight='bold',
             arrowprops=dict(arrowstyle='->', color=color_time, lw=0.8))

# 图例
lines = [line1, line2]
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='center right', fontsize=10, framealpha=0.9)

ax1.grid(True, alpha=0.25, linestyle='-')
fig.tight_layout()

out_path = r'c:\Users\gjj\Desktop\graduation-design-main\latex_template\figure\exp_cei_curve.png'
fig.savefig(out_path, dpi=300, bbox_inches='tight')
print(f'Saved to {out_path}')
plt.close()
