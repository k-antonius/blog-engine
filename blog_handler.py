'''
Created on Jan 7, 2017

@author: kennethalamantia
'''
import os
import re

import jinja2
import webapp2
from google.appengine.ext import ndb
from cookie_validator import CookieUtil, PwdUtil

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
JINJA = jinja2.Environment(loader = jinja2.FileSystemLoader(TEMPLATE_DIR),
                               extensions=['jinja2.ext.autoescape'],
                               autoescape=True)
# HTML Filenames
MAIN_PAGE = "blog.html"
NEW_POST = "newpost.html"
NEW_POST_DISPLAY = "new_post_display.html"
SIGNUP_TEMPLATE = "signup_page.html"
WELCOME_TEMPLATE = "welcome.html"
LOGIN_TEMPLATE = "login_page.html"

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
        
    def render_str(self, a, **kw):
        t = JINJA.get_template(a)
        return t.render(kw)
    
    def render(self, *a, **kw):
        self.write(self.render_str(*a, **kw))
    
    def get_attribute(self, type):
        '''
        Returns the value of the specified request type.
        '''
        return self.request.get(type)     
    
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
        
        # ensure the user is in the data base
        # check the password matches the password in the database
        # set the cookie for the user logged in
        if cls.already_exists(form_data.get(USER)):
            return None
        else :
            new_user = User(user_name = form_data.get(USER), 
                            password = form_data.get(PASSWORD), 
                            email= form_data.get(EMAIL), 
                            id = form_data.get(USER),
                            num_posts = 0)
            new_user_key = new_user.put()
            return new_user_key
                            
    @classmethod
    def already_exists(cls, user_name):
        '''
        Checks the database to see whether the user exists. Returns true if 
        is does, false otherwise.
        '''
        if cls.get_by_id(user_name):
            return True
        else:
            return False

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
    
    
    @classmethod
    def create_new_post(cls, subject, content, user_name):
        '''
        Creates a new post in the database, setting its subject, content,
        and author. The key for the post is in the form:
        ("User", user_name, "post_id", post_number) post number is the number
        of posts a given user has made.
        An ndb User entity is the parent of every post.
        '''
        user_key = ndb.Key("User", user_name)
        user = user_key.get()
        post_number = user.num_posts + 1
        new_post = BlogPost(post_subject = subject,
                            post_content = content,
                            post_author = user_name,
                            parent = user_key)
        new_post.key = ndb.Key("User", user_name, "post_id", post_number)
        new_post_key = new_post.put()
        user.num_posts += 1
        assert user.num_posts == post_number
        return new_post_key
    
class Comment(ndb.Model):
    '''
    Parent is the blog post.
    '''
    comment_body = ndb.TextProperty(required = True)
    date_created = ndb.DateTimeProperty(auto_now_add = True)
    last_edited = ndb.DateTimeProperty()
    author = ndb.StringProperty(required = True)
    num_likes = ndb.IntegerProperty()
    

class BlogMainPage(Handler):
    def get(self):
        all_posts = BlogPost.all()
        all_posts.order('date_created')
        self.render(MAIN_PAGE, blog_posts = all_posts)

class NewPost(Handler):
    
    def get(self):
        '''
        Renders the new post form on an initial request.
        '''
        self.render(NEW_POST)
        
    def post(self):
        '''
        Takes input from the new post form, validates the input, and 
        adds a new entity to the database, storing the information from
        the new blog post.
        '''
        
        form_helper = FormInputHelper(INPUTS.iterkeys(), INPUTS, errors, self)
        to_render = form_helper.process_form_inputs()
        if not form_helper.valid_input:
            self.render(NEW_POST, **to_render)
        else:
            new_blog_post = BlogPost(post_title = to_render.get("subject"),
                                     post_body = to_render.get("content"))
            new_db_entry = new_blog_post.put()
            new_db_entry_id = new_db_entry.id() # Use the URL friendly feature!
            
            self.redirect('/blog/post_id/' + str(new_db_entry_id))
        
