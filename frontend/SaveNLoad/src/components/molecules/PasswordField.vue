<template>
  <div class="position-relative">
    <input
      v-model="model"
      :id="id"
      :name="name"
      :type="visible ? 'text' : 'password'"
      :placeholder="placeholder"
      class="color-primary form-control bg-primary border border-1 border-secondary rounded-1 py-2 text-white pe-5"
      :class="{ 'is-invalid': invalid }"
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
import { ref } from 'vue';

const props = defineProps({
  id: String,
  name: String,
  placeholder: String,
  toggleId: String,
  invalid: { type: Boolean, default: false }
});

const model = defineModel<string>({ default: '' });

const visible = ref(false);

const toggle = () => {
  visible.value = !visible.value;
};
</script>
