import { RouterProvider } from 'react-router';
import { router } from './routes';
import { LanguageProvider } from "./lib/language";

export default function App() {
  return (
    <LanguageProvider>
      <RouterProvider router={router} />
    </LanguageProvider>
  );
}
