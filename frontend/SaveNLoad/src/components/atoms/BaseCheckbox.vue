<template>
  <div class="form-check">
    <input
      class="form-check-input"
      type="checkbox"
      :id="id"
      :checked="modelValue"
      @change="$emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
    />
    <label v-if="label" class="form-check-label" :for="id">{{ label }}</label>
    <slot v-else />
  </div>
</template>

<script setup lang="ts">
defineProps({
  id: String,
  label: String,
  modelValue: Boolean
});

defineEmits(['update:modelValue']);
</script>
