.PHONY: install dev backend frontend test seed ranker

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

# runs both; Ctrl+C stops both
dev:
	$(MAKE) -j2 backend frontend

test:
	cd backend && python -m pytest -q
	cd frontend && npx tsc --noEmit

seed:
	cd backend && python scripts/seed_donors.py --donors 200

ranker:
	cd backend && python scripts/train_ranker.py --synthetic 3000
