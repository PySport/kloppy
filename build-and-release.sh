#!/bin/bash

CURRENT_VERSION=`python -c "import kloppy; print(kloppy.__version__)"`

python setup.py sdist
python setup.py bdist_wheel

twine upload dist/kloppy-$CURRENT_VERSION*