docker build -t local_node -f Dockerfile_dev .
docker run --gpus=all --env-file=.env -v naeural_vol:/exe_eng/_local_cache local_node