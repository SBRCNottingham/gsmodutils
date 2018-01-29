# Create the reusable docker image for python projects with docker build . -t gsmodutils
FROM python

RUN mkdir /gsmodutils
COPY . /gsmodutils
WORKDIR gsmodutils

RUN pip install -r requirements.txt
RUN pip install -e .
