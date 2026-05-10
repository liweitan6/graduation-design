import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    component: () => import('../components/Layout.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
      },
      {
        path: 'diversity',
        name: 'Diversity',
        component: () => import('../views/Diversity.vue'),
      },
      {
        path: 'assistant',
        name: 'Assistant',
        component: () => import('../views/Assistant.vue'),
      },
      {
        path: 'cases',
        name: 'Cases',
        component: () => import('../views/Cases.vue'),
      },
      {
        path: 'import',
        name: 'Import',
        component: () => import('../views/Import.vue'),
      },
      {
        path: 'coverage',
        name: 'Coverage',
        component: () => import('../views/Coverage.vue'),
      },
      {
        path: 'efficiency',
        name: 'Efficiency',
        component: () => import('../views/Efficiency.vue'),
      },
      {
        path: 'correlations',
        name: 'Correlations',
        component: () => import('../views/Correlations.vue'),
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
