<template>
  <div class="form-check" :class="{ 'form-switch': switchStyle }">
    <input
      v-model="model"
      class="form-check-input"
      :class="inputClass"
      type="checkbox"
      :id="id"
      :disabled="disabled"
    />
    <label v-if="label" class="form-check-label" :class="labelClass" :for="id">
      {{ label }}
    </label>
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps({
  id: { type: String, default: '' },
  label: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  switchStyle: { type: Boolean, default: false },
  inputClass: { type: String, default: '' },
  labelClass: { type: String, default: '' }
});

const model = defineModel<boolean>({ default: false });
</script>
