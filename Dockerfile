# Create the reusable docker image for python projects with docker build . -t gsmodutils
FROM python

RUN pip install gsmodutils
