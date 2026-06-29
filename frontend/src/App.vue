<template>
  <NavBar v-if="showNav" />
  <router-view />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import NavBar from './components/NavBar.vue'

const route = useRoute()

const showNav = computed(() => {
  const name = route.name as string
  return ['search', 'review', 'history', 'config'].includes(name)
})
</script>
