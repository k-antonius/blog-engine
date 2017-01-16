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
MAIN_PAGE = "blog.html"
NEW_POST = "newpost.html"
NEW_POST_DISPLAY = "new_post_display.html"
SIGNUP_TEMPLATE = "signup_page.html"
WELCOME_TEMPLATE = "welcome.html"
LOGIN_TEMPLATE = "login_page.html"

# Add regex for form input verification
INPUTS = {"subject" : "^.{1,100}$",
          "content" : "^.{1,}$"}

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
        
    def render_str(self, a, **kw):
        t = JINJA.get_template(a)
        return t.render(kw)
    
    def render(self, *a, **kw):
        self.write(self.render_str(*a, **kw))

class BlogPost(ndb.Model):
    '''
    Class to describe the entity used to store blog entries in the data store.
    This entity has three properties, the title of the post, the text body 
    content of the post, and the time the post is created.
    '''
    post_title = ndb.StringProperty(required = True)
    post_body = ndb.TextProperty(required = True)
    post_time = ndb.DateTimeProperty(auto_now_add=True)
    
class User(ndb.Model):
    name = ndb.StringProperty(required = True)
    password = ndb.StringProperty(required = True)
    email = ndb.StringProperty()
    id = name
        
class BlogMainPage(Handler):
    def get(self):
        all_posts = BlogPost.all()
        all_posts.order('post_time')
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
        self.valid_input = True
        raw_inputs = self.get_form_inputs()
        to_render = self.verify_inputs(raw_inputs)
        if not self.valid_input:
            self.render(NEW_POST, **to_render)
        else:
            new_blog_post = BlogPost(post_title = to_render.get("subject"),
                                     post_body = to_render.get("content"))
            new_db_entry = new_blog_post.put()
            new_db_entry_id = new_db_entry.id()
            
            self.redirect('/blog/post_id/' + str(new_db_entry_id))
        
    def get_form_inputs(self):
        '''
        Helper function to retrieve input from html forms.
        Gets the input fields specified in valid_inputs dictionary.
        '''
        raw_inputs = {}
        for input in INPUTS:
            raw_inputs[input] = self.request.get(input)
        return raw_inputs
    
    def verify_inputs(self, raw_inputs):
        '''
        Takes the dictionary of raw form inputs and verifies that they match
        the regex supplied in INPUTS. The subject input must be betwee 1 and
        100 characters. The content input must be at least 1.
        Returns a dictionary with added error messages if necessary.
        '''
        output_strings = {}
        for input in raw_inputs:
            if not self._is_valid(raw_inputs[input], input):
                output_strings[input + "_error"] = "Invalid input."
                output_strings[input] = raw_inputs.get(input)
                self.valid_input = False
            else:
                output_strings[input] = raw_inputs.get(input)
        return output_strings
        
    def _is_valid(self, input, regex_key):
        '''
        Helper function that returns a boolean value based on whether
        input string matches regex obtained from INPUTS with regex_key.
        '''
        pattern = re.compile(INPUTS[regex_key])
        return pattern.match(input)
        
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
        self.input_to_regex = {"username" : r"^[a-zA-Z0-9_-]{3,20}$",
                          "password" : r"^.{3,20}$",
                          "verify" : r"^.{3,20}$",
                          "email" : r"(^[\S]+@[\S]+.[\S]+$)|(^(?![\s\S]))"
                          }
        self.input_to_error = {"username" : "The username is invalid.",
                               "password" : "The password is invalid.",
                               "verify" : "The verification field is invalid.",
                               "email" : "Invalid email address."}

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
                            password = pwd_helper.new_pwd_salt_pair())
            new_user.put()
            self.redirect("/blog/welcome")
    
class Welcome(Handler):
    def get(self):
        cookie_helper = CookieUtil(self)
        name_cookie = self.request.cookies.get("name")
        if name_cookie:
            if (cookie_helper.validate_hash(name_cookie)):
                username = cookie_helper.get_value(name_cookie)
                self.render(WELCOME_TEMPLATE, username = username)
            else:
                self.redirect("/blog/login")
                
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

            cookie_helper = CookieUtil(self)
            cookie_helper.set_cookie("name", to_render.get("username"))
            self.redirect("/blog/welcome")
        
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
                               ("/blog/login", Login)], debug=True)

