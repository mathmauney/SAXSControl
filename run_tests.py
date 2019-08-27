import unittest
import os

loader = unittest.TestLoader()
start_dir = os.getcwd() + '/test/unittests'
print(start_dir)
suite = loader.discover(start_dir)

runner = unittest.TextTestRunner()
runner.run(suite)
