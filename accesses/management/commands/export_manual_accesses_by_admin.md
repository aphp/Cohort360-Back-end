# export_manual_accesses_by_admin (#3757)

Exports to CSV the accounts an admin created or modified (the account itself or one of its Manual accesses), with their current and future Manual accesses.

## Run

On the back-end pod:

```bash
python manage.py export_manual_accesses_by_admin --username <admin APH id> --output /tmp/export.csv
```

Then copy the file out with `kubectl cp <pod>:/tmp/export.csv ./export.csv`.

## Output

`;`-separated CSV, UTF-8 with BOM (opens in Excel). One row per access; an account with no current access gets one row with empty access columns. The last column says whether the admin created or modified the access.

## Limits

- Only accounts with a Manual profile.
- Expired, deleted, ORBIS and inactive-profile accesses are excluded.
- Account `created_by`/`updated_by` only exist since 3.29.1; older accounts show up only through their accesses.
- Only the last modifier is stored.
