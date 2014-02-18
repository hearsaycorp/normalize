#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This is a convenience nose wrapper, for use with 'coverage' and
'setup.py test'; run it using:

    $ ./run_tests.py

You can also pass 'nose' arguments to this script, for instance to run
individual tests or to skip redirection of output so 'pdb.set_trace()'
works:

    $ ./run_tests.py -s -v normalize.test_foo

"""

import os
import sys

try:
    import nose
except ImportError:
    recommend = (
        "pip install nose unittest2 -r requirements.txt" if
        "VIRTUAL_ENV" in os.environ else
        "sudo easy_install nose unittest2 richenum"
    )
    sys.stderr.write(
        "Running the tests requires Nose. Try:\n\n{cmd}\n\nAborting.\n"
        .format(cmd=recommend)
    )
    sys.exit(1)


args = [] if "distutils" in sys.modules else sys.argv[1:]

nose.main(argv=['nosetests'] + args)
