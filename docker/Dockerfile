# This should be able to run all tests for our App Engine Projects
# and also be able to handle automated deployments
# Node is there for Javascript Builds and tests

FROM circleci/python:2.7.14-stretch-node
# Python 2.7.12 is what is running on AppEngine
# sothis would be more authentic:
# RUN wget https://www.python.org/ftp/python/2.7.12/Python-2.7.12.tgz && \
#     tar xzf Python-2.7.12.tgz && \
#     rm Python-2.7.12.tgz && \
#     cd Python-2.7.12 && \
#     ./configure && \
#     make install


#LABEL description="This text illustrates"

# See https://github.com/CircleCI-Public/circleci-dockerfiles/blob/master/python/images/2.7.14/node-browsers/Dockerfile
# for inspiration on how to build Browsers for headless testing

# carefull! python packages get installed into system python and not user python
RUN sudo apt-get install -y libfreetype6-dev libjpeg-dev zlib1g-dev libtiff-dev python-pil
# update to a git which can run paralell (-j8)
RUN sudo /bin/sh -c 'echo "deb http://ftp.us.debian.org/debian testing main contrib non-free" >> /etc/apt/sources.list' \
	&& sudo apt-get update \
	&& sudo apt-get install -y git less \
	&& sudo apt-get clean all

RUN curl -s https://dl.google.com/dl/cloudsdk/release/google-cloud-sdk.tar.gz > /tmp/google-cloud-sdk.tar.gz \
	&& sudo mkdir -p /usr/local/gcloud \
	&& sudo tar -C /usr/local/gcloud -xf /tmp/google-cloud-sdk.tar.gz \
	&& rm /tmp/google-cloud-sdk.tar.gz \
	&& sudo /usr/local/gcloud/google-cloud-sdk/install.sh \
	&& /usr/local/gcloud/google-cloud-sdk/bin/gcloud config set disable_usage_reporting true
ENV PATH $PATH:/usr/local/gcloud/google-cloud-sdk/bin

ENV GAE_VERSION '1.9.69'

RUN curl -s https://storage.googleapis.com/appengine-sdks/featured/google_appengine_${GAE_VERSION}.zip > /tmp/google_appengine.zip \
	&& sudo unzip -q /tmp/google_appengine.zip -d /usr/local/ \
	&& rm /tmp/google_appengine.zip
ENV PATH $PATH:/usr/local/google_appengine

# Python QA Modules & Modules from https://cloud.google.com/appengine/docs/standard/python/tools/built-in-libraries-27
RUN sudo /usr/local/bin/pip install pillow==3.0 --global-option="build_ext" --global-option="--enable-freetype" \
	&& sudo /usr/local/bin/pip install --cache-dir /pypi-offline-cache \
	'bumpversion==0.5.3' \
	'doit<0.30' \
	'flake8==2.6.2' \
	'glob2==0.6' \
	'isort==4.3.4' \
	'lxml==3.7.3' \
	'nose==1.3.7' \
	'NoseGAE==0.5.10' \
	'numpy==1.6.1' \
	'prospector==0.12.7' \
	'pycrypto==2.6.1' \
	'pytz==2017.3' \
	'PyYAML==3.10' \
	'requests==2.18.4' \
	&& sudo rm -Rf /root/.cache \
	&& sudo mv /pypi-offline-cache /home/circleci/ \
	&& sudo chown -R circleci.circleci /home/circleci/ \
	&& mkdir /home/circleci/.pip \
	&& mkdir /home/circleci/pypi-downloads \
	&& echo '[global]' > /home/circleci/.pip/pip.conf \
	&& echo "cache-dir=/home/circleci/pypi-offline-cache/" >> /home/circleci/.pip/pip.conf \
	&& echo "find-links=file:///home/circleci/pypi-offline-cache/ file:///home/circleci/pypi-downloads"

# Cache of pypi modules
WORKDIR /home/circleci/pypi-downloads
COPY ./requirements.txt requirements.txt
RUN pip download -r requirements.txt

# Cache of npm modules
WORKDIR /home/circleci/
COPY ./package.json package.json
RUN yarn config set modules-folder /home/circleci/node_modules \
	&& yarn config set yarn-offline-mirror /home/circleci/npm-packages-offline-cache \
	&& yarn install \
	&& rm -Rf node_modules/

# why not https://docs.docker.com/engine/reference/builder/#add
COPY ./bootstrap.sh /bootstrap.sh
ENTRYPOINT ["sh", "/bootstrap.sh"]
CMD ["/bin/bash"]
