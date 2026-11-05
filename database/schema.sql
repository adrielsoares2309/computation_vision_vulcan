-- Schema operacional SQLite para VulcanTech Smart Metals S.A.

CREATE TABLE IF NOT EXISTS sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    id_celula TEXT NOT NULL,
    liga_metalica TEXT NOT NULL,
    temperatura_fuso_c REAL,
    vibracao_triaxial_rms_mms REAL,
    torque_fuso_nm REAL,
    vazao_refrigerante_lmin REAL,
    corrente_estator_amp REAL,
    pressao_hidraulica_bar REAL,
    nivel_ruido_db REAL,
    warnings_json TEXT DEFAULT '[]',
    data_source TEXT NOT NULL DEFAULT 'api',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sensor_readings_celula_ts ON sensor_readings(id_celula, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_readings_source ON sensor_readings(data_source);

CREATE TABLE IF NOT EXISTS maintenance_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reading_id INTEGER,
    timestamp TEXT NOT NULL,
    id_celula TEXT NOT NULL,
    liga_metalica TEXT NOT NULL,
    predicted_class_code INTEGER NOT NULL,
    predicted_class_name TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    scores_json TEXT NOT NULL,
    warnings_json TEXT DEFAULT '[]',
    model_name TEXT NOT NULL,
    data_source TEXT NOT NULL DEFAULT 'api',
    created_at TEXT NOT NULL,
    FOREIGN KEY (reading_id) REFERENCES sensor_readings(id)
);

CREATE INDEX IF NOT EXISTS idx_predictions_celula_ts ON maintenance_predictions(id_celula, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_source ON maintenance_predictions(data_source);

CREATE TABLE IF NOT EXISTS maintenance_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER,
    timestamp TEXT NOT NULL,
    id_celula TEXT NOT NULL,
    fault_code INTEGER NOT NULL,
    fault_name TEXT NOT NULL,
    severity TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    message TEXT NOT NULL,
    data_source TEXT NOT NULL DEFAULT 'api',
    acknowledged INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (prediction_id) REFERENCES maintenance_predictions(id)
);

CREATE INDEX IF NOT EXISTS idx_alerts_celula_ts ON maintenance_alerts(id_celula, timestamp DESC);

CREATE TABLE IF NOT EXISTS vision_inspections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_uid TEXT NOT NULL UNIQUE,
    timestamp TEXT NOT NULL,
    piece_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    modality TEXT NOT NULL,
    predicted_class TEXT NOT NULL,
    scores_json TEXT NOT NULL,
    score_type TEXT NOT NULL,
    model_status TEXT NOT NULL,
    experimental INTEGER NOT NULL DEFAULT 1,
    validated_for_industrial_use INTEGER NOT NULL DEFAULT 0,
    warnings_json TEXT NOT NULL,
    data_source TEXT NOT NULL DEFAULT 'api',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_vision_ts ON vision_inspections(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_vision_modality ON vision_inspections(modality);

CREATE TABLE IF NOT EXISTS production_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    id_celula TEXT NOT NULL,
    liga_metalica TEXT NOT NULL,
    shift TEXT NOT NULL,
    planned_time_min REAL NOT NULL,
    downtime_min REAL NOT NULL,
    ideal_cycle_time_min REAL NOT NULL,
    total_count INTEGER NOT NULL,
    good_count INTEGER NOT NULL,
    rejected_count INTEGER NOT NULL,
    downtime_reason TEXT,
    associated_fault_class INTEGER DEFAULT 0,
    data_source TEXT NOT NULL DEFAULT 'simulated',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_production_celula_ts ON production_events(id_celula, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_production_source ON production_events(data_source);

