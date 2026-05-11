# React / Next.js Coding Standards

Owner: Nova. All web frontend code MUST follow these standards.

## Project Structure

```
src/
├── app/                        # Next.js App Router
│   ├── (auth)/                 # Route groups for layout sharing
│   │   ├── login/page.tsx
│   │   └── layout.tsx
│   ├── (dashboard)/
│   │   ├── page.tsx
│   │   ├── loading.tsx         # Suspense loading UI
│   │   ├── error.tsx           # Error boundary
│   │   └── layout.tsx
│   ├── api/                    # Route handlers (BFF only — no business logic)
│   ├── layout.tsx              # Root layout
│   ├── not-found.tsx
│   └── global-error.tsx
├── components/
│   ├── ui/                     # Design system primitives (Button, Input, Card, etc.)
│   │   ├── Button/
│   │   │   ├── Button.tsx
│   │   │   ├── Button.test.tsx
│   │   │   ├── Button.stories.tsx
│   │   │   └── index.ts
│   │   └── ...
│   ├── features/               # Feature-specific composed components
│   │   └── {feature}/
│   │       ├── {Component}.tsx
│   │       ├── {Component}.test.tsx
│   │       └── {Component}.stories.tsx
│   └── layouts/                # Shared layout components (Header, Sidebar, etc.)
├── hooks/                      # Shared custom hooks
│   ├── use-{hook-name}.ts
│   └── __tests__/
├── lib/                        # Utilities and shared logic
│   ├── api/                    # API client, React Query hooks
│   │   ├── client.ts           # Configured fetch/axios instance
│   │   ├── hooks/              # React Query hooks per resource
│   │   │   └── use-{resource}.ts
│   │   └── types.ts            # API response/request types
│   ├── validations/            # Zod schemas for forms + API
│   ├── utils/                  # Pure utility functions
│   └── constants.ts
├── stores/                     # Zustand stores (client state only)
│   └── use-{store-name}.ts
├── styles/
│   ├── tokens.css              # Design token CSS custom properties
│   └── globals.css
├── types/                      # Shared TypeScript types
│   ├── api.ts                  # API envelope types
│   └── {domain}.ts
└── __mocks__/                  # Test mocks
```

## Layering Rules

Page → Feature Component → UI Component. Data flows down, events flow up.

- **Page (`app/**/page.tsx`)**: Data fetching (server components or React Query), layout composition, error/loading states. No direct DOM markup beyond composition.
- **Feature Component (`components/features/`)**: Composes UI components with business logic. Connects to stores/hooks. Handles user interactions.
- **UI Component (`components/ui/`)**: Pure presentational. No data fetching, no store access, no API calls. Props in, JSX out. Fully reusable and documented in Storybook.
- **Hook (`hooks/`)**: Encapsulates reusable stateful logic. No JSX. Can call other hooks.
- **API Layer (`lib/api/`)**: API calls + React Query hooks. No UI concerns.

Never import from `app/` into `components/`. Never import feature components into UI components.

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Components | `PascalCase` | `UserCard.tsx` |
| Component dirs | `PascalCase` | `components/ui/Button/` |
| Hooks | `camelCase`, `use` prefix | `use-auth.ts` → `useAuth` |
| Utilities | `camelCase` | `format-date.ts` → `formatDate` |
| Types/Interfaces | `PascalCase`, no `I` prefix | `UserProfile` (not `IUserProfile`) |
| Constants | `UPPER_SNAKE_CASE` | `MAX_PAGE_SIZE` |
| CSS classes | `camelCase` (CSS modules) or Tailwind utilities | `styles.cardWrapper` |
| Pages | `kebab-case` dirs | `app/user-profile/page.tsx` |
| Zod schemas | `camelCase` + `Schema` suffix | `loginFormSchema` |
| API hooks | `use` + verb + resource | `useCreateUser`, `useUsers` |
| Stores | `use` + store name + `Store` | `useAuthStore` |

## TypeScript Rules

- `strict: true` — no exceptions.
- No `any`. Use `unknown` + type narrowing when type is truly unknown.
- No type assertions (`as`) except in tests. Use type guards.
- All component props explicitly typed via `interface` (not inline).
- Prefer `interface` for props/objects, `type` for unions/intersections/utilities.
- Use `satisfies` for type-safe config objects.
- Discriminated unions for component variant props.

