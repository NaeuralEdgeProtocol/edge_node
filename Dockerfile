FROM aidamian/base_edge_node:x86_64-py3.10.12-th2.2.2.cu121-tr4.39.3

WORKDIR /edgenode

COPY  . /edgenode

# set a generic env variable 
ENV AINODE_DOCKER Yes

# set a generic env variable 
ENV AINODE_DOCKER_SOURCE main

# set default Execution Engine id
ENV EE_ID E2dkr

# Temporary fix:
ENV AINODE_ENV $AI_ENV
ENV AINODE_ENV_VER $AI_ENV_VER

ENV TZ=Europe/Bucharest
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# also can use EE_DEVICE to define target such as cuda:0 or cuda:1 instead of cpu
# althouh this is not recommended as it should be in .env file
# ENV EE_DEVICE cuda:0

# configure default config_startup file
ENV EE_CONFIG .config_startup.json

## The following line should NOT be moved to based as it should always be updated
RUN pip install --no-cache-dir kmonitor PyE2 decentra-vision
## END do not move

CMD ["python","device.py"]
