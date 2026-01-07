<template>
  <BaseInput
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
    :input-class="inputClasses"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import BaseInput from '@/components/atoms/BaseInput.vue';

const props = defineProps({
  id: String,
  name: String,
  type: { type: String, default: 'text' },
  placeholder: String,
  required: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false },
  maxlength: { type: [Number, String], default: undefined },
  invalid: { type: Boolean, default: false },
  tabindex: { type: [Number, String], default: undefined },
  inputClass: { type: String, default: '' }
});

const model = defineModel<string>({ default: '' });

const inputClasses = computed(() => ([
  'color-primary form-control bg-primary border border-1 border-secondary rounded-1 py-2 text-white',
  { 'is-invalid': !!props.invalid },
  props.inputClass
]));
</script>
