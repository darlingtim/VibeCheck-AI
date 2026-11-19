# VibeCheck-AI
Festival Feedback Detective | evidence-grounded AI review intelligence CLI

## Runtime logs

LLM review processing writes success and failure events to
`logs/llm_service.log`. Every failed API attempt also gets its own diagnostic
file in `logs/errors/`, including the error type, message, and traceback. Log
files are local runtime data and are ignored by Git.
