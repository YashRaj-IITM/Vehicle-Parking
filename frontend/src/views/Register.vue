<template>
  <div class="register-container container d-flex justify-content-center align-items-center min-vh-100">
    <div class="card shadow-sm p-4 rounded-4 border-0" style="max-width: 400px; width: 100%;">
      <h3 class="text-center text-primary fw-bold mb-3">Create Your Account</h3>
      <div v-if="notification" :class="['alert', notificationType === 'success' ? 'alert-success' : 'alert-danger']" role="alert">
        {{ notification }}
      </div>
      <form @submit.prevent="registerUser">
        <div class="mb-3">
          <label for="email" class="form-label fw-semibold">Email</label>
          <input type="email" class="form-control rounded-3 shadow-sm" v-model="email" required placeholder="Enter your email">
        </div>
        <div class="mb-3">
          <label for="full_name" class="form-label fw-semibold">Full Name</label>
          <input type="text" class="form-control rounded-3 shadow-sm" v-model="fullName" required placeholder="Enter your full name">
        </div>
        <div class="mb-3">
          <label for="password" class="form-label fw-semibold">Password</label>
          <input type="password" class="form-control rounded-3 shadow-sm" v-model="password" required placeholder="Choose a strong password">
        </div>
        <div class="mb-3">
          <label for="confirm_password" class="form-label fw-semibold">Confirm Password</label>
          <input type="password" class="form-control rounded-3 shadow-sm" v-model="confirmPassword" required placeholder="Re-enter your password">
        </div>
        <button type="submit" class="btn btn-primary w-100 rounded-3 fw-semibold shadow-sm">Register</button>
      </form>
      <p class="mt-3 text-center small">
        Already have an account? <router-link to="/login" class="text-decoration-none text-primary fw-semibold">Login here</router-link>.
      </p>
    </div>
  </div>
</template>

<script>
import { register } from '../api';

export default {
  name: 'UserRegister',
  data() {
    return {
      email: '',
      fullName: '',
      password: '',
      confirmPassword: '',
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
    async registerUser() {
      this.notification = '';
      if (this.password !== this.confirmPassword) {
        this.showNotification('Passwords do not match.', 'error');
        return;
      }
      try {
        const res = await register(this.email, this.fullName, this.password);
        if (res.data.success) {
          this.showNotification('Registration successful! You can now log in.', 'success');
          setTimeout(() => this.$router.push('/login'), 1500);
        } else {
          this.showNotification(res.data.error || 'Registration failed.', 'error');
        }
      } catch (err) {
        this.showNotification(err.response?.data?.error || 'Registration failed.', 'error');
      }
    }
  }
};
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 60vh;
  /* background: url("/bg.jpg") no-repeat center center/cover; */
  border-radius: 25px;
}
.card {
  background: rgba(255, 255, 255, 0.9);
}
</style> 