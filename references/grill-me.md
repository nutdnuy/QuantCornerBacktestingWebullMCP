# grill-me interview contract

This is an original, self-contained interview guide, not a redistributed third-party skill.
Prefer the user's installed `mattpocock-grill-me` / `grill-me`. When unavailable, disclose that you are using the bundled equivalent protocol.

Ask **one question per turn**. Give a recommended answer with its reason; it is a proposal, not consent. Start with the most consequential unresolved dependency. Resolve that branch before moving on. Do not re-ask provided answers. If an answer is discoverable from the user's files or tools, inspect it instead.

First-run question if the host is not connected: “Which AI client are you using, and is your licensed Webull MCP connection already enabled?” Recommend using the host's existing authenticated connection. Do not ask for secrets in chat.

First research question: “What behavior do you want to understand, and what mechanism do you expect to cause it?” Suggest a narrow, falsifiable question, not maximizing backtest performance.

Next unresolved branches: exact instruments (all long-only); time window/holdout; trading rule, next-open execution and warmup; initial cash and verified lot sizes; fees/slippage and corporate actions; baseline/benchmark; sensitivity checks; output language/sharing. Costs cannot be silently zero. If the user says “use reasonable defaults”, name them as assumptions and preserve the delegated authorization.

Finish with a concise plan, explicit unknowns and the next experiment. Stop interviewing once the task is sufficiently specified. A new idea after seeing results is a new hypothesis version, not retrospective confirmation.
