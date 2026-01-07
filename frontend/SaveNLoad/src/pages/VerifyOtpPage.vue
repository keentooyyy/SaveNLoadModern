<template>
  <AuthLayout title="Save N Load" subtitle="We've sent a verification code to your email.">
    <form @submit.prevent="onSubmit">
      <div class="mb-3">
        <InputLabel text="6-Digit Verification Code" label-class="mb-2" />
        <div class="otp-grid" :class="{ 'is-invalid': !!fieldErrors?.otp_code }">
          <input
            v-for="(value, index) in otpDigits"
            :key="index"
            :ref="el => setOtpRef(el, index)"
            v-model="otpDigits[index]"
            inputmode="numeric"
            maxlength="1"
            class="otp-box"
            type="text"
            autocomplete="one-time-code"
            @input="onOtpInput(index, $event)"
            @keydown="onOtpKeydown(index, $event)"
            @paste="onOtpPaste($event)"
          />
        </div>
      </div>
      <div class="d-grid mt-2">
        <IconButton
          type="button"
          variant="secondary"
          class="text-white fw-bold py-2"
          :disabled="isResending || isVerifying"
          :loading="isResending"
          @click="onResend"
        >
          RESEND CODE
        </IconButton>
      </div>
      <AuthFooterLink prefix="Remember your password? " link-text="Login" to="/login" />
      <AuthFooterLink
        prefix="Wrong email? "
        link-text="Start Over"
        to="/forgot-password"
        text-class="mt-2"
      />
    </form>
  </AuthLayout>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import AuthLayout from '@/layouts/AuthLayout.vue';
import { useAuthStore } from '@/stores/auth';
import IconButton from '@/components/atoms/IconButton.vue';
import InputLabel from '@/components/atoms/InputLabel.vue';
import AuthFooterLink from '@/components/molecules/AuthFooterLink.vue';

const store = useAuthStore();
const router = useRouter();

const email = ref(store.otpEmail || '');
const otpDigits = ref<string[]>(Array.from({ length: 6 }, () => ''));
const otpRefs = ref<HTMLInputElement[]>([]);

const otpCode = computed(() => otpDigits.value.join(''));

watch(
  () => store.otpEmail,
  (next) => {
    if (next) {
      email.value = next;
    }
  }
);

const loading = computed(() => store.loading);
const fieldErrors = computed(() => store.fieldErrors);
const verifying = ref(false);
const resending = ref(false);
const isVerifying = computed(() => loading.value || verifying.value);
const isResending = computed(() => loading.value || resending.value);

const clearFieldError = (key: string) => {
  if (store.fieldErrors && store.fieldErrors[key]) {
    const next = { ...store.fieldErrors };
    delete next[key];
    store.fieldErrors = Object.keys(next).length ? next : null;
  }
  if (store.error) {
    store.error = '';
  }
};

watch(otpCode, (value) => {
  if (value) {
    clearFieldError('otp_code');
  }
  if (value.length === otpDigits.value.length && !loading.value) {
    onSubmit();
  }
});

const setOtpRef = (el: HTMLInputElement | null, index: number) => {
  if (!el) {
    return;
  }
  otpRefs.value[index] = el;
};

const focusOtp = (index: number) => {
  const el = otpRefs.value[index];
  if (el) {
    el.focus();
    el.select();
  }
};

const onOtpInput = (index: number, event: Event) => {
  const target = event.target as HTMLInputElement;
  const nextValue = target.value.replace(/\D/g, '');
  otpDigits.value[index] = nextValue.slice(-1);
  if (nextValue && index < otpDigits.value.length - 1) {
    focusOtp(index + 1);
  }
};

const onOtpKeydown = (index: number, event: KeyboardEvent) => {
  if (event.key === 'Backspace' && !otpDigits.value[index] && index > 0) {
    focusOtp(index - 1);
  }
};

const onOtpPaste = (event: ClipboardEvent) => {
  const data = event.clipboardData?.getData('text') || '';
  const digits = data.replace(/\D/g, '').slice(0, otpDigits.value.length).split('');
  if (!digits.length) {
    return;
  }
  event.preventDefault();
  otpDigits.value = otpDigits.value.map((_, idx) => digits[idx] || '');
  const nextIndex = Math.min(digits.length, otpDigits.value.length - 1);
  focusOtp(nextIndex);
};

const onSubmit = async () => {
  if (isVerifying.value) {
    return;
  }
  verifying.value = true;
  try {
    await store.verifyOtp({ email: email.value, otp_code: otpCode.value });
    await router.push('/reset-password');
  } catch {
    // handled by store
  } finally {
    verifying.value = false;
  }
};

const onResend = async () => {
  if (isResending.value) {
    return;
  }
  resending.value = true;
  try {
    await store.resendOtp({ email: email.value });
  } catch {
    // handled by store
  } finally {
    resending.value = false;
  }
};

onMounted(async () => {
  const config = await store.loadAuthConfig();
  if (!config.emailEnabled || !config.emailRegistrationRequired) {
    window.location.assign('/login');
  }
});
</script>

<style scoped>
.otp-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(44px, 1fr));
  gap: 0.5rem;
}

.otp-box {
  width: 100%;
  height: 4.8rem;
  border-radius: 0.5rem;
  border: 1px solid var(--color-primary);
  background-color: var(--primary-opacity-20);
  color: var(--color-white);
  font-size: 1.25rem;
  text-align: center;
  letter-spacing: 0.1rem;
}

.otp-box:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 0.15rem var(--primary-opacity-30);
}

.otp-grid.is-invalid .otp-box {
  border-color: var(--color-danger);
}

.otp-grid.is-invalid .otp-box:focus {
  box-shadow: none;
}

@media (max-width: 575.98px) {
  .otp-grid {
    gap: 0.4rem;
  }

  .otp-box {
    height: 3.2rem;
    font-size: 1.1rem;
  }
}

@media (max-width: 320px) {
  .otp-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
