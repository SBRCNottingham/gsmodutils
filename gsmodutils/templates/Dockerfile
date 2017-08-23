FROM python

RUN mkdir /model
COPY . /model
WORKDIR /model
RUN pip install -r requirements.txt
RUN pip install --use-wheel --no-index --find-links=/home/jpg/gsmodutils/ gsmodutils
