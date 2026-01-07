<template>
  <CollapsibleCard
    title="Admin Settings"
    icon="fa-sliders-h"
    collapse-id="adminSettingsCollapse"
    header-class="admin-settings-header"
    icon-class="admin-settings-icon"
    title-class="admin-settings-title"
    chevron-class="admin-settings-chevron"
    chevron-id="adminSettingsChevron"
  >
    <form @submit.prevent="onSubmit">
      <div class="mb-3">
        <div class="form-check form-switch">
          <input
            id="rawgEnabled"
            class="form-check-input bg-primary border-secondary"
            type="checkbox"
            v-model="form.rawgEnabled"
          />
          <label class="form-check-label text-white" for="rawgEnabled">Enable RAWG</label>
        </div>
      </div>
      <div v-if="form.rawgEnabled" class="mb-3">
        <InputLabel for-id="rawgApiKey" text="RAWG API KEY" />
        <div class="position-relative">
          <TextInput
            id="rawgApiKey"
            v-model="form.rawgApiKey"
            :type="revealState.rawgApiKey ? 'text' : 'password'"
            placeholder="Enter RAWG API key"
            input-class="pe-5"
          />
          <i
            class="position-absolute top-50 end-0 translate-middle-y me-3 text-white-50 fw-light"
            :class="revealState.rawgApiKey ? 'fas fa-eye-slash' : 'fas fa-eye'"
            role="button"
            tabindex="-1"
            @click="toggleReveal('rawgApiKey', ['rawg.api_key'], 'RAWG API Key')"
          ></i>
        </div>
      </div>

      <div class="mb-3">
        <div class="form-check form-switch">
          <input
            id="emailEnabled"
            class="form-check-input bg-primary border-secondary"
            type="checkbox"
            v-model="form.emailEnabled"
          />
          <label class="form-check-label text-white" for="emailEnabled">Enable Email</label>
        </div>
      </div>

      <div v-if="form.emailEnabled" class="mb-3">
        <div class="form-check form-switch">
          <input
            id="emailRegistrationRequired"
            class="form-check-input bg-primary border-secondary"
            type="checkbox"
            v-model="form.emailRegistrationRequired"
          />
          <label class="form-check-label text-white" for="emailRegistrationRequired">
            Require Email on Registration
          </label>
        </div>
      </div>

      <div v-if="form.emailEnabled" class="row g-3">
        <div class="col-12 col-md-6">
          <InputLabel for-id="gmailUser" text="GMAIL USER" />
          <TextInput
            id="gmailUser"
            v-model="form.gmailUser"
            placeholder="you@gmail.com"
          />
        </div>
        <div class="col-12 col-md-6">
          <InputLabel for-id="gmailAppPassword" text="GMAIL APP PASSWORD" />
          <div class="position-relative">
            <TextInput
              id="gmailAppPassword"
              v-model="form.gmailAppPassword"
              :type="revealState.gmailAppPassword ? 'text' : 'password'"
              placeholder="App password"
              input-class="pe-5"
            />
            <i
              class="position-absolute top-50 end-0 translate-middle-y me-3 text-white-50 fw-light"
              :class="revealState.gmailAppPassword ? 'fas fa-eye-slash' : 'fas fa-eye'"
              role="button"
              tabindex="-1"
              @click="toggleReveal('gmailAppPassword', ['email.gmail_app_password'], 'Gmail App Password')"
            ></i>
          </div>
        </div>
      </div>

      <div class="mt-4 mb-3">
        <div class="form-check form-switch">
          <input
            id="guestEnabled"
            class="form-check-input bg-primary border-secondary"
            type="checkbox"
            v-model="form.guestEnabled"
          />
          <label class="form-check-label text-white" for="guestEnabled">Enable Guest Accounts</label>
        </div>
      </div>
      <div v-if="form.guestEnabled" class="mb-3">
        <InputLabel for-id="guestTtl" text="GUEST TTL (DAYS)" />
        <TextInput
          id="guestTtl"
          v-model="form.guestTtlDays"
          placeholder="14"
        />
      </div>

      <div class="mb-3">
        <InputLabel for-id="defaultPassword" text="RESET DEFAULT PASSWORD" />
        <div class="position-relative">
          <TextInput
            id="defaultPassword"
            v-model="form.resetDefaultPassword"
            :type="revealState.resetDefaultPassword ? 'text' : 'password'"
            placeholder="Enter default reset password"
            input-class="pe-5"
          />
          <i
            class="position-absolute top-50 end-0 translate-middle-y me-3 text-white-50 fw-light"
            :class="revealState.resetDefaultPassword ? 'fas fa-eye-slash' : 'fas fa-eye'"
            role="button"
            tabindex="-1"
            @click="toggleReveal('resetDefaultPassword', ['reset.default_password'], 'Reset Default Password')"
          ></i>
        </div>
      </div>

      <FormActions>
        <IconButton
          type="submit"
          variant="secondary"
          class="text-white fw-bold"
          icon="fa-save"
          :disabled="isSaving"
          :loading="isSaving"
        >
          Save Settings
        </IconButton>
        <IconButton
          type="button"
          variant="outline-secondary"
          class="text-white"
          icon="fa-heart-pulse"
          :disabled="isSaving || isHealthChecking"
          :loading="isHealthChecking"
          @click="onHealthCheck"
        >
          Run Health Check
        </IconButton>
      </FormActions>

    </form>
  </CollapsibleCard>
  <Teleport to="body">
    <div
      v-if="revealModal.open"
      class="modal fade show confirm-modal"
      tabindex="-1"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="revealModal.titleId"
      @click.self="closeReveal"
    >
      <div class="modal-dialog modal-dialog-centered" style="max-width: 420px;">
        <div class="modal-content modal-shell">
          <div class="modal-header modal-shell__header">
            <h5 :id="revealModal.titleId" class="modal-title text-white mb-0">
              Reveal {{ revealModal.label }}
            </h5>
            <button class="btn-close btn-close-white" type="button" aria-label="Close" @click="closeReveal"></button>
          </div>
          <div class="modal-body modal-shell__body">
            <p class="text-white-50 mb-3">Confirm your admin password to reveal this value.</p>
            <PasswordField v-model="revealModal.password" placeholder="Admin password" />
          </div>
          <div class="modal-footer modal-shell__footer d-flex justify-content-end">
            <button class="btn btn-outline-secondary text-white" type="button" @click="closeReveal">
              Cancel
            </button>
            <button class="btn btn-light text-primary" type="button" @click="confirmReveal" :disabled="isRevealLoading">
              Reveal
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="revealModal.open" class="modal-backdrop fade show confirm-modal-backdrop"></div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue';
import CollapsibleCard from '@/components/molecules/CollapsibleCard.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import TextInput from '@/components/atoms/TextInput.vue';
import FormActions from '@/components/molecules/FormActions.vue';
import IconButton from '@/components/atoms/IconButton.vue';
import PasswordField from '@/components/molecules/PasswordField.vue';
import { useSettingsStore } from '@/stores/settings';

