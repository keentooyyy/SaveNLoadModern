<template>
  <div class="d-flex align-items-center shadow bg-primary page-header">
    <div class="d-flex align-items-center justify-content-between gap-3 w-100 px-4">
      <div class="d-flex align-items-center gap-3">
        <span
          class="text-white d-lg-none p-0 d-flex align-items-center"
          role="button"
          tabindex="0"
          data-bs-toggle="offcanvas"
          data-bs-target="#sidebarMobile"
          aria-controls="sidebarMobile"
          aria-label="Toggle sidebar"
        >
          <i class="fas fa-bars fs-3"></i>
        </span>
        <h6 class="text-white mb-0">{{ title }}</h6>
      </div>
      <div class="d-flex align-items-center gap-3">
        <div class="dropdown">
          <button
            class="user-chip"
            type="button"
            id="headerUserMenu"
            data-bs-toggle="dropdown"
            aria-expanded="false"
          >
            <div class="d-none d-sm-flex flex-column align-items-start lh-1 text-start">
              <span class="text-white fw-semibold">Hello, {{ displayName }}</span>
            </div>
            <div class="avatar-wrap">
              <img :src="avatarUrl" :alt="avatarAlt" class="avatar" />
            </div> 
          </button>
          <ul class="dropdown-menu dropdown-menu-end user-menu shadow-lg">
            <li>
              <button class="dropdown-item text-white d-flex align-items-center gap-2" type="button" @click="emit('settings')">
                <i class="fas fa-cog"></i>
                Settings
              </button>
            </li>
            <li>
              <button class="dropdown-item text-white d-flex align-items-center gap-2" type="button" @click="emit('logout')">
                <i class="fas fa-sign-out-alt"></i>
                Log Out
              </button>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';

const emit = defineEmits(['profile', 'settings', 'logout']);

const props = defineProps({
  title: { type: String, default: 'Page' },
  userLabel: { type: String, default: '' },
  userRole: { type: String, default: '' }
});

const AVATAR_SEED_PREFIX = 'savenload_avatar_seed_';
const avatarSeed = ref('');
const lastLabel = ref('');

const randomId = () => {
  const uuid = (crypto as any)?.randomUUID?.() || Math.random().toString(16).slice(2, 10);
  const noise = Math.floor(Math.random() * 1_000_000);
  return `${uuid}-${noise}`;
};

const resolveSeed = (label: string) => {
  if (typeof window === 'undefined') {
    return randomId();
  }
  const key = `${AVATAR_SEED_PREFIX}${label || 'user'}`;
  const storedSeed = localStorage.getItem(key);
  if (storedSeed && storedSeed !== 'undefined') {
    return storedSeed;
  }
  const newSeed = randomId();
  localStorage.setItem(key, newSeed);
  return newSeed;
};

watch(
  () => props.userLabel,
  (label) => {
    if (label === lastLabel.value && avatarSeed.value) {
      return;
    }
    lastLabel.value = label;
    avatarSeed.value = resolveSeed(label || 'user');
  },
  { immediate: true }
);

const avatarUrl = computed(() => {
  const encoded = encodeURIComponent(avatarSeed.value || 'user');
  return `https://api.dicebear.com/7.x/pixel-art/svg?seed=${encoded}`;
});

const avatarAlt = computed(() => 'User avatar');
const displayName = computed(() => props.userLabel || 'User');
</script>

<style scoped>
.page-header {
  min-height: 82px;
}

.avatar {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 50%;
}

.avatar-wrap {
  position: relative;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  overflow: hidden;
  background: var(--black-opacity-30);
}

.user-chip {
  border: none;
  background: transparent;
  color: #fff;
  padding: 6px 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-chip:hover {
  background: var(--white-opacity-05);
}

.dropdown-menu.user-menu {
  min-width: 220px;
  background: #0f1625;
  border: 1px solid var(--white-opacity-12);
  border-radius: 12px;
  padding: 0.35rem 0;
  box-shadow: 0 10px 24px var(--black-opacity-50);
  margin-top: 6px;
}

.dropdown-item {
  padding: 0.65rem 1rem;
}

.dropdown-item:hover {
  background-color: var(--white-opacity-08);
}
</style>
