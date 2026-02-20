.PHONY: build up test


build:
docker-compose build


up:
docker-compose up


test:
pytest -q