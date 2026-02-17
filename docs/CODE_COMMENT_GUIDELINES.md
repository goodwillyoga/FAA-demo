# Code Comment Guidelines

These rules define how comments should be written in this repository.

## Purpose
Comments should help readers understand intent and tradeoffs quickly, without reading every line of code.

## What to Comment
- Non-obvious formulas or thresholds and the rationale behind them.
- Business or domain assumptions that affect behavior.
- Safety/quality constraints and fallback behavior.
- Cross-component expectations (for example schema contracts or API assumptions).

## What Not to Comment
- Obvious statements that repeat the code.
- Long narrative blocks that reduce readability.
- Temporary implementation notes that do not explain behavior.

## Style
- Use short, direct, user-facing language.
- Explain both `what` and `why` when logic is non-trivial.
- Keep comments close to the code they explain.
- Prefer one to three lines for most comments.
- Avoid first-person phrasing in code comments.

## Example Pattern
- Good: "Weight sustained wind more than gust spikes because baseline wind drives persistent drift risk."
- Avoid: "Set value to variable." 
