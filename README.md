Akogun is a modern detection engineering platform built as a security data detection layer on top of it.  It is named after the Yoruba term meaning "One who repels war."

Akogun is a custom-built SIEM and threat hunting platform, utilized as a learning platform and portfolio builder.  It runs on a Intel NUC using DuckDB and Parquet as the query engine and core storage layer.

Designed to emulate major data lake and analytics platforms such as AWS S3, Azure Data Explorer, and GCP Storage at home lab scale. Parquet files can be processed and ingested into ClickHouse, Snowflake, and Databricks without changing the detection logic. Only the execution engine scales. 

Telemetry flows from windows/linux, network and cloud sources through Fluent Bit and into a normalized Parquet store. 
- DuckDB queries the store directly
- A detection runner executes scheduled rules against live data
- Alerts land in Postgres and surface in the SIEM UI

The following query languages are supported: 
- KQL - Kusto Query Language | Active
- SPL - Splunk Processing Language | Active
- SQL - Native DuckDB | Active
- AQL - Arkime-style packet queries | In-progress
- Lucene - Lucene-style search | Planned
- EQL - Elastic Query Language | Planned


Log Sources:
- Windows Sysmon via Winlogbeat
- Linux Auditd and Laurel
- Zeek network sensor
- AWS CloudTrail
- Azure/Entra
- Kubernetes audit logs

Current Phase: 0 - Research | Environment | GH Scaffolding
