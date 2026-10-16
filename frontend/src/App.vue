<template>
  <div id="app">
    <nav class="navbar navbar-expand-lg navbar-light bg-light shadow-sm">
      <div class="container-fluid">
        <router-link class="navbar-brand fw-bold d-flex align-items-center" to="/">Claude&nbsp;Park
          <span v-if="isLoggedIn" :class="['badge', isAdmin ? 'bg-danger' : 'bg-primary', 'ms-2']">{{ isAdmin ? 'Admin' : 'User' }}</span>
        </router-link>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navBar" aria-controls="navBar" aria-expanded="false" aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navBar">
          <ul class="navbar-nav ms-auto mb-2 mb-lg-0">
            <li class="nav-item" v-if="!isLoggedIn">
              <router-link class="nav-link" to="/login">Login</router-link>
            </li>
            <li class="nav-item" v-if="!isLoggedIn">
              <router-link class="nav-link" to="/register">Register</router-link>
            </li>
            <li class="nav-item" v-if="isLoggedIn && !isAdmin">
              <router-link class="nav-link" to="/dashboard">Dashboard</router-link>
            </li>

            <li class="nav-item" v-if="isLoggedIn && isAdmin && $route.path !== '/admin'">
              <router-link class="nav-link" to="/admin">Admin</router-link>
            </li>
            <li class="nav-item" v-if="isLoggedIn && isAdmin">
              <router-link class="nav-link" to="/admin/user-list">Users</router-link>
            </li>
            <li class="nav-item" v-if="isLoggedIn && isAdmin">
              <router-link class="nav-link" to="/admin/stats">Stats</router-link>
            </li>
            <li class="nav-item" v-if="isLoggedIn && isAdmin">
              <router-link class="nav-link" to="/admin/user-reminders">📧 Reminders</router-link>
            </li>
            <li class="nav-item" v-if="isLoggedIn">
              <button class="btn btn-sm btn-outline-danger ms-lg-3" @click="logout">Logout</button>
            </li>
          </ul>
        </div>
      </div>
    </nav>
    <router-view />
  </div>
</template>

<script>
import { setAuthToken, logout } from './api';

export default {
  name: 'App',
  computed: {
    isLoggedIn() {
      return !!localStorage.getItem('token');
    },
    isAdmin() {
      return localStorage.getItem('is_admin') === 'true';
    }
  },
  methods: {
    async logout() {
      try {
        await logout();
      } catch (e) {
        /* ignore logout error */
      }
      localStorage.clear();
      setAuthToken(null);
      // Force page reload to update navbar immediately
      window.location.reload();
    }
  }
};
</script>

<style>
body {
  margin: 0;
  font-family: Avenir, Helvetica, Arial, sans-serif;
}
</style>
