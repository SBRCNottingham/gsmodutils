from distutils.core import setup, Extension


setup(
    name="gsmodutils",
    version = "0.1",
    description = "",
    author = "James Gilbert",
    author_email = "james.gilbert@nottingham.ac.uk",
    url = "",
    license = "GPL",
    packages = ["gsmodutils"],
    scripts = ["gsmodutils/parse_scrumpy.py", "gsmodutils/gsm_project.py"]
)
