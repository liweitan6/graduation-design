<template>
  <div class="import-page">
    <!-- Import Method Selection -->
    <el-card class="method-card">
      <template #header>
        <div class="card-header">
          <span>导入测试用例与日志</span>
          <el-radio-group v-model="importMethod" size="default">
            <el-radio-button label="file">上传文件</el-radio-button>
            <el-radio-button label="manual">手动输入</el-radio-button>
            <el-radio-button label="sample">示例数据</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <!-- File Upload - Dual Upload -->
      <div v-if="importMethod === 'file'" class="upload-section">
        <el-row :gutter="20">
          <!-- JSON Data File -->
          <el-col :span="12">
            <div class="upload-box">
              <h4>
                <el-icon><Document /></el-icon>
                测试用例 (JSON)
                <el-tag type="danger" size="small">必填</el-tag>
              </h4>
              <el-upload
                ref="jsonUploadRef"
                :auto-upload="false"
                :limit="1"
                accept=".json"
                :on-change="handleJsonFileChange"
                :on-remove="() => jsonFileLoaded = false"
                drag
                class="upload-dragger"
              >
                <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                <div class="el-upload__text">
                  请拖拽 <strong>JSON</strong> 文件至此
                </div>
              </el-upload>
              <div class="upload-status" v-if="jsonFileLoaded">
                <el-icon color="#10b981"><CircleCheck /></el-icon>
                已加载 {{ pendingCases.length }} 条用例
              </div>
            </div>
          </el-col>
          
          <!-- Log File -->
          <el-col :span="12">
            <div class="upload-box">
              <h4>
                <el-icon><Tickets /></el-icon>
                执行日志 (.log/.txt)
                <el-tag type="info" size="small">选填</el-tag>
              </h4>
              <el-upload
                ref="logUploadRef"
                :auto-upload="false"
                :limit="1"
                accept=".log,.txt"
                :on-change="handleLogFileChange"
                :on-remove="() => logContent = ''"
                drag
                class="upload-dragger"
              >
                <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                <div class="el-upload__text">
                  请拖拽 <strong>LOG</strong> 文件至此
                </div>
              </el-upload>
              <div class="upload-status" v-if="logContent">
                <el-icon color="#10b981"><CircleCheck /></el-icon>
                日志文件已加载 ({{ Math.round(logContent.length / 1024) }}KB)
              </div>
            </div>
          </el-col>
        </el-row>
        
        <div class="upload-tip">
          <el-button link type="primary" @click="showFormatExample">查看 JSON 格式示例</el-button>
          <span class="tip-divider">|</span>
          <span>日志文件将按照 case_uid 自动解析并匹配至对应测试用例</span>
        </div>
      </div>

      <!-- Manual Input -->
      <div v-else-if="importMethod === 'manual'" class="manual-section">
        <el-form :model="manualForm" label-position="top">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="用例 ID (Case UID)" required>
                <el-input v-model="manualForm.case_uid" placeholder="例如：fuzz_resnet50_seed_001" />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="执行状态" required>
                <el-select v-model="manualForm.status" placeholder="请选择">
                  <el-option label="通过 (Success)" value="Success" />
                  <el-option label="崩溃 (Crash)" value="Crash" />
                  <el-option label="超时 (Timeout)" value="Timeout" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="执行耗时 (秒)">
                <el-input-number v-model="manualForm.execution_time" :min="0" :precision="3" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="边界覆盖率">
                <el-input-number v-model="manualForm.edge_coverage" :min="0" />
              </el-form-item>
            </el-col>
            <el-col :span="16">
              <el-form-item label="错误信息">
                <el-input v-model="manualForm.error_message" placeholder="若运行成功请留空" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="模型结构 (Model Structure JSON)">
            <el-input
              v-model="manualForm.model_structure_json"
              type="textarea"
              :rows="3"
              placeholder='{"layers": ["Conv2d", "ReLU"], "operators": ["Conv2d", "ReLU"], "depth": 2}'
            />
          </el-form-item>
          <el-form-item label="执行日志文本">
            <el-input
              v-model="manualForm.log_content"
              type="textarea"
              :rows="4"
              placeholder="[2026-02-07 14:32:15] [INFO] Starting fuzzing session..."
            />
          </el-form-item>
          <el-button type="primary" @click="addManualCase">
            <el-icon><Plus /></el-icon>
            添加至导入列表
          </el-button>
        </el-form>
      </div>

      <!-- Sample Data -->
      <div v-else class="sample-section">
        <el-alert
          title="加载演示专用的示例测试用例与执行日志"
          type="info"
          :closable="false"
          show-icon
        />
        <el-button type="primary" class="mt-16" @click="loadSampleData" :loading="loading">
          <el-icon><DocumentCopy /></el-icon>
          加载 10 条带日志的示例数据
        </el-button>
      </div>
    </el-card>

    <!-- Preview & Import -->
    <el-card class="preview-card" v-if="pendingCases.length > 0">
      <template #header>
        <div class="card-header">
          <span>待导入列表 (共 {{ pendingCases.length }} 条用例)</span>
          <div>
            <el-button @click="clearPending">清空列表</el-button>
            <el-button type="primary" @click="executeImport" :loading="importing">
              <el-icon><Upload /></el-icon>
              开始导入数据库
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="pendingCases" max-height="400" @row-click="showLogDetail">
        <el-table-column prop="case_uid" label="用例 ID" min-width="160" />
        <el-table-column prop="status" label="执行状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="edge_coverage" label="覆盖率" width="90" />
        <el-table-column prop="execution_time" label="耗时" width="70" />
        <el-table-column prop="error_message" label="错误描述" min-width="180">
          <template #default="{ row }">
            <span class="error-text">{{ truncate(row.error_message, 40) || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="日志" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.log_content" type="success" size="small">
              <el-icon><Tickets /></el-icon>
            </el-tag>
            <span v-else class="no-log">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="60">
          <template #default="{ $index }">
            <el-button type="danger" link @click.stop="removePendingCase($index)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Import Result -->
    <el-card v-if="importResult" class="result-card">
      <el-result
        :icon="importResult.success ? 'success' : 'error'"
        :title="importResult.success ? '导入成功！' : '导入失败'"
        :sub-title="importResult.message"
      >
        <template #extra>
          <el-button type="primary" @click="goToCases">查看用例</el-button>
        </template>
      </el-result>
    </el-card>

    <!-- 格式示例对话框 -->
    <el-dialog v-model="showFormatDialog" title="JSON 格式示例" width="650px">
      <pre class="format-example">{{ formatExample }}</pre>
    </el-dialog>

    <!-- 日志详情对话框 -->
    <el-dialog v-model="showLogDialog" :title="`日志内容: ${selectedCase?.case_uid}`" width="700px">
      <pre class="log-content">{{ selectedCase?.log_content || '暂无日志内容' }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled, Plus, Upload, Delete, DocumentCopy, Document, Tickets, CircleCheck } from '@element-plus/icons-vue'
import { ingestCases } from '../api'

interface TestCase {
  case_uid: string
  status: string
  execution_time: number
  edge_coverage: number
  model_structure?: any
  error_message?: string
  parameters?: any
  log_content?: string
}

const router = useRouter()
const importMethod = ref('file')
const loading = ref(false)
const importing = ref(false)
const pendingCases = ref<TestCase[]>([])
const importResult = ref<{ success: boolean; message: string } | null>(null)
const showFormatDialog = ref(false)
const showLogDialog = ref(false)
const selectedCase = ref<TestCase | null>(null)
const jsonFileLoaded = ref(false)
const logContent = ref('')

const manualForm = ref({
  case_uid: '',
  status: 'Success',
  execution_time: 0,
  edge_coverage: 0,
  error_message: '',
  model_structure_json: '',
  log_content: ''
})

const formatExample = `[
  {
    "case_uid": "fuzz_resnet50_seed_001",
    "status": "Crash",
    "execution_time": 0.85,
    "edge_coverage": 2340,
    "model_structure": {
      "layers": ["Conv2d", "BatchNorm2d", "ReLU"],
      "operators": ["Conv2d", "BatchNorm2d", "ReLU"],
      "depth": 3
    },
    "error_message": "RuntimeError: CUDA out of memory"
  }
]`

const getStatusType = (status: string) => {
  switch (status) {
    case 'Success': return 'success'
    case 'Crash': return 'danger'
    case 'Timeout': return 'warning'
    default: return 'info'
  }
}

const truncate = (str: string | undefined, len: number) => {
  if (!str) return ''
  return str.length > len ? str.substring(0, len) + '...' : str
}

const showFormatExample = () => {
  showFormatDialog.value = true
}

const showLogDetail = (row: TestCase) => {
  if (row.log_content) {
    selectedCase.value = row
    showLogDialog.value = true
  }
}

// Parse log file and extract logs for each case
const parseLogFile = (content: string): Map<string, string> => {
  const logMap = new Map<string, string>()
  const sections = content.split(/={40,}/)
  
  for (const section of sections) {
    // Find case_uid in the log section
    const match = section.match(/Starting fuzzing session:\s*(\S+)/)
    if (match && match[1]) {
      const caseUid = match[1]
      logMap.set(caseUid, section.trim())
    }
  }
  
  return logMap
}

const handleJsonFileChange = (file: any) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const content = JSON.parse(e.target?.result as string)
      const cases = Array.isArray(content) ? content : [content]
      pendingCases.value = cases.map(c => ({
        case_uid: c.case_uid,
        status: c.status || 'Success',
        execution_time: c.execution_time || 0,
        edge_coverage: c.edge_coverage || 0,
        model_structure: c.model_structure || {},
        error_message: c.error_message || null,
        parameters: c.parameters || {},
        log_content: c.log_content || undefined
      }))
      jsonFileLoaded.value = true
      
      // If log file already loaded, match logs
      if (logContent.value) {
        matchLogsWithCases()
      }
      
      ElMessage.success(`成功从 JSON 文件中加载了 ${cases.length} 条用例`)
    } catch (err) {
      ElMessage.error('JSON 格式错误，请检查文件内容')
      jsonFileLoaded.value = false
    }
  }
  reader.readAsText(file.raw)
}

