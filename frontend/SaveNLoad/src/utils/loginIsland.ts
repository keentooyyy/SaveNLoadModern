import '@/styles/custom.css';
import '@/styles/app.css';
import LoginPage from '@/pages/LoginPage.vue';
import { mountIsland } from '@/utils/islands';

void mountIsland('login', LoginPage);
