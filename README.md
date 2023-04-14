### kross

This is a simple implementation of a service discovery system across multiple kubernetes clusters.

#### Usage

[to update]

- use config.template.yaml to adjust to your env
- build a docker image
- create a serviceaccount with enough authorities
- create a Pod with the image and sa
- run main.py

#### Files

- manifest
  - kross.yaml: k8s object for kross
- script
  - ci.sh: CI script for kross
- src
  - handler.py: handle k8s svc events
  - item.py: some encodable and decodable objects for svc
  - main.py: load configuration and start the main loop
  - peer.py: check kross peers
  - server.py: process kross basic http API requests
  - store.py: store agent abstract class and implementation
