<template>
  <AuthLayout
    title="Save N Load"
    subtitle="Managing saves has never been easier."
    :on-reset="resetStatus"
  >
    <form @submit.prevent="onSubmit">
      <div class="mb-3">
        <InputLabel text="USERNAME OR EMAIL" />
        <TextInput
          v-model="form.username"
          placeholder="Enter your username or email"
          :invalid="!!fieldErrors?.username"
          required
          tabindex="1"
        />
      </div>
      <div class="mb-2">
        <div class="d-flex justify-content-between align-items-center">
          <InputLabel text="PASSWORD" label-class="mb-0" />
          <a
            v-if="showForgotPassword"
            href="/forgot-password"
            class="text-secondary text-decoration-none fs-6"
            tabindex="-1"
          >
            Forgot Password?
          </a>
        </div>
        <PasswordField
          v-model="form.password"
          placeholder="Enter your password"
          :invalid="!!fieldErrors?.password"
          tabindex="2"
        />
      </div>
      <div class="mb-3">
        <BaseCheckbox
          id="rememberMe"
          v-model="form.rememberMe"
          label="Remember Me"
          input-class="bg-primary border-secondary"
          label-class="text-white fs-6"
        />
      </div>
      <div class="d-grid">
        <IconButton
          type="submit"
          variant="secondary"
          class="text-white fw-bold mt-3 py-2"
          :disabled="isSubmitting"
          :loading="isLoginLoading"
          tabindex="3"
        >
          LOGIN
        </IconButton>
      </div>
      <div v-if="guestEnabled" class="d-grid mt-2">
        <IconButton
          type="button"
          variant="outline-secondary"
          class="text-white fw-bold py-2"
          :disabled="isSubmitting"
          :loading="isGuestLoading"
          @click="onGuest"
          tabindex="4"
        >
          CONTINUE AS GUEST
        </IconButton>
      </div>
      <AuthFooterLink
        prefix="Don't have an account? "
        link-text="Create an account"
        to="/register"
        tabindex="-1"
      />
    </form>
    <ModalShell
      ref="guestModalShell"
      :open="showGuestModal"
      :show="guestModal.open"
      :labelled-by="guestModal.titleId"
      modal-class="confirm-modal"
      backdrop-class="confirm-modal-backdrop"
      dialog-style="max-width: 460px;"
    >
      <template #header>
        <div class="modal-header modal-shell__header">
          <h5 :id="guestModal.titleId" class="modal-title text-white mb-0">Guest Account</h5>
          <button
            class="btn-close btn-close-white"
            type="button"
            aria-label="Close"
            @click="requestGuestClose"
          ></button>
        </div>
      </template>
      <template #body>
        <div class="modal-body modal-shell__body">
          <p class="text-white-50 mb-3">{{ guestModal.message }}</p>
          <div v-if="guestModal.loading" class="text-white-50">Creating guest account...</div>
          <div v-else class="text-white">
            <div class="guest-credential-card">
              <div class="guest-credential-title">Your Guest Credentials</div>
              <div class="guest-credential-row">
                <span class="guest-credential-label">Username</span>
                <code class="guest-credential-value">{{ guestModal.username }}</code>
              </div>
              <div class="guest-credential-row">
                <span class="guest-credential-label">Password</span>
                <code class="guest-credential-value">{{ guestModal.password }}</code>
              </div>
              <div class="guest-credential-hint">
                Make a note of these credentials. You will need them to upgrade later.
              </div>
            </div>
          </div>
        </div>
      </template>
      <template #footer>
        <div class="modal-footer modal-shell__footer d-flex justify-content-end">
          <button class="btn btn-outline-secondary text-white" type="button" @click="requestGuestClose">
            Close
          </button>
        </div>
      </template>
    </ModalShell>
  </AuthLayout>
</template>

<script setup lang="ts">
import { reactive, computed, watch, ref, nextTick } from 'vue';
import AuthLayout from '@/layouts/AuthLayout.vue';
import PasswordField from '@/components/molecules/PasswordField.vue';
import { useAuthStore } from '@/stores/auth';
import { useDashboardStore } from '@/stores/dashboard';
import IconButton from '@/components/atoms/IconButton.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import TextInput from '@/components/atoms/TextInput.vue';
import AuthFooterLink from '@/components/molecules/AuthFooterLink.vue';
import ModalShell from '@/components/molecules/ModalShell.vue';
import BaseCheckbox from '@/components/atoms/BaseCheckbox.vue';
import { useAuthConfig } from '@/composables/useAuthConfig';
import { notify } from '@/utils/notify';

const store = useAuthStore();
const dashboardStore = useDashboardStore();
const guestModalShell = ref<{ modalEl: HTMLElement | null } | null>(null);
let guestCloseFallbackTimer: number | null = null;

const form = reactive({
  username: '',
  password: '',
  rememberMe: false
});

const loading = computed(() => store.loading);
const fieldErrors = computed(() => store.fieldErrors);
const showForgotPassword = computed(() => (
  store.authConfigLoaded
  && store.authConfig.emailEnabled
  && store.authConfig.emailRegistrationRequired
));
const guestEnabled = computed(() => store.authConfigLoaded && store.authConfig.guestEnabled);

