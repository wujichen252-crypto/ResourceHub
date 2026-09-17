<template>
  <div class="login-container">
    <section class="login-intro">
      <div class="intro-brand"><span class="intro-mark">R</span><strong>ResourceHub</strong></div>
      <div class="intro-copy">
        <p class="intro-kicker">Knowledge · Prompts · Reuse</p>
        <h1>把好想法，<br />整理成下一次的起点。</h1>
        <p>一处收纳笔记、提示词和工作方法，让你的经验不再散落在不同的角落。</p>
      </div>
      <div class="intro-notes"><span class="intro-note">笔记 / 研究记录</span><span class="intro-note ai">✦ AI 提示词库</span><span class="intro-note">可复用的知识</span></div>
    </section>
    <section class="login-panel">
      <Transition name="fade-slide" mode="out-in">
      <div class="login-card animate-fade-in-up" :key="activeTab">
        <!-- Logo -->
        <div class="login-header">
          <span class="logo-dot">◆</span>
          <h1 class="login-title">ResourceHub</h1>
          <p class="login-subtitle">知识管理与 AI 提示词库</p>
        </div>

        <!-- Tabs -->
        <el-tabs v-model="activeTab" class="login-tabs">
          <el-tab-pane label="登录" name="login">
            <el-form
              ref="loginFormRef"
              :model="loginForm"
              :rules="loginRules"
              label-position="top"
              @keyup.enter="handleLogin"
            >
              <el-form-item label="用户名" prop="username">
                <el-input v-model="loginForm.username" placeholder="请输入用户名" />
              </el-form-item>
              <el-form-item label="密码" prop="password">
                <el-input
                  v-model="loginForm.password"
                  type="password"
                  show-password
                  placeholder="请输入密码"
                />
              </el-form-item>
              <el-form-item>
                <div class="form-actions">
                  <el-button type="primary" :loading="loading" class="submit-btn" @click="handleLogin">
                    {{ loading ? '登录中...' : '登 录' }}
                  </el-button>
                  <el-button text size="small" @click="showForgotDialog = true">
                    忘记密码？
                  </el-button>
                </div>
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="注册" name="register">
            <el-form
              ref="registerFormRef"
              :model="registerForm"
              :rules="registerRules"
              label-position="top"
              @keyup.enter="handleRegister"
            >
              <el-form-item label="用户名" prop="username">
                <el-input v-model="registerForm.username" placeholder="3-50 位字母/数字/下划线" />
              </el-form-item>
              <el-form-item label="邮箱" prop="email">
                <el-input v-model="registerForm.email" placeholder="选填" />
              </el-form-item>
              <el-form-item label="密码" prop="password">
                <el-input
                  v-model="registerForm.password"
                  type="password"
                  show-password
                  placeholder="至少 8 位"
                />
              </el-form-item>
              <el-form-item label="确认密码" prop="confirmPassword">
                <el-input
                  v-model="registerForm.confirmPassword"
                  type="password"
                  show-password
                  placeholder="再次输入密码"
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="loading" class="submit-btn" @click="handleRegister">
                  {{ loading ? '注册中...' : '注 册' }}
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </div>
      </Transition>
    </section>

    <!-- Forgot Password Dialog -->
    <Transition name="scaleIn" appear>
      <el-dialog
        v-model="showForgotDialog"
        title="找回密码"
        width="400px"
        :close-on-click-modal="false"
        class="forgot-dialog"
      >
        <el-form label-position="top" @keyup.enter="handleForgotPassword">
          <el-form-item label="用户名">
            <el-input v-model="forgotForm.username" placeholder="请输入注册时的用户名" />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="forgotForm.email" placeholder="请输入注册时填写的邮箱" />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input v-model="forgotForm.newPassword" type="password" show-password placeholder="至少 8 位" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="forgotLoading" class="submit-btn" @click="handleForgotPassword">
              {{ forgotLoading ? '提交中...' : '重置密码' }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-dialog>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { authApi } from '../api/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const activeTab = ref('login')
const loading = ref(false)
const showForgotDialog = ref(false)
const forgotLoading = ref(false)

const forgotForm = reactive({
  username: '',
  email: '',
  newPassword: '',
})

const loginFormRef = ref<FormInstance>()
const registerFormRef = ref<FormInstance>()

// 登录表单
const loginForm = reactive({
  username: '',
  password: '',
})

const loginRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

// 注册表单
const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
})

const validateConfirm = (_rule: any, value: string, callback: Function) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const registerRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3-50 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少 8 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

