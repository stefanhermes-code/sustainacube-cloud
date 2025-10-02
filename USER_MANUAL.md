## SustainaCube: User Manual

This guide explains how to install, run, and use the SustainaCube Sustainability ExpertCenter on Windows.

### 1) Requirements
- Windows 10/11
- Python 3.8+ (3.10–3.12 recommended)
- Internet connection (for OpenAI Assistant usage)
- OpenAI API Key stored in `.env`


### 2) Start the app
- Run `run_sustainacube.bat` 

### 3) User selection and multi-user lock
- Choose your name (e.g., “Stefan Hermes” or “Bart ten Brink”).
- The app uses a lock file to prevent two people from processing at the same time. If someone else is processing, you’ll see who it is.

### 4) Loading documents
- The left sidebar shows “New Files” if there are unprocessed or updated documents.
- Click “Load New Documents” to process them.
- Progress shows current file, ETA, and file counter.
- The right sidebar’s “Quick Stats” shows:
  - Total Files Available
  - Files Processed
  - New Files

Notes:
- Skipped files (no text/unsupported) are not counted as “new” after processing.
- Processing is resumable: already-processed files are skipped on the next run unless they changed.

### 5) Asking questions
1. Enter a question in “Ask a Question”.
2. Optionally enable “Use OpenAI Assistant” to use your Assistant with Retrieval/WebSearch.
3. Click “Get Answer”. The system will:
   - Use your local document segments (fallback), or
   - Use the OpenAI Assistant if enabled.
4. Source references are shown under “📚 Sources”.

### 6) Exporting answers
- “Copy Answer (HTML)” creates a clean, professional HTML export (sans-serif, headings, lists, sources).
- “Copy Answer (Text)” creates a plain-text export.

### 7) Troubleshooting
- “New files” too high after a fresh start:
  - Expected if no cache exists yet; process once to create it.
- “Assistant error” or no sources with Assistant:
  - Ensure `OPENAI_API_KEY` and `OPENAI_ASSISTANT_ID` are set.
  - Some Assistant responses won’t attach files; the app extracts source hints from text where possible.
- OCR/Scanned PDFs:
  - The app tries OCR automatically when normal text extraction fails.
- Port in use:
  - If Streamlit can’t start, another session may be running. Close it or run `streamlit run sustainacube_minimal.py --server.port 8502`.

### 8) FAQ
- Q: Can two people process at the same time?
  - A: No. A lock prevents collisions; the sidebar shows who is processing.
- Q: Can Bart run it from Dropbox?
  - A: Yes. Each user runs their own local Streamlit server. The lock prevents simultaneous processing of the shared database.
- Q: How do I reset everything?
  - A: Not recommended. If needed, manually delete `processed_cache.json` and `chunks_store.jsonl` in `SustainaCube_RAG` while the app is closed. This forces a full reprocess.


