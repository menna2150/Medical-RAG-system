-- =====================================================================
-- MedRAG-EG  ·  Relational schema (Postgres flavour)
-- =====================================================================
-- This schema mirrors the JSON seed files. The runtime path uses FAISS +
-- JSON for portability; this DDL is the production target when the data
-- volume justifies a real RDBMS.

CREATE TABLE diseases (
    id              TEXT PRIMARY KEY,                -- e.g. d_influenza
    name            TEXT NOT NULL,
    icd11           TEXT,
    description     TEXT NOT NULL,
    source          TEXT NOT NULL,                   -- WHO / NICE / PubMed / textbook
    last_reviewed   DATE
);

CREATE TABLE disease_tests (
    disease_id      TEXT REFERENCES diseases(id) ON DELETE CASCADE,
    test_name       TEXT NOT NULL,
    PRIMARY KEY (disease_id, test_name)
);

-- Symptoms ----------------------------------------------------------------

CREATE TABLE symptoms (
    id              SERIAL PRIMARY KEY,
    name_en         TEXT UNIQUE NOT NULL,
    name_ar         TEXT,
    body_system     TEXT
);

CREATE TABLE symptom_mapping (
    symptom_id      INTEGER REFERENCES symptoms(id)  ON DELETE CASCADE,
    disease_id      TEXT    REFERENCES diseases(id)  ON DELETE CASCADE,
    weight          REAL NOT NULL CHECK (weight BETWEEN 0 AND 1),
    PRIMARY KEY (symptom_id, disease_id)
);

CREATE INDEX idx_symptom_mapping_disease ON symptom_mapping(disease_id);
CREATE INDEX idx_symptom_mapping_weight  ON symptom_mapping(weight DESC);

-- Medications (Egyptian market) -------------------------------------------

CREATE TABLE medications (
    drug_id         TEXT PRIMARY KEY,                -- e.g. m_amoxicillin
    generic_name    TEXT UNIQUE NOT NULL,
    price_egp       TEXT,                            -- range e.g. "30 – 70"
    last_verified   DATE,
    notes           TEXT
);

CREATE TABLE medication_classes (
    drug_id         TEXT REFERENCES medications(drug_id) ON DELETE CASCADE,
    class_name      TEXT NOT NULL,                   -- e.g. antibiotic, penicillin
    PRIMARY KEY (drug_id, class_name)
);

CREATE TABLE medication_brands_egypt (
    drug_id         TEXT REFERENCES medications(drug_id) ON DELETE CASCADE,
    brand_name      TEXT NOT NULL,
    PRIMARY KEY (drug_id, brand_name)
);

CREATE TABLE medication_indications (
    drug_id         TEXT REFERENCES medications(drug_id) ON DELETE CASCADE,
    indication      TEXT NOT NULL,
    PRIMARY KEY (drug_id, indication)
);

CREATE TABLE disease_treatments (
    disease_id      TEXT REFERENCES diseases(id)        ON DELETE CASCADE,
    drug_id         TEXT REFERENCES medications(drug_id) ON DELETE CASCADE,
    line_of_therapy SMALLINT,                        -- 1 = first line, 2 = second, ...
    PRIMARY KEY (disease_id, drug_id)
);

-- Audit / explainability --------------------------------------------------

CREATE TABLE rag_chunks (
    id              SERIAL PRIMARY KEY,
    disease_id      TEXT REFERENCES diseases(id),
    text            TEXT NOT NULL,
    source          TEXT NOT NULL,
    embedding_dim   INTEGER NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
