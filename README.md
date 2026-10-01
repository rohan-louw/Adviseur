# Adviseur

AI-assisted client communication triage and workflow management for financial advisers.

## Demo MVP features

- Gmail ingestion using an `ADVISEUR` label
- Duplicate Gmail-message prevention
- AI classification: category, urgency, human-review flag, reason, recommended action
- PostgreSQL persistence
- Client profiles and message history
- Primary and alternate email matching
- Manual message assignment
- Inbox status workflow and filters
- Browser dashboard with separate navigation views

## Local run

1. Create and activate a Python virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in local values.
4. Keep `credentials.json` and `token.json` local only; never commit them.
5. Run:
   `streamlit run app.py`

## Database

For a new PostgreSQL database, run `schema.sql` once before starting the app.

## Deployment

See `DEPLOYMENT.md`.
