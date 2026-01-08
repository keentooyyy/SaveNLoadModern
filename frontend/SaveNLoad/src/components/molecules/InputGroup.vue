<template>
  <div class="input-group">
    <template v-if="buttonFirst">
      <slot name="button">
        <IconButton
          :type="buttonType"
          :variant="buttonVariant"
          :size="buttonSize"
          :icon="buttonIcon"
          :class="buttonClass"
          :id="buttonId"
          @click="$emit('action')"
        >
          {{ buttonLabel }}
        </IconButton>
      </slot>
      <slot name="input">
        <TextInput
          v-model="model"
          :id="inputId"
          :type="inputType"
          :placeholder="placeholder"
          :input-class="inputClass"
          @keydown.enter.prevent="$emit('action')"
        />
      </slot>
    </template>
    <template v-else>
      <slot name="input">
        <TextInput
          v-model="model"
          :id="inputId"
          :type="inputType"
          :placeholder="placeholder"
          :input-class="inputClass"
          @keydown.enter.prevent="$emit('action')"
        />
      </slot>
      <slot name="button">
        <IconButton
          :type="buttonType"
          :variant="buttonVariant"
          :size="buttonSize"
          :icon="buttonIcon"
          :class="buttonClass"
          :id="buttonId"
          @click="$emit('action')"
        >
          {{ buttonLabel }}
        </IconButton>
      </slot>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue';
import IconButton from '@/components/atoms/IconButton.vue';
import TextInput from '@/components/atoms/TextInput.vue';

defineProps({
  inputId: String,
  inputType: { type: String, default: 'text' },
  placeholder: String,
  inputClass: { type: String, default: '' },
  buttonFirst: { type: Boolean, default: false },
  buttonLabel: { type: String, default: '' },
  buttonIcon: { type: String, default: '' },
  buttonVariant: { type: String, default: 'secondary' },
  buttonSize: { type: String, default: '' },
  buttonClass: { type: String, default: '' },
  buttonType: { type: String as PropType<'button' | 'submit' | 'reset'>, default: 'button' },
  buttonId: { type: String, default: '' }
});

defineEmits(['action']);

const model = defineModel<string>({ default: '' });
</script>
