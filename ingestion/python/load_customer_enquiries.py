"""
File: load_customer_enquiries.py
Description: This script loads Brisbane City Council customer enquiry data into Neon PostgreSQL.

The Brisbane API limits:
    - limit <= 100
    - offset + limit <= 10,000

To avoid the offset limitation, this loader extracts data one source-date
at a time.

Modes:
    backfill
        Load from --start-date through the latest available source date.

    incremental
        Reload from the last successfully loaded source date through the
        latest available source date.

The last successful ingestion is tracked in the generic
raw.ingestion_state table so this pattern can support multiple APIs.
Author: Pankaj Shitole
"""

# Import necessary libraries
import argparse
import os
from datetime import date, datetime, timedelta, timezone

import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.extras import execute_values


# API endpoint for fetching customer enquiries data
API_URL = (
    "https://data.brisbane.qld.gov.au/api/explore/v2.1/"
    "catalog/datasets/contact-centre-customer-enquiries/records"
)

PIPELINE_NAME = "customer_enquiries"
SOURCE_NAME = "brisbane_open_data"
PAGE_SIZE = 100  # Number of records to fetch per API request

# Function to establish a database connection using environment variables
def get_db_connection():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        sslmode="require",
    )

# Function to create the raw.customer_enquiries table if it doesn't exist
def prepare_database(conn):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            CREATE SCHEMA IF NOT EXISTS raw;

            CREATE TABLE IF NOT EXISTS raw.customer_enquiries (
                date DATE,
                channel TEXT,
                work_site TEXT,
                category TEXT,
                service TEXT,
                volume BIGINT
            );

            CREATE TABLE IF NOT EXISTS raw.ingestion_state (
                pipeline_name TEXT PRIMARY KEY,
                source_name TEXT NOT NULL,
                last_successful_run_at TIMESTAMPTZ,
                last_successful_source_date DATE,
                last_status TEXT,
                last_rows_loaded BIGINT,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )

    conn.commit()

