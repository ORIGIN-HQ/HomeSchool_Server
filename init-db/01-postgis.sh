#!/bin/bash
set -e

# This script runs when the PostgreSQL container is first created
# It ensures PostGIS is properly enabled

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Enable PostGIS extension
    CREATE EXTENSION IF NOT EXISTS postgis;
    
    -- Enable PostGIS topology
    CREATE EXTENSION IF NOT EXISTS postgis_topology;
    
    -- Verify PostGIS is working
    SELECT PostGIS_Version();
    
    -- Grant necessary permissions
    GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;
EOSQL

echo "PostGIS extensions enabled successfully"