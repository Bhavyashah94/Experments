import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import { migrateV1ToV2 } from './services/storage';
import './assets/style.css';

// Perform any schema migration on boot
migrateV1ToV2();

const app = createApp(App);
app.use(createPinia());
app.mount('#app');
