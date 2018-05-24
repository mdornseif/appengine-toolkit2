#!/bin/sh
docker build --tag gae .
docker tag gae mdornseif/gae:stable
docker push mdornseif/gae:stable
docker run --rm --env-file env.list --env CHECKOUT_KEY="`cat ~/.ssh/id_github_key`" -ti mdornseif/gae bash
docker run --rm -ti mdornseif/gae bash
