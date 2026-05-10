<template>
  <div class="coverage-page">
    <!-- Summary Cards -->
    <el-row :gutter="20" class="summary-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-number">{{ summary.total_known_operators }}</div>
          <div class="stat-label">已知算子总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card covered">
          <div class="stat-number">{{ summary.covered_operators }}</div>
          <div class="stat-label">已覆盖算子数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card rate">
          <div class="stat-number">{{ summary.coverage_rate }}%</div>
          <div class="stat-label">总覆盖率</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card gap">
          <div class="stat-number">{{ summary.total_pairs_untested }}</div>
          <div class="stat-label">未测试算子对</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Heatmap -->
    <el-card class="heatmap-card">
      <template #header>
        <div class="card-header">
          <span>算子对覆盖热力图</span>
          <el-tag type="info">颜色越亮表示测试次数越多</el-tag>
        </div>
      </template>
      <div ref="heatmapRef" class="heatmap-box"></div>
    </el-card>

    <!-- Operator Coverage Table -->
    <el-row :gutter="20" class="mt-20">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>各算子覆盖状态</span>
          </template>
          <el-table :data="operatorCoverage" max-height="400" size="small">
            <el-table-column prop="operator" label="算子名称" min-width="140">
              <template #default="{ row }">
                <code class="op-name">{{ row.operator }}</code>
              </template>
            </el-table-column>
            <el-table-column prop="total_cases" label="测试次数" width="100" sortable />
            <el-table-column prop="crash_cases" label="崩溃次数" width="90" sortable />
            <el-table-column prop="covered" label="覆盖状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.covered ? 'success' : 'danger'" size="small">
                  {{ row.covered ? '已覆盖' : '存在缺口' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>未覆盖算子对 (TOP 20)</span>
              <el-button type="warning" size="small" @click="handleAutoGenerate" :loading="generating">
                🤖 一键 AI 补盲
              </el-button>
            </div>
          </template>
          <el-table :data="uncoveredPairs.slice(0, 20)" max-height="400" size="small">
            <el-table-column label="起始算子" min-width="120">
              <template #default="{ row }">
                <code class="op-name">{{ row.from }}</code>
              </template>
            </el-table-column>
            <el-table-column label="" width="40">
              <template #default>→</template>
            </el-table-column>
            <el-table-column label="终止算子" min-width="120">
              <template #default="{ row }">
                <code class="op-name">{{ row.to }}</code>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- AI 补盲结果弹窗 -->
    <el-dialog v-model="showGenDialog" title="AI 定向补盲生成结果" width="750px" top="5vh">
      <el-alert v-if="genResult" :title="genResult.message" type="success" :closable="false" show-icon class="mb-16" />
      <div v-if="genResult?.uncovered_pairs_used" class="mb-16">
        <h4 style="color: #f8fafc; margin-bottom: 8px;">本次补盲目标算子对：</h4>
        <el-tag v-for="(p, i) in genResult.uncovered_pairs_used" :key="i" class="pair-tag" type="warning" size="small">
          {{ p.from }} → {{ p.to }}
        </el-tag>
      </div>
      <div v-if="genResult?.generated_cases" class="gen-content">
        <h4 style="color: #f8fafc; margin-bottom: 8px;">生成的测试用例建议：</h4>
        <pre class="gen-code">{{ genResult.generated_cases }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { getCoverageGaps, autoGenerateFromGaps } from '../api'
import { ElMessage } from 'element-plus'

const heatmapRef = ref<HTMLElement | null>(null)
let heatmapChart: echarts.ECharts | null = null

const summary = ref<any>({})
const operatorCoverage = ref<any[]>([])
const uncoveredPairs = ref<any[]>([])
const generating = ref(false)
const showGenDialog = ref(false)
const genResult = ref<any>(null)

const fetchData = async () => {
  try {
    const res = await getCoverageGaps()
    const data = res.data
    summary.value = data.summary || {}
    operatorCoverage.value = data.operator_coverage || []
    uncoveredPairs.value = data.uncovered_pairs || []
    renderHeatmap(data.heatmap_operators || [], data.heatmap_data || [])
  } catch (err) {
    console.error('Failed to fetch coverage gaps:', err)
  }
}

const renderHeatmap = (operators: string[], data: number[][]) => {
  if (!heatmapChart) return
  const maxVal = Math.max(...data.map(d => d[2] || 0), 1)
  
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        return `<strong>${operators[params.data[0]]}</strong> → <strong>${operators[params.data[1]]}</strong><br/>测试次数: ${params.data[2]}`
      }
    },
    grid: { top: 80, bottom: 30, left: 140, right: 30 },
    xAxis: {
      type: 'category',
      data: operators,
      axisLabel: { rotate: 45, color: '#94a3b8', fontSize: 10 },
      splitArea: { show: true, areaStyle: { color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.04)'] } }
    },
    yAxis: {
      type: 'category',
      data: operators,
      axisLabel: { color: '#94a3b8', fontSize: 10 },
      splitArea: { show: true, areaStyle: { color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.04)'] } }
    },
    visualMap: {
      min: 0, max: maxVal,
      calculable: true,
      orient: 'horizontal',
      left: 'center', top: 10,
      inRange: {
        color: ['#1e293b', '#312e81', '#4338ca', '#6366f1', '#818cf8', '#a5b4fc']
      },
      textStyle: { color: '#94a3b8' }
    },
    series: [{
      type: 'heatmap',
      data: data,
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' }
      }
    }]
  }
  heatmapChart.setOption(option)
}

onMounted(() => {
  if (heatmapRef.value) {
    heatmapChart = echarts.init(heatmapRef.value, 'dark')
  }
  fetchData()
  window.addEventListener('resize', () => heatmapChart?.resize())
})

onUnmounted(() => {
  window.removeEventListener('resize', () => heatmapChart?.resize())
})

const handleAutoGenerate = async () => {
  generating.value = true
  try {
    const res = await autoGenerateFromGaps(5)
    genResult.value = res.data
    showGenDialog.value = true
    ElMessage.success(res.data.message || '补盲建议已生成')
  } catch (err) {
    ElMessage.error('AI 补盲生成失败，请检查 Python 服务是否运行')
    console.error(err)
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
.coverage-page {
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.summary-row { margin-bottom: 20px; }
.mt-20 { margin-top: 20px; }

.stat-card {
  text-align: center;
  padding: 10px 0;
}

.stat-number {
  font-size: 2rem;
  font-weight: 700;
  color: #f8fafc;
}

.stat-card.covered .stat-number { color: #10b981; }
.stat-card.rate .stat-number { color: #6366f1; }
.stat-card.gap .stat-number { color: #f59e0b; }

.stat-label {
  font-size: 13px;
  color: #94a3b8;
  margin-top: 4px;
}

.heatmap-card { margin-bottom: 20px; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.heatmap-box {
  width: 100%;
  height: 500px;
}

.op-name {
  color: #818cf8;
  font-family: 'Fira Code', monospace;
  font-size: 13px;
}

:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: #1e293b;
  --el-table-border-color: #334155;
  --el-table-text-color: #f8fafc;
}

.mb-16 { margin-bottom: 16px; }

.pair-tag {
  margin: 2px 4px;
  font-family: 'Fira Code', monospace;
}

.gen-content {
  max-height: 50vh;
  overflow-y: auto;
}

.gen-code {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 16px;
  color: #e2e8f0;
  font-family: 'Fira Code', monospace;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.6;
}
</style>