async function handleLogin() {
  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await authStore.login(loginForm)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  } catch (err: any) {
    const errMsg = err?.response?.data?.msg || err?.message || '登录失败'
    ElMessage.error(errMsg)
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  const valid = await registerFormRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await authStore.register({
      username: registerForm.username,
      password: registerForm.password,
      email: registerForm.email || undefined,
    })
    ElMessage.success('注册成功')
    router.push('/dashboard')
  } catch (err: any) {
    ElMessage.error(err.response?.data?.msg || '注册失败')
  } finally {
    loading.value = false
  }
}

async function handleForgotPassword() {
  if (!forgotForm.username.trim() || !forgotForm.email.trim() || !forgotForm.newPassword.trim()) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (forgotForm.newPassword.length < 8) {
    ElMessage.warning('密码长度至少 8 位')
    return
  }
  forgotLoading.value = true
  try {
    await authApi.forgotPassword({
      username: forgotForm.username.trim(),
      email: forgotForm.email.trim(),
      new_password: forgotForm.newPassword,
    })
    ElMessage.success('密码重置成功，请使用新密码登录')
    showForgotDialog.value = false
    forgotForm.username = ''
    forgotForm.email = ''
    forgotForm.newPassword = ''
  } catch (err: any) {
    ElMessage.error(err.response?.data?.msg || '重置失败')
  } finally {
    forgotLoading.value = false
  }
}
</script>

<style scoped>
.login-container { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(360px, .85fr); min-height: 100vh; background: var(--rh-bg-base); }
.login-intro { position: relative; display: flex; flex-direction: column; justify-content: space-between; overflow: hidden; padding: 9vh 8vw 7vh; background: var(--rh-text-primary); color: var(--rh-bg-card); }
.login-intro::before, .login-intro::after { position: absolute; border: 1px solid rgba(183,216,75,.34); border-radius: 50%; content: ''; pointer-events: none; }.login-intro::before { width: 520px; height: 520px; right: -220px; bottom: -190px; }.login-intro::after { width: 260px; height: 260px; right: 70px; bottom: 40px; }
.intro-brand { position: relative; z-index: 1; display: flex; align-items: center; gap: 10px; font-family: Georgia, serif; font-size: 19px; }.intro-mark { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 50%; background: var(--rh-ai); color: var(--rh-text-primary); font-size: 21px; font-weight: 700; }
.intro-copy { position: relative; z-index: 1; max-width: 550px; }.intro-kicker { margin-bottom: 22px; color: var(--rh-ai); font-size: 12px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }.intro-copy h1 { max-width: 540px; font-family: Georgia, 'Times New Roman', serif; font-size: clamp(40px, 5vw, 72px); font-weight: 400; line-height: 1.04; }.intro-copy p { max-width: 420px; margin-top: 24px; color: rgba(255,255,255,.64); font-size: 16px; line-height: 1.8; }.intro-notes { position: relative; z-index: 1; display: flex; flex-wrap: wrap; gap: 8px; }.intro-note { padding: 7px 10px; border: 1px solid rgba(255,255,255,.2); border-radius: 3px; color: rgba(255,255,255,.72); font-size: 12px; }.intro-note.ai { border-color: rgba(183,216,75,.45); color: var(--rh-ai); }
.login-panel { display: flex; align-items: center; justify-content: center; padding: 40px 7vw; background: var(--rh-bg-card); }.login-card { width: 100%; max-width: 420px; }.login-header { margin-bottom: 34px; }.logo-dot { display: none; }.login-title { margin: 0 0 8px; color: var(--rh-text-primary); font-family: Georgia, serif; font-size: 32px; font-weight: 500; }.login-subtitle { margin: 0; color: var(--rh-text-tertiary); font-size: 14px; }.login-tabs :deep(.el-tabs__item) { color: var(--rh-text-tertiary); font-size: 14px; font-weight: 700; }.login-tabs :deep(.el-tabs__item.is-active) { color: var(--rh-primary); }.login-tabs :deep(.el-tabs__active-bar) { background: var(--rh-primary); }.login-tabs :deep(.el-tabs__nav-wrap::after) { background: var(--rh-border); }.login-tabs :deep(.el-form-item__label) { color: var(--rh-text-secondary); font-size: 13px; font-weight: 700; }.login-tabs :deep(.el-input__wrapper) { min-height: 44px; padding: 8px 12px; }.form-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; }.submit-btn { height: 44px; font-size: 14px; }.forgot-dialog .el-dialog { border-radius: var(--rh-radius-md); }
@media (max-width: 760px) { .login-container { display: block; }.login-intro { min-height: 250px; padding: 28px 24px; }.intro-copy { margin-top: 45px; }.intro-copy h1 { font-size: 38px; }.intro-copy p, .intro-notes { display: none; }.login-panel { min-height: calc(100vh - 250px); padding: 42px 24px; }.login-title { font-size: 28px; } }
</style>

<style>
.login-intro { display: flex; }
.login-panel { display: flex; }
</style>
