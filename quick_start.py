"""Compatibility launcher. See README.md for the current pipeline."""
import sys
from sportslab.__main__ import main
if __name__=='__main__':
    sys.argv.insert(1,'serve')
    main()
