<template>
  <div class="container mt-5">
    <div v-if="notification" :class="['alert', notificationType === 'success' ? 'alert-success' : 'alert-danger']" role="alert" style="position:sticky;top:0;z-index:1000;">
      {{ notification }}
    </div>
    <!-- Search removed from User Dashboard -->

    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2 class="fw-bold text-dark">Welcome, {{ user.full_name }} 👋</h2>
    </div>

    <div class="row">
      <div class="col-md-6">
        <div class="card mb-3">
          <div class="card-header">Available Parking Lots</div>
          <div class="card-body">
            <input v-model="q" class="form-control mb-3" placeholder="Search by name, address or PIN..." @input="debouncedSearch" />
            <ul class="list-group">
              <li v-for="lot in lots" :key="lot.id" class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                  <strong>{{ lot.prime_location_name }}</strong>
                  <div class="small text-muted">{{ lot.address }} • ₹{{ lot.price_per_hour }}/hr</div>
                </div>
                <div>
                  <div class="small">Available: <span class="badge bg-success">{{ lot.available_spots }}</span></div>
                  <button class="btn btn-sm btn-primary mt-2" @click="reserve(lot.id)" :disabled="lot.available_spots === 0 || hasActiveReservation">Reserve</button>
                </div>
              </li>
            </ul>
          </div>
        </div>

        <div class="card">
          <div class="card-header">My Reservations</div>
          <div class="card-body">
            <ul class="list-group">
              <li v-for="r in reservations" :key="r.id" class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                  Spot: <strong>{{ r.spot_number }}</strong> in Lot: <strong>{{ r.lot_name || r.lot_id }}</strong>
                  <div class="small text-muted">In: {{ formatDateTime(r.parking_timestamp) }}</div>
                </div>
                <div>
                  <div class="small">Duration: {{ r.duration_hours }} hrs <span v-if="!r.is_active">• ₹{{ r.total_cost }}</span></div>
                  <button v-if="r.is_active" class="btn btn-sm btn-danger mt-2" @click="release(r.id)">Release</button>
                  <button v-else class="btn btn-sm btn-outline-secondary mt-2" @click="removeRecord(r)">Remove</button>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div class="col-md-6">
        <div class="card">
          <div class="card-header">Your Summary</div>
          <div class="card-body">
            <p>Total Reservations: <strong>{{ stats.total_reservations }}</strong></p>
            <p>Total Hours Parked: <strong>{{ stats.total_hours }}</strong></p>
            <p>Total Spent: <strong>₹{{ stats.total_spent }}</strong></p>
            <button class="btn btn-outline-success btn-sm" :disabled="exporting" @click="exportCsv">
              {{ exporting ? 'Preparing CSV...' : 'Export history (CSV)' }}
            </button>
          </div>
        </div>
        <div class="card mt-3">
          <div class="card-header">My Profile</div>
          <div class="card-body">
            <form @submit.prevent="saveProfile">
              <input v-model="profile.full_name" class="form-control mb-2" placeholder="Full name" required />
              <input v-model="profile.phone" class="form-control mb-2" placeholder="Phone" maxlength="15" />
              <input v-model="profile.vehicle_number" class="form-control mb-2" placeholder="Vehicle number (e.g. KA01AB1234)" maxlength="20" />
              <button class="btn btn-primary btn-sm" type="submit">Save profile</button>
              <button class="btn btn-outline-danger btn-sm ms-2" type="button" @click="removeAccount">Delete account</button>
            </form>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { listParkingLots, reserveSpot, myReservations, releaseSpot, getUserStats, getProfile, updateProfile, deleteReservation, deleteAccount, startExport, exportStatus, errMsg } from '../api';

