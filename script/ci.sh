#!/bin/bash
root_path=$(cd $(dirname $0);cd ..; pwd)
image_name="kross"
version="latest"

docker build -t ${image_name}:${version} ${root_path}
docker tag ${image_name}:${version} calvincui/${image_name}:${version}
docker push calvincui/${image_name}:${version}
