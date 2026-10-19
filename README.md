# AI Universal Student Assistant

A learning and knowledge assistant for students and self-learners. It combines
a small **local AI model**, **document-based answers (RAG)**, optional **web
search** and an optional **Gemini** model in one Streamlit app.

## Goal

Build a universal learning assistant, not just a chatbot. It should help
school, college and engineering students, competitive-exam aspirants and
professionals to learn topics, understand their own documents, research
questions and solve academic problems, on modest hardware.

## Features

- **Chat** – answers questions and follow-ups. A router picks between
  local Qwen, local documents, web search and Gemini. Each answer shows how
  long it took and which of your notes were given to the model. When your notes
  have no good match, it can use a short Wikipedia extract as background
  (free, no key; switch it off in the sidebar). Wikipedia links are shown under
  the answer so you can check the source.
- **Knowledge base** – upload PDF, Word (.docx), TXT or Markdown files from
  the sidebar. They are converted to text, indexed and used to ground answers.
  Large PDFs are read page by page with a progress bar (a 300-page test PDF
  took about 2 seconds to import). Documents can be listed and removed from the
  same sidebar. Uploads up to 300 MB are accepted.
- **Formulas and calculator** – exact results for numerical work, computed with
  Python instead of the AI model. Type an expression such as `(12 + 8) * 3 / 4`
  or `20% of 150`, or pick a formula (Ohm's law, Newton's second law, equations
  of motion, kinetic energy, Pythagoras, interest and more), choose the unknown
  and get the answer with the working. Plain calculations typed in the chat are
  answered by the same calculator.
- **Marks prediction** – a small scikit-learn model that gives an *estimate*
  from study hours, attendance and assignments. It is trained on a small
  **synthetic** sample dataset (`dataset/students.csv`, see `dataset/README.md`),
  so treat it as a demo.
- **Notes summarizer** – short summaries of pasted notes. It uses the same
  local llama server, and splits long notes into chunks.
- **Write & learn** – explain a topic, write an essay or answer, improve your
  own writing, or turn text or a document into study notes. Choose the level
  (class 6 to 8, 9 to 12, college), the length and the language (English, Hindi,
  Marathi, Bengali, Tamil, Telugu, Spanish, French, German, Arabic). Quality
  depends on the model: Gemini online is much stronger than the small local
  model, and long answers are slow on a CPU-only computer.
- **Quiz** – practice questions from any document in your knowledge base.
  Fill-in-the-blank questions (including formula completion) are built
  directly from your notes, so they are instant and need no AI. An optional AI
  mode asks the model for question and answer pairs and falls back to
  fill-in-the-blank when its output cannot be used.

## Look and feel

The interface uses a dark theme with Material icons, defined in `ui_theme.py` and
`.streamlit/config.toml`. Fonts load from Google Fonts, so the first load needs
internet; without it the app falls back to system fonts.

## How it works

```
Streamlit app (app.py)
   └─ chatbot.py ── ai_router.py ── routes each question to:
        ├─ Local Qwen 2.5 0.5B (llama.cpp server)   [fast default]
        ├─ Local RAG (knowledge/retriever.py)        [your documents]
        ├─ Tavily web search                         [optional, live info]
        └─ Gemini                                    [optional, hard questions]
   └─ quality_control.py / accuracy.py – checks and cleans answers

Uploads: documents_to_import → knowledge/ingest → knowledge/documents → index
```

## Requirements

