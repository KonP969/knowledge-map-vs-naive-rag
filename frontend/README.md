# Frontend

React 19 + TypeScript + Vite + Tailwind. See the [root README](../README.md) for setup.

```bash
npm install
npm run dev                              # http://localhost:5173
npm run build
npx tsc -p tsconfig.app.json --noEmit    # type check
npm run test:e2e                         # Playwright smoke suite
```

`npm run dev` proxies `/api` to the backend on `http://localhost:8000`
(override with `VITE_PROXY_TARGET`).
