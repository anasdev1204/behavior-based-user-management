# Introduction

This project explores a behavior-based user management system that runs as a background service on Windows. While active, it passively measures on-device interaction patterns (e.g., mouse drag velocity, inter-keystroke intervals) to learn a private, local profile of the primary user and flag anomalies that may indicate someone else is using the machine.

# Use Cases

-   **Personal security:** On a single-user machine, detect when a different person begins interacting and trigger alerts or lock the session.
-   **Parental controls & app gating:** Restrict or relax access to specific apps based on who appears to be using the device (e.g., tighten policies when behavior doesn’t match the primary user).
-   **Context-aware UX:** Optionally adapt settings (notifications, workspace) when confidence in the active user drops.

# Roadmap

-   [ ] **Scope, repo, environment, config, storage schema** — Define goals, set up repository, create environment and configuration, and design a local storage format for event streams and features.
-   [ ] **Input capture MVP (keyboard + mouse)** — Collect low-level keyboard and mouse events with minimal overhead.
-   [ ] **Convert raw events into stable features over rolling windows** — Compute features (e.g., dwell/flight times, path curvature, click cadence) with noise-robust statistics.
-   [ ] **Labeled data collection + EDA** — Gather self-labeled sessions, build train/validation splits, and perform exploratory analysis.
-   [ ] **Modeling & validation** — Train per-user anomaly/verification models; evaluate with ROC/PR, equal-error rate, and latency/CPU budget.
-   [ ] **Background service + real-time loop** — Package as a Windows service with a streaming feature pipeline and real-time inference.
-   [ ] **Validation in the wild, tuning, and hardening** — Run pilots on diverse hardware, tune thresholds, add fallbacks, and harden against spoofing and drift.

# Disclaimer

This project **does not** collect personally identifiable content or transmit data off-device. All processing stays local, focuses on behavioral timing/shape signals (not text or screen contents), and is designed to preserve user privacy.
