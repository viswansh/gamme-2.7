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
import logging
import re
import webapp2
import StringIO
import urllib


from helpers import Bunch, getTopText, getTopAttribute, insert_with_priority
from oauth2_plugin import oauth2_plugin
from boto.exception import S3ResponseError
from boto.pyami.config import Config
from google.appengine.api import users, files
from xml.dom.minidom import parseString


## Jinja2 for HTML templating ##
jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

def errorhandler(handler, error):
    error_str = '<span STYLE=\"color: rgb(100%, 0%, 0%)\">' + error + '</span>'
    template_values = { 'error_str' : error_str}
    template = jinja_environment.get_template('index.html')
    handler.out.write(template.render(template_values))


class GammeParserHelper():
    """
    Helper class to make parse dom status/error messages
    and also maintains display header information
    """
    error_table_header = ['MessageSubject', 'ErrorMessage', 'SentTime', 'MessageSize']

    def make_email_tuple(self, dom_message):
        subject=getTopText(dom_message, 'MessageSubject')
        errormsg=getTopText(dom_message, 'ErrorMessage')
        senttime=getTopText(dom_message, 'SentTime')
        size=getTopAttribute(dom_message, 'MessageSize', 'value')
        if subject.strip() != '':
            return (subject, errormsg, senttime, size)
        return None

    def set_dict(self, dict, key, val):
        if key in dict:
            dict[key].append(val)
        else:
            dict[key] = [self.error_table_header]
            dict[key].append(val)

    def process_email_stats(self, dom):
        success = 0
        failed  = 0
        for folders in dom.getElementsByTagName('FolderList'):
            success += int(folders.getElementsByTagName('SuccessCount')[0].getAttribute('value'))
            failed += int(folders.getElementsByTagName('FailCount')[0].getAttribute('value'))
        return Bunch(success=success, failed=failed)

class MainPage(webapp2.RequestHandler):
    """ 
    Main page request Handler
    Simple renders intial page
    """
    def get(self):
        user_id = " "
        template_values = { 'user_text' : user_id }
        template = jinja_environment.get_template('index.html')
        self.response.out.write(template.render(template_values))

class QueryUser(webapp2.RequestHandler):
    """ 
    Request Handler for queryuser 
    requests user status files from gs cloud storage
    parses the xml file and retrieves error messages
    """
    def get(self):
        userid = self.request.get('userid')
        
        #  Sanity checks #
        """ Testing for empty user string """
        if userid.strip() == '':
            errorhandler(self.response,'Empty User ID')
            return
        
        """ Testing for valid results """
        result_bunch = gscloud.get_userobjects(userid)
        if len(result_bunch.result) == 0:
            errorhandler(self.response,'User Status files not found')
            return
        
        pids = ''
        success = 0
        failed  = 0
        stats   = []
        errors_dict = {}
        template_values = {}
        gamma_helper = GammeParserHelper()
        for object in result_bunch.result:
            dom = parseString(object.obj_uri.get_contents_as_string())
            user = getTopText(dom, 'SourceUser')
            if user != userid:
                pass
            ## Finding status ##
            pids = pids + ' ' + object.pid
            main_status = dom.getElementsByTagName('MigrationStatus')[0].getAttribute('value')
            insert_with_priority(template_values, 'main_status', main_status, config.Status_priority)
            for category in config.Migration_categories:
                d = dom.getElementsByTagName(category + 'MigrationStatus')
                if d == None:
                    pass
                key = category + '_status'
                template_values[key] = d[0].getElementsByTagName('MigrationStatus')[0].getAttribute('value')
                if category == 'Email':
                   bunch = gamma_helper.process_email_stats(d[0])
                   success += bunch.success
                   failed  += bunch.failed
                   ## Find detailed error message report ##
                   failed_msgs = d[0].getElementsByTagName('FailedMessages')
                   if failed_msgs == None:
                       pass
                   for message in failed_msgs:
                     tuple = gamma_helper.make_email_tuple(message)
                     if tuple != None:
                         matched = False
                         for error_pattern in config.Error_categories:
                             if re.match(error_pattern, tuple[1]):
                                 error_cat = config.Error_categories[error_pattern]
                                 gamma_helper.set_dict(errors_dict, error_cat, tuple)
                                 matched = True
                                 break;
                         if matched == False:
                             error_cat = 'Other failed messages'
                             gamma_helper.set_dict(errors_dict, error_cat, tuple)
        i = 1
        errors_results = []
        for key in errors_dict:
            uri_link = key + ' (' + str(len(errors_dict[key])) +')'
            errors_results.append((uri_link, 'link_' + str(i), 'div_' + str(i), errors_dict[key])) 
            i += 1
        
        stats.append('Messages Migrated: ' + str(success))
        stats.append('Messages Failed: ' + str(failed))
        stats.append('Percentage Success: ' + str(success*100/(success+failed)))
        
        """ template values used by jijna2 to render index.html"""
        template_values['user_name']  = userid
        template_values['email_stats']   = stats
        template_values['error_results'] = errors_results
        template_values['pids'] = pids
        
        template = jinja_environment.get_template('index.html')
        self.response.out.write(template.render(template_values))


app = webapp2.WSGIApplication([('/', MainPage),
                               ('/queryuser',   QueryUser)],
                                debug=True)
