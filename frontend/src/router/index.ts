import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
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
      path: '/asset/:id',
      name: 'asset-detail',
      component: () => import('../pages/AssetDetailPage.vue'),
    },
    {
      path: '/review/:id',
      name: 'review-detail',
      component: () => import('../pages/ReviewDetailPage.vue'),
    },
    {
      path: '/config',
      name: 'config',
      component: () => import('../pages/ConfigPage.vue'),
    },
  ],
})

export default router