```typescript
// GOOD — discriminated union for variants
interface ButtonBaseProps {
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  children: React.ReactNode;
}

interface ButtonAsButton extends ButtonBaseProps {
  as?: 'button';
  onClick: () => void;
  href?: never;
}

interface ButtonAsLink extends ButtonBaseProps {
  as: 'a';
  href: string;
  onClick?: never;
}

type ButtonProps = ButtonAsButton | ButtonAsLink;
```

## Component Patterns

### Functional components only. No class components.

```typescript
// components/ui/UserCard/UserCard.tsx
interface UserCardProps {
  user: User;
  onSelect?: (id: string) => void;
  className?: string;
}

export function UserCard({ user, onSelect, className }: UserCardProps) {
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onSelect?.(user.id);
      }
    },
    [user.id, onSelect],
  );

  return (
    <article
      role="button"
      tabIndex={0}
      aria-label={`Select ${user.name}`}
      onClick={() => onSelect?.(user.id)}
      onKeyDown={handleKeyDown}
      className={cn(styles.card, className)}
    >
      <h3>{user.name}</h3>
      <p>{user.email}</p>
    </article>
  );
}
```

Rules:
- Named exports only. No default exports (except `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx` — Next.js requires them).
- Props interface defined in same file, above the component.
- Accept `className` prop on all UI components for composition.
- Use `cn()` (clsx/tailwind-merge) for conditional class composition.
- No inline styles except truly dynamic values (e.g., `style={{ width: `${percent}%` }}`).
- Destructure props in function signature.
- Every component in its own directory with barrel `index.ts` export.

### Server vs Client Components

```typescript
// Server Component (default in App Router) — data fetching, no interactivity
// app/users/page.tsx
export default async function UsersPage() {
  const users = await getUsers(); // server-side fetch
  return <UserList users={users} />;
}

// Client Component — interactivity, hooks, browser APIs
// components/features/users/UserList.tsx
'use client';

import { useState } from 'react';

export function UserList({ users }: { users: User[] }) {
  const [search, setSearch] = useState('');
  // ...
}
```

- Default to Server Components. Only add `'use client'` when you need interactivity, hooks, or browser APIs.
- Never pass functions as props from Server → Client components (not serializable).
- Keep client components as leaf nodes — push `'use client'` boundary as far down as possible.

## State Management

### Server state: React Query (TanStack Query)

```typescript
// lib/api/hooks/use-users.ts
export function useUsers(params?: UsersParams) {
  return useQuery({
    queryKey: ['users', params],
    queryFn: () => apiClient.get<PaginatedResponse<User>>('/api/v1/users', { params }),
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateUserRequest) =>
      apiClient.post<ApiResponse<User>>('/api/v1/users', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
```

Rules:
- React Query for ALL server state. No `useEffect` + `useState` for data fetching.
- Query keys: `[resource, ...params]` array format, always.
- Set `staleTime` per query — no global default that masks refetch behavior.
- Optimistic updates for mutations where UX demands instant feedback.
- Prefetch on hover/focus for predictable navigations.

### Client state: Zustand

```typescript
// stores/use-auth-store.ts
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  login: (user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  isAuthenticated: false,
  login: (user) => set({ user, isAuthenticated: true }),
  logout: () => set({ user: null, isAuthenticated: false }),
}));
```

Rules:
- Zustand for client-only state (UI state, auth, preferences).
- Never store server data in Zustand — that's React Query's job.
- One store per domain, not one giant store.
- Selectors for performance: `useAuthStore((s) => s.user)` not `useAuthStore()`.

## Forms & Validation

Zod schemas + React Hook Form:

```typescript
// lib/validations/user.ts
export const createUserSchema = z.object({
  email: z.string().email('Invalid email'),
  name: z.string().min(2, 'Name too short').max(100).trim(),
  role: z.enum(['admin', 'member']).default('member'),
});

export type CreateUserFormData = z.infer<typeof createUserSchema>;

// components/features/users/CreateUserForm.tsx
'use client';

export function CreateUserForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<CreateUserFormData>({
    resolver: zodResolver(createUserSchema),
  });
  const createUser = useCreateUser();

  const onSubmit = (data: CreateUserFormData) => {
    createUser.mutate(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <Input
        {...register('email')}
        label="Email"
        error={errors.email?.message}
        type="email"
        autoComplete="email"
      />
      {/* ... */}
    </form>
  );
}
```

