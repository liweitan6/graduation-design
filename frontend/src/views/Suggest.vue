<template>
  <div class="suggest-page">
    <!-- Input Section -->
    <el-card class="input-card glass-panel">
      <div class="input-header">
        <el-icon :size="24" color="#10b981"><MagicStick /></el-icon>
        <h3>AI-Driven Mutation Suggestions</h3>
      </div>
      <p class="input-desc">
        Describe the operators or test scenarios you want to improve. 
        The AI will analyze historical error patterns and provide targeted mutation strategies.
      </p>
      <el-input
        v-model="query"
        type="textarea"
        :rows="3"
        placeholder="e.g., '我想测试 Conv2d 和 BatchNorm2d 组合，如何设计用例才能发现更多 bug？'"
        @keyup.ctrl.enter="handleSuggest"
      />
      <div class="input-actions">
        <el-button type="primary" @click="handleSuggest" :loading="loading" size="large">
          <el-icon><MagicStick /></el-icon>
          Generate Suggestions
        </el-button>
        <div class="quick-prompts">
          <el-tag 
            v-for="prompt in quickPrompts" :key="prompt" 
            class="quick-tag" 
            effect="plain"
            @click="query = prompt"
          >
            {{ prompt }}
          </el-tag>
        </div>
      </div>
    </el-card>

    <!-- Data Summary -->
    <el-row :gutter="20" class="summary-row" v-if="dataSummary">
      <el-col :span="6">
        <el-card class="mini-card">
          <div class="mini-number">{{ dataSummary.total_cases }}</div>
          <div class="mini-label">Historical Cases</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="mini-card">
          <div class="mini-number crash">{{ dataSummary.crash_rate }}%</div>
          <div class="mini-label">Crash Rate</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="mini-card">
          <div class="mini-number ops">{{ dataSummary.operators_tested }}</div>
          <div class="mini-label">Operators Tested</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="mini-card">
          <div class="mini-label">High Risk Operators</div>
          <div class="risk-tags">
            <el-tag 
              v-for="[op, count] in (dataSummary.high_risk_operators || [])" 
              :key="op" type="danger" size="small"
            >
              {{ op }} ({{ count }})
            </el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- AI Result -->
    <transition name="fade">
      <el-card v-if="suggestions" class="result-card">
        <template #header>
          <div class="result-header">
            <div class="result-badge">
              <el-icon><MagicStick /></el-icon>
              AI Mutation Suggestions
            </div>
            <el-tag type="success" size="small">Based on {{ dataSummary?.total_cases || 0 }} historical cases</el-tag>
          </div>
        </template>
        <div class="suggestion-content" v-html="formattedSuggestions"></div>
      </el-card>
    </transition>

    <!-- Methodology -->
    <el-card class="method-card" v-if="!suggestions">
      <template #header><span>How It Works</span></template>
      <el-row :gutter="20">
        <el-col :span="8">
          <div class="step">
            <div class="step-num">1</div>
            <h4>Analyze History</h4>
            <p>Extract error patterns, operator crash rates, and coverage gaps from all historical test data.</p>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="step">
            <div class="step-num">2</div>
            <h4>Pattern Recognition</h4>
            <p>Identify high-risk operator combinations and parameter ranges that frequently trigger bugs.</p>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="step">
            <div class="step-num">3</div>
            <h4>Generate Mutations</h4>
            <p>AI generates targeted test case variations with traceable reasoning linked to historical evidence.</p>
          </div>
        </el-col>
      </el-row>
      <el-divider />
      <div class="advantage">
        <h4>Advantages over Direct AI Testing</h4>
        <el-row :gutter="16">
          <el-col :span="6"><el-tag effect="dark" type="success" class="adv-tag">Explainable</el-tag><p>Every suggestion links to data evidence</p></el-col>
          <el-col :span="6"><el-tag effect="dark" type="success" class="adv-tag">Traceable</el-tag><p>Decisions can be audited & reproduced</p></el-col>
          <el-col :span="6"><el-tag effect="dark" type="success" class="adv-tag">Cumulative</el-tag><p>More data = better suggestions</p></el-col>
          <el-col :span="6"><el-tag effect="dark" type="success" class="adv-tag">Collaborative</el-tag><p>Engineers can review, modify, annotate</p></el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { MagicStick } from '@element-plus/icons-vue'
import { getSuggestions } from '../api'
import { ElMessage } from 'element-plus'

const query = ref('')
const loading = ref(false)
const suggestions = ref('')
const dataSummary = ref<any>(null)

const quickPrompts = [
  '如何优化 Conv2d 相关测试用例以发现更多显存问题？',
  '帮我分析 LSTM 和 RNN 类算子的测试策略',
  '哪些算子组合最容易触发 Shape Mismatch？',
  '建议一些针对 Attention 机制的边界测试用例'
]

const formattedSuggestions = computed(() => {
  if (!suggestions.value) return ''
  return suggestions.value
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
    .replace(/(\d+)\.\s/g, '<span class="num-bullet">$1.</span> ')
})

const handleSuggest = async () => {
  if (!query.value.trim()) {
    ElMessage.warning('Please enter a query')
    return
  }
  loading.value = true
  suggestions.value = ''

  try {
    const res = await getSuggestions(query.value)
    suggestions.value = res.data.suggestions || ''
    dataSummary.value = res.data.data_summary || null
  } catch (err: any) {
    console.error(err)
    ElMessage.error('Failed to generate suggestions. Ensure Python API is running.')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.suggest-page {
  max-width: 1200px;
  margin: 0 auto;
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.input-card { margin-bottom: 24px; padding: 8px; }
.input-header {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 8px;
}
.input-header h3 { font-size: 1.25rem; font-weight: 700; color: #f8fafc; margin: 0; }
.input-desc { color: #94a3b8; margin-bottom: 16px; line-height: 1.6; }

.input-actions {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quick-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-tag {
  cursor: pointer;
  transition: all 0.2s;
}
.quick-tag:hover {
  border-color: #6366f1;
  color: #818cf8;
}

.summary-row { margin-bottom: 24px; }
.mini-card { text-align: center; padding: 8px 0; }
.mini-number { font-size: 1.5rem; font-weight: 700; color: #f8fafc; }
.mini-number.crash { color: #f43f5e; }
.mini-number.ops { color: #6366f1; }
.mini-label { font-size: 12px; color: #94a3b8; margin-top: 4px; }
.risk-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; justify-content: center; }

.result-card { margin-bottom: 24px; }
.result-header {
  display: flex; justify-content: space-between; align-items: center;
}
.result-badge {
  display: inline-flex; align-items: center; gap: 6px;
  background: #10b981; color: #fff;
  padding: 6px 14px; border-radius: 100px;
  font-size: 13px; font-weight: 600;
}

.suggestion-content {
  line-height: 2;
  font-size: 15px;
  color: #e2e8f0;
}

.suggestion-content :deep(.num-bullet) {
  color: #818cf8;
  font-weight: 700;
}

.method-card { margin-bottom: 24px; }
.step { text-align: center; padding: 16px; }
.step-num {
  width: 40px; height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  color: #fff; font-size: 18px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 12px;
}
.step h4 { color: #f8fafc; margin-bottom: 8px; }
.step p { color: #94a3b8; font-size: 13px; line-height: 1.6; }

.advantage { text-align: center; }
.advantage h4 { color: #f8fafc; margin-bottom: 16px; }
.adv-tag { margin-bottom: 8px; }
.advantage p { color: #94a3b8; font-size: 12px; line-height: 1.5; }
</style>
