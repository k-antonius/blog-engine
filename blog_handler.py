'''
Created on Jan 7, 2017

@author: kennethalamantia
'''
import os
import re

import jinja2
import webapp2
from google.appengine.ext import ndb
from blog_utilities import CookieUtil, PwdUtil

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
JINJA = jinja2.Environment(loader = jinja2.FileSystemLoader(TEMPLATE_DIR),
                               extensions=['jinja2.ext.autoescape'],
                               autoescape=True)
# HTML Filenames
MAIN_PAGE_TEMPLATE = "blog.html"
NEW_POST_TEMPLATE = "newpost.html"
POST_ONLY_TEMPLATE = "new_post_display.html"
SIGNUP_TEMPLATE = "signup_page.html"
WELCOME_TEMPLATE = "welcome.html"
LOGIN_TEMPLATE = "login_page.html"
COMMENT_TEMPLATE = "new_comment.html"

# URI Routes
HOME = "/blog"
NEWPOST = HOME + "/new_post"
SIGNUP = HOME + "/signup"
WELCOME = HOME + "/user_welcome"
LOGIN =  HOME + "/login"
LOGOUT = HOME + "/logout"
POSTDISPLAY = r"/blog/post_id/(\w+-\w+|\w+)"
NEWCOMMENT = r"/blog/post_id/(\w+-\w+|\w+)/comment"

# Form Input Fields
USER = "username"
PASSWORD = "password"
PWD_VERIFY = "pwd_verify"
EMAIL = "email"
SUBJECT = "subject"
CONTENT = "content"
ERROR = "_error"    

class Handler(webapp2.RequestHandler):
        
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
        
    def render_str(self, *a, **kw):
        t = JINJA.get_template(*a)
        return t.render(**kw)
    
    def render(self, *a, **kw):
        self.write(self.render_str(*a, **kw))
    
    def get_attribute(self, type):
        '''
        Returns the value of the specified request type.
        '''
        return self.request.get(type)
    
    def _check_logged_in(self, route):
        '''
        Checks to make sure correct user is logged in. If not redirects to 
        @param URI route.
        If a user is logged in returns the user's name as a string.
        '''
        # get user name from cookie
        # check to make sure user is logged in
        logged_in_user = CookieUtil.get_cookie(USER, self)
        if not logged_in_user:
            self.redirect(route)
        else:
            return logged_in_user
            
    def _validate_user_input(self, template, *args):
        '''
        Checks that user input into the form is valid. If it is not,
        generates suitable error messages and re-renders the page. If valid,
        returns the data input into the form in a dict keyed to the global
        constants.
        '''
        form_helper = FormHelper(self)
        form_data = form_helper.validate_form_data(args)
        if not form_helper.valid_input:
            self.render(template, **form_data)
        else:
            return form_data     
    
class User(ndb.Model):
    '''
    This is a root entity.
    '''
    user_name = ndb.StringProperty(required = True)
    password = ndb.StringProperty(required = True)
    email = ndb.StringProperty()
    date_created = ndb.DateTimeProperty(auto_now_add = True)
    user_picture = ndb.StringProperty()
    num_posts = ndb.IntegerProperty()
    
    @classmethod
    def create_new_user(cls, form_data):
        '''
        Creates a new user account in the database. If account is successfully
        created returns the user's key. If the user already exists, this 
        method returns a string error message.
        
        @param user_name is a str -- also the id of the key.
        @param password is a str -- the user's password.
        @param email - optional email address
        '''
        if not cls.already_exists(form_data.get(USER)):
            secured_pwd = cls.secure_password(form_data.get(PASSWORD))
            new_user = User(user_name = form_data.get(USER), 
                            password = secured_pwd, 
                            email= form_data.get(EMAIL), 
                            id = form_data.get(USER),
                            num_posts = 0)
            new_user_key = new_user.put()
            return new_user_key
                            
    @classmethod
    def already_exists(cls, user_name):
        '''
        Checks the database to see whether the user exists.
        @param user_name: the string to check
        @return: the user entity or None if no such user exists 
        '''
        return cls.get_by_id(user_name)
        
    
    @classmethod
    def increment_num_posts(cls, user_name):
        '''
        Increment the number of posts this user has made by one, 
        given the user name, the key id of a user entity. Returns the number
        of posts for this user resulting from the increment operation.
        '''
        user_key = ndb.Key("User", user_name)
        user = user_key.get()
        user.num_posts += 1
        user.put()
        return user.num_posts
    
    @classmethod
    def get_num_posts(cls, user_name):
        '''
        Given the key id of this user, returns the number of posts this user
        has made.
        '''
        user_key = ndb.Key("User", user_name)
        user = user_key.get()
        return user.num_posts
    
    @classmethod
    def secure_password(cls, clear_text):
        '''
        Returns a hashed and salted password for storing in database.
        @param clear_text: the clear-text password to make secure
        @return a secure password in the form "hasedpassword,salt"
        '''
        pwd_helper = PwdUtil(clear_text)
        return pwd_helper.new_pwd_salt_pair()

