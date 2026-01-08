import '@/styles/custom.css';
import '@/styles/app.css';
import SettingsPage from '@/pages/SettingsPage.vue';
import { mountIsland } from '@/utils/islands';

void mountIsland('settings', SettingsPage);
