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
    seed_default_tuning_data()


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
