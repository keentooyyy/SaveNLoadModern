<template>
  <BaseCard>
    <SectionHeader title="Manage accounts" subtitle="Admin controls" />
    <div class="table-responsive mt-3">
      <table class="table table-dark table-borderless align-middle">
        <thead>
          <tr class="text-uppercase text-secondary small">
            <th>User</th>
            <th>Email</th>
            <th>Role</th>
            <th class="text-end">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>{{ user.name }}</td>
            <td class="text-secondary">{{ user.email }}</td>
            <td><BaseBadge>{{ user.role }}</BaseBadge></td>
            <td class="text-end">
              <div class="d-inline-flex gap-2">
                <BaseButton size="sm" variant="secondary">Reset</BaseButton>
                <BaseButton size="sm" variant="outline-light">Remove</BaseButton>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import BaseBadge from '@/components/atoms/BaseBadge.vue';
import BaseButton from '@/components/atoms/BaseButton.vue';
import BaseCard from '@/components/atoms/BaseCard.vue';
import SectionHeader from '@/components/molecules/SectionHeader.vue';

defineProps({
  users: { type: Array, default: () => [] }
});
</script>
