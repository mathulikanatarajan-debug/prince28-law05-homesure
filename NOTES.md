\# HomeSure — Database and Query Plan Notes



\## 1. Database migrations



Created the documents and pages tables using Alembic migrations.



\- `5a3485f70471`: Create documents and pages.

\- `59888dbfdaf5`: Add GIN index on metadata.

\- Verified migration upgrade and downgrade successfully.



\## 2. Database loader



Tested the idempotent loader with 20 sample records.



First run:

\- Inserted: 20

\- Updated: 0

\- Unchanged: 0



Second run:

\- Inserted: 0

\- Updated: 0

\- Unchanged: 20



After editing one record:

\- Inserted: 0

\- Updated: 1

\- Unchanged: 19



This confirms that the loader inserts new records, updates changed records, and skips unchanged records.



\## 3. EXPLAIN ANALYZE



Query tested:



```sql

SELECT id, title

FROM documents

WHERE metadata @> CAST(:f AS jsonb);

```



Metadata filter:



`project\_reg\_no = TN/35/Building/0185/2025`



\### Normal planner choice



PostgreSQL selected:



`Seq Scan on documents`



It checked all 20 rows. For a small table, a sequential scan can be cheaper than using an index.



\### Demonstrating GIN index usage



After executing:



```sql

SET enable\_seqscan = off;

```



PostgreSQL selected:



\- `Bitmap Heap Scan on documents`

\- `Bitmap Index Scan on ix\_documents\_metadata\_gin`



This confirms that the GIN index supports the JSONB containment operator `@>`.



\## 4. Why does PostgreSQL choose Seq Scan?



The query planner estimates the cost of different execution plans. Since this table contains only 20 records, reading the whole table can be cheaper than accessing the index and then fetching matching rows.



As the table grows, and when the filter is selective enough, PostgreSQL may choose the GIN index automatically.



Disabling sequential scans was only a demonstration to prove that the index can be used. It is not a recommended production setting.



\## 5. Conclusion



\- Alembic migrations were tested.

\- The database loader was verified as idempotent.

\- API tests and lint checks passed.

\- The GIN index was verified using EXPLAIN ANALYZE.
