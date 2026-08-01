<template>
  <n-card :bordered="false" class="stat-card">
    <n-stat :label="title" :value="value">
      <template #prefix>
        <span style="font-size: 20px">{{ icon }}</span>
      </template>
    </n-stat>
  </n-card>
</template>

<script setup>
defineProps({ title: String, value: Number, type: String, icon: String })
</script>

<style scoped>
.stat-card {
  text-align: center;
}
</style>
