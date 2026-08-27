/**
 * Feature route registry.
 *
 * Six developers work on separate feature branches during the sprint. A single
 * hand maintained route list would conflict on every merge and would break the
 * build whenever one feature had not been merged yet.
 *
 * Instead each feature folder exports its own `routes.jsx`, and Vite's
 * `import.meta.glob` collects them at build time. Adding a feature therefore
 * means adding one file, never editing a shared one.
 *
 * Route shape:
 * ```js
 * { path: '/appointments', element: <MyAppointments />, roles: ['student'], layout: 'app' }
 * ```
 * `layout` is `'app'` (inside the signed in shell) or `'public'`.
 * `roles` omitted means any signed in role may open the screen.
 */

const modules = import.meta.glob('../features/*/routes.jsx', { eager: true });

/**
 * Collect every route declared by every feature module.
 * @returns {Array<{path: string, element: JSX.Element, roles?: string[], layout?: string}>}
 */
export function collectFeatureRoutes() {
  return Object.values(modules)
    .flatMap((module) => module.default ?? [])
    .filter((route) => route && route.path && route.element);
}

/**
 * Routes rendered outside the signed in shell, such as login and registration.
 * @returns {Array<object>} Public routes.
 */
export function publicRoutes() {
  return collectFeatureRoutes().filter((route) => route.layout === 'public');
}

/**
 * Routes rendered inside the signed in application shell.
 * @returns {Array<object>} Protected routes.
 */
export function appRoutes() {
  return collectFeatureRoutes().filter((route) => route.layout !== 'public');
}
