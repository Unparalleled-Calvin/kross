FROM python:3.8-alpine
WORKDIR /kross
ADD . /kross
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install -r ./requirements.txt
CMD ["python", "./src/main.py"]