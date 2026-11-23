import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { bootstrapApplication } from './bootstrap';
import App from './App';

bootstrapApplication();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