- Zod schemas shared between frontend validation and API types.
- Derive TypeScript types from Zod (`z.infer<>`), never duplicate.
- `noValidate` on `<form>` — let Zod handle it, not browser defaults.
- Show field-level errors inline, not as a toast.
- Disable submit button during mutation (`createUser.isPending`).

## Error Handling

### Error Boundaries (Next.js)

```typescript
// app/dashboard/error.tsx
'use client';

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log to error tracking service
    reportError(error);
  }, [error]);

  return (
    <ErrorState
      title="Something went wrong"
      message={error.message}
      onRetry={reset}
    />
  );
}
```

### API Error Handling

```typescript
// lib/api/client.ts
class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      body.error?.code ?? 'UNKNOWN',
      body.error?.message ?? 'An unexpected error occurred',
      body.error?.details,
    );
  }
  const json = await response.json();
  return json.data;
}
```

Rules:
- Every page has `error.tsx` and `loading.tsx`.
- Every data-dependent component handles loading, error, and empty states.
- Never show raw error messages to users — map to friendly text.
- Log errors to monitoring service (Sentry, etc.) in error boundaries.
- API errors: catch in React Query `onError`, show toast or inline message.

## Every Screen Must Handle 4 States

```typescript
function UserList() {
  const { data, isLoading, isError, error } = useUsers();

  if (isLoading) return <UserListSkeleton />;          // Loading
  if (isError) return <ErrorState error={error} />;     // Error
  if (!data?.length) return <EmptyState />;              // Empty
  return <ul>{data.map(u => <UserCard key={u.id} user={u} />)}</ul>; // Success
}
```

No exceptions. Every component that depends on async data covers all four states.

## Accessibility (WCAG 2.1 AA)

- All interactive elements keyboard-navigable (`tabIndex`, `onKeyDown` for custom elements).
- Semantic HTML: `<button>` for actions, `<a>` for navigation, `<nav>`, `<main>`, `<article>`, `<section>` with labels.
- ARIA attributes only when semantic HTML is insufficient. Don't add `role="button"` to a `<button>`.
- Color contrast: 4.5:1 for normal text, 3:1 for large text.
- Focus management: visible focus indicator on all interactive elements. Trap focus in modals.
- Images: `alt` text on all `<img>` / `next/image`. Decorative images: `alt=""`.
- Form inputs: visible `<label>` elements (not just placeholder text).
- Announce dynamic content changes via `aria-live` regions.
- Skip navigation link as first focusable element.
- Test with screen reader (VoiceOver) and keyboard-only navigation.

## Performance

### Budgets

| Metric | Target |
|--------|--------|
| LCP | < 2.5s |
| FID / INP | < 100ms |
| CLS | < 0.1 |
| Bundle (initial JS) | < 150KB gzipped |

### Rules

- `next/image` for all images — automatic optimization, lazy loading, proper sizing.
- Code splitting: `dynamic()` import for heavy components not in initial viewport.
- `React.memo()` only when profiling proves unnecessary re-renders — not preemptively.
- `useMemo` / `useCallback` for expensive computations and stable references passed to child components. Don't wrap everything.
- Virtualize lists > 50 items (`@tanstack/react-virtual`).
- Fonts: `next/font` for zero layout shift.
- Prefetch links for likely navigations: `<Link prefetch>`.
- No barrel file re-exports in deeply nested components (causes tree-shaking issues).

## Styling

### Design Tokens First

```css
/* styles/tokens.css — generated from Pixel's design system */
:root {
  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --radius-md: 0.5rem;
  --font-body: 'Inter', sans-serif;
  /* ... */
}
```

- Pixel's design tokens are the single source of truth.
- Reference tokens via CSS custom properties or Tailwind theme extension.
- No hardcoded colors, font sizes, or spacing values in components.
- Dark mode via `[data-theme="dark"]` or `prefers-color-scheme` toggling token values.

### CSS Approach

Use CSS Modules or Tailwind CSS — pick one per project, don't mix.

```typescript
// CSS Modules
import styles from './Button.module.css';
<button className={cn(styles.button, styles[variant])} />

// Tailwind
<button className={cn('px-4 py-2 rounded-md font-medium', variantStyles[variant])} />
```

