Context:

I need storage for normalized log events. It needs to support fast analytical queries, compression, multi-query engine compatibility, and runs on 16GB NUC without a dedicated database daemon.

Options included:
	• JSON (Written natively in FluentBit)
	• PostGresSQL - a traditional database
	• ORC - columnar format


Decision: Parquet

Why not JSON: 
	• Row Oriented
	• Every query scans every field of every row, even if only two fields are needed
		○ This does not scale
	• No built-in compression 
	• No schema enforcement 

Why not PostgreSQL:
	• Optimized for transactional workloads
		○ Inserts, updates, deletes, point lookups 
		○ Opposite of Security Analytics
			§ Append-only writes and large analytical reads across millions of rows
	• PostgreSQL could work but it requires a running daemon, consumes significant RAM and doesn't provide the engine portability that Parquet does

Why not ORC:
	•  It's columnar but is primarily for the Hive/Hadoop ecosystem 
	• Parquet has broader support
		○ DuckDB, Spark, Pandas, DataBricks, Snowflake and ClickHouse all read it natively
		

Positive Consequences:
	• DuckDB reads Parquet directly with no ingestion gap
	• Same files will work with PySpark for scale processing
	• Columnar storage means queries that filter on a single field only read that column.
		○ Performance advantage for detectuib queries that filter on process name, username, IP addresses, etc…
		○ Built-in compression reduces storage versus JSON

Negative Consequences:
	• Parquet files are not human readable
	• Cat-ing a Parquet file is not possible
		○ DuckDB or a Parquet viewer is required
	• Appending to an existing Parquet file requires rewriting it
		○ Fluent Bit writers new files rather than appending
			§ Accumulation of small files over time
			§ Small file accumulation will require management

Production Scale Consideration:
	• This is the exact pattern used at the Microsoft Sentinel Scale
		○ Azure Data Lake Storage Gen2 stores Parquet files
		○ Azure Data Explorer (kusto) queries them
	• Netflix runs something similar
		○ PySpark reads the same Parquet format
	• This home lab, from an arcitecture standpoint is identical to production
	• The difference is the execution engine and the file management layer, not the storage format
	
<img width="1173" height="2275" alt="image" src="https://github.com/user-attachments/assets/23e87035-3b0e-4d72-bca7-cfee9bf555e3" />
