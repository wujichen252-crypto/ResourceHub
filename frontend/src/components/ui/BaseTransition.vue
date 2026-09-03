<template>
  <Transition :name="transitionName" mode="out-in" v-bind="$attrs">
    <slot />
  </Transition>
</template>

<script setup lang="ts">
defineProps<{
  /** 过渡名称，默认 'fade-slide' */
  transitionName?: string
}>()
</script>
