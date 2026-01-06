<template>
  <Teleport to="body">
    <div v-if="open">
      <div
        class="modal fade show d-block"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        @click.self="onClose"
      >
        <div class="modal-dialog modal-dialog-centered operation-modal-dialog">
          <div class="modal-content bg-primary text-white border-0">
            <header class="modal-header bg-primary border-secondary">
              <h5 :id="titleId" class="mb-0">{{ title }}</h5>
              <button
                v-if="closable"
                class="btn-close btn-close-white ms-auto"
                type="button"
                aria-label="Close"
                @click="onClose"
              ></button>
            </header>

            <div class="modal-body bg-primary">
              <div class="operation-progress">
                <div class="operation-progress-track">
                  <div class="operation-progress-bar" :class="variantClass" :style="{ width: `${progress}%` }"></div>
                </div>
                <div class="d-flex justify-content-between align-items-center mt-2">
                  <span class="text-white fw-medium">{{ statusText }}</span>
                  <span class="text-white-50 small">{{ Math.round(progress) }}%</span>
                </div>
                <p v-if="detail" class="text-white-50 small mt-2 mb-0">{{ detail }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-backdrop fade show"></div>
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
.operation-modal-dialog {
  max-width: 520px;
}

.modal-content {
  border-radius: 12px;
  overflow: hidden;
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
  background: #2f96b4;
}

.operation-progress-bar.is-success {
  background: #51a351;
}

.operation-progress-bar.is-warning {
  background: #f89406;
}

.operation-progress-bar.is-danger {
  background: #bd362f;
}

</style>
