<template>
  <div class="form-check form-switch settings-toggle" :class="wrapperClass">
    <input
      :id="id"
      v-model="model"
      class="form-check-input bg-primary border-secondary"
      type="checkbox"
      :disabled="disabled"
    />
    <label class="form-check-label text-white" :for="id">
      {{ label }}
    </label>
    <span
      class="badge ms-2"
      :class="model ? 'bg-secondary text-white' : 'bg-dark text-white'"
    >
      {{ model ? onText : offText }}
    </span>
  </div>
</template>

<script setup lang="ts">
defineProps({
  id: { type: String, required: true },
  label: { type: String, required: true },
  disabled: { type: Boolean, default: false },
  onText: { type: String, default: 'Enabled' },
  offText: { type: String, default: 'Disabled' },
  wrapperClass: { type: String, default: '' }
});

const model = defineModel<boolean>({ default: false });
</script>

<style scoped>
.settings-toggle .form-check-input:not(:checked) {
  background-color: var(--white-opacity-10);
  border-color: var(--white-opacity-30);
}

.settings-toggle .form-check-input:checked {
  background-color: var(--bs-primary);
  border-color: var(--bs-primary);
}
</style>
