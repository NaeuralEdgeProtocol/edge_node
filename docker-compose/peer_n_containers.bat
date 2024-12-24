@echo off
setlocal enabledelayedexpansion

REM Hardcoded number of containers
set NUM_CONTAINERS=5
set NUM_SUPERVISORS=2
set CONTAINER_IMAGE=naeural/edge_node:develop

REM Generic names for containers and edge nodes
set GENERIC_EDGE_NODE_ID=cluster_nen_
set GENERIC_CONTAINER_ID=naeural_0
set GENERIC_CONTAINER_VOLUME=0naeural_0

REM Generate the list of container IDs dynamically
for /l %%i in (1,1,%NUM_CONTAINERS%) do (
    REM Generic container ID and edge node ID
    set CONTAINER_IDS[%%i]=!GENERIC_CONTAINER_VOLUME!%%i
    set EDGE_NODE_IDS[%%i]=!GENERIC_EDGE_NODE_ID!%%i
    set CONTAINER_VOLUMES[%%i]=!GENERIC_CONTAINER_VOLUME!%%i

    REM Check if the container is a supervisor
    if %%i leq %NUM_SUPERVISORS% (
        set CONTAINER_IS_SUPERVISOR[%%i]=true
    ) else (
        set CONTAINER_IS_SUPERVISOR[%%i]=false
    )
)

SET PATH_TO_LOCAL_ADDRESS_FILE=/edge_node/_local_cache/_data/local_address.txt


REM Loop over containers to extract local_address.txt and parse it
for /l %%i in (1, 1, %NUM_CONTAINERS%) do (
    REM Get the container's local_address.txt file
    echo Extracting local address for container !EDGE_NODE_IDS[%%i]! from !PATH_TO_LOCAL_ADDRESS_FILE!
    for /f "tokens=1,2" %%a in ('docker exec !CONTAINER_IDS[%%i]! cat !PATH_TO_LOCAL_ADDRESS_FILE!') do (
        REM Store the address in the NODE_ADDRESSES array
        set NODE_ADDRESSES[%%i]=%%a
    )
)

echo Local addresses for all containers:

REM Generate authorized_addrs file for each container
for /l %%i in (1, 1, %NUM_CONTAINERS%) do (
    REM Set the path to the authorized_addrs file
    set AUTH_PATH="./!CONTAINER_VOLUMES[%%i]!/authorized_addrs"

    REM Clear the file.
    echo. > !AUTH_PATH!

    echo Authorized addresses for container !EDGE_NODE_IDS[%%i]!:

    REM Iterate through all the containers
    for /l %%j in (1, 1, %NUM_CONTAINERS%) do (
        if %%i==%%j (
            REM Skip the current container
        ) else (
            if !CONTAINER_IS_SUPERVISOR[%%j]! == true (
                REM Supervisors are always authorized
                echo   !NODE_ADDRESSES[%%j]!  !EDGE_NODE_IDS[%%j]!
                echo !NODE_ADDRESSES[%%j]!  !EDGE_NODE_IDS[%%j]! >> !AUTH_PATH!
            ) else (
                REM Custom logic for authorizing non-supervisor containers.
                set /a i_parity=%%i %% 2
                set /a j_parity=%%j %% 2
                if !i_parity! == !j_parity! (
                    REM Containers with the same parity are authorized
                    echo   !NODE_ADDRESSES[%%j]!  !EDGE_NODE_IDS[%%j]!
                    echo !NODE_ADDRESSES[%%j]!  !EDGE_NODE_IDS[%%j]! >> !AUTH_PATH!
                )
            )
        )
    )
)

