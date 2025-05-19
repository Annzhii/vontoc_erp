import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Sent',
    component: () => import('@/pages/MailFolder.vue'),
  }
]

let router = createRouter({
  history: createWebHistory('/frontend'),
  routes,
})

export default router
