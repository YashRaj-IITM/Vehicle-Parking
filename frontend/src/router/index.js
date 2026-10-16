import { createRouter, createWebHistory } from 'vue-router';
import HomePage from '../views/Home.vue';
import UserLogin from '../views/Login.vue';
import UserRegister from '../views/Register.vue';
import UserDashboard from '../views/UserDashboard.vue';
import AdminDashboard from '../views/AdminDashboard.vue';
import AdminUserReminders from '../views/AdminUserReminders.vue';
import UserList from '../views/UserList.vue';
import AdminStats from '../views/AdminStats.vue';

const routes = [
  { path: '/', name: 'Home', component: HomePage },
  { path: '/login', name: 'Login', component: UserLogin, meta:{guest:true} },
  { path: '/register', name: 'Register', component: UserRegister, meta:{guest:true} },
  { path: '/dashboard', name: 'UserDashboard', component: UserDashboard, meta:{requiresAuth:true} },
  { path: '/admin', name: 'AdminDashboard', component: AdminDashboard, meta:{requiresAuth:true, requiresAdmin:true} },
  { path: '/admin/user-reminders', name: 'AdminUserReminders', component: AdminUserReminders, meta:{requiresAuth:true, requiresAdmin:true} },
  { path: '/admin/user-list', name: 'UserList', component: UserList, meta:{requiresAuth:true, requiresAdmin:true} },
  { path: '/admin/stats', name: 'AdminStats', component: AdminStats, meta:{requiresAuth:true, requiresAdmin:true} },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token');
  const isAdmin = localStorage.getItem('is_admin') === 'true';
  if (to.meta.requiresAuth && !token) {
    return next('/login');
  }
  if (to.meta.requiresAdmin && !isAdmin) {
    return next('/dashboard');
  }
  if (to.meta.guest && token) {
    return next(isAdmin ? '/admin' : '/dashboard');
  }
  if (to.path === '/' && token) {
    return next(isAdmin ? '/admin' : '/dashboard');
  }
  next();
});

export default router; 