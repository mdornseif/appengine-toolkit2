#!/bin/sh
cp ../requirements-dev.txt .
cat ../requirements-dev.txt ../requirements-lib.txt | sort -u > requirements-cache.txt
docker build --tag gae .
docker tag gae mdornseif/gae:`date +'%Y.%b'`
docker push mdornseif/gae:`date +'%Y.%b'`
# docker push mdornseif/gae:latest
# docker tag gae mdornseif/gae:stable
# docker push mdornseif/gae:stable
# docker run --rm --env-file env.list --env CHECKOUT_KEY="`cat ~/.ssh/id_github_key`" -ti mdornseif/gae bash
# docker run --rm -ti mdornseif/gae:stable bash
