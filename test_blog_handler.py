'''
Test suite for blog_handler module.
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
    '''Base class to set up testing harness.
    '''
    def setUp(self):
        '''App engine test framework setup. See app engine docs for testing
        with NDB cloud storeage.
        '''
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        ndb.get_context().set_cache_policy(False)
#         print os.environ['APPLICATION_ID']

    def tearDown(self):
        '''Clean up prior tests.
        '''
        self.testbed.deactivate()

    def _setPostResponse(self, postDict, headersList=None):
        '''Make a mock request of the application.
        @param postDict: dict of POST items to pass with a mock request
        @param headersList: list of headers for the request
        '''
        return blog.app.get_response(blog.SIGN_UP, POST=postDict,
                                     headers=headersList)

    def _testInResponseBody(self, stringToLookFor, response):
        '''Tests whether input string is contained in the body of the response.
        @param response: the response to look in.
        @param stringToLookFor: The string to look for.
        '''
        self.assertTrue(stringToLookFor in response.body, stringToLookFor +
                        " not present in response body: " + response.body)

    @classmethod
    def _createDummyUser(cls, username, password):
        '''Create a dummy user account for testing.
        @param username: the username of the mock user
        @param password: the password of the mock user
        '''
        return blog.User.create_new_user({blog.USER : username,
                              blog.PASSWORD : password})

    @classmethod
    def _createDummyPost(cls, username, subject, content):
        '''Creates a dummy blog post for testing.
        @param username is the username that will have a cookie set to be
        logged in
        @param subject: of mock post
        @param content: of mock post
        '''
        postDict = {blog.SUBJECT : subject,
                    blog.CONTENT : content}
        headersList = [("Cookie",
                        util.CookieUtil._format_cookie(blog.USER, username))]
        return blog.app.get_response(blog.NEW_POST, POST=postDict,
                                     headers=headersList)

class TestSignupInputVerification(TestBlog):
    '''Class to test signup form.
    '''

    def testUsernameValidation(self):
        '''Test validation of user name form.
        '''
        response = self._setPostResponse({blog.USER : ''})
        assert response.status_int == 200
        self.assertTrue("The username is invalid." in response.body,
                        "Invalid username error msg not present.")

    def testPasswordValidation(self):
        '''Test validation of password form.
        '''
        response = self._setPostResponse({blog.USER : "friend",
                                          blog.PASSWORD : "ff",
                                          blog.PWD_VERIFY : "ff"})
        self.assertTrue("The password is invalid." in response.body,
                        "Invalid password error msg not present.")

    def testEmailValidation(self):
        '''Test validation of email form.
        '''
        response = self._setPostResponse({blog.USER : "friend",
                                          blog.PASSWORD : "ttt",
                                          blog.PWD_VERIFY : "ttt",
                                          blog.EMAIL : "garbage"})
        self.assertTrue("Invalid email address." in response.body,
                        "Email error msg not present.")

    def testPasswordMatchVerification(self):
        '''Test password match form.
        '''
        response = self._setPostResponse({blog.USER : "friend",
                                          blog.PASSWORD : "ttt",
                                          blog.PWD_VERIFY : "tttp",
                                          blog.EMAIL : "garbage@ttt.com"})
        self.assertTrue("The passwords do not match." in response.body,
                        "Password match error msg not present.")

    def testSuccessfulSignup(self):
        '''Test a request to the application that generates a successful
        signup response.
        '''
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
        '''Tests attempting to create a new user when that user already exists.
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
    '''Class to test the creation of new posts.
    '''

    def setPostRequest(self, username, subject, content):
        '''Method that sets the response to test. 
        @param username is the username that will have a cookie set to be
        logged in
        @param subject: of mock post
        @param content: of mock post
        '''
        postDict = {blog.SUBJECT : subject,
                    blog.CONTENT : content}
        headersList = [("Cookie",
                        util.CookieUtil._format_cookie(blog.USER, username))]
        return blog.app.get_response(blog.NEW_POST, POST=postDict,
                                     headers=headersList)

    def testNewPostDBCorrectness(self):
        '''Makes a series of posts and then tests the DB for correctness.
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
        self.assertEqual(post1.post_number, "1")
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
        self.assertEqual(post1.post_number, "2")

    def testNewPostBadSubject(self):
        '''Test making a post with an invalid subject field.
        '''
        blog.User.create_new_user({blog.USER : "test_username",
                              blog.PASSWORD : "test_password"})
        # Post 1
        response = self.setPostRequest("test_username", "",
                                       "test_content")
        self.assertTrue("You must have a subject of less than "
                        + "100 chars in length." in response.body, "subject" +
                        "error msg should be in body")

        # Post 2
        response = self.setPostRequest("test_username", "1234567890" +
                                       "123456789012345678901234567890" +
                                       "123456789012345678901234567890" +
                                       "123456789012345678901234567890" +
                                       "123456789012345678901234567890",
                                       "test_content")
        self.assertTrue("You must have a subject of less than "
                        + "100 chars in length." in response.body, "subject" +
                        "error msg should be in body")

    def testNewPostBadContent(self):
        '''Test making a new post with a bad content field.
        '''
        blog.User.create_new_user({blog.USER : "test_username",
                              blog.PASSWORD : "test_password"})
        # Post 1
        response = self.setPostRequest("test_username", "test_subject",
                                       "")
        self.assertTrue("You must include some content." in response.body,
                        "No content error msg should be in response body.")

    def testNoUserLoggedIn(self):
        '''Test attempting to create a post with no logged in user.
        '''
        blog.User.create_new_user({blog.USER : "test_username",
                              blog.PASSWORD : "test_password"})

        # Post 2 - redirect in get
        response = blog.app.get_response(blog.NEW_POST)
        self.assertEqual(response.location, "http://localhost/blog/signup",
                   "failure to be signed in did not redirect correctly (get)")


class TestComments(TestBlog):
    '''Class to test making comments.
    '''
    # set post request helper method (similar to TestNewPosts)
    P_AUTHOR = "post_author"
    C_AUTHOR = "comment_author"

    def setUpTest(self):
        '''Create dummy post author, post, and visiting user for testing.
        '''
        # set dummy post author
        self._createDummyUser(self.P_AUTHOR, "test_password")
        # set dummy post
        self._createDummyPost(self.P_AUTHOR, "test_subject", "test_content")
        # set comment author
        self._createDummyUser(self.C_AUTHOR, "test_password2")

    def _setPostRequest(self, author, content, post_key):
        '''Create a request and generate a response from the application.
        @param author: the user to set as post author
        @param content: the str that will be the comment content
        @param post_key: the url NDB key for the blog post entity
        '''
        postDict = {blog.CONTENT : content}
        headersList = [("Cookie",
                        util.CookieUtil._format_cookie(blog.USER, author))]
        return blog.app.get_response("/blog/post_id/" + post_key + "/comment",
                                     POST=postDict,
                                     headers=headersList)

    def testNewCommentDBCorrectness(self):
        '''Tests correctly adding a new comment to a post. 
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
        self.assertEqual(post_key.get().comments_made, 2)
        self._setPostRequest(self.C_AUTHOR, "3d comment_content",
                             post_key.urlsafe())
        self.assertEqual(post_key.get().comments_made, 3)


    def testInputVerification(self):
        '''Test no input into comment form.
        '''
        self.setUpTest()
        # there is only 1 blog post, so it's 1 by default
        post_key = ndb.Key("User", self.P_AUTHOR, "BlogPost", "1")
        # set post response
        response = self._setPostRequest(self.C_AUTHOR, "",
                                        post_key.urlsafe())
        self.assertTrue("You must include some content." in response.body,
                        "Test should raise missing content error msg.")

    def testNoUserLoggedIn(self):
        '''Test making comment with no user logged in.
        '''
        # test what happens when a user is not logged in
        self.setUpTest()
        post_key = ndb.Key("User", self.P_AUTHOR, "BlogPost", "1").urlsafe()
        response = blog.app.get_response("/blog/post_id/" + post_key +
                                         "/comment")
        self.assertEqual(response.location, "http://localhost/blog/signup",
                   "failure to be signed in did not redirect correctly (get)")

