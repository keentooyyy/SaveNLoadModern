<template>
  <div class="container-fluid px-4 pt-3">
    <div class="card shadow-lg bg-primary text-white border-0">
      <button
        class="card-header bg-primary text-white border-0 p-3 w-100 text-start d-flex justify-content-between align-items-center"
        :class="[headerClass, { active: isOpen }]"
        type="button"
        data-bs-toggle="collapse"
        :data-bs-target="`#${collapseId}`"
        :aria-expanded="isOpen"
        :aria-controls="collapseId"
      >
        <div class="d-flex align-items-center">
          <i class="fas me-3 text-white" :class="[iconClass, icon]" />
          <h5 class="mb-0 text-white" :class="titleClass">{{ title }}</h5>
        </div>
        <i class="fas fa-chevron-right text-white" :class="chevronClass" :id="chevronId"></i>
      </button>

      <div class="collapse" :id="collapseId">
        <div class="card-body" :class="bodyClass">
          <slot />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';

const props = defineProps({
  title: { type: String, required: true },
  icon: { type: String, required: true },
  collapseId: { type: String, required: true },
  headerClass: { type: String, default: '' },
  iconClass: { type: String, default: '' },
  titleClass: { type: String, default: '' },
  chevronClass: { type: String, default: '' },
  chevronId: { type: String, default: '' },
  bodyClass: { type: String, default: '' }
});

const isOpen = ref(false);

let collapseElement: HTMLElement | null = null;
const handleShow = () => {
  isOpen.value = true;
};
const handleHide = () => {
  isOpen.value = false;
};

onMounted(() => {
  collapseElement = document.getElementById(props.collapseId);
  if (!collapseElement) {
    return;
  }

  collapseElement.addEventListener('show.bs.collapse', handleShow);
  collapseElement.addEventListener('hide.bs.collapse', handleHide);

  if (collapseElement.classList.contains('show')) {
    isOpen.value = true;
  }
});

onBeforeUnmount(() => {
  if (!collapseElement) {
    return;
  }
  collapseElement.removeEventListener('show.bs.collapse', handleShow);
  collapseElement.removeEventListener('hide.bs.collapse', handleHide);
});
</script>

<style scoped>
:is(.add-game-header, .account-settings-header, .operation-queue-header, .manage-accounts-header) {
  cursor: pointer;
  transition: all 0.3s ease;
}

:is(.add-game-header, .account-settings-header, .operation-queue-header, .manage-accounts-header)
  :is(.add-game-chevron, .account-settings-chevron, .operation-queue-chevron, .manage-accounts-chevron) {
  transition: transform 0.3s ease;
}

:is(.add-game-header, .account-settings-header, .operation-queue-header, .manage-accounts-header).active
  :is(
    .add-game-icon,
    .add-game-title,
    .add-game-chevron,
    .account-settings-icon,
    .account-settings-title,
    .account-settings-chevron,
    .operation-queue-icon,
    .operation-queue-title,
    .operation-queue-chevron,
    .manage-accounts-icon,
    .manage-accounts-title,
    .manage-accounts-chevron
  ) {
  color: var(--color-primary) !important;
}

:is(.add-game-header, .account-settings-header, .operation-queue-header, .manage-accounts-header).active
  :is(.add-game-chevron, .account-settings-chevron, .operation-queue-chevron, .manage-accounts-chevron) {
  transform: rotate(90deg);
}
</style>
