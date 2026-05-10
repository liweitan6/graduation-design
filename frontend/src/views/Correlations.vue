<template>
  <div class="correlations-page">
    <!-- Summary -->
    <el-row :gutter="20" class="summary-row">
      <el-col :span="8">
        <el-card class="stat-card">
          <div class="stat-number danger">{{ summary.total_error_cases }}</div>
          <div class="stat-label">已分析的错误用例</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card">
          <div class="stat-number warn">{{ summary.unique_dangerous_pairs }}</div>
          <div class="stat-label">危险算子对类型</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card">
          <div class="stat-number primary">{{ summary.top_suspect_operator || '-' }}</div>
          <div class="stat-label">最高风险算子</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Operator Fault Summary -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span>🎯 算子故障定位汇总</span>
          <el-tag type="info">基于结构化错误分析聚合</el-tag>
        </div>
      </template>
      <el-table :data="operatorFaultSummary" size="small" max-height="350">
        <el-table-column prop="operator" label="算子名称" min-width="130">
          <template #default="{ row }">
            <code class="op-name">{{ row.operator }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="total_faults" label="故障次数" width="110" sortable />
        <el-table-column prop="avg_confidence" label="平均置信度" width="130" sortable>
          <template #default="{ row }">
            <el-progress
              :percentage="Math.round(row.avg_confidence * 100)"
              :color="row.avg_confidence > 0.7 ? '#f43f5e' : (row.avg_confidence > 0.4 ? '#f59e0b' : '#6366f1')"
              :stroke-width="14"
              :text-inside="true"
            />
          </template>
        </el-table-column>
        <el-table-column label="错误类别分布" min-width="250">
          <template #default="{ row }">
            <el-tag
              v-for="(count, cat) in row.error_categories"
              :key="cat"
              :type="getErrorTagType(cat as string)"
              size="small"
              class="error-tag"
            >
              {{ cat }}: {{ count }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Dangerous Pairs -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span>⚡ 危险算子对 (高崩溃关联)</span>
          <el-tag type="warning">具有最高崩溃相关性的相邻算子对</el-tag>
        </div>
      </template>
      <el-table :data="dangerousPairs" size="small" max-height="350">
        <el-table-column label="算子对 (A -> B)" min-width="200">
          <template #default="{ row }">
            <span class="pair-chain">{{ row.pair }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_errors" label="错误计数" width="110" sortable />
        <el-table-column prop="dominant_error" label="主要错误类型" width="170">
          <template #default="{ row }">
            <el-tag :type="getErrorTagType(row.dominant_error)" size="small">
              {{ row.dominant_error }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="错误明细" min-width="220">
          <template #default="{ row }">
            <el-tag
              v-for="(count, cat) in row.error_breakdown"
              :key="cat"
              :type="getErrorTagType(cat as string)"
              size="small"
              class="error-tag"
            >
              {{ cat }}: {{ count }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Detailed Case Analysis -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span>🔍 个案故障定位详情</span>
          <el-input v-model="caseSearch" placeholder="搜索用例 ID（如 demo_daikon）" clearable size="small" style="width: 280px" prefix-icon="Search" />
        </div>
      </template>
      <el-table :data="filteredCases" size="small" max-height="400">
        <el-table-column prop="case_uid" label="用例 ID" min-width="170">
          <template #default="{ row }">
            <code class="uid">{{ row.case_uid }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="error_category" label="错误类别" width="150">
          <template #default="{ row }">
            <el-tag :type="getErrorTagType(row.error_category)" size="small">
              {{ row.error_category }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="嫌疑算子" min-width="250">
          <template #default="{ row }">
            <div v-for="(s, idx) in row.suspect_operators" :key="idx" class="suspect-item">
              <el-tag type="danger" size="small" effect="dark">{{ s.operator }}</el-tag>
              <span class="confidence">{{ Math.round(s.confidence * 100) }}%</span>
              <span class="reason-text">{{ truncate(s.reason, 60) }}</span>
            </div>
            <span v-if="!row.suspect_operators?.length" class="no-data">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="suggestion" label="修复建议" min-width="200">
          <template #default="{ row }">
            <span class="suggestion-text">{{ truncate(row.suggestion, 80) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openBoundaryAnalysis(row.case_uid)" :loading="boundaryLoading === row.case_uid" color="#f59e0b" plain>
              🔬 边界对比
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Dialog for Boundary Analysis -->
    <el-dialog v-model="boundaryDialogVisible" title="🔬 故障临界线差分对比分析" width="850px" destroy-on-close custom-class="glass-dialog">
      <div v-loading="boundaryLoading === currentBoundaryUid">
        <div v-if="boundaryData">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-card class="diff-card success-card" shadow="never">
                <template #header>
                  <div class="diff-header">
                    <span class="dot green-dot"></span> 对照组 (成功用例: {{ boundaryData.successful_case.uid }})
                  </div>
                </template>
                <pre class="diff-code">{{ JSON.stringify(boundaryData.diff.successful_values, null, 2) }}</pre>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card class="diff-card danger-card" shadow="never">
                <template #header>
                  <div class="diff-header">
                    <span class="dot red-dot"></span> 崩溃组 (越界用例: {{ boundaryData.failed_case.uid }})
                  </div>
                </template>
                <pre class="diff-code">{{ JSON.stringify(boundaryData.diff.failed_values, null, 2) }}</pre>
              </el-card>
            </el-col>
          </el-row>
          
          <div class="boundary-rule-container">
            <h4 class="rule-title">
              <el-icon><Monitor /></el-icon> 算法级定界发现 (Daikon Invariants)
            </h4>
            <div v-if="boundaryData.daikon_violations && boundaryData.daikon_violations.length > 0">
              <el-tag v-for="(rule, index) in boundaryData.daikon_violations" :key="index" type="danger" effect="plain" class="daikon-tag">
                被打破的绝对数学约束：<code class="daikon-code">{{ rule }}</code>
              </el-tag>
            </div>
            <div v-else class="rule-content" style="color: #94a3b8; font-size: 12px; margin-bottom: 10px;">
              <i>未能从对照组中提取到显著的线性数学约束，将退化为依赖纯参数差值推理。</i>
            </div>

            <h4 class="rule-title" style="margin-top: 15px;">
              <el-icon><Cpu /></el-icon> LLM 故障安全边界分析报告
            </h4>
            <div class="rule-content">{{ boundaryData.boundary_rule }}</div>
          </div>
        </div>
        <div v-else-if="boundaryError" class="error-msg">
          {{ boundaryError }}
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getCorrelations, analyzeFaultBoundary } from '../api'

const summary = ref<any>({})
const operatorFaultSummary = ref<any[]>([])
const dangerousPairs = ref<any[]>([])
const detailedCases = ref<any[]>([])
const caseSearch = ref('')

const filteredCases = computed(() => {
  if (!caseSearch.value) return detailedCases.value
  const keyword = caseSearch.value.toLowerCase()
  return detailedCases.value.filter((c: any) => c.case_uid.toLowerCase().includes(keyword))
})

const boundaryDialogVisible = ref(false)
const boundaryLoading = ref<string | null>(null)
const currentBoundaryUid = ref('')
const boundaryData = ref<any>(null)
const boundaryError = ref('')

const openBoundaryAnalysis = async (uid: string) => {
  currentBoundaryUid.value = uid
  boundaryLoading.value = uid
  boundaryData.value = null
  boundaryError.value = ''
  boundaryDialogVisible.value = true
  
  try {
    const res = await analyzeFaultBoundary(uid)
    boundaryData.value = res.data
  } catch (err: any) {
    boundaryError.value = err.response?.data?.detail || err.message || '分析失败'
  } finally {
    boundaryLoading.value = null
  }
}

const truncate = (str: string | undefined, len: number) => {
  if (!str) return ''
  return str.length > len ? str.substring(0, len) + '...' : str
}

const getErrorTagType = (cat: string) => {
  switch (cat) {
    case 'cuda_oom': return 'danger'
    case 'shape_mismatch': return 'warning'
    case 'segfault': return 'danger'
    case 'timeout': return 'info'
    case 'device_mismatch': return ''
    case 'index_error': return 'warning'
    default: return 'info'
  }
}

onMounted(async () => {
  try {
    const res = await getCorrelations()
    const data = res.data
    summary.value = data.summary || {}
    operatorFaultSummary.value = data.operator_fault_summary || []
    dangerousPairs.value = data.dangerous_pairs || []
    detailedCases.value = data.detailed_cases || []
  } catch (err) {
    console.error('Failed to load correlations:', err)
  }
})
</script>

<style scoped>
.correlations-page { animation: fadeIn 0.5s ease-out; }
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.summary-row { margin-bottom: 20px; }
.section-card { margin-bottom: 20px; }

.stat-card { text-align: center; padding: 10px 0; }
.stat-number { font-size: 2rem; font-weight: 700; }
.stat-number.danger { color: #f43f5e; }
.stat-number.warn { color: #f59e0b; }
.stat-number.primary { color: #818cf8; font-size: 1.4rem; }
.stat-label { font-size: 13px; color: #94a3b8; margin-top: 4px; }

.card-header {
  display: flex; justify-content: space-between; align-items: center;
}

.op-name { color: #818cf8; font-family: 'Fira Code', monospace; font-size: 13px; }
.uid { color: #818cf8; font-family: 'Fira Code', monospace; font-size: 12px; }

.pair-chain {
  color: #f59e0b;
  font-family: 'Fira Code', monospace;
  font-size: 13px;
  font-weight: 600;
}

.error-tag { margin: 2px 4px 2px 0; }

.suspect-item {
  display: flex; align-items: center; gap: 6px;
  margin-bottom: 4px; flex-wrap: wrap;
}

.confidence {
  color: #f43f5e; font-weight: 700; font-size: 12px; min-width: 32px;
}

.reason-text { color: #94a3b8; font-size: 12px; }
.suggestion-text { color: #cbd5e1; font-size: 12px; line-height: 1.5; }
.no-data { color: #475569; }

:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: #1e293b;
  --el-table-border-color: #334155;
  --el-table-text-color: #f8fafc;
}

.diff-card { background: rgba(30, 41, 59, 0.5); border: 1px solid #334155; margin-bottom: 20px;}
.success-card { border-top: 3px solid #10b981; }
.danger-card { border-top: 3px solid #f43f5e; }
.diff-header { font-size: 13px; color: #cbd5e1; display: flex; align-items: center; gap: 8px;}
.dot { width: 8px; height: 8px; border-radius: 50%; }
.green-dot { background-color: #10b981; }
.red-dot { background-color: #f43f5e; }
.diff-code { font-family: 'Fira Code', monospace; font-size: 13px; color: #f8fafc; white-space: pre-wrap; word-break: break-all; margin: 0; }
.boundary-rule-container { background: rgba(245, 158, 11, 0.1); border-left: 4px solid #f59e0b; padding: 15px; border-radius: 4px; }
.rule-title { margin: 0 0 10px 0; color: #f59e0b; font-size: 14px; }
.rule-content { color: #1e293b; font-size: 14px; line-height: 1.6; }
.daikon-tag { margin-bottom: 8px; display: block; width: fit-content; border-color: #f43f5e; color: #f43f5e; }
.daikon-code { font-family: 'Fira Code', monospace; font-weight: bold; font-size: 14px; background: rgba(244, 63, 94, 0.1); padding: 2px 6px; border-radius: 4px; }
</style>
