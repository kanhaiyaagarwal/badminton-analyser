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
    _migrate_user_google_auth()
    _migrate_user_profile()
    _migrate_challenge_form_summary()
    _migrate_squat_variants()
    _migrate_feature_access_catalog()
    _migrate_user_signup_code()
    _migrate_mimic_session_screenshots()
    _migrate_mimic_session_uploaded_video()
    _migrate_mimic_session_audio_fields()
    _migrate_fix_non_ascii_s3_keys()
    _migrate_invite_code_scope()
    _migrate_add_workout_to_existing_users()
    _migrate_workout_session_m1()
    _migrate_exercise_progression()
    _migrate_exercise_demo_video()
    seed_default_tuning_data()
    seed_challenge_defaults()
    seed_feature_access()
    seed_exercises()


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
                from .db_models.user import ALL_FEATURES
                conn.execute(text(
                    "UPDATE users SET enabled_features = :all_feat WHERE is_admin = 1"
                ), {"all_feat": json.dumps(ALL_FEATURES)})
                conn.execute(text(
                    "UPDATE users SET enabled_features = :default_feat WHERE is_admin = 0 OR is_admin IS NULL"
                ), {"default_feat": json.dumps(["pushup"])})
                logger.info("Added and backfilled users.enabled_features")
    except Exception as e:
        logger.debug(f"users enabled_features migration skipped: {e}")


def _migrate_user_google_auth():
    """Add auth_provider column and make hashed_password nullable for Google OAuth."""
    import logging
    logger = logging.getLogger(__name__)

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("users")}
        with engine.begin() as conn:
            if "auth_provider" not in existing:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN auth_provider VARCHAR(20) DEFAULT 'local' NOT NULL"
                ))
                logger.info("Added column users.auth_provider")

            # Make hashed_password nullable (for Google OAuth users who have no password)
            # This is safe for MySQL; SQLite ignores ALTER COLUMN
            try:
                conn.execute(text(
                    "ALTER TABLE users MODIFY COLUMN hashed_password VARCHAR(255) NULL"
                ))
                logger.info("Made users.hashed_password nullable")
            except Exception:
                pass  # SQLite doesn't support MODIFY COLUMN, but it's already lenient with NULLs
    except Exception as e:
        logger.debug(f"users google auth migration skipped: {e}")


def _migrate_user_profile():
    """Add mobile column and drop username unique constraint."""
    import logging
    logger = logging.getLogger(__name__)

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("users")}
        with engine.begin() as conn:
            if "mobile" not in existing:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN mobile VARCHAR(20)"
                ))
                logger.info("Added column users.mobile")

            # Drop unique constraint on username (MySQL)
            try:
                indexes = inspector.get_indexes("users")
                for idx in indexes:
                    if idx.get("unique") and "username" in idx.get("column_names", []):
                        conn.execute(text(f"DROP INDEX {idx['name']} ON users"))
                        logger.info(f"Dropped unique index {idx['name']} on users.username")
                        break
            except Exception as e:
                logger.debug(f"username index drop skipped: {e}")
    except Exception as e:
        logger.debug(f"users profile migration skipped: {e}")


def _migrate_challenge_form_summary():
    """Add form_summary JSON column to challenge_sessions if missing."""
    import logging
    logger = logging.getLogger(__name__)

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("challenge_sessions")}
        if "form_summary" not in existing:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE challenge_sessions ADD COLUMN form_summary JSON"
                ))
                logger.info("Added column challenge_sessions.form_summary")
    except Exception as e:
        logger.debug(f"challenge_sessions form_summary migration skipped: {e}")


