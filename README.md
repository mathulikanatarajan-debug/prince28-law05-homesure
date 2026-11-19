
# HomeSure

Helps home buyers check an apartment project and builder agreement against RERA rules in Tamil Nadu.

**Status:** Day 1 foundation (FastAPI skeleton, quality gates). Live URL from Day 5.

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

## Run it locally

```bash
uv sync
```

Windows:

```powershell
copy .env.example .env
```

Run the server:

```bash
uv run uvicorn homesure.api.main:create_app --factory --reload
```

Then open http://localhost:8000/docs

## Checks

```bash
uv run pytest
uv run ruff check .
```
