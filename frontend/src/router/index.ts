import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      redirect: '/search',
    },
    {
      path: '/search',
      name: 'search',
      component: () => import('../pages/SearchPage.vue'),
    },
    {
      path: '/review',
      name: 'review',
      component: () => import('../pages/ReviewPage.vue'),
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../pages/HistoryPage.vue'),
    },
    {
      path: '/config',
      name: 'config',
      component: () => import('../pages/ConfigPage.vue'),
    },
  ],
})

export default router
