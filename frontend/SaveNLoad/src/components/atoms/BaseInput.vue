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
    :maxlength="maxlength"
    :tabindex="tabindex"
    class="form-control"
    :class="inputClass"
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
  maxlength: { type: [Number, String], default: undefined },
  tabindex: { type: [Number, String], default: undefined },
  inputClass: { type: [String, Array, Object], default: '' }
});

const model = defineModel<string>({ default: '' });
</script>
