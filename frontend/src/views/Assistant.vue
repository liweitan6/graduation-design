<template>
  <div class="assistant-page">
    <!-- Header & Search Bar -->
    <div class="assistant-header glass-panel">
      <div class="header-main">
        <el-icon :size="32" color="#6366f1"><MagicStick /></el-icon>
        <div class="title-wrap">
          <h2>AI 智能测试助手</h2>
          <p>基于 RAG 与大模型检索历史用例并生成变异策略。</p>
        </div>
      </div>
      
      <div class="search-box">
        <el-input
          v-model="query"
          placeholder="例如：'查找 Conv2d 的崩溃并建议变异策略'"
          class="main-search-input"
          size="large"
          @keyup.enter="handleCombinedTask"
          clearable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
          <template #append>
            <el-button @click="handleCombinedTask" :loading="loading" type="primary">
              执行 AI 分析
            </el-button>
          </template>
        </el-input>
        
        <div class="search-hints">
          <el-tag 
            v-for="hint in quickPrompts" 
            :key="hint" 
            size="small" 
            effect="plain" 
            class="hint-tag"
            @click="query = hint"
          >
            {{ hint }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="assistant-results" v-loading="loading">
      <el-tabs v-model="activeTab" class="custom-tabs" v-if="searched || suggestions">
        <!-- 标签页 1: 智能分析与检索 -->
        <el-tab-pane name="insights" label="智能分析与检索">
          <div class="pane-content">
            <!-- RAG Answer -->
            <transition name="fade">
              <div v-if="ragAnswer" class="rag-answer-section glass-panel">
                <div class="section-badge">
                  <el-icon><MagicStick /></el-icon>
                  AI 智能洞察
                </div>
                <div class="answer-content" v-html="formattedAnswer"></div>
              </div>
            </transition>

            <!-- Test Case Results -->
            <div v-if="results.length > 0" class="results-list">
              <div class="results-title">检索到的参考用例 (Top {{ results.length }})</div>
              <el-row :gutter="20">
                <el-col :span="8" v-for="item in results" :key="item.case_uid">
                  <el-card shadow="hover" class="result-card clickable-card" @click="handleCaseClick(item)">
                    <div class="card-top">
                      <span class="uid">{{ item.case_uid }}</span>
                      <el-tag :type="getStatusType(item.status)" size="small">{{ item.status }}</el-tag>
                    </div>
                    <div class="card-metrics">
                      <div class="metric">
                        <span class="label">相似度</span>
                        <span class="value">{{ (item.similarity_score * 100).toFixed(1) }}%</span>
                      </div>
                      <div class="metric">
                        <span class="label">覆盖率</span>
                        <span class="value">{{ item.edge_coverage }}</span>
                      </div>
                    </div>
                    <div class="error-snippet" v-if="item.error_message">
                      {{ item.error_message.slice(0, 80) }}...
                    </div>
                  </el-card>
                </el-col>
              </el-row>
            </div>
            <el-empty v-else-if="!loading && searched" description="未找到匹配的用例。" />
          </div>
        </el-tab-pane>

        <!-- 标签页 2: 变异策略建议 -->
        <el-tab-pane name="mutation" label="变异策略建议">
          <div class="pane-content">
            <!-- Data Summary Statistics -->
            <el-row :gutter="20" class="summary-row" v-if="dataSummary">
              <el-col :span="6">
                <el-card class="mini-card">
                  <div class="mini-number">{{ dataSummary.total_cases }}</div>
                  <div class="mini-label">历史用例总数</div>
                </el-card>
              </el-col>
              <el-col :span="6">
                <el-card class="mini-card">
                  <div class="mini-number crash">{{ dataSummary.crash_rate }}%</div>
                  <div class="mini-label">平均崩溃率</div>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card class="mini-card">
                  <div class="mini-label">识别到的高风险算子</div>
                  <div class="risk-tags">
                    <el-tag 
                      v-for="[op, count] in (dataSummary.high_risk_operators || [])" 
                      :key="op" type="danger" size="small"
                    >
                      {{ op }} ({{ count }} 次错误)
                    </el-tag>
                  </div>
                </el-card>
              </el-col>
            </el-row>

            <!-- Mutation Suggestions -->
            <el-card v-if="suggestions" class="suggest-result-card">
              <template #header>
                <div class="result-header">
                  <div class="result-badge">
                    <el-icon><MagicStick /></el-icon>
                    生成的变异策略建议
                  </div>
                </div>
              </template>
              <div class="suggestion-content" v-html="formattedSuggestions"></div>
            </el-card>
            <el-empty v-else-if="!loading" description="执行分析以生成变异策略。" />
          </div>
        </el-tab-pane>

        <!-- 标签页 3: 技术原理 -->
        <el-tab-pane name="math" label="技术原理">
           <el-card class="method-card">
            <template #header><span>AI 助手系统架构</span></template>
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="step">
                  <div class="step-num">1</div>
                  <h4>语义检索</h4>
                  <p>利用 Milvus 向量数据库与 SentenceTransformers 模型，在海量历史数据中检索与当前查询语义最相似的测试用例。</p>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="step">
                  <div class="step-num">2</div>
                  <h4>RAG 意图分析</h4>
                  <p>大语言模型（LLM）深度解析检索到的上下文，挖掘历史报错的深层成因与逻辑关联。</p>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="step">
                  <div class="step-num">3</div>
                  <h4>模式变异生成</h4>
                  <p>AI 将提取的错误模式映射至目标算子，自动生成能够精准触发表层或深层缺陷的测试用例变异建议。</p>
                </div>
              </el-col>
            </el-row>
            <el-divider />
            <div class="advantage">
              <h4>系统价值</h4>
              <el-row :gutter="16">
                <el-col :span="6"><div class="adv-item"><el-tag effect="dark" type="success">可解释性</el-tag></div></el-col>
                <el-col :span="6"><div class="adv-item"><el-tag effect="dark" type="success">可追溯性</el-tag></div></el-col>
                <el-col :span="6"><div class="adv-item"><el-tag effect="dark" type="success">知识累积</el-tag></div></el-col>
                <el-col :span="6"><div class="adv-item"><el-tag effect="dark" type="success">具备可操作性</el-tag></div></el-col>
              </el-row>
            </div>
          </el-card>
        </el-tab-pane>
      </el-tabs>

      <!-- Welcome / Default State -->
      <div v-else class="welcome-screen">
        <el-row :gutter="40">
          <el-col :span="14">
            <img src="https://img.freepik.com/free-vector/artificial-intelligence-concept-illustration_114360-7013.jpg" class="welcome-img" />
          </el-col>
          <el-col :span="10" class="welcome-text">
            <h3>今天我可以如何协助您的深度学习测试？</h3>
            <ul class="feature-list">
              <li><el-icon color="#10b981"><CircleCheckFilled /></el-icon> <strong>查找相似崩溃</strong>：通过错误日志或算子描述查找历史相似问题。</li>
              <li><el-icon color="#10b981"><CircleCheckFilled /></el-icon> <strong>挖掘因果关系</strong>：通过 RAG 意图分析深入理解报错根因。</li>
              <li><el-icon color="#10b981"><CircleCheckFilled /></el-icon> <strong>生成变异策略</strong>：基于历史经验快速生成高质量的变异方向。</li>
              <li><el-icon color="#10b981"><CircleCheckFilled /></el-icon> <strong>揭示隐藏模式</strong>：从海量失败数据中自动提取高风险算子组合。</li>
            </ul>
             <el-button type="primary" size="large" @click="handleSampleSearch" class="mt-20">尝试示例分析</el-button>
          </el-col>
        </el-row>
      </div>
    </div>

    <!-- Details View Drawer -->
    <CaseDetailDrawer v-model="drawerVisible" :case-data="selectedCase" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Search, MagicStick, CircleCheckFilled } from '@element-plus/icons-vue'
