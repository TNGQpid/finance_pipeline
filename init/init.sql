CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS raw.prices (
    symbol TEXT,
    date DATE,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT,
    retrieved_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.news (
    id SERIAL PRIMARY KEY,
    symbol TEXT,
    headline TEXT,
    source TEXT,
    published_at TIMESTAMP,
    content TEXT,
    retrieved_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.macro (
    indicator TEXT,
    date DATE,
    value NUMERIC,
    retrieved_at TIMESTAMP DEFAULT NOW()
);