## Testing

### Test Types & Framework Stack

| Test Type | Framework | Location | Run By |
|-----------|-----------|----------|--------|
| Unit (components, hooks) | Vitest + @testing-library/react | `*.test.tsx` colocated | CI (every commit) |
| Integration (pages, features) | Vitest + MSW + React Query | `*.test.tsx` colocated | CI (every commit) |
| E2E (user flows) | Playwright | `e2e/` | CI (every PR) |
| Visual Regression / Screenshot | Playwright visual comparisons + Storybook | `e2e/` + `*.stories.tsx` | CI (every PR) |
| Performance | Lighthouse CI | CI pipeline | CI (every PR) |
| Load / Stress | k6 (backend) + Lighthouse throttled | `load-tests/` | CI (pre-release) |
| Security | npm audit + ESLint security rules + OWASP ZAP | CI pipeline | CI (every PR) |
| Accessibility | axe-core + Playwright a11y + Storybook a11y addon | Integrated | CI (every PR) |
| Storybook (component docs) | Storybook + @storybook/test | `*.stories.tsx` colocated | CI (every PR) |

### Unit Tests — Components (Vitest + Testing Library)

```typescript
// components/ui/Button/Button.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

describe('Button', () => {
  it('calls onClick when clicked', async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Save</Button>);

    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled onClick={vi.fn()}>Save</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('renders all variants without crashing', () => {
    const variants = ['primary', 'secondary', 'ghost'] as const;
    variants.forEach((variant) => {
      const { unmount } = render(<Button variant={variant} onClick={vi.fn()}>Test</Button>);
      expect(screen.getByRole('button')).toBeInTheDocument();
      unmount();
    });
  });
});
```

### Integration Tests — Pages/Features (MSW)

```typescript
// components/features/users/UserList.test.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  http.get('/api/v1/users', () =>
    HttpResponse.json({ status: 'success', data: [mockUser] }),
  ),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('UserList', () => {
  it('renders users from API', async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <UserList />
      </QueryClientProvider>,
    );

    expect(await screen.findByText(mockUser.name)).toBeInTheDocument();
  });

  it('shows error state when API fails', async () => {
    server.use(
      http.get('/api/v1/users', () =>
        HttpResponse.json({ status: 'error', error: { code: 'INTERNAL', message: 'Server error' } }, { status: 500 }),
      ),
    );

    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <UserList />
      </QueryClientProvider>,
    );

    expect(await screen.findByText(/something went wrong/i)).toBeInTheDocument();
  });

  it('shows empty state when no users', async () => {
    server.use(
      http.get('/api/v1/users', () =>
        HttpResponse.json({ status: 'success', data: [] }),
      ),
    );

    render(
      <QueryClientProvider client={new QueryClient()}>
        <UserList />
      </QueryClientProvider>,
    );

    expect(await screen.findByText(/no users/i)).toBeInTheDocument();
  });
});
```

### E2E Tests — Playwright

```typescript
// e2e/users.spec.ts
import { test, expect } from '@playwright/test';

test.describe('User management', () => {
  test('user can create a new account', async ({ page }) => {
    await page.goto('/signup');
    await page.getByLabel('Email').fill('test@example.com');
    await page.getByLabel('Name').fill('Test User');
    await page.getByRole('button', { name: 'Sign up' }).click();

    await expect(page.getByText('Welcome, Test User')).toBeVisible();
  });

  test('user can search and filter', async ({ page }) => {
    await page.goto('/users');
    await page.getByPlaceholder('Search users').fill('Alice');

    await expect(page.getByRole('article')).toHaveCount(1);
    await expect(page.getByText('Alice')).toBeVisible();
  });

  test('shows error page on server failure', async ({ page }) => {
    await page.route('**/api/v1/users', (route) =>
      route.fulfill({ status: 500, body: '{}' }),
    );
    await page.goto('/users');

    await expect(page.getByText('Something went wrong')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Retry' })).toBeVisible();
  });
});
```

### Visual Regression / Screenshot Tests

**Playwright visual comparisons for pages:**

