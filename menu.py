import copy
import os

from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse, NoReverseMatch

from .utils import get_callable

from django.conf import settings

from django.forms.widgets import Media, MediaDefiningClass
from django.utils.safestring import mark_safe

from django.utils.html import conditional_escape, html_safe, format_html
from django.core.urlresolvers import resolve

from .manager import MenuManager 
from .items import URL, SubMenu, Separator
from .boundhandler import BoundHandler
from .itemhandlers import SeparatorHandler, URLHandler, SubmenuHandler


# Builtin URL matchers
def EXACT(request_path):
    return request_path

def TAIL1(request_path):    
    return request_path.rsplit(os.sep, 1)[-1]

def TAIL2(request_path):    
    return os.sep.join(request_path.rsplit(os.sep, 2)[-2:])
    
def HEAD1(request_path):  
    #? would fail on empty path?
    return os.sep.join(request_path.split(os.sep, 2)[:2])

def HEAD2(request_path):  
    #? would fail on empty path?
    return os.sep.join(request_path.split(os.sep, 3)[:3])
    
#! media
#! handle empty menus?
#! Needs attrs?
#class Menu(MediaDefiningClass):
class Menu():
    """
    Base class that generates menu list.
    
    @param menu [{menu item}, ...]
    @param trail_key a callable to convert the request path into keys 
    for URL trails. Default is EXACT (all the request path must match 
    the configured URLs)
    @param attrs to add to menu items
    """
    # immutable
    #? maybe for submenus also
    #? what is a good default here? Nothing?
    media = Media()
    #    css = {'all':'/django_menus/dropdown.css'}
    #)

    handlers = {
        SubMenu: SubmenuHandler,
        Separator: SeparatorHandler,
        URL: URLHandler
        }
        
    #disable_invalid_items = False
    disable_invalid_items = True
    attrs = {}
    
    # Two classwide caches
    # {app_name->{menu_name->[bound_items]}
    bound_menu_cache = {}
    # {app_name->{menu_name->{url->[chain of bound items]}}
    url_chain_cache = {}
    #url_chains = {}
        
    def __init__(self, request, 
        menu_name,
        app_name=None,
        disable_invalid=None,
        trail_key=EXACT,
        expand_trail=False,
        select_trail=False,     
        select_leaf=False,     
        attrs={}
        ):
        self.request = request
        #print('..........request:')
        #print(str(request))
        #print(str(menu_name))
        #print('..........menu_name:' + menu_name)
        if (not app_name):
            app_name = resolve(request.path).app_name
            if (not app_name):
                raise ImproperlyConfigured('Not given an app name, and none available from request.') 
        self.app_name = app_name
        self.menu_name = menu_name
        
        #self.path = ''
        # copy to prevent changing the original
        #self.menu = [] if menu is None else copy.deepcopy(menu)
        
        if disable_invalid is not None:
            self.disable_invalid = disable_invalid
        self.trail_key = trail_key
        self.expand_trail = expand_trail
        self.select_trail = select_trail
        self.select_leaf = select_leaf
        self.attrs.update(attrs)
        
        # build initial data
        self.bound_menu = self.get_bound_menu(app_name, menu_name)
        #self.validate(self.bound_menu)

    def get_trail(self):
        '''
        If the request is matched against menu data, get a trail.
        
        @return the trail, or empty trail (list)
        '''
        #? better matches
        trail = []
        #? why bother with the test?
        if (self.expand_trail or self.select_trail or self.select_leaf):
            trails = self.get_trails()
            #print('trails:' + str(trails))
            print('self.request.path_info:' + str(self.request.path_info))
            key = self.trail_key(self.request.path_info)
            t = trails.get(key)
            if (t):
                trail = t
            #trail = self.url_chain_cache[self.app].get(self.request.path_info)
            #trail = self.url_chains.get(self.request.path_info)
        if (self.select_leaf and trail):
            trail = trail[-1:]
        return trail

                                       
    #from django.utils.module_loading import import_string
    #item_class = import_string('django_menus.items.SubMenu')

    #? failing here is another argument for preconsruction?
    def dispatch(self, menu_item_data):
        handler = self.handlers.get(menu_item_data.__class__)
        #if (not handler):
        return BoundHandler(
            handler(),
            menu_item_data
            )

    #! test 'active'
    def _html_output_recursive(self, b, menu, 
        menu_start, 
        menu_end, 
        item_start,
        item_end,
        menu_is_valid=True,
    ):
        '''
        Output HTML.
        Construct the surrounding HTML framework for items.
        Used by as_table(), as_ul(), as_p().
        '''
        visible_count = 0
        #? extra classes: selected, expanded, disabled?, submenu  
        # so triggered by  selected, expanded,
        # validate
        # if printing
        #   extend(chain, valid)
        #   set any extensions
        #       select, if matches
        #       expand, if matches
        #       disable, if invalid
        #   output
        trail = self.get_trail()
        print('trail:' + str(trail))

        for bh in menu:
            valid = bh.validate(self.request, menu_is_valid)
            if (valid or self.disable_invalid_items):
                # ok, print
                
                #print('rend:' + repr(bh))
                #! can be boolean
                visible_count += 1
                
                # extend the data (this sets some dynamic 
                # configuration)
                ctx = bh.get_initial_context(self, valid, trail)

                #? unwanted mess
                html_class_attr = ''
                css_classes = bh.get_wrap_css_classes(ctx)
                if css_classes:
                    html_class_attr = ' class="%s"' % ' '.join(css_classes)
                if (bh.wrap):
                    b.append(item_start.format(attrs=html_class_attr))
                b.append(bh.as_view(ctx))
                #if (isinstance(item, SubMenu)):
                if (hasattr(bh, 'submenu') and bh.submenu):
                    bsub = []
                    count = self._html_output_recursive(bsub, bh.submenu,
                        menu_start,
                        menu_end,
                        item_start,
                        item_end
                    )
                    if (count > 0):
                        b.append(menu_start)
                        b.extend(bsub)
                        b.append(menu_end)
                if (bh.wrap):
                    b.append(item_end)
        return visible_count
            
    def _html_output(self, menu_start, menu_end, item_start, item_end):
        b = []
        self._html_output_recursive(
            b, 
            self.bound_menu, 
            menu_start,
            menu_end,
            item_start,
            item_end
        )
        return mark_safe(''.join(b))

    def as_ul(self):
        "Return this menu rendered as HTML <li>s -- excluding the <ul></ul>."
        return self._html_output(
            menu_start = '<ul>',
            menu_end = '</ul>',
            item_start = '<li {attrs}>',
            item_end = '</li>'
            )

    def as_div(self):
        "Return this menu rendered as HTML <div>s -- excluding a wrapping <div></div>."
        return self._html_output(
            menu_start = '<div class="submenu">',
            menu_end = '</div>',
            item_start = '<div {attrs}>',
            item_end = '</div>'
            )
            
    def __str__(self):
        return self.as_ul()

    def __repr__(self):
        return '<{} disable_invalid_items={}>'.format(
            self.__class__.__name__,
            disable_invalid_items,
            #'menu': ';'.join(self.fields),
        )

    def chains_to_string(self):
        b = ['chains:']
        #for k, v in self.url_chains.items():
            #b.append('  {}->{}'.format(
            #k,
            #str(v)
            #))
        for app in self.url_chain_cache:
            for k, v in self.url_chain_cache[app].items():
                b.append('  {}.{}->{}'.format(
                app,
                k,
                str(v)
                ))
        return '\n'.join(b)
                
    @property
    def media(self):
        """Return all media required to render the items on this menu."""
        media = self.media
        for e in self.menu:
            media = media + e.media
        return media

    def _validate_recursive(self, 
        bound_menu,
        menu_is_valid=True,
        ):
        for bh in bound_menu:
            #bh = self.dispatch(item)
            item_is_valid = bh.validate(menu_is_valid)
            #test
            #if (hasattr(item, 'name') and (item.name == 'TV')):
                #bh.is_valid = False
                #item_is_valid = False
                #bh.set_handler_attr('is_expanded', True)
            #bound_menu.append(bh)
                    
            #submenu recurse
            #if (hasattr(item, 'submenu') and item.submenu):
            if (isinstance(bh, SubMenu)):
                self._validate_recursive(
                    bh.submenu, 
                    (item_is_valid and menu_is_valid),
                )

    #like def full_clean(self):
    #! called where? errors < is_valid < [user control]
    def validate(self, bound_menu):
        """
        Run validations.
        Also generates boundfields.
        Also build menu wide data such as marking descendant hide or 
        disable.
        """
        #self._validate_recursive(self.bound_menu) 
        self._validate_recursive(bound_menu) 
        #print(self.chains_to_string())


    def _bind_recursive(self, 
        menu, 
        bound_menu,
        url_chains,
        url_chain=[]
        ):
        for item in menu:
            bh = self.dispatch(item)
            bound_menu.append(bh)
            
            # chains
            if hasattr(bh.item_data, 'url'):
                url = bh.item_data.url
                if (not isinstance(item, SubMenu)):
                    # NB: this code shallow copies, which is good
                    chain = list(url_chain)
                    chain.append(bh)
                    url_chains[url] = chain 
                    
            #submenu recurse
            if (hasattr(item, 'submenu') and item.submenu):
                #? protect
                url_chain.append(bh)
                self._bind_recursive(
                    item.submenu, 
                    bh.submenu,
                    url_chains, 
                    url_chain
                )
                url_chain.pop()

    def cache_bound_menu(self, app, menu_name):
        '''
        Build the bound-handler and trail caches.
        '''
        if (not (app in self.bound_menu_cache)):
            self.bound_menu_cache[app] = {}            
            self.url_chain_cache[app] = {}            
        if (not (menu_name in self.bound_menu_cache[app])):
            mm = MenuManager()
            menu = mm.get(app, menu_name)
            if (not menu):
                raise ImproperlyConfigured('Unable to find menu configuration. app_name:"{}": menu_name:"{}"'.format(app, menu_name)) 
            bound_menu = []
            url_chains = {}
            self._bind_recursive(menu, bound_menu, url_chains) 
            self.bound_menu_cache[app][menu_name] = bound_menu
            self.url_chain_cache[app][menu_name] = url_chains

    def get_bound_menu(self, app, menu_name):
        r = None
        try:
            r = self.bound_menu_cache[app][menu_name]
        except KeyError:
            self.cache_bound_menu(app, menu_name)
            r = self.bound_menu_cache[app][menu_name]
        return r
        
    #? not properly defended
    def get_trails(self):
        app = self.app_name
        menu_name = self.menu_name
        if (
            (app not in self.bound_menu_cache)
            and (menu_name not in self.bound_menu_cache[app])
        ):
            self.cache_bound_menu(app, menu_name)
        return self.url_chain_cache[app][menu_name]
