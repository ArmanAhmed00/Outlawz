# Agent failure log

**How failures are found:** `scripts/eval/agent_eval_runner.py --rag` → read the trace of every
failed run in `eval/results/agent_eval_results.json` → note the **first** thing that went wrong (an early
wrong turn causes most of what follows) → group into categories → fix the biggest category first.

## Categories (fill the counts after each eval run)

| Category | Description | Count | Fix | Fixed? |
|---|---|:---:|---|:---:|
| Wrong tool | e.g. search_corpus instead of get_article for "Article 5" | | | |
| Redundant search | same information searched twice | | | |
| No recovery | gave up after one empty search, or invented an answer | | | |
| Math in its head | computed without the calculator | | | |
| Over-searching out of scope | searched again and again on an off-topic question | | | |
| Unwanted action | proposed send_message without being asked | | | |

## Failed runs

| Question | Scenario | First thing that went wrong | Category |
|---|---|---|---|
| | | | |

## Regression check

| Change | Priority questions OK | Agent questions OK | Broke |
|---|:---:|:---:|---|
| | | | |
