<template>
  <Layout>
    <router-view />
  </Layout>
</template>

<script setup>

import { computed } from 'vue'

import DesktopLayout from '@/components/DesktopLayout.vue'

const Layout = computed(() => {
	return DesktopLayout
})

</script>