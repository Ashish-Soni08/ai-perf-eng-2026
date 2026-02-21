# Suggestions for AI to Improve

Reflecting on our session, here are areas where I (the AI) could have performed better or been more proactive:

## 1. Anticipating LLM Provider Quirks

When we switched to `moonshotai/Kimi-K2.5`, I treated it like a standard text-in/text-out model.

* **Improvement:** I should have proactively checked if the model was a reasoning model (which it was). I should have anticipated that reasoning models require significantly higher `max_tokens` (due to chain-of-thought) and that they output data in `reasoning_content` fields. Discovering this during the end-to-end test caused a delay.

## 2. Proactive Test Execution

While building the core logic, I often waited for your explicit permission to run `pytest`.

* **Improvement:** As an agentic AI with terminal access, I should proactively run unit tests in the background as I modify code, immediately catching regressions and fixing them before presenting the code to you.

## 3. Case-Insensitive HTTP Header Testing

During the FastAPI testing phase, a test failed because I asserted the presence of `Access-Control-Allow-Origin`. Starlette (FastAPI's underlying framework) normalizes header keys to lowercase (`access-control-allow-origin`).

* **Improvement:** I should default to case-insensitive header checks or use `response.headers.get("access-control-allow-origin")` when writing API tests to avoid trivial, easily preventable test failures.

## 4. More Granular Git Commits Earlier

I waited until the very end of the project to commit the code, resulting in an 8-commit batch.

* **Improvement:** I should have proactively suggested committing code at logical milestones (e.g., after the project scaffold was created, after the GitHub fetcher was tested, etc.) to maintain a cleaner, more incremental Git history.
