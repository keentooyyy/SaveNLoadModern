import '@/styles/custom.css';
import '@/styles/app.css';
import RegisterPage from '@/pages/RegisterPage.vue';
import { mountIsland } from '@/utils/islands';

void mountIsland('register', RegisterPage);
