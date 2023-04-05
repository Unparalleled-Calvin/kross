### kross

This is a simple implementation of a service discovery system across multiple kubernetes clusters.

#### Usage

- use config.template.yaml to adjust to your env
- build a docker image
- create a serviceaccount with enough authorities
- create a Pod with the image and sa
- run main.py