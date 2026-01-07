<template>
  <div class="card" :class="cardClass">
    <div v-if="$slots.header" class="card-header" :class="headerClass">
      <slot name="header" />
    </div>
    <div class="card-body" :class="bodyClass">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps({
  cardClass: { type: String, default: '' },
  headerClass: { type: String, default: '' },
  bodyClass: { type: String, default: '' }
});
</script>
