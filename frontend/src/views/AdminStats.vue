<template>
  <div class="container mt-4">
    <div v-if="loading" class="text-center">
      <div class="spinner-border" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <p class="mt-2">Loading statistics...</p>
    </div>

    <div v-else>
      <!-- Header -->
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="fw-bold text-dark">📊 Parking Statistics</h2>
        <button class="btn btn-outline-primary" @click="refreshStats">
          <i class="fas fa-sync-alt"></i> Refresh
        </button>
      </div>

      <div class="row mb-4">
        <div class="col-md-3 mb-3">
          <div class="card bg-primary text-white h-100">
            <div class="card-body text-center">
              <h3 class="mb-0">{{ stats.totalLots }}</h3>
              <p class="mb-0">Parking Lots</p>
            </div>
          </div>
        </div>
        <div class="col-md-3 mb-3">
          <div class="card bg-success text-white h-100">
            <div class="card-body text-center">
              <h3 class="mb-0">{{ stats.totalSpots }}</h3>
              <p class="mb-0">Total Spots</p>
            </div>
          </div>
        </div>
        <div class="col-md-3 mb-3">
          <div class="card bg-info text-white h-100">
            <div class="card-body text-center">
              <h3 class="mb-0">{{ stats.availableSpots }}</h3>
              <p class="mb-0">Available Spots</p>
            </div>
          </div>
        </div>
        <div class="col-md-3 mb-3">
          <div class="card bg-danger text-white h-100">
            <div class="card-body text-center">
              <h3 class="mb-0">{{ stats.occupiedSpots }}</h3>
              <p class="mb-0">Occupied Spots</p>
            </div>
          </div>
        </div>
      </div>

      <div class="row">
        <div class="col-12">
          <div class="card">
            <div class="card-header">
              <h5 class="mb-0">Lots Summary</h5>
            </div>
            <div class="card-body">
              <div class="row">
                <div v-for="lot in stats.lotStats" :key="lot.id" class="col-md-4 mb-3">
                  <div class="card border-primary">
                    <div class="card-header bg-primary text-white">
                      <h6 class="mb-0">{{ lot.name }}</h6>
                    </div>
                    <div class="card-body">
                      <div class="row text-center">
                        <div class="col-6">
                          <h5 class="text-primary">{{ lot.total_spots }}</h5>
                          <small class="text-muted">Total Spots</small>
                        </div>
                        <div class="col-6">
                          <h5 class="text-success">{{ lot.available_spots }}</h5>
                          <small class="text-muted">Available</small>
                        </div>
                      </div>
                      <hr>
                      <div class="text-center">
                        <h6 class="text-info">₹{{ lot.price_per_hour }}/hr</h6>
                        <small class="text-muted">Price per hour</small>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="row mt-4">
        <div class="col-12">
          <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
              <h5 class="mb-0">User Summary</h5>
              <div class="text-end">
                <small class="text-muted">Total Revenue: <strong>₹{{ stats.totalRevenue }}</strong></small>
              </div>
            </div>
            <div class="card-body">
              <div class="table-responsive">
                <table class="table table-striped">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Name</th>
                      <th>Email</th>
                      <th>Vehicle</th>
                      <th>Total Reservations</th>
                      <th>Total Hours</th>
                      <th>Total Spent (₹)</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="user in stats.userStats" :key="user.id">
                      <td>{{ user.id }}</td>
                      <td>{{ user.full_name }}</td>
                      <td>{{ user.email }}</td>
                      <td>{{ user.vehicle_number || '-' }}</td>
                      <td>{{ user.total_reservations }}</td>
                      <td>{{ user.total_hours }}</td>
                      <td>{{ user.total_spent }}</td>
                    </tr>
                    <tr v-if="stats.userStats.length === 0">
                      <td colspan="7" class="text-center text-muted">No user records available</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { getAdminStats } from '@/api.js'

export default {
  name: 'AdminStats',
  data() {
    return {
      loading: true,
      stats: {
        totalLots: 0,
        totalSpots: 0,
        availableSpots: 0,
        occupiedSpots: 0,
            lotStats: [],
            userStats: [],
            totalRevenue: 0
      }
    }
  },
  async mounted() {
    await this.loadStats()
  },
  methods: {
    async loadStats() {
      try {
        this.loading = true
        const response = await getAdminStats()
        this.stats = response.data
        this.loading = false
      } catch (error) {
        console.error('Error loading stats:', error)
        this.loading = false
        this.showNotification('Failed to load statistics', 'error')
      }
    },
    async refreshStats() {
      await this.loadStats()
    },
    showNotification(message, type = 'info') {
      alert(`${type.toUpperCase()}: ${message}`)
    }
  }
}
</script>

<style scoped>
.card {
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.progress {
  border-radius: 10px;
}

.table th {
  border-top: none;
}

.avatar {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.rank {
  width: 30px;
  text-align: center;
}

.badge {
  font-size: 0.8em;
}
</style> 