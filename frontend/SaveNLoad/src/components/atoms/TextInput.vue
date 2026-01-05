<template>
  <input
    v-model="model"
    :id="id"
    :name="name"
    :type="type"
    :placeholder="placeholder"
    :required="required"
    :disabled="disabled"
    :readonly="readonly"
    class="color-primary form-control bg-primary border border-1 border-secondary rounded-1 py-2 text-white"
    :class="[{ 'is-invalid': invalid }, inputClass]"
  />
</template>

<script setup lang="ts">
defineProps({
  id: String,
  name: String,
  type: { type: String, default: 'text' },
  placeholder: String,
  required: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false },
  invalid: { type: Boolean, default: false },
  inputClass: { type: String, default: '' }
});

const model = defineModel<string>({ default: '' });
</script>
