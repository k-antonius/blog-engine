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
    

class Handler(webapp2.RequestHandler):
    def __init__(self, request, response):
        self.initialize(request, response)
        
        # HTML Filenames
        self.MAIN_PAGE = "blog.html"
        self.NEW_POST = "newpost.html"
        self.NEW_POST_DISPLAY = "new_post_display.html"
        self.SIGNUP_TEMPLATE = "signup_page.html"
        self.WELCOME_TEMPLATE = "welcome.html"
        self.LOGIN_TEMPLATE = "login_page.html"

        # Form Input Fields
        self.USER = "username"
        self.PASSWORD = "password"
        self.PWD_VERIFY = "pwd_verify"
        self.EMAIL = "email"
        self.SUBJECT = "subject"
        self.CONTENT = "content"
        
        self.ERROR = "_error"
        
        # Form Input Verification regex (type : regex) where type is one
        # of the defined form input fields above.
        self.form_verification_table = {
                                USER : r"^[a-zA-Z0-9_-]{3,20}$",
                                PASSWORD: r"^.{3,20}$",
                                PWD_VERIFY : r"^.{3,20}$",
                                EMAIL: r"(^[\S]+@[\S]+.[\S]+$)|(^(?![\s\S]))",
                                SUBJECT : "^.{1,100}$",
                                CONTENT : "^.{1,}$"
                                }
        # Form Input Verification Error Messages
        self.form_input_error_msgs = {
                            USER : "The username is invalid.",
                            PASSWORD : "The password is invalid.",
                            PWD_VERIFY : "The passwords don't match.",
                            EMAIL : "Invalid email address.",
                            SUBJECT : "You must have a subject of less than" 
                                       + "100 chars in length.",
                            CONTENT: "Your post must have content."
                            }
        
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
    name = ndb.StringProperty(required = True)
    password = ndb.StringProperty(required = True)
    email = ndb.EmailProperty()
    date_created = ndb.DateTimeProperty(auto_now_add = True)
    user_picture = ndb.LinkProperty()
    num_posts = ndb.IntegerProperty()
    
    @classmethod
    def create_new_user(cls, user_name, password, email=None):
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
        if cls.already_exists(user_name):
            return "User already exists."
        else :
            new_user = User(name = user_name, 
                            password = password, 
                            email= email, 
                            id = user_name,
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
            return true
        else:
            return false

class BlogPost(ndb.Model):
    '''
    Parent is the user-author of the post.
    '''
    post_subject = ndb.StringProperty(required = True)
    post_content = ndb.TextProperty(required = True)
    post_author = ndb.StringProperty(required = True)
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
        return new_post_key
    
class Comment(ndb.Model):
    '''
    Parent is the blog post.
    '''
    comment_body = ndb.TextProperty(required = True)
    date_created = ndb.DateTimeProperty(auto_now_add = True)
    last_edited = ndb.DateTimeProperty()
    author = ndb.StringProperty(require = True)
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
    # TODO add user to database when sign up. Check to make sure there isn't
    # already another user with username/email
    # otherwise login page will work even if you don't sign up!
    def __init__(self, request, response):
        self.initialize(request, response)
        

    def get(self):
        self.render(SIGNUP_TEMPLATE)
        
    def post(self):

        helper = FormInputHelper(self.input_to_regex.iterkeys(),
                                 self.input_to_regex,
                                 self.input_to_error,
                                 self,
                                 True)
        to_render = helper.process_form_input()
        
        if not helper.valid_input:
            self.render(SIGNUP_TEMPLATE, **to_render)
        else:
            cookie_helper = CookieUtil(self)
            cookie_helper.set_cookie("name", to_render.get("username"))
            pwd_helper = PwdUtil(to_render.get("password"))
            new_user = User(name = to_render.get("username"),
                            password = pwd_helper.new_pwd_salt_pair(),
                            id = to_render.get("username"))
            new_user.put()
            self.redirect("/blog/welcome")
    
class Welcome(Handler):
    def get(self):
        cookie_helper = CookieUtil(self)
        name_cookie = self.request.cookies.get("name")
        if name_cookie and (len(cookie_helper.get_value(name_cookie)) > 1):
            if (cookie_helper.validate_hash(name_cookie)):
                username = cookie_helper.get_value(name_cookie)
                self.render(WELCOME_TEMPLATE, username = username)
            else:
                self.redirect("/blog/login")
        else:
            self.redirect("/blog/signup")
                
class Login(Handler):
    # add check to make sure user is in database
    def get(self):
        self.render(LOGIN_TEMPLATE)
    
    def post(self):
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
    
        
class FormInputHelper(object):
    '''
    Class to help process form input.
    
    form_fields - a list of the names of form fields. Need to be strings.
    form_regex - a dictionary that maps the name of the form field to the 
                regex matching acceptable input to that field.
    form_errors - dictionary mapping form field names to error messages
    is_signup_form - optional flag, will
    handler_obj - an instance of the webapp2 handler object using this class.
    '''
    
    def __init__(self, form_fields, form_regex, form_errors, handler_obj,
                 is_signup_form = None):
        self.form_fields = {}
        for field_name in form_fields:
            self.form_fields[field_name] = None
        self.form_errors = form_errors
        self.form_regex = form_regex
        self.valid_input = True
        self.output_map = {}
        self.is_signup_form = is_signup_form
        self.handler_obj = handler_obj
        
    def process_form_input(self):
        '''
        Rename this method.
        '''
        self.get_inputs()
        self.validate_form_data()
        if self.is_signup_form:
            self.passwords_match()
        return self.output_map
        
    def _is_valid(self, form_data, field_name):
        '''
        Helper method.
        If returns true if the form_data is valid, false otherwise.
        field_name - name of the form field.
        '''
        pattern = re.compile(self.form_regex[field_name])
        return pattern.match(form_data)
    
    def get_inputs(self):
        '''
        Uses a GET request of handler object to populate the form_fields
        dictionary with the input using put in the form.
        '''
        for field in self.form_fields:
            self.form_fields[field] = self.handler_obj.request.get(field)
        
    
    def validate_form_data(self):
        '''
        Checks each input form element to make sure it matches the specified
        requirements and updates the appropriate form output. If the input
        is not correct, generates an error message.
        '''
        for field_name in self.form_fields:
            if not self._is_valid(self.form_fields.get(field_name), 
                                  field_name):
                
                self.valid_input = False
                self.output_map[field_name + "_error"] = self.form_errors.get(
                                                                    field_name)
                self.output_map[field_name] = ""
            else:
                self.output_map[field_name] = self.form_fields[field_name]
    
    def passwords_match(self):
        '''
        This method only works if the optional is_signup_form argument is 
        passed to the constructor.
        Check whether input password and verify fields match.
        '''
        if not self.form_fields["password"] == self.form_fields["verify"]:
            self.output_map["password_error"] = "Passwords don't match"
            self.valid_input = False
        
app = webapp2.WSGIApplication([("/blog", BlogMainPage),
                               ("/blog/newpost", NewPost),
                               (r"/blog/post_id/(\d+)", NewPostDisplay),
                               ("/blog/signup", Signup),
                               ("/blog/welcome", Welcome),
                               ("/blog/login", Login),
                               ("/blog/logout", Logout)], debug=True)