class testLoginLogout(TestBlog):
    '''
    Class to test logging in and out.
    Attributes:
        REALUSER - user name of the real user
        FAKEUSER - user name that does not exist
        ACTUALPWD - correct password for REALUSER
    '''
    
    REALUSER = "realuser"
    FAKEUSER = "fakeuser"
    ACTUALPWD = "12345"

    def _setPostRequest(self, username, password):
        '''Sets up a POST request via the login form and generates a response.
        Tests in this class check the correctness of the response.
        @param username: the username to enter into the login form
        @param password: the password to enter into the login form
        '''
        postDict = {blog.USER : username, blog.PASSWORD : password}
        return blog.app.get_response(blog.LOGIN, POST=postDict)

    def testLogin(self):
        '''Test vanilla login with correct username and password.
        Make sure page redirects correctly.
        '''
        self._createDummyUser(self.REALUSER, self.ACTUALPWD)
        response = self._setPostRequest(self.REALUSER, self.ACTUALPWD)
        self.assertEqual(response.location, "http://localhost" + blog.WELCOME,
                   "successful signup did not redirect to welcome page." +
                   " Location was " + response.location)

    def testBagLogin(self):
        '''Test login with incorrect username. Make sure correct error msg
        is displayed.
        '''
        self._createDummyUser(self.REALUSER, self.ACTUALPWD)
        response = self._setPostRequest(self.FAKEUSER, self.ACTUALPWD)
        self._testInResponseBody("That user does not exist.", response)

    def testLoginBadPassword(self):
        '''Tests the result of loggin in with the incorrect password for a given
        username.
        '''
        self._createDummyUser(self.REALUSER, self.ACTUALPWD)
        response = self._setPostRequest(self.REALUSER, "wrong_password")
        self._testInResponseBody("Incorrect password.", response)

    def testGarbageUsername(self):
        '''Tests a username that should be caught by regex input verification.
        '''
        response = self._setPostRequest("a", self.ACTUALPWD)
        self._testInResponseBody("The username is invalid.", response)

    def testGarbagePassword(self):
        '''Tests a password that should be caught by regex input verification.
        '''
        response = self._setPostRequest(self.REALUSER, "a")
        self._testInResponseBody("The password is invalid.", response)

    def testLogout(self):
        '''Tests logging out a logged in user.
        '''
        headerList = [("Cookie",
                       util.CookieUtil._format_cookie(blog.USER, self.REALUSER)
                       )]
        response = blog.app.get_response(blog.LOGOUT, headers=headerList)
        self.assertEqual(response.location, "http://localhost" + blog.SIGN_UP,
                   "successful logout did not redirect to signup page." +
                   " Location was " + response.location)

    def testLogoutWhileLoggedOut(self):
        '''Test effect of logging out while not logged in.
        '''
        response = blog.app.get_response(blog.LOGOUT)
        self.assertEqual(response.location, "http://localhost" + blog.SIGN_UP,
                   "successful logout did not redirect to signup page." +
                   " Location was " + response.location)

    def testLoginLogoutLogin(self):
        '''Test logging in, out, and back in.
        '''
        self._createDummyUser(self.REALUSER, self.ACTUALPWD)
        response = self._setPostRequest(self.REALUSER, self.ACTUALPWD)
        self.assertEqual(response.location, "http://localhost" + blog.WELCOME,
                   "successful signup did not redirect to welcome page." +
                   " Location was " + response.location)
        # logout
        headerList = [("Cookie",
                       util.CookieUtil._format_cookie(blog.USER, self.REALUSER)
                       )]
        response = blog.app.get_response(blog.LOGOUT, headers=headerList)
        self.assertEqual(response.location, "http://localhost" + blog.SIGN_UP,
                   "successful logout did not redirect to signup page." +
                   " Location was " + response.location)
        # login
        response = self._setPostRequest(self.REALUSER, self.ACTUALPWD)
        self.assertEqual(response.location, "http://localhost" + blog.WELCOME,
                   "successful signup did not redirect to welcome page." +
                   " Location was " + response.location)


