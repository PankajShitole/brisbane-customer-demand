# Brisbane Customer Demand Analytics

A hands-on data engineering and analytics engineering project using Python, PostgreSQL, dbt Core, and SQL to transform Brisbane City Council customer enquiry data into reliable, tested, analytics-ready datasets.

## 1. Business Problem

Brisbane City Council receives customer enquiries across multiple channels, services, categories, and work sites. Understanding how this demand changes over time can help operational teams identify demand patterns, changes in channel usage, high-volume services, and workload trends.

This project builds a small analytical data platform to ingest publicly available customer enquiry data, transform it into structured datasets, validate data quality, and prepare it for reporting and business analysis.

The objective is to demonstrate an end-to-end ELT pipeline using practical data engineering and analytics engineering techniques.

### Business Questions

The analytical models are intended to answer questions such as:

1. **Demand trends:** How does enquiry volume change daily, weekly, and monthly?
2. **Channel usage:** Which channels account for the largest share of enquiry volume, and how does that mix change over time?
3. **Service demand:** Which services and categories generate the highest enquiry volumes?
4. **Work-site demand:** How does recorded enquiry volume differ across work sites?
5. **Demand shifts:** Which channels, services, or categories are increasing or decreasing in volume over time?

These questions support demand analysis and resource-planning discussions. The dataset contains aggregated observations, so the project does not claim to measure individual ticket resolution times, SLA compliance, or actual staffing adequacy.

## 2. Project Objectives

The project aims to:

- Ingest data from a public API using Python.
- Load source observations into PostgreSQL.
- Use dbt Core for SQL-based transformations.
- Separate source-oriented staging logic from reusable transformations and reporting models.
- Implement built-in and custom SQL data quality tests.
- Document data sources, models, assumptions, and lineage.
- Explore incremental ingestion and incremental dbt models.
- Maintain the project using Git and GitHub.
- Prepare tested, reporting-friendly datasets for potential Power BI consumption.

The project is built incrementally, with correctness and understandable design taking priority over unnecessary complexity.

## 3. Technology Stack

| Technology | Purpose |
|---|---|
| Python | API extraction and raw-data ingestion |
| PostgreSQL / Neon | Raw storage and transformed analytical datasets |
| dbt Core | SQL transformations, testing, documentation, and lineage |
| dbt-postgres | Connects dbt Core to PostgreSQL |
| Git | Version control |
| GitHub | Source-code hosting and project documentation |
| Power BI | Potential downstream reporting consumer |

The project uses dbt Core locally and does not depend on paid dbt Cloud features.

## 4. Data Source

The project uses the Brisbane City Council open-data dataset:

**Contact Centre Customer Enquiries**

Source API:

