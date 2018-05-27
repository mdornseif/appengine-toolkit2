.. _gaetk2-deployment:

Deployment, CI & CD
===================

Outline
-------

For AppEngine Python Standard Environment you have to provide a full Setup including all (most) libraries you want to use. So `building` consists of pulling in all needed python libraries. If you use any complex Javascript  building also includes running webpack to construct the needed javascript bundles.

`Checking` means runing code analysys tools to find bugs and ensure coding standards are adhered to.

`Testing` includes running `unit tests` for Python and Javascript to check single components whithout any test to live data and APIs.
`Acceptance testing` we run against a complete app installed on a special App Engine `version` but with access to all life data.

`Deployment` is the installation of the App on Google App Engine. Be it on a Development or Production Version.

`Releasing` includes automated `Checking` and `Testing` of software and preparing it for `Deployment` in Production.

Production deployment is done via an `blue/green schema <https://martinfowler.com/bliki/BlueGreenDeployment.html>`_ where you deploy to an inactive version and then migrate traffic from the active version to the newly deployed version. In case of issues you can quickly migrate the traffic back. Google App engine is very well suited to this approach.

All this steps are meant to be run inside Docker Containers to ensure repeatable and stable infrastructure. Services like Circle CI or Travis CI can provide automation for this steps.

All the semi-automated and automated steps are handled via `doit <http://pydoit.org>`_, a Python based `make` alternative.



Docker Primer
-------------

You might think of the Docker container engine as a light weight VM system. It downloads the containers (think "VM") it needs automatically from the internet and can give you shell access to the container.

The `mdornseif/gae <https://hub.docker.com/r/mdornseif/gae/>`_ image is well suited to build, test and deploy for and to Google App Engine Python Standard Environment.

If you have `Docker installed <https://docs.docker.com/docker-for-mac/>`_, it is easy to get a shell inside the container ready for building::

    docker run --rm -ti mdornseif/gae bash

Docker containers are destroyed after each run so do not save anything important in them.
To keep data permanently store it on the host system. To exchange data between the container and your host computer you can mount a directory via `-v` (mount)::

    docker run  --rm -ti -v "$(pwd)":/hostdir mdornseif/gae bash
    ls /hostdir
    touch /hostdir/test.txt

When you want to checkout something from inside the docker container you
need SSH keys. It is somewhat difficult to that.

.. warning::

    The way described here is inherently insecure. Do only use it unless you are the only user on the host and the host does only run trusted processes. Also only run a single trusted container.

If you have your SSH-Key for accessing github in ``~/.ssh/id_github_key`` you can pass it into the container via this command::

   docker run --rm --env CHECKOUT_KEY="`cat ~/.ssh/id_github_key`" -ti mdornseif/gae bash

This will make the key available inside the image under ``~/.ssh/id_rsa`` where git/ssh should pick it up automatically. You can put additional variables into the file ``env.list`` and use it via ``--env-file env.list``.
OR just add them to the command line via ``--env NAME=valiue``.

Most usuable is ``CIRCLE_REPOSITORY_URL`` where you can provide the repository to be checked out on start. ``CIRCLE_BRANCH`` selects the branch to check out. The usual Setup would be something like this::

	echo "CIRCLE_REPOSITORY_URL=git@github.com:myUser/myProj.git" > env.list
	echo "CIRCLE_BRANCH=testing" >> env.list
	docker run --rm --env-file env.list --env CHECKOUT_KEY="`cat ~/.ssh/id_github_key`" -ti mdornseif/gae bash


Repository Structure
--------------------

It is assumed that you work based the lines of the `GitHub Flow <http://scottchacon.com/2011/08/31/github-flow.html>`_ (See also `here <https://guides.github.com/introduction/flow/>`_.

* Anything in the ``master`` branch should be ready for production
* To work on something new, create a descriptively named branch
* regularly push your york to the server to profit from automated testing
* For help or feedback, or the branch is ready for merging, open a pull request
* Once ``master`` has something significant new, a release should follod imediately.

There ist a ``staging`` branch for reviewing features which are not ready for production. This is our way to get arround using [feature flags](https://featureflags.io).

The ``hotfix`` branch is for getting around usually processes in emergencies.

In addition there is a ``release`` branch which is meant for a final Acceptance-Check and to ensure certain steps like writing a change log and informing the user base is done.

So the branches with special meaning are::
* master - where your stable code lives, automatically deployed to http://master-dot-yourapp.appspot.com
* release - where your production code lives, automatically deployed to http://release-dot-yourapp.appspot.com
* staging - testing of certain features http://staging-dot-yourapp.appspot.com
* hotfix - Experiments used in production http://hotfix-dot-yourapp.appspot.com


Checks
------

.. todo::

	docker run --env-file env.list --env CHECKOUT_KEY="`cat yourkey`" -ti mdornseif/gae doit check

	If you want to run a somewhat less strict code analysis, use ``doit CICHECK`.


Unit Tests
----------


CI - Continues Integration
--------------------------

If you have a docker based CI system this works very well with the gaetk2 deployment strategy. For example a Circle CI configuration would look like this::

	version: 2
	defaults: &defaults
	  working_directory: ~/repo/
	  docker:
	    # - image: circleci/python:2.7.15-node-browsers
	    - image: mdornseif/gae:stable
	jobs:
	  build:
	    <<: *defaults
	    steps:
	      - checkout:
	          path: ~/repo
	      - run: doit -f dodo-new.py submodules
	      - run: doit -f dodo-new.py BUILD
	      - run: doit -f dodo-new.py CICHECK CITEST
	  deploy:
	    <<: *defaults
	    steps:
	      - checkout:
	          path: ~/repo
	      - run: doit -f dodo-new.py submodules
	      - run: doit -f dodo-new.py BUILD
	      # see https://circleci.com/docs/2.0/google-auth/
	      # https://circleci.com/docs/1.0/deploy-google-app-engine/
	      # add key at https://circleci.com/gh/hudora/huWaWi/edit#env-vars
	      - run: echo $GCLOUD_SERVICE_KEY | base64 --decode --ignore-garbage > ${HOME}/gcloud-service-key.json > ~/gcloud-service-key.json
	      - run: gcloud auth activate-service-account --key-file ${HOME}/gcloud-service-key.json
	      - deploy: gcloud -q app deploy ./app.yaml --project=huwawi2 --version=$CIRCLE_BRANCH --no-promote
	  test_acceptance:
	    <<: *defaults
	    steps:
	      - checkout:
	          path: ~/repo
	      - run: doit -f dodo-new.py submodules
	      - run: doit -f dodo-new.py BUILD
	      - run: doit -f dodo-new.py CITEST_ACCEPTANCE

	workflows:
	  version: 2
	  build-and-deploy:
	    jobs:
	      - build
	      - deploy:
	          requires:
	            - build
	          filters:
	            branches:
	              only:
	                - staging
	                - hotfix
	                - master
	                - release
	      - test_acceptance:
	          requires:
	            - build
	            - deploy
	          filters:
	            branches:
	              only:
	                - staging
	                - hotfix
	                - master
	                - release

That's all.



Automated Deployments
---------------------

Create a Service Account at https://console.cloud.google.com/iam-admin/serviceaccounts/project?project=huwawi2 Permissions needed are `App Engine -> App Engine Deployer` and `Storage -> Storag Object Admin`. (See http://filez.foxel.org/2d1Q2W0y2E33). Download the Key as JSON, Pass it throu base64 and add it as Circle CI environment variable `GCLOUD_SERVICE_KEY` at https://circleci.com/gh/hudora/huWaWi/edit#env-vars