def _migrate_squat_variants():
    """Migrate old 'squat' challenge type to the 3 new squat variants."""
    import logging
    import json
    logger = logging.getLogger(__name__)

    db = SessionLocal()
    try:
        from sqlalchemy import text

        # 1. Migrate old squat sessions to squat_full
        try:
            result = db.execute(text(
                "UPDATE challenge_sessions SET challenge_type = 'squat_full' "
                "WHERE challenge_type = 'squat'"
            ))
            if result.rowcount > 0:
                logger.info(f"Migrated {result.rowcount} squat sessions to squat_full")
        except Exception as e:
            logger.debug(f"squat session migration skipped: {e}")

        # 2. Migrate old squat records to squat_full
        try:
            result = db.execute(text(
                "UPDATE challenge_records SET challenge_type = 'squat_full' "
                "WHERE challenge_type = 'squat'"
            ))
            if result.rowcount > 0:
                logger.info(f"Migrated {result.rowcount} squat records to squat_full")
        except Exception as e:
            logger.debug(f"squat record migration skipped: {e}")

        # 3. Migrate old squat config to squat_full
        try:
            result = db.execute(text(
                "UPDATE challenge_configs SET challenge_type = 'squat_full' "
                "WHERE challenge_type = 'squat'"
            ))
            if result.rowcount > 0:
                logger.info(f"Migrated squat config to squat_full")
        except Exception as e:
            logger.debug(f"squat config migration skipped: {e}")

        # 4. Consolidate squat variant features back to single "squat"
        try:
            from .db_models.user import User
            squat_variants = {"squat_hold", "squat_half", "squat_full"}
            users = db.query(User).all()
            for user in users:
                features = user.enabled_features or []
                if any(v in features for v in squat_variants):
                    features = [f for f in features if f not in squat_variants]
                    if "squat" not in features:
                        features.append("squat")
                    user.enabled_features = features
                    logger.info(f"Migrated user {user.id} features: consolidated squat variants to 'squat'")
        except Exception as e:
            logger.debug(f"user features migration skipped: {e}")

        # 5. Remove old squat variant feature access rows (replaced by single "squat")
        try:
            db.execute(text(
                "DELETE FROM feature_access WHERE feature_name IN ('squat_hold', 'squat_half', 'squat_full')"
            ))
        except Exception as e:
            logger.debug(f"feature_access squat cleanup skipped: {e}")

        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Squat variant migration failed: {e}")
    finally:
        db.close()


def _migrate_feature_access_catalog():
    """Add catalog columns to feature_access if missing."""
    import logging
    logger = logging.getLogger(__name__)

    new_columns = {
        "requestable": "BOOLEAN DEFAULT 1",
        "display_name": "VARCHAR(64)",
        "description": "VARCHAR(512)",
        "icon": "VARCHAR(8)",
    }

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("feature_access")}
        with engine.begin() as conn:
            for col_name, col_type in new_columns.items():
                if col_name not in existing:
                    conn.execute(text(
                        f"ALTER TABLE feature_access ADD COLUMN {col_name} {col_type}"
                    ))
                    logger.info(f"Added column feature_access.{col_name}")
    except Exception as e:
        logger.debug(f"feature_access catalog migration skipped: {e}")


def _migrate_user_signup_code():
    """Add signed_up_with_code column to users table."""
    import logging
    logger = logging.getLogger(__name__)
    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("users")}
        if "signed_up_with_code" not in existing:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN signed_up_with_code VARCHAR(50)"
                ))
                logger.info("Added column users.signed_up_with_code")
    except Exception as e:
        logger.debug(f"users signup code migration skipped: {e}")


def _migrate_mimic_session_screenshots():
    """Add screenshot columns to mimic_sessions if missing."""
    import logging
    logger = logging.getLogger(__name__)

    new_columns = {
        "screenshots_s3_prefix": "VARCHAR(512)",
        "screenshot_count": "INTEGER DEFAULT 0",
    }

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("mimic_sessions")}
        with engine.begin() as conn:
            for col_name, col_type in new_columns.items():
                if col_name not in existing:
                    conn.execute(text(
                        f"ALTER TABLE mimic_sessions ADD COLUMN {col_name} {col_type}"
                    ))
                    logger.info(f"Added column mimic_sessions.{col_name}")
    except Exception as e:
        logger.debug(f"mimic_sessions screenshot migration skipped: {e}")


