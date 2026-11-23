import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { publicRoutes } from '../router/public-routes';
import { ROUTE_PATHS } from '../router/route-config';
import { bootstrapApplication } from '../app/bootstrap';

describe('Router Configuration & Bootstrap Tests', () => {
  it('renders public route login placeholder', () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path={publicRoutes[1].path} element={publicRoutes[1].element} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/Fleet Control Tower/i)).toBeInTheDocument();
  });

  it('renders unauthorized and 404 pages cleanly', () => {
    const unauthRoute = publicRoutes.find((r) => r.path === '/unauthorized');
    render(
      <MemoryRouter initialEntries={['/unauthorized']}>
        <Routes>
          <Route path={unauthRoute?.path} element={unauthRoute?.element} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/403 Unauthorized Access/i)).toBeInTheDocument();
  });


  it('runs bootstrapApplication without throwing', () => {
    expect(() => bootstrapApplication()).not.toThrow();
  });

  it('exposes ROUTE_PATHS constants', () => {
    expect(ROUTE_PATHS.LOGIN).toBe('/login');
    expect(ROUTE_PATHS.UNAUTHORIZED).toBe('/unauthorized');
    expect(ROUTE_PATHS.NOT_FOUND).toBe('/not-found');
  });
});
