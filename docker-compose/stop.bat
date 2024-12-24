@echo off

REM Stop the containers
docker-compose stop

REM Remove the stopped containers
docker-compose rm -f

echo "Containers have been stopped and removed."