def _migrate_mimic_session_uploaded_video():
    """Add uploaded_video_path column to mimic_sessions if missing."""
    import logging
    logger = logging.getLogger(__name__)

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("mimic_sessions")}
        if "uploaded_video_path" not in existing:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE mimic_sessions ADD COLUMN uploaded_video_path VARCHAR(512)"
                ))
                logger.info("Added column mimic_sessions.uploaded_video_path")
    except Exception as e:
        logger.debug(f"mimic_sessions uploaded_video_path migration skipped: {e}")


def _migrate_mimic_session_audio_fields():
    """Add audio_confidence/audio_offset columns and expand status ENUM for audio_mismatch."""
    import logging
    logger = logging.getLogger(__name__)

    new_columns = {
        "audio_confidence": "FLOAT",
        "audio_offset": "FLOAT",
    }

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("mimic_sessions")}
        with engine.begin() as conn:
            for col_name, col_type in new_columns.items():
                if col_name not in existing:
                    conn.execute(text(
                        f"ALTER TABLE mimic_sessions ADD COLUMN {col_name} {col_type}"
                    ))
                    logger.info(f"Added column mimic_sessions.{col_name}")

            # Expand status ENUM to include 'audio_mismatch' (MySQL only — SQLite ignores)
            try:
                conn.execute(text(
                    "ALTER TABLE mimic_sessions MODIFY COLUMN status "
                    "ENUM('ready','active','ended','audio_mismatch') DEFAULT 'ready'"
                ))
                logger.info("Expanded mimic_sessions.status ENUM to include 'audio_mismatch'")
            except Exception:
                pass  # SQLite doesn't support MODIFY COLUMN / ENUM
    except Exception as e:
        logger.debug(f"mimic_sessions audio fields migration skipped: {e}")


def _migrate_fix_non_ascii_s3_keys():
    """Fix S3 keys containing non-ASCII characters that break boto3's HTTP layer."""
    import logging
    import re
    logger = logging.getLogger(__name__)

    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            rows = conn.execute(text(
                "SELECT id, annotated_video_path FROM jobs "
                "WHERE annotated_video_path IS NOT NULL"
            )).fetchall()

            for row in rows:
                job_id, path = row[0], row[1]
                if not path:
                    continue
                # Check if path has non-ASCII characters
                try:
                    path.encode('ascii')
                    continue  # All ASCII, no fix needed
                except UnicodeEncodeError:
                    pass

                # Sanitize: keep directory prefix, fix filename
                parts = path.rsplit('/', 1)
                if len(parts) == 2:
                    prefix, filename = parts
                    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
                    name = name.encode('ascii', 'replace').decode('ascii').replace('?', '_')
                    name = re.sub(r'[^\w\-.]', '_', name)
                    name = re.sub(r'_+', '_', name).strip('_')
                    new_filename = f"{name}.{ext}" if ext else name
                    new_path = f"{prefix}/{new_filename}"
                else:
                    continue

                if new_path == path:
                    continue

                # Copy S3 object to sanitized key
                try:
                    from .services.storage_service import get_storage_service
                    from urllib.parse import quote
                    storage = get_storage_service()
                    if storage.is_s3():
                        bucket = storage.outputs.bucket
                        # Use URL-encoded string CopySource to avoid latin-1 encoding issues
                        encoded_source = f"{bucket}/{quote(path, safe='/')}"
                        storage.outputs.s3_client.copy_object(
                            Bucket=bucket,
                            CopySource=encoded_source,
                            Key=new_path,
                        )
                        logger.info(f"Copied S3 object for job {job_id}: {path!r} -> {new_path!r}")
                except Exception as e:
                    logger.warning(f"Could not copy S3 object for job {job_id}: {e}")

                # Update DB regardless (even if S3 copy fails, the old key doesn't work anyway)
                conn.execute(text(
                    "UPDATE jobs SET annotated_video_path = :new_path WHERE id = :job_id"
                ), {"new_path": new_path, "job_id": job_id})
                logger.info(f"Updated annotated_video_path for job {job_id}: {new_path}")
    except Exception as e:
        logger.debug(f"Non-ASCII S3 key migration skipped: {e}")


