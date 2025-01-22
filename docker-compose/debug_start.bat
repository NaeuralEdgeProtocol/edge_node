@echo off

REM First we need to build the `local_edge_node` image
cd ..
docker build -t local_edge_node -f Dockerfile_dev .
cd docker-compose

copy debug-docker-compose.yaml docker-compose.yaml

REM Start the containers
docker-compose up -d

docker-compose logs -f -n 1000 naeural_02

echo Containers are starting...
