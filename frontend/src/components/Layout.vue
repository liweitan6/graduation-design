<template>
  <el-container class="layout-container">
    <el-aside width="240px" class="aside">
      <div class="logo">
        <el-icon :size="24" color="#6366f1"><Monitor /></el-icon>
        <span class="logo-text">DL Fuzzing</span>
      </div>
      
      <el-menu
        :default-active="activeRoute"
        class="menu"
        background-color="transparent"
        text-color="#94a3b8"
        active-text-color="#f8fafc"
        router
      >
        <el-menu-item index="/">
          <el-icon><DataLine /></el-icon>
          <span>总览仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/diversity">
          <el-icon><PieChart /></el-icon>
          <span>多样性可视化</span>
        </el-menu-item>
        <el-menu-item index="/cases">
          <el-icon><Document /></el-icon>
          <span>测试用例管理</span>
        </el-menu-item>
        <el-menu-item index="/import">
          <el-icon><UploadFilled /></el-icon>
          <span>导入测试数据</span>
        </el-menu-item>
        <el-divider style="margin: 8px 16px; border-color: rgba(255,255,255,0.06);" />
        <el-menu-item index="/coverage">
          <el-icon><Grid /></el-icon>
          <span>算子覆盖分析</span>
        </el-menu-item>
        <el-menu-item index="/efficiency">
          <el-icon><TrendCharts /></el-icon>
          <span>测试效能分析</span>
        </el-menu-item>
        <el-menu-item index="/assistant">
          <el-icon><MagicStick /></el-icon>
          <span>AI 智能助手</span>
        </el-menu-item>
        <el-menu-item index="/correlations">
          <el-icon><Connection /></el-icon>
          <span>故障关联分析</span>
        </el-menu-item>
      </el-menu>

      <div class="aside-footer">
        <div class="env-tag">graduation_design</div>
      </div>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <h2 class="page-title">{{ pageTitle }}</h2>
        </div>
        <div class="header-right">
          <el-button circle bg>
            <el-icon><Bell /></el-icon>
          </el-button>
          <el-avatar :size="32" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
        </div>
      </el-header>

      <el-main class="main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { 
  Monitor, DataLine, PieChart, Bell, Document, UploadFilled,
  Grid, TrendCharts, MagicStick, Connection
} from '@element-plus/icons-vue'

const route = useRoute()
const activeRoute = computed(() => route.path)

const pageTitle = computed(() => {
  switch(route.path) {
    case '/': return '系统运行总览'
    case '/diversity': return '测试用例多样性分布'
    case '/assistant': return 'AI 智能测试助手'
    case '/cases': return '测试用例管理'
    case '/import': return '导入测试记录'
    case '/coverage': return '算子覆盖缺口分析'
    case '/efficiency': return '测试效能评估'
    case '/correlations': return '故障根因关联分析'
    default: return '深度学习模糊测试管理系统'
  }
})
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.aside {
  background-color: var(--sidebar-bg);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 12px;
}

.logo-text {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  background: linear-gradient(to right, #6366f1, #a855f7);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.menu {
  border-right: none;
  flex: 1;
}

.menu :deep(.el-menu-item) {
  height: 50px;
  margin: 4px 12px;
  border-radius: 8px;
}

.menu :deep(.el-menu-item.is-active) {
  background: rgba(99, 102, 241, 0.1) !important;
}

.aside-footer {
  padding: 24px;
}

.env-tag {
  background: rgba(255, 255, 255, 0.05);
  padding: 6px 12px;
  border-radius: 100px;
  font-size: 12px;
  color: var(--text-secondary);
  text-align: center;
  border: 1px solid var(--border-color);
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
}

.main {
  background-color: var(--bg-color);
  padding: 24px;
}
</style>
