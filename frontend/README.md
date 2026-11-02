# Still frontend

The Vue interface loads five fixed practices from the backend catalog and keeps the profile picker, optional chat suggestion, history, and Crisis support in a low-interaction flow. The first two practices are course skills; three shorter options were authored for the app. A chat suggestion appears directly below the latest reply. One start tap begins a guided practice. Prompts advance automatically; optional speech uses the browser's speech synthesis and does not require a microphone.

Start the development server from this directory:

```sh
npm install
npm run dev
```

The app expects FastAPI at `http://127.0.0.1:8000` by default. `VITE_API_URL` can point to another local API during development. Do not put Gemini or other private credentials in Vite environment variables. Crisis support is bundled in the Vue interface and remains available if the API is offline.
