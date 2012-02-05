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
from xml.dom.minidom import parseString


### uses Jinja2 for HTML templating ####
jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

### Main Page Request Handler ###
class MainPage(webapp2.RequestHandler):
    def get(self):
        user_id = " "
        template_values = { 'user_text' : user_id }
        template = jinja_environment.get_template('index.html')
        self.response.out.write(template.render(template_values))

### Query user ###
class QueryUser(webapp2.RequestHandler):
    def get(self):
        userid = self.request.get('userid')
        ## test for empty userid ##
        if userid.strip() == '':
            errorhandler(self.response,'Empty User ID')
            return

        ## if not status files available ##
        ## TODO check trace files for additional info ##
        result_bunch = gscloud.get_userobjects(userid)
        if len(result_bunch.result) == 0:
            errorhandler(self.response,'User Status files not found')
            return

        results = []
        for obj_uri in result_bunch.result:
            dom = parseString(obj_uri.get_contents_as_string())
            user = getText(dom.getElementsByTagName('SourceUser')[0].childNodes)
            if user != userid:
                pass
            main_status = dom.getElementsByTagName('MigrationStatus')[0].getAttribute('value')
            results.append('Migration Status: ' + main_status)
            results.append('Messages Migrated: ' + '677')
            results.append('Percentag Success: ' + '98')

        template_values = {'user_name' : user,
                           'results' : results}
            
        template = jinja_environment.get_template('index.html')
        self.response.out.write(template.render(template_values))

        
def getText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

def errorhandler(handler, error):
    error_str = '<span STYLE=\"color: rgb(100%, 0%, 0%)\">' + error + '</span>'
    template_values = { 'error_str' : error_str}
    template = jinja_environment.get_template('index.html')
    handler.out.write(template.render(template_values))

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