import { askRAG, getSuggestions } from '../api'
import { ElMessage } from 'element-plus'
import CaseDetailDrawer from '../components/CaseDetailDrawer.vue'

// --- State ---
const query = ref('')
const loading = ref(false)
const searched = ref(false)
const activeTab = ref('insights')

// Search/RAG State
const results = ref<any[]>([])
const ragAnswer = ref('')

// Suggest/Stat State
const suggestions = ref('')
const dataSummary = ref<any>(null)

// UI State
const selectedCase = ref<any>(null)
const drawerVisible = ref(false)

const quickPrompts = [
  '查找 Conv2d 显存泄漏并提供修复建议',
  '优化 LSTM 测试场景以提升覆盖率',
  '为什么 Attention 层在训练时会崩溃？',
  '历史数据中失败率最高的算子组合'
]

// --- Computed ---
const formattedAnswer = computed(() => {
  if (!ragAnswer.value) return ''
  return ragAnswer.value
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
})

const formattedSuggestions = computed(() => {
  if (!suggestions.value) return ''
  return suggestions.value
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
    .replace(/(\d+)\.\s/g, '<span class="num-bullet">$1.</span> ')
})

// --- Handlers ---
const handleCaseClick = (item: any) => {
  selectedCase.value = item
  drawerVisible.value = true
}