class NewPostDisplay(Handler):
    def get(self, blog_post_id):
        current_blog_post = BlogPost.get_by_id(long(blog_post_id))
        current_title = current_blog_post.post_title
        current_body = current_blog_post.post_body
        self.render(NEW_POST_DISPLAY, title=current_title, 
                    content=current_body)
        
class Signup(Handler):

    def get(self):
        self.render(SIGNUP_TEMPLATE)
        
    def post(self):
        form_data = self._validate_user_input()
        self._check_user_exists(form_data)
        
        cookie_helper = CookieUtil(self)
        cookie_helper.set_cookie(USER, form_data.get(USER))
        pwd_helper = PwdUtil(form_data.get(PASSWORD))
        form_data[PASSWORD] = pwd_helper.new_pwd_salt_pair()
        User.create_new_user(form_data)
        self.redirect("/blog/welcome")
                
    def _validate_user_input(self):
        '''
        Checks that user input into the signup form is valid. If it is not,
        generates suitable error messages and re-renders the page. If valid,
        returns the data input into the form in a dict keyed to the global
        constants.
        '''
        form_helper = FormHelper(self)
        form_data = form_helper.validate_form_data(USER, PASSWORD, PWD_VERIFY,
                                                  EMAIL)
        if not form_helper.valid_input:
            self.render(SIGNUP_TEMPLATE, **form_data)
        else:
            return form_data
            
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
    
class Welcome(Handler):
    def get(self):
        cookie_helper = CookieUtil(self)
        name_cookie = self.request.cookies.get(USER)
        if name_cookie and (len(cookie_helper.get_value(name_cookie)) > 1):
            if (cookie_helper.validate_hash(name_cookie)):
                username = cookie_helper.get_value(name_cookie)
                self.render(WELCOME_TEMPLATE, username = username)
            else:
                self.redirect("/blog/login")
        else:
            self.redirect("/blog/signup")
                
class Login(Handler):
    def get(self):
        self.render(LOGIN_TEMPLATE)
    
    def post(self):
        # These should be removed now
        form_fields = ["username",
                            "password"]
        regex_map = {"username" : r"^[a-zA-Z0-9_-]{3,20}$",
                          "password" : r"^.{3,20}$"}
        error_map = {"username" : "Please enter a username.",
                     "password" : "Please enter a password."}
        helper = FormInputHelper(form_fields, regex_map, error_map, self)
        to_render = helper.process_form_input()
        if not helper.valid_input:
            self.render(LOGIN_TEMPLATE, **to_render)
        else:
            current_user = User.get_by_id(to_render.get("username"))
            if current_user:
                current_user_pwd = current_user.password
                pwd_helper = PwdUtil(to_render.get("password"),
                                     current_user_pwd) 
                if pwd_helper.verify_password():
                    cookie_helper = CookieUtil(self)
                    cookie_helper.set_cookie("name", to_render.get("username"))
                    self.redirect("/blog/welcome")
                else:
                    to_render["password_error"] = "Incorrect password."
                    self.render(LOGIN_TEMPLATE, **to_render)
            else:
                to_render["username_error"] = "That user does not exist."
                self.render(LOGIN_TEMPLATE, **to_render)
                
class Logout(Handler):
    def get(self):
        cookie_helper = CookieUtil(self)
        cookie_helper.set_cookie("name", "")
        self.redirect("/blog/signup")
        
class FormHelper(object):
    '''
    Class to help process form input.
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
                        PWD_VERIFY : "The passwords don't match.",
                        EMAIL : "Invalid email address.",
                        SUBJECT : "You must have a subject of less than" 
                                   + "100 chars in length.",
                        CONTENT: "Your post must have content."
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
        
    def validate_form_data(self, *args):
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
        
app = webapp2.WSGIApplication([("/blog", BlogMainPage),
                               ("/blog/newpost", NewPost),
                               (r"/blog/post_id/(\d+)", NewPostDisplay),
                               ("/blog/signup", Signup),
                               ("/blog/welcome", Welcome),
                               ("/blog/login", Login),
                               ("/blog/logout", Logout)], debug=True)

