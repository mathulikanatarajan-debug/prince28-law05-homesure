
# HomeSure

Helps home buyers check an apartment project and builder agreement against RERA rules in Tamil Nadu.

**Status:** FastAPI backend with PostgreSQL-backed document routes.

## Who it's for

IT employee in Chennai (OMR) about to book a Rs 75 lakh apartment in an under-construction project.

## The problem

Many home buyers do not fully understand their rights before booking an apartment. They may not know whether a project is registered under RERA or whether the builder is following the required rules. Builder agreements can also contain confusing or one-sided conditions. HomeSure aims to help buyers identify these issues before making an important financial decision.

## Data sources

RERA Act 2016, Tamil Nadu RERA Rules 2017, TNRERA orders and circulars, project registration disclosures for 300 projects.

- https://www.rera.tn.gov.in/
- https://www.indiacode.nic.in/

Terms: Public law and orders. Cite section or order number.

## Hardest problem (my interview story)

Disclosures vs law: a builder's agreement must be checked clause by clause against RERA (advance limit, carpet area, delay interest), and delay compensation must be computed in code.

## Signature feature

Project health card: enter a registration number and see completion date, extensions, complaints and orders with citations.

## Target metric

Clause checks agree with a reviewer for 85%+ of clauses in 10 agreements.

## Setup

From the repository root:

```powershell
uv sync
copy .env.example .env
```

Keep `.env` local; do not commit database credentials. Start the API directly with:

```powershell
uv run poe dev
```

The local API listens on port 8000.

## Docker Compose

Build and start the API, PostgreSQL, and Redis:

```powershell
docker compose up --build -d
docker compose ps
```

Service ports:

- API: http://localhost:8001
- PostgreSQL: `localhost:5433`
- Redis: `localhost:6379`

Open the API documentation at http://localhost:8001/docs. Health is available at
http://localhost:8001/health and database readiness at
http://localhost:8001/ready.

Stop the containers while preserving the database volume:

```powershell
docker compose down
```

## Tests and quality checks

Run unit tests (no database required):

```powershell
uv run poe test
```

Integration tests and the coverage task require the Compose PostgreSQL service.
Each integration run provisions and removes a uniquely named temporary database:

```powershell
docker compose up -d db
uv run poe test-integration
uv run poe cov
```

Run lint and formatting checks with:

```powershell
uv run poe lint
```

## Run locally

### Prerequisites

- Python 3.12+
- uv
- Docker Desktop with Docker Compose

### Start the application

From the repository root:

```bash
docker compose up --build -d
```

The API is available at:

- Health: http://localhost:8001/health
- Readiness: http://localhost:8001/ready

### Run tests

Run unit tests:

```bash
uv run poe test
```

Run integration tests using the test database:

```bash
uv run poe test-integration
```

Run all tests with coverage:

```bash
uv run poe cov
```

Run lint checks:

```bash
uv run poe lint
```

### Stop the services

```bash
docker compose down
```

## Live deployment

**Live API:** https://homesure-api.onrender.com

**Health:** https://homesure-api.onrender.com/health

**Readiness:** https://homesure-api.onrender.com/ready

## GitHub Actions

![CI](https://github.com/mathulikanatarajan-debug/prince28-law05-homesure/actions/workflows/ci.yml/badge.svg?branch=main)
![CD](https://github.com/mathulikanatarajan-debug/prince28-law05-homesure/actions/workflows/cd.yml/badge.svg?branch=main)
