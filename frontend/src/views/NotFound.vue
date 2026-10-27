<template>
  <div class="not-found-page">
    <div class="not-found-card">
      <p class="not-found-code">404</p>
      <h1 class="not-found-title">页面不存在</h1>
      <p class="not-found-desc">该地址可能已失效，或链接输入有误。</p>
      <div class="not-found-actions">
        <el-button @click="router.back()">返回上一页</el-button>
        <el-button type="primary" @click="router.push('/dashboard')">回到工作台</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<style scoped>
.not-found-page {
  display: grid;
  place-items: center;
  min-height: 60vh;
  padding: 32px;
}

.not-found-card {
  max-width: 420px;
  text-align: center;
}

.not-found-code {
  font-family: var(--rh-font-display);
  font-size: 64px;
  font-weight: 500;
  line-height: 1;
  color: var(--rh-border-strong);
}

.not-found-title {
  margin-top: 12px;
  font-family: var(--rh-font-display);
  font-size: 26px;
  font-weight: 500;
  color: var(--rh-text-primary);
}

.not-found-desc {
  margin-top: 8px;
  color: var(--rh-text-secondary);
  font-size: 14px;
}

.not-found-actions {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 24px;
}
</style>