def _migrate_invite_code_scope():
    """Add scope column to invite_codes table and default existing codes to fitness."""
    import logging
    logger = logging.getLogger(__name__)
    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("invite_codes")}
        if "scope" not in existing:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE invite_codes ADD COLUMN scope VARCHAR(20)"
                ))
                logger.info("Added column invite_codes.scope")
                # Default all existing codes to fitness
                conn.execute(text(
                    "UPDATE invite_codes SET scope = 'fitness' WHERE scope IS NULL"
                ))
                logger.info("Set existing invite codes scope to 'fitness'")
        else:
            # Backfill: if column exists but some codes still NULL, set to fitness
            with engine.begin() as conn:
                result = conn.execute(text(
                    "UPDATE invite_codes SET scope = 'fitness' WHERE scope IS NULL"
                ))
                if result.rowcount > 0:
                    logger.info(f"Backfilled {result.rowcount} invite codes scope to 'fitness'")
    except Exception as e:
        logger.debug(f"invite_codes scope migration skipped: {e}")


def _migrate_workout_session_m1():
    """Add M1 workout session columns: planned_exercises, time_budget, set tracking."""
    import logging
    logger = logging.getLogger(__name__)

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)

        # WorkoutSession columns
        try:
            existing = {c["name"] for c in inspector.get_columns("workout_sessions")}
            with engine.begin() as conn:
                if "planned_exercises" not in existing:
                    conn.execute(text(
                        "ALTER TABLE workout_sessions ADD COLUMN planned_exercises JSON"
                    ))
                    logger.info("Added column workout_sessions.planned_exercises")
                if "time_budget_minutes" not in existing:
                    conn.execute(text(
                        "ALTER TABLE workout_sessions ADD COLUMN time_budget_minutes INTEGER"
                    ))
                    logger.info("Added column workout_sessions.time_budget_minutes")
        except Exception as e:
            logger.debug(f"workout_sessions M1 migration skipped: {e}")

        # ExerciseSet columns
        try:
            existing = {c["name"] for c in inspector.get_columns("exercise_sets")}
            with engine.begin() as conn:
                if "completed_at" not in existing:
                    conn.execute(text(
                        "ALTER TABLE exercise_sets ADD COLUMN completed_at DATETIME"
                    ))
                    logger.info("Added column exercise_sets.completed_at")
                if "exercise_order" not in existing:
                    conn.execute(text(
                        "ALTER TABLE exercise_sets ADD COLUMN exercise_order INTEGER"
                    ))
                    logger.info("Added column exercise_sets.exercise_order")
                if "is_skipped" not in existing:
                    conn.execute(text(
                        "ALTER TABLE exercise_sets ADD COLUMN is_skipped BOOLEAN DEFAULT 0"
                    ))
                    logger.info("Added column exercise_sets.is_skipped")
        except Exception as e:
            logger.debug(f"exercise_sets M1 migration skipped: {e}")
    except Exception as e:
        logger.debug(f"Workout M1 migration skipped: {e}")


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