class BlogPost(ndb.Model):
    '''
    Parent is the user-author of the post.
    '''
    post_subject = ndb.StringProperty(required = True)
    post_content = ndb.TextProperty(required = True)
    post_author = ndb.StringProperty(required = True)
    post_number = ndb.IntegerProperty()
    date_created = ndb.DateTimeProperty(auto_now_add = True)
    last_edited = ndb.DateTimeProperty()
    num_likes = ndb.IntegerProperty()
    num_comments = ndb.IntegerProperty()
    
    
    @classmethod
    def create_new_post(cls, user_name, form_data):
        '''
        Creates a new post in the database, setting its subject, content,
        and author. The key for the post is in the form:
        ("User", user_name, "post_id", post_number) post number is the number
        of posts a given user has made.
        An ndb User entity is the parent of every post.
        '''
        
        post_number = User.increment_num_posts(user_name)
        new_post = BlogPost(post_subject = form_data.get(SUBJECT),
                            post_content = form_data.get(CONTENT),
                            post_author = user_name,
                            parent = ndb.Key("User", user_name))
        new_post.post_number = post_number
        new_post.key = ndb.Key("User", user_name, "BlogPost", str(post_number))
        new_post_key = new_post.put()
       
        return new_post_key
    
    @classmethod
    def increment_num_comments(cls, post_entity):
        '''
        Increments the number of comments on this post. The number of 
        comments of a post is also the id of a given child comment entity.
        '''
        if post_entity.num_comments:
            post_entity.num_comments += 1
        else:
            post_entity.num_comments = 1
        post_entity.put()
        return post_entity.num_comments
    
    @classmethod 
    def get_post_key(cls, user_name, post_id):
        '''
        Returns the key object of a post entity given its author and int id.
        '''
        pass 
    
class Comment(ndb.Model):
    '''
    Parent is the blog post.
    '''
    content = ndb.TextProperty(required = True)
    date_created = ndb.DateTimeProperty(auto_now_add = True)
    last_edited = ndb.DateTimeProperty()
    author = ndb.StringProperty(required = True)
    num_likes = ndb.IntegerProperty()
    
    @classmethod
    def create_new_comment(cls, user_name, url_string, form_data):
        '''
        Creates a new comment for a specific post.
        user_name - user making the comment
        post_id - id of blog post user is commenting on
        form_data - dictionary of data from post response
        '''
        parent_key = ndb.Key(urlsafe=url_string)
        parent_post = parent_key.get()
        new_comment = Comment(content = form_data.get(CONTENT),
                              author = user_name,
                              parent = parent_key)
        comment_num = BlogPost.increment_num_comments(parent_post)
        new_comment.key = ndb.Key("Comment", str(comment_num), parent=parent_key)
        new_comment.put()
        return new_comment.key
        
    @classmethod
    def get_comment_key(cls, comment_num, post_key):
        '''
        Returns the key object of a given comment, given its ancestor path
        ids.
        '''
        return ndb.Key("Comment", str(comment_num), parent=post_key)                      

