<template>
  <div class="smart-search">
    <div class="search-header glass-panel">
      <el-input
        v-model="query"
        placeholder="Enter search query (e.g., 'Find Conv2d crashes' or 'Why does my model crash?')"
        class="search-input"
        @keyup.enter="handleSearch"
      >
        <template #prefix>
          <el-icon class="el-input__icon"><Search /></el-icon>
        </template>
        <template #append>
          <el-button @click="handleSearch" :loading="loading" type="primary">
            Analyze
          </el-button>
        </template>
      </el-input>
      
      <div class="search-options">
        <el-checkbox v-model="useRAG">Enable Intent Analysis (RAG)</el-checkbox>
        <el-tooltip content="Uses LLM to classify intent and provide recommendations">
          <el-icon class="ml-5 info-icon"><InfoFilled /></el-icon>
        </el-tooltip>
      </div>
    </div>

    <div class="search-results" v-loading="loading">
      <!-- RAG Answer Segment -->
      <transition name="fade">
        <div v-if="ragAnswer" class="rag-answer-section glass-panel">
          <div class="section-badge">
            <el-icon><MagicStick /></el-icon>
            AI Insight
          </div>
          <div class="answer-content" v-html="formattedAnswer"></div>
        </div>
      </transition>

      <!-- Case Results Segment -->
      <div v-if="results.length > 0" class="results-list">
        <div class="results-title">Retrieved Test Cases (Top {{ results.length }})</div>
        <el-row :gutter="20">
          <el-col :span="8" v-for="item in results" :key="item.case_uid">
            <el-card shadow="hover" class="result-card clickable-card" @click="handleCaseClick(item)">
              <div class="card-top">
                <span class="uid">{{ item.case_uid }}</span>
                <el-tag :type="getStatusType(item.status)" size="small">{{ item.status }}</el-tag>
              </div>
              
              <div class="card-metrics">
                <div class="metric">
                  <span class="label">Similarity</span>
                  <span class="value">{{ (item.similarity_score * 100).toFixed(1) }}%</span>
                </div>
                <div class="metric">
                  <span class="label">Coverage</span>
                  <span class="value">{{ item.edge_coverage }}</span>
                </div>
              </div>

              <div class="error-snippet" v-if="item.error_message">
                {{ item.error_message.slice(0, 100) }}...
              </div>

              <div class="card-footer">
                <el-tag effect="plain" size="small" type="info">Source: {{ item.match_source }}</el-tag>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <el-empty v-else-if="!loading && searched" description="No results found for your query" />
    </div>

    <!-- Case Detail Drawer -->
    <CaseDetailDrawer v-model="drawerVisible" :case-data="selectedCase" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Search, InfoFilled, MagicStick } from '@element-plus/icons-vue'
import { semanticSearch, askRAG } from '../api'
import { ElMessage } from 'element-plus'
import CaseDetailDrawer from '../components/CaseDetailDrawer.vue'

const query = ref('')
const loading = ref(false)
const searched = ref(false)
const useRAG = ref(true)
const results = ref<any[]>([])
const ragAnswer = ref('')
const selectedCase = ref<any>(null)
const drawerVisible = ref(false)

const handleCaseClick = (item: any) => {
  selectedCase.value = item
  drawerVisible.value = true
}

const formattedAnswer = computed(() => {
  if (!ragAnswer.value) return ''
  // Basic markdown-like formatting for the AI answer
  return ragAnswer.value
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
})

const getStatusType = (status: string) => {
  switch(status) {
    case 'Success': return 'success'
    case 'Crash': return 'danger'
    case 'Timeout': return 'warning'
    default: return 'info'
  }
}

const handleSearch = async () => {
  if (!query.value.trim()) return
  
  loading.value = true
  searched.value = true
  results.value = []
  ragAnswer.value = ''

  try {
    if (useRAG.value) {
      // Step 1: Get RAG Answer
      const ragRes = await askRAG(query.value)
      ragAnswer.value = ragRes.data.answer
      // Use the context from RAG for the results display
      results.value = ragRes.data.context || []
    } else {
      // Step 2: Conventional Semantic Search
      const searchRes = await semanticSearch(query.value)
      results.value = searchRes.data.results
    }
  } catch (err: any) {
    console.error(err)
    ElMessage.error('Failed to connect to search service. Ensure Python API is running.')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.smart-search {
  max-width: 1200px;
  margin: 0 auto;
  animation: fadeIn 0.5s ease-out;
}

.search-header {
  padding: 30px;
  margin-bottom: 30px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.search-input {
  max-width: 800px;
}

:deep(.search-input .el-input-group__append) {
  background-color: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.search-options {
  display: flex;
  align-items: center;
  color: var(--text-secondary);
  font-size: 14px;
}

.info-icon {
  cursor: help;
  color: var(--text-secondary);
}

.search-results {
  min-height: 400px;
}

.rag-answer-section {
  padding: 28px;
  margin-bottom: 40px;
  border-left: 4px solid var(--secondary-color);
  background: rgba(16, 185, 129, 0.1); /* 增加背景不透明度 */
  border-radius: 0 12px 12px 0;
}

.section-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--secondary-color);
  color: #ffffff;
  padding: 6px 14px;
  border-radius: 100px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 24px;
}

.answer-content {
  line-height: 1.8;
  font-size: 16px;
  color: #ffffff; /* 纯白文字提高清晰度 */
}

.results-title {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 24px;
  color: #ffffff;
}

.result-card {
  margin-bottom: 20px;
  transition: transform 0.3s ease;
  background-color: #1e293b !important; /* 实体背景 */
}

.result-card:hover {
  transform: translateY(-5px);
}

.clickable-card {
  cursor: pointer;
  transition: all 0.3s ease;
}

.clickable-card:hover {
  border-color: var(--primary-color) !important;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.uid {
  font-family: 'Fira Code', monospace;
  font-weight: 600;
  font-size: 14px;
  color: #818cf8;
}

.card-metrics {
  display: flex;
  gap: 20px;
  margin-bottom: 16px;
}

.metric .label {
  display: block;
  font-size: 11px;
  color: #94a3b8;
  text-transform: uppercase;
  margin-bottom: 4px;
  font-weight: 600;
}

.metric .value {
  font-weight: 700;
  font-size: 16px;
  color: #ffffff;
}

.error-snippet {
  font-size: 12px;
  color: #fb7185;
  background: #111827; /* 深色背景 */
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 16px;
  font-family: 'Fira Code', monospace;
  border: 1px solid rgba(251, 113, 133, 0.2);
}

.card-footer {
  border-top: 1px solid #334155;
  padding-top: 12px;
}

.ml-5 { margin-left: 5px; }

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
