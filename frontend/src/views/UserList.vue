<template>
  <div class="container mt-5">
    <div v-if="notification" :class="['alert', notificationType === 'success' ? 'alert-success' : 'alert-danger']">{{ notification }}</div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h2>Users</h2>
      <input v-model="q" class="form-control w-auto" placeholder="Search name, email, vehicle..." @input="debouncedLoad" />
    </div>
    <table class="table table-bordered table-hover bg-white">
      <thead class="table-light">
        <tr><th>ID</th><th>Full Name</th><th>Email</th><th>Phone</th><th>Vehicle</th><th>Role</th><th>Status</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td>{{ user.id }}</td>
          <td>{{ user.full_name }}</td>
          <td>{{ user.email }}</td>
          <td>{{ user.phone || 'N/A' }}</td>
          <td>{{ user.vehicle_number || 'N/A' }}</td>
          <td>{{ user.is_admin ? 'Admin' : 'User' }}</td>
          <td><span :class="['badge', user.active ? 'bg-success' : 'bg-secondary']">{{ user.active ? 'Active' : 'Blacklisted' }}</span></td>
          <td class="text-end">
            <template v-if="!user.is_admin">
              <button class="btn btn-sm btn-outline-warning me-1" @click="toggle(user)">{{ user.active ? 'Blacklist' : 'Activate' }}</button>
              <button class="btn btn-sm btn-outline-danger" @click="remove(user)">Delete</button>
            </template>
          </td>
        </tr>
        <tr v-if="!users.length"><td colspan="8" class="text-center text-muted">No users found.</td></tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import { getUsers, setUserStatus, deleteUser, errMsg } from '../api';

export default {
  name: 'UserList',
  data() {
    return { users: [], q: '', timer: null, notification: '', notificationType: '' };
  },
  methods: {
    notify(msg, type = 'success') {
      this.notification = msg; this.notificationType = type;
      setTimeout(() => { this.notification = ''; }, 3000);
    },
    debouncedLoad() { clearTimeout(this.timer); this.timer = setTimeout(this.load, 300); },
    async load() {
      try { this.users = (await getUsers(this.q)).data; }
      catch (e) { this.notify(errMsg(e, 'Failed to fetch users'), 'error'); }
    },
    async toggle(user) {
      try {
        await setUserStatus(user.id, user.active ? 'blacklist' : 'activate');
        this.notify(user.active ? 'User blacklisted' : 'User activated');
        await this.load();
      } catch (e) { this.notify(errMsg(e), 'error'); }
    },
    async remove(user) {
      if (!confirm('Delete ' + user.full_name + '? The account is anonymised and blocked; parking records are kept for reporting.')) return;
      try { await deleteUser(user.id); this.notify('User deleted'); await this.load(); }
      catch (e) { this.notify(errMsg(e), 'error'); }
    }
  },
  mounted() { this.load(); }
};
</script>

<style scoped>
.user-list-container { max-width: 700px; margin: 0 auto; padding: 2rem; }
table { width: 100%; border-collapse: collapse; }
th, td { border: 1px solid #ccc; padding: 0.5rem; text-align: center; }
</style> 