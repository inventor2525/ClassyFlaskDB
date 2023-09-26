from setuptools import setup, find_packages

setup(
    name="ClassyFlaskDB",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "Flask",
        "SQLAlchemy"
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A library to use attributes on classes, fields and properties to more easily save data to SQLite and transmit it using Flask",
    license="MIT",
    keywords="flask sqlite sqlalchemy",
    url="https://github.com/yourusername/ClassyFlaskDB"
)