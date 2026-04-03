Context: This project requires a query engine that reads Parquet natively and supports SQL and KQL-esque analytics.  It needs to run on 16GB RAM without separate server process and is capable of being embedded in Python.  Candidates were PostgreSQL, SQLite, ClickHouse, and DuckDB

Why not SQLite:
	• Row-oriented and not columnar. 
	• Same issue as PostgreSQL for analytical workloads
	• Does not support Parquet natively

Why not PostgreSQL:
	• Requires a running server process consuming upwards of 500MB minimum.
	• Doesn't read Parquet natively
		○ Requires loading data into PostgreSQL tables
			§ Double storage and ingestion step
		○ Not for the analytics layer

Why not ClickHouse:
	• This is the correct engine at scale 
		○ Prospectively on Phase 6 upgrade path
		○ Requires a server daemon
		○ Consumes more RAM
		○ More operational complexity than DuckDB for a single-node home lab

Why DuckDB: 
	•  Embedded
		○ No daemon
		○ No server
		○ No configuration
	• Reads Parquet directly from disk with predicate pushdown
	• Detection Runner can query Parquet files with no additional infrastructure
	• Supports full SQL plus window functions, lateral joins, and ASOF joins that are directly useful for detection correlation
		○ Around 2GB RAM for most workloads 

Positive Consequences:
	• Zero operational overhead
		○ No service to monitor, restart, or tune
	• Detection Runner is a Python script
		○ Not a microservice talking to a database.
	• Full SQL expressions for detection queries

Negative Consequences:
	• DuckDB is embedded
		○ Can only be accessed by one process at a time with write access
		○ SIEM UI and Detection Runner cannot both write simultaneously without coordination
	• Read-only access can be shared but writes need to be serialized
	• No built-in replication
	• No high availability
		○ Single point of failure at the storage layer

Production Scale Consideration:
	• At scale DuckDB is replaced by the following:
		○ ADX for Microsoft workloads
		○ Apache Spark for Netflix workloads
		○ Both use the same Parquet storage layer
	• Migration path is:
		○ Swap query engine
		○ Keep the Parquet files
		○ Rewrite queries in the target language
			§ KQL for ADX
			§ Spark SQL for Databricks
	• Detection logic expressed in Sigma is portable to any target via sigma-cli 
			
