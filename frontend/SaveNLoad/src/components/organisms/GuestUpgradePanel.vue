<template>
  <CollapsibleCard
    title="Upgrade Guest Account"
    icon="fa-user-plus"
    collapse-id="guestUpgradeCollapse"
    header-class="guest-upgrade-header"
    icon-class="guest-upgrade-icon"
    title-class="guest-upgrade-title"
    chevron-class="guest-upgrade-chevron"
    chevron-id="guestUpgradeChevron"
  >
    <div v-if="migrationStatus === 'migrating'" class="alert alert-info mb-3">
      Migration in progress. Save/load is temporarily disabled.
    </div>
    <div v-else-if="migrationStatus === 'failed'" class="alert alert-warning mb-3">
      Migration failed. Please try again.
    </div>
    <form @submit.prevent="onSubmit">
      <div class="mb-3">
        <InputLabel for-id="guestUpgradeUsername" text="NEW USERNAME" />
        <TextInput
          id="guestUpgradeUsername"
          v-model="username"
          placeholder="Choose a username"
          :disabled="isSubmitting"
          required
        />
      </div>
      <div class="mb-3">
        <InputLabel for-id="guestUpgradeEmail" text="EMAIL" />
        <TextInput
          id="guestUpgradeEmail"
          v-model="email"
          type="email"
          placeholder="Enter your email"
          :disabled="isSubmitting"
          required
        />
      </div>
      <div class="mb-3">
        <InputLabel for-id="guestUpgradePassword" text="PASSWORD" />
        <PasswordField
          id="guestUpgradePassword"
          v-model="password"
          placeholder="Create a password"
          :disabled="isSubmitting"
          required
        />
      </div>
      <FormActions>
        <IconButton
          type="submit"
          variant="secondary"
          class="text-white fw-bold"
          :disabled="isSubmitting || migrationStatus === 'migrating'"
          :loading="isSubmitting"
        >
          Upgrade Account
        </IconButton>
      </FormActions>
    </form>
  </CollapsibleCard>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import CollapsibleCard from '@/components/molecules/CollapsibleCard.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import TextInput from '@/components/atoms/TextInput.vue';
import PasswordField from '@/components/molecules/PasswordField.vue';
import FormActions from '@/components/molecules/FormActions.vue';
import IconButton from '@/components/atoms/IconButton.vue';
import { useAuthStore } from '@/stores/auth';

const authStore = useAuthStore();

const username = ref('');
const email = ref('');
const password = ref('');

const migrationStatus = computed(() => authStore.user?.guest_migration_status || '');
const isSubmitting = computed(() => authStore.loading);

const onSubmit = async () => {
  if (isSubmitting.value || migrationStatus.value === 'migrating') {
    return;
  }
  const trimmedUsername = username.value.trim();
  if (trimmedUsername.toLowerCase().includes('guest')) {
    const t = (window as any).toastr;
    if (t?.error) {
      t.error('Username cannot contain "guest".');
    }
    return;
  }
  try {
    await authStore.upgradeGuest({
      username: trimmedUsername,
      email: email.value.trim(),
      password: password.value
    });
  } catch {
    // errors handled by store
  }
};

onMounted(() => {
  if (authStore.guestCredentials?.username) {
    username.value = authStore.guestCredentials.username;
  }
  if (authStore.guestCredentials?.password) {
    password.value = authStore.guestCredentials.password;
  }
});
</script>
