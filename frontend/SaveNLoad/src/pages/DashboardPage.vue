<template>
  <AppLayout>
    <div class="container-fluid px-0">
      <PageHeader title="Home" />
      <RecentList :items="activity" />
      <GameGrid :games="games" />
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import PageHeader from '@/components/organisms/PageHeader.vue';
import RecentList from '@/components/organisms/RecentList.vue';
import GameGrid from '@/components/organisms/GameGrid.vue';
import AppLayout from '@/layouts/AppLayout.vue';

const games = [];
const activity = [];
</script>
