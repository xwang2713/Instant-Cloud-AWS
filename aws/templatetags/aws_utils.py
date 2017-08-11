from django.template import Library, Node
from django.template import VariableDoesNotExist, TemplateSyntaxError
from django.core.urlresolvers import resolve, reverse
from django.http import Http404
from aws.utilities import is_admin
from datetime import datetime
from settings import VERSIONS

DOUBLE_SUBMIT ="<div style='display:none'><input type='hidden' name='double_submit_token' value='%s' /></div>"
FORMAT_LINK="<a href='%s'>%s</a>"

register = Library()

@register.filter
def url_name(url_path):
    try:
        match = resolve(url_path)
    except Http404:
        return ''
    return match.url_name

class DoubleSubmitNode(Node):   
    def render(self, context):
        return DOUBLE_SUBMIT % datetime.now()

@register.tag
def double_submit_token(parser, token):
    return DoubleSubmitNode()

class VersionNumberNode(Node):
    def __init__(self, key):
        self.key = key
    def render(self, context):
        return VERSIONS[self.key]
    
@register.tag
def version_number(parser, token):
    try:
        key = token.split_contents()
    except ValueError:
        raise TemplateSyntaxError("tag requires a single argument")    
    return VersionNumberNode(key[1])

class FormatLinkNode(Node):
    def __init__(self, link_text, url_name):
        self.url_name = url_name
        self.link_text = link_text

    def render(self, context):
        
        request = context['request']
        current_path = request.get_full_path()
        url_name = self.url_name
        link_text = self.link_text
        
        try:
            match = resolve(current_path)
            current_url_name = match.url_name
        except Http404:
            return link_text
        
        if url_name == current_url_name:
            return link_text
            
        
        new_link = reverse(url_name)
        
        return FORMAT_LINK % (new_link, link_text)
     
@register.tag
def format_link(parser, token):
    
    try:
        args = token.split_contents()
    except ValueError:
        raise TemplateSyntaxError('tag requires exactly two arguments')
    if len(args) <> 3:
        raise TemplateSyntaxError('tag requires exactly two arguments')
    
    for i, arg in enumerate(args):
        if isinstance(arg, unicode):
            if arg[0] == arg[-1] and arg[0] in ('"', "'"):
                args[i] = arg[1:-1]
    
    return FormatLinkNode(args[1], args[2])

class AdminNode(Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist
   
    def render(self, context):        
        output = self.nodelist.render(context)       
        request = context['request']
        if is_admin(request):
            return output
        else:
            return ''
    
@register.tag
def admin(parser, token):    
    # Only displays nodes between ``{% admin %}`` and ``{% endadmin %}`` if
    # the user is an admin (active and superuser)
    nodelist = parser.parse(('endadmin',))
    parser.delete_first_token()
    return AdminNode(nodelist)    
