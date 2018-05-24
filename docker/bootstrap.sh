#!/bin/sh
set -e
set -x

# Workaround old docker images with incorrect $HOME
# check https://github.com/docker/docker/issues/2968 for details
if [ "${HOME}" = "/" ]
then
  export HOME=$(getent passwd $(id -un) | cut -d: -f6)
fi

mkdir -p ~/.ssh

echo 'github.com ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==
bitbucket.org ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAubiN81eDcafrgMeLzaFPsw2kNvEcqTKl/VqLat/MaB33pZy0y3rJZtnqwR2qOOvbwKZYKiEO1O6VqNEBxKvJJelCq0dTXWT5pbO2gDXC6h6QDXCaHo6pOHGPUy+YBaGQRGuSusMEASYiWunYN0vCAI8QaXnWMXNMdFP3jHAJH0eDsoiGnLPBlBp4TNm6rYI74nMzgz3B9IikW4WVK+dc8KZJZWYjAuORU3jc1c/NPskD2ASinf8v3xnfXeukU0sJ5N6m5E8VLjObPEO+mN2t/FZTMZLiFqPWc/ALSqnMnnhwrNi2rbfg/rd/IpL8Le3pSBne8+seeFVBoGqzHM9yXw==
' >> ~/.ssh/known_hosts

(umask 077; touch ~/.ssh/id_rsa)
chmod 0600 ~/.ssh/id_rsa
(cat <<EOF > ~/.ssh/id_rsa
$CHECKOUT_KEY
EOF
)

if [ -n "$GCLOUD_SERVICE_KEY" ]
then
  (umask 077; touch ~/gcloud-service-key.json)
  chmod 0600 ~/gcloud-service-key.json
  echo $GCLOUD_SERVICE_KEY | base64 --decode --ignore-garbage > ${HOME}/gcloud-service-key.json > ~/gcloud-service-key.json
  sudo /opt/google-cloud-sdk/bin/gcloud auth activate-service-account --key-file ${HOME}/gcloud-service-key.json
  # sudo /opt/google-cloud-sdk/bin/gcloud config set project $GCLOUD_PROJECT
fi

# use git+ssh instead of https
git config --global url."ssh://git@github.com".insteadOf "https://github.com" || true

if [ -n "$CIRCLE_REPOSITORY_URL" ]
then
  echo "cloning $CIRCLE_REPOSITORY_URL"
  if [ -e /home/circleci/repo/.git ]
  then
    cd /home/circleci/repo
    git remote set-url origin "$CIRCLE_REPOSITORY_URL" || true
  else
    mkdir -p /home/circleci/repo
    cd /home/circleci/repo
    git clone --recurse-submodules -j8 "$CIRCLE_REPOSITORY_URL" .
  fi

  if [ -n "$CIRCLE_TAG" ]
  then
    git fetch --force origin "refs/tags/${CIRCLE_TAG}"
  else
    git fetch --force origin "master:remotes/origin/master"
  fi

  if [ -n "$CIRCLE_TAG" ]
  then
    git checkout -q "$CIRCLE_TAG"
  elif [ -n "$CIRCLE_BRANCH" ]
  then
    git checkout -q -B "$CIRCLE_BRANCH"
  fi
  # git reset --hard "$CIRCLE_SHA1"
  echo "set up now"
fi

$@
