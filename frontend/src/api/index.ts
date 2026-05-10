import axios from 'axios'

// 切换到 Java 后端
const api = axios.create({
    baseURL: 'http://localhost:8080', // Java Spring Boot 后端
    timeout: 60000  // RAG 调用 LLM 需要较长时间
})

// Python 服务 (仅用于语义检索和 RAG，现在通过 Java 代理)
// const pythonApi = axios.create({
//   baseURL: 'http://localhost:5000',
//   timeout: 30000
// })

// ==================== 统计接口 ====================

export const getStatisticsOverview = () => {
    return api.get('/api/statistics/overview')
}

export const getStatisticsStatus = () => {
    return api.get('/api/statistics/status')
}

export const getStatisticsErrors = () => {
    return api.get('/api/statistics/errors')
}

// 兼容旧接口
export const getStatistics = (query: string = '总览') => {
    return getStatisticsOverview()
}

// ==================== 用例接口 ====================

export const getCases = (page: number = 0, size: number = 10, status?: string) => {
    return api.get('/api/cases', { params: { page, size, status } })
}

export const getRecentCases = (limit: number = 10) => {
    return api.get('/api/cases/recent')
}

export const getCaseById = (id: number) => {
    return api.get(`/api/cases/${id}`)
}

export const getCaseByCaseUid = (caseUid: string) => {
    return api.get(`/api/cases/uid/${caseUid}`)
}

// ==================== 搜索接口 (代理到 Python) ====================

export const semanticSearch = (query: string) => {
    return api.post('/api/search', { query })
}

export const askRAG = (query: string) => {
    return api.post('/api/ask', { query })
}

// Python 服务直接调用（用于数据导入，绕过 Java 代理）
const pythonApi = axios.create({
    baseURL: 'http://localhost:5000',
    timeout: 60000  // 导入可能需要较长时间
})

// 数据导入接口（直接调用 Python 服务）
export const ingestCases = (cases: any[]) => {
    return pythonApi.post('/api/ingest', cases)
}

// ==================== 分析接口 (直接调用 Python 服务) ====================

export const getCoverageGaps = () => {
    return pythonApi.get('/api/analysis/coverage-gaps')
}

export const getEfficiencyAnalysis = () => {
    return pythonApi.get('/api/analysis/efficiency')
}

export const getErrorPatterns = () => {
    return pythonApi.get('/api/analysis/error-patterns')
}

export const getSuggestions = (query: string) => {
    return pythonApi.post('/api/suggest', { query })
}

export const analyzeCase = (caseUid: string) => {
    return pythonApi.post('/api/analyze-case', { case_uid: caseUid })
}

export const getCorrelations = () => {
    return pythonApi.get('/api/analysis/correlations')
}

export const analyzeFaultBoundary = (failedCaseUid: string) => {
    return pythonApi.post('/api/analysis/fault-boundary', { failed_case_uid: failedCaseUid })
}

// ==================== 自动化闭环接口 ====================

export const autoGenerateFromGaps = (maxPairs: number = 5) => {
    return pythonApi.post('/api/auto-generate-from-gaps', { max_pairs: maxPairs })
}

export const pruneByEfficiency = (ceiThreshold: number = 0, dryRun: boolean = true) => {
    return pythonApi.post('/api/analysis/efficiency/prune', {
        cei_threshold: ceiThreshold,
        dry_run: dryRun
    })
}

export default api
