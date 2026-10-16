<template>
  <div class="container mt-4">
    <!-- Header -->
    <div class="row mb-4">
      <div class="col-12">
        <h2 class="text-center mb-3">📧 Parking Reminders</h2>
        <p class="text-center text-muted">Schedule reminders for parking lot users</p>
      </div>
    </div>

    <!-- Notification -->
    <div v-if="notification" :class="['alert', notificationType === 'success' ? 'alert-success' : 'alert-danger']" role="alert">
      {{ notification }}
    </div>
    
    <!-- Send Reminders -->
    <div class="card mb-4">
      <div class="card-header">
        <h5 class="mb-0">📤 Send Parking Reminders</h5>
      </div>
      <div class="card-body">
        <div class="row">
          <div class="col-md-6">
            <label class="form-label">Reminder Time</label>
            <input type="datetime-local" v-model="reminderTime" class="form-control" required>
          </div>
          <div class="col-md-6">
            <label class="form-label">Subject</label>
            <input type="text" v-model="reminderSubject" class="form-control" placeholder="Parking Reminder">
          </div>
        </div>
        <div class="row mt-3">
          <div class="col-12">
            <label class="form-label">Message</label>
            <textarea v-model="reminderBody" class="form-control" rows="2" placeholder="Reminder about your parking..."></textarea>
          </div>
        </div>
        <div class="row mt-3">
          <div class="col-12">
            <button @click="sendReminders" class="btn btn-primary">
              <i class="fas fa-paper-plane"></i> Send Reminders
            </button>
          </div>
        </div>
        <!-- User selection -->
        <div class="row mt-4">
          <div class="col-12">
            <label class="form-label">Select Users</label>
            <div class="mb-2">
              <input type="checkbox" id="selectAll" v-model="selectAll" @change="toggleSelectAll">
              <label for="selectAll" class="ms-2">Select All</label>
            </div>
            <div class="user-list" style="max-height:250px; overflow:auto; border:1px solid #e9ecef; padding:10px; border-radius:8px;">
              <div v-if="users.length === 0" class="text-muted">No users found.</div>
              <div v-for="user in users" :key="user.id" class="form-check">
                <input class="form-check-input" type="checkbox" :id="'user-'+user.id" :value="user.id" v-model="selectedUserIds">
                <label class="form-check-label ms-2" :for="'user-'+user.id">{{ user.full_name }} — <small class="text-muted">{{ user.email }}</small></label>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
            
    <!-- Scheduling UI removed -->

  </div>
</template>

<script>
import { getUsers, scheduleBulkReminders } from '../api';

export default {
  name: 'AdminUserReminders',
  data() {
    return {
      users: [],
      selectedUserIds: [],
      selectAll: false,
      reminderTime: '',
      reminderSubject: 'Parking Reminder',
      reminderBody: 'Check your parking status and manage your reservations.',
      notification: '',
      notificationType: '',
      
  // Parking Reminder Scheduling (removed from UI)
    };
  },
  methods: {
    showNotification(message, type = 'success') {
      this.notification = message;
      this.notificationType = type;
      setTimeout(() => {
        this.notification = '';
        this.notificationType = '';
      }, 3000);
    },

    async loadUsers() {
      try {
        const response = await getUsers();
        this.users = response.data.filter(u => !u.is_admin && u.active);
        // reset selections when users reload
        this.selectedUserIds = [];
        this.selectAll = false;
      } catch (error) {
        this.showNotification('Failed to load users.', 'error');
      }
    },

    async sendReminders() {
      if (!this.reminderTime) {
        this.showNotification('Please select a reminder time.', 'error');
        return;
      }

      try {
        const localDate = new Date(this.reminderTime);
        const targetIds = (this.selectedUserIds && this.selectedUserIds.length) ? this.selectedUserIds : this.users.map(user => user.id);
        const response = await scheduleBulkReminders(
          targetIds,
          localDate.toISOString(),
          this.reminderSubject,
          this.reminderBody
        );

        const sentCount = response && response.data && (response.data.count || response.data.scheduled_count || 0);
        this.showNotification(`Reminders scheduled for ${sentCount} users!`);
        this.reminderTime = '';
        this.reminderSubject = 'Parking Reminder';
        this.reminderBody = 'Check your parking status and manage your reservations.';
        await this.loadUsers();
      } catch (error) {
        this.showNotification(error.response?.data?.error || 'Failed to send reminders.', 'error');
      }
    },

    // Toggle select-all checkbox
    toggleSelectAll() {
      if (this.selectAll) {
        this.selectedUserIds = this.users.map(u => u.id);
      } else {
        this.selectedUserIds = [];
      }
    }
  },

  async mounted() {
    await this.loadUsers();
  }
};
</script>

<style scoped>
.card {
  border: none;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  border-radius: 12px;
}

.card-header {
  background-color: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  border-radius: 12px 12px 0 0 !important;
}

.btn {
  border-radius: 8px;
  padding: 0.5rem 1rem;
}

.form-control, .form-select {
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.form-control:focus, .form-select:focus {
  border-color: #80bdff;
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}
</style>
