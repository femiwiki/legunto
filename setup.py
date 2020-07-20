import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="legunto",
    version="0.0.1",
    scripts=["legunto"],
    description="Fetch MediaWiki Scribunto modules from wikis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    install_requires=["mwclient"],
)
