# Mistakes as a Reminder

Here is a log of the technical mistakes and errors encountered during this session. This serves as a reminder of what went wrong and how it was fixed.

## 1. FastAPI Validation Error Handling

* **The Mistake:** When implementing global exception handlers in `main.py`, I caught Pydantic's `ValidationError` to format 422 responses.
* **The Impact:** FastAPI actually raises `RequestValidationError` for bad incoming requests, not a raw Pydantic `ValidationError`. Because of this, invalid requests fell through to the generic 500 internal server error handler instead of returning a 422 status code.
* **The Fix:** Changed the exception handler to target `fastapi.exceptions.RequestValidationError`.

## 2. Reasoning Model Token Starvation

* **The Mistake:** Set `max_tokens=2048` for `moonshotai/Kimi-K2.5`.
* **The Impact:** Kimi-K2.5 is a reasoning model. It outputs a chain-of-thought before the final answer. The 2048 token limit was entirely consumed by the "thinking" phase, resulting in `finish_reason: length` and `content: None`.
* **The Fix:** Increased `LLM_MAX_TOKENS` strictly to `8192` to provide enough headroom for both reasoning and the final JSON generation.

## 3. Reasoning Content Field Extraction

* **The Mistake:** Standard OpenAI-compatible SDKs expect the final answer in `choices[0].message.content`. I didn't account for the `reasoning_content` field.
* **The Impact:** If the content was entirely placed in `reasoning_content` (or if `content` was None), the application raised an error instead of gracefully degrading or extracting the thinking.
* **The Fix:** Updated `llm_client.py` to check `msg.content`, and if empty, fallback to checking `msg.reasoning_content` or `msg.reasoning`.

## 4. Case-Sensitive Header Assertions in Tests

* **The Mistake:** In `test_app.py`, the CORS test asserted `"Access-Control-Allow-Origin" in response.headers`.
* **The Impact:** The test failed because Starlette/HTTPX normalizes all HTTP header keys to lowercase.
* **The Fix:** Updated the assertion to check against the lowercase key `"access-control-allow-origin"`.
