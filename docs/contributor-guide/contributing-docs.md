# Documentation contribution guidelines

Contributing to the documentation benefits everyone who uses kloppy. If something in the docs doesn’t make sense to you, updating the relevant section after you figure it out is a great way to ensure it will help the next person. Please visit the [issues page](https://github.com/PySport/kloppy/issues?page=1&q=is%3Aopen+sort%3Aupdated-desc+label%3Adocumentation) for a full list of issues that are currently open regarding the kloppy documentation.

## About the kloppy documentation

The documentation is written in [Markdown](https://daringfireball.net/projects/markdown/), which is a simple and easy-to-use markup language. The [Markdown Guide](https://www.markdownguide.org/) provides an excellent tutorial on how to write Markdown. To perform more complex changes to the documentation, it is recommended to review the [MkDocs](https://www.mkdocs.org/user-guide/writing-your-docs) documentation as well.

The kloppy documentation consists of two parts: the docstrings in the code itself and the docs in the folder `doc/`. The docstrings provide a clear explanation of the usage of the individual functions, while the documentation in `doc/` consists of tutorial-like overviews per topic together with some other information.

### Docstrings

The docstrings follow the Google Style Python Docstrings Convention. Follow [google's style guide](https://google.github.io/styleguide/pyguide.html) for detailed instructions on how to write a correct docstring.

### Documentation pages

The tutorials make heavy use of the [`markdownn-exec`](https://pawamoy.github.io/markdown-exec) extension. This extension lets you put code in the documentation which will be run during the doc build. For example:

```
\`\`\`pycon exec="on"
>>> x = 2
>>> print(x**3)
\`\`\`
```

will be rendered as:

```
\`\`\`
In [1]: x = 2

In [2]: print(x**3)
Out[2]: 8
\`\`\`
```

Almost all code examples in the docs are run (and the output saved) during the doc build. This approach means that code examples will always be up to date, but it does make the doc building a bit more complex.

Our API documentation files in doc/source/reference house the auto-generated documentation from the docstrings. For classes, there are a few subtleties around controlling which methods and attributes have pages auto-generated.

We have two autosummary templates for classes.

\_templates/autosummary/class.rst. Use this when you want to automatically generate a page for every public method and attribute on the class. The Attributes and Methods sections will be automatically added to the class’ rendered documentation by numpydoc. See DataFrame for an example.

\_templates/autosummary/class_without_autosummary. Use this when you want to pick a subset of methods / attributes to auto-generate pages for. When using this template, you should include an Attributes and Methods section in the class docstring. See CategoricalIndex for an example.

Every method should be included in a toctree in one of the documentation files in doc/source/reference, else Sphinx will emit a warning.

The utility script scripts/validate_docstrings.py can be used to get a csv summary of the API documentation. And also validate common errors in the docstring of a specific class, function or method. The summary also compares the list of methods documented in the files in doc/source/reference (which is used to generate the API Reference page) and the actual public methods. This will identify methods documented in doc/source/reference that are not actually class methods, and existing methods that are not documented in doc/source/reference.

## Updating a pandas docstring

When improving a single function or method’s docstring, it is not necessarily needed to build the full documentation (see next section). However, there is a script that checks a docstring (for example for the DataFrame.mean method):

python scripts/validate_docstrings.py pandas.DataFrame.mean
This script will indicate some formatting errors if present, and will also run and test the examples included in the docstring. Check the pandas docstring guide for a detailed guide on how to format the docstring.

The examples in the docstring (‘doctests’) must be valid Python code, that in a deterministic way returns the presented output, and that can be copied and run by users. This can be checked with the script above, and is also tested on Travis. A failing doctest will be a blocker for merging a PR. Check the examples section in the docstring guide for some tips and tricks to get the doctests passing.

When doing a PR with a docstring update, it is good to post the output of the validation script in a comment on github.

## How to build the kloppy documentation

### Requirements

First, you need to have a development environment to be able to build pandas (see the docs on creating a development environment).

### Building the documentation

So how do you build the docs? Navigate to your local doc/ directory in the console and run:

python make.py html
Then you can find the HTML output in the folder doc/build/html/.

The first time you build the docs, it will take quite a while because it has to run all the code examples and build all the generated docstring pages. In subsequent evocations, sphinx will try to only build the pages that have been modified.

If you want to do a full clean build, do:

python make.py clean
python make.py html
You can tell make.py to compile only a single section of the docs, greatly reducing the turn-around time for checking your changes.

# omit autosummary and API section

python make.py clean
python make.py --no-api

# compile the docs with only a single section, relative to the "source" folder.

# For example, compiling only this guide (doc/source/development/contributing.rst)

python make.py clean
python make.py --single development/contributing.rst

# compile the reference docs for a single function

python make.py clean
python make.py --single pandas.DataFrame.join

# compile whatsnew and API section (to resolve links in the whatsnew)

python make.py clean
python make.py --whatsnew
For comparison, a full documentation build may take 15 minutes, but a single section may take 15 seconds. Subsequent builds, which only process portions you have changed, will be faster.

The build will automatically use the number of cores available on your machine to speed up the documentation build. You can override this:

python make.py html --num-jobs 4
Open the following file in a web browser to see the full documentation you just built doc/build/html/index.html.

And you’ll have the satisfaction of seeing your new and improved documentation!

### Building main branch documentation

When pull requests are merged into the pandas main branch, the main parts of the documentation are also built by Travis-CI. These docs are then hosted here, see also the Continuous Integration section.

## Previewing changes

Once, the pull request is submitted, Netlify will automatically build the documentation. To view the built site:

1. Wait for the CI / Web and docs check to complete.
1. Click Details next to it.
1. From the Artifacts drop-down, click docs or website to download the site as a ZIP file.
