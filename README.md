# Credit Approval System

Minimal Django + DRF application for the credit approval assignment.

Quick start

1. Put the provided Excel files into a local `data/` folder at the repository root:

   - `data/customer_data.xlsx`
   - `data/loan_data.xlsx`

2. Build and run with docker-compose:

```bash
docker-compose build
docker-compose up
```

3. Run migrations (in a separate terminal):

```bash
docker-compose run --rm web python manage.py migrate
```

4. Trigger ingestion of the Excel files (this enqueues a Celery task):

```bash
docker-compose run --rm web python manage.py ingest_excel
```

APIs (base path `/api`):

- `POST /api/register` - register new customer
- `POST /api/check-eligibility` - check loan eligibility
- `POST /api/create-loan` - create a loan (if eligible)
- `GET /api/view-loan/<loan_id>` - view a loan
- `GET /api/view-loans/<customer_id>` - view loans for a customer

Notes

- Celery + Redis are used for background ingestion. The management command enqueues the task.
- If you don't have the original Excel files, create `data/` and add sample files.
