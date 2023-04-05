#!/bin/bash
root_path=$(cd $(dirname $0);cd ..; pwd)
image_name="kross"
version="latest"

docker build -t ${image_name}:${version} ${root_path}
docker tag ${image_name}:${version} easzlab.io.local:5000/${image_name}:${version}
docker push easzlab.io.local:5000/${image_name}:${version}
