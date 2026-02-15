"""Database setup and session management."""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import get_settings

settings = get_settings()

# SQLite needs check_same_thread=False, MySQL/PostgreSQL don't
connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True  # Handles connection drops for MySQL/PostgreSQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
    _migrate_stream_session_post_analysis()
    _migrate_challenge_config_enabled()
    _migrate_challenge_session_screenshots()
    _migrate_user_lockout()
    _migrate_otp_purpose()
    _migrate_user_enabled_features()
    seed_default_tuning_data()
    seed_challenge_defaults()


def _migrate_stream_session_post_analysis():
    """Add post-analysis columns to stream_sessions if missing (ALTER TABLE)."""
    import logging
    logger = logging.getLogger(__name__)

    new_columns = {
        "analysis_status": "VARCHAR(20) DEFAULT 'none'",
        "analysis_progress": "INTEGER DEFAULT 0",
        "annotated_video_local_path": "VARCHAR(512)",
        "annotated_video_s3_key": "VARCHAR(512)",
        "raw_video_local_path": "VARCHAR(512)",
        "raw_video_s3_key": "VARCHAR(512)",
        "frame_data_local_path": "VARCHAR(512)",
        "frame_data_s3_key": "VARCHAR(512)",
        "enable_tuning_data": "BOOLEAN DEFAULT 0",
        "enable_shuttle_tracking": "BOOLEAN DEFAULT 1",
        "stream_mode": "VARCHAR(20) DEFAULT 'basic'",
        "chunk_duration": "INTEGER DEFAULT 60",
        "post_analysis_shots": "INTEGER",
        "post_analysis_distribution": "JSON",
        "post_analysis_rallies": "INTEGER",
        "post_analysis_shuttle_hits": "INTEGER",
        "post_analysis_rally_data": "JSON",
        "storage_type": "VARCHAR(10) DEFAULT 'local'",
        "s3_output_prefix": "VARCHAR(512)",
    }

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("stream_sessions")}
        with engine.begin() as conn:
            for col_name, col_type in new_columns.items():
                if col_name not in existing:
                    conn.execute(text(
                        f"ALTER TABLE stream_sessions ADD COLUMN {col_name} {col_type}"
                    ))
                    logger.info(f"Added column stream_sessions.{col_name}")
    except Exception as e:
        logger.debug(f"stream_sessions migration skipped: {e}")


def _migrate_challenge_config_enabled():
    """Add 'enabled' column to challenge_configs if missing."""
    import logging
    logger = logging.getLogger(__name__)

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("challenge_configs")}
        if "enabled" not in existing:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE challenge_configs ADD COLUMN enabled BOOLEAN DEFAULT 0 NOT NULL"
                ))
                logger.info("Added column challenge_configs.enabled")
    except Exception as e:
        logger.debug(f"challenge_configs migration skipped: {e}")


def _migrate_challenge_session_screenshots():
    """Add screenshot columns to challenge_sessions if missing."""
    import logging
    logger = logging.getLogger(__name__)

    new_columns = {
        "screenshots_s3_prefix": "VARCHAR(512)",
        "screenshot_count": "INTEGER DEFAULT 0",
    }

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("challenge_sessions")}
        with engine.begin() as conn:
            for col_name, col_type in new_columns.items():
                if col_name not in existing:
                    conn.execute(text(
                        f"ALTER TABLE challenge_sessions ADD COLUMN {col_name} {col_type}"
                    ))
                    logger.info(f"Added column challenge_sessions.{col_name}")
    except Exception as e:
        logger.debug(f"challenge_sessions screenshot migration skipped: {e}")


def _migrate_user_lockout():
    """Add lockout columns to users table if missing."""
    import logging
    logger = logging.getLogger(__name__)

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("users")}
        with engine.begin() as conn:
            if "failed_login_attempts" not in existing:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0"
                ))
                logger.info("Added column users.failed_login_attempts")
            if "locked_until" not in existing:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN locked_until DATETIME"
                ))
                logger.info("Added column users.locked_until")
    except Exception as e:
        logger.debug(f"users lockout migration skipped: {e}")


def _migrate_otp_purpose():
    """Add purpose column to email_otps table if missing."""
    import logging
    logger = logging.getLogger(__name__)

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("email_otps")}
        if "purpose" not in existing:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE email_otps ADD COLUMN purpose VARCHAR(20) DEFAULT 'verify'"
                ))
                logger.info("Added column email_otps.purpose")
    except Exception as e:
        logger.debug(f"email_otps purpose migration skipped: {e}")


