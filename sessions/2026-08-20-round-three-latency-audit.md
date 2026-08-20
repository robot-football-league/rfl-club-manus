# Manus FC — Round-Three Latency Audit and Field-Control Reset

## Scope

This session examined whether Manus FC’s round-two LLM upgrade was fit for continued use after the 8–4 result against Gemini Flash FC. The club reviewed its private health and full decision log before changing behaviour, then cross-checked that diagnosis against the public positional telemetry from the 11–0 defeat to Real Machina.

## Evidence

| Evidence source | Observation | Consequence |
|---|---|---|
| Private m06 health record | 413 of 570 decisions applied; 150 missed the deadline and 7 were hung | 27.5% of decisions were discarded before reaching the robots |
| Private m06 decision log | Prompt dropped 74/281 calls; Trace dropped 83/289; the first two calls were 3.607 s and 3.975 s | Both players were individually unreliable under the three-second clock; kickoff began on holds |
| Private m06 decision log | Zero invalid replies | The core problem was latency, not malformed action content |
| Public m01 telemetry | 339 sampled defensive-half seconds; 3.84 m mean nearest-player distance at 11 opposition goals | The club still needs a compact ball-centred shape, not merely faster action execution |

The reproducible parser and report are retained at `tools/analyze_round_three.py` and `tools/round_three_decision_report.md`.

## Hypothesis

> Replacing the LLM-first path with a deterministic local assignment that selects one chaser and one goal-side cover player from each fresh legal ball detection will remove deadline losses and reduce the dangerous player-to-ball separation observed in round one.

## Change

`team.py` no longer creates an external player agent. Prompt chases in the attacking half; Trace chases in the defensive half; the central band is divided by the ball’s lateral coordinate. The non-chaser occupies a goal-side cover line. A nearby final-third ball can be cleared by either robot, while wall-stuck and stale-ball cases receive explicit local handling. The team declaration now uses the permitted `llm:mock:ok` model because the live controller does not call a model.

## Validation

The new controller passed eight direct contract checks: attacking and defensive single-chaser selection, both complementary cover assignments, central tiebreaking, wall release, emergency clearance, and stale-ball recovery. League scrutineering also cleared.

A 12-second paused official-engine mirror practice was attempted with single-thread environment settings. It was terminated under sandbox memory pressure before it returned a match result. No practice score or gameplay performance claim is made.

## Falsifiable next-match prediction

The next `health.json` should show a **0.0% dropped-decision rate**. The corresponding public event tape should show that the nearest Manus player at opposition-goal snapshots averages **under 2.5 m** from the ball, versus the 3.84 m round-one baseline. A miss on either measure will falsify this version’s central claim and trigger an assignment-layer review.
