# VibeCheck-AI
Festival Feedback Detective | evidence-grounded AI review intelligence CLI

## Runtime logs

LLM review processing writes success and failure events to
`logs/llm_service.log`. Every failed API attempt also gets its own diagnostic
file in `logs/errors/`, including the error type, message, and traceback. Log
files are local runtime data and are ignored by Git.

## LLM provider

OpenAI is used by default. To use Gemini, set these values in `.env`:

```text
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash
```

Set `LLM_PROVIDER=openai` and `OPENAI_API_KEY` to use OpenAI. API keys must
remain in `.env` and must not be committed.

When `LLM_PROVIDER=openai`, a failed OpenAI request is automatically retried
with Gemini if `GEMINI_API_KEY` is configured. Each failed provider attempt is
written to its own diagnostic file.
