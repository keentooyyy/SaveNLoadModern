<template>
  <div class="position-relative">
    <BaseInput
      v-model="model"
      :id="id"
      :name="name"
      :type="visible ? 'text' : 'password'"
      :placeholder="placeholder"
      :tabindex="tabindex"
      :input-class="inputClasses"
    />
    <i
      :id="toggleId"
      class="position-absolute top-50 end-0 translate-middle-y me-3 text-white-50 fw-light"
      :class="visible ? 'fas fa-eye' : 'fas fa-eye-slash'"
      role="button"
      tabindex="-1"
      aria-hidden="true"
      @click="toggle"
    ></i>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import BaseInput from '@/components/atoms/BaseInput.vue';

const props = defineProps({
  id: String,
  name: String,
  placeholder: String,
  toggleId: String,
  invalid: { type: Boolean, default: false },
  tabindex: { type: [Number, String], default: undefined }
});

const model = defineModel<string>({ default: '' });

const visible = ref(false);

const inputClasses = computed(() => ([
  'color-primary form-control bg-primary border border-1 border-secondary rounded-1 py-2 text-white pe-5',
  { 'is-invalid': props.invalid }
]));

const toggle = () => {
  visible.value = !visible.value;
};
</script>
