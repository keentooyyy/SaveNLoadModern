<template>
  <Teleport to="body">
    <div v-if="open" class="operation-modal-backdrop" role="presentation" @click.self="onClose">
      <div class="operation-modal-card" role="dialog" aria-modal="true" :aria-labelledby="titleId">
        <header class="operation-modal-header" :class="variantClass">
          <div class="operation-modal-icon">
            <i :class="iconClass"></i>
          </div>
          <div class="operation-modal-heading">
            <h5 :id="titleId" class="mb-1">{{ title }}</h5>
            <p class="mb-0 text-white-50 small">{{ subtitle }}</p>
          </div>
          <button
            v-if="closable"
            class="btn-close btn-close-white ms-auto"
            type="button"
            aria-label="Close"
            @click="onClose"
          ></button>
        </header>

        <div class="operation-modal-body">
          <div class="operation-progress">
            <div class="operation-progress-track">
              <div class="operation-progress-bar" :class="variantClass" :style="{ width: `${progress}%` }"></div>
            </div>
            <div class="d-flex justify-content-between align-items-center mt-2">
              <span class="text-white fw-medium">{{ statusText }}</span>
              <span class="text-white-50 small">{{ Math.round(progress) }}%</span>
            </div>
            <p class="text-white-50 small mt-2 mb-0">{{ detail }}</p>
          </div>
        </div>

        <div v-if="closable" class="operation-modal-footer">
          <button class="btn btn-outline-light btn-sm" type="button" @click="onClose">Close</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: 'Operation in progress' },
  subtitle: { type: String, default: 'Please keep this window open.' },
  statusText: { type: String, default: 'Preparing...' },
  detail: { type: String, default: 'Working on your request.' },
  progress: { type: Number, default: 0 },
  variant: { type: String, default: 'info' },
  closable: { type: Boolean, default: false }
});

const emit = defineEmits(['close']);

const titleId = `operationModalTitle_${Math.random().toString(36).slice(2, 8)}`;

const variantClass = computed(() => {
  if (props.variant === 'success') {
    return 'is-success';
  }
  if (props.variant === 'danger') {
    return 'is-danger';
  }
  if (props.variant === 'warning') {
    return 'is-warning';
  }
  return 'is-info';
});

const iconClass = computed(() => {
  if (props.variant === 'success') {
    return 'fas fa-check';
  }
  if (props.variant === 'danger') {
    return 'fas fa-times';
  }
  if (props.variant === 'warning') {
    return 'fas fa-exclamation';
  }
  return 'fas fa-bolt';
});

const onClose = () => {
  if (!props.closable) {
    return;
  }
  emit('close');
};
</script>

<style scoped>
.operation-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(6, 9, 16, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  z-index: 1200;
}

.operation-modal-card {
  width: min(520px, 100%);
  background: var(--color-primary);
  border-radius: 12px;
  border: 1px solid var(--white-opacity-10);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.4);
  overflow: hidden;
}

.operation-modal-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--white-opacity-10);
}

.operation-modal-header.is-info {
  background: var(--primary-opacity-30);
}

.operation-modal-header.is-success {
  background: rgba(32, 107, 74, 0.5);
}

.operation-modal-header.is-warning {
  background: rgba(152, 104, 32, 0.5);
}

.operation-modal-header.is-danger {
  background: rgba(129, 44, 44, 0.5);
}

.operation-modal-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--white-opacity-10);
  display: grid;
  place-items: center;
  font-size: 1rem;
  color: var(--color-white);
}

.operation-modal-body {
  padding: 1.25rem;
}

.operation-progress-track {
  height: 8px;
  border-radius: 999px;
  background: var(--white-opacity-10);
  overflow: hidden;
}

.operation-progress-bar {
  height: 100%;
  transition: width 0.3s ease;
  border-radius: inherit;
}

.operation-progress-bar.is-info {
  background: var(--color-primary);
}

.operation-progress-bar.is-success {
  background: var(--color-success);
}

.operation-progress-bar.is-warning {
  background: var(--color-warning);
}

.operation-progress-bar.is-danger {
  background: var(--color-danger);
}

.operation-modal-footer {
  padding: 0 1.25rem 1.25rem;
  display: flex;
  justify-content: flex-end;
}
</style>
