<template>
  <div class="cases-page">
    <!-- Filter Bar -->
    <el-card class="filter-card">
      <el-row :gutter="20" align="middle">
        <el-col :span="6">
          <el-select v-model="statusFilter" placeholder="按状态筛选" clearable @change="fetchCases">
            <el-option label="所有状态" value="" />
            <el-option label="通过" value="Success" />
            <el-option label="崩溃" value="Crash" />
            <el-option label="超时" value="Timeout" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-input v-model="searchKeyword" placeholder="搜索用例 ID..." clearable @keyup.enter="fetchCases">
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
        <el-col :span="12" class="text-right">
          <el-button @click="fetchCases" :loading="loading">
            <el-icon><Refresh /></el-icon>
            刷新列表
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- Cases Table -->
    <el-card class="table-card">
      <el-table 
        :data="filteredCases" 
        style="width: 100%" 
        v-loading="loading"
        @row-click="handleRowClick"
        row-class-name="clickable-row"
      >
        <el-table-column prop="caseUid" label="用例 ID" min-width="200">
          <template #default="{ row }">
            <span class="case-uid">{{ row.caseUid }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" effect="dark">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="edgeCoverage" label="边界覆盖率" width="140" sortable>
          <template #default="{ row }">
            <el-progress 
              :percentage="Math.min(100, row.edgeCoverage / 50)" 
              :stroke-width="8"
              :show-text="false"
              :color="getProgressColor(row.edgeCoverage)"
            />
            <span class="coverage-value">{{ row.edgeCoverage }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="executionTime" label="耗时 (秒)" width="120" sortable>
          <template #default="{ row }">
            {{ row.executionTime?.toFixed(3) }}
          </template>
        </el-table-column>
        <el-table-column prop="errorMessage" label="错误信息" min-width="250">
          <template #default="{ row }">
            <el-tooltip v-if="row.errorMessage" :content="row.errorMessage" placement="top">
              <span class="error-msg">{{ truncateMessage(row.errorMessage) }}</span>
            </el-tooltip>
            <span v-else class="no-error">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.createdAt) }}
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="totalCases"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchCases"
          @current-change="fetchCases"
        />
      </div>
    </el-card>

    <!-- Case Detail Drawer -->
    <CaseDetailDrawer v-model="drawerVisible" :case-data="selectedCase" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import { getCases } from '../api'
import CaseDetailDrawer from '../components/CaseDetailDrawer.vue'

interface TestCase {
  id?: number
  caseUid: string
  status: string
  edgeCoverage: number
  executionTime: number
  errorMessage?: string
  createdAt?: string
  parameters?: string | Record<string, any>
}

const loading = ref(false)
const cases = ref<TestCase[]>([])
const currentPage = ref(1)
const pageSize = ref(10)
const totalCases = ref(0)
const statusFilter = ref('')
const searchKeyword = ref('')
const drawerVisible = ref(false)
const selectedCase = ref<TestCase | null>(null)

const filteredCases = computed(() => {
  if (!searchKeyword.value) return cases.value
  return cases.value.filter(c => 
    c.caseUid.toLowerCase().includes(searchKeyword.value.toLowerCase())
  )
})

const getStatusType = (status: string) => {
  switch (status) {
    case 'Success': return 'success'
    case 'Crash': return 'danger'
    case 'Timeout': return 'warning'
    default: return 'info'
  }
}

const getProgressColor = (coverage: number) => {
  if (coverage > 3000) return '#10b981'
  if (coverage > 1500) return '#f59e0b'
  return '#f43f5e'
}

const truncateMessage = (msg: string) => {
  return msg.length > 50 ? msg.substring(0, 50) + '...' : msg
}

const formatDate = (dateStr?: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const handleRowClick = (row: TestCase) => {
  selectedCase.value = row
  drawerVisible.value = true
}

const fetchCases = async () => {
  loading.value = true
  try {
    const res = await getCases(currentPage.value - 1, pageSize.value, statusFilter.value || undefined)
    if (res.data) {
      // Spring Boot Page 格式
      cases.value = res.data.content || []
      totalCases.value = res.data.totalElements || 0
    }
  } catch (err) {
    console.error('Failed to fetch cases:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchCases()
})
</script>

<style scoped>
.cases-page {
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.filter-card {
  margin-bottom: 20px;
}

.text-right {
  text-align: right;
}

.table-card {
  margin-bottom: 20px;
}

.clickable-row {
  cursor: pointer;
}

.clickable-row:hover {
  background-color: rgba(99, 102, 241, 0.05) !important;
}

.case-uid {
  font-family: 'Fira Code', monospace;
  color: #818cf8; /* 加亮紫蓝色 */
  font-weight: 500;
}

.coverage-value {
  margin-left: 8px;
  font-size: 12px;
  color: #cbd5e1; /* 加亮文字 */
}

.error-msg {
  color: #fb7185; /* 更明亮的红色 */
  font-size: 13px;
}

.no-error {
  color: #64748b;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

/* Detail Drawer Styles */
.case-detail {
  padding: 24px;
  color: #ffffff;
}

.mb-20 {
  margin-bottom: 20px;
}

.case-uid-detail {
  font-family: 'Fira Code', monospace;
  color: #818cf8;
  font-size: 16px;
  font-weight: 600;
}

.coverage-highlight {
  color: #34d399; /* 更明亮的绿色 */
  font-weight: 600;
  font-size: 16px;
}

.detail-section {
  margin-bottom: 28px;
}

.detail-section h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
  padding-bottom: 10px;
  border-bottom: 1px solid #334155;
}

.error-detail {
  white-space: pre-wrap;
  word-break: break-all;
  background: #1e1b1e; /* 实体深色背景 */
  border: 1px solid #7f1d1d;
  padding: 16px;
  border-radius: 8px;
  font-size: 13px;
  color: #fca5a5; /* 更浅的红色文字 */
  line-height: 1.6;
  max-height: 250px;
  overflow-y: auto;
  font-family: 'Fira Code', monospace;
}

.structure-info {
  background: #111827; /* 深色实体背景 */
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 20px;
}

.info-row {
  margin-bottom: 16px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-row .label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.tags-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.connection-code {
  display: block;
  background: #020617;
  padding: 12px 16px;
  border: 1px solid #1e293b;
  border-radius: 6px;
  font-size: 13px;
  word-break: break-all;
  color: #34d399;
  font-family: 'Fira Code', monospace;
}

.log-content {
  white-space: pre-wrap;
  word-break: break-all;
  background: #020617; /* 纯黑背景增强对比 */
  border: 1px solid #1e293b;
  padding: 20px;
  border-radius: 8px;
  font-size: 12px;
  color: #e2e8f0; /* 亮灰白文字 */
  line-height: 1.6;
  max-height: 350px;
  overflow-y: auto;
  font-family: 'Fira Code', monospace;
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

:deep(.el-descriptions__label) {
  background-color: #1e293b !important;
  color: #94a3b8 !important;
  font-weight: 600;
}

:deep(.el-descriptions__content) {
  background-color: #0f172a !important;
  color: #ffffff !important;
}

:deep(.el-drawer) {
  background-color: #0b0f1a;
  border-left: 1px solid #334155;
}

:deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: 20px 24px;
  border-bottom: 1px solid #334155;
  color: #ffffff;
}

:deep(.el-drawer__title) {
  font-weight: 600;
  color: #ffffff;
}

:deep(.el-select) {
  width: 100%;
}

:deep(.el-drawer__body) {
  padding: 0;
}
</style>