```typescript
// e2e/visual/users.visual.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Visual regression', () => {
  test('users page matches snapshot', async ({ page }) => {
    await page.goto('/users');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('users-page.png', { maxDiffPixelRatio: 0.01 });
  });

  test('users page dark mode matches snapshot', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto('/users');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('users-page-dark.png', { maxDiffPixelRatio: 0.01 });
  });

  test('users page mobile matches snapshot', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/users');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('users-page-mobile.png', { maxDiffPixelRatio: 0.01 });
  });
});
```

**Storybook for component-level visual testing:**

```typescript
// components/ui/Button/Button.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';

const meta: Meta<typeof Button> = {
  component: Button,
  tags: ['autodocs'],
  argTypes: {
    variant: { control: 'select', options: ['primary', 'secondary', 'ghost'] },
    size: { control: 'select', options: ['sm', 'md', 'lg'] },
  },
};
export default meta;

type Story = StoryObj<typeof Button>;

export const Primary: Story = {
  args: { variant: 'primary', children: 'Click me' },
};

export const Disabled: Story = {
  args: { variant: 'primary', children: 'Click me', disabled: true },
};

export const Loading: Story = {
  args: { variant: 'primary', children: 'Saving...', loading: true },
};

export const AllVariants: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem' }}>
      <Button variant="primary">Primary</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="ghost">Ghost</Button>
    </div>
  ),
};
```

Rules:
- Every UI component (`components/ui/`) MUST have a Storybook story.
- Every variant, every state (default, hover, disabled, loading, error).
- Use `tags: ['autodocs']` for auto-generated documentation.
- Feature components get stories too if reusable across pages.
- Playwright visual tests for full-page screenshots (light, dark, mobile).
- Update snapshots via `npx playwright test --update-snapshots`, review diff, commit.

### Performance Tests (Lighthouse CI)

```yaml
# .lighthouserc.yml
ci:
  collect:
    url:
      - http://localhost:3000/
      - http://localhost:3000/users
      - http://localhost:3000/login
    settings:
      chromeFlags: '--no-sandbox'
  assert:
    assertions:
      categories:performance:
        - error
        - minScore: 0.9
      categories:accessibility:
        - error
        - minScore: 0.95
      first-contentful-paint:
        - warn
        - maxNumericValue: 2000
      largest-contentful-paint:
        - error
        - maxNumericValue: 2500
      cumulative-layout-shift:
        - error
        - maxNumericValue: 0.1
      total-blocking-time:
        - warn
        - maxNumericValue: 300
      interactive:
        - warn
        - maxNumericValue: 3500
```

```json
// package.json scripts
{
  "scripts": {
    "lighthouse": "lhci autorun",
    "lighthouse:collect": "lhci collect --url=http://localhost:3000"
  }
}
```

Performance budgets:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| LCP | < 2.5s | > 3.0s |
| FID / INP | < 100ms | > 200ms |
| CLS | < 0.1 | > 0.15 |
| Bundle (initial JS) | < 150KB gzipped | > 180KB |
| Performance score | > 90 | < 85 |

Rules:
- Lighthouse CI runs on every PR against affected pages.
- Block merge if LCP regresses >200ms, CLS regresses >0.05, or bundle size increases >5KB.
- Track Web Vitals in production via `next/web-vitals` callback.
- Code splitting: `dynamic()` import for heavy components not in initial viewport.

### Load / Stress Tests (k6)

```javascript
// load-tests/k6/users-load.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 50 },   // ramp up
    { duration: '2m', target: 50 },     // sustain
    { duration: '30s', target: 200 },   // spike
    { duration: '1m', target: 200 },    // sustain spike
    { duration: '30s', target: 0 },     // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const res = http.get(`${__ENV.BASE_URL}/api/v1/users?limit=20`);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  sleep(1);
}
```

Rules:
- k6 load tests run against staging before every release.
- Thresholds: P95 < 500ms, P99 < 1000ms, error rate < 1%.
- Include spike tests (sudden traffic surge) and soak tests (30+ minutes).
- Frontend load: Lighthouse with CPU/network throttling simulates slow devices.
- Results stored in `docs/load-test-results/` with date-stamped reports.

### Security Tests

