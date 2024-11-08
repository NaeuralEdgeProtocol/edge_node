FROM aidamian/base_edge_node:x86_64-py3.10.12-th2.3.1.cu121-tr4.43.3

WORKDIR /edge_node

COPY  . /edge_node

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
RUN pip install --no-cache-dir kmonitor naeural_client decentra-vision python-telegram-bot
## END do not move

RUN pip install --no-cache-dir --no-deps naeural-core
