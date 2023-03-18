#!/usr/bin/env bash

if [ -z $1 ]; then
    echo "Usage: $0 <env_file>"
    echo "The env file will have your keys and secrets."
    exit 1
fi

environment=$1

docker run -d --rm --env-file $environment --name riddlr riddlr
