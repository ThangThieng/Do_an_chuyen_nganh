# Lệnh tắt cho Linux/macOS (Windows: scripts/lms.ps1) – SPEC 6.4
.PHONY: setup ingest etl-backfill users api web moodle-stub etl messaging-check test e2e bench docker

setup:
	python -m pip install -r requirements.txt
	cd frontend && npm install
	python -m database.migrate up --target analytics
	python -m database.migrate up --target moodle

# Nạp CSV Moodle thật: make ingest REAL_DATA_DIR=/đường/dẫn/Data_11-2026
ingest:
	python -m ingest.run --data-dir "$(REAL_DATA_DIR)" --batch 2026-11

etl-backfill:
	python -m etl.jobs.backfill --from 2026-09-13

users:
	python -m backend.app.cli sync-users

api:
	python -m uvicorn backend.app.main:app --port 8000

web:
	cd frontend && npm run dev

moodle-stub:
	python -m tools.moodle_ws_stub

etl:
	python -m etl.scheduler

messaging-check:
	python -m backend.app.cli messaging-check

test:
	python -m pytest -q
	cd frontend && npm test

e2e:
	cd frontend && npx playwright test

bench:
	python -m perf.explain_queries --dataset x1

docker:
	docker compose --env-file docker/.env up --build -d
