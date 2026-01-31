"""
Test script to verify database setup and PostGIS functionality.
Run this after setting up the database to ensure everything works.

Usage:
    python test_db_setup.py
"""
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import get_settings


def test_database_connection():
    """Test basic database connection."""
    print("\n🔍 Testing database connection...")
    try:
        settings = get_settings()
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
            
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def test_postgis_enabled():
    """Test if PostGIS extension is enabled."""
    print("\n🗺️  Testing PostGIS extension...")
    try:
        settings = get_settings()
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT PostGIS_Version();"))
            version = result.scalar()
            print(f"✅ PostGIS enabled: version {version}")
            return True
    except Exception as e:
        print(f"❌ PostGIS not enabled: {e}")
        return False


def test_tables_exist():
    """Test if all required tables exist."""
    print("\n📋 Testing tables...")
    try:
        settings = get_settings()
        engine = create_engine(settings.database_url)
        
        required_tables = ['users', 'parents', 'tutors']
        
        with engine.connect() as conn:
            for table in required_tables:
                result = conn.execute(text(
                    f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}');"
                ))
                exists = result.scalar()
                if exists:
                    print(f"  ✅ Table '{table}' exists")
                else:
                    print(f"  ❌ Table '{table}' missing")
                    return False
        
        print("✅ All required tables exist")
        return True
    except Exception as e:
        print(f"❌ Table check failed: {e}")
        return False


def test_spatial_index():
    """Test if spatial index exists on users.location."""
    print("\n🎯 Testing spatial indexes...")
    try:
        settings = get_settings()
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT indexname FROM pg_indexes WHERE tablename = 'users' AND indexname = 'idx_users_location';"
            ))
            index = result.scalar()
            
            if index:
                print("✅ Spatial index 'idx_users_location' exists")
                return True
            else:
                print("❌ Spatial index 'idx_users_location' not found")
                return False
    except Exception as e:
        print(f"❌ Spatial index check failed: {e}")
        return False


def test_geospatial_operations():
    """Test basic geospatial operations."""
    print("\n🌍 Testing geospatial operations...")
    try:
        settings = get_settings()
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            # Test point creation
            result = conn.execute(text(
                "SELECT ST_AsText(ST_GeomFromText('POINT(36.817223 -1.286389)', 4326));"
            ))
            point = result.scalar()
            assert point == 'POINT(36.817223 -1.286389)'
            print("  ✅ Point creation works")
            
            # Test distance calculation
            result = conn.execute(text("""
                SELECT ST_Distance(
                    ST_GeomFromText('POINT(36.817223 -1.286389)', 4326)::geography,
                    ST_GeomFromText('POINT(36.827223 -1.296389)', 4326)::geography
                );
            """))
            distance = result.scalar()
            assert distance > 0
            print(f"  ✅ Distance calculation works: {distance:.2f} meters")
            
            # Test bounding box
            result = conn.execute(text("""
                SELECT ST_Within(
                    ST_GeomFromText('POINT(36.817223 -1.286389)', 4326),
                    ST_MakeEnvelope(36.8, -1.3, 36.9, -1.2, 4326)
                );
            """))
            within = result.scalar()
            assert within is True
            print("  ✅ Bounding box queries work")
        
        print("✅ All geospatial operations successful")
        return True
    except Exception as e:
        print(f"❌ Geospatial operations failed: {e}")
        return False


def test_session_management():
    """Test SQLAlchemy session management."""
    print("\n🔄 Testing session management...")
    try:
        from app.db import SessionLocal
        
        session = SessionLocal()
        try:
            # Test transaction
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1
            print("✅ Session creation and queries work")
            return True
        finally:
            session.close()
    except Exception as e:
        print(f"❌ Session management failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 DATABASE SETUP VERIFICATION")
    print("=" * 60)
    
    tests = [
        test_database_connection,
        test_postgis_enabled,
        test_tables_exist,
        test_spatial_index,
        test_geospatial_operations,
        test_session_management,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Database is ready.")
        print("\nNext steps:")
        print("  1. Start the server: uvicorn app.main:app --reload")
        print("  2. Check health: curl http://localhost:8000/health")
        print("  3. Proceed to Issue #3: Google OAuth Authentication")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        print("\nCommon fixes:")
        print("  - Ensure PostgreSQL is running: docker-compose up -d")
        print("  - Check .env DATABASE_URL is correct")
        print("  - Run migrations: alembic upgrade head")
        return 1


if __name__ == "__main__":
    sys.exit(main())

