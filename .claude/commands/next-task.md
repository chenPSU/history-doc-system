---
description: Pick up the next unchecked task in TASKS.md and work on it
---
Read CLAUDE.md, TASKS.md and docs/decisions.md. Find the first unchecked task whose earlier tasks are done.
If it depends on an OPEN decision, ask the owner (in Thai) first, with your recommendation and the options.
Otherwise state the plan in 3-5 lines (in Thai), build it with tests, run `pytest -q`, check the acceptance criteria, then tick the box in TASKS.md and summarise what changed (in Thai).
