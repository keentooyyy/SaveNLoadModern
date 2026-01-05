<template>
  <AuthLayout title="Save N Load" subtitle="Set your new password.">
    <form @submit.prevent>
      <div class="mb-3">
        <label class="fs-6 opacity-50">NEW PASSWORD</label>
        <PasswordField placeholder="Enter new password" />
      </div>
      <div class="mb-3">
        <label class="fs-6 opacity-50">CONFIRM PASSWORD</label>
        <PasswordField placeholder="Confirm new password" />
      </div>
      <div class="d-grid">
        <button type="submit" class="btn btn-secondary text-white fw-bold mt-3 py-2">RESET PASSWORD</button>
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
import PasswordField from '@/components/molecules/PasswordField.vue';
</script>
