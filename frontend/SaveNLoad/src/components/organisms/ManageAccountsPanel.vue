<template>
  <CollapsibleCard
    title="Manage Accounts"
    icon="fa-users"
    collapse-id="manageAccountsCollapse"
    header-class="manage-accounts-header"
    icon-class="manage-accounts-icon"
    title-class="manage-accounts-title"
    chevron-class="manage-accounts-chevron"
    chevron-id="manageAccountsChevron"
  >
    <div class="mb-4">
      <InputLabel text="SEARCH BY USERNAME OR EMAIL" label-class="mb-2" />
      <InputGroup
        v-model="searchQuery"
        placeholder="Type username or email to search..."
        button-label="Search"
        button-icon="fa-search"
        button-class="text-white"
        @action="onSearch"
      />
    </div>

    <hr class="border-secondary mb-4" />

    <div class="mb-3">
      <SectionTitle text="All Users" />
      <div class="text-white">
        <div v-if="loading" class="text-center py-3">
          <div class="spinner-border text-light" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
        </div>
        <div v-else-if="error" class="text-center py-3 text-white-50">{{ error }}</div>
        <div v-else-if="!users.length" class="text-center py-3 text-white-50">No users found.</div>
        <div v-else class="table-responsive">
          <table class="table table-dark table-hover align-middle mb-0 manage-users-table">
            <thead>
              <tr>
                <th scope="col" class="text-white-50">Username</th>
                <th scope="col" class="text-white-50">Email</th>
                <th scope="col" class="text-white-50 text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in users" :key="user.id">
                <td class="fw-semibold text-white">{{ user.username }}</td>
                <td class="text-white-50">{{ user.email }}</td>
                <td class="text-end">
                  <div class="d-inline-flex gap-2">
                    <button class="btn btn-sm btn-outline-secondary text-white" type="button" @click="onReset(user)">
                      Reset Password
                    </button>
                    <button class="btn btn-sm btn-outline-danger text-white" type="button" @click="onDelete(user)">
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="pagination.total_pages > 1" class="d-flex justify-content-between align-items-center mt-3">
          <button
            class="btn btn-sm btn-outline-light"
            type="button"
            :disabled="!pagination.has_previous"
            @click="goToPage(pagination.page - 1)"
          >
            Prev
          </button>
          <span class="text-white-50 small">Page {{ pagination.page }} of {{ pagination.total_pages }}</span>
          <button
            class="btn btn-sm btn-outline-light"
            type="button"
            :disabled="!pagination.has_next"
            @click="goToPage(pagination.page + 1)"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  </CollapsibleCard>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import CollapsibleCard from '@/components/molecules/CollapsibleCard.vue';
import InputGroup from '@/components/molecules/InputGroup.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import SectionTitle from '@/components/atoms/SectionTitle.vue';
import { useSettingsStore } from '@/stores/settings';
import { useConfirm } from '@/composables/useConfirm';

type UserItem = {
  id: number;
  username: string;
  email: string;
};

const store = useSettingsStore();
const { requestConfirm } = useConfirm();
const searchQuery = ref('');
const users = ref<UserItem[]>([]);
const loading = ref(false);
const error = ref('');
const pagination = ref({
  page: 1,
  total_pages: 1,
  has_next: false,
  has_previous: false
});

const notify = {
  success: (msg: string) => {
    const t = (window as any).toastr;
    if (t?.success) {
      t.success(msg);
    }
  },
  error: (msg: string) => {
    const t = (window as any).toastr;
    if (t?.error) {
      t.error(msg);
    }
  }
};

const loadUsers = async (page = 1) => {
  loading.value = true;
  error.value = '';
  try {
    const data = await store.listUsers(searchQuery.value.trim(), page);
    users.value = data?.users || [];
    pagination.value = data?.pagination || {
      page,
      total_pages: 1,
      has_next: false,
      has_previous: false
    };
  } catch (err: any) {
    error.value = err?.message || '';
  } finally {
    loading.value = false;
  }
};

const onSearch = () => {
  loadUsers(1);
};

const goToPage = (page: number) => {
  loadUsers(page);
};

const onReset = async (user: UserItem) => {
  const confirmed = await requestConfirm({
    title: 'Reset Password',
    message: `Reset password for ${user.username}?`,
    confirmText: 'Reset',
    variant: 'danger'
  });
  if (!confirmed) {
    return;
  }
  await store.resetUserPassword(user.id);
};

const waitForDeletion = async (operationId: string) => {
  const maxAttempts = 20;
  const delayMs = 2000;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      const data = await store.checkOperationStatus(operationId);
      if (data?.completed || data?.status === 'completed') {
        return { status: 'completed', message: data?.message || '' };
      }
      if (data?.failed || data?.status === 'failed') {
        return { status: 'failed', message: data?.message || data?.error || '' };
      }
    } catch {
      return { status: 'failed', message: '' };
    }
    await new Promise((resolve) => setTimeout(resolve, delayMs));
  }

  return { status: 'failed', message: '' };
};

const waitForRemoval = async (userId: number) => {
  const maxAttempts = 5;
  const delayMs = 800;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    await loadUsers(pagination.value.page);
    if (!users.value.some((user) => user.id === userId)) {
      return true;
    }
    await new Promise((resolve) => setTimeout(resolve, delayMs));
  }

  return false;
};

const onDelete = async (user: UserItem) => {
  const confirmed = await requestConfirm({
    title: 'Delete User',
    message: `Delete user ${user.username}? This cannot be undone.`,
    confirmText: 'Delete',
    variant: 'danger'
  });
  if (!confirmed) {
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    const data = await store.deleteUser(user.id);
    const operationId = data?.operation_id;
    let completionMessage = data?.message || '';
    if (operationId) {
      const result = await waitForDeletion(operationId);
      if (result.status !== 'completed') {
        throw new Error(result.message);
      }
      completionMessage = result.message;
    }
    const removed = await waitForRemoval(user.id);
    if (!removed) {
      users.value = users.value.filter((item) => item.id !== user.id);
    }
    if (completionMessage) {
      notify.success(completionMessage);
    }
  } catch (err: any) {
    error.value = err?.message || '';
    if (error.value) {
      notify.error(error.value);
    }
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  if (store.bootstrapUsersLoaded) {
    users.value = store.users;
    pagination.value = store.usersPagination;
    return;
  }
  loadUsers(1);
});
</script>

<style scoped>
.manage-users-table {
  --bs-table-bg: transparent;
  --bs-table-border-color: var(--white-opacity-10);
  --bs-table-hover-bg: var(--white-opacity-08);
}

.manage-users-table th,
.manage-users-table td {
  border-color: var(--white-opacity-10);
}

</style>
