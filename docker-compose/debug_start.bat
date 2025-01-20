@echo off

copy debug-docker-compose.yaml docker-compose.yaml


REM Start the containers
docker-compose up -d

docker-compose logs -f -n 1000 naeural_02

echo Containers are starting...