export default {
  name: 'UserDashboard',
  data() {
    return {
      user: { full_name: 'User' },
      lots: [],
      reservations: [],
      stats: { total_reservations: 0, total_hours: 0, total_spent: 0 },
      q: '', timer: null, exporting: false,
      profile: { full_name: '', phone: '', vehicle_number: '' },
      notification: '',
      notificationType: ''
    }
  },
  computed: {
    hasActiveReservation() {
      return this.reservations && this.reservations.some(r => r.is_active);
    }
  },
  methods: {
    async loadLots() {
      try {
        const res = await listParkingLots(this.q);
        this.lots = res.data;
      } catch (e) {
        console.error(e);
        this.showNotification('Failed to load lots', 'error');
      }
    },
    async reserve(lot_id) {
      try {
        const res = await reserveSpot(lot_id);
        this.showNotification('Reserved spot: ' + res.data.reservation.spot_number, 'success');
        await this.loadReservations();
        await this.loadLots();
        await this.loadStats();
      } catch (e) {
        console.error(e);
        this.showNotification(e.response?.data?.error || 'Failed to reserve', 'error');
      }
    },
    async loadReservations() {
      try {
        const res = await myReservations();
        this.reservations = res.data;
      } catch (e) {
        console.error(e);
      }
    },
    async release(reservation_id) {
      if (!confirm('Release this parking reservation?')) return;
      try {
        const res = await releaseSpot(reservation_id);
        this.showNotification('Released. Total cost: ₹' + res.data.reservation.total_cost, 'success');
        await this.loadReservations();
        await this.loadLots();
        await this.loadStats();
      } catch (e) {
        console.error(e);
        this.showNotification(e.response?.data?.error || 'Failed to release', 'error');
      }
    },
    debouncedSearch() { clearTimeout(this.timer); this.timer = setTimeout(this.loadLots, 300); },
    async loadProfile() {
      try { this.profile = (await getProfile()).data; } catch (e) { console.error(e); }
    },
    async saveProfile() {
      try {
        const res = await updateProfile(this.profile);
        this.profile = res.data.user;
        localStorage.setItem('full_name', this.profile.full_name);
        this.user.full_name = this.profile.full_name;
        this.showNotification('Profile updated', 'success');
      } catch (e) { this.showNotification(errMsg(e, 'Failed to update profile'), 'error'); }
    },
    async removeRecord(r) {
      try { await deleteReservation(r.id); await this.loadReservations(); await this.loadStats(); }
      catch (e) { this.showNotification(errMsg(e), 'error'); }
    },
    async removeAccount() {
      if (!confirm('Delete your account? Your personal details are erased and you will not be able to log in again.')) return;
      try { await deleteAccount(); localStorage.clear(); window.location.assign('/'); }
      catch (e) { this.showNotification(errMsg(e), 'error'); }
    },
    async exportCsv() {
      this.exporting = true;
      try {
        const start = await startExport();
        for (let i = 0; i < 30; i++) {
          await new Promise((r) => setTimeout(r, 1500));
          const res = await exportStatus(start.data.task_id);
          if (res.status === 200) {
            const url = URL.createObjectURL(res.data);
            const a = document.createElement('a');
            a.href = url; a.download = 'reservations.csv'; a.click();
            URL.revokeObjectURL(url);
            this.showNotification('CSV downloaded (a copy was also emailed to you)', 'success');
            return;
          }
        }
        this.showNotification('Export is taking long, please try again later', 'error');
      } catch (e) {
        this.showNotification('Export unavailable: start Redis and the Celery worker', 'error');
      } finally { this.exporting = false; }
    },
    async loadStats() {
      try {
        const res = await getUserStats();
        this.stats = res.data;
      } catch (e) { console.error(e); }
    },
    showNotification(msg, type='success') { this.notification = msg; this.notificationType = type; setTimeout(()=>{ this.notification=''; },3000); },
    formatDateTime(dt){ if(!dt) return ''; return new Date(dt).toLocaleString(); }
  },
  async mounted(){
    // populate user name from localStorage (set during login)
    try {
      const name = localStorage.getItem('full_name');
      if (name) this.user.full_name = name;
    } catch (e) { /* ignore if not available */ }
    await this.loadProfile();
    await this.loadLots();
    await this.loadReservations();
    await this.loadStats();
  }
}
</script>

<style scoped>
body {
  background-color: #f4f6f9;
}
.card {
  border-radius: 12px;
}
.card-header {
  background-color: #ffffff !important;
  border-bottom: 1px solid #ddd;
  font-size: 16px;
  padding: 12px 16px;
}
.list-group-item {
  transition: all 0.3s ease-in-out;
  border-radius: 8px;
  margin-bottom: 6px;
  font-size: 15px;
  padding: 12px 14px;
  border: none;
}
.list-group-item:hover {
  background-color: rgba(0, 123, 255, 0.1);
  color: #007bff;
  transform: translateX(5px);
}
.active {
  background-color: #007bff !important;
  color: #ffffff !important;
}
.quiz-card {
  transition: all 0.3s ease-in-out;
  background: #ffffff;
  border-radius: 10px;
  padding: 12px;
  text-align: center;
}
.quiz-card:hover {
  background-color: #f8f9fa;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
}
.btn-outline-primary {
  border-radius: 8px;
  padding: 6px 14px;
  transition: all 0.3s ease-in-out;
}
.btn-outline-primary:hover {
  background-color: #007bff;
  color: #fff;
}
.past-attempt-card {
  border-left: 5px solid #007bff;
  padding: 8px;
  transition: all 0.3s ease-in-out;
}
.past-attempt-card:hover {
  background-color: #f8f9fa;
}
#toggle-past-attempts {
  font-size: 14px;
  padding: 4px 10px;
  border-radius: 6px;
}

/* Search removed */

.input-group-text {
  border: none;
}

.form-control:focus {
  border-color: #007bff;
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}
</style> 