class BlogMainPage(Handler):
    def get(self):
        all_posts = BlogPost.all()
        all_posts.order('date_created')
        self.render(MAIN_PAGE_TEMPLATE, blog_posts = all_posts)

class NewPost(Handler):
    
    def get(self):
        '''
        Renders the new post form on an initial request.
        '''
        self.render(NEW_POST_TEMPLATE)
        user_name = self._check_logged_in(SIGNUP)
        
    def post(self):
        '''
        Takes input from the new post form, validates the input, and 
        adds a new entity to the database, storing the information from
        the new blog post.
        '''
        user_name = self._check_logged_in(SIGNUP)
        if user_name:
            valid_data = self._validate_user_input(NEW_POST_TEMPLATE,
                                               SUBJECT, CONTENT)
            if valid_data:
                new_post_key = BlogPost.create_new_post(user_name, valid_data)
                self.redirect('/blog/post_id/' + new_post_key.urlsafe())
    
        
class NewPostDisplay(Handler):
    def get(self, *args):
        current_blog_post_key = ndb.Key(urlsafe=args[0])
        current_blog_post = current_blog_post_key.get()
        current_title = current_blog_post.post_subject
        current_body = current_blog_post.post_content
        self.render(POST_ONLY_TEMPLATE, subject=current_title, 
                    content=current_body)
        
class Signup(Handler):

    def get(self):
        self.render(SIGNUP_TEMPLATE)
        
    def post(self):
        valid_form_data = self._validate_user_input(SIGNUP_TEMPLATE,
                                                    USER, PASSWORD, PWD_VERIFY,
                                                    EMAIL)
        if valid_form_data:
            self._check_user_exists(valid_form_data)
            CookieUtil.set_cookie(USER, valid_form_data.get(USER), self)
            pwd_helper = PwdUtil(valid_form_data.get(PASSWORD))
            valid_form_data[PASSWORD] = pwd_helper.new_pwd_salt_pair()
            User.create_new_user(valid_form_data)
            self.redirect(WELCOME)
            
    def _check_user_exists(self, form_data):
        '''
        Queries the database to see whether a user with the given username
        exists. If it does it re-renders the page with an appropriate error
        message.
        '''
        if User.already_exists(form_data.get(USER)):
            form_data[USER + ERROR] = ("User already exists. Please" +
                                       " choose another user name.")
            self.render(SIGNUP_TEMPLATE, **form_data)

class NewComment(Handler):
    '''
    Handles new comment requests.
    '''
    def get(self, *args):
        '''
        Renders the new comment html.
        '''
        # need to make a form using the post static html as a base
        self.render(COMMENT_TEMPLATE)
        self._check_logged_in(SIGNUP)
    
    def post(self, *args):
        '''
        Handles form submission of new comment.
        '''
        user_name = self._check_logged_in(SIGNUP)
        if user_name:
            valid_data = self._validate_user_input(COMMENT_TEMPLATE, CONTENT)
            if valid_data:
                post_key_string = args[0]
                new_comment_key = Comment.create_new_comment(user_name,
                                                             post_key_string,
                                                             valid_data)
                self.redirect('/blog/post_id/' + post_key_string)
                                                             
    
class Welcome(Handler):
    def get(self):
        username = CookieUtil.get_cookie(USER, self)
        if username:
            self.render(WELCOME_TEMPLATE, username = username)
        else:
            self.redirect(LOGIN) # Eventually change for to allow 
                                         # for either signup or login
                
