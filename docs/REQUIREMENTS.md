
# HomeSure – Project Requirements

## Functional Requirements

### FR1 – Project Registration Check
The system must accept a Tamil Nadu RERA registration number and retrieve the matching project details.

### FR2 – Project Completion Details
The system must display the original completion date and all available approved extensions.

### FR3 – Agreement Clause Analysis
The system must analyze at least 10 important clauses in a builder agreement and identify possible RERA compliance issues.

### FR4 – Advance Payment Validation
The system must flag advance payments exceeding 10% of the apartment cost before a registered agreement for sale.

### FR5 – Project Health Card
The system must generate a project health card containing registration status, completion details, complaints, regulatory orders, and source citations.

## Non-Functional Requirements

### NFR1 – Response Time
The API must respond to normal project lookup requests within 3 seconds under the defined test load.

### NFR2 – Accuracy
The clause analysis must achieve at least 85% agreement with a human reviewer across 10 test agreements.

### NFR3 – Security
The system must validate uploaded files and limit PDF uploads to 10 MB.

### NFR4 – Reliability
The API must maintain at least 99% availability during the defined monitoring period.

### NFR5 – Maintainability
The project must use Python 3.12, type hints, Ruff linting, and automated pytest tests.
