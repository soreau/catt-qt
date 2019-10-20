"""A control GUI for Chromecasts"""

# -*- coding: utf-8 -*-

import sys
from cattqt import cattqt

if sys.version_info.major < 3:
    print("This program requires Python 3 and above to run.")
    sys.exit(1)

__author__ = cattqt.author
__email__ = cattqt.email
__version__ = cattqt.version


def main() -> None:
    cattqt.main()
