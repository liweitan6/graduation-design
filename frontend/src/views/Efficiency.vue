<template>
  <div class="efficiency-page">
    <!-- Summary Cards -->
    <el-row :gutter="20" class="summary-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-number">{{ summary.total_cases }}</div>
          <div class="stat-label">总用例数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card avg">
          <div class="stat-number">{{ summary.avg_cei }}</div>
          <div class="stat-label">平均 CEI</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card high">
          <div class="stat-number">{{ summary.max_cei }}</div>
          <div class="stat-label">最高 CEI</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card low">
          <div class="stat-number">{{ summary.min_cei }}</div>
          <div class="stat-label">最低 CEI</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Scatter Chart: Complexity vs Coverage -->
    <el-card class="chart-card">
      <template #header>
        <div class="card-header">
          <span>用例复杂度 vs. 边界覆盖率</span>
          <el-tag type="info">气泡大小 = CEI 指数</el-tag>
        </div>
      </template>
      <div ref="scatterRef" class="chart-box"></div>
    </el-card>

    <!-- CEI Ranking Table -->
    <el-row :gutter="20" class="mt-20">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span style="color: #10b981;">🏆 高效能用例排行 (高 CEI)</span>
          </template>
          <el-table :data="topCases" size="small">
            <el-table-column prop="case_uid" label="用例" min-width="160">
              <template #default="{ row }">
                <code class="uid">{{ row.case_uid }}</code>
              </template>
            </el-table-column>
            <el-table-column prop="cei" label="CEI" width="80" sortable />
            <el-table-column prop="edge_coverage" label="覆盖率" width="100" />
            <el-table-column prop="complexity" label="复杂度" width="100" />
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 'Success' ? 'success' : (row.status === 'Crash' ? 'danger' : 'warning')" size="small">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <span style="color: #f59e0b;">📉 低效能用例排行 (低 CEI)</span>
          </template>
          <el-table :data="bottomCases" size="small">
            <el-table-column prop="case_uid" label="用例" min-width="160">
              <template #default="{ row }">
                <code class="uid">{{ row.case_uid }}</code>
              </template>
            </el-table-column>
            <el-table-column prop="cei" label="CEI" width="80" sortable />
            <el-table-column prop="edge_coverage" label="覆盖率" width="100" />
            <el-table-column prop="complexity" label="复杂度" width="100" />
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 'Success' ? 'success' : (row.status === 'Crash' ? 'danger' : 'warning')" size="small">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- Methodology Card -->
    <el-card class="mt-20 method-card">
      <template #header><span>技术原理：覆盖效能指数 (CEI)</span></template>
      <div class="method-content">
        <div class="formula">
          <strong>CEI = 边界覆盖率 / 复杂度</strong>
        </div>
        <p>其中 <code>复杂度 = Σ(算子权重 × 出现次数)</code>，权重比例基于计算开销：</p>
        <div class="weight-tags">
          <el-tag v-for="(w, op) in sampleWeights" :key="op" :type="w > 3 ? 'danger' : (w > 1 ? 'warning' : 'info')" size="small" class="weight-tag">
            {{ op }} = {{ w }}
          </el-tag>
        </div>
        <p class="insight">高 CEI 表示用较为简单的模型结构覆盖了更多的代码边界，此类用例在高效回归测试中具有极高价值。</p>
      </div>
    </el-card>
    <!-- CEI 智能清退控制卡片 -->
    <el-card class="mt-20 prune-card">
      <template #header>
        <div class="card-header">
          <span>🧪 CEI 智能筛选与清退</span>
          <div>
            <el-button type="primary" size="small" @click="handlePrune(true)" :loading="pruning">
              预览清退方案
            </el-button>
            <el-button type="danger" size="small" @click="confirmPrune" :loading="pruning" :disabled="!pruneResult">
              执行清退
            </el-button>
          </div>
        </div>
      </template>
      <div class="prune-desc">
        <p>系统将自动计算 CEI 阈值（默认为中位数的 50%），将低于该阈值的低效能用例标记为候选清退对象。点击「预览」先查看影响范围，确认后再点击「执行」。</p>
      </div>
      <!-- 预览结果展示 -->
      <div v-if="pruneResult" class="prune-result">
        <el-row :gutter="16" class="prune-stats">
          <el-col :span="6">
            <div class="prune-stat-item">
              <div class="prune-stat-val">{{ pruneResult.cei_threshold }}</div>
              <div class="prune-stat-label">CEI 阈值 ({{ pruneResult.auto_threshold_source }})</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="prune-stat-item danger">
              <div class="prune-stat-val">{{ pruneResult.summary?.to_prune }}</div>
              <div class="prune-stat-label">待清退用例数</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="prune-stat-item success">
              <div class="prune-stat-val">{{ pruneResult.summary?.to_keep }}</div>
              <div class="prune-stat-label">保留用例数</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="prune-stat-item">
              <div class="prune-stat-val">{{ pruneResult.efficiency_improvement?.coverage_retained }}</div>
              <div class="prune-stat-label">覆盖率保留比</div>
            </div>
          </el-col>
        </el-row>
        <el-row :gutter="16" class="prune-improvement">
          <el-col :span="12">
            <div class="prune-stat-item">
              <div class="prune-stat-val" style="color: #94a3b8;">{{ pruneResult.efficiency_improvement?.avg_cei_before }}</div>
              <div class="prune-stat-label">清退前平均 CEI</div>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="prune-stat-item success">
              <div class="prune-stat-val">{{ pruneResult.efficiency_improvement?.avg_cei_after }}</div>
              <div class="prune-stat-label">清退后平均 CEI ✨</div>
            </div>
          </el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { getEfficiencyAnalysis, pruneByEfficiency } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const scatterRef = ref<HTMLElement | null>(null)