[Brisbane Open Data API](https://data.brisbane.qld.gov.au/api/explore/v2.1/catalog/datasets/contact-centre-customer-enquiries/records)

The source provides aggregated enquiry observations with fields including:

| Field | Meaning |
|---|---|
| `date` | Date associated with the observation |
| `channel` | Enquiry channel |
| `work_site` | Recorded work site |
| `category` | Enquiry category |
| `service` | Service associated with the enquiry |
| `volume` | Aggregated enquiry volume |

### Data Grain

The candidate grain for dated observations is:

`date + channel + work_site + category + service`

Initial source profiling found no duplicate combinations at this grain among the dated observations examined.

The grain is validated in the current loaded sample through a custom dbt SQL test.

### Data Considerations

- The source contains aggregated observations, not individual customer enquiry records.
- Some source records have missing dates. The current ingestion sample contains dated records.
- The API limits the number of records returned per request, so ingestion uses date-based windows rather than relying on unrestricted offset pagination.
- Historical source data may be corrected, so ingestion must account for potential updates to previously loaded periods.
- The current database sample is limited to a small date range for development and testing. It should not be interpreted as a complete historical dataset.

## 5. Architecture

The intended pipeline is:

```text
Brisbane City Council Open Data API
                 |
                 v
        Python ingestion
                 |
                 v
       PostgreSQL / Neon
            raw schema
                 |
                 v
            dbt Core
                 |
                 v
             Staging
                 |
                 v
           Intermediate
                 |
                 v
               Marts
                 |
                 v
       Analytics / Power BI
```

### Layer Responsibilities

#### Raw

Stores ingested source observations in PostgreSQL.

Python is responsible for extraction and loading. The raw table is declared in dbt as an upstream source rather than being created by a dbt transformation model.

#### Staging

Provides a consistent, source-oriented representation of the data.

Typical responsibilities include:

- Renaming source columns.
- Standardizing data types and values where necessary.
- Applying lightweight source-level transformations.
- Defining basic data quality expectations.

Implemented model:

`stg_customer_enquiries`

#### Intermediate

Will contain reusable transformation logic where separating business calculations or multi-step SQL improves clarity and maintainability.

Proposed first model:

`int_monthly_demand_by_channel`

Its intended grain is one row per month and channel, with total enquiry volume for that combination.

#### Marts

Will contain reporting-oriented models designed around the business questions and downstream consumers.

A proposed model is:

`mart_monthly_channel_demand`

Its intended purpose is to expose monthly channel demand and useful reporting metrics, such as channel share and period-over-period changes.

Intermediate and mart models will be added when their business purpose is clear. Not every transformation requires a separate model.

## 6. Repository Structure

The project is organized as follows:

```text
brisbane-customer-demand/
├── ingestion/
│   └── python/
│       └── load_customer_enquiries.py
├── dbt/
│   ├── dbt_project.yml
│   ├── models/
│   │   ├── staging/
│   │   │   ├── _sources.yml
│   │   │   ├── stg_customer_enquiries.sql
│   │   │   └── _stg_customer_enquiries.yml
│   │   ├── intermediate/
│   │   └── marts/
│   ├── tests/
│   │   └── assert_dated_source_grain_is_unique.sql
│   ├── macros/
│   ├── seeds/
│   ├── snapshots/
│   └── analyses/
├── sql/
├── tests/
├── docs/
│   └── dbt_learning_log.md
├── requirements.txt
├── .gitignore
└── README.md
```

Some directories are reserved for planned work and may not contain implementation files yet.

## 7. Current Implementation Status

### Completed

- [x] Public API selected and investigated.
- [x] Python ingestion pipeline implemented.
- [x] PostgreSQL raw table populated with a development sample.
- [x] dbt Core and the PostgreSQL adapter configured locally.
- [x] dbt connection verified with `dbt debug`.
- [x] Source declared in dbt YAML.
- [x] Staging view `stg_customer_enquiries` created successfully.
- [x] Staging model tested for non-null values in six required column assertions.
- [x] Custom singular SQL test created to check the dated five-column grain.
- [x] `dbt build --select stg_customer_enquiries` completed successfully.

### Planned

- [ ] Build intermediate transformation models.
- [ ] Build business-facing mart models.
- [ ] Add tests for business rules and metric correctness.
- [ ] Evaluate and implement a dbt incremental model.
- [ ] Generate and review dbt documentation and lineage.
- [ ] Exercise data quality failure scenarios and recovery.
- [ ] Improve README examples as the implementation grows.
- [ ] Evaluate orchestration with Airflow after the core pipeline is stable.
- [ ] Prepare the final datasets for reporting consumption.

## 8. Data Quality and Testing

Data quality is validated through dbt tests.

### Built-in Column Tests

The staging model has `not_null` tests on:

- `enquiry_date`
- `channel`
- `work_site`
- `category`
- `service`
- `volume`

These tests express expectations for the staging model's current analytical data. In particular, the date test reflects that the current ingestion sample contains dated records, not that the complete upstream source never contains missing dates.

### Custom SQL Test

File:

`dbt/tests/assert_dated_source_grain_is_unique.sql`

The test groups dated observations by:

- `enquiry_date`
- `channel`
- `work_site`
- `category`
- `service`

It returns combinations that occur more than once.

In dbt singular tests, a query returning zero rows means the assertion passes. Returned rows indicate a violation that needs investigation.

### Validation Commands

Run the staging tests:

```bash
cd dbt
dbt test --select stg_customer_enquiries
```

Build the staging model and its associated tests:

```bash
dbt build --select stg_customer_enquiries
```

The tests validate the current data at execution time. They do not guarantee that future ingestion batches will always satisfy the same assumptions.

## 9. Local Setup

### Prerequisites

- Python
- Git
- A PostgreSQL-compatible database, such as Neon
- dbt Core with the PostgreSQL adapter
- Access to the public Brisbane Open Data API

### Python Environment

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### dbt Environment

Activate the Python environment and move into the dbt project:

```bash
source .venv/bin/activate
cd dbt
```

Check the installed version:

```bash
dbt --version
```

Validate project configuration and the database connection:

```bash
dbt debug
```

### Database Credentials

Configure the dbt profile for your PostgreSQL database using the local `profiles.yml` and appropriate connection settings.

Do not commit credentials, passwords, connection strings containing secrets, or local environment files to GitHub.

## 10. Running the Project

### Parse the dbt Project

```bash
cd dbt
dbt parse
```

### Compile a Model

```bash
dbt compile --select stg_customer_enquiries
```

Compilation renders dbt's SQL and resolves Jinja references. It does not, by itself, prove that the resulting SQL executes successfully or that the data is correct.

### Run the Staging Model

```bash
dbt run --select stg_customer_enquiries
```

### Run Staging Tests

```bash
dbt test --select stg_customer_enquiries
```

### Build the Staging Model and Tests

```bash
dbt build --select stg_customer_enquiries
```

The Python ingestion script is located at:

`ingestion/python/load_customer_enquiries.py`

Use the script's supported command-line options to select an ingestion mode and date range. The raw ingestion process should be completed before running downstream dbt transformations.

## 11. Key Design Decisions

### Python for Ingestion, dbt for Transformations

Python handles extraction and loading. dbt handles SQL-based warehouse transformations and analytical data quality tests.

This separation keeps ingestion responsibilities distinct from analytical modeling.

### Sources and Refs

`source()` identifies an upstream relation declared in source YAML.

`ref()` identifies another dbt model and establishes a dependency in dbt's model graph.

These declarations help dbt resolve relations and build model lineage.

### Materializations

Materialization is selected based on model purpose and operational requirements.

- Views are useful for lightweight transformations that should reflect current upstream data when queried.
- Tables are useful when persisting transformed results is beneficial.
- Incremental models may be useful for larger datasets, but require a correct strategy for updates and late-arriving data.

The project will start with correctness and clear model behavior before introducing incremental complexity.

### Model Layers

The raw, staging, intermediate, and marts structure is an architectural choice for this project, not a mandatory structure imposed by dbt.

Models will be separated when that improves readability, reuse, testing, or downstream consumption.

## 12. Learning Outcomes

This project is intended to develop practical skills in:

- Python API ingestion.
- PostgreSQL data loading and querying.
- dbt project configuration and profiles.
- Sources, models, `source()`, and `ref()`.
- SQL transformations and materializations.
- Built-in and custom data quality tests.
- Model dependencies and lineage.
- Incremental processing and handling historical corrections.
- Git-based development and technical documentation.
- Explaining architecture and design trade-offs in data engineering interviews.

A detailed learning journal is maintained separately in `docs/dbt_learning_log.md`.

## 13. Future Improvements

Potential extensions, after the core analytical pipeline is complete, include:

- Additional tests for business rules and valid volume values.
- More detailed handling of source records with missing dates.
- Incremental dbt transformations with explicit late-arriving-data handling.
- Generated dbt documentation.
- Automated execution and monitoring.
- Power BI reporting.
- Airflow orchestration, if justified by the completed pipeline.

These extensions will be introduced according to project needs rather than added solely to increase the number of tools used.

## 14. Project Goal

The goal is to build a reliable, understandable, and tested analytical data pipeline that demonstrates how public source data can be transformed into useful business-facing datasets.

The emphasis is on correctness, clear modeling decisions, repeatable testing, and the ability to explain why each component exists.
