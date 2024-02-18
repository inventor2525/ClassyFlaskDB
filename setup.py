from setuptools import setup, find_packages

setup(
    name="ClassyFlaskDB",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "Flask",
        "SQLAlchemy",
		
        "six",
		"pytz",
		"urllib3",
		"idna",
		"certifi",
		"pydub",
		"tzlocal",
    ],
    author="Charlie Angela Mehlenbeck",
    author_email="charlie_inventor2003@yahoo.com",
    description="A decorator library to easily save data to SQLite or json and generate Flask server and client code.",
	long_description=open("README.md").read(),
    license="MIT",
    keywords="flask sqlite sqlalchemy",
    url="https://github.com/Inventor2525/ClassyFlaskDB"
)