# Function to retrieve the last successful ingestion state for the pipeline
def get_ingestion_state(conn):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                last_successful_run_at,
                last_successful_source_date
            FROM raw.ingestion_state
            WHERE pipeline_name = %s;
            """,
            (PIPELINE_NAME,),
        )

        return cursor.fetchone()
    
# Function to fetch a page of customer enquiries data from the API
def fetch_page(window_start, window_end, offset):
    params = {
        "limit": PAGE_SIZE,
        "offset": offset,
        "where": (
            f"date >= date'{window_start}' "
            f"AND date < date'{window_end}'"
        ),
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=60,
    )

    if not response.ok:
        print("API URL:", response.url)
        print("API status:", response.status_code)
        print("API response:", response.text)

    response.raise_for_status()

    return response.json()

# Function to insert rows of customer enquiries data into the database
def insert_rows(cursor, rows):
    values = [
        (
            row.get("date"),
            row.get("channel"),
            row.get("work_site"),
            row.get("category"),
            row.get("service"),
            row.get("volume"),
        )
        for row in rows
    ]

    if not values:
        return

    execute_values(
        cursor,
        """
        INSERT INTO raw.customer_enquiries (
            date,
            channel,
            work_site,
            category,
            service,
            volume
        )
        VALUES %s
        """,
        values,
        page_size=PAGE_SIZE,
    )
    
# Function to load customer enquiries data for a specific date window
def load_date_window(cursor, window_start, window_end):
    offset = 0
    window_rows = 0

    while True:
        payload = fetch_page(
            window_start,
            window_end,
            offset,
        )

        rows = payload.get("results", [])

        if not rows:
            break

        insert_rows(cursor, rows)

        window_rows += len(rows)
        offset += len(rows)

        if len(rows) < PAGE_SIZE:
            break

    return window_rows

# Function to update the ingestion state in the database after a successful load
def update_ingestion_state(
    cursor,
    successful_source_date,
    rows_loaded,
    run_started_at,
):
    cursor.execute(
        """
        INSERT INTO raw.ingestion_state (
            pipeline_name,
            source_name,
            last_successful_run_at,
            last_successful_source_date,
            last_status,
            last_rows_loaded,
            updated_at
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            'SUCCESS',
            %s,
            NOW()
        )
        ON CONFLICT (pipeline_name)
        DO UPDATE SET
            source_name = EXCLUDED.source_name,
            last_successful_run_at = EXCLUDED.last_successful_run_at,
            last_successful_source_date = EXCLUDED.last_successful_source_date,
            last_status = EXCLUDED.last_status,
            last_rows_loaded = EXCLUDED.last_rows_loaded,
            updated_at = NOW();
        """,
        (
            PIPELINE_NAME,
            SOURCE_NAME,
            run_started_at,
            successful_source_date,
            rows_loaded,
        ),
    )



# Function to parse command-line arguments for the script
def parse_args():
    parser = argparse.ArgumentParser(
        description="Load Brisbane customer enquiry data."
    )

    parser.add_argument(
        "--mode",
        choices=["backfill", "incremental"],
        required=True,
    )

    parser.add_argument(
        "--start-date",
        help="Start date for backfill, e.g. 2024-01-01",
    )

    parser.add_argument(
        "--end-date",
        help=(
            "Optional exclusive end date for backfill. "
            "Example: 2024-01-08"
        ),
    )
    
    parser.add_argument(
        "--as-of-date",
        help=(
            "Simulated latest source date for incremental runs. "
            "Useful for testing historical incremental ingestion."
        ),
    )

    return parser.parse_args()

# Main function to orchestrate the data loading process based on the specified mode and date range
def main():
    load_dotenv()

    args = parse_args()

    conn = get_db_connection()

    run_started_at = datetime.now(timezone.utc)

    try:
        prepare_database(conn)

        state = get_ingestion_state(conn)

        if args.mode == "backfill":
            if not args.start_date:
                raise ValueError(
                    "--start-date is required for backfill mode."
                )

            start_date = date.fromisoformat(args.start_date)

            if args.end_date:
                end_date = date.fromisoformat(args.end_date)
            else:
                # For now, use today's date as the exclusive boundary.
                end_date = date.today()

        else:
            if state is None:
                raise ValueError(
                    "No previous successful ingestion found. "
                    "Run a backfill first."
                )

            last_successful_source_date = state[1]

            if last_successful_source_date is None:
                raise ValueError(
                    "Previous ingestion has no successful source date."
                )

            # Re-load the last successful date to handle source corrections.
            start_date = last_successful_source_date

            if args.as_of_date:
                end_date = date.fromisoformat(args.as_of_date) + timedelta(days=1)
            else:
                end_date = date.today()

        if start_date >= end_date:
            raise ValueError(
                f"Invalid date range: {start_date} to {end_date}"
            )

        print(
            f"Loading source dates from {start_date} "
            f"through {end_date - timedelta(days=1)}..."
        )

        total_loaded = 0
        current_date = start_date

        with conn:
            with conn.cursor() as cursor:

                # Replace the extraction window inside the same transaction.
                cursor.execute(
                    """
                    DELETE FROM raw.customer_enquiries
                    WHERE date >= %s
                      AND date < %s;
                    """,
                    (start_date, end_date),
                )

                while current_date < end_date:
                    next_date = current_date + timedelta(days=1)

                    rows_loaded = load_date_window(
                        cursor,
                        current_date,
                        next_date,
                    )

                    total_loaded += rows_loaded

                    print(
                        f"{current_date}: "
                        f"{rows_loaded:,} rows"
                    )

                    current_date = next_date

                # The latest successfully processed source date is the
                # final date included in the extraction.
                successful_source_date = end_date - timedelta(days=1)

                update_ingestion_state(
                    cursor,
                    successful_source_date,
                    total_loaded,
                    run_started_at,
                )

        print()
        print("Ingestion completed successfully.")
        print(f"Rows loaded: {total_loaded:,}")
        print(
            f"Latest source date: "
            f"{successful_source_date}"
        )
        print(
            f"Run started: "
            f"{run_started_at.isoformat()}"
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()
