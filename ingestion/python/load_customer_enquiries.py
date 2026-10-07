"""
File: load_customer_enquiries.py
Description: This script loads customer enquiries data into the database.
Author: Pankaj Shitole
"""

# Import necessary libraries
import os
import psycopg2
from dotenv import load_dotenv
import requests

# API endpoint for fetching customer enquiries data
API_URL = (
    "https://data.brisbane.qld.gov.au/api/explore/v2.1/"
    "catalog/datasets/contact-centre-customer-enquiries/records"
)

START_DATE = "2024-01-01"
PAGE_SIZE = 500  # Number of records to fetch per API request

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
def prepare_raw_table(conn):
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

            DELETE FROM raw.customer_enquiries
            WHERE date >= %s;
            """,
            (START_DATE,),
        )

    conn.commit()

# Function to fetch a page of customer enquiries data from the API
def fetch_page(offset):
    params = {
        "limit": PAGE_SIZE,
        "offset": offset,
        "where": f"date >= '{START_DATE}'",
    }

    response = requests.get(API_URL, params=params, timeout=60)
    response.raise_for_status()

    return response.json()


def insert_rows(conn, rows):
    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO raw.customer_enquiries (
                date,
                channel,
                work_site,
                category,
                service,
                volume
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    row.get("date"),
                    row.get("channel"),
                    row.get("work_site"),
                    row.get("category"),
                    row.get("service"),
                    row.get("volume"),
                )
                for row in rows
            ],
        )

    conn.commit()


def main():
    load_dotenv()

    conn = get_db_connection()

    try:
        prepare_raw_table(conn)

        offset = 0
        total_loaded = 0

        while True:
            payload = fetch_page(offset)
            rows = payload.get("results", [])

            if not rows:
                break

            insert_rows(conn, rows)

            total_loaded += len(rows)
            offset += PAGE_SIZE

            print(f"Loaded {total_loaded:,} rows")

            if len(rows) < PAGE_SIZE:
                break

        print(f"Finished. Loaded {total_loaded:,} rows.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
