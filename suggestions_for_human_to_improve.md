# Suggestions for Human to Improve Prompting

Based on our session building the GitHub Repository Summarizer API, here are some tips on how you can improve your prompting to get faster, more autonomous results:

## 1. When to Give the AI Autonomy ("Roll With It")

In our session, you explicitly asked to work incrementally and get feedback after each task. While this is great for control, it often creates unnecessary bottlenecks.

**Better Approach:** Give conditional autonomy.

* *Prompt:* "Implement the GitHub API fetcher and the content filtering logic. Write tests for both, run them until they pass, and only ask for my review once the tests are green."
* *Why:* This allows the AI to get into a flow state, write code, hit an error, debug it, and fix it without stopping to ask you for permission at each micro-step.

## 2. Test Execution

You frequently had to prompt me to run tests or verify behavior. The AI can execute terminal commands natively.

**Better Approach:** Bake test execution into the feature request.

* *Prompt:* "Add custom exception handlers for FastAPI. Once implemented, run the `pytest` suite and ensure no existing tests are broken. If they are, fix them before stopping."
* *Why:* It turns a multi-step conversation ("Write code" -> "Here it is" -> "Now test it" -> "Here are the results") into a single prompt.

## 3. Dealing with Infrastructure and APIs

When we ran into the Nebius Token Factory URL issue (`eu-west1`), I had to wait for you to point it out.

**Better Approach:** Provide constraints and copy-pasted docs upfront.

* *Prompt:* "We are using Nebius Token Factory. Here is the base URL: `https://api.tokenfactory.eu-west1.nebius.com/v1/`. Use `moonshotai/Kimi-K2.5`. Note that this is a reasoning model, so account for that in the response parsing."
* *Why:* Giving the AI exact endpoint strings or quick copy-pastes from documentation prevents trial-and-error debugging.

## 4. End-to-End Workflows

Instead of asking "Can you commit each file...", you can define the exact Git workflow you prefer at the start of the session.

**Better Approach:** "Set as a rule for this session: whenever a major feature is complete and tests pass, automatically group the files logically and commit them using Conventional Commits, then push."
