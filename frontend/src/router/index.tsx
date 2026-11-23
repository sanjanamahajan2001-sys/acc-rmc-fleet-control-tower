import { env } from '../config/env';
import React from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { protectedRoutes } from './protected-routes';
import { publicRoutes } from './public-routes';

const router = createBrowserRouter([...publicRoutes, protectedRoutes], {
  basename: env.VITE_BASE_URL,
});

export const AppRouter: React.FC = () => {
  return <RouterProvider router={router} />;
};

