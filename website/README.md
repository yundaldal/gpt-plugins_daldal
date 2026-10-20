# Daldal teacher plugin toolbox

A static Korean landing page that helps teachers browse eight Daldal ChatGPT plugins, download the matching ZIP, follow the upload and install steps, and copy the first question.

## Run locally

```powershell
npm install
npm run dev
```

Vite prints the local preview URL. For the production build, run `npm run build`; the generated site is in `dist/` and can be served with `npm run preview`.

## Content and checks

- Edit the catalog in `content/plugins.json` and the guide in `content/guide.json`.
- `npm run check:content` renders `index.html` and checks the catalog, download mapping, install order, prompt, and required page copy.
- `npm run check:downloads` checks each GitHub link's resolved ZIP path and first four ZIP signature bytes; it requires network access.
- `npm run build` creates the deployable static output in `dist/`.
- `npm run test:e2e` builds the site, starts its production preview, and checks the key browser flows at desktop and mobile sizes. Install Playwright's Chromium first with `npx playwright install chromium` if needed.
- `npm run check:predeploy` audits text contrast and serves the production build under `/gpt-plugins_daldal/` to verify its assets, anchors, and plugin ZIP links.
- Review screenshots from the browser checks are saved in `review/`.

The product catalog and guide are JSON-driven; `scripts/render-content.mjs` writes the static page before dev and build commands. The page remains readable when JavaScript or image requests are unavailable.

## Publish

The site is hosted at <https://yundaldal.github.io/gpt-plugins_daldal/>. Publishing is manual: merge the site and `.github/workflows/deploy-website.yml` to `main`, open **Actions → Deploy website to GitHub Pages**, select `main`, and choose **Run workflow**. The workflow reruns the checks above before publishing `website/dist`.
