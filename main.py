#!/usr/bin/env python

from google.appengine.api import mail
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler 
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
import time, urllib, os, logging


def baseN(num,b,numerals="0123456789abcdefghijklmnopqrstuvwxyz"): 
    return ((num == 0) and  "0" ) or (baseN(num // b, b).lstrip("0") + numerals[num % b])

class MainHandler(webapp.RequestHandler):

    def get(self):
        user = users.get_current_user()
        if user:
            logout_url = users.create_logout_url("/")
            hooks = MailHook.all().filter('user =', user)
        else:
            login_url = users.create_login_url('/')
        app_id = "mailhooks2" # can we get this dynamically?
        self.response.out.write(template.render('templates/main.html', locals()))

    def post(self):
        if self.request.POST.get('name', None):
            h = MailHook.all().filter('name =', self.request.POST['name']).get()
            h.delete()
        else:
            h = MailHook(hook_url=self.request.POST['url'])
            h.put()
        self.redirect('/')

class MailHandler(InboundMailHandler):
    def receive(self, mail_message):
        to_user = self.get_email_name()
        logging.info("Received a message from: %s to %s", mail_message.sender,
                to_user)
        h = MailHook.all().filter('name =', to_user).get()
        if h:
            params = {
                'subject': mail_message.subject,
                'from': mail_message.sender,
                'to': mail_message.to,
                'date': mail_message.date,
                'text-bodies': [msg.decode() for _, msg in mail_message.bodies("text/plain")],
                'html-bodies': [msg.decode() for _, msg in mail_message.bodies("html/plain")],
            }
            urllib.urlopen(h.hook_url, urllib.urlencode(params, True))

    def get_email_name(self):
        # mail_message.to isn't quite what we want
        # for a bunch of silly reasons. we need to
        # get the "to" data from the self.request.url
        # self.request.url is "http://myserver/_ah/<user>%40<my_app>.appspot.com"
        to_email = self.request.url.split("/")[-1]
        to_email = urllib.unquote(to_email)
        return to_email.split("@")[0] 

class MailHook(db.Model):
    user = db.UserProperty(auto_current_user_add=True)
    hook_url = db.StringProperty(required=True)
    name = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)

    def __init__(self, *args, **kwargs):
        kwargs['name'] = kwargs.get('name', baseN(abs(hash(time.time())), 36))
        super(MailHook, self).__init__(*args, **kwargs)

def main():
    application = webapp.WSGIApplication([
        ('/', MainHandler),
        MailHandler.mapping()], debug=True)
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
