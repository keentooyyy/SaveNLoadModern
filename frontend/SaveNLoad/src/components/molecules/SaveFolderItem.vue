<template>
  <div class="list-group-item bg-primary text-white border-secondary transition-bg list-group-item-hover rounded-3 border border-secondary bg-opacity-10 p-3">
    <div class="d-flex flex-column flex-sm-row justify-content-between align-items-start align-items-sm-center gap-2">
      <div class="w-100">
        <h6 class="mb-1 text-white">Save {{ folder.folder_number }}</h6>
        <small class="text-white-50">{{ formatDate(folder.created_at) }}</small>
      </div>
      <div class="d-flex flex-column flex-sm-row gap-2 saves-item-actions">
        <button class="btn btn-sm btn-secondary text-white saves-item-btn" type="button" @click="emit('load', folder)">
          <i class="fas fa-download me-1"></i>
          Load
        </button>
        <button class="btn btn-sm btn-outline-danger text-white saves-item-btn" type="button" @click="emit('delete', folder)">
          <i class="fas fa-trash me-1"></i>
          Delete
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
type SaveFolder = {
  folder_number: number;
  created_at: string;
};

const props = defineProps({
  folder: { type: Object as () => SaveFolder, required: true }
});

const emit = defineEmits(['load', 'delete']);

const formatDate = (value: string) => {
  if (!value) {
    return '';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const datePart = date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
  const timePart = date
    .toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  return `${datePart} ${timePart}`;
};
</script>

<style scoped>
.saves-item-actions {
  width: 100%;
}

.saves-item-btn {
  width: 100%;
}

@media (min-width: 576px) {
  .saves-item-actions {
    width: auto;
  }

  .saves-item-btn {
    width: auto;
    min-width: 96px;
  }
}
</style>