const handleSampleSearch = () => {
  query.value = quickPrompts[0] || ''
  handleCombinedTask()
}

const handleCombinedTask = async () => {
  if (!query.value.trim()) {
    ElMessage.warning('请输入查询内容或描述')
    return
  }

  loading.value = true
  searched.value = true
  results.value = []
  ragAnswer.value = ''
  suggestions.value = ''
  dataSummary.value = null
  activeTab.value = 'insights'

  try {
    // 触发并行请求 (RAG Search + Mutation Generation)
    const [ragRes, suggestRes] = await Promise.all([
      askRAG(query.value),
      getSuggestions(query.value)
    ])

    // Handle RAG/Search results
    ragAnswer.value = ragRes.data.answer
    results.value = ragRes.data.context || []

    // Handle Mutation results
    suggestions.value = suggestRes.data.suggestions || ''
    dataSummary.value = suggestRes.data.data_summary || null
    
  } catch (err: any) {
    console.error(err)
    ElMessage.error('AI 服务暂时不可用，请检查后端日志。')
  } finally {
    loading.value = false
  }
}

const getStatusType = (status: string) => {
  switch(status) {
    case 'Success': return 'success'
    case 'Crash': return 'danger'
    case 'Timeout': return 'warning'
    default: return 'info'
  }
}
</script>

<style scoped>
.assistant-page {
  max-width: 1300px;
  margin: 0 auto;
  animation: fadeIn 0.5s ease-out;
}

/* Header Section */
.assistant-header {
  padding: 40px;
  margin-bottom: 30px;
  display: flex;
  flex-direction: column;
  gap: 30px;
  align-items: center;
}

.header-main {
  display: flex;
  align-items: center;
  gap: 16px;
  text-align: center;
}

.title-wrap h2 {
  font-size: 2rem;
  font-weight: 800;
  margin: 0;
  background: linear-gradient(to right, #818cf8, #c084fc);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.title-wrap p {
  color: #94a3b8;
  margin: 8px 0 0;
  font-size: 1.1rem;
}

/* Search Box */
.search-box {
  width: 100%;
  max-width: 850px;
}

.main-search-input {
  box-shadow: 0 10px 30px rgba(0,0,0,0.2);
}

:deep(.main-search-input .el-input-group__append) {
  background-color: #6366f1;
  color: white;
  border-color: #6366f1;
  font-weight: 600;
}

.search-hints {
  margin-top: 16px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}

.hint-tag {
  cursor: pointer;
  transition: all 0.3s;
  background: rgba(255,255,255,0.03);
  border-color: rgba(255,255,255,0.1);
  color: #94a3b8;
}

.hint-tag:hover {
  border-color: #6366f1;
  color: #818cf8;
  background: rgba(99, 102, 241, 0.1);
}

/* Tabs Styling */
.custom-tabs :deep(.el-tabs__item) {
  color: #94a3b8;
  font-size: 16px;
  font-weight: 600;
  height: 50px;
}

.custom-tabs :deep(.el-tabs__item.is-active) {
  color: #818cf8;
}

.custom-tabs :deep(.el-tabs__active-bar) {
  background-color: #818cf8;
}

.pane-content {
  padding: 24px 0;
}

/* Results Content */
.rag-answer-section {
  padding: 30px;
  margin-bottom: 40px;
  border-left: 5px solid #10b981;
  background: rgba(16, 185, 129, 0.05);
  border-radius: 4px 12px 12px 4px;
}

.section-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #10b981;
  color: #ffffff;
  padding: 6px 16px;
  border-radius: 100px;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 24px;
}

