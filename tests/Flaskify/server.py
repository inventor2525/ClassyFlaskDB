from model import *
from flask import Flask

if __name__ == "__main__":
    FLASKIFY.secret = 42
    app = FLASKIFY.make_server('localhost', 5000)