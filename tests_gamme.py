import os

# Note:- Always before import boto as its statically bound #
os.environ['BOTO_CONFIG'] = 'boto_test.cfg'

import boto
import cgi
import config
import gscloud
import unittest

class GammeUnitTest(unittest.TestCase):
    """
    Unit Tests for Gamme
    """
    buckets = []
    def setUp(self):
        self.buckets = gscloud.get_buckets()

    def testBuckets(self):
        buckets = gscloud.get_buckets()
        self.assertIn('gamme-cs-bucket', buckets)
        self.assertIn('gamme-cs-bucket2', buckets)
        self.assertNotIn('gamme-cs-bucket3', buckets)

    def testUser(self):
        userid = 'amw'
        result_bunch = gscloud.get_userobjects(userid, self.buckets)
        self.assertNotEqual(len(result_bunch.result), 0)
        
        userid = ''
        result_bunch = gscloud.get_userobjects(userid, self.buckets)
        self.assertEqual(len(result_bunch.result), 0)

        userid = 'amw-wrong'
        result_bunch = gscloud.get_userobjects(userid, self.buckets)
        self.assertEqual(len(result_bunch.result), 0)


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(GammeUnitTest("testBuckets"))
    suite.addTest(GammeUnitTest("testUser"))
    unittest.TextTestRunner(verbosity=2).run(suite)
