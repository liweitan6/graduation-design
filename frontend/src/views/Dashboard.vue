<template>
  <div class="dashboard">
    <!-- Stat Cards -->
    <el-row :gutter="20">
      <el-col :span="6" v-for="item in stats" :key="item.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <div class="stat-label">{{ item.label }}</div>
              <div class="stat-value">{{ item.value }}</div>
            </div>
            <div class="stat-icon" :style="{ backgroundColor: item.color + '20', color: item.color }">
              <component :is="item.icon" />
            </div>
          </div>
          <div class="stat-footer">
            <span class="trend" :class="item.trend > 0 ? 'up' : 'down'">
              {{ item.trend > 0 ? '+' : '' }}{{ item.trend }}%
            </span>
            <span class="footer-text">较上一小时</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Charts Row -->
    <el-row :gutter="20" class="mt-20">
      <el-col :span="24">
        <el-card class="chart-card">
          <template #header>测试状态分布</template>
          <div ref="pieChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Table Row -->
    <el-row class="mt-20">
      <el-col :span="24">
        <el-card class="table-card">
          <template #header>
            <div class="card-header">
              <span>最近测试用例</span>
              <el-button type="primary" link @click="router.push('/cases')">查看全部</el-button>
            </div>
          </template>
          <el-table 
            :data="recentCases" 
            style="width: 100%" 
            v-loading="loading"
            @row-click="handleRowClick"
            row-class-name="clickable-row"
          >
            <el-table-column prop="case_uid" label="用例 ID" min-width="180" />
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="edge_coverage" label="边界覆盖率" sortBy="edge_coverage" />
            <el-table-column prop="execution_time" label="耗时 (秒)" />
            <el-table-column prop="created_at" label="创建时间" min-width="160" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- Case Detail Drawer -->
    <CaseDetailDrawer v-model="drawerVisible" :case-data="selectedCase" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { 
  Monitor, 
  CircleCheck, 
  CircleClose, 
  Timer 
} from '@element-plus/icons-vue'
import { getStatistics, getRecentCases } from '../api'
import CaseDetailDrawer from '../components/CaseDetailDrawer.vue'

const pieChartRef = ref<HTMLElement | null>(null)
let pieChart: echarts.ECharts | null = null

const loading = ref(false)
const router = useRouter()
const drawerVisible = ref(false)
const selectedCase = ref<any>(null)

const stats = ref([
  { label: '累计测试用例', value: '0', icon: Monitor, color: '#6366f1', trend: 0 },
  { label: '测试通过率', value: '0%', icon: CircleCheck, color: '#10b981', trend: 0 },
  { label: '异常崩溃总数', value: '0', icon: CircleClose, color: '#f43f5e', trend: 0 },
  { label: '平均执行耗时', value: '0s', icon: Timer, color: '#f59e0b', trend: 0 }
])

const recentCases = ref([])

const handleRowClick = (row: any) => {
  selectedCase.value = row
  drawerVisible.value = true
}

const getStatusType = (status: string) => {
  switch(status) {
    case 'Success': return 'success'
    case 'Crash': return 'danger'
    case 'Timeout': return 'warning'
    default: return 'info'
  }
}

const initCharts = () => {

  if (pieChartRef.value) {
    pieChart = echarts.init(pieChartRef.value, 'dark')
    pieChart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item' },
      legend: { bottom: '5%', left: 'center', textStyle: { color: '#cbd5e1' } },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#1e293b', borderWidth: 2 },
        label: { show: false },
        data: [
          { value: 942, name: '通过', itemStyle: { color: '#10b981' } },
          { value: 45, name: '崩溃', itemStyle: { color: '#f43f5e' } },
          { value: 13, name: '超时', itemStyle: { color: '#f59e0b' } }
        ]
      }]
    })
  }
}

const handleResize = () => {
  pieChart?.resize()
}

onMounted(async () => {
  initCharts()
  window.addEventListener('resize', handleResize)
  
  loading.value = true
  try {
    // 1. 获取统计数据 (Java 后端返回格式不同)
    const statRes = await getStatistics('总览')
    if (statRes.data) {
      const data = statRes.data
      if (stats.value[0]) stats.value[0].value = (data.total || 0).toLocaleString()
      if (stats.value[1]) stats.value[1].value = data.total > 0 
        ? ((data.successCount / data.total) * 100).toFixed(1) + '%' 
        : '0%'
      if (stats.value[2]) stats.value[2].value = (data.failCount || 0).toLocaleString()
      if (stats.value[3]) stats.value[3].value = (data.avgTime || 0) + 's'

      // 更新饼图
      if (pieChart) {
        pieChart.setOption({
          series: [{
            data: [
              { value: data.successCount || 0, name: '通过', itemStyle: { color: '#10b981' } },
              { value: data.failCount || 0, name: '失败', itemStyle: { color: '#f43f5e' } }
            ]
          }]
        })
      }
    }

    // 2. 获取最近用例
    const casesRes = await getRecentCases()
    if (casesRes.data) {
      // 保留原始字段，同时添加 snake_case 字段用于表格显示
      recentCases.value = casesRes.data.map((c: any) => ({
        ...c, // 保留原始字段 (caseUid, errorMessage, parameters 等)
        case_uid: c.caseUid,
        edge_coverage: c.edgeCoverage,
        execution_time: c.executionTime?.toFixed(3),
        created_at: c.createdAt || new Date().toISOString().slice(0, 19).replace('T', ' ')
      }))
    }

  } catch (err) {
    console.warn('Backend error:', err)
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.dashboard {
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.mt-20 { margin-top: 20px; }

.stat-card {
  border-left: 4px solid var(--primary-color);
  transition: transform 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-5px);
}

.stat-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label {
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  margin-top: 8px;
  color: var(--text-primary);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-footer {
  margin-top: 16px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.trend.up { color: #10b981; }
.trend.down { color: #f43f5e; }
.footer-text { color: var(--text-secondary); }

.chart-card { height: 450px; }
.chart-box { height: 350px; width: 100%; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-card {
  background: var(--card-bg);
}

:deep(.clickable-row) {
  cursor: pointer;
}

:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: #1e293b;
  --el-table-border-color: #334155;
  --el-table-text-color: #f8fafc;
}

:deep(.el-table th.el-table__cell) {
  background-color: #1e293b !important;
  color: #cbd5e1;
  font-weight: 600;
}

:deep(.el-table__row:hover > td.el-table__cell) {
  background-color: #334155 !important;
}

:deep(.el-table td.el-table__cell) {
  padding: 12px 0;
}

</style>