const store = useSettingsStore();

  const form = reactive({
    rawgEnabled: false,
    rawgApiKey: '',
    emailEnabled: false,
    emailRegistrationRequired: true,
    gmailUser: '',
    gmailAppPassword: '',
    guestEnabled: false,
    guestTtlDays: '14',
    resetDefaultPassword: ''
  });

const isSaving = computed(() => store.adminSettingsSaving);
const isHealthChecking = computed(() => store.adminSettingsHealthLoading);
const isRevealLoading = computed(() => store.adminSettingsRevealLoading);
const health = computed(() => store.adminSettingsHealth);
const revealState = reactive({
  rawgApiKey: false,
  gmailAppPassword: false,
  resetDefaultPassword: false
});
const revealUnlocked = reactive({
  rawgApiKey: false,
  gmailAppPassword: false,
  resetDefaultPassword: false
});

const revealModal = reactive({
  open: false,
  keys: [] as string[],
  label: '',
  password: '',
  titleId: `revealModalTitle_${Math.random().toString(36).slice(2, 8)}`
});

  const applySettings = (settings: Record<string, any>) => {
    form.rawgEnabled = !!settings['feature.rawg.enabled'];
    form.rawgApiKey = settings['rawg.api_key'] || '';
    form.emailEnabled = !!settings['feature.email.enabled'];
    form.emailRegistrationRequired = settings['feature.email.registration_required'] !== false;
    form.gmailUser = settings['email.gmail_user'] || '';
    form.gmailAppPassword = settings['email.gmail_app_password'] || '';
    form.guestEnabled = !!settings['feature.guest.enabled'];
    form.guestTtlDays = String(settings['feature.guest.ttl_days'] ?? '14');
    form.resetDefaultPassword = settings['reset.default_password'] || '';
  };

