CREATE TABLE IF NOT EXISTS drivers (
    driver_id INTEGER PRIMARY KEY,
    driver_ref TEXT,
    number INTEGER,
    code TEXT,
    forename TEXT NOT NULL,
    surname TEXT NOT NULL,
    dob DATE,
    nationality TEXT,
    url TEXT
);

CREATE TABLE IF NOT EXISTS constructors (
    constructor_id INTEGER PRIMARY KEY,
    constructor_ref TEXT,
    name TEXT NOT NULL,
    nationality TEXT,
    url TEXT
);

CREATE TABLE IF NOT EXISTS circuits (
    circuit_id INTEGER PRIMARY KEY,
    circuit_ref TEXT,
    name TEXT NOT NULL,
    location TEXT,
    country TEXT,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    alt INTEGER,
    url TEXT
);

CREATE TABLE IF NOT EXISTS races (
    race_id INTEGER PRIMARY KEY,
    year INTEGER NOT NULL,
    round INTEGER NOT NULL,
    circuit_id INTEGER NOT NULL REFERENCES circuits(circuit_id),
    name TEXT NOT NULL,
    date DATE,
    time TEXT,
    url TEXT,
    fp1_date DATE,
    fp1_time TEXT,
    fp2_date DATE,
    fp2_time TEXT,
    fp3_date DATE,
    fp3_time TEXT,
    quali_date DATE,
    quali_time TEXT,
    sprint_date DATE,
    sprint_time TEXT
);

CREATE TABLE IF NOT EXISTS results (
    result_id INTEGER PRIMARY KEY,
    race_id INTEGER NOT NULL REFERENCES races(race_id),
    driver_id INTEGER NOT NULL REFERENCES drivers(driver_id),
    constructor_id INTEGER NOT NULL REFERENCES constructors(constructor_id),
    number INTEGER,
    grid INTEGER,
    position INTEGER,
    position_text TEXT,
    position_order INTEGER,
    points DOUBLE PRECISION,
    laps INTEGER,
    time TEXT,
    milliseconds BIGINT,
    fastest_lap INTEGER,
    rank INTEGER,
    fastest_lap_time TEXT,
    fastest_lap_speed DOUBLE PRECISION,
    status_id INTEGER
);
