# This should be able to run all tests for our App Engine Projects
# and also be able to handle automated deployments
# Node is there for Javascript Builds and tests

FROM circleci/python:2.7.16-buster
# Python 2.7.12 is what is running on AppEngine
# so this would be more authentic:
# RUN wget https://www.python.org/ftp/python/2.7.12/Python-2.7.12.tgz && \
#     tar xzf Python-2.7.12.tgz && \
#     rm Python-2.7.12.tgz && \
#     cd Python-2.7.12 && \
#     ./configure && \
#     make install


# See https://github.com/CircleCI-Public/circleci-dockerfiles/blob/master/python/images/2.7.14/node-browsers/Dockerfile
# for inspiration on how to build Browsers for headless testing

# carefull! python packages get installed into system python and not user python
RUN sudo apt-get install -y less graphviz libfreetype6-dev libjpeg-dev zlib1g-dev libtiff-dev \
	&& sudo /bin/sh -c 'echo "deb http://ftp.us.debian.org/debian testing main contrib non-free" >> /etc/apt/sources.list' \
	&& sudo apt-get update \
	&& sudo apt-get install python-pil \
	&& sudo apt-get clean autoclean \
	&& sudo apt-get autoremove --yes \
	&& sudo rm -rf /var/lib/{apt,dpkg,cache,log}/

# RUN \
#	curl -L https://codeclimate.com/downloads/test-reporter/test-reporter-latest-linux-amd64 > ~/cc-test-reporter \
#	&& sudo mv ~/cc-test-reporter /usr/local/bin/cc-test-reporter \
#	&& sudo chmod +x /usr/local/bin/cc-test-reporter

RUN curl -s https://dl.google.com/dl/cloudsdk/release/google-cloud-sdk.tar.gz > /tmp/google-cloud-sdk.tar.gz \
	&& sudo mkdir -p /usr/local/gcloud \
	&& sudo tar -C /usr/local/gcloud -xf /tmp/google-cloud-sdk.tar.gz \
	&& rm /tmp/google-cloud-sdk.tar.gz \
	&& sudo /usr/local/gcloud/google-cloud-sdk/install.sh \
	&& /usr/local/gcloud/google-cloud-sdk/bin/gcloud config set disable_usage_reporting true \
	&& sudo /usr/local/gcloud/google-cloud-sdk/bin/gcloud components install app-engine-python-extras
ENV PATH "$PATH:/usr/local/gcloud/google-cloud-sdk/bin"

# update to a git which can run paralell (-j8) and install py3
# and pseudo-python which needs py3
RUN sudo apt-get update \
		&& sudo apt-get install -y --fix-missing git \
		&& sudo apt-get clean all && sudo rm -Rf /root/.cache
# RUN sudo apt-get install -y --fix-missing python3 python3-distutils python3-setuptools
# RUN sudo apt-get clean all \
#     && curl https://bootstrap.pypa.io/get-pip.py -o ~/get-pip.py
# RUN sudo python3 ~/get-pip.py && rm ~/get-pip.py \
#     && sudo pip3 install PyYAML --global-option="--without-libyaml" \
#     && sudo pip3 install mypy==0.650 javascripthon==0.10 pseudo==0.2.16 pseudo-python==0.2.34 \
RUN sudo apt-get clean all && sudo rm -Rf /root/.cache

# Cache of pypi modules
# WORKDIR /home/circleci/pypi-downloads
# RUN mkdir -p /home/circleci/.pip \
# 	&& echo '[global]' > /home/circleci/.pip/pip.conf \
# 	&& echo "cache-dir=/home/circleci/pypi-offline-cache/" >> /home/circleci/.pip/pip.conf \
# 	&& echo "find-links=file:///home/circleci/pypi-offline-cache/ file:///home/circleci/pypi-downloads" \
# 	&& mkdir -p /home/circleci/pypi-offline-cache/ \
# 	&& mkdir -p /home/circleci/pypi-downloads \
# 	&& sudo chown -R circleci /home/circleci/pypi-offline-cache/ /home/circleci/pypi-downloads

RUN sudo pip install --upgrade pip \
 	&& sudo /usr/local/bin/pip2 install Pillow==3.0 --global-option="build_ext" --global-option="--enable-freetype"

COPY ./requirements-dev.txt requirements-dev.txt
RUN \
	# Python QA Modules & Modules from https://cloud.google.com/appengine/docs/standard/python/tools/built-in-libraries-27
	sudo /usr/local/bin/pip2 install -r requirements-dev.txt \
	&& sudo rm -Rf /root/.cache \
	&& /usr/local/bin/pip2 freeze > ~/requirements-installed.txt \
	&& cat ~/requirements-installed.txt

# # Cache of npm modules
# WORKDIR /home/circleci/
# COPY ./package.json package.json
# RUN yarn config set modules-folder /home/circleci/node_modules \
# 	&& yarn config set yarn-offline-mirror /home/circleci/npm-packages-offline-cache \
# 	&& yarn install \
# 	&& rm -Rf node_modules/

# why not https://docs.docker.com/engine/reference/builder/#add
COPY ./bootstrap.sh /bootstrap.sh
ENTRYPOINT ["sh", "/bootstrap.sh"]
CMD ["/bin/bash"]