- Python 3.10+ (developed on 3.13) and Windows, macOS or Linux
- About 8 GB RAM for the local model; no GPU needed
- [llama.cpp](https://github.com/ggml-org/llama.cpp) `llama-server`
- The model file `qwen2.5-0.5b-instruct-q4_k_m.gguf`

## Setup

```bash
git clone https://github.com/saurabhchandurkar2-boop/AI-Universal-Student-Assistant.git
cd AI_Student_Assistant
python -m venv venv
venv\Scripts\activate          # Windows  (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
```

**1. Get the local model.** Download `qwen2.5-0.5b-instruct-q4_k_m.gguf`
(for example from the Qwen2.5-0.5B-Instruct-GGUF page on Hugging Face) and put
it at `models/qwen/qwen2.5-0.5b-instruct-q4_k_m.gguf`.

**2. Start the local model server** (leave it running):

```bash
llama-server -m models/qwen/qwen2.5-0.5b-instruct-q4_k_m.gguf --host 127.0.0.1 --port 8080 --ctx-size 2048 --threads 4
```

**3. (Optional) Add API keys.** Copy `.env.example` and set the values as
environment variables. Without keys the app still works with the local model
and your documents.

```powershell
$env:GEMINI_API_KEY="your-key"
$env:TAVILY_API_KEY="your-key"
```

**4. Run the app:**

```bash
streamlit run app.py
```

## Free public demo

You can put a free online demo on Streamlit Community Cloud so anyone can try it
in a browser, including on a phone. The demo answers with Gemini using each
visitor's own key, and each visitor's documents stay private. See
[DEPLOY.md](DEPLOY.md). The fully offline Qwen version is the one you run on
your own computer.

## Using your own documents

Open the **Knowledge Base** section in the sidebar, choose PDF, Word, TXT or MD
files and click **Add to knowledge base**. Ask questions in the Chatbot tab.
Scanned PDFs without a text layer are not supported (they need OCR first).

## Sample knowledge

On first run the app imports six short sample study notes from
`documents_to_import/` (Ohm's law, Newton's laws, equations of motion,
photosynthesis, Pythagoras theorem, Indian independence movement) so you can try
questions right away.

## Tests and evaluation

```bash
python tests/test_smoke.py          # upload, remove and predictor checks
python tests/test_hosted.py         # hosted-mode privacy and key checks
python tests/test_quiz.py           # quiz generator checks
python tests/test_wiki.py           # Wikipedia lookup checks (no internet needed)
python tests/test_study_helper.py   # Write & learn prompt checks
python eval/retrieval_eval.py       # 15 questions with known answers
```

`eval/retrieval_eval.py` checks that the retriever finds the right document and
text. It does not need the llama server. On the bundled sample notes it finds
the correct source for 15/15 questions, including formula questions. This is a small, easy test set, so it
shows the pipeline works, not that retrieval is perfect on your own documents.
It does not test the quality of the model's final answers.

## Known limitations

- The local 0.5B model is small. It can give weak or wrong answers, so answers
  should be checked. For numbers, use the Formulas tab or type the calculation
  in the chat: those results are exact. Word problems written in sentences are
  still answered by the AI model and may be wrong.
- PDF text extraction keeps symbols such as ², × and ½, but complex layouts
  (multi-column pages, equations drawn as images, tables) may not extract
  cleanly. Pages that are scans need OCR first and are skipped with a warning.
- Wikipedia background needs an internet connection. The page found can be only
  loosely related to the question, and the model can still misread it, so check
  the linked source.
- Marks prediction is trained on synthetic data. It is not a real predictor.
- The Notes Summarizer uses the llama server. If the server is not running it
  falls back to downloading a second Qwen model through `transformers`
  (install `requirements-local-extra.txt` first; large download, slow on small
  machines).
- GitHub hosts the code only. The fully offline version needs the local model
  server on your own machine. The free online demo uses Gemini instead (see
  [DEPLOY.md](DEPLOY.md)).
- Privacy: documents you upload and questions you ask stay on your machine,
  except text sent to Gemini or Tavily when you enable those keys.

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## License

MIT – see [LICENSE](LICENSE).

## Credits

Wikipedia extracts are shown with a link to the source page and are available
under the Creative Commons Attribution-ShareAlike license.

The interface uses the Inter and Poppins fonts, bundled under the SIL Open Font
License 1.1 (see `static/fonts/FONT-LICENSES.txt`).
