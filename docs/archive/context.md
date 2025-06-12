# Project Name: Rally

## Overview
Rally is a full-stack web application designed to help paddle, pickleball, and tennis teams manage lineups, player availability, performance insights, and league results.

The stack includes:
- Frontend: HTML, JavaScript, React (modular/component-based)
- Backend: Python (Flask)
- Hosting/CI: Railway
- Data: Stored locally (JSON), or via server memory

## Architecture Notes
- Each team or player has status tracking (bye/injured/assigned).
- Performance analytics includes win %, PTI, court-level detail.
- Messaging and auto-reminders are built in.
- Mobile-first design and potential PWA use case.
- Components are modular — avoid monolithic views or tangled logic.

## Coding Style
- Python follows PEP8 and uses docstrings.
- React follows functional component standards and hooks.
- JS follows Airbnb style guide + Prettier.
- Inline documentation is prioritized across the stack.

## AI Guidance
Cursor should:
- Respect modularity and avoid large rewrites.
- Explain reasoning before changes.
- Suggest improvements or refactoring when patterns are detected.
- Never assume DB or ORM unless explicitly noted.
