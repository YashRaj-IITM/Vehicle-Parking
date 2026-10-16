<template>
  <div class="container mt-5">
    <div class="text-center">
      <h1 class="display-4 fw-bold">Welcome to Claude Park</h1>
      <p class="lead">Find parking spots, manage reservations, and track your parking history!</p>
      <router-link to="/login" class="btn btn-primary btn-lg m-2">Login</router-link>
      <router-link to="/register" class="btn btn-outline-primary btn-lg m-2">Register</router-link>
    </div>
  </div>
</template>

<script>
export default {
  name: 'HomePage'
};
</script>

<style scoped>
.container {
  margin-top: 5rem;
}
</style>