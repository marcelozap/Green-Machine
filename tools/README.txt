These binaries are **not** stored on GitHub (too large; use releases instead).

**After you clone this repo**, download into `tools/`:

```powershell
powershell -ExecutionPolicy Bypass -File tools/download.ps1
```

Then:

```powershell
.\tools\cloudflared.exe tunnel --url http://127.0.0.1:8000
.\tools\flyctl.exe version
```

Official release pages (same URLs the script uses):

- cloudflared: https://github.com/cloudflare/cloudflared/releases  
- flyctl: https://github.com/superfly/flyctl/releases  

More context: **docs/TUNNELS_PC.txt**
