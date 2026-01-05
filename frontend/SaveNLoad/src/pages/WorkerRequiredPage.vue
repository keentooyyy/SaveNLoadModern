<template>
  <AppLayout>
    <div class="container d-flex align-items-center justify-content-center min-vh-80">
      <div class="text-center w-100 max-width-600">
        <div class="mb-4">
          <img src="/images/icon.png" alt="Worker Missing" width="80" height="80" />
        </div>
        <h2 class="text-white mb-3">Worker Missing</h2>
        <p class="text-white-50 mb-4">To use the application you need to have a client worker running.</p>

        <div class="p-3 mb-4 rounded d-flex align-items-start worker-id-hint">
          <i class="fas fa-info-circle me-3 mt-1 fs-5"></i>
          <div>
            <strong>Tip:</strong> The correct Worker ID contains your PC name + a unique code.<br />
            Example: <code>YOUR-PC-NAME_a1:b2:c3:d4:e5:f6</code>
          </div>
        </div>

        <div class="card bg-dark border-secondary p-4 text-center">
          <div class="mb-3">
            <div class="spinner-border text-white spinner-lg" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
          </div>
          <h5 class="text-white mb-2">Searching for Workers</h5>
          <p class="text-white-50 mb-0">Please ensure the SaveNLoad client is running on your PC.</p>
        </div>
        <button class="btn btn-outline-light mt-3" type="button">
          <i class="fas fa-sync-alt me-2"></i>Refresh List
        </button>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import AppLayout from '@/layouts/AppLayout.vue';
</script>
