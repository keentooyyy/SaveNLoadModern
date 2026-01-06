<template>
  <CollapsibleCard
    title="Account Settings"
    icon="fa-user-cog"
    collapse-id="accountSettingsCollapse"
    header-class="account-settings-header"
    icon-class="account-settings-icon"
    title-class="account-settings-title"
    chevron-class="account-settings-chevron"
    chevron-id="accountSettingsChevron"
  >
    <form id="accountSettingsForm" @submit.prevent="onSubmit" @reset.prevent="onReset">
      <div class="mb-3">
        <InputLabel for-id="accountEmail" text="EMAIL" />
        <TextInput id="accountEmail" v-model="email" type="email" placeholder="Enter your email" />
      </div>

      <div class="mb-3">
        <InputLabel label-class="mb-0">
          CURRENT PASSWORD <span class="text-white-50">(optional)</span>
        </InputLabel>
        <PasswordField v-model="currentPassword" placeholder="Enter current password" />
      </div>

      <div class="mb-3">
        <InputLabel label-class="mb-0">
          NEW PASSWORD <span class="text-white-50">(optional)</span>
        </InputLabel>
        <PasswordField v-model="newPassword" placeholder="Enter new password" />
      </div>

      <div class="mb-3">
        <InputLabel label-class="mb-0">
          CONFIRM NEW PASSWORD <span class="text-white-50">(optional)</span>
        </InputLabel>
        <PasswordField v-model="confirmPassword" placeholder="Confirm new password" />
      </div>

      <FormActions>
        <IconButton type="submit" variant="secondary" class="text-white fw-bold" icon="fa-save" :disabled="saving">
          Save Changes
        </IconButton>
        <IconButton type="reset" variant="outline-secondary" class="text-white" :disabled="saving">Clear</IconButton>
      </FormActions>
    </form>
  </CollapsibleCard>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import CollapsibleCard from '@/components/molecules/CollapsibleCard.vue';
import PasswordField from '@/components/molecules/PasswordField.vue';
import FormActions from '@/components/molecules/FormActions.vue';
import IconButton from '@/components/atoms/IconButton.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import TextInput from '@/components/atoms/TextInput.vue';
import { useSettingsStore } from '@/stores/settings';

const store = useSettingsStore();
const email = ref('');
const currentPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const saving = ref(false);

const loadProfile = async () => {
  try {
    const user = await store.loadCurrentUser();
    email.value = user?.email || '';
  } catch {
    // Ignore profile load errors.
  }
};

const onReset = () => {
  currentPassword.value = '';
  newPassword.value = '';
  confirmPassword.value = '';
};

const onSubmit = async () => {
  saving.value = true;
  try {
    await store.updateAccount({
      email: email.value.trim(),
      current_password: currentPassword.value,
      new_password: newPassword.value,
      confirm_password: confirmPassword.value
    });
    onReset();
  } catch (err: any) {
    const t = (window as any).toastr;
    if (t?.error && err?.message) {
      t.error(err.message);
    }
  } finally {
    saving.value = false;
  }
};

onMounted(() => {
  loadProfile();
});
</script>
