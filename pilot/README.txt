# pilot/ — Glass Cockpit (React + Vite)

Local dev:

  npm install
  npm run dev

`vite.config.ts` proxies `/health`, `/backtest`, `/market` to `http://127.0.0.1:8000` when `VITE_ENGINE_URL` is unset.

Vercel (production):

  Set root directory to **pilot**, build `npm run build`, output **dist**.  
  Set env **`VITE_ENGINE_URL`** to your public **HTTPS** Engine base (tunnel).  
  See **`../docs/VERCEL_AND_ENGINE.txt`** and **`ENV_EXAMPLE.txt`**.