def seed_feature_access():
    """Ensure FeatureAccess rows exist for all features with display metadata."""
    from .db_models.feature_access import FeatureAccess
    import logging

    logger = logging.getLogger(__name__)

    FEATURES = {
        "badminton": {
            "access_mode": "per_user", "default_on_signup": False, "requestable": True,
            "display_name": "Badminton Analysis", "icon": "\U0001f3f8",
            "description": "Upload videos or stream live for real-time shot detection, movement tracking, and coaching insights.",
        },
        "pushup": {
            "access_mode": "per_user", "default_on_signup": True, "requestable": True,
            "display_name": "Pushup Challenge", "icon": "\U0001f4aa",
            "description": "Test your max pushup reps with live pose detection and real-time form feedback.",
        },
        "squat": {
            "access_mode": "per_user", "default_on_signup": True, "requestable": True,
            "display_name": "Squat Challenge", "icon": "\U0001f9ce",
            "description": "Full, half, and hold squat challenges with AI-powered form analysis.",
        },
        "plank": {
            "access_mode": "per_user", "default_on_signup": False, "requestable": True,
            "display_name": "Plank Challenge", "icon": "\U0001f9d8",
            "description": "Hold your plank as long as you can with real-time pose tracking and form scoring.",
        },
        "mimic": {
            "access_mode": "per_user", "default_on_signup": False, "requestable": True,
            "display_name": "MoveMatch", "icon": "\U0001f57a",
            "description": "Mirror dance moves from reels and videos in real-time. Perfect for learning Zumba, choreography, and trending dances.",
        },
        "workout": {
            "access_mode": "per_user", "default_on_signup": True, "requestable": True,
            "display_name": "AI Fitness Coach", "icon": "\U0001f3cb",
            "description": "Personalized workout plans, exercise library, and AI coaching for your fitness journey.",
        },
    }

    db = SessionLocal()
    try:
        for name, defaults in FEATURES.items():
            existing = db.query(FeatureAccess).filter(
                FeatureAccess.feature_name == name
            ).first()
            if not existing:
                row = FeatureAccess(
                    feature_name=name,
                    access_mode=defaults["access_mode"],
                    default_on_signup=defaults["default_on_signup"],
                    requestable=defaults.get("requestable", True),
                    display_name=defaults.get("display_name"),
                    description=defaults.get("description"),
                    icon=defaults.get("icon"),
                )
                db.add(row)
                logger.info(f"Seeded feature_access for {name}")
            elif not existing.display_name:
                existing.display_name = defaults.get("display_name")
                existing.description = defaults.get("description")
                existing.icon = defaults.get("icon")
                existing.requestable = defaults.get("requestable", True)
                logger.info(f"Updated feature_access display metadata for {name}")
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Failed to seed feature_access: {e}")
    finally:
        db.close()


def _migrate_add_workout_to_existing_users():
    """Backfill: add 'workout' to enabled_features for all existing users."""
    import logging
    import json
    logger = logging.getLogger(__name__)

    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            rows = conn.execute(text(
                "SELECT id, enabled_features FROM users WHERE enabled_features IS NOT NULL"
            )).fetchall()

            for row in rows:
                user_id = row[0]
                features = row[1]
                if isinstance(features, str):
                    features = json.loads(features)
                if features is None:
                    features = []
                if "workout" not in features:
                    features.append("workout")
                    conn.execute(text(
                        "UPDATE users SET enabled_features = :features WHERE id = :uid"
                    ), {"features": json.dumps(features), "uid": user_id})

            logger.info("Backfilled 'workout' feature to existing users")
    except Exception as e:
        logger.debug(f"Workout feature backfill skipped: {e}")


def _migrate_exercise_progression():
    """Create exercise_progressions table and add form_score to exercise_sets."""
    import logging
    logger = logging.getLogger(__name__)

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        # The table is created by Base.metadata.create_all() above,
        # but we need to add form_score column to exercise_sets
        if "exercise_sets" in tables:
            existing = {c["name"] for c in inspector.get_columns("exercise_sets")}
            if "form_score" not in existing:
                with engine.begin() as conn:
                    conn.execute(text(
                        "ALTER TABLE exercise_sets ADD COLUMN form_score INTEGER"
                    ))
                    logger.info("Added column exercise_sets.form_score")
    except Exception as e:
        logger.debug(f"exercise_progression migration skipped: {e}")


