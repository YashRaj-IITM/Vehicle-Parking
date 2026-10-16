<template>
  <div class="container mt-5">
    <div v-if="notification" :class="['alert', notificationType === 'success' ? 'alert-success' : 'alert-danger']" role="alert" style="position:sticky;top:0;z-index:1000;">
      {{ notification }}
    </div>

    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2 class="fw-medium text-dark">Admin — Parking Lots</h2>
      <div>
        <router-link to="/admin/stats" class="btn btn-secondary me-2">📊 Stats</router-link>
        <router-link to="/admin/user-reminders" class="btn btn-info">🔔 Users</router-link>
      </div>
    </div>

    <div class="row">
      <div class="col-md-5">
        <div class="card mb-3">
          <div class="card-header">{{ editingId ? 'Edit Parking Lot' : 'Create Parking Lot' }}</div>
          <div class="card-body">
            <form @submit.prevent="saveLot">
              <div class="mb-2">
                <input v-model="form.prime_location_name" class="form-control" placeholder="Location name" required />
              </div>
              <div class="mb-2">
                <input v-model="form.price_per_hour" type="number" step="0.01" class="form-control" placeholder="Price per hour" required />
              </div>
              <div class="mb-2">
                <input v-model="form.address" class="form-control" placeholder="Address" required />
              </div>
              <div class="mb-2">
                <input v-model="form.pin_code" class="form-control" placeholder="Pin code" required />
              </div>
              <div class="mb-2">
                <input v-model.number="form.maximum_number_of_spots" type="number" class="form-control" placeholder="Maximum spots" required />
              </div>
              <button class="btn btn-primary w-100" type="submit">{{ editingId ? 'Save Changes' : 'Create Lot' }}</button>
              <button v-if="editingId" class="btn btn-outline-secondary w-100 mt-2" type="button" @click="cancelEdit">Cancel</button>
            </form>
          </div>
        </div>

        <div class="card">
          <div class="card-header">Parking Lots</div>
          <div class="card-body">
            <ul class="list-group">
              <li v-for="lot in lots" :key="lot.id" class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                  <strong>{{ lot.prime_location_name }}</strong>
                  <div class="small text-muted">{{ lot.address }} • ₹{{ lot.price_per_hour }}/hr</div>
                </div>
                <div class="text-end">
                  <div class="small">Available: <span class="badge bg-success">{{ lot.available_spots }}</span></div>
                  <div class="small">Occupied: <span class="badge bg-danger">{{ lot.occupied_spots }}</span></div>
                  <div class="mt-2">
                    <button class="btn btn-sm btn-outline-primary me-1" @click="viewSpots(lot.id)">View Spots</button>
                    <button class="btn btn-sm btn-outline-secondary me-1" @click="startEdit(lot)">Edit</button>
                    <button class="btn btn-sm btn-danger" @click="deleteLot(lot.id)">Delete</button>
                  </div>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div class="col-md-7">
        <div v-if="selectedLot" class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <div>
              <strong>{{ selectedLot.lot.name }}</strong>
              
            </div>
            <div>
              <button class="btn btn-sm btn-outline-secondary me-2" @click="closeSpots">Close</button>
            </div>
          </div>
          <div class="card-body">
            <div class="mb-3">Showing spots for lot: <strong>{{ selectedLot.lot.name }}</strong></div>
            <div class="row">
              <div v-for="spot in selectedLot.spots" :key="spot.id" class="col-3 mb-3">
                <div :class="['p-2 text-center rounded', spot.status === 'O' ? 'bg-danger text-white' : 'bg-light']">
                  <div><strong>{{ spot.spot_number }}</strong></div>
                  <div class="small">Status: {{ spot.status === 'O' ? 'Occupied' : 'Available' }}</div>
                  <div v-if="spot.current_reservation" class="small mt-1">By: {{ spot.current_reservation.user_full_name }} ({{ spot.current_reservation.vehicle_number || 'no vehicle no.' }})<br/>At: {{ formatDateTime(spot.current_reservation.parking_timestamp) }}</div>
                  <button v-else class="btn btn-sm btn-link text-danger p-0" @click="removeSpot(spot)">Delete</button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="card">
          <div class="card-body text-center text-muted">Select a lot and click "View Spots" to see spot status and reservations.</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { getParkingLots, createParkingLot, updateParkingLot, deleteParkingLot, getParkingSpots, deleteSpot } from '../api';

