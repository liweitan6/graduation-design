import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from pathlib import Path

matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

metrics = ['准确性', '可操作性', '幻觉抑制']
llm_raw = np.array([2.8, 2.3, 3.6])
rag_raw = np.array([4.2, 4.0, 1.4])

# 原文中“幻觉程度”越低越好。为了让雷达图面积越大表示质量越高，
# 将其转换为“幻觉抑制”得分：6 - 幻觉程度。
llm = np.array([llm_raw[0], llm_raw[1], 6 - llm_raw[2]])
rag = np.array([rag_raw[0], rag_raw[1], 6 - rag_raw[2]])

angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False)
angles = np.concatenate([angles, [angles[0]]])
llm_closed = np.concatenate([llm, [llm[0]]])
rag_closed = np.concatenate([rag, [rag[0]]])

fig = plt.figure(figsize=(7.8, 5.8))
ax = fig.add_subplot(111, polar=True)

color_llm = '#EF4444'
color_rag = '#2563EB'

ax.plot(angles, llm_closed, color=color_llm, linewidth=2.2, marker='o', label='直接LLM输出')
ax.fill(angles, llm_closed, color=color_llm, alpha=0.18)
ax.plot(angles, rag_closed, color=color_rag, linewidth=2.2, marker='o', label='RAG辅助诊断')
ax.fill(angles, rag_closed, color=color_rag, alpha=0.22)

ax.set_theta_offset(np.pi / 2)
ax.set_theta_direction(-1)
ax.set_xticks(angles[:-1])
ax.set_xticklabels(metrics, fontsize=12)
ax.set_ylim(0, 5)
ax.set_yticks([1, 2, 3, 4, 5])
ax.set_yticklabels(['1', '2', '3', '4', '5'], fontsize=9, color='#6B7280')
ax.grid(True, linestyle='--', alpha=0.35)
ax.spines['polar'].set_color('#9CA3AF')

llm_offsets = [0.30, 0.28, -0.42]
rag_offsets = [0.30, 0.28, 0.24]

for angle, value, raw_value, metric, offset in zip(angles[:-1], llm, llm_raw, metrics, llm_offsets):
    text = f'{raw_value:.1f}' if '幻觉' not in metric else f'{raw_value:.1f}(程度)'
    ax.text(angle, value + offset, text, color=color_llm, ha='center', va='center', fontsize=10, fontweight='bold')

for angle, value, raw_value, metric, offset in zip(angles[:-1], rag, rag_raw, metrics, rag_offsets):
    text = f'{raw_value:.1f}' if '幻觉' not in metric else f'{raw_value:.1f}(程度)'
    ax.text(angle, value + offset, text, color=color_rag, ha='center', va='center', fontsize=10, fontweight='bold')

ax.set_title('RAG辅助诊断与直接LLM输出的质量对比', fontsize=15, fontweight='bold', pad=24)
ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.17), ncol=2, frameon=False, fontsize=11)

fig.text(
    0.5,
    0.045,
    '说明：原始“幻觉程度”为越低越好，雷达图中按“幻觉抑制 = 6 - 幻觉程度”绘制，标注保留原始幻觉程度得分。',
    ha='center',
    va='center',
    fontsize=9,
    color='#4B5563',
)

fig.tight_layout(rect=[0, 0.08, 1, 0.98])

out_path = Path(__file__).resolve().parents[1] / 'figure' / 'exp_rag_compare.png'
fig.savefig(out_path, dpi=300, bbox_inches='tight')
plt.close(fig)
print(f'Saved to {out_path}')
