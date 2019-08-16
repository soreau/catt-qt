"""A control GUI for Chromecasts"""

# -*- coding: utf-8 -*-

import sys
from cattqt import cattqt

if sys.version_info.major < 3:
    print("This program requires Python 3 and above to run.")
    sys.exit(1)


def main() -> None:
    cattqt.main()


__author__ = "Scott Moreau"
__email__ = "oreaus@gmail.com"
__version__ = "1.7"
