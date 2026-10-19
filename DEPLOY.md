# Deploy a free public demo (Streamlit Community Cloud)

This puts the app online with a public link that works in any browser, including
mobile Chrome. It costs nothing.

## What the public demo is (and is not)

| | On your computer | Public demo |
|---|---|---|
| AI model | Local Qwen (offline, private) | Gemini, using each visitor's own free key |
| Documents | Saved in your knowledge base | Private to each visitor, deleted on restart |
| Web search | Your Tavily key (optional) | Visitor's own Tavily key (optional) |
| Calculator, formulas, marks prediction, fill-in-the-blank quiz | Yes | Yes |
| Wikipedia background (free, no key) | Yes | Yes |

The demo detects that there is no local model and switches to hosted mode
automatically (see `hosted.py`). Your own API keys are **not** used for visitors,
so nobody can spend your quota.

## Steps

1. Push the project to GitHub (see the README). The repository must be public
   for the free plan.
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **Create app**, then choose:
   - Repository: `saurabhchandurkar2-boop/AI-Universal-Student-Assistant`
   - Branch: `main`
   - Main file path: `app.py`
4. Open **Advanced settings** and choose Python **3.12**.
5. Click **Deploy**. The first build takes a few minutes.
6. Copy the public link and put it at the top of your README.

## What visitors do

Open the link, paste a free Gemini key (from https://aistudio.google.com) into
**Connect your own keys** in the sidebar, then ask questions. They can upload
their own PDF, Word, TXT or MD files (up to 50 MB each, 20 documents).

## Good to know

- Free apps go to sleep when nobody uses them and wake up on the next visit.
- Free hosting has limited memory, so very large PDFs may fail. The upload limit
  in hosted mode is 50 MB per file.
- Uploaded files are not stored permanently. Restarting the app removes them.
- Do not put API keys in the code or in the repository.

## Test hosted mode on your own computer

```bash
# Windows PowerShell
$env:APP_MODE = "hosted"
streamlit run app.py
```

Set `APP_MODE` to `local` to force normal mode, or leave it unset to let the app
choose.