const handleLogFileChange = (file: any) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    logContent.value = e.target?.result as string
    
    // Match logs with existing cases
    if (pendingCases.value.length > 0) {
      matchLogsWithCases()
    }
    
    ElMessage.success('日志文件已加载')
  }
  reader.readAsText(file.raw)
}

const matchLogsWithCases = () => {
  const logMap = parseLogFile(logContent.value)
  let matchCount = 0
  
  for (const testCase of pendingCases.value) {
    const log = logMap.get(testCase.case_uid)
    if (log) {
      testCase.log_content = log
      matchCount++
    }
  }
  
  if (matchCount > 0) {
    ElMessage.success(`成功匹配 ${matchCount} 条日志至测试用例`)
  } else {
    ElMessage.warning('未找到匹配的日志，请检查日志文件中的 case_uid')
  }
}

const addManualCase = () => {
  if (!manualForm.value.case_uid) {
    ElMessage.warning('用例 ID (Case UID) 为必填项')
    return
  }

  let modelStructure = {}
  if (manualForm.value.model_structure_json) {
    try {
      modelStructure = JSON.parse(manualForm.value.model_structure_json)
    } catch {
      ElMessage.error('模型结构 JSON 格式有误')
      return
    }
  }

  pendingCases.value.push({
    case_uid: manualForm.value.case_uid,
    status: manualForm.value.status,
    execution_time: manualForm.value.execution_time,
    edge_coverage: manualForm.value.edge_coverage,
    model_structure: modelStructure,
    error_message: manualForm.value.error_message || undefined,
    parameters: {},
    log_content: manualForm.value.log_content || undefined
  })

  // Reset form
  manualForm.value = {
    case_uid: '',
    status: 'Success',
    execution_time: 0,
    edge_coverage: 0,
    error_message: '',
    model_structure_json: '',
    log_content: ''
  }

  ElMessage.success('用例已添加至待导入列表')
}

