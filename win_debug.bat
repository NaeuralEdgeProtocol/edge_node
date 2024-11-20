docker build -t local_node -f Dockerfile_dev .
docker run --rm --gpus=all --env-file=.env -v naeural_vol:/edge_node/_local_cache local_node