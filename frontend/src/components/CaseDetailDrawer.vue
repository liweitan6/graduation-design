<template>
  <el-drawer v-model="visible" title="测试用例详情" size="50%" @close="$emit('update:modelValue', false)">
    <div v-if="caseData" class="case-detail">
      <!-- Basic Info -->
      <el-descriptions :column="2" border class="mb-20">
        <el-descriptions-item label="用例 ID" :span="2">
          <span class="case-uid-detail">{{ getVal(caseData, ['caseUid', 'case_uid']) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="执行状态">
          <el-tag :type="getStatusType(caseData.status)" effect="dark">{{ caseData.status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="执行耗时">
          {{ formatExecutionTime(getVal(caseData, ['executionTime', 'execution_time'])) }}s
        </el-descriptions-item>
        <el-descriptions-item label="边界覆盖率">
          <span class="coverage-highlight">{{ getVal(caseData, ['edgeCoverage', 'edge_coverage']) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatDate(getVal(caseData, ['createdAt', 'created_at'])) }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- Error Message -->
      <div v-if="getVal(caseData, ['errorMessage', 'error_message'])" class="detail-section">
        <h4><el-icon><WarningFilled /></el-icon> 错误堆栈信息</h4>
        <pre class="error-detail">{{ getVal(caseData, ['errorMessage', 'error_message']) }}</pre>
      </div>

      <!-- Model Structure -->
      <div v-if="getModelStructure(caseData)" class="detail-section">
        <h4><el-icon><Connection /></el-icon> 神经网络模型结构</h4>
        <div class="structure-info">
          <div v-if="getModelStructure(caseData)?.layers" class="info-row">
            <span class="label">网络层类型 (LAYERS):</span>
            <div class="tags-wrap">
              <el-tag v-for="layer in getModelStructure(caseData)?.layers?.slice(0, 10)" :key="layer" size="small" type="info" effect="plain">
                {{ layer }}
              </el-tag>
              <el-tag v-if="getModelStructure(caseData)?.layers?.length > 10" size="small" type="info" effect="plain">
                +{{ getModelStructure(caseData)?.layers?.length - 10 }} 更多
              </el-tag>
            </div>
          </div>
          <div v-if="getModelStructure(caseData)?.operators" class="info-row">
            <span class="label">使用的算子 (OPERATORS):</span>
            <div class="tags-wrap">
              <el-tag v-for="op in getModelStructure(caseData)?.operators" :key="op" size="small" type="success" effect="light">
                {{ op }}
              </el-tag>
            </div>
          </div>
          <div v-if="getModelStructure(caseData)?.depth" class="info-row">
            <span class="label">模型深度 (DEPTH):</span>
            <span class="depth-value">{{ getModelStructure(caseData)?.depth }}</span>
          </div>
          
          <div v-if="connectionNodes.length > 0" class="info-row">
            <span class="label">拓扑连接与故障定位图 (DAG):</span>
            <div class="dag-visual" v-loading="analyzing" element-loading-background="rgba(17, 24, 39, 0.8)">
              <div class="dag-chain">
                <template v-for="(node, idx) in connectionNodes" :key="idx">
                  <el-tooltip :content="node.reason" placement="top" v-if="node.isSuspect">
                    <span class="dag-node suspect">
                      {{ node.op }} <span class="conf">{{ Math.round(node.confidence * 100) }}%</span>
                    </span>
                  </el-tooltip>
                  <span v-else class="dag-node normal">{{ node.op }}</span>
                  <span v-if="Number(idx) < connectionNodes.length - 1" class="dag-arrow">→</span>
                </template>
              </div>
              
              <div v-if="faultResult" class="fault-analysis-box">
                <div class="fault-title"><el-icon><Monitor /></el-icon> AI 故障根因分析结果</div>
                <p>{{ faultResult.analysis }}</p>
                <div class="fault-suggestion">💡 {{ faultResult.suggestion }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Parameters -->
      <div v-if="getParameters(caseData)" class="detail-section">
        <h4><el-icon><Setting /></el-icon> 输入参数详情</h4>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item v-for="(value, key) in getFilteredParams(caseData)" :key="key" :label="key">
            {{ value }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- Daikon Fault Boundary Validation -->
      <div v-if="isFailedCase" class="detail-section">
        <h4><el-icon><Aim /></el-icon> Daikon 双空间故障边界验证</h4>
        <div class="boundary-panel" v-loading="boundaryLoading" element-loading-background="rgba(17, 24, 39, 0.75)">
          <div class="boundary-actions">
            <div class="boundary-desc">
              自动推断成功空间约束，并生成满足/不满足约束的样例执行验证。
            </div>
            <el-button size="small" type="primary" :loading="boundaryLoading" @click.stop="runBoundaryAnalysis">
              {{ boundaryResult ? '重新验证' : '开始验证' }}
            </el-button>
          </div>

          <el-alert
            v-if="boundaryError"
            :title="boundaryError"
            type="error"
            show-icon
            :closable="false"
            class="boundary-alert"
          />

          <template v-if="boundaryResult">
            <div class="boundary-rule-box">
              <div class="boundary-rule-title">故障边界规则</div>
              <div class="boundary-rule-text">{{ boundaryResult.boundary_rule || '暂未生成边界规则' }}</div>
            </div>

            <div v-if="boundaryResult.daikon_violations?.length" class="constraint-tags">
              <span class="constraint-label">Daikon 约束式：</span>
              <el-tag v-for="item in boundaryResult.daikon_violations" :key="item" type="warning" effect="plain">
                {{ item }}
              </el-tag>
            </div>

            <div v-if="boundaryValidationReports.length" class="validation-list">
              <div v-for="(report, index) in boundaryValidationReports" :key="report.constraint || index" class="validation-card">
                <div class="validation-header">
                  <div class="constraint-code">{{ report.constraint }}</div>
                  <el-tag :type="report.is_validated ? 'success' : 'danger'" effect="dark">
                    {{ report.is_validated ? '验证通过' : '验证未通过' }}
                  </el-tag>
                </div>

                <el-row :gutter="12">
                  <el-col :span="12">
                    <div class="sample-box positive">
                      <div class="sample-title">满足约束样例，应成功执行</div>
                      <div v-for="(sample, idx) in report.positive_cases || []" :key="`p-${idx}`" class="sample-item">
                        <el-tag size="small" :type="sample.execution_success ? 'success' : 'danger'">
                          {{ sample.execution_success ? '成功' : '异常' }}
                        </el-tag>
                        <span class="sample-param">{{ sample.mutated_key }} = {{ sample.mutated_value }}</span>
                        <el-tooltip v-if="sample.message" :content="sample.message" placement="top">
                          <span class="sample-msg">{{ truncateMessage(sample.message) }}</span>
                        </el-tooltip>
                      </div>
                      <div v-if="!report.positive_cases?.length" class="empty-samples">未生成正样例</div>
                    </div>
                  </el-col>
                  <el-col :span="12">
                    <div class="sample-box negative">
                      <div class="sample-title">不满足约束样例，应触发报错</div>
                      <div v-for="(sample, idx) in report.negative_cases || []" :key="`n-${idx}`" class="sample-item">
                        <el-tag size="small" :type="sample.execution_success ? 'danger' : 'success'">
                          {{ sample.execution_success ? '未报错' : '已报错' }}
                        </el-tag>
                        <span class="sample-param">{{ sample.mutated_key }} = {{ sample.mutated_value }}</span>
                        <el-tooltip v-if="sample.message" :content="sample.message" placement="top">
                          <span class="sample-msg">{{ truncateMessage(sample.message) }}</span>
                        </el-tooltip>
                      </div>
                      <div v-if="!report.negative_cases?.length" class="empty-samples">未生成反样例</div>
                    </div>
                  </el-col>
                </el-row>
              </div>
            </div>
            <el-empty v-else description="未得到可验证的 Daikon 约束" :image-size="80" />
          </template>
        </div>
      </div>

      <!-- Execution Log -->
      <div v-if="getLogContent(caseData)" class="detail-section">
        <h4><el-icon><Document /></el-icon> 完整运行日志</h4>
        <pre class="log-content">{{ getLogContent(caseData) }}</pre>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { WarningFilled, Connection, Setting, Document, Monitor, Aim } from '@element-plus/icons-vue'
import { analyzeCase, analyzeFaultBoundary } from '../api'

const props = defineProps<{
  modelValue: boolean
  caseData: any
}>()
const emit = defineEmits(['update:modelValue'])

const visible = ref(props.modelValue)
const analyzing = ref(false)
const faultResult = ref<any>(null)
const boundaryLoading = ref(false)
const boundaryResult = ref<any>(null)
const boundaryError = ref('')

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, async (val) => {
  emit('update:modelValue', val)
  boundaryResult.value = null
  boundaryError.value = ''
  if (val && props.caseData && isFailedCase.value) {
    analyzing.value = true
    faultResult.value = null
    try {
      const uid = getVal(props.caseData, ['caseUid', 'case_uid'])
      if (uid) {
        const res = await analyzeCase(uid)
        faultResult.value = res.data.fault_localization
      }
    } catch (e) {
      console.error('Failed to analyze case:', e)
    } finally {
      analyzing.value = false
    }
  } else {
    faultResult.value = null
  }
})

// Helper to get value from multiple possible keys (camelCase or snake_case)
const getVal = (obj: any, keys: string[]) => {
  if (!obj) return null
  for (const key of keys) {
    if (obj[key] !== undefined && obj[key] !== null) return obj[key]
  }
  return null
}

const isFailedCase = computed(() => {
  const status = String(props.caseData?.status || '').toUpperCase()
  return !!props.caseData && !['SUCCESS', 'PASSED'].includes(status)
})

const boundaryValidationReports = computed(() => boundaryResult.value?.daikon_validation || [])

const getStatusType = (status: string) => {
  switch (status) {
    case 'Success': return 'success'
    case 'Crash': return 'danger'
    case 'Timeout': return 'warning'
    default: return 'info'
  }
}

const truncateMessage = (msg: string) => {
  if (!msg) return ''
  return msg.length > 50 ? msg.substring(0, 50) + '...' : msg
}

const runBoundaryAnalysis = async () => {
  const uid = getVal(props.caseData, ['caseUid', 'case_uid'])
  if (!uid) return
  boundaryLoading.value = true
  boundaryError.value = ''
  try {
    const res = await analyzeFaultBoundary(uid)
    boundaryResult.value = res.data
  } catch (e: any) {
    console.error('Failed to analyze fault boundary:', e)
    boundaryError.value = e?.response?.data?.detail || '故障边界验证失败，请检查 Python 分析服务是否启动。'
  } finally {
    boundaryLoading.value = false
  }
}

const formatDate = (dateStr?: string) => {
  if (!dateStr) return '-'
  try {
    return new Date(dateStr).toLocaleString('zh-CN')
  } catch {
    return dateStr
  }
}

const formatExecutionTime = (time: any) => {
  if (time === undefined || time === null) return '0.000'
  const num = Number(time)
  return isNaN(num) ? '0.000' : num.toFixed(3)
}

const parseParameters = (testCase: any): Record<string, any> | null => {
  const params = testCase.parameters
  if (!params) return null
  if (typeof params === 'string') {
    try {
      return JSON.parse(params)
    } catch {
      return null
    }
  }
  return params
}

const getModelStructure = (testCase: any) => {
  const params = parseParameters(testCase)
  // Check if model_structure is directly in caseData or in parameters
  return params?.model_structure || testCase.model_structure || null
}

const connectionNodes = computed(() => {
  const connStr = getModelStructure(props.caseData)?.connections
  if (!connStr) return []
  const ops = connStr.split('->')
  
  const suspects = faultResult.value?.suspect_operators || []
  
  return ops.map((op: string, idx: number) => {
    const suspectObj = suspects.find((s: any) => s.index === idx)
    return {
      op,
      isSuspect: !!suspectObj,
      confidence: suspectObj ? suspectObj.confidence : 0,
      reason: suspectObj ? suspectObj.reason : ''
    }
  })
})

const getParameters = (testCase: any) => {
  return parseParameters(testCase) || null
}

const getFilteredParams = (testCase: any): Record<string, any> => {
  const params = parseParameters(testCase)
  if (!params) return {}
  
  const excluded = ['model_structure', 'vis_x', 'vis_y', 'structure_vector_id', 'log_vector_id', 'log_content']
  const result: Record<string, any> = {}
  
  for (const [key, value] of Object.entries(params)) {
    if (!excluded.includes(key) && value !== null && value !== undefined) {
      result[key] = typeof value === 'object' ? JSON.stringify(value) : value
    }
  }
  return result
}

const getLogContent = (testCase: any) => {
  const params = parseParameters(testCase)
  return params?.log_content || testCase.log_content || null
}
</script>

<style scoped>
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
  color: #34d399;
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
  background: #1e1b1e;
  border: 1px solid #7f1d1d;
  padding: 16px;
  border-radius: 8px;
  font-size: 13px;
  color: #fca5a5;
  line-height: 1.6;
  max-height: 250px;
  overflow-y: auto;
  font-family: 'Fira Code', monospace;
}

.structure-info {
  background: #111827;
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

.depth-value {
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
}

.tags-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.dag-visual {
  background: #020617;
  padding: 16px;
  border: 1px solid #1e293b;
  border-radius: 6px;
  min-height: 80px;
}

.dag-chain {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 4px;
  margin-bottom: 20px;
}

.dag-node {
  padding: 4px 8px;
  border-radius: 4px;
  font-family: 'Fira Code', monospace;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.dag-node.normal {
  background: #1e293b;
  color: #94a3b8;
}

.dag-node.suspect {
  background: rgba(225, 29, 72, 0.15);
  border: 1px solid #e11d48;
  color: #fb7185;
  font-weight: 600;
  box-shadow: 0 0 8px rgba(225, 29, 72, 0.4);
  cursor: help;
}

.dag-node.suspect .conf {
  background: #e11d48;
  color: #fff;
  padding: 0 4px;
  border-radius: 2px;
  font-size: 11px;
}

.dag-arrow {
  color: #475569;
  font-weight: bold;
}

.fault-analysis-box {
  margin-top: 16px;
  padding: 16px;
  background: rgba(30, 41, 59, 0.5);
  border-left: 3px solid #f59e0b;
  border-radius: 4px;
}

.fault-title {
  color: #f59e0b;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.fault-analysis-box p {
  color: #cbd5e1;
  font-size: 13px;
  line-height: 1.5;
  margin: 0 0 8px 0;
}

.fault-suggestion {
  color: #34d399;
  font-size: 13px;
  font-weight: 500;
}

.boundary-panel {
  background: #111827;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 18px;
  min-height: 96px;
}

.boundary-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.boundary-desc {
  color: #94a3b8;
  font-size: 13px;
  line-height: 1.5;
}

.boundary-alert {
  margin-bottom: 16px;
}

.boundary-rule-box {
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(96, 165, 250, 0.35);
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 14px;
}

.boundary-rule-title {
  color: #93c5fd;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 6px;
}

.boundary-rule-text {
  color: #e0f2fe;
  font-size: 14px;
  line-height: 1.6;
}

.constraint-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.constraint-label {
  color: #cbd5e1;
  font-size: 12px;
  font-weight: 600;
}

.validation-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.validation-card {
  background: #020617;
  border: 1px solid #1e293b;
  border-radius: 8px;
  padding: 14px;
}

.validation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.constraint-code {
  font-family: 'Fira Code', monospace;
  color: #fbbf24;
  font-size: 13px;
  word-break: break-all;
}

.sample-box {
  border-radius: 6px;
  padding: 12px;
  min-height: 112px;
}

.sample-box.positive {
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.28);
}

.sample-box.negative {
  background: rgba(244, 63, 94, 0.08);
  border: 1px solid rgba(244, 63, 94, 0.28);
}

.sample-title {
  color: #e2e8f0;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 10px;
}

.sample-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
}

.sample-param {
  color: #cbd5e1;
  font-family: 'Fira Code', monospace;
}

.sample-msg {
  color: #94a3b8;
  cursor: help;
}

.empty-samples {
  color: #64748b;
  font-size: 12px;
}

.log-content {
  white-space: pre-wrap;
  word-break: break-all;
  background: #020617;
  border: 1px solid #1e293b;
  padding: 20px;
  border-radius: 8px;
  font-size: 12px;
  color: #e2e8f0;
  line-height: 1.6;
  max-height: 350px;
  overflow-y: auto;
  font-family: 'Fira Code', monospace;
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

:deep(.el-drawer__body) {
  padding: 0;
}
</style>