let scatterChart: echarts.ECharts | null = null

const summary = ref<any>({})
const topCases = ref<any[]>([])
const bottomCases = ref<any[]>([])
const pruning = ref(false)
const pruneResult = ref<any>(null)

const sampleWeights: Record<string, number> = {
  'Conv2d': 3, 'LSTM': 4, 'TransformerEncoderLayer': 5,
  'Linear': 2, 'ReLU': 1, 'Add': 1, 'BatchNorm2d': 1
}

const getStatusColor = (status: string) => {
  switch(status) {
    case 'Success': return '#10b981'
    case 'Crash': return '#f43f5e'
    case 'Timeout': return '#f59e0b'
    default: return '#94a3b8'
  }
}

const fetchData = async () => {
  try {
    const res = await getEfficiencyAnalysis()
    const data = res.data
    summary.value = data.summary || {}
    topCases.value = (data.summary?.top_efficient || []).slice(0, 5)
    bottomCases.value = (data.summary?.least_efficient || []).slice(0, 5)
    renderChart(data.cases || [])
  } catch (err) {
    console.error('Failed to fetch efficiency data:', err)
  }
}

const renderChart = (cases: any[]) => {
  if (!scatterChart) return

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      formatter: (params: any) => {
        const d = params.data
        return `<strong>${d.case_uid}</strong><br/>
                状态: ${d.status}<br/>
                复杂度: ${d.complexity}<br/>
                覆盖率: ${d.edge_coverage}<br/>
                CEI 指数: ${d.cei}`
      }
    },
    grid: { top: 40, right: 40, bottom: 60, left: 60 },
    xAxis: {
      name: '复杂度 (算子加权总和)',
      nameLocation: 'middle', nameGap: 35,
      nameTextStyle: { color: '#94a3b8' },
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLabel: { color: '#94a3b8' }
    },
    yAxis: {
      name: '边界覆盖率',
      nameLocation: 'middle', nameGap: 45,
      nameTextStyle: { color: '#94a3b8' },
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLabel: { color: '#94a3b8' }
    },
    series: [{
      type: 'scatter',
      data: cases.map(c => ({
        value: [c.complexity, c.edge_coverage],
        symbolSize: Math.max(8, Math.min(40, c.cei / 20)),
        ...c
      })),
      itemStyle: {
        color: (params: any) => getStatusColor(params.data.status),
        opacity: 0.85,
        shadowBlur: 8,
        shadowColor: 'rgba(0,0,0,0.4)'
      },
      emphasis: {
        itemStyle: { borderWidth: 2, borderColor: '#fff' }
      }
    }]
  }
  scatterChart.setOption(option)
}