def _migrate_exercise_demo_video():
    """Add demo_video_url column to exercises and populate YouTube Shorts URLs."""
    import logging
    logger = logging.getLogger(__name__)

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        if "exercises" not in inspector.get_table_names():
            return
        existing = {c["name"] for c in inspector.get_columns("exercises")}
        if "demo_video_url" not in existing:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE exercises ADD COLUMN demo_video_url VARCHAR(512)"))
                logger.info("Added column exercises.demo_video_url")

        # Populate YouTube Shorts URLs — 118 exercises
        YOUTUBE_URLS = {
            # Compound (44)
            "arnold-press": "https://www.youtube.com/shorts/6K_N9AGhItQ",
            "barbell-row": "https://www.youtube.com/shorts/phVtqawIgbk",
            "barbell-squat": "https://www.youtube.com/shorts/MLoZuAkIyZI",
            "barbell-thruster": "https://www.youtube.com/shorts/XvhRYWgekT4",
            "battle-ropes": "https://www.youtube.com/shorts/X5g7P_M8Wo4",
            "bench-press": "https://www.youtube.com/shorts/hWbUlkb5Ms4",
            "bulgarian-split-squat": "https://www.youtube.com/shorts/Q20qIs79tJc",
            "cable-pull-through": "https://www.youtube.com/shorts/dcHyetTdY_I",
            "chest-press-machine": "https://www.youtube.com/shorts/JsQd_KYl4w8",
            "chest-supported-row": "https://www.youtube.com/shorts/czoQ_ncuqqI",
            "chin-up": "https://www.youtube.com/shorts/Oi3bW9nQmGI",
            "close-grip-bench-press": "https://www.youtube.com/shorts/4yKLxOsrGfg",
            "deadlift": "https://www.youtube.com/shorts/ZaTM37cfiDs",
            "decline-bench-press": "https://www.youtube.com/shorts/EdDqD4aKwxM",
            "dips": "https://www.youtube.com/shorts/ci5tcFgIntI",
            "dumbbell-snatch": "https://www.youtube.com/shorts/rCVmr5bgI7c",
            "farmers-walk": "https://www.youtube.com/shorts/1uOs1hP3u4A",
            "front-squat": "https://www.youtube.com/shorts/_qv0m3tPd3s",
            "good-morning": "https://www.youtube.com/shorts/7cpldMZjLOs",
            "hack-squat": "https://www.youtube.com/shorts/g9i05umL5vc",
            "hip-thrust": "https://www.youtube.com/shorts/8BPi7X21BhA",
            "incline-bench-press": "https://www.youtube.com/shorts/98HWfiRonkE",
            "incline-dumbbell-press": "https://www.youtube.com/shorts/8fXfwG4ftaQ",
            "kettlebell-swing": "https://www.youtube.com/shorts/aSYap2yhW8s",
            "lat-pulldown": "https://www.youtube.com/shorts/bNmvKpJSWKM",
            "leg-press": "https://www.youtube.com/shorts/nDh_BlnLCGc",
            "lunges": "https://www.youtube.com/shorts/1cS-6KsJW9g",
            "pendlay-row": "https://www.youtube.com/shorts/tYxEGi7ir4I",
            "power-clean": "https://www.youtube.com/shorts/HFKsnymM_R4",
            "pull-up": "https://www.youtube.com/shorts/ym1V5H35IpA",
            "romanian-deadlift": "https://www.youtube.com/shorts/5rIqP63yWFg",
            "seated-cable-row": "https://www.youtube.com/shorts/qD1WZ5pSuvk",
            "seated-row-machine": "https://www.youtube.com/shorts/DHA7QGDa2qg",
            "shoulder-press": "https://www.youtube.com/shorts/hIcHJ4xP9Ng",
            "single-arm-dumbbell-row": "https://www.youtube.com/shorts/qN54-QNO1eQ",
            "sled-push": "https://www.youtube.com/shorts/Qw8q55JR5VY",
            "smith-machine-squat": "https://www.youtube.com/shorts/GkiiLtJMg9g",
            "step-up": "https://www.youtube.com/shorts/EswvBNNHsRg",
            "stiff-leg-deadlift": "https://www.youtube.com/shorts/4ZEZd1zVJzE",
            "sumo-deadlift": "https://www.youtube.com/shorts/k_jHUVBU-T0",
            "sumo-squat": "https://www.youtube.com/shorts/ihvHG1QH654",
            "t-bar-row": "https://www.youtube.com/shorts/8pR3JoZ0iBU",
            "turkish-get-up": "https://www.youtube.com/shorts/g5dwOlGGfmU",
            "upright-row": "https://www.youtube.com/shorts/U-KG4oahSLA",
            # Bodyweight (32)
            "ab-wheel-rollout": "https://www.youtube.com/shorts/MinlHnG7j4k",
            "bear-crawl": "https://www.youtube.com/shorts/LCVMqEmgglo",
            "bicycle-crunch": "https://www.youtube.com/shorts/NWzlS1Lp1e8",
            "bodyweight-squat": "https://www.youtube.com/shorts/eFEVKmp3M4g",
            "box-jump": "https://www.youtube.com/shorts/HJZh-12p6vg",
            "burpee": "https://www.youtube.com/shorts/FUJTlYHJdg8",
            "crunch": "https://www.youtube.com/shorts/dkGwcfo9zto",
            "dead-bug": "https://www.youtube.com/shorts/x-BStnplCYg",
            "decline-sit-up": "https://www.youtube.com/shorts/dwB9Rp_patE",
            "diamond-push-up": "https://www.youtube.com/shorts/PPTj-MW2tcs",
            "donkey-kick": "https://www.youtube.com/shorts/YoOlLusFMYU",
            "fire-hydrant": "https://www.youtube.com/shorts/BLx5wSzafxg",
            "glute-bridge": "https://www.youtube.com/shorts/R6n608M3czU",
            "hanging-leg-raise": "https://www.youtube.com/shorts/2n4UqRIJyk4",
            "high-knees": "https://www.youtube.com/shorts/d9kQK5Ds0wo",
            "hollow-body-hold": "https://www.youtube.com/shorts/Mjeur54Z0wI",
            "jump-rope": "https://www.youtube.com/shorts/Nssl3QZL6L8",
            "jump-squat": "https://www.youtube.com/shorts/eFEVKmp3M4g",
            "jumping-jacks": "https://www.youtube.com/shorts/7Pxr4xOrhNk",
            "mountain-climber": "https://www.youtube.com/shorts/hZb6jTbCLeE",
            "nordic-curl": "https://www.youtube.com/shorts/1IIavrSbEvo",
            "plank": "https://www.youtube.com/shorts/v25dawSzRTM",
            "push-up": "https://www.youtube.com/shorts/_YrJc-kTYA0",
            "russian-twist": "https://www.youtube.com/shorts/-BzNffL_6YE",
            "side-plank": "https://www.youtube.com/shorts/wP7xBF-LZxs",
            "single-leg-calf-raise": "https://www.youtube.com/shorts/PJGXyldAWk4",
            "sissy-squat": "https://www.youtube.com/shorts/AYN-U5nZieY",
            "superman": "https://www.youtube.com/shorts/w5WIZ-rY9NQ",
            "tricep-dip-bench": "https://www.youtube.com/shorts/9llvBAV4RHI",
            "v-up": "https://www.youtube.com/shorts/BNIPC_HaXWQ",
            "wall-sit": "https://www.youtube.com/shorts/S_SmgeQ7hiU",
            "wide-grip-push-up": "https://www.youtube.com/shorts/TEGkpxBvU_Y",
            # Isolation (34)
            "abductor-machine": "https://www.youtube.com/shorts/01HilwRf8m8",
            "adductor-machine": "https://www.youtube.com/shorts/fwpMYCWdUNY",
            "barbell-shrug": "https://www.youtube.com/shorts/MlqHEfydPpE",
            "bicep-curl": "https://www.youtube.com/shorts/MKWBV29S6c0",
            "cable-crossover": "https://www.youtube.com/shorts/M97ra0UR-40",
            "cable-crunch": "https://www.youtube.com/shorts/K2m0jj6RfYg",
            "cable-curl": "https://www.youtube.com/shorts/CrbTqNOlFgE",
            "cable-fly": "https://www.youtube.com/shorts/I-Ue34qLxc4",
            "cable-lateral-raise": "https://www.youtube.com/shorts/f_OGBg2KxgY",
            "calf-raise": "https://www.youtube.com/shorts/baEXLy09Ncc",
            "concentration-curl": "https://www.youtube.com/shorts/TYrurDZTj9I",
            "donkey-calf-raise": "https://www.youtube.com/shorts/a-x_NR-ibos",
            "dumbbell-fly": "https://www.youtube.com/shorts/rk8YayRoTRQ",
            "dumbbell-shrug": "https://www.youtube.com/shorts/rFsSeClGnNA",
            "dumbbell-tricep-kickback": "https://www.youtube.com/shorts/3Bv1n7-DN7c",
            "face-pull": "https://www.youtube.com/shorts/qEyoBOpvqR4",
            "front-raise": "https://www.youtube.com/shorts/1lXa528j0Vs",
            "glute-kickback": "https://www.youtube.com/shorts/n-cgsNePyFo",
            "hammer-curl": "https://www.youtube.com/shorts/lmIo_gVE8T4",
            "hyperextension": "https://www.youtube.com/shorts/EBui4Bt5N7o",
            "incline-dumbbell-curl": "https://www.youtube.com/shorts/XhIsIcjIbCw",
            "incline-dumbbell-fly": "https://www.youtube.com/shorts/kIpagzRxFPo",
            "lateral-raise": "https://www.youtube.com/shorts/JMt_uxE8bBc",
            "leg-curl": "https://www.youtube.com/shorts/_lgE0gPvbik",
            "leg-extension": "https://www.youtube.com/shorts/uM86QE59Tgc",
            "overhead-tricep-extension": "https://www.youtube.com/shorts/b5le--KkyH0",
            "pec-deck": "https://www.youtube.com/shorts/fgXSA2-o0NM",
            "preacher-curl": "https://www.youtube.com/shorts/fgYBENCgIME",
            "reverse-curl": "https://www.youtube.com/shorts/ZG2n5IcYIcY",
            "reverse-fly": "https://www.youtube.com/shorts/-TKqxK7-ehc",
            "seated-calf-raise": "https://www.youtube.com/shorts/ar8nav0jGoE",
            "seated-leg-curl": "https://www.youtube.com/shorts/NxPR7G_YNHI",
            "skull-crusher": "https://www.youtube.com/shorts/K3mFeNz4e3w",
            "tricep-pushdown": "https://www.youtube.com/shorts/fehf9ZV0tHY",
            # Cardio & Flexibility (8)
            "ankle-mobility-drill": "https://www.youtube.com/shorts/m6J-9oQ9lHQ",
            "band-shoulder-dislocates": "https://www.youtube.com/shorts/gXE-gVzYD9w",
            "cat-cow-stretch": "https://www.youtube.com/shorts/2of247Kt0tU",
            "childs-pose": "https://www.youtube.com/shorts/1ygQrW_0MZY",
            "foam-roll": "https://www.youtube.com/shorts/7_m0E0N-PtY",
            "hip-flexor-stretch": "https://www.youtube.com/shorts/ktgtEWGhFd8",
            "pigeon-pose": "https://www.youtube.com/shorts/AI5A1PRYX7E",
            "worlds-greatest-stretch": "https://www.youtube.com/shorts/7XheaZERvBQ",
        }

        with engine.begin() as conn:
            updated = 0
            for slug, url in YOUTUBE_URLS.items():
                result = conn.execute(text(
                    "UPDATE exercises SET demo_video_url = :url WHERE slug = :slug"
                ), {"url": url, "slug": slug})
                if result.rowcount > 0:
                    updated += 1
            if updated:
                logger.info(f"Populated {updated} exercise demo video URLs")
    except Exception as e:
        logger.error(f"exercise demo_video migration failed: {e}")


def seed_exercises():
    """Seed the exercises table from exercise_seed module."""
    from .features.workout.services.exercise_seed import seed_exercises as _seed
    _seed(engine)


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
