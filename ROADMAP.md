# Roadmap

**Goal:** a universal learning assistant that helps people learn, understand
documents, research topics and solve academic problems.

| Stage | Focus | Status |
|---|---|---|
| V26 | Stability, speed and answer quality | Mostly done |
| V27 | Better RAG (chunking, retrieval, source use) | In progress – upload, index, remove and a 12-question retrieval test work; needs a larger test set |
| V28 | Student features (better marks model, summarizer, revision tools) | Partly done – exact calculator and formula solver, summarizer uses the llama server; marks model still uses synthetic data; quiz from notes, Wikipedia background and a Write & learn tab added |
| V29 | UI/UX polish | Mostly done – dark theme, icons, clear buttons; needs user testing and screenshots |
| V30 | Testing and evaluation (question set with known answers, scores) | Started – smoke tests and retrieval evaluation; answer-quality evaluation still to do |
| V31 | Deployment and portfolio (docs, screenshots, setup guide) | Started – README, license, requirements |

## Next steps

- Grow the test set and add an answer-quality evaluation (full chatbot).
- Replace the synthetic marks dataset with real, consented data.
- Add OCR for scanned PDFs.
- Solve word problems by extracting the numbers and using the formula solver.
- Hide cover pages and tables of contents from search results.
- Streaming answers (needs care: the answer engine retries and edits answers after generation).
