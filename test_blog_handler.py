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
import blog_handler
from google.appengine.ext.db import SelfReference
from cherrypy import response


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
    @classmethod    
    def _createDummyUser(cls, username, password):
        '''
        Create a dummy user account for testing.
        '''
        return blog.User.create_new_user({blog.USER : username,
                              blog.PASSWORD : password})
    
    @classmethod        
    def _createDummyPost(cls, username, subject, content):
        '''
        Creates a dummy blog post to test comment feature on.
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
                   "successful signup did not redirect to welcome page." +
                   " Location was " + response.location)
    
    def testUserAlreadyExists(self):
        '''
        Tests attempting to create a new user when that user already exists.
        '''
        self._createDummyUser("alreadyExists", "12345")
        response = self._setPostResponse({blog.USER : "alreadyExists",
                                          blog.PASSWORD : "12345",
                                          blog.PWD_VERIFY: "12345"})
        self.assertTrue("User already exists. Please choose another user name" 
                       in response.body, "Error msg for attempting to create" +
                       " a user with a duplicate username is incorrect." +
                       " The body of the response was:" + response.body)
        

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
        self.assertEqual(response.location, "http://localhost/blog/post_id/" +
                         str(post1Key.urlsafe()), "new post not redirecting to" + 
                         "static link page properly. Location was " + 
                         str(response.location) + " but was expected to be " +
                         str(post1Key.urlsafe())) 
        
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
        self.assertTrue("You must include some content." in response.body,
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
    
# Class to test login handler

# Class to test logout handler

# Class to test comment handler and database correctness
class TestComments(TestBlog):
    # set post request helper method (similar to TestNewPosts)
    P_AUTHOR = "post_author"
    C_AUTHOR = "comment_author"
    
    def setUpTest(self):
        # set dummy post author
        self._createDummyUser(self.P_AUTHOR, "test_password")
        # set dummy post
        self._createDummyPost(self.P_AUTHOR, "test_subject", "test_content")
        # set comment author
        self._createDummyUser(self.C_AUTHOR, "test_password2")
        
    def _setPostRequest(self, author, content, post_key):
        '''
        Method that sets the response to test. 
        author - post's author as a string, comes from a cookie
        content - content of the comment, as a string
        '''
        postDict = {blog.CONTENT : content}
        headersList = [("Cookie", 
                        util.CookieUtil._format_cookie(blog.USER, author))]
        return blog.app.get_response("/blog/post_id/" + post_key + "/comment", 
                                     POST = postDict, 
                                     headers=headersList)
    
    def testNewCommentDBCorrectness(self):
        '''
        Tests correctly adding a new comment to a post. 
        Checks correctness of DB after adding the new comment.
        '''
        self.setUpTest()
        # there is only 1 blog post, so it's 1 by default
        post_key = ndb.Key("User", self.P_AUTHOR, "BlogPost", "1")
        # set post response
        self._setPostRequest(self.C_AUTHOR, "comment_content",
                             post_key.urlsafe())
        new_comment_key = blog.Comment.get_comment_key("1", post_key)
        new_comment = new_comment_key.get()
                                                       
        self.assertEqual(new_comment.content, "comment_content",
                         "New Comment Content is not corrent, was " +
                         new_comment.content + " but should have been" +
                         " 'comment_content'")
        
        self._setPostRequest(self.C_AUTHOR, "2nd comment_content", 
                             post_key.urlsafe())
        
        new_comment2 = blog.Comment.get_comment_key("2", post_key).get()
        self.assertEqual(new_comment2.content, "2nd comment_content",
                         "New Comment Content is not corrent, was " +
                         new_comment.content + " but should have been" +
                         " '2nd comment_content'")
        self.assertEqual(post_key.get().num_comments, 2)
        self._setPostRequest(self.C_AUTHOR, "3d comment_content", 
                             post_key.urlsafe())
        self.assertEqual(post_key.get().num_comments, 3)
        
    
    def testInputVerification(self):
        self.setUpTest()
        # there is only 1 blog post, so it's 1 by default
        post_key = ndb.Key("User", self.P_AUTHOR, "BlogPost", "1")
        # set post response
        response  = self._setPostRequest(self.C_AUTHOR, "",
                                        post_key.urlsafe())
        self.assertTrue("You must include some content." in response.body,
                        "Test should raise missing content error msg.")
        
        
    
    def testNoUserLoggedIn(self):
        # test what happens when a user is not logged in
        self.setUpTest()
        post_key = ndb.Key("User", self.P_AUTHOR, "BlogPost", "1").urlsafe()
        response = blog.app.get_response("/blog/post_id/" + post_key + 
                                         "/comment")
        self.assertEqual(response.location, "http://localhost/blog/signup",
                   "failure to be signed in did not redirect correctly (get)")
    
    def testRendering(self):
        # Test the rending of a page after making a comment
        pass
    
    def testDeleteComment(self):
        # Implement this next round
        pass

# Class to test post liking

class testLoginLogout(TestBlog):
    '''
    Class to test logging in and out.
    '''
    REALUSER = "realuser"
    FAKEUSER = "fakeuser"
    ACTUALPWD = "12345"
    
    def _setPostRequest(self, username, password):
        '''
        Sets up a POST request via the login form and generates a response.
        Tests in this class check the correctness of the response.
        @param username: the username to enter into the login form
        @param password: the password to enter into the login form
        '''
        
        postDict = {blog.USER : username, blog.PASSWORD : password}
        return blog.app.get_response(blog.LOGIN, POST = postDict)
    
    # test successful login
    def testLogin(self):
        '''
        Test vanilla login with correct username and password.
        Make sure page redirects correctly.
        '''
        self._createDummyUser(self.REALUSER, self.ACTUALPWD)
        response = self._setPostRequest(self.REALUSER, self.ACTUALPWD)
        self.assertEqual(response.location, "http://localhost" + blog.WELCOME,
                   "successful signup did not redirect to welcome page." +
                   " Location was " + response.location)
    
    # test login with incorrect username
    def testBagLogin(self):
        '''
        Test login with incorrect username. Make sure correct error msg
        is displayed.
        '''
        self._createDummyUser(self.REALUSER, self.ACTUALPWD)
        response = self._setPostRequest(self.FAKEUSER, self.ACTUALPWD)
        self.assertTrue("That user does not exist." in response.body,
                        "Error message did not render correctly for bad " + 
                        "username. Rendered body was: " + response.body)
        
    
    # test login with incorrect password
    
    # test entering garbage into the form fields
    
    # test reaching login page while being logged in
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
        
    
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()