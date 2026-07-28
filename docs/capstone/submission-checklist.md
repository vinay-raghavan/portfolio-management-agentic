# Kaggle Submission Checklist

## Repository Package

- [x] TradePilot Sentinel product name and positioning.
- [x] Architecture source of truth.
- [x] 16:9 system architecture diagram.
- [x] 16:9 decision-intelligence diagram.
- [x] 16:9 agentic workflow diagram.
- [x] 16:9 safety and action-tier diagram.
- [x] 16:9 evaluation and deployability diagram.
- [x] Cover image.
- [x] Presentation deck with speaker notes.
- [x] Selected public-safe product screenshots.
- [x] Public-safe eval summary.
- [x] Kaggle writeup under 2,500 words.
- [x] Video storyboard for a sub-5-minute recording.
- [x] Docker and Podman setup instructions.
- [x] Deterministic CI and credential-gated eval workflow.

## Final Verification

- [x] Run root contract and security tests.
- [x] Run agent-service unit and integration tests.
- [x] Run web typecheck and production build.
- [x] Validate Docker or Podman Compose configuration.
- [x] Run the deterministic eval triage.
- [x] Regenerate the capstone evidence manifest.
- [x] Scan the tracked tree and Git history for secrets, local paths, private
  references, and real account data.
- [x] Verify every link in the public README and capstone package.
- [ ] Confirm the final `develop` CI run is green.

## Video And Media Gallery

- [ ] Record the agentic pre-market prompt and multi-tool response.
- [ ] Record the screener, recommendation, strategy, and simulated backtest.
- [ ] Record proposal, human approval, simulated fill, and report in order.
- [ ] Show the safety boundary and live-trading refusal.
- [ ] Show eval and container evidence.
- [ ] Edit the video to 5 minutes or less.
- [ ] Upload the video to YouTube.
- [ ] Upload the cover, diagrams, and selected screenshots to the Kaggle Media
  Gallery.
- [ ] Attach the YouTube video in the Media Gallery.

## Public Project Link

- [ ] Merge the submission package PR into `develop`.
- [ ] Create the release merge from `develop` into locked `main`.
- [ ] Confirm `main` contains the final docs, media, and setup instructions.
- [ ] Update the GitHub repository description to TradePilot Sentinel.
- [ ] Make the repository public only after the secret and history scan passes.
- [ ] Use the public GitHub URL as the Kaggle project link.

## Kaggle Form

- [ ] Select the Concierge Agents track.
- [ ] Create the Kaggle Writeup and paste `writeup.md`.
- [ ] Confirm the writeup remains below 2,500 words after Kaggle formatting.
- [ ] Attach the public project link.
- [ ] Attach the Media Gallery and required public YouTube video.
- [ ] Verify the submission visibly demonstrates at least three course concepts.
- [ ] Preview the final submission from a signed-out browser session.
- [ ] Submit before July 6, 2026 at 11:59 PM Pacific Time.

## Course Concept Evidence Map

| Concept | Code evidence | Video or media evidence |
| --- | --- | --- |
| Agent / multi-agent system using ADK | `apps/agent-service/app/agent.py` | Agent prompt, multi-tool response, architecture slide |
| MCP server | `apps/mcp-server/portfolio_mcp/server.py` | Architecture and safety slides |
| Security features | `packages/policy`, MCP catalog tests | Approval sequence, refusal, safety slide |
| Deployability | `docker-compose.yml`, Dockerfiles, GitHub Actions | Evaluation and deployability slide |
| Agent skills and Agents CLI | skills, eval datasets, eval runner | Eval results and development explanation |

Do not claim Antigravity evidence unless the final video actually demonstrates
work performed in Antigravity.
