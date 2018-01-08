"""
* tools - internal helpers
* handlers - farious base classes and MixIns for Request-Handlers
* views - concrete implementation of Request-Handlers
"""
import os.path
import sys


# Add bundled libraries to path
mypath = os.path.abspath(__file__)
mydir = os.path.dirname(mypath)
vendordir = os.path.join(mydir, './vendor/1stvamp-memorised/')
sys.path.insert(0, vendordir)
