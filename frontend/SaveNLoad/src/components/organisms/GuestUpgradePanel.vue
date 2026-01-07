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
          icon="fa-user-check"
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
import { useSettingsStore } from '@/stores/settings';

const authStore = useAuthStore();
const settingsStore = useSettingsStore();

const GUEST_CREDS_KEY = 'savenload_guest_credentials';

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
    const data = await authStore.upgradeGuest({
      username: trimmedUsername,
      email: email.value.trim(),
      password: password.value
    });
    const operationId = data?.operation_id;
    if (operationId) {
      await pollUpgradeStatus(operationId);
    } else {
      await authStore.refreshUser();
      if (!authStore.user?.is_guest) {
        clearGuestCredentials();
      }
    }
  } catch {
    // errors handled by store
  }
};

const pollUpgradeStatus = async (operationId: string) => {
  const maxAttempts = 30;
  const delayMs = 2000;
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      const status = await settingsStore.checkOperationStatus(operationId);
      if (status?.completed || status?.failed) {
        await authStore.refreshUser();
        if (status?.completed && !authStore.user?.is_guest) {
          clearGuestCredentials();
        }
        return;
      }
    } catch {
      // ignore poll errors
    }
    await new Promise((resolve) => setTimeout(resolve, delayMs));
  }
  await authStore.refreshUser();
  if (!authStore.user?.is_guest) {
    clearGuestCredentials();
  }
};

const clearGuestCredentials = () => {
  authStore.guestCredentials = null;
  try {
    window.sessionStorage.removeItem(GUEST_CREDS_KEY);
  } catch {
    // ignore
  }
  try {
    window.localStorage.removeItem(GUEST_CREDS_KEY);
  } catch {
    // ignore
  }
};

onMounted(() => {
  if (authStore.guestCredentials?.username) {
    username.value = authStore.guestCredentials.username;
  }
  if (authStore.guestCredentials?.password) {
    password.value = authStore.guestCredentials.password;
  }
  if (!username.value && authStore.user?.username) {
    username.value = authStore.user.username;
  }
  if (!password.value) {
    try {
      const stored = window.sessionStorage.getItem(GUEST_CREDS_KEY)
        || window.localStorage.getItem(GUEST_CREDS_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as { username?: string; password?: string };
        if (!username.value && parsed?.username) {
          username.value = parsed.username;
        }
        if (!password.value && parsed?.password) {
          password.value = parsed.password;
        }
      }
    } catch {
      // ignore
    }
  }
});
</script>
