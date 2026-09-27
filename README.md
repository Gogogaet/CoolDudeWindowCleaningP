# Cool Dudes Window Cleaning — Python Field Desk

This is the Python/Streamlit business workspace for Cool Dudes Window Cleaning.

## Included

- Private email/password authentication with Supabase Auth
- Password reset and password change flows
- Persistent customer records
- Appointment bookings with customer links, date/time, service, amount, status, address, and notes
- Lead pipeline with source, status, estimated value, and next follow-up
- Territory map centered on Fremont, Nebraska
- Saved territory polygons
- Doorstep tracking with Not knocked / Said no / Maybe / Yes statuses
- Revenue, expenses, and simple net-before-tax reporting
- Monthly revenue goal
- JSON business-data export
- Row-level security so signed-in users only access their own business rows

## Run locally

    python -m pip install -r requirements.txt
    streamlit run app.py

## Supabase setup

1. Create a Supabase project.
2. Open the SQL Editor and run supabase/schema.sql.
3. Get the project URL and publishable key from the Supabase project settings.
4. Put them into Streamlit Secrets:

    SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
    SUPABASE_PUBLISHABLE_KEY = "YOUR-SUPABASE-PUBLISHABLE-KEY"

Use .streamlit/secrets.example.toml as the template.

Do not commit .streamlit/secrets.toml, passwords, API keys, or a Supabase secret/service-role key to this public repository.

## Streamlit Community Cloud

Create the app from this repository, use branch main, and use app.py as the entrypoint. Put the Supabase values in the app's Secrets/Advanced settings rather than the Git repository.

## Data model

Supabase stores profiles, customers, bookings, leads, doorsteps, territories, and expenses in separate tables. Row-level security uses the signed-in user's auth.uid() as the owner key.

## Current limitation

The business app is ready for a real backend, but external services such as SMS, online payment processing, transactional email, and automatic address geocoding are not connected yet.
