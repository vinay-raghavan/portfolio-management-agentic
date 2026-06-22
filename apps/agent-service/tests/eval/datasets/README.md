# Evaluation Datasets

This directory contains evaluation datasets for testing agent behavior.

The default dataset covers positive portfolio workflows and negative
safety workflows:

- Pre-market briefing with portfolio, watchlist, signal, research, and risk context.
- Momentum screener to draft paper strategy.
- Simulated backtest to pending paper order proposal, approval queue, and audit trail.
- Approval-gated simulated fill with paper-position accounting and audit evidence.
- Persisted strategy draft and backtest request history review.
- Recommendation explanation with factor evidence, history, risk gates, ledger context, citations, and paper-only next actions.
- Paper-trading report with redacted audit export.
- Risk review.
- Feature navigation.
- Refuse live market order.
- Refuse Fyers trading-token use.
- Refuse live strategy enablement.
- Refuse credential disclosure.

## Running Evaluations

From the repository root, first check whether model-backed evals can run without
printing credential values:

```bash
uv run python scripts/run_agent_evals.py preflight --json
```

When credentials are configured, run the default generate-and-grade loop:

```bash
uv run python scripts/run_agent_evals.py run --fail-on-skip
```

The wrapper is only a guard and command launcher. The official ADK eval path
remains `agents-cli eval generate` followed by `agents-cli eval grade`.

### Default Dataset
```bash
# Generate traces using the default dataset
agents-cli eval generate
agents-cli eval grade
```

### Custom Dataset
```bash
# Generate traces for a custom dataset
agents-cli eval generate --dataset tests/eval/datasets/custom-dataset.json --output custom_traces/
agents-cli eval grade --metrics general_quality --traces custom_traces/
```

## Dataset Format

Each dataset file follows the Gemini Enterprise Agent Platform Evaluation
dataset format. An eval case may use **either** of two shapes — both are
valid input to `agents-cli eval generate`:

**Shape A — single-prompt case:**

```json
{
  "eval_cases": [
    {
      "eval_case_id": "unique_case_id",
      "prompt": {
        "role": "user",
        "parts": [{"text": "User message"}]
      }
    }
  ]
}
```

**Shape B — continued-conversation case (the "N+1" pattern):**
The case carries prior turns in `agent_data` and the last turn ends with a
user message; `eval generate` appends the next agent response.

```json
{
  "eval_cases": [
    {
      "eval_case_id": "unique_case_id",
      "agent_data": {
        "turns": [
          {
            "turn_index": 0,
            "events": [
              {"author": "user",  "content": {"role": "user",  "parts": [{"text": "First user message"}]}},
              {"author": "agent", "content": {"role": "model", "parts": [{"text": "First agent reply"}]}},
              {"author": "user",  "content": {"role": "user",  "parts": [{"text": "Follow-up user message"}]}}
            ]
          }
        ]
      }
    }
  ]
}
```

## Key Fields

- `eval_cases`: Array of evaluation cases.
- `eval_case_id`: Unique identifier for the evaluation case (optional).
- `prompt`: A single user message — Shape A.
- `agent_data.turns`: Prior conversation turns ending with a user message — Shape B.

## Creating Custom Datasets

You can create custom datasets in two ways:

1. **By Hand**: Copy `basic-dataset.json` as a template and manually add evaluation cases.
2. **Synthesize**: Use the synthetic dataset generation command to generate conversation scenarios:
   ```bash
   agents-cli eval dataset synthesize --count 10
   ```

## Discovering Metrics

You can discover available out-of-the-box evaluation metrics by running:

```bash
agents-cli eval metric list
```

## Beyond Generate and Grade

Once you have a baseline, the eval surface has a few more commands worth knowing about:

- `agents-cli eval compare BASE CAND` — diff two grade-results files (regression check).
- `agents-cli eval analyze RESULTS` — cluster failure modes from a grade-results file.
- `agents-cli eval optimize` — auto-tune your agent's prompts using eval data.

See the [Evaluation Guide](https://google.github.io/agents-cli/guide/evaluation/) for the full surface and metric reference.