.answer-content {
  line-height: 1.85;
  font-size: 17px;
  color: #e2e8f0;
}

.results-title {
  font-size: 1.4rem;
  font-weight: 700;
  margin-bottom: 24px;
  color: #f8fafc;
}

/* Cards */
.result-card {
  margin-bottom: 20px;
  background-color: #1e293b !important;
  border-color: #334155 !important;
}

.clickable-card {
  cursor: pointer;
  transition: all 0.3s;
}

.clickable-card:hover {
  transform: translateY(-5px);
  border-color: #6366f1 !important;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.2);
}

.card-top {
  display: flex;
  justify-content: space-between;
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
  font-weight: 700;
  text-transform: uppercase;
}

.metric .value {
  font-weight: 800;
  font-size: 18px;
  color: #f8fafc;
}

.error-snippet {
  font-size: 12px;
  color: #fb7185;
  background: #0f172a;
  padding: 12px;
  border-radius: 6px;
  font-family: 'Fira Code', monospace;
  border: 1px solid rgba(251, 113, 133, 0.15);
}

/* Suggestion Tab Styles */
.summary-row { margin-bottom: 24px; }
.mini-card { text-align: center; padding: 12px 0; background: #1e293b !important; }
.mini-number { font-size: 1.8rem; font-weight: 800; color: #f8fafc; }
.mini-number.crash { color: #f43f5e; }
.mini-number.ops { color: #818cf8; }
.mini-label { font-size: 12px; color: #94a3b8; margin-top: 6px; text-transform: uppercase; letter-spacing: 0.05em; }
.risk-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; justify-content: center; }

.suggest-result-card { border-left: 5px solid #818cf8; background: #1e293b !important; }
.result-badge { 
  display: inline-flex; align-items: center; gap: 8px; 
  background: #818cf8; color: #fff; padding: 6px 16px; 
  border-radius: 100px; font-size: 13px; font-weight: 700; 
}
.suggestion-content { line-height: 1.9; font-size: 16px; color: #e2e8f0; }
.suggestion-content :deep(.num-bullet) { color: #818cf8; font-weight: 800; }

/* Methodology */
.step { text-align: center; padding: 20px; }
.step-num {
  width: 44px; height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #c084fc);
  color: #fff; font-size: 20px; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 16px;
}
.step h4 { color: #f8fafc; margin-bottom: 10px; font-size: 1.1rem; }
.step p { color: #94a3b8; font-size: 13px; line-height: 1.6; }
.advantage { text-align: center; padding-top: 10px; }
.advantage h4 { color: #f8fafc; margin-bottom: 20px; }
.adv-item { margin-bottom: 15px; }

/* Welcome Screen */
.welcome-screen {
  padding: 60px 0;
}
.welcome-img {
  width: 100%;
  border-radius: 12px;
  opacity: 0.8;
}
.welcome-text h3 {
  font-size: 1.8rem;
  font-weight: 700;
  color: #f8fafc;
  margin-bottom: 24px;
}
.feature-list {
  list-style: none;
  padding: 0;
  margin-bottom: 30px;
}
.feature-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  font-size: 1.05rem;
  color: #cbd5e1;
}
.mt-20 { margin-top: 20px; }

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(15px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
