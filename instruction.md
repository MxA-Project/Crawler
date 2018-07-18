1. start redis
2. start multiple tor instances with docker :
    `docker run --rm -it -p 9050:9050 -p 10000:10000 znetstar/tor-router -j NUMBER_INSTANCES -h 10000`
