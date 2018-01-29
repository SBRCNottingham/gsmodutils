# Requires the gsmodutils docker image to be installed on a users system
FROM gsmodutils

RUN mkdir /model
COPY . /model
WORKDIR /model
RUN pip install -r requirements.txt
