<template>
  <input
    :id="id"
    :name="name"
    :type="type"
    :placeholder="placeholder"
    :value="modelValue"
    class="form-control"
    @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  />
</template>

<script setup lang="ts">
defineProps({
  id: String,
  name: String,
  type: { type: String, default: 'text' },
  placeholder: String,
  modelValue: String
});

defineEmits(['update:modelValue']);
</script>