class testLikeUnlike(TestBlog):
    '''
    Class of tests for liking and unliking posts.
    Attributes:
        POST_AUTHOR: mock author name of post author
        OTHER_USER: mock user name of another user
        PASSWORD: password used in these tests
    '''
    
    POST_AUTHOR = "p_author"
    OTHER_USER = "other_user"
    PASSWORD = "ttt"


    def _setupTest(self):
        '''Set up mock user account for post author, make a mock post, and 
        set up a mock user account for other.
        '''
        self._createDummyUser(self.POST_AUTHOR, self.PASSWORD)
        self._createDummyUser(self.OTHER_USER, self.PASSWORD)
        self._createDummyPost(self.POST_AUTHOR, "mock subject", "mock_content")

    def _getMockPostKeyStr(self):
        '''Returns the mock post's ndb Key object in url safe key string format. 
        '''
        return ndb.Key("User", self.POST_AUTHOR, "BlogPost", "1").urlsafe()

    def _get_MockPostEntity(self):
        '''Returns the mock post entity. Assumes there is only 1 mock post.
        '''
        return ndb.Key(urlsafe=self._getMockPostKeyStr()).get()

    def _setLikeResponse(self, liking_user, login_user=True):
        '''Generates an appropriate like response from the application.
        @param liking_user: the string username of the user liking the post
        @param login_user: defaults to True, will log in the liking user. Set
        to false to test the application with a logged out liking user.
        '''
        headerList = []
        if login_user:
            headerList = [("Cookie",
                       util.CookieUtil._format_cookie(blog.USER, liking_user))]
        post_key = self._getMockPostKeyStr()
        return blog.app.get_response("/blog/post_id/" + post_key,
                                     headers=headerList,
                                     POST={"like_post" :
                                           "like_post_" + post_key})

    def testLikeVanilla(self):
        '''Liking user is logged in, post is not liking user's post, post is 
        yet to be liked by the liking user.
        '''
        self._setupTest()
        response = self._setLikeResponse(self.OTHER_USER)
        # unlike should be in the response body
        self.assertTrue("Unlike" in response.body, "Unlike is not present in" +
                   " the body of the response. Response was:" + response.body)
        # the post key should be in the response body
        self.assertTrue(self._getMockPostKeyStr() in response.body, "Url safe key is" +
                   " not present in the body of the response. Response was:" +
                   response.body)
        # other user should be in the post's users liked list
        self.assertTrue(self.OTHER_USER in self._get_MockPostEntity().users_liked,
                   "Liking user not present in list of users who have liked" +
                   " post.")

    def testUnlikeVanilla(self):
        '''Liking user is logged in, post is not liking user's post, post has
        been liked already by liking user.
        '''
        self._setupTest()
        # like post
        response = self._setLikeResponse(self.OTHER_USER)
        self.assertTrue(self.OTHER_USER in self._get_MockPostEntity().users_liked,
                   "Liking user not present in list of users who have liked" +
                   " post.")
        self.assertTrue("Unlike" in response.body, "Unlike is not present in" +
                   " the body of the response. Response was:" + response.body)
        # unlike post
        response = self._setLikeResponse(self.OTHER_USER)
        self.assertTrue(self.OTHER_USER not in self._get_MockPostEntity().users_liked,
                   "Liking user should not be present in list of users who have liked" +
                   " post.")
        self.assertTrue("Like" in response.body, "Like is not present in" +
                   " the body of the response. Response was:" + response.body)

    def testLikeOwnPost(self):
        '''Liking user is logged in, is post's author.
        '''
        # in some test cases there is a problem with escaped apostrophes
        # this is a standing issue. It does not appear outside of the
        # test suite
        ERROR_MSG = "You can&#39;t be a post&#39;s author to like a post"
        self._setupTest()
        response = self._setLikeResponse(self.POST_AUTHOR)
        self.assertTrue(ERROR_MSG in response.body, "Error msg incorrect" +
                        " for liking own post." + response.body)
        self.assertTrue(self.POST_AUTHOR not in self._get_MockPostEntity().users_liked,
                   "Liking user should not be present in list of users who have liked" +
                   " post.")


    # test for attempting to like post while logged in
    def testLikeLoggedOut(self):
        '''Liking user is logged out. Liking user is not post author.
        '''
        ERROR_MSG = "You must be logged in to like a post"
        self._setupTest()
        response = self._setLikeResponse(self.OTHER_USER, False)
        self.assertTrue(ERROR_MSG in response.body, "Error msg incorrect" +
                        " for liking post while logged out." + response.body)

        response = self._setLikeResponse(self.POST_AUTHOR, False)
        self.assertTrue(ERROR_MSG in response.body, "Error msg incorrect" +
                        " for liking post while logged out." + response.body)