```typescript
// Security-focused tests
describe('Security', () => {
  it('CSP headers are set correctly', async ({ page }) => {
    const response = await page.goto('/');
    const csp = response?.headers()['content-security-policy'];
    expect(csp).toBeDefined();
    expect(csp).not.toContain('unsafe-eval');
  });

  it('no secrets in client bundle', async ({ page }) => {
    await page.goto('/');
    const scripts = await page.evaluate(() =>
      Array.from(document.querySelectorAll('script[src]')).map((s) => (s as HTMLScriptElement).src),
    );
    for (const src of scripts) {
      const content = await (await fetch(src)).text();
      expect(content).not.toMatch(/NEXT_PUBLIC_.*SECRET/i);
      expect(content).not.toMatch(/sk_live_/);
      expect(content).not.toMatch(/password/i);
    }
  });
});
```

CI pipeline security checks:

```json
// package.json scripts
{
  "scripts": {
    "security:audit": "npm audit --audit-level=high",
    "security:lint": "eslint --config .eslintrc.security.js src/",
    "security:zap": "zap-cli quick-scan --self-contained http://localhost:3000"
  }
}
```

ESLint security rules (`.eslintrc.security.js`):

```javascript
module.exports = {
  plugins: ['security'],
  rules: {
    'security/detect-object-injection': 'warn',
    'security/detect-non-literal-regexp': 'warn',
    'security/detect-eval-with-expression': 'error',
    'security/detect-no-csrf-before-method-override': 'error',
    'no-eval': 'error',
  },
};
```

Rules:
- `npm audit` runs on every PR. Fail on high/critical vulnerabilities.
- ESLint security plugin catches common patterns (eval, object injection, CSRF).
- OWASP ZAP scan on staging before each release.
- CSP headers tested — no `unsafe-eval`.
- Client bundle scanned for leaked secrets.
- `dangerouslySetInnerHTML` flagged in code review — must use DOMPurify.
- @Shield reviews security test coverage as part of security review.

### Accessibility Tests

```typescript
// Playwright accessibility tests
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility', () => {
  test('users page has no accessibility violations', async ({ page }) => {
    await page.goto('/users');
    await page.waitForLoadState('networkidle');

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test('login form is keyboard navigable', async ({ page }) => {
    await page.goto('/login');

    await page.keyboard.press('Tab'); // email input
    await expect(page.getByLabel('Email')).toBeFocused();

    await page.keyboard.press('Tab'); // password input
    await expect(page.getByLabel('Password')).toBeFocused();

    await page.keyboard.press('Tab'); // submit button
    await expect(page.getByRole('button', { name: /sign in/i })).toBeFocused();
  });

  test('focus is trapped in modal', async ({ page }) => {
    await page.goto('/users');
    await page.getByRole('button', { name: 'Create User' }).click();

    // Focus should be inside modal
    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();

    // Tab through all elements — focus should not escape modal
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab');
      const focused = page.locator(':focus');
      await expect(focused).toBeAttached();
      // Verify focused element is inside the modal
      const isInModal = await focused.evaluate(
        (el, modalEl) => modalEl?.contains(el) ?? false,
        await modal.elementHandle(),
      );
      expect(isInModal).toBe(true);
    }
  });

  test('images have alt text', async ({ page }) => {
    await page.goto('/users');
    const images = page.locator('img');
    const count = await images.count();

    for (let i = 0; i < count; i++) {
      const alt = await images.nth(i).getAttribute('alt');
      expect(alt).not.toBeNull();
      // alt="" is valid for decorative images
    }
  });

  test('color contrast meets WCAG AA', async ({ page }) => {
    await page.goto('/users');
    const results = await new AxeBuilder({ page })
      .withRules(['color-contrast'])
      .analyze();

    expect(results.violations).toEqual([]);
  });
});
```

Storybook a11y addon:

```typescript
// .storybook/main.ts
export default {
  addons: [
    '@storybook/addon-a11y', // adds accessibility panel to every story
  ],
};
```

Rules:
- axe-core runs on every page during Playwright E2E — zero critical/serious violations.
- Keyboard navigation tested for all interactive flows.
- Focus trapping tested for all modals and dialogs.
- Color contrast tested via axe-core `color-contrast` rule.
- All images have `alt` attributes (decorative images: `alt=""`).
- Storybook a11y addon enabled — shows violations on every component story.
- Skip navigation link verified as first focusable element.
- `aria-live` regions tested for dynamic content updates.
- CI blocks merge on any critical or serious accessibility violation.
- Accessibility regressions are P1 bugs (see operational-standards.md).

### Testing Rules Summary

