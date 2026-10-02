# Distraction-Based Reaction Game

A Tkinter-based Human–Computer Interaction laboratory project that measures reaction time under two visual-distraction conditions.

> **ITEC80D – Human Computer Interaction | Laboratory Exercise No. 2**

## Screenshots

### Main Interface

![Distraction-Based Reaction Game - Main Interface](assets/screenshots/Main Interface.png)

## Overview

The **Distraction-Based Reaction Game** asks a participant to click a centre target as soon as it turns green and displays **“CLICK NOW!”**.

The experiment contains two conditions:

| Condition | Description |
| --- | --- |
| **A — Low-distraction** | Plain interface with no distractor objects |
| **B — High-distraction** | Moving/changing shapes and decoy text surrounding the same target |

Both conditions use the same task, target position, waiting range, response timeout, feedback timing, and number of trials. The condition order can be set to **A then B** or **B then A** for counterbalancing.

## Features

- 10 trials per condition (20 trials per participant session)
- Random pre-stimulus delay between **1.5 and 4.0 seconds**
- **2-second** response timeout
- Early-click, distractor-click, delayed-response, and stray-click tracking
- Automatic reaction-time measurement using `time.perf_counter()`
- Score system with faster correct responses receiving more points
- Personal-best reaction-time feedback
- Optional sound on errors
- Live trial progress and session status
- Per-trial interaction log
- Summary statistics for both conditions
- Automatic CSV saving
- Manual CSV export for the current session
- Incomplete-session saving when Reset or Exit interrupts a running session

## Interface

The UI was reorganized for a cleaner public-repository presentation while keeping the original interaction flow intact:

- Clear participant-information card
- Dedicated game/reaction area
- Session progress strip
- Session interaction log
- Results/statistics panel
- Consistent typography, spacing, borders, buttons, and status feedback

## Experimental Rules

The application records every trial as a dictionary in `self.results`.

A correct trial is a click on the target after it turns green.

An incorrect trial can be:

- **Early click** — the participant clicks before the target turns green.
- **Distractor click** — the participant clicks a distractor after the target turns green.
- **Delayed response** — the participant does not click the target within the response window.
- **Stray click** — a background click is recorded and the trial continues.

Distractors never use green, so the green target remains the intended stimulus.

## Data Collected

Each trial is stored with the following fields:

```text
participant_id
age_group
experience_level
session
condition_order
condition
distraction_level
trial
task
stimulus_type
wait_ms
expected_response
actual_response
reaction_time_ms
correct
early_click
error_type
error_count
stray_clicks
timestamp
session_status
```

### Storage

By default, completed and incomplete session records are appended to:

```text
raw_interaction_data/raw_data.csv
```

The application creates the `raw_interaction_data` folder automatically when data are first saved.

The repository `.gitignore` excludes the generated raw CSV data so participant interaction data are not accidentally committed to a public GitHub repository.

## Requirements

- Python 3.x
- Tkinter

Tkinter is included with most standard Python installations. On some Linux distributions, the Tkinter system package may need to be installed separately.

No third-party Python packages are required.

## How to Run

Clone the repository, open a terminal in the project folder, and run:

```bash
python DistractionReactionGame.py
```

On systems where `python` points to Python 2 or is not available, use:

```bash
python3 DistractionReactionGame.py
```

## How to Use

1. Enter an anonymous participant code such as `P01`.
2. Select the participant's age group.
3. Select the participant's experience level.
4. Choose the session number.
5. Choose the condition order.
6. Click **Start Game**.
7. Wait for the centre box to turn green.
8. Click the green target as quickly as possible.
9. Continue until both conditions are complete.
10. Review the recorded data and summary results.
11. Use **Export CSV** when a separate copy of the current session is needed.

## Project Structure

```text
DistractionReactionGame/
├── DistractionReactionGame.py
├── README.md
├── .gitignore
└── raw_interaction_data/
    └── raw_data.csv        # generated at runtime; ignored by Git
```

## Data and Privacy Note

Use anonymous participant codes only. Do **not** place names or other unnecessary personally identifying information in the participant fields.

Because this repository is intended for public GitHub use, generated participant data should remain local unless you have explicit permission and an appropriate data-management plan for publishing them.

## Enhancements

The original project identified these personal enhancements beyond the laboratory guide:

- **Score system** — faster correct reactions earn more points.
- **Personal-best feedback** — the application announces a new fastest reaction time during the session.
- **Sound toggle** — optional system sound feedback can be enabled for errors.

## Academic Context

This project was developed for:

**ITEC80D — Human Computer Interaction**  
**Laboratory Exercise No. 2**

Developer placeholder from the original project:

**REMULLA, CHRISTIAN**

## Notes for GitHub

The main application file is intentionally kept as a single Python script so it remains easy to submit, run, inspect, and demonstrate in a laboratory setting. The code is organized into configuration, utility functions, UI construction, game flow, input handling, data recording, results, and application entry-point sections.
