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
import { onMounted, ref, toRef } from 'vue';
import CollapsibleCard from '@/components/molecules/CollapsibleCard.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import TextInput from '@/components/atoms/TextInput.vue';
import PasswordField from '@/components/molecules/PasswordField.vue';
import FormActions from '@/components/molecules/FormActions.vue';
import IconButton from '@/components/atoms/IconButton.vue';
const props = defineProps<{
  migrationStatus: string;
  isSubmitting: boolean;
  guestCredentials: { username?: string; password?: string } | null;
  currentUsername: string;
  upgradeGuest: (payload: { username: string; email: string; password: string }) => Promise<any>;
  refreshUser: () => Promise<any>;
  checkOperationStatus: (operationId: string) => Promise<any>;
  clearGuestCredentials: () => void;
  getIsGuest: () => boolean;
}>();

const GUEST_CREDS_KEY = 'savenload_guest_credentials';

const username = ref('');
const email = ref('');
const password = ref('');
const migrationStatus = toRef(props, 'migrationStatus');
const isSubmitting = toRef(props, 'isSubmitting');

const onSubmit = async () => {
  if (props.isSubmitting || props.migrationStatus === 'migrating') {
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
    const data = await props.upgradeGuest({
      username: trimmedUsername,
      email: email.value.trim(),
      password: password.value
    });
    const operationId = data?.operation_id;
    if (operationId) {
      await pollUpgradeStatus(operationId);
    } else {
      await props.refreshUser();
      if (!props.getIsGuest()) {
        props.clearGuestCredentials();
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
      const status = await props.checkOperationStatus(operationId);
      if (status?.completed || status?.failed) {
        await props.refreshUser();
        if (status?.completed && !props.getIsGuest()) {
          props.clearGuestCredentials();
        }
        return;
      }
    } catch {
      // ignore poll errors
    }
    await new Promise((resolve) => setTimeout(resolve, delayMs));
  }
  await props.refreshUser();
  if (!props.getIsGuest()) {
    props.clearGuestCredentials();
  }
};

onMounted(() => {
  if (props.guestCredentials?.username) {
    username.value = props.guestCredentials.username;
  }
  if (props.guestCredentials?.password) {
    password.value = props.guestCredentials.password;
  }
  if (!username.value && props.currentUsername) {
    username.value = props.currentUsername;
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
