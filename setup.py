from setuptools import setup, find_packages


setup(
    name="gsmodutils",
    version = "0.0.1",
    description = "",
    author = "James Gilbert",
    author_email = "james.gilbert@nottingham.ac.uk",
    url = "",
    license = "MIT",
    packages = ["gsmodutils"],
    scripts = ["gsmodutils/parse_scrumpy.py", "gsmodutils/gsm_project.py"],
    entry_points={
          'console_scripts': ['gsm_project=gsmodutils.gsm_project:main'],
    },
    include_package_data=True
)
