🚀 **Just wrapped up an exciting AI Performance Engineering assignment!**

I built a **GitHub Repository Summarizer API** from scratch that takes any public repo URL and uses an LLM to generate a structured analysis of the project's purpose, technologies, and architecture.

This project was a fantastic deep dive into handling real-world constraints when working with LLMs:
🔹 **The Challenge:** How do you fit a massive repository with thousands of files into a single LLM prompt without hitting context limits?
🔹 **The Solution:** I designed a 6-tier prioritization parser that filters out noise (binaries, lock files, generated code) and ranks files by importance (READMEs > Manifests > Configs > Source Code). The system dynamically packs a ~200K character budget with the most crucial file tree and content data.

**Tech Stack used:**
⚡ **FastAPI** & **Pydantic** for async, robust, and strongly-typed API endpoints
🔍 **GitHub REST API** to recursively map repository file trees and fetch raw content
🧠 **Nebius Token Factory** using the `moonshotai/Kimi-K2.5` reasoning model. Leveraging a massive **256K context window**, this model handles complex Chain-of-Thought reasoning to distill complex repos into crisp, structured JSON outputs.

Built in collaboration with **Antigravity** and **Claude 3.7 Sonnet (Thinking Mode)**, demonstrating how powerful agentic workflows can accelerate engineering.

Check out the architecture and the code here: <https://github.com/Ashish-Soni08/ai-perf-eng-2026>

What’s your preferred strategy for feeding massive amounts of context into LLMs? Let me know below! 👇

# AI #MachineLearning #FastAPI #Python #LLM #NebiusAcademy #SoftwareEngineering #AgenticAI #Claude37