class Login(Handler):
    def get(self):
        '''
        Renders the login page. If a user is already logged in, redirects to
        the welcome page.
        '''
        if CookieUtil.get_cookie(USER, self):
            self.redirect(WELCOME)
        self.render(LOGIN_TEMPLATE)
    
    def post(self):
        '''
        Receives data input into login form. Verifies that input against
        regular expressions and then the database. Redirects the user to
        the welcome page if login was successful.
        '''
        valid_form_data = self._validate_user_input(LOGIN_TEMPLATE,
                                                    USER, PASSWORD)
        current_user = self._check_username(valid_form_data)
        if self._check_password(valid_form_data, current_user.password):
            CookieUtil.set_cookie(USER, valid_form_data.get(USER), self)
            self.redirect(WELCOME)
    
    def _check_username(self, form_data):
        '''
        Checks to make sure a user with the username input exists. If not
        re-renders the page with an error message. Returns the user entity
        from the database to use with password checking.
        @param form_data: dictionary containing data from input form
        @return: the user entity
        '''
        user_entity = User.already_exists(form_data.get(USER))
        if user_entity:
            return user_entity
        else:
            form_data["username_error"] = "That user does not exist."
            self.render(LOGIN_TEMPLATE, form_data)
            
    def _check_password(self, form_data, db_password):
        '''
        Checks to make sure form password matches database password.
        Re-renders the form if it is not correct with error msg.
        @param form_data: the data from the input form
        @param db_password: the password for the current user from the database
        '''
        pwd_helper = PwdUtil(form_data.get(PASSWORD), db_password)
        if pwd_helper.verify_password():
            return True
        else:
            form_data["password_error"] = "Incorrect password."
            self.render(LOGIN_TEMPLATE, form_data)
                
class Logout(Handler):
    def get(self):
        '''
        Logs the user out and redirects to the signup page.
        '''
        CookieUtil.set_cookie(USER, "", self)
        self.redirect(SIGNUP)
        
class FormHelper(object):
    '''
    Class to help process form input. 
    @param hander is the Handler sub-class instance using this class.
    '''
    # Form Input Verification regex (type : regex) where type is one
    # of the defined form input fields above.
    def __init__(self, handler):
        self._regex_table = {
                        USER : r"^[a-zA-Z0-9_-]{3,20}$",
                        PASSWORD: r"^.{3,20}$",
                        PWD_VERIFY : r"^.{3,20}$",
                        EMAIL: r"(^[\S]+@[\S]+.[\S]+$)|(^(?![\s\S]))",
                        SUBJECT : "^.{1,100}$",
                        CONTENT : "^.{1,}$"
                        }
        # Form Input Verification Error Messages
        self._error_table = {
                        USER : "The username is invalid.",
                        PASSWORD : "The password is invalid.",
                        PWD_VERIFY : "The passwords do not match.",
                        EMAIL : "Invalid email address.",
                        SUBJECT : "You must have a subject of less than" 
                                   + "100 chars in length.",
                        CONTENT: "You must include some content."
                        }
        self.valid_input = True
        self._handler = handler
        
    def _is_input_valid(self, input_name):
        '''
        Helper method.
        If returns true if the form_data is valid, false otherwise.
        field_name - name of the form field.
        '''
        if input_name == PWD_VERIFY:
            return self._handler.get_attribute(
                            PWD_VERIFY) == self._handler.get_attribute(PASSWORD)
        else:
            pattern = re.compile(self._regex_table[input_name])
            return pattern.match(self._handler.get_attribute(input_name))
        
    def validate_form_data(self, args):
        '''
        Checks each input form element to make sure it matches the specified
        requirements and updates the appropriate form output. If the input
        is not correct, generates an error message.
        '''
        to_render = {}
        for input_name in args:
            if not self._is_input_valid(input_name):
                to_render[input_name + ERROR] = self._error_table.get(input_name)
                to_render[input_name] = ""
                self.valid_input = False
            else:
                to_render[input_name] = self._handler.get_attribute(input_name)
        return to_render
        
app = webapp2.WSGIApplication([(HOME, BlogMainPage),
                               (NEWPOST, NewPost),
                               (POSTDISPLAY, NewPostDisplay),
                               (NEWCOMMENT, NewComment),
                               (SIGNUP, Signup),
                               (WELCOME, Welcome),
                               (LOGIN, Login),
                               (LOGOUT, Logout)], debug=True)

