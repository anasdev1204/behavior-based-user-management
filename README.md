# Introduction

This project explores a behavior-based user management system that runs as a background service on Windows. While active, it passively measures on-device interaction patterns (e.g., mouse drag velocity, inter-keystroke intervals) to learn a private, local profile of the primary user and flag anomalies that may indicate someone else is using the machine.

# Use Cases

-   **Personal security:** On a single-user machine, detect when a different person begins interacting and trigger alerts or lock the session.
-   **Parental controls & app gating:** Restrict or relax access to specific apps based on who appears to be using the device (e.g., tighten policies when behavior doesn’t match the primary user).
-   **Context-aware UX:** Optionally adapt settings (notifications, workspace) when confidence in the active user drops.

# How to

Currently, the program only captures the data from the user input and does not perform any other steps on it.

1. Clone the repository
``` bash
    git clone https://github.com/anasdev1204/behavior-based-user-management.git 
    cd behavior-based-user-management
```

2. Create a virtual environment and install the requirement from the file
```bash
    python -m venv .venv
    ./.venv/Scripts/activate # On MacOs: source ./venv/bin/activate
    pip install -r requirements.txt
```

3. Bootstrap the program
```bash
    python -m src.service.bootstrap --init
```

4. Start the capture
```bash
    python -m src.service.capture --init
```
All captured data will be stored in the sqlite db located in `db_path` (config.yaml).

# Roadmap

-   [x] **Scope, repo, environment, config, storage schema** — Define goals, set up repository, create environment and configuration, and design a local storage format for event streams and features.
-   [x] **Input capture MVP (keyboard + mouse)** — Collect low-level keyboard and mouse events with minimal overhead.
-   [ ] **Convert raw events into stable features over rolling windows** — Compute features (e.g., dwell/flight times, path curvature, click cadence) with noise-robust statistics.
-   [ ] **Labeled data collection + EDA** — Gather self-labeled sessions, build train/validation splits, and perform exploratory analysis.
-   [ ] **Modeling & validation** — Train per-user anomaly/verification models; evaluate with ROC/PR, equal-error rate, and latency/CPU budget.
-   [ ] **Background service + real-time loop** — Package as a Windows service with a streaming feature pipeline and real-time inference.
-   [ ] **Validation in the wild, tuning, and hardening** — Run pilots on diverse hardware, tune thresholds, add fallbacks, and harden against spoofing and drift.

# Disclaimer

This project **does not** collect personally identifiable content or transmit data off-device. All processing stays local, focuses on behavioral timing/shape signals (not text or screen contents), and is designed to preserve user privacy.
*NOTE*: The program currently saves the keys pressed by the user but only for testing purposes. This feature will not be used in the final version of the program