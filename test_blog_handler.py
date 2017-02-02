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
        
    def _setPostResponse(self, postDict, headersList=None):
        return blog.app.get_response(blog.SIGNUP, POST = postDict, 
                                     headers=headersList)

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
        self.assertTrue(util.CookieUtil._hash("friend") in 
                                            response.headers.get("Set-Cookie"))
        self.assertEqual(response.location, "http://localhost" + blog.WELCOME,
                   "successful signup did not redirect to welcome page.")

class TestNewPost(TestBlog):
    
    # need to set the cookie properly
    
    def setPostRequest(self, username, subject, content):
        '''
        Method that sets the response to test. 
        @param username is the username that will have a cookie set to be
        logged in
        @param subject and @param content are the subject and content of the
        new post.
        '''
        postDict = {blog.SUBJECT : subject, 
                    blog.CONTENT : content}
        headersList = [("Cookie", 
                        util.CookieUtil._format_cookie(blog.USER, username))]
        return blog.app.get_response(blog.NEWPOST, POST = postDict, 
                                     headers=headersList)
        
    def testNewPostDBCorrectness(self):
        '''
        Tests makes a series of posts and then tests the DB for correctness.
        Posts are only made during this test.
        '''
        blog.User.create_new_user({blog.USER : "test_username",
                              blog.PASSWORD : "test_password"})
        # Post 1 
        response = self.setPostRequest("test_username", "test_subject", 
                                       "test_content")
        post1Key = ndb.Key("User", "test_username", "BlogPost", "1")
        post1 = post1Key.get()
        self.assertTrue(post1Key)
        self.assertEqual(post1.post_subject, "test_subject")
        self.assertEqual(post1.post_content, "test_content")
        self.assertEqual(post1.post_author, "test_username")
        self.assertEqual(post1.post_number, 1)
        
        # Post 2
        
        response = self.setPostRequest("test_username", "test_subject2", 
                                       "test_content2")
        post1Key = ndb.Key("User", "test_username", "BlogPost", "2")
        post1 = post1Key.get()
        self.assertTrue(post1Key)
        self.assertEqual(post1.post_subject, "test_subject2")
        self.assertEqual(post1.post_content, "test_content2")
        self.assertEqual(post1.post_author, "test_username")
        self.assertEqual(post1.post_number, 2)
        
    # Test empty subject and subject too long
    def testNewPostBadSubject(self):
        blog.User.create_new_user({blog.USER : "test_username",
                              blog.PASSWORD : "test_password"})
        # Post 1 
        response = self.setPostRequest("test_username", "", 
                                       "test_content")
        self.assertTrue("You must have a subject of less than" 
                        + "100 chars in length." in response.body, "subject" +
                        "error msg should be in body")
        
        # Post 2
        response = self.setPostRequest("test_username", "1234567890" +
                                       "123456789012345678901234567890" +
                                       "123456789012345678901234567890" +
                                       "123456789012345678901234567890" +
                                       "123456789012345678901234567890", 
                                       "test_content")
        self.assertTrue("You must have a subject of less than" 
                        + "100 chars in length." in response.body, "subject" +
                        "error msg should be in body")
    
    # Test empty content
    def testNewPostBadContent(self):
        blog.User.create_new_user({blog.USER : "test_username",
                              blog.PASSWORD : "test_password"})
        # Post 1 
        response = self.setPostRequest("test_username", "test_subject", 
                                       "")
        self.assertTrue("Your post must have content." in response.body,
                        "No content error msg should be in response body.")
    
    # Test no user logged in
    def testNoUserLoggedIn(self):
        '''
        Test to make sure a post cannot be created without a logged in user.
        If someone attempts to create a new post and is not logged in, they
        should be redirected to the signup page.
        '''
        blog.User.create_new_user({blog.USER : "test_username",
                              blog.PASSWORD : "test_password"})
        # Post 1 - redirect in post 
        response = self.setPostRequest("", "test_subject", 
                                       "test_content")
        self.assertEqual(response.location, "http://localhost/blog/signup",
                   "failure to be signed in did not redirect correctly (post).")
        
        # Post 2 - redirect in get
        response = blog.app.get_response(blog.NEWPOST)
        self.assertEqual(response.location, "http://localhost/blog/signup",
                   "failure to be signed in did not redirect correctly (get)")
    
    # Test redirects to static link correctly when successful new post is made
    
# Class to test login handler

# Class to test logout handler

# Class to test comment handler and database correctness

# Class to test post liking
        
    
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()