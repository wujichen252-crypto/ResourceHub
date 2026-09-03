<template>
  <div class="login-container">
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
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: var(--rh-bg-base);
  padding: 24px;
}

.login-card {
  width: 400px;
  max-width: 100%;
  padding: 40px 36px 32px;
  background: var(--rh-bg-card);
  border-radius: var(--rh-radius-md);
  border: 1px solid var(--rh-border);
  box-shadow: var(--rh-shadow-sm);
  transition: border-color var(--rh-duration-normal) var(--rh-transition-normal),
              box-shadow var(--rh-duration-normal) var(--rh-transition-normal);
}

/* ── Header ── */

.login-header {
  text-align: center;
  margin-bottom: 28px;
}

.logo-dot {
  display: inline-block;
  color: var(--rh-primary);
  font-size: 16px;
  line-height: 1;
  margin-bottom: 4px;
}

.login-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--rh-text-primary);
  letter-spacing: -0.02em;
  margin: 0 0 4px;
}

.login-subtitle {
  font-size: 13px;
  color: var(--rh-text-tertiary);
  margin: 0;
}

/* ── Tabs ── */

.login-tabs {
  margin-top: 4px;
}

.login-tabs :deep(.el-tabs__item) {
  font-size: 15px;
  font-weight: 500;
  color: var(--rh-text-tertiary);
  transition: var(--rh-transition-all-normal);
}

.login-tabs :deep(.el-tabs__item.is-active) {
  color: var(--rh-primary);
}

.login-tabs :deep(.el-tabs__active-bar) {
  background-color: var(--rh-primary);
}

.login-tabs :deep(.el-tabs__nav-wrap::after) {
  background-color: var(--rh-border);
}

.login-tabs :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 500;
  color: var(--rh-text-secondary);
  margin-bottom: 6px;
}

.login-tabs :deep(.el-input__wrapper) {
  padding: 8px 12px;
}

/* ── Actions ── */

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.submit-btn {
  height: 40px;
  font-size: 14px;
}

/* ── Dark Mode Card Hover ── */

@media (hover: hover) {
  .login-card:hover {
    box-shadow: var(--rh-shadow-md);
  }
}
</style>

<!-- Dialog non-scoped styles -->

<style>
.forgot-dialog .el-dialog {
  border-radius: var(--rh-radius-md);
}
</style>
