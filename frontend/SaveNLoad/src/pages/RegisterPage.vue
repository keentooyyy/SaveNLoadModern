<template>
  <AuthLayout title="Save N Load" subtitle="Create your account to get started.">
    <form @submit.prevent>
      <div class="mb-3">
        <label class="fs-6 opacity-50">USERNAME</label>
        <input
          class="color-primary form-control bg-primary border border-1 border-secondary rounded-1 py-2 text-white"
          type="text"
          placeholder="Enter your username"
          required
        />
      </div>
      <div class="mb-3">
        <label class="fs-6 opacity-50">EMAIL</label>
        <input
          class="color-primary form-control bg-primary border border-1 border-secondary rounded-1 py-2 text-white"
          type="email"
          placeholder="Enter your email"
          required
        />
      </div>
      <div class="mb-3">
        <label class="fs-6 mb-0 opacity-50">PASSWORD</label>
        <PasswordField placeholder="Enter your password" />
      </div>
      <div class="mb-3">
        <label class="fs-6 mb-0 opacity-50">REPEAT PASSWORD</label>
        <PasswordField placeholder="Repeat your password" />
      </div>
      <div class="d-grid">
        <button type="submit" class="btn btn-secondary text-white fw-bold mt-3 py-2">REGISTER</button>
      </div>
      <p class="text-white fs-6 text-center mt-3">
        Already have an account?
        <RouterLink to="/login" class="text-secondary text-decoration-none fs-6">Login</RouterLink>
      </p>
    </form>
  </AuthLayout>
</template>

<script setup lang="ts">
import AuthLayout from '@/layouts/AuthLayout.vue';
import PasswordField from '@/components/molecules/PasswordField.vue';
</script>