- Test behavior, not implementation. Query by role/label/text, not CSS class or test ID.
- MSW for API mocking in component tests — no manual fetch mocks.
- Coverage: 80%+ for UI components, 60%+ for pages.
- Storybook story for every UI component — doubles as visual documentation.
- Playwright for critical user flows and visual regression.
- Lighthouse CI for performance gates on every PR.
- k6 for load testing against staging pre-release.
- axe-core for automated accessibility checks on every page.
- Security: npm audit + ESLint security plugin + OWASP ZAP.
- All tests must be deterministic and independent.

## API Integration Patterns

```typescript
// lib/api/client.ts
const BASE_URL = process.env.NEXT_PUBLIC_API_URL;

export const apiClient = {
  get: <T>(path: string, config?: RequestConfig) =>
    fetchWithAuth<T>(`${BASE_URL}${path}`, { method: 'GET', ...config }),

  post: <T>(path: string, body: unknown, config?: RequestConfig) =>
    fetchWithAuth<T>(`${BASE_URL}${path}`, {
      method: 'POST',
      body: JSON.stringify(body),
      ...config,
    }),
  // put, patch, delete ...
};
```

- Centralized API client with auth token injection.
- One React Query hook file per resource (`use-users.ts`, `use-products.ts`).
- Never call `fetch` directly in components — always go through `apiClient` → React Query hook.
- API base URL from env var `NEXT_PUBLIC_API_URL`.

## Security in Code

- No secrets in client code. Only `NEXT_PUBLIC_*` env vars are exposed to browser.
- Sanitize user-generated HTML (if you must render it) via `DOMPurify`.
- CSRF: use `SameSite=Strict` cookies, not localStorage for tokens.
- Auth tokens: `httpOnly` cookie preferred. If localStorage, clear on logout and set short expiry.
- CSP headers configured in `next.config.js` or middleware.
- Never use `dangerouslySetInnerHTML` unless content is sanitized.
- Validate all URL parameters and search params before use.

## Observability

### Error Tracking

- Wrap the app in an error boundary that reports to your error tracking service (Sentry, BugSnag, etc.).
- Configure: user context (ID, email hash), environment tags (staging/production), release version.
- Source maps: upload on every build — without them stack traces are minified gibberish.
- Breadcrumbs: automatically capture console logs, navigation events, user clicks, XHR/fetch calls.
- Custom context: attach React component tree, current route, feature flags to error reports.

```typescript
// app/layout.tsx
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  release: process.env.NEXT_PUBLIC_APP_VERSION,
  integrations: [
    new Sentry.Replay({
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],
  tracesSampleRate: 0.1,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
});
```

Rules:
- Every error-prone boundary (pages, feature components) wrapped in error boundary.
- User ID and email hash attached before sensitive operations.
- Source maps uploaded automatically via build step or deployment hook.
- Sentry DSN from `NEXT_PUBLIC_SENTRY_DSN` environment variable.

### Client-Side Logging

- Structured log entries: `{ level, timestamp, message, context: { route, userId, sessionId, traceId } }`.
- Log transport: batch and send to your logging backend (never log to console in production except errors).
- Log levels: error (unexpected), warn (degraded experience), info (user milestones), debug (dev only).
- Never log PII, tokens, passwords, or full request/response bodies on the client.

```typescript
// lib/logging/client-logger.ts
const clientLogger = {
  error: (message: string, context?: Record<string, unknown>) => {
    const entry = {
      level: 'error',
      timestamp: new Date().toISOString(),
      message,
      context: { ...context, userId: userStore.userId, sessionId: sessionStore.sessionId },
    };
    // Send to logging backend
    sendToLoggingBackend(entry);
  },
  info: (message: string, context?: Record<string, unknown>) => {
    if (process.env.NODE_ENV === 'production') {
      const entry = { level: 'info', timestamp: new Date().toISOString(), message, context };
      sendToLoggingBackend(entry);
    }
  },
};
```

### Performance Monitoring (Real User Monitoring / RUM)

- Track Web Vitals: LCP, FID/INP, CLS, TTFB, FCP — report to your RUM provider.
- Custom performance marks: wrap critical flows (search, checkout, data table render) with `performance.mark()` / `performance.measure()`.
- Bundle size monitoring: track JS payload size per route — alert if a route exceeds budget.
- API call latency: measure and report fetch duration per endpoint from the client perspective.
- Long task detection: use `PerformanceObserver` for tasks > 50ms, report to metrics backend.

