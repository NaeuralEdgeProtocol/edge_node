docker build -t local_node -f Dockerfile_devnet .
docker run --rm --gpus=all --env-file=.env -v r1vol:/edge_node/_local_cache local_node