'''
Created on Jan 30, 2017

@author: kennethalamantia
'''
import os
import unittest

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import testbed
import webapp2

import blog_handler as blog
import blog_utilities as util


class TestBlog(unittest.TestCase):


    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        ndb.get_context().set_cache_policy(False)
#         print os.environ['APPLICATION_ID']


    def tearDown(self):
        self.testbed.deactivate()
        
    def _setPostResponse(self, postDict):
        return blog.app.get_response(blog.SIGNUP, POST = postDict)

class TestSignupInputVerification(TestBlog):
    
    def testUsernameValidation(self):
        response = self._setPostResponse({blog.USER : ''})
        assert response.status_int == 200
        self.assertTrue("The username is invalid." in response.body, 
                        "Invalid username error msg not present.")
    
    def testPasswordValidation(self):
        response = self._setPostResponse({blog.USER : "friend",
                                          blog.PASSWORD : "ff",
                                          blog.PWD_VERIFY : "ff"})
        self.assertTrue("The password is invalid." in response.body,
                        "Invalid password error msg not present.")
    def testEmailValidation(self):
        response = self._setPostResponse({blog.USER : "friend",
                                          blog.PASSWORD : "ttt",
                                          blog.PWD_VERIFY : "ttt",
                                          blog.EMAIL : "garbage"})
        self.assertTrue("Invalid email address." in response.body,
                        "Email error msg not present.")
    def testPasswordMatchVerification(self):
        response = self._setPostResponse({blog.USER : "friend",
                                          blog.PASSWORD : "ttt",
                                          blog.PWD_VERIFY : "tttp",
                                          blog.EMAIL : "garbage@ttt.com"})
        print response.body
        self.assertTrue("The passwords do not match." in response.body,
                        "Password match error msg not present.")
        
    def testSuccessfulSignup(self):
        response = self._setPostResponse({blog.USER : "friend",
                                          blog.PASSWORD : "ttt",
                                          blog.PWD_VERIFY : "ttt",
                                          blog.EMAIL : "ttt@ttt.com"})
        self.assertEqual(ndb.Key("User", "friend").get().email, "ttt@ttt.com",
                         "email is incorrect in db")
        self.assertEqual(ndb.Key("User", "friend").get().user_name, 
                         "friend", "user name is incorrect in db")
        self.assertTrue("username=friend" in response.headers.get("Set-Cookie"))
        self.assertTrue(util.CookieUtil.test_hash("friend") in 
                                            response.headers.get("Set-Cookie"))

class TestNewPost(TestBlog):
    
    # need to set the cookie properly
    
    # test new post body valid/invalid
    # test new post content valid/invalid
    
    # test effect on User entity multiple posts etc.
    
    # test new post in db        

        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()