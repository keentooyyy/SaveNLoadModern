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
    <form id="accountSettingsForm">
      <div class="mb-3">
        <InputLabel for-id="accountEmail" text="EMAIL" />
        <TextInput id="accountEmail" type="email" placeholder="Enter your email" />
      </div>

      <div class="mb-3">
        <InputLabel label-class="mb-0">
          CURRENT PASSWORD <span class="text-white-50">(optional)</span>
        </InputLabel>
        <PasswordField placeholder="Enter current password" />
      </div>

      <div class="mb-3">
        <InputLabel label-class="mb-0">
          NEW PASSWORD <span class="text-white-50">(optional)</span>
        </InputLabel>
        <PasswordField placeholder="Enter new password" />
      </div>

      <div class="mb-3">
        <InputLabel label-class="mb-0">
          CONFIRM NEW PASSWORD <span class="text-white-50">(optional)</span>
        </InputLabel>
        <PasswordField placeholder="Confirm new password" />
      </div>

      <FormActions>
        <IconButton type="submit" variant="secondary" class="text-white fw-bold" icon="fa-save">
          Save Changes
        </IconButton>
        <IconButton type="reset" variant="outline-secondary" class="text-white">Clear</IconButton>
      </FormActions>
    </form>
  </CollapsibleCard>
</template>

<script setup lang="ts">
import CollapsibleCard from '@/components/molecules/CollapsibleCard.vue';
import PasswordField from '@/components/molecules/PasswordField.vue';
import FormActions from '@/components/molecules/FormActions.vue';
import IconButton from '@/components/atoms/IconButton.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import TextInput from '@/components/atoms/TextInput.vue';
</script>
