'''
Created on Jan 7, 2017

@author: kennethalamantia
'''
import os
import re

import jinja2
import webapp2
from google.appengine.ext import db
import cookie_validator

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
JINJA = jinja2.Environment(loader = jinja2.FileSystemLoader(TEMPLATE_DIR),
                               extensions=['jinja2.ext.autoescape'],
                               autoescape=True)
MAIN_PAGE = "blog.html"
NEW_POST = "newpost.html"
NEW_POST_DISPLAY = "new_post_display.html"
SIGNUP_TEMPLATE = "login_template.html"
WELCOME_TEMPLATE = "welcome.html"

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

class BlogPost(db.Model):
    '''
    Class to describe the entity used to store blog entries in the data store.
    This entity has three properties, the title of the post, the text body 
    content of the post, and the time the post is created.
    '''
    post_title = db.StringProperty(required = True)
    post_body = db.TextProperty(required = True)
    post_time = db.DateTimeProperty(auto_now_add=True)
    
class User(db.Model):
    name = db.StringProperty(required = True)
    password = db.StringProperty(required = True)
        
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
            if not self.is_valid(raw_inputs[input], input):
                output_strings[input + "_error"] = "Invalid input."
                output_strings[input] = raw_inputs.get(input)
                self.valid_input = False
            else:
                output_strings[input] = raw_inputs.get(input)
        return output_strings
        
    def is_valid(self, input, regex_key):
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
    def __init__(self, request, response):
        self.initialize(request, response)
        self.INPUT_MAP = {"username" : r"^[a-zA-Z0-9_-]{3,20}$",
                          "password" : r"^.{3,20}$",
                          "verify" : r"^.{3,20}$",
                          "email" : r"^[\S]+@[\S]+.[\S]+$"
                          }

    def get(self):
        self.render(SIGNUP_TEMPLATE)
        
    def post(self):
        self.valid_input = True
        self.output_map = dict()
        input_map = self.get_inputs(self.INPUT_MAP.iterkeys())
        self.validate_form_data(input_map, self.output_map)
        self.passwords_match(input_map, self.output_map)
        to_render = self.output_map
        
        if not self.valid_input:
            self.render(SIGNUP_TEMPLATE, **to_render)
        else:
            self.set_cookie("name", to_render.get("username"))
            self.set_cookie("password", to_render.get("password"))
            self.redirect("/blog/welcome")
    
    def set_cookie(self, cookie_name, cookie_value):
        self.response.headers.add_header(
            "Set-Cookie", cookie_validator.format_cookie(cookie_name, 
                                                        cookie_value))
    
    def is_valid(self, data, re_input_key):
        '''
        If returns true if the data is valid, false otherwise.
        '''
        pattern = re.compile(self.INPUT_MAP[re_input_key])
        return pattern.match(data)
    
    def get_inputs(self, input_list):
        '''
        Gets the data entered in the text and password inputs. Stores the input
        in a dictionary.
        INPUT_MAP key : string value entered.
        '''
        output_map = dict()
        for input in input_list:
            output_map[input] = self.request.get(input)
        return output_map
    
    def validate_form_data(self, input_map, output_map):
        '''
        Checks each input form element to make sure it matches the specified
        requirements and updates the appropriate form output. If the input
        is not correct, generates an error message.
        '''
        for key in input_map:
            if not self.is_valid(input_map[key], key):
                if key == "email" and input_map[key] == "":
                    continue
                self.valid_input = False
                output_map[key + "_error"] = self.generate_invalid_response(key)
                output_map[key] = ""
            else:
                output_map[key] = input_map[key]
                
    def passwords_match(self, input_map, output_map):
        '''
        Check whether input password and verify fields match.
        '''
        if not input_map["password"] == input_map["verify"]:
            output_map["password_error"] = "Passwords don't match"
            self.valid_input = False
        
    def generate_invalid_response(self, input_type):
        response = "That's not a valid {type}."
        return response.format(type = input_type)
    
class Welcome(Handler):
    def get(self):
        name_cookie = self.request.cookies.get("name")
        if name_cookie:
            if cookie_validator.validate_hash(name_cookie):
                username = cookie_validator.get_value(name_cookie)
                self.render(WELCOME_TEMPLATE, username = username)  
        
app = webapp2.WSGIApplication([('/blog', BlogMainPage),
                               ('/blog/newpost', NewPost),
                               (r'/blog/post_id/(\d+)', NewPostDisplay),
                               ('/blog/signup', Signup),
                               ('/blog/welcome', Welcome)], debug=True)