const loadSampleData = () => {
  pendingCases.value = [
    { case_uid: 'sample_resnet_001', status: 'Crash', execution_time: 0.85, edge_coverage: 2340, model_structure: { layers: ['Conv2d', 'ReLU'], operators: ['Conv2d', 'ReLU'], depth: 2 }, error_message: 'CUDA out of memory', log_content: '[2026-02-07 14:32:15] [INFO] Starting fuzzing session: sample_resnet_001\n[2026-02-07 14:32:16] [ERROR] RuntimeError: CUDA out of memory\n[2026-02-07 14:32:16] [CRASH] Test case crashed after 0.85s' },
    { case_uid: 'sample_vgg_002', status: 'Crash', execution_time: 1.23, edge_coverage: 1890, model_structure: { layers: ['Conv2d', 'MaxPool2d'], operators: ['Conv2d', 'MaxPool2d'], depth: 2 }, error_message: 'Size mismatch', log_content: '[2026-02-07 14:33:42] [INFO] Starting fuzzing session: sample_vgg_002\n[2026-02-07 14:33:44] [ERROR] RuntimeError: size mismatch\n[2026-02-07 14:33:44] [CRASH] Test case crashed after 1.23s' },
    { case_uid: 'sample_bert_003', status: 'Timeout', execution_time: 30.0, edge_coverage: 450, model_structure: { layers: ['Embedding', 'Attention'], operators: ['Embedding', 'Attention'], depth: 2 }, error_message: 'Execution timeout', log_content: '[2026-02-07 14:35:10] [INFO] Starting fuzzing session: sample_bert_003\n[2026-02-07 14:35:40] [ERROR] TimeoutError: Execution exceeded 30s\n[2026-02-07 14:35:40] [TIMEOUT] Test case timed out' },
    { case_uid: 'sample_mobile_004', status: 'Success', execution_time: 0.32, edge_coverage: 3120, model_structure: { layers: ['Conv2d', 'BatchNorm'], operators: ['Conv2d', 'BatchNorm'], depth: 2 }, log_content: '[2026-02-07 14:36:55] [INFO] Starting fuzzing session: sample_mobile_004\n[2026-02-07 14:36:56] [SUCCESS] Test case passed in 0.32s' },
    { case_uid: 'sample_dense_005', status: 'Crash', execution_time: 0.67, edge_coverage: 2780, model_structure: { layers: ['DenseBlock'], operators: ['DenseBlock'], depth: 1 }, error_message: 'Segmentation fault', log_content: '[2026-02-07 14:38:20] [INFO] Starting fuzzing session: sample_dense_005\n[2026-02-07 14:38:21] [ERROR] Segmentation fault (core dumped)\n[2026-02-07 14:38:21] [CRASH] Test case crashed after 0.67s' },
    { case_uid: 'sample_incept_006', status: 'Crash', execution_time: 1.89, edge_coverage: 1560, model_structure: { layers: ['InceptionA', 'InceptionB'], operators: ['InceptionA'], depth: 2 }, error_message: 'Batch size mismatch', log_content: '[2026-02-07 14:48:22] [INFO] Starting fuzzing session: sample_incept_006\n[2026-02-07 14:48:24] [ERROR] ValueError: batch_size mismatch\n[2026-02-07 14:48:24] [CRASH] Test case crashed after 1.89s' },
    { case_uid: 'sample_effnet_007', status: 'Success', execution_time: 0.45, edge_coverage: 4210, model_structure: { layers: ['MBConv', 'Swish'], operators: ['MBConv', 'Swish'], depth: 2 }, log_content: '[2026-02-07 14:44:15] [INFO] Starting fuzzing session: sample_effnet_007\n[2026-02-07 14:44:16] [SUCCESS] Test case passed in 0.45s' },
    { case_uid: 'sample_trans_008', status: 'Crash', execution_time: 2.10, edge_coverage: 980, model_structure: { layers: ['Transformer'], operators: ['Transformer'], depth: 1 }, error_message: 'Device mismatch', log_content: '[2026-02-07 14:42:30] [INFO] Starting fuzzing session: sample_trans_008\n[2026-02-07 14:42:32] [ERROR] RuntimeError: device mismatch cuda:0 vs cpu\n[2026-02-07 14:42:32] [CRASH] Test case crashed after 2.10s' },
    { case_uid: 'sample_yolo_009', status: 'Success', execution_time: 0.78, edge_coverage: 3890, model_structure: { layers: ['Conv2d', 'SPP', 'Detect'], operators: ['Conv2d', 'SPP'], depth: 3 }, log_content: '[2026-02-07 14:40:05] [INFO] Starting fuzzing session: sample_yolo_009\n[2026-02-07 14:40:06] [SUCCESS] Test case passed in 0.78s' },
    { case_uid: 'sample_lstm_010', status: 'Crash', execution_time: 0.56, edge_coverage: 1120, model_structure: { layers: ['LSTM', 'Linear'], operators: ['LSTM', 'Linear'], depth: 2 }, error_message: 'Index out of bounds', log_content: '[2026-02-07 14:46:00] [INFO] Starting fuzzing session: sample_lstm_010\n[2026-02-07 14:46:01] [ERROR] IndexError: index 256 out of bounds\n[2026-02-07 14:46:01] [CRASH] Test case crashed after 0.56s' }
  ]
  ElMessage.success('已加载 10 条带日志的示例数据')
}

