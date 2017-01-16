'''
Created on Jan 14, 2017

@author: kennethalamantia
'''

import hashlib
import hmac

KEY = "fatfriend"
class Validator(object):
    
    def __init__(self, handler):
        self.handler = handler
        
    def set_cookie(self, cookie_name, cookie_value):
        self.handler.response.headers.add_header(
            "Set-Cookie", cookie_validator.format_cookie(cookie_name, 
                                                        cookie_value))
    def hash(str_to_hash):
        '''
        Hashes a string value using the hmac algorith using sha256.
        '''
        return hmac.new(KEY, str_to_hash, hashlib.sha256).hexdigest()
    
    def value_and_hash(value):
        '''
        Takes a string value, hashes it and returns a string in the format
        "value|hash"
        '''
        hashed_value = hash(value)
        return_template = "{value}|{hash}"
        return return_template.format(value=value, hash=hashed_value)
    
    def validate_hash(value_w_hash):
        '''
        Takes a cookie value and unknown hash in the format "value|hash",
        re-hashes the value, and returns true if the re-hashed value is 
        equivalent to the unknown hash.
        '''
        value_w_hash = value_w_hash.encode("utf-8")
        value = get_value(value_w_hash)
        unknown_hash = value_w_hash[value_w_hash.index("|")+1:]
        if hash(value) == unknown_hash:
            return True
        else:
            return False
    
    def format_cookie(name, value):
        '''
        Convenience method that returns a formatted cookie.
        '''
        cookie_template = "{name}={value}; Path=/"
        return cookie_template.format(name=name, value = value_and_hash(value))
    
    def get_value(value_w_hash):
        '''
        Given an input in the format "value|hash" extracts and returns only the
        value part preceding the pipe character.
        '''
        slice_idx = value_w_hash.index("|")
        return value_w_hash[:slice_idx]

    


        