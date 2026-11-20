.PHONY: help install test test-integration cov lint format up down logs

help:
    @echo "HomeSure development commands"

install:
    uv sync --all-groups

test:
    uv run poe test

test-integration:
    uv run poe test-integration

cov:
    uv run poe cov

lint:
    uv run poe lint

format:
    uv run ruff format .

up:
    docker compose up --build -d

down:
    docker compose down

logs:
    docker compose logs -f
