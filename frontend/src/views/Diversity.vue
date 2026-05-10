<template>
  <div class="diversity-analysis">
    <el-card class="visual-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span>隐空间维度可视化 (PCA)</span>
            <el-tag type="info" class="ml-10">384 维 → 2 维投影</el-tag>
          </div>
          <div class="header-right">
            <el-select v-model="filterStatus" placeholder="筛选状态" clearable size="small" style="width: 140px">
              <el-option label="通过" value="Success" />
              <el-option label="崩溃" value="Crash" />
              <el-option label="超时" value="Timeout" />
            </el-select>
            <el-button @click="fetchData" :loading="loading" circle bg>
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
        </div>
      </template>

      <div class="main-content">
        <div ref="scatterChartRef" class="scatter-box"></div>
        
        <!-- Detail Panel (Fixed or Overlay) -->
        <transition name="slide-fade">
          <div v-if="selectedPoint" class="detail-panel glass-panel">
            <div class="panel-header">
              <h3>用例详情</h3>
              <el-button link @click="selectedPoint = null">
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
            <div class="panel-body">
              <div class="detail-item">
                <span class="label">用例 ID:</span>
                <span class="value">{{ selectedPoint.case_uid }}</span>
              </div>
              <div class="detail-item">
                <span class="label">执行状态:</span>
                <el-tag :type="getStatusType(selectedPoint.status)" size="small">
                  {{ selectedPoint.status }}
                </el-tag>
              </div>
              <div class="detail-item">
                <span class="label">边界覆盖率:</span>
                <span class="value">{{ selectedPoint.edge_coverage }}</span>
              </div>
              <div class="detail-item" v-if="selectedPoint.error_message">
                <span class="label">错误信息:</span>
                <div class="error-text">{{ selectedPoint.error_message }}</div>
              </div>
              <div class="detail-item">
                <span class="label">输入参数:</span>
                <pre class="json-text">{{ JSON.stringify(selectedPoint.parameters, null, 2) }}</pre>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </el-card>

    <!-- Analysis Summary -->
    <el-row :gutter="20" class="mt-20">
      <el-col :span="8">
        <el-card class="summary-card">
          <template #header>聚类分析挖掘</template>
          <p class="summary-text">
            测试用例基于执行日志和模型结构的语义相似度进行聚类。
            边缘区域的簇通常代表极端的变异场景。
          </p>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card class="summary-card">
          <template #header>特征显著性</template>
          <div class="feature-tags">
            <el-check-tag checked>Conv2d</el-check-tag>
            <el-check-tag class="ml-10">OOM</el-check-tag>
            <el-check-tag class="ml-10">Shape Mismatch</el-check-tag>
            <el-check-tag class="ml-10">ResNet</el-check-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { Refresh, Close } from '@element-plus/icons-vue'
// import api from '../api'

const scatterChartRef = ref<HTMLElement | null>(null)
let scatterChart: echarts.ECharts | null = null
const loading = ref(false)
const filterStatus = ref('')
const selectedPoint = ref<any>(null)

const getStatusType = (status: string) => {
  switch(status) {
    case 'Success': return 'success'
    case 'Crash': return 'danger'
    case 'Timeout': return 'warning'
    default: return 'info'
  }
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
  loading.value = true
  try {
    // In a real app, we'd have an endpoint to get all cases with their vis_x/vis_y
    // For now, since we already have the MySQL table, 
    // we'll assume the Java backend would provide this.
    // We'll mock it based on the data structure in storage.
    
    // Mocking 50 data points for visualization
    const mockData = []
    const statuses = ['Success', 'Crash', 'Timeout']
    for (let i = 0; i < 50; i++) {
      const status = statuses[Math.floor(Math.random() * statuses.length)]
      mockData.push({
        case_uid: `case_fuzz_${Math.random().toString(16).slice(2, 6)}`,
        status: status,
        vis_x: (Math.random() * 2 - 1).toFixed(4),
        vis_y: (Math.random() * 2 - 1).toFixed(4),
        edge_coverage: Math.floor(Math.random() * 5000),
        error_message: status !== 'Success' ? 'RuntimeError: Some error context here...' : null,
        parameters: { model: 'resnet50', mutation: 'random' }
      })
    }
    
    updateChart(mockData)
  } finally {
    loading.value = false
  }
}

const updateChart = (data: any[]) => {
  if (!scatterChart) return

  const filteredData = filterStatus.value 
    ? data.filter(item => item.status === filterStatus.value)
    : data

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 20, right: 40, bottom: 40, left: 40 },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        return `<div style="font-weight:600">${params.data.case_uid}</div>
                <div style="color:${getStatusColor(params.data.status)}">${params.data.status}</div>`
      }
    },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLine: { show: false },
      axisLabel: { color: '#64748b' }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      axisLine: { show: false },
      axisLabel: { color: '#64748b' }
    },
    series: [{
      type: 'scatter',
      data: filteredData.map(item => ({
        value: [item.vis_x, item.vis_y],
        ...item
      })),
      symbolSize: 12,
      itemStyle: {
        color: (params: any) => getStatusColor(params.data.status),
        opacity: 0.8,
        shadowBlur: 10,
        shadowColor: 'rgba(0,0,0,0.5)'
      },
      emphasis: {
        itemStyle: {
          symbolSize: 18,
          opacity: 1,
          borderWidth: 2,
          borderColor: '#fff'
        }
      }
    }]
  }

  scatterChart.setOption(option)
}

const initChart = () => {
  if (scatterChartRef.value) {
    scatterChart = echarts.init(scatterChartRef.value, 'dark')
    scatterChart.on('click', (params: any) => {
      selectedPoint.value = params.data
    })
    fetchData()
  }
}

watch(filterStatus, () => fetchData())

onMounted(() => {
  initChart()
  window.addEventListener('resize', () => scatterChart?.resize())
})

onUnmounted(() => {
  window.removeEventListener('resize', () => scatterChart?.resize())
})
</script>

<style scoped>
.diversity-analysis {
  animation: fadeIn 0.5s ease-out;
}

.visual-card {
  height: 650px;
  position: relative;
}

.main-content {
  position: relative;
  height: 550px;
}

.scatter-box {
  width: 100%;
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.ml-10 { margin-left: 10px; }
.mt-20 { margin-top: 20px; }

/* Detail Panel Overlay */
.detail-panel {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 320px;
  max-height: 500px;
  z-index: 10;
  padding: 20px;
  overflow-y: auto;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.panel-header h3 {
  font-size: 1.125rem;
  font-weight: 600;
}

.detail-item {
  margin-bottom: 16px;
}

.detail-item .label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.detail-item .value {
  font-size: 14px;
  word-break: break-all;
}

.error-text {
  font-family: monospace;
  font-size: 12px;
  color: #f43f5e;
  padding: 8px;
  background: rgba(244, 63, 94, 0.1);
  border-radius: 4px;
  border: 1px solid rgba(244, 63, 94, 0.2);
}

.json-text {
  font-size: 12px;
  background: rgba(0, 0, 0, 0.2);
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
  color: #94a3b8;
}

.summary-text {
  color: var(--text-secondary);
  line-height: 1.6;
  font-size: 14px;
}

.feature-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* Transitions */
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}
.slide-fade-leave-active {
  transition: all 0.2s cubic-bezier(1, 0.5, 0.8, 1);
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateX(20px);
  opacity: 0;
}
</style>
