import { onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';

type AuthConfigOptions = {
  requireEmailFlow?: boolean;
};

export const useAuthConfig = (options: AuthConfigOptions = {}) => {
  const store = useAuthStore();

  const load = async () => {
    const config = await store.loadAuthConfig();
    if (options.requireEmailFlow && (!config.emailEnabled || !config.emailRegistrationRequired)) {
      window.location.assign('/login');
    }
    return config;
  };

  onMounted(() => {
    void load();
  });

  return {
    load
  };
};
