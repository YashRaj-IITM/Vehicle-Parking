<template>
  <div class="login-container">
    <div class="login-box">
      <h4 class="text-center">Welcome to</h4>
      <h3 class="text-center highlight">Vehicle Parking Management System</h3>
      <p class="text-center subtext">Sign in to continue</p>
      <div v-if="notification" :class="['alert', notificationType === 'success' ? 'alert-success' : 'alert-danger']" role="alert">
        {{ notification }}
      </div>
      <form @submit.prevent="loginUser">
        <div class="mb-3">
          <label for="email" class="form-label">Email</label>
          <input type="email" class="form-control" v-model="email" placeholder="Enter your email" required>
        </div>
        <div class="mb-3">
          <label for="password" class="form-label">Password</label>
          <input type="password" class="form-control" v-model="password" placeholder="Enter your password" required>
        </div>
        <button type="submit" class="btn-login">Login</button>
      </form>
    </div>
  </div>
</template>

<script>
import { login, setAuthToken } from '../api';

export default {
  name: 'UserLogin',
  data() {
    return {
      email: '',
      password: '',
      notification: '',
      notificationType: '',
      notificationTimeout: null
    };
  },
  methods: {
    showNotification(message, type = 'error') {
      this.notification = message;
      this.notificationType = type;
      if (this.notificationTimeout) clearTimeout(this.notificationTimeout);
      this.notificationTimeout = setTimeout(() => {
        this.notification = '';
        this.notificationType = '';
      }, 3000);
    },
    async loginUser() {
      this.notification = '';
      try {
        const res = await login(this.email, this.password);
        if (res.data.success) {
          setAuthToken(res.data.token);
          localStorage.setItem('full_name', res.data.user.full_name);
          localStorage.setItem('is_admin', res.data.user.is_admin);
          // Force page reload to update navbar immediately
          window.location.reload();
        } else {
          this.showNotification(res.data.error || 'Login failed.', 'error');
        }
      } catch (err) {
        this.showNotification(err.response?.data?.error || 'Login failed. Please check your credentials.', 'error');
      }
    }
  }
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 85vh;
  /* background: url("/bgg.jpg") no-repeat center center/cover; */
  border-radius: 25px;
}
.login-box {
  background: rgba(255, 255, 255, 0.933);
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.1);
  max-width: 360px;
  width: 100%;
}
h2 {
  font-size: 1.8rem;
  color: #1F2937;
  font-weight: 600;
}
.highlight {
  color: #3B82F6;
}
.subtext {
  font-size: 1rem;
  color: #6B7280;
  margin-bottom: 20px;
}
.form-control {
  border-radius: 8px;
  padding: 10px;
  border: 1px solid #D1D5DB;
  font-size: 1rem;
  background: #F9FAFB;
}
.form-control:focus {
  border-color: #3B82F6;
  box-shadow: 0px 0px 6px rgba(59, 130, 246, 0.3);
}
.btn-login {
  display: block;
  width: 100%;
  padding: 12px;
  font-size: 1.1rem;
  font-weight: 600;
  color: white;
  background: #3B82F6;
  border-radius: 8px;
  transition: all 0.3s ease-in-out;
  border: none;
  text-align: center;
  cursor: pointer;
}
.btn-login:hover {
  background: #2563EB;
  transform: translateY(-2px);
  box-shadow: 0px 6px 12px rgba(59, 130, 246, 0.3);
}
</style> 