def _migrate_user_enabled_features():
    """Add enabled_features JSON column to users table and backfill."""
    import logging
    import json
    logger = logging.getLogger(__name__)

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("users")}
        if "enabled_features" not in existing:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN enabled_features JSON"
                ))
                # Backfill: admins get all features, non-admins get pushup only
                from .db_models.user import ALL_FEATURES, DEFAULT_FEATURES
                conn.execute(text(
                    "UPDATE users SET enabled_features = :all_feat WHERE is_admin = 1"
                ), {"all_feat": json.dumps(ALL_FEATURES)})
                conn.execute(text(
                    "UPDATE users SET enabled_features = :default_feat WHERE is_admin = 0 OR is_admin IS NULL"
                ), {"default_feat": json.dumps(DEFAULT_FEATURES)})
                logger.info("Added and backfilled users.enabled_features")
    except Exception as e:
        logger.debug(f"users enabled_features migration skipped: {e}")


def seed_challenge_defaults():
    """Ensure ChallengeConfig rows exist for all challenge types with defaults."""
    from .features.challenges.db_models.challenge import ChallengeConfig
    from .features.challenges.services.rep_counter import CHALLENGE_DEFAULTS
    import logging

    logger = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        for ctype, defaults in CHALLENGE_DEFAULTS.items():
            existing = db.query(ChallengeConfig).filter(
                ChallengeConfig.challenge_type == ctype
            ).first()
            if not existing:
                row = ChallengeConfig(
                    challenge_type=ctype,
                    thresholds=defaults,
                    enabled=(ctype == "pushup"),
                )
                db.add(row)
                logger.info(f"Seeded challenge config for {ctype} (enabled={ctype == 'pushup'})")
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Failed to seed challenge defaults: {e}")
    finally:
        db.close()


def seed_default_tuning_data():
    """Seed default tuning presets and activity schemas."""
    from .db_models.tuning import TuningPreset, ActivityThresholdSchema
    from .models.tuning import get_default_badminton_thresholds, get_badminton_activity_schema
    import logging

    logger = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        default_thresholds = get_default_badminton_thresholds()

        # Check if default preset already exists
        existing = db.query(TuningPreset).filter(
            TuningPreset.is_default == True,
            TuningPreset.activity_type == "badminton"
        ).first()

        if not existing:
            # Create default badminton preset
            default_preset = TuningPreset(
                name="Default",
                description="System default thresholds for badminton shot detection",
                activity_type="badminton",
                thresholds=default_thresholds,
                is_active=True,
                is_default=True,
                created_by=None  # System-created
            )
            db.add(default_preset)
            logger.info("Created default badminton preset")
        else:
            # Update existing default preset to include new position thresholds
            # (handles schema updates when new thresholds are added)
            current_thresholds = existing.thresholds or {}
            updated = False

            # Ensure position thresholds exist and have all required keys
            if "position" not in current_thresholds:
                current_thresholds["position"] = default_thresholds.get("position", {})
                updated = True
            else:
                # Check for new position threshold keys
                for key, val in default_thresholds.get("position", {}).items():
                    if key not in current_thresholds["position"]:
                        current_thresholds["position"][key] = val
                        updated = True

            if updated:
                existing.thresholds = current_thresholds
                logger.info("Updated default badminton preset with new position thresholds")

        # Check if activity schema exists
        existing_schema = db.query(ActivityThresholdSchema).filter(
            ActivityThresholdSchema.activity_type == "badminton"
        ).first()

        badminton_schema = get_badminton_activity_schema()

        if not existing_schema:
            # Create badminton activity schema
            activity_schema = ActivityThresholdSchema(
                activity_type="badminton",
                display_name="Badminton",
                description="Shot detection for badminton",
                schema=badminton_schema,
                classifier_module="api.services.frame_analyzer"
            )
            db.add(activity_schema)
            logger.info("Created badminton activity schema")
        else:
            # Update schema to include new thresholds
            existing_schema.schema = badminton_schema
            logger.info("Updated badminton activity schema")

        db.commit()
    except Exception as e:
        db.rollback()
        # Log but don't fail - seeding is not critical
        logger.warning(f"Failed to seed tuning data: {e}")
    finally:
        db.close()
