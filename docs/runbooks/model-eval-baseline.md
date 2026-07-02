# Model Eval Baseline Runbook

## Goal

Capture the first model-backed baseline for the portfolio and paper-trading
agent, then turn failures into targeted instruction, tool-description, test, or
eval improvements.

## Preconditions

- `agents-cli` is installed and available on `PATH`.
- Model or judge credentials are configured in the shell that runs the command.
- No trading credentials are required or allowed for eval execution.
- Generated traces, grade results, and summaries remain under ignored
  `artifacts/` paths unless intentionally exported for review.

## Credential-Safe Preflight

Local credential values can live in the ignored root `.env` file:

```bash
GOOGLE_API_KEY=<your local token>
GOOGLE_CLOUD_PROJECT=<your project id>
# Optional if you use a service account key instead of gcloud ADC:
GOOGLE_APPLICATION_CREDENTIALS=<path to local service-account.json>
```

The eval runner loads `.env` by default before preflight and before launching
`agents-cli`. Shell environment values take precedence over `.env` values.
For `agents-cli` v0.5.0, `GOOGLE_API_KEY` alone is not enough: the Vertex eval
path also needs project context and Application Default Credentials. Use either
`gcloud auth application-default login` locally or set
`GOOGLE_APPLICATION_CREDENTIALS` to a local, ignored service-account file.

Run from the repository root:

```bash
uv run python scripts/run_agent_evals.py preflight --json
```

The preflight prints credential key names only. It does not print credential
values.

## Baseline Run

Run from the repository root in a credentialed environment:

```bash
uv run python scripts/run_agent_evals.py run --fail-on-skip
```

The wrapper executes:

```bash
agents-cli eval generate --dataset tests/eval/datasets/basic-dataset.json --output artifacts/evals/traces
agents-cli eval grade --config tests/eval/eval_config.yaml --traces artifacts/evals/traces --output artifacts/evals/grade-results
```

The default summary path is:

```text
apps/agent-service/artifacts/evals/baseline-summary.json
```

Use `--summary-output artifacts/evals/<name>.json` to keep multiple summaries
inside the app artifact directory.

The summary includes `submission_readiness`:

- `blocked`: preflight skipped because credentials, files, or binaries are missing.
- `failed`: `agents-cli eval generate` or `agents-cli eval grade` exited non-zero.
- `artifact_gap`: the baseline completed but no trace or grade-result artifacts were listed.
- `ready_for_triage`: traces and grade results exist; run deterministic triage next.
- `dry_run`: commands were validated but not executed.

## Manual GitHub Workflow

The manual Eval baseline workflow can run the same loop in GitHub Actions:

```text
.github/workflows/eval-baseline.yml
```

Dispatch it from the Actions tab with the desired provider. The workflow uses
repository secrets for model credentials, runs preflight, runs the baseline,
executes deterministic triage, and uploads `apps/agent-service/artifacts/evals`
as an artifact.

## Deterministic Triage

Run triage after a baseline, or before one to verify the output path:

```bash
uv run python scripts/run_agent_evals.py triage --json
```

The default triage report path is:

```text
apps/agent-service/artifacts/evals/triage-report.json
```

Triage is credential-free. It reads grade-result JSON and trace JSON artifacts,
then classifies failures into:

- `forbidden_action_policy`
- `provider_readiness`
- `paper_trading_workflow`
- `grounding_and_citations`
- `tool_trajectory`
- `response_quality`

The triage report also includes `submission_readiness`:

- `blocked`: no grade-result artifacts exist yet.
- `needs_hardening`: one or more eval failures were detected and should become
  instruction, tool-description, deterministic-test, or eval-regression work.
- `ready_for_capstone_submission`: grade results exist and deterministic triage
  found no failed metrics.

The default eval config runs three metrics:

- `portfolio_response_quality`: LLM judge for final response quality and rubric fit.
- `workflow_tool_trajectory_policy`: local deterministic code metric for required safe tool calls, allowed alternatives, and ordering.
- `forbidden_action_policy`: local deterministic code metric for forbidden tool calls and refusal behavior.

## Review Steps

1. Open the baseline summary and confirm `status` is `completed` and
   `submission_readiness.status` is `ready_for_triage`.
2. Review `command_results` for non-zero return codes.
3. Open the triage report and inspect `submission_readiness.status`, `summary`,
   `failures`, `tool_calls`, and `suggested_regression`.
4. Open the listed grade result JSON or HTML files from `grade_result_files`
   for judge rationales and score details.
5. Convert each confirmed failure into the smallest useful regression:
   deterministic pytest for policy/tool contracts, eval case for agent behavior,
   or tool-description/instruction change for trajectory quality.
6. Regenerate the capstone evidence manifest after triage:

   ```bash
   uv run python scripts/build_capstone_evidence.py
   ```

## Compare Future Runs

After a fix creates a new grade result JSON, compare it with the baseline:

```bash
agents-cli eval compare <baseline_results_json> <candidate_results_json>
```

The baseline summary includes the same compare template so future agents do not
need to infer the comparison path.

## Safety Notes

- Evals must never call or expose live-trading tools, broker trading tokens, or
  provider secret values.
- The deterministic metrics fail traces that call forbidden tools, call tools on
  forbidden prompts, skip required workflow tools, or violate approval/fill
  ordering.
- Treat a correct final answer from a dangerous tool trajectory as a failure.
