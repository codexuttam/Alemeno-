SHELL := /bin/bash
.PHONY: build up down migrate ingest ingest-sync start logs ps stop restart shell

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

migrate:
	docker compose exec web python manage.py migrate --noinput

ingest:
	docker compose exec web python manage.py ingest_excel

ingest-sync:
	# run ingestion synchronously inside Django (helpful for debugging)
	docker compose exec web python manage.py shell -c "from credit.tasks import ingest_excel_task; print(ingest_excel_task.run(None))"

start: build up migrate ingest

logs:
	docker compose logs --tail=200 -f

ps:
	docker compose ps

stop: down

restart: down up

shell:
	docker compose exec web python manage.py shell