onMounted(() => {
  if (scatterRef.value) {
    scatterChart = echarts.init(scatterRef.value, 'dark')
  }
  fetchData()
  window.addEventListener('resize', () => scatterChart?.resize())
})

onUnmounted(() => {
  window.removeEventListener('resize', () => scatterChart?.resize())
})

const handlePrune = async (dryRun: boolean) => {
  pruning.value = true
  try {
    const res = await pruneByEfficiency(0, dryRun)
    pruneResult.value = res.data
    if (dryRun) {
      ElMessage.info(`预览完成：${res.data.summary?.to_prune} 条用例低于 CEI 阈值 ${res.data.cei_threshold}`)
    } else {
      ElMessage.success(`已清退 ${res.data.summary?.actually_deleted} 条低效能用例`)
      fetchData()
    }
  } catch (err) {
    ElMessage.error('CEI 分析失败，请检查 Python 服务')
    console.error(err)
  } finally {
    pruning.value = false
  }
}

const confirmPrune = () => {
  if (!pruneResult.value) return
  ElMessageBox.confirm(
    `确认清退 ${pruneResult.value.summary?.to_prune} 条 CEI 低于 ${pruneResult.value.cei_threshold} 的低效能用例？此操作不可撤销。`,
    '确认清退',
    { confirmButtonText: '确认清退', cancelButtonText: '取消', type: 'warning' }
  ).then(() => {
    handlePrune(false)
  }).catch(() => {
    ElMessage.info('已取消')
  })
}
</script>

<style scoped>
.efficiency-page {
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.summary-row { margin-bottom: 20px; }
.mt-20 { margin-top: 20px; }

.stat-card { text-align: center; padding: 10px 0; }
.stat-number { font-size: 2rem; font-weight: 700; color: #f8fafc; }
.stat-card.avg .stat-number { color: #6366f1; }
.stat-card.high .stat-number { color: #10b981; }
.stat-card.low .stat-number { color: #f59e0b; }
.stat-label { font-size: 13px; color: #94a3b8; margin-top: 4px; }

.chart-card { margin-bottom: 20px; }
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.chart-box { width: 100%; height: 450px; }

.uid { color: #818cf8; font-family: 'Fira Code', monospace; font-size: 13px; }

.method-card .method-content { line-height: 1.8; color: #cbd5e1; }
.formula {
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 8px;
  padding: 16px;
  font-size: 18px;
  text-align: center;
  margin-bottom: 16px;
  color: #a5b4fc;
}
.weight-tags { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }
.weight-tag { font-family: 'Fira Code', monospace; }
.insight { color: #94a3b8; font-style: italic; margin-top: 12px; }

:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: #1e293b;
  --el-table-border-color: #334155;
  --el-table-text-color: #f8fafc;
}

.prune-card .prune-desc {
  color: #94a3b8;
  font-size: 13px;
  margin-bottom: 16px;
  line-height: 1.6;
}

.prune-result {
  margin-top: 12px;
}

.prune-stats {
  margin-bottom: 16px;
}

.prune-stat-item {
  text-align: center;
  padding: 12px 8px;
  background: rgba(255,255,255,0.03);
  border-radius: 8px;
  border: 1px solid #334155;
}

.prune-stat-item.danger .prune-stat-val { color: #f43f5e; }
.prune-stat-item.success .prune-stat-val { color: #10b981; }

.prune-stat-val {
  font-size: 1.5rem;
  font-weight: 700;
  color: #f8fafc;
}

.prune-stat-label {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.prune-improvement {
  margin-top: 12px;
  padding: 12px;
  background: rgba(99, 102, 241, 0.05);
  border-radius: 8px;
}
</style>
