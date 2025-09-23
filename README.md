#  Frontend (CSV-first UI)

Modern, minimal 3-panel app using **React + Vite + TypeScript + Tailwind** and **liquid-glass-react**.

Left: **Cases** · Center: **Case Dashboard** · Right: **Chat**

## Quickstart
```bash
npm i
npm run dev
```

By default, it uses a **localStorage mock** backend. Set `VITE_API_BASE` to your Python FastAPI URL to wire the real API:

```bash
# .env.local
VITE_API_BASE=http://localhost:8000
```

## Project layout
```
src/
  components/
    CaseChatPanel.tsx
    CaseDashboard.tsx
    SidebarCases.tsx
  services/
    api.ts            # axios + localStorage mock
  shell/
    AppShell.tsx
  views/
    CaseView.tsx
  store.ts            # Zustand global store
  main.tsx
  index.css
```

## Notes
- The dashboard now reflects each reimbursement stage end-to-end: intake → eligibility → documentation resolution → RCM review → reimbursement forecast → signature → final package.
- The AI chat is scripted as a deterministic workflow guide. It requests uploads, triggers dummy eligibility / conversion / RCM checks, and updates the dashboard and documents automatically.
- Chat now includes an inline uploader that only activates when the workflow requests documentation, so the user can respond without leaving the conversation.
- The shell received a refreshed dark glassmorphism look with upgraded cards, timeline, and case queue chips for a modern command-center feel.
- Sample output artifacts are generated during the flow (SOAP note draft, CMS 1500 PDF, summary text). Signed SOAP uploads kick off final package creation.
- Tailwind is kept lightweight; `liquid-glass-react` provides the glass effect containers.

## License
MIT
