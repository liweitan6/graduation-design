import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
import os

# Set professional academic styling
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')

# Programmatic bulletproof Chinese font selection & registration for Windows/cross-platform
plt.rcParams['font.family'] = 'sans-serif'

# List standard Windows Chinese font file paths
windows_fonts = [
    'C:/Windows/Fonts/simhei.ttf',   # SimHei (TTF - Extremely stable, parses cleanly as 'SimHei')
    'C:/Windows/Fonts/msyh.ttc',    # Microsoft YaHei
    'C:/Windows/Fonts/simsun.ttc'    # SimSun
]

font_loaded = False
for fpath in windows_fonts:
    if os.path.exists(fpath):
        try:
            font_manager.fontManager.addfont(fpath)
            prop = font_manager.FontProperties(fname=fpath)
            plt.rcParams['font.sans-serif'] = [prop.get_name()] + ['DejaVu Sans', 'Arial', 'Helvetica']
            font_loaded = True
            break
        except Exception:
            pass

if not font_loaded:
    # Fallback to dynamic system scan
    system_chinese_fonts = [f.name for f in font_manager.fontManager.ttflist 
                            if any(keyword in f.name for keyword in ['YaHei', 'Hei', 'SimHei', 'SimSun', 'Song', 'STHeiti', 'STSong'])]
    if system_chinese_fonts:
        plt.rcParams['font.sans-serif'] = [system_chinese_fonts[0]] + ['DejaVu Sans', 'Arial', 'Helvetica']
    else:
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'Arial']

plt.rcParams['axes.unicode_minus'] = False

# Custom colors for a high-end academic feel
COLOR_PRIMARY = '#1f4e79'   # Royal Academic Blue
COLOR_SECONDARY = '#d9534f' # Crimson Red
COLOR_SUCCESS = '#2ca02c'   # Muted Green
COLOR_MUTED = '#7f8c8d'     # Slate Gray
COLOR_LIGHT_BG = '#f4f6f7'  # Light Gray-Blue

# ----------------------------------------------------
# CHART 1: Known Constraint Recall & False Positives (CHINESE)
# ----------------------------------------------------
fig, ax1 = plt.subplots(figsize=(8, 4.5), dpi=300)

categories = ['卷积空间约束\n(Conv Space)', 
              '转置卷积输出\n(TransConv Out)', 
              '分组卷积整除\n(GroupConv Div)', 
              '池化窗口约束\n(Pooling Window)', 
              '三变量空间坍缩\n(3-Var Collapse)']

x = np.arange(len(categories))
width = 0.35

# Plot Recall Rate on the Left Y-axis (Primary)
color_recall = COLOR_PRIMARY
rects1 = ax1.bar(x - width/2, [100]*5, width, label='目标约束召回率', color=color_recall, alpha=0.9, edgecolor='none')
ax1.set_ylabel('召回率 (Recall Rate %)', color=color_recall, fontsize=11)
ax1.set_ylim(0, 120)
ax1.tick_params(axis='y', labelcolor=color_recall)
ax1.set_title('Daikon 模块在已知目标约束下的召回与误报统计', fontsize=13, pad=15)

# Plot Accompanying False Positives on the Right Y-axis (Secondary)
ax2 = ax1.twinx()
color_fp = COLOR_SECONDARY
rects2 = ax2.bar(x + width/2, [0, 1, 0, 0, 2], width, label='伴随误报数', color=color_fp, alpha=0.85, edgecolor='none')
ax2.set_ylabel('伴随误报数 (条)', color=color_fp, fontsize=11)
ax2.set_ylim(0, 3)
ax2.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
ax2.tick_params(axis='y', labelcolor=color_fp)

# X-axis ticks
ax1.set_xticks(x)
ax1.set_xticklabels(categories, fontsize=9.5)
ax1.grid(True, linestyle='--', alpha=0.5)

# Add values above bars
def autolabel_left(rects):
    for rect in rects:
        height = rect.get_height()
        ax1.annotate(f'{height}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9.5, color=COLOR_PRIMARY, fontweight='bold')

def autolabel_right(rects):
    for rect in rects:
        height = rect.get_height()
        ax2.annotate(f'{height} 条',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9.5, color=COLOR_SECONDARY)

autolabel_left(rects1)
autolabel_right(rects2)

# Legend setup - placed horizontally below the plot to prevent any overlap with the 100% bars
lines, labels = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines + lines2, labels + labels2, loc='upper center', bbox_to_anchor=(0.5, -0.18), 
           ncol=2, frameon=True, facecolor='white', framealpha=0.9, fontsize=9.5)

fig.tight_layout()
plt.savefig('../latex_template/figure/ppt_daikon_recall.png', bbox_inches='tight', dpi=300)
plt.close()

# ----------------------------------------------------
# CHART 2: Validation Sample Correctness (Validation Accuracy) - CHINESE
# ----------------------------------------------------
fig2, ax = plt.subplots(figsize=(8, 4.5), dpi=300)

sample_types = ['正样例 $S^+$\n(期望运行成功 - 满足约束)', 
                '反样例 $S^-$\n(期望触发崩溃 - 违反约束)']

# We plot the two bars closer together on the X-axis (centered at 0.35 and 0.65)
# to remove empty grouped-bar spaces and bring them visually close.
x_centers = [0.35, 0.65]
bar_width = 0.14

# Simple high-contrast bars
rects = ax.bar(x_centers, [9, 9], bar_width, color=[COLOR_SUCCESS, COLOR_SECONDARY], edgecolor='none', alpha=0.9)

ax.set_ylabel('物理跑测样例数量 (条)', fontsize=11)
ax.set_ylim(0, 11.5)  # Adjusted limit as the text card is removed
ax.set_xlim(0, 1)     # Centers the bars perfectly
ax.set_title('约束驱动验证样例在隔离沙箱中的真实跑测结果', fontsize=13, pad=15)
ax.set_xticks(x_centers)
ax.set_xticklabels(sample_types, fontsize=10)
ax.grid(True, linestyle='--', alpha=0.5)

# Label values above the bars
for rect in rects:
    height = rect.get_height()
    ax.annotate(f'{height} 例\n(100%)',
                xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 4),
                textcoords="offset points",
                ha='center', va='bottom', fontsize=9.5, fontweight='bold')

# Legend setup - placed horizontally below the plot to avoid overlapping
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor=COLOR_SUCCESS, alpha=0.9, label='物理运行: 成功 (Success)'),
    Patch(facecolor=COLOR_SECONDARY, alpha=0.9, label='物理运行: 触发预期崩溃 (Expected Crash)')
]
ax.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, -0.18), 
          ncol=2, frameon=True, facecolor='white', framealpha=0.9, fontsize=9.5)

fig2.tight_layout()
plt.savefig('../latex_template/figure/ppt_daikon_validation.png', bbox_inches='tight', dpi=300)
plt.close()

print("Chinese academic-grade charts successfully generated and saved to latex_template/figure/ folder!")
