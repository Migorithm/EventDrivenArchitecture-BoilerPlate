include .env
EXPORT = export PYTHONPATH=$(PWD)


migration:
	$(EXPORT) && pipenv run alembic revision --autogenerate -m "initial tables"

upgrade:
	$(EXPORT) && pipenv run alembic upgrade head

downgrade:
	$(EXPORT) && pipenv run alembic downgrade -1

shell:
	$(EXPORT) && pipenv run python

checks:
	$(EXPORT) && pipenv run sh scripts/checks.sh

dev-db-sync:
	echo $(DEV_DB_HOST)
	echo $(DEV_DB_PW)
	echo $(POSTGRES_DB)
	PGPASSWORD=$(DEV_DB_PW) pg_dump -C -h $(DEV_DB_HOST) -U harmony harmony_transaction | psql -h localhost -U $(POSTGRES_USER) $(POSTGRES_DB)

stage-db-sync:
	PGPASSWORD=$(STAGE_DB_PW) pg_dump -C -h $(STAGE_DB_HOST) -U flanb harmony_transaction | psql -h localhost -U $(STAGE_POSTGRES_USER) $(STAGE_POSTGRES_DB)

prod-db-sync:
	PGPASSWORD=$(PROD_POSTGRES_DB_PW) pg_dump -C -h $(PROD_POSTGRES_HOST) -U flanb harmony_transaction | psql -h localhost -U $(PROD_POSTGRES_USER) $(PROD_POSTGRES_DB)
local-db-reset:
	psql -h localhost -p $(POSTGRES_PORT) -U $(POSTGRES_USER) $(POSTGRES_DB) -t -c "select 'drop table \"' || tablename || '\" cascade;' from pg_tables where schemaname='public'" | psql -h localhost -p $(POSTGRES_PORT) -U $(POSTGRES_USER) $(POSTGRES_DB)
