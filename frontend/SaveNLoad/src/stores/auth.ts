import { defineStore } from 'pinia';
import { ref } from 'vue';
import { useSettingsStore } from '@/stores/settings';
import { ensureCsrfToken, requestWithRetry, safeJsonParse } from '@/utils/apiClient';

type AuthUser = {
  id: number;
  username: string;
  role: string;
};

type FieldErrors = Record<string, string | string[]>;

const API_BASE = import.meta.env.VITE_API_BASE;

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
  },
  info: (msg: string) => {
    const t = (window as any).toastr;
    if (t?.info) {
      t.info(msg);
    }
  }
};

const buildErrorMessage = (data: any) => {
  const fallback = (data?.message || data?.error || '').toString().trim();
  const isGenericFallback = fallback === 'Please fix the errors below.';
  const errorMessages: string[] = [];

  const errors = data?.errors;
  if (errors && typeof errors === 'object') {
    Object.values(errors).forEach((value) => {
      if (Array.isArray(value)) {
        value.forEach((item) => {
          if (item) {
            errorMessages.push(String(item));
          }
        });
      } else if (value) {
        errorMessages.push(String(value));
      }
    });
  }

  if (errorMessages.length) {
    if (isGenericFallback) {
      return errorMessages.join(' ');
    }
    if (fallback && !errorMessages.includes(fallback)) {
      return `${fallback} ${errorMessages.join(' ')}`.trim();
    }
    return errorMessages.join(' ');
  }

  return fallback || 'Request failed.';
};

