from locust import HttpLocust, TaskSet
from uuid import uuid4, uuid1
from json import dumps as j

def login(l):
    l.client.get("/login")
    l.data_id = str(uuid4())

def index(l):
    l.client.get("/data/map/aaa")

def valu(l):
    l.client.get("/data/map/aaa/" + l.data_id)

def add(l):
    l.client.post("/data/map/aaa", j({l.data_id : str(uuid1())}), headers = {"content-type":"application/json"})

def rem(l):
    l.client.delete("/data/map/aaa/" + l.data_id)

def profile(l):
    l.client.get("/data/info")

class UserBehavior(TaskSet):
    tasks = {index: 2, profile: 1, add: 5, valu: 3, rem: 1}

    def on_start(self):
        login(self)

    def on_stop(self):
        logout(self)

class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait = 500
    max_wait = 10000

# virtual env create
# pip install locustio
# locust -f <this file> --host=http://<required http host>
