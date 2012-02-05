"""
pyVersion  2.7
google_app version 1.6.2
"""

from __future__ import with_statement

import os

os.environ['BOTO_CONFIG'] = 'boto.cfg'
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

import boto
import cgi
import config
import gscloud
import jinja2
import webapp2
import StringIO
import urllib

from oauth2_plugin import oauth2_plugin
from boto.exception import S3ResponseError
from boto.pyami.config import Config
from google.appengine.api import users, files

### uses Jinja2 for HTML templating ####
jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

### Main Page Request Handler ###
class MainPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        user_id = ""
        if user:
            user_id = user.user_id()
        template_values = { 'user_text' : user_id }
        template = jinja_environment.get_template('index.html')
        self.response.out.write(template.render(template_values))

### Query user ###
class QueryUser(webapp2.RequestHandler):
    def get(self):
        self.response.out.write('<h2>under construction</h2>')


class CloudAccess(webapp2.RequestHandler):
    def get(self):
        result_bunch = gscloud.get_userobjects('craftd')
        if result_bunch.result != None:
            self.response.out.write('<body>' + str(result_bunch.result) + '</body>')
        else:
            self.response.out.write('<body>' + str(result_bunch.error) + '</body>')            



app = webapp2.WSGIApplication([('/', MainPage),
                               ('/queryuser',   QueryUser),
                               ('/cloudaccess', CloudAccess)],
                                debug=True)