async function apiPost(path: string, body: Record<string, unknown>) {
  const csrfToken = await ensureCsrfToken();
  const response = await requestWithRetry(() => (
    fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      credentials: 'include',
      body: JSON.stringify(body)
    })
  ));

  const data = await safeJsonParse(response);
  if (!response.ok) {
    const error = new Error(buildErrorMessage(data));
    (error as any).status = response.status;
    (error as any).errors = data?.errors || null;
    throw error;
  }

  return data;
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null);
  const loading = ref(false);
  const message = ref('');
  const error = ref('');
  const fieldErrors = ref<FieldErrors | null>(null);
  const otpEmail = ref('');
  const isLoggingOut = ref(false);
  const isBootstrapped = ref(false);
  let bootstrapPromise: Promise<void> | null = null;

  const resetStatus = () => {
    message.value = '';
    error.value = '';
    fieldErrors.value = null;
  };

  const initCsrf = async () => {
    await ensureCsrfToken();
  };

  const fetchCurrentUser = async () => {
    const response = await fetch(`${API_BASE}/auth/me`, {
      method: 'GET',
      credentials: 'include'
    });

    if (response.ok) {
      const data = await response.json();
      user.value = data?.user || null;
      return;
    }

    if (response.status === 401) {
      user.value = null;
      return;
    }

    throw new Error('Failed to load current user.');
  };

  const isAuthPath = () => {
    const path = window.location.pathname;
    return [
      '/',
      '/login',
      '/register',
      '/forgot-password',
      '/reset-password',
      '/verify-otp'
    ].includes(path);
  };

  const bootstrap = async (options: { force?: boolean } = {}) => {
    if (isBootstrapped.value) {
      return;
    }

    if (!bootstrapPromise) {
      bootstrapPromise = (async () => {
        try {
          if (options.force || !isAuthPath()) {
            await fetchCurrentUser();
          }
        } catch {
          user.value = null;
        } finally {
          isBootstrapped.value = true;
        }
      })();
    }

    await bootstrapPromise;
  };

  const login = async (payload: { username: string; password: string; rememberMe: boolean }) => {
    loading.value = true;
    resetStatus();
    try {
      const data = await apiPost('/auth/login', payload);
      user.value = data?.user || null;
      message.value = data?.message || '';
      if (message.value) {
        notify.success(message.value);
      }
      return data;
    } catch (err: any) {
      error.value = err.message || '';
      if (error.value) {
        notify.error(error.value);
      }
      fieldErrors.value = err.errors || null;
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const register = async (payload: {
    username: string;
    email: string;
    password: string;
    repeatPassword: string;
  }) => {
    loading.value = true;
    resetStatus();
    try {
      const data = await apiPost('/auth/register', payload);
      message.value = data?.message || '';
      if (message.value) {
        notify.success(message.value);
      }
      return data;
    } catch (err: any) {
      error.value = err.message || '';
      if (error.value) {
        notify.error(error.value);
      }
      fieldErrors.value = err.errors || null;
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const forgotPassword = async (payload: { email: string }) => {
    loading.value = true;
    resetStatus();
    try {
      const data = await apiPost('/auth/forgot-password', payload);
      otpEmail.value = payload.email;
      message.value = data?.message || '';
      if (message.value) {
        notify.success(message.value);
      }
      return data;
    } catch (err: any) {
      error.value = err.message || '';
      if (error.value) {
        notify.error(error.value);
      }
      fieldErrors.value = err.errors || null;
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const verifyOtp = async (payload: { email: string; otp_code: string }) => {
    loading.value = true;
    resetStatus();
    try {
      const data = await apiPost('/auth/verify-otp', payload);
      message.value = data?.message || '';
      if (message.value) {
        notify.success(message.value);
      }
      return data;
    } catch (err: any) {
      error.value = err.message || '';
      if (error.value) {
        notify.error(error.value);
      }
      fieldErrors.value = err.errors || (error.value ? { otp_code: error.value } : null);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const resendOtp = async (payload: { email: string }) => {
    loading.value = true;
    resetStatus();
    try {
      const data = await apiPost('/auth/verify-otp', { ...payload, action: 'resend' });
      message.value = data?.message || '';
      if (message.value) {
        notify.success(message.value);
      }
      return data;
    } catch (err: any) {
      error.value = err.message || '';
      if (error.value) {
        notify.error(error.value);
      }
      fieldErrors.value = err.errors || null;
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const resetPassword = async (payload: { new_password: string; confirm_password: string }) => {
    loading.value = true;
    resetStatus();
    try {
      const data = await apiPost('/auth/reset-password', payload);
      message.value = data?.message || '';
      if (message.value) {
        notify.success(message.value);
      }
      return data;
    } catch (err: any) {
      error.value = err.message || '';
      if (error.value) {
        notify.error(error.value);
      }
      fieldErrors.value = err.errors || null;
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const logout = async () => {
    loading.value = true;
    resetStatus();
    isLoggingOut.value = true;
    try {
      const clientId = window.localStorage.getItem('savenload_client_id');
      if (clientId) {
        try {
          await apiPost('/api/client/unclaim/', { client_id: clientId });
        } catch (err: any) {
          error.value = err?.message || '';
          if (error.value) {
            notify.error(error.value);
          }
        } finally {
          window.localStorage.removeItem('savenload_client_id');
        }
      }
      const data = await apiPost('/auth/logout', {});
      user.value = null;
      const settingsStore = useSettingsStore();
      settingsStore.resetState();
      if (typeof window !== 'undefined') {
        window.sessionStorage.removeItem('savenload_avatar_seed');
        window.sessionStorage.removeItem('savenload_avatar_seed_label');
      }
      message.value = data?.message || '';
      if (message.value) {
        notify.success(message.value);
      }
      return data;
    } catch (err: any) {
      error.value = err.message || '';
      if (error.value) {
        notify.error(error.value);
      }
      throw err;
    } finally {
      loading.value = false;
      isLoggingOut.value = false;
    }
  };

  return {
    user,
    loading,
    message,
    error,
    fieldErrors,
    otpEmail,
    isLoggingOut,
    isBootstrapped,
    initCsrf,
    bootstrap,
    resetStatus,
    login,
    register,
    forgotPassword,
    verifyOtp,
    resendOtp,
    resetPassword,
    logout
  };
});
