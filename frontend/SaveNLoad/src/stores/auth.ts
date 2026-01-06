import { defineStore } from 'pinia';
import { ref } from 'vue';

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

const getCookie = (name: string) => {
  const match = document.cookie.match(new RegExp(`(^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[2]) : '';
};

const ensureCsrf = async () => {
  const token = getCookie('csrftoken');
  if (token) {
    return token;
  }
  await fetch(`${API_BASE}/auth/csrf`, { credentials: 'include' });
  return getCookie('csrftoken');
};

async function apiPost(path: string, body: Record<string, unknown>) {
  const csrfToken = await ensureCsrf();
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    },
    credentials: 'include',
    body: JSON.stringify(body)
  });

  let data: any = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const error = new Error(data?.message || data?.error || '');
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
    await ensureCsrf();
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

  const bootstrap = async () => {
    if (isBootstrapped.value) {
      return;
    }

    if (!bootstrapPromise) {
      bootstrapPromise = (async () => {
        try {
          await fetchCurrentUser();
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
