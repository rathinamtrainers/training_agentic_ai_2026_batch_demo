-- Runs once, on an empty volume, when the container is first created.
-- The table itself is created by 01_ingest.py; this only makes sure the
-- database knows what a vector is before anything tries to store one.
CREATE EXTENSION IF NOT EXISTS vector;
