import { onMounted } from 'vue';

type AuthConfigOptions = {
  requireEmailFlow?: boolean;
  loadAuthConfig: () => Promise<{ emailEnabled: boolean; emailRegistrationRequired: boolean }>;
};

export const useAuthConfig = (options: AuthConfigOptions) => {
  const load = async () => {
    const config = await options.loadAuthConfig();
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