const removePendingCase = (index: number) => {
  pendingCases.value.splice(index, 1)
}

const clearPending = () => {
  pendingCases.value = []
  importResult.value = null
  jsonFileLoaded.value = false
  logContent.value = ''
}

const executeImport = async () => {
  if (pendingCases.value.length === 0) {
    ElMessage.warning('待导入列表为空')
    return
  }

  importing.value = true
  try {
    // Include log_content in parameters for storage
    const casesWithLogs = pendingCases.value.map(c => ({
      ...c,
      parameters: {
        ...(c.parameters || {}),
        log_content: c.log_content || null
      }
    }))
    
    const res = await ingestCases(casesWithLogs)
    importResult.value = {
      success: true,
      message: `成功导入 ${res.data.success} 条带日志的测试用例`
    }
    pendingCases.value = []
    jsonFileLoaded.value = false
    logContent.value = ''
    ElMessage.success('Import completed!')
  } catch (err: any) {
    importResult.value = {
      success: false,
      message: err.response?.data?.detail || err.message || '导入失败'
    }
    ElMessage.error('导入失败')
  } finally {
    importing.value = false
  }
}

const goToCases = () => {
  router.push('/cases')
}
</script>

<style scoped>
.import-page {
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.method-card,
.preview-card,
.result-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.upload-section {
  padding: 20px 0;
}

.upload-box {
  padding: 16px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  border: 1px solid var(--border-color);
}

.upload-box h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 14px;
  color: var(--text-primary);
}

.upload-dragger {
  width: 100%;
}

.upload-status {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #10b981;
  font-size: 13px;
}

.upload-tip {
  margin-top: 16px;
  font-size: 13px;
  color: var(--text-secondary);
}

.tip-divider {
  margin: 0 12px;
  color: var(--border-color);
}

.manual-section {
  padding: 10px 0;
}

.sample-section {
  padding: 20px 0;
}

.mt-16 {
  margin-top: 16px;
}

.error-text {
  color: #f43f5e;
  font-size: 13px;
}

.no-log {
  color: var(--text-secondary);
}

.format-example,
.log-content {
  background: rgba(0, 0, 0, 0.2);
  padding: 16px;
  border-radius: 8px;
  font-size: 13px;
  overflow-x: auto;
  white-space: pre-wrap;
  max-height: 400px;
  overflow-y: auto;
}

:deep(.el-upload-dragger) {
  background: rgba(99, 102, 241, 0.05);
  border-color: var(--border-color);
  padding: 20px;
}

:deep(.el-upload-dragger:hover) {
  border-color: #6366f1;
}

:deep(.el-table) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.02);
}

:deep(.el-table tr) {
  cursor: pointer;
}
</style>
