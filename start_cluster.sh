#!/bin/bash

# Pull the latest images
docker-compose pull

# Start the containers in detached mode
docker-compose up -d

echo "Containers are starting..."