```typescript
// lib/observability/web-vitals.ts
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

function sendMetrics(metric: Metric) {
  // Send to RUM backend (DataDog, New Relic, etc.)
  navigator.sendBeacon(`${process.env.NEXT_PUBLIC_METRICS_URL}/vitals`, {
    name: metric.name,
    value: metric.value,
    id: metric.id,
    rating: metric.rating,
  });
}

getCLS(sendMetrics);
getFID(sendMetrics);
getFCP(sendMetrics);
getLCP(sendMetrics);
getTTFB(sendMetrics);

// Custom performance tracking
export function trackPerformance(name: string, fn: () => void) {
  performance.mark(`${name}-start`);
  fn();
  performance.mark(`${name}-end`);
  performance.measure(name, `${name}-start`, `${name}-end`);
}
```

### Session & User Journey Tracking

- Generate a client session ID on page load, attach to all logs and traces.
- Trace ID propagation: pass `traceparent` header on API calls to correlate frontend → backend traces.
- Route change tracking: log every navigation with `{ from, to, duration }`.
- Feature flag exposure tracking: log when a user is exposed to a flag variant.

```typescript
// lib/observability/session.ts
import { useRouter } from 'next/navigation';

export function useSessionTracking() {
  const router = useRouter();
  const [sessionId] = useState(() => crypto.randomUUID());

  useEffect(() => {
    const handleRouteChange = (from: string, to: string) => {
      const duration = performance.now() - routeStartTime.current;
      clientLogger.info('route_change', { from, to, duration, sessionId });
      routeStartTime.current = performance.now();
    };

    // Attach to all fetch/XHR calls
    const originalFetch = window.fetch;
    window.fetch = function (...args) {
      const headers = args[1]?.headers || {};
      return originalFetch.call(window, args[0], {
        ...args[1],
        headers: {
          ...headers,
          'traceparent': `00-${traceId}-${spanId}-01`,
        },
      });
    };

    return () => {
      window.fetch = originalFetch;
    };
  }, [sessionId]);

  return sessionId;
}
```

### Server-Side Observability (Next.js API Routes / SSR)

- Structured JSON logging in API routes and middleware (follows shared-standards.md baseline).
- Request correlation: generate or propagate `traceId` in middleware, attach to all logs.
- Health check endpoint: `GET /api/health` returning `{ status, version, uptime }`.
- SSR performance: track server-side render duration per page, report to metrics backend.

```typescript
// app/api/health/route.ts
export async function GET() {
  return Response.json({
    status: 'ok',
    version: process.env.NEXT_PUBLIC_APP_VERSION,
    uptime: process.uptime(),
  });
}

// middleware.ts — correlation ID propagation
import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  const traceId = request.headers.get('x-trace-id') || crypto.randomUUID();
  const requestId = crypto.randomUUID();

  const response = NextResponse.next({
    request: {
      headers: new Headers(request.headers),
    },
  });

  response.headers.set('x-trace-id', traceId);
  response.headers.set('x-request-id', requestId);

  return response;
}
```

### Alerting Thresholds (reference operational-standards.md)

- LCP P75: alert if > 2.5s
- CLS P75: alert if > 0.1
- INP P75: alert if > 200ms
- JS error rate: alert if > 1% of sessions
- API route error rate: alert if > 1% over 5-minute window
- API route P99 latency: alert if > 2x SLO target

### Key Rules

- Error tracking, RUM, and logging providers are configured via environment variables — never hardcode vendor SDKs inline.
- All observability code in a dedicated `lib/observability/` directory.
- Reference `@.claude/rules/shared/shared-standards.md` for the baseline.
- Reference `@.claude/rules/shared/operational-standards.md` for SLO/alerting definitions.

## Environment & Configuration

```typescript
// lib/env.ts — validate client-side env vars at build time
import { z } from 'zod';

const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url(),
  NEXT_PUBLIC_SENTRY_DSN: z.string().optional(),
});

export const env = envSchema.parse({
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  NEXT_PUBLIC_SENTRY_DSN: process.env.NEXT_PUBLIC_SENTRY_DSN,
});
```

- Validate env vars at build time — fail the build on missing required vars.
- Type-safe access via the validated `env` object, never raw `process.env`.
