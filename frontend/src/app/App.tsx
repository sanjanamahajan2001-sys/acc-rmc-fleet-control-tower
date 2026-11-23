import { AppProviders } from './providers';
import { AppRouter } from '../router';
import '../styles/global.css';

export const App = () => {
  return (
    <AppProviders>
      <AppRouter />
    </AppProviders>
  );
};

export default App;
