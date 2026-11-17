# Risk Summarizer API

A FastAPI service that reads a piece of text or a public web page, summarises it with **Google Gemini**, and returns a **structured risk assessment** as validated JSON: a short summary, a risk level (`low`, `medium`, `high`) and the reasons behind it.

## Features

- Accepts **plain text** or a **URL**
- **Structured output:** the model is asked for JSON that matches a Pydantic schema, and the reply is validated before it is returned
- **Safe URL fetching:** only http/https, public IP addresses only, request timeout, 1 MB size limit, limited and re-validated redirects
- Clear error codes (`400` bad URL, `422` bad input, `502` AI service problem)
- Unit tests that run without an API key (the model call is mocked)
- Docker and Docker Compose support

## Tech stack

Python, FastAPI, Pydantic, Google Gemini API (`google-genai`), Requests, BeautifulSoup, Pytest, Docker

## Project structure

```
app/
  main.py      API routes and error handling
  schemas.py   Request, response and RiskSummary models
  llm.py       Gemini call, prompt and output validation
  fetcher.py   Safe URL download and text extraction
tests/         Unit tests (mocked model and DNS)
Dockerfile, docker-compose.yml, requirements.txt, .env.example
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env               # then put your key in .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive API docs.

Get a Gemini API key from Google AI Studio. Never commit your real `.env` file.

## Run with Docker

```bash
docker build -t risk-summarizer .
docker run --env-file .env -p 8000:8000 risk-summarizer
```

Or with Docker Compose:

```bash
docker compose up --build
```

## API

### `GET /health`
Returns `{"status": "ok"}`.

### `POST /summarize`

Send exactly one of `text` or `url`.

```bash
curl -X POST http://127.0.0.1:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"text": "Your document text, at least 50 characters long..."}'
```

```bash
curl -X POST http://127.0.0.1:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

Response shape (values are illustrative):

```json
{
  "source": "text",
  "characters_analysed": 215,
  "result": {
    "summary": "...",
    "risk_level": "high",
    "reasons": ["...", "..."]
  }
}
```

| Status | Meaning |
|---|---|
| 200 | Success |
| 400 | The URL is not allowed or could not be fetched |
| 422 | Invalid input, or not enough text (minimum 50 characters) |
| 502 | The AI service failed or returned an unexpected format |

## Tests

```bash
pytest
```

The tests cover input validation, URL safety checks, text extraction and the API routes. The Gemini call is mocked, so they run without a key or network access.

## Design notes

- **Why structured output?** Free-text summaries are hard for other code to use. A schema-validated JSON reply can be stored, filtered and displayed reliably, and invalid replies are caught instead of passed on.
- **Why validate URLs?** A server that fetches user-supplied URLs can be tricked into reaching internal services (server-side request forgery). Requests are limited to public addresses, and redirects are checked again at each step.
- **Why `def` and not `async def` for the route?** The route makes blocking network calls, so FastAPI runs it in a worker thread and the server stays responsive.
- **Prompt:** the system prompt tells the model to treat the document as data and to use only facts stated in it.

## Limitations

- The model can still **hallucinate** or misjudge risk. Treat the output as an aid for a human reader, not a verdict.
- A malicious document may try **prompt injection**. The prompt reduces the risk but cannot remove it.
- URL checks resolve the host name before downloading, so a **DNS rebinding** attack is not fully prevented.
- Pages that need JavaScript to show their content will not be extracted well.
- Input is cut to 30,000 characters.
- There is no authentication, rate limiting or caching.
- The tests mock the model, so a real Gemini call has to be checked manually with your own key.

## Ideas for next steps

- Add authentication and rate limiting
- Support PDF upload
- Evaluate summary quality on a small labelled set
- Cache results for repeated inputs
- Deploy on Render or a similar platform