export default {
  name: 'AdminDashboard',
  data() {
    return {
      lots: [],
      selectedLot: null,
      selectedLotId: null,
      editingId: null,
      form: {
        prime_location_name: '',
        price_per_hour: 0,
        address: '',
        pin_code: '',
        maximum_number_of_spots: 0
      },
      notification: '',
      notificationType: ''
    };
  },
  methods: {
    async loadLots() {
      try {
        const res = await getParkingLots();
        this.lots = res.data;
      } catch (e) {
        console.error(e);
        this.showNotification('Failed to load lots', 'error');
      }
    },
    async saveLot() {
      try {
        const f = this.form;
        if (this.editingId) {
          await updateParkingLot(this.editingId, { ...f });
          this.showNotification('Parking lot updated', 'success');
          if (this.selectedLotId === this.editingId) await this.viewSpots(this.editingId);
        } else {
          await createParkingLot(f.prime_location_name, f.price_per_hour, f.address, f.pin_code, f.maximum_number_of_spots);
          this.showNotification('Parking lot created', 'success');
        }
        this.cancelEdit();
        await this.loadLots();
      } catch (e) {
        console.error(e);
        this.showNotification(e.response?.data?.error || 'Failed to save lot', 'error');
      }
    },
    startEdit(lot) {
      this.editingId = lot.id;
      this.form = {
        prime_location_name: lot.prime_location_name, price_per_hour: lot.price_per_hour,
        address: lot.address, pin_code: lot.pin_code, maximum_number_of_spots: lot.maximum_number_of_spots
      };
    },
    cancelEdit() {
      this.editingId = null;
      this.form = { prime_location_name: '', price_per_hour: 0, address: '', pin_code: '', maximum_number_of_spots: 0 };
    },
    async removeSpot(spot) {
      if (!confirm('Delete spot ' + spot.spot_number + '?')) return;
      try {
        await deleteSpot(spot.id);
        this.showNotification('Spot deleted', 'success');
        await this.viewSpots(this.selectedLotId);
        await this.loadLots();
      } catch (e) {
        this.showNotification(e.response?.data?.error || 'Failed to delete spot', 'error');
      }
    },
    async deleteLot(id) {
      if (!confirm('Delete this parking lot? Only allowed when all spots are empty. Past reservation records are kept.')) return;
      try {
        await deleteParkingLot(id);
        this.showNotification('Parking lot deleted', 'success');
        await this.loadLots();
        if (this.selectedLotId === id) this.selectedLot = null;
      } catch (e) {
        console.error(e);
        this.showNotification(e.response?.data?.error || 'Failed to delete lot', 'error');
      }
    },
    async viewSpots(lot_id) {
      try {
        const res = await getParkingSpots(lot_id);
        this.selectedLot = res.data;
        this.selectedLotId = lot_id;
      } catch (e) {
        console.error(e);
        this.showNotification('Failed to load spots', 'error');
      }
    },
    closeSpots() {
      this.selectedLot = null;
      this.selectedLotId = null;
    },
    showNotification(msg, type = 'success') {
      this.notification = msg; this.notificationType = type;
      setTimeout(()=>{ this.notification = ''; this.notificationType = ''; }, 3000);
    },
    formatDateTime(dt){ if(!dt) return ''; return new Date(dt).toLocaleString(); }
  },
  async mounted(){ await this.loadLots(); }
}
</script>

<style scoped>
.card {
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
  margin-bottom: 1.5rem;
}
.card-header {
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
  cursor: pointer;
}
.list-group-item-action:hover {
  background-color: #e9ecef;
  color: #007bff;
  transform: translateX(5px);
}
.active-admin {
  background-color: #007bff !important;
  color: #ffffff !important;
}

/* Ensure all elements inside active-admin have white text */
.active-admin * {
  color: #ffffff !important;
}

/* Override button colors inside active-admin */
.active-admin .btn {
  color: #ffffff !important;
  border-color: #ffffff !important;
}

.active-admin .btn:hover {
  background-color: rgba(255, 255, 255, 0.2) !important;
  color: #ffffff !important;
}

.active-admin .btn:active {
  background-color: rgba(255, 255, 255, 0.3) !important;
  color: #ffffff !important;
}

/* When editing, change text color to black for better readability */
.list-group-item input {
  color: #000000 !important;
}

.list-group-item input::placeholder {
  color: #6c757d !important;
}

/* Make dropdown text black in questions list */
.list-group-item select {
  color: #000000 !important;
}

.list-group-item select option {
  color: #000000 !important;
}

/* Ensure edit buttons and text are black when in edit mode */
.list-group-item .btn-success,
.list-group-item .btn-secondary {
  color: #000000 !important;
  border-color: #000000 !important;
}

.list-group-item .btn-success:hover,
.list-group-item .btn-secondary:hover {
  color: #000000 !important;
}

.list-group-item .btn-success:active,
.list-group-item .btn-secondary:active {
  color: #000000 !important;
}
.btn-outline-secondary, .btn-outline-danger {
  border-radius: 8px;
  padding: 4px 10px;
  margin-left: 2px;
  transition: all 0.2s;
}
.btn-outline-secondary:hover {
  background-color: #007bff;
  color: #fff;
}
.btn-outline-secondary:active {
  background-color: #0056b3;
  color: #fff !important;
}
.btn-outline-danger:hover {
  background-color: #dc3545;
  color: #fff;
}
.btn-outline-danger:active {
  background-color: #c82333;
  color: #fff !important;
}

/* Add white text effect for all buttons when clicked */
.btn:active {
  color: #fff !important;
}

/* Specific button types for better visual feedback */
.btn-primary:active {
  background-color:rgb(115, 127, 139) !important;
  color: #fff !important;
}

.btn-secondary:active {
  background-color: #545b62 !important;
  color: #fff !important;
}

.btn-success:active {
  background-color: #1e7e34 !important;
  color: #fff !important;
}

.btn-warning:active {
  background-color: #e0a800 !important;
  color: #fff !important;
}

.btn-info:active {
  background-color: #117a8b !important;
  color: #fff !important;
}

.btn-danger:active {
  background-color: #c82333 !important;
  color: #fff !important;
}
</style> 