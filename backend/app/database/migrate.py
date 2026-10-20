from sqlalchemy import inspect, text
from app.database.session import engine, Base
import app.models.models # Ensure all models are registered

def migrate_database():
    """
    Safely applies additive column migrations for SQLite and PostgreSQL
    without dropping existing data, and creates any newly defined tables.
    """
    Base.metadata.create_all(bind=engine)
    insp = inspect(engine)
    if "scan_images" in insp.get_table_names():
        existing = {c["name"] for c in insp.get_columns("scan_images")}
        cols_to_add = [
            ("image_type", "VARCHAR(30) DEFAULT 'FRONT'"),
            ("preprocessed_file_path", "VARCHAR(500)"),
            ("quality_score", "FLOAT DEFAULT 1.0"),
            ("preprocessing_status", "VARCHAR(50) DEFAULT 'NOT_REQUIRED'"),
            ("quality_decision", "VARCHAR(30) DEFAULT 'ACCEPTABLE'"),
            ("retake_guidance", "TEXT"),
            ("content_hash", "VARCHAR(64)"),
            ("perceptual_hash", "VARCHAR(64)"),
            ("is_duplicate", "BOOLEAN DEFAULT 0"),
            ("duplicate_of_id", "INTEGER"),
            ("duplicate_type", "VARCHAR(30)"),
            ("duplicate_reason", "TEXT"),
            ("ocr_status", "VARCHAR(50) DEFAULT 'PENDING'"),
            ("ocr_engine_used", "VARCHAR(50)"),
            ("ocr_confidence", "FLOAT DEFAULT 0.0"),
            ("ocr_detections_count", "INTEGER DEFAULT 0"),
            ("ocr_attempt_count", "INTEGER DEFAULT 0"),
            ("ocr_raw_boxes", "TEXT"),
        ]
        with engine.begin() as conn:
            for col, col_type in cols_to_add:
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE scan_images ADD COLUMN {col} {col_type}"))

    if "scans" in insp.get_table_names():
        existing_scans = {c["name"] for c in insp.get_columns("scans")}
        scan_cols_to_add = [
            ("scan_reliability", "TEXT"),
            ("coverage_summary", "TEXT"),
        ]
        with engine.begin() as conn:
            for col, col_type in scan_cols_to_add:
                if col not in existing_scans:
                    conn.execute(text(f"ALTER TABLE scans ADD COLUMN {col} {col_type}"))

    if "extracted_declarations" in insp.get_table_names():
        existing_decl = {c["name"] for c in insp.get_columns("extracted_declarations")}
        decl_cols_to_add = [
            ("raw_value", "TEXT"),
            ("unit", "VARCHAR(30)"),
            ("currency", "VARCHAR(10)"),
            ("extraction_method", "VARCHAR(50) DEFAULT 'DETERMINISTIC_CONTEXT'"),
            ("extraction_status", "VARCHAR(30) DEFAULT 'NOT_FOUND'"),
            ("field_confidence", "FLOAT DEFAULT 0.0"),
            ("raw_ocr_confidence", "FLOAT DEFAULT 0.0"),
            ("source_image_id", "INTEGER"),
            ("source_ocr_ids", "TEXT"),
            ("evidence", "TEXT"),
            ("has_conflict", "BOOLEAN DEFAULT 0"),
            ("alternate_candidates", "TEXT"),
        ]
        with engine.begin() as conn:
            for col, col_type in decl_cols_to_add:
                if col not in existing_decl:
                    conn.execute(text(f"ALTER TABLE extracted_declarations ADD COLUMN {col} {col_type}"))

if __name__ == "__main__":
    migrate_database()
    print("Database migration completed successfully.")
