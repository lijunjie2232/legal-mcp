#!/bin/bash

# Elasticsearch Docker Setup and Configuration Script
# For legal document storage and query project

set -e  # Exit immediately on error

ES_PASSWORD="elawstic"
KIBANA_SYSTEM_PASSWORD="kibana_pass"
ES_CONTAINER_NAME="es01"
ES_VERSION="9.3.4"
ES_PORT=9200

# create es_data
# if [ ! -d "../es_data" || ! -d "../es_data/data" || ! -d "../es_data/logs" || ! -d "../es_data/config" || ! -d "../es_data/snapshots" ]
# then
#   mkdir -p ../es_data/{data,logs,config,snapshots}
# fi

chmod -R 777 ../es_data

echo "=========================================="
echo "Elasticsearch Docker Environment Setup"
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed, please install Docker first"
    exit 1
fi

# Check if docker compose is available
if ! command -v docker compose &> /dev/null; then
    echo "Error: Docker Compose is not installed, please install Docker Compose first"
    exit 1
fi

echo ""
echo "Step 1: Checking and stopping existing containers..."
if docker ps -a --format '{{.Names}}' | grep -q "^${ES_CONTAINER_NAME}$"; then
    echo "Found existing container ${ES_CONTAINER_NAME}, stopping and removing..."
    docker compose down
    echo "✓ Old container cleaned up"
else
    echo "✓ No existing containers"
fi

echo ""
echo "Step 2: Starting Elasticsearch container..."
docker compose up -d
echo "✓ Elasticsearch container started"

echo ""
echo "Step 3: Waiting for Elasticsearch to start..."
MAX_WAIT=60
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:${ES_PORT}/ > /dev/null 2>&1; then
        echo "✓ Elasticsearch is ready"
        break
    fi
    echo "  Waiting... (${WAIT_COUNT}/${MAX_WAIT})"
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 2))
done

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo "Error: Elasticsearch startup timeout"
    docker logs ${ES_CONTAINER_NAME}
    exit 1
fi

echo ""
echo "Step 4: Installing Kuromoji plugin..."
# Kuromoji is a Japanese tokenizer plugin for Japanese text analysis
echo "Downloading and installing analysis-kuromoji plugin..."
docker exec ${ES_CONTAINER_NAME} /usr/share/elasticsearch/bin/elasticsearch-plugin install analysis-kuromoji --batch
echo "✓ Kuromoji plugin installed"

# Restart Elasticsearch to load the plugin
echo "Restarting Elasticsearch to load plugin..."
docker compose restart > /dev/null 2>&1
echo "Waiting for Elasticsearch to restart (about 30 seconds)..."
sleep 30

# Wait for service to be ready again
echo "Verifying service is ready again..."
MAX_WAIT=60
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:${ES_PORT}/ > /dev/null 2>&1; then
        echo "✓ Elasticsearch restart completed and ready"
        break
    fi
    echo "  Waiting for restart... (${WAIT_COUNT}/${MAX_WAIT})"
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 2))
done

echo ""
echo "Step 5: Setting elastic user password..."
# First use elasticsearch-reset-password to generate a temporary password
echo "Generating temporary password for elastic user..."
TEMP_PASSWORD=$(docker exec -i ${ES_CONTAINER_NAME} /usr/share/elasticsearch/bin/elasticsearch-reset-password -s -a -b -u elastic)
# TEMP_PASSWORD=$(echo "$TEMP_PASSWORD_OUTPUT" | grep -oP 'New value:\s+\K\S+')

if [ -z "$TEMP_PASSWORD" ]; then
    echo "✗ Unable to get temporary password for elastic user"
    echo "Output: $TEMP_PASSWORD_OUTPUT"
    exit 1
fi

echo "✓ Temporary password for elastic user generated"

# Use temporary password via curl to set our desired password
echo "Changing elastic user password to: ${ES_PASSWORD}"
curl -s -X POST "http://localhost:${ES_PORT}/_security/user/elastic/_password" \
    -u elastic:${TEMP_PASSWORD} \
    -H "Content-Type: application/json" \
    -d "{\"password\": \"${ES_PASSWORD}\"}" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✓ elastic user password successfully set to: ${ES_PASSWORD}"
else
    echo "✗ Failed to set elastic user password"
    echo "Trying to view logs for more information..."
    docker logs ${ES_CONTAINER_NAME} | tail -20
    exit 1
fi

echo ""
echo "Step 6: Setting kibana_system user password..."
# Set password for kibana_system user
echo "Generating temporary password for kibana_system user..."
KIBANA_TEMP_PASSWORD_OUTPUT=$(docker exec -i ${ES_CONTAINER_NAME} /usr/share/elasticsearch/bin/elasticsearch-reset-password -u kibana_system -b 2>&1)
KIBANA_TEMP_PASSWORD=$(echo "$KIBANA_TEMP_PASSWORD_OUTPUT" | grep -oP 'New value:\s+\K\S+')

if [ -z "$KIBANA_TEMP_PASSWORD" ]; then
    echo "✗ Unable to get temporary password for kibana_system user"
    echo "Output: $KIBANA_TEMP_PASSWORD_OUTPUT"
    exit 1
fi

echo "✓ Temporary password for kibana_system user generated"

# Use temporary password via curl to set our desired password
echo "Changing kibana_system user password to: ${KIBANA_SYSTEM_PASSWORD}"
curl -s -X POST "http://localhost:${ES_PORT}/_security/user/kibana_system/_password" \
    -u elastic:${ES_PASSWORD} \
    -H "Content-Type: application/json" \
    -d "{\"password\": \"${KIBANA_SYSTEM_PASSWORD}\"}" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✓ kibana_system user password successfully set to: ${KIBANA_SYSTEM_PASSWORD}"
else
    echo "✗ Failed to set kibana_system user password"
    echo "Trying to view logs for more information..."
    docker logs ${ES_CONTAINER_NAME} | tail -20
    exit 1
fi

echo ""
echo "Step 7: Verifying connection..."
echo "Testing Elasticsearch connection..."
RESPONSE=$(curl -s -u elastic:${ES_PASSWORD} http://localhost:${ES_PORT}/)
if echo "$RESPONSE" | grep -q "cluster_name"; then
    echo "✓ Connection successful"
    CLUSTER_NAME=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['cluster_name'])" 2>/dev/null || echo "unknown")
    ES_VERSION_NUM=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['version']['number'])" 2>/dev/null || echo "unknown")
    NODE_NAME=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['name'])" 2>/dev/null || echo "unknown")
    echo "  Node name: ${NODE_NAME}"
    echo "  Cluster name: ${CLUSTER_NAME}"
    echo "  ES version: ${ES_VERSION_NUM}"
else
    echo "✗ Connection failed"
    echo "Response: $RESPONSE"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ Elasticsearch environment setup completed!"
echo "=========================================="
echo ""
echo "Access Information:"
echo "  Elasticsearch URL:      http://localhost:${ES_PORT}"
echo "  Elasticsearch Username:   elastic"
echo "  Elasticsearch Password:     ${ES_PASSWORD}"
echo "  Kibana System Username:   kibana_system"
echo "  Kibana System Password:     ${KIBANA_SYSTEM_PASSWORD}"
echo ""
echo "Common Commands:"
echo "  View status:     docker ps"
echo "  View logs:       docker logs ${ES_CONTAINER_NAME}"
echo "  Stop service:    docker compose down"
echo "  Restart service: docker compose restart"
echo "  Test connection: curl -u elastic:${ES_PASSWORD} http://localhost:${ES_PORT}/"
echo ""
