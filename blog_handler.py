'''
Created on Jan 7, 2017

@author: kennethalamantia
'''
import os
import re

import jinja2
import webapp2
from google.appengine.ext import db

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
JINJA = jinja2.Environment(loader = jinja2.FileSystemLoader(TEMPLATE_DIR),
                               extensions=['jinja2.ext.autoescape'],
                               autoescape=True)
MAIN_PAGE = "blog.html"
NEW_POST = "newpost.html"

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
        
class Blog(Handler):
    pass

class NewPost(Handler):
    
    def get(self):
        self.render(NEW_POST)
        
    def post(self):
        self.valid_input = True
        raw_inputs = self.get_form_inputs()
        to_render = self.verify_inputs(raw_inputs)
        if not self.valid_input:
            self.render(NEW_POST, **to_render)
        else:
            self.write("Thanks!")
        
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
        

        
app = webapp2.WSGIApplication([('/blog', Blog),
                               ('/newpost', NewPost)],
                              debug=True)