useAuthConfig({ loadAuthConfig: () => store.loadAuthConfig() });
const activeAction = ref<'login' | 'guest' | null>(null);
const isSubmitting = computed(() => loading.value || activeAction.value !== null);
const isLoginLoading = computed(() => activeAction.value === 'login' && isSubmitting.value);
const isGuestLoading = computed(() => activeAction.value === 'guest' && isSubmitting.value);
const guestModal = reactive({
  open: false,
  closing: false,
  manualClose: false,
  loading: false,
  username: '',
  password: '',
  message: 'Save these credentials before closing.',
  titleId: `guestModalTitle_${Math.random().toString(36).slice(2, 8)}`
});

const showGuestModal = computed(() => guestModal.open || guestModal.closing);

const clearFieldError = (key: string) => {
  if (store.fieldErrors && store.fieldErrors[key]) {
    const next = { ...store.fieldErrors };
    delete next[key];
    store.fieldErrors = Object.keys(next).length ? next : null;
  }
  if (store.error) {
    store.error = '';
  }
};

const resetStatus = () => {
  store.resetStatus();
};


watch(() => form.username, () => clearFieldError('username'));
watch(() => form.password, () => clearFieldError('password'));

const onSubmit = async () => {
  if (isSubmitting.value) {
    return;
  }
  activeAction.value = 'login';
  try {
    await store.login({
      username: form.username,
      password: form.password,
      rememberMe: form.rememberMe
    });
    notify.flashSuccess(store.message || 'Login successful.');
    try {
      await dashboardStore.loadDashboard();
      window.location.assign('/dashboard');
    } catch (err: any) {
      if (err?.status === 503) {
        window.location.assign('/worker-required');
        return;
      }
      if (err?.status === 401) {
        return;
      }
      window.location.assign('/dashboard');
    }
  } catch {
    // handled by store
  } finally {
    activeAction.value = null;
  }
};

const onGuest = async () => {
  if (isSubmitting.value) {
    return;
  }
  activeAction.value = 'guest';
  store.suppressWorkerRedirect = true;
  guestModal.open = true;
  guestModal.closing = false;
  guestModal.manualClose = false;
  guestModal.loading = true;
  guestModal.username = '';
  guestModal.password = '';
  try {
    const data = await store.loginGuest();
    const creds = data?.guest_credentials;
    guestModal.username = creds?.username || store.user?.username || '';
    guestModal.password = creds?.password || '';
  } catch {
    // handled by store
    guestModal.open = false;
    store.suppressWorkerRedirect = false;
  } finally {
    activeAction.value = null;
    guestModal.loading = false;
  }
};

const requestGuestClose = () => {
  guestModal.manualClose = true;
  store.suppressWorkerRedirect = false;
  closeGuestModal();
};

const closeGuestModal = async () => {
  if (!guestModal.manualClose) {
    return;
  }
  if (guestModal.closing) {
    return;
  }
  if (guestCloseFallbackTimer !== null) {
    window.clearTimeout(guestCloseFallbackTimer);
    guestCloseFallbackTimer = null;
  }
  guestModal.open = false;
  guestModal.closing = true;
  if (!store.user) {
    guestModal.closing = false;
    return;
  }
  await nextTick();
  const modalEl = guestModalShell.value?.modalEl || null;
  const doRedirect = async () => {
    guestModal.closing = false;
    try {
      await dashboardStore.loadDashboard();
      window.location.assign('/dashboard');
    } catch (err: any) {
      if (err?.status === 503) {
        window.location.assign('/worker-required');
        return;
      }
      if (err?.status === 401) {
        return;
      }
      window.location.assign('/dashboard');
    }
  };
  if (modalEl) {
    const onTransitionEnd = () => {
      modalEl.removeEventListener('transitionend', onTransitionEnd);
      void doRedirect();
    };
    modalEl.addEventListener('transitionend', onTransitionEnd);
    guestCloseFallbackTimer = window.setTimeout(() => {
      modalEl.removeEventListener('transitionend', onTransitionEnd);
      void doRedirect();
    }, 350);
    return;
  }
  await doRedirect();
};
</script>

<style scoped>
.confirm-modal {
  display: block;
  z-index: 1250;
  opacity: 0;
  transition: opacity 0.25s ease;
}

.confirm-modal-backdrop {
  background: var(--overlay-bg);
  z-index: 1240;
  opacity: 0;
  transition: opacity 0.25s ease;
}

.confirm-modal.show {
  opacity: 1;
}

.confirm-modal-backdrop.show {
  opacity: 1;
}

.guest-credential-card {
  border-radius: 16px;
  padding: 18px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.02));
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
}

.guest-credential-title {
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 12px;
}

.guest-credential-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(10, 12, 20, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.guest-credential-row + .guest-credential-row {
  margin-top: 10px;
}

.guest-credential-label {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.6);
}

.guest-credential-value {
  font-size: 1rem;
  color: #f5f5f5;
  padding: 2px 8px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.35);
}

.guest-credential-hint {
  margin-top: 14px;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.6);
}
</style>
