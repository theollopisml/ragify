# CLAUDE.md — Collaboration Guidelines

## Workflow

- **Bloc by bloc**: one functional bloc at a time (e.g. indexing, RAG, frontend). Never large batches.
- **No anticipation**: don't create files or folders "just in case". Only create what the current bloc requires.
- **Validate before moving on**: always wait for user validation before proceeding to the next bloc.

## When planning

- Clearly segment the steps of the upcoming bloc.
- Justify every technical choice: why this tool, this lib, this approach over another.
- Give the big picture: where this bloc fits in the overall project.

## When executing

- Explain what each significant part of the code does.
- Be pedagogical: the user wants to understand, not just get working code.
- Comment non-obvious decisions directly in the code when relevant.

## Project

- **Ragify**: conversational AI assistant (RAG) for a Shopify plant container store.
- Stack: FastAPI + Qdrant + Claude API + Preact/vanilla JS
- Full spec in `doc/cahier-des-charges-rag-shopify.md`
