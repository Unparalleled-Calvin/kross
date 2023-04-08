#!/bin/bash
root_path=$(cd $(dirname $0); pwd)
image_name="simple-server"
version="latest"

docker build -t ${image_name}:${version} ${root_path}
docker tag ${image_name}:${version} easzlab.io.local:5000/${image_name}:${version}
docker push easzlab.io.local:5000/${image_name}:${version}
