<template>
  <AuthLayout title="Save N Load" subtitle="Reset your password to regain access.">
    <form @submit.prevent>
      <div class="mb-3">
        <label class="fs-6 opacity-50">EMAIL</label>
        <input
          class="color-primary form-control bg-primary border border-1 border-secondary rounded-1 py-2 text-white"
          type="email"
          placeholder="Enter your email"
          required
        />
      </div>
      <div class="d-grid">
        <button type="submit" class="btn btn-secondary text-white fw-bold mt-3 py-2">SEND OTP</button>
      </div>
      <p class="text-white fs-6 text-center mt-3">
        Remember your password?
        <RouterLink to="/login" class="text-secondary text-decoration-none fs-6">Login</RouterLink>
      </p>
    </form>
  </AuthLayout>
</template>

<script setup lang="ts">
import AuthLayout from '@/layouts/AuthLayout.vue';
</script>