const loadSettings = async () => {
  const settings = await store.loadAdminSettings();
  applySettings(settings || {});
};

const onSubmit = async () => {
  try {
    await store.updateAdminSettings({
      'feature.rawg.enabled': form.rawgEnabled,
      'rawg.api_key': form.rawgApiKey.trim(),
      'feature.email.enabled': form.emailEnabled,
      'feature.email.registration_required': form.emailRegistrationRequired,
      'email.gmail_user': form.gmailUser.trim(),
      'email.gmail_app_password': form.gmailAppPassword.trim(),
      'feature.guest.enabled': form.guestEnabled,
      'feature.guest.ttl_days': Number(form.guestTtlDays),
      'reset.default_password': form.resetDefaultPassword
    });
    const t = (window as any).toastr;
    if (t?.success) {
      t.success('Admin settings saved.');
    }
  } catch {
    const t = (window as any).toastr;
    if (t?.error) {
      t.error('Failed to save admin settings.');
    }
  }
};

const onHealthCheck = async () => {
  const health = await store.checkAdminSettingsHealth();
  if (!health) {
    return;
  }
  const t = (window as any).toastr;
  if (!t) {
    return;
  }
  const rawg = formatHealth(health.rawg);
  const email = formatHealth(health.email);
  const message = `RAWG: ${rawg}\nEmail: ${email}`;
  const isHealthy = health.rawg?.healthy && health.email?.healthy;
  if (isHealthy && t.success) {
    t.success(message, 'Health Check');
  } else if (t.warning) {
    t.warning(message, 'Health Check');
  } else if (t.info) {
    t.info(message, 'Health Check');
  }
};

const openReveal = (keys: string[], label: string) => {
  revealModal.open = true;
  revealModal.keys = keys;
  revealModal.label = label;
  revealModal.password = '';
};

const toggleReveal = (field: 'rawgApiKey' | 'gmailAppPassword' | 'resetDefaultPassword', keys: string[], label: string) => {
  if (revealState[field]) {
    revealState[field] = false;
    return;
  }
  if (revealUnlocked[field]) {
    revealState[field] = true;
    return;
  }
  openReveal(keys, label);
};

const closeReveal = () => {
  revealModal.open = false;
  revealModal.keys = [];
  revealModal.label = '';
  revealModal.password = '';
};

const confirmReveal = async () => {
  if (!revealModal.password) {
    return;
  }
  try {
    const revealed = await store.revealAdminSettings(revealModal.keys, revealModal.password);
    if (revealed['rawg.api_key'] !== undefined) {
      form.rawgApiKey = revealed['rawg.api_key'] || '';
      revealState.rawgApiKey = true;
      revealUnlocked.rawgApiKey = true;
    }
    if (revealed['email.gmail_app_password'] !== undefined) {
      form.gmailAppPassword = revealed['email.gmail_app_password'] || '';
      revealState.gmailAppPassword = true;
      revealUnlocked.gmailAppPassword = true;
    }
    if (revealed['reset.default_password'] !== undefined) {
      form.resetDefaultPassword = revealed['reset.default_password'] || '';
      revealState.resetDefaultPassword = true;
      revealUnlocked.resetDefaultPassword = true;
    }
    closeReveal();
  } catch {
    // handled by store
  }
};

const formatHealth = (entry?: { enabled?: boolean; healthy?: boolean; message?: string }) => {
  if (!entry) {
    return 'No data';
  }
  const status = entry.enabled ? (entry.healthy ? 'Healthy' : 'Unhealthy') : 'Disabled';
  const message = entry.message ? ` - ${entry.message}` : '';
  return `${status}${message}`;
};

onMounted(() => {
  void loadSettings();
});
</script>

<style scoped>
.confirm-modal {
  display: block;
  z-index: 1250;
}

.confirm-modal-backdrop {
  background: var(--overlay-bg);
  z-index: 1240;
}
</style>