class testPwdUtil(TestBlog):
    '''Tests the password utility functions. Tests results of using a unicode
    vs. ASCII password.
    Attributes:
        unicodePwd: a unicode password
        bytesPwd: an ASCII string password
    '''
    unicodePwd = u"abc123"
    bytesPwd = "abc123"

    def testMixedUnicodeBytes(self):
        '''Tests mixed unicode and strings.
        '''
        pwd_helper = util.PwdUtil(self.unicodePwd)
        db_password = pwd_helper.new_pwd_salt_pair()
        self.assertTrue(type(db_password), "unicode")

        pwd_helper2 = util.PwdUtil(self.unicodePwd, db_password)
        self.assertTrue(pwd_helper2.verify_password())

class testPostEditing(TestBlog):
    '''
    Class to test editing posts functionality. Class fields are constants
    used in testing.
    '''
    AUTHOR = "post_author"
    SUBJECT = "test_subject"
    CONTENT = "test_content"
    PASSWORD = "some_pwd"
    OTHER_USER = "other_user"
    EDITED_CONTENT = CONTENT + "edited"
    EDITED_SUBJECT = SUBJECT + "edited"

    def _setupTest(self):
        '''Set up mock user account for post author, make a mock post, and 
        set up a mock user account for other.
        '''
        self._createDummyUser(self.AUTHOR, self.PASSWORD)
        self._createDummyUser(self.OTHER_USER, self.PASSWORD)
        self._createDummyPost(self.AUTHOR, self.SUBJECT, self.CONTENT)

    def _getMockPostKeyStr(self):
        '''Returns the mock post's ndb Key object in url safe key string format. 
        '''
        return ndb.Key("User", self.AUTHOR, "BlogPost", "1").urlsafe()

    def _get_MockPostEntity(self):
        '''Returns the mock post entity. Assumes there is only 1 mock post.
        '''
        return ndb.Key(urlsafe=self._getMockPostKeyStr()).get()


    def setPostRequest(self, username, subject, content):
        '''Method that sets the response to test. 
        @param username is the username that will have a cookie set to be
        logged in
        @param subject and 
        @param content are the subject and content of the new post.
        '''
        postDict = {blog.SUBJECT : subject,
                    blog.CONTENT : content}
        headersList = [("Cookie",
                        util.CookieUtil._format_cookie(blog.USER, username))]
        post_id = self._getMockPostKeyStr()
        return blog.app.get_response("/blog/post_id/" + post_id + "/edit",
                                     POST=postDict,
                                     headers=headersList)

    def testVanillaEdit(self):
        '''Tests editing a post with the correct user and input.
        '''
        self._setupTest()
        self.setPostRequest(self.AUTHOR, self.EDITED_SUBJECT,
                                       self.EDITED_CONTENT)
        cur_post = self._get_MockPostEntity()
        self.assertEqual(cur_post.post_subject, self.EDITED_SUBJECT)
        self.assertEqual(cur_post.post_content, self.EDITED_CONTENT)

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
