import re
from django.core.exceptions import ImproperlyConfigured
from django.forms.widgets import Media


from django.utils.safestring import mark_safe
from django.templatetags.static import static
from django.utils.html import conditional_escape, html_safe, format_html


class MenuItem:
    str_tmpl = None
    #attrs = {}

    #def __init__(self, attrs=None):
        #if attrs is not None:
        #    self.attrs = attrs.copy()

    #? handy?
    def absolute_path(self, path):
        """
        Given a relative or absolute path to a static asset, return an absolute
        path. An absolute path will be returned unchanged while a relative path
        will be passed to django.templatetags.static.static().
        """
        if path.startswith(('http://', 'https://', '/')):
            return path
        return static(path)

    #! don't duplicate with menu
    #def _build_attrs(self, attrs):
        #b = []         
        #for k,v in attrs.items():
            #b.append('{0}="{1}"'.format(k, v))
        #return ' '.join(b)
        
    #def append_css_class(self, name):
        #if ('class' not in self.attrs):
            #self.attrs['class'] = name
        #else:
            #self.attrs['class'] = '{} {}'.format(self.attrs['class'], name)
 
    def get_context(self, path):
        pass
        
    def render(self, path=None):
        ctx = self.get_context(path)
        return mark_safe(self.str_tmpl.format(**ctx))



class URLMenuItem(MenuItem):
    #? will be absolute
    #? will test for nothing? But then not run validators?
    def prepare_url(self, url):
        return url
        
    def run_validators(self, url):
        validated = True
        for v in self.validators:
            try:
                v(url)
            except ValidationError as e:
                validated = False
        return validated

    def clean(self):
        if (self.url is None):
            self.clean_url = '#'   
        else:
            url = self.prepare_url(self.url)
            self.valid = self.run_validators(url)
            self.clean_url = url
        
    def _rend_icon(self, icon_ref):
        #icon = '<img class="menu-item-icon">' 
        icon = '<svg class="menu-item-icon" xmlns="http://www.w3.org/2000/svg" width="0" height="0" viewBox="0 0 0 0" ></svg>'
        if (icon_ref is not None):
            icon = '<img class="menu-item-icon" src="{}" />'.format(
            icon_ref
            )
        return icon
        
    def get_context(self, path):
        return dict(
            icon = self._rend_icon(self.icon_ref),
            url = self.clean_url,
            name = conditional_escape(self.name)
        );
        
        
                    
#! must do all the URL/attr gear of URL
class SubMenu(URLMenuItem):
    str_tmpl = '<a href="{url}">{icon}{name}</a>'
    submenu = None
    clean_url = None
    
    def __init__(self, name, url, menu_ref,
            icon_ref=None, 
            expanded=False
        ):
        self.menu_ref = menu_ref
        self.name = name
        self.url = url
        self.icon_ref = icon_ref
        self.expanded=expanded



class Separator(MenuItem):
    str_tmpl = '<hr/>'

    #def __init__(self, attrs=None):
    #    super().__init__(attrs)
    def get_context(self, path):
        return {};  
  
  

  
  
#! need to normalise reverses, external urls, etc?
#? can reverses simply be reverse('news-year-archive', args=(year,))?
class URL(URLMenuItem):
    str_tmpl = '<a href="{url}">{icon}{name}</a>'
    validators = []
    valid = False
    attrs={}
    media = Media()
    clean_url = None
    
    def __init__(self, name, url,
        icon_ref=None, 
        localize=False, 
        disabled=False,
        validators=[],
        attrs={}
        ):
        self.name = name
        self.url = url
        self.icon_ref = icon_ref
        self.localize = localize
        self.disabled = disabled
        if (validators):
            #! chain, if we stick with lists
            self.validators = validators
        self.attrs.update(attrs)
        


    def match_url(self, request):
        """
        match url determines if this is selected
        """
        matched = False
        if (not self.clean_url):
             raise ImproperlyConfigured('match_url requested before validation')
        #if self.exact_url:
        #    if re.match("%s$" % (self.url,), request.path):
        #        matched = True
        #elif re.match("%s" % self.url, request.path):
        if re.match("%s" % self.clean_url, request.path):
            matched = True
        return matched

    #def _rend_icon(self, icon_ref):
        ##icon = '<img class="menu-item-icon">' 
        #icon = '<svg class="menu-item-icon" xmlns="http://www.w3.org/2000/svg" width="0" height="0" viewBox="0 0 0 0" ></svg>'
        #if (icon_ref is not None):
            #icon = '<img class="menu-item-icon" src="{}" />'.format(
            #icon_ref
            #)
        #return icon
        
    #def get_context(self):
        #return dict(
            #icon = self._rend_icon(self.icon_ref),
            #url = self.clean_url,
            #name = conditional_escape(self.name)
        #);


        
class QuerySet():
    queryset = None
    title_field = None
    url_template = None
    use_absolute_url = False
    icon_ref=None, 
    localize=False, 
    disabled=False,
    validators=None,
    attrs={}
        
    def __init__(self, queryset, title_field=None, url_field=None, use_absolute_url=False,
        icon_ref=None, 
        localize=False, 
        disabled=False,
        validators=None,
        attrs={}
    ):
        if (queryset):
            self.queryset = queryset  
        if (not self.queryset):
            raise ImproperlyConfigured("'queryset' attribute required")
        if (url_field):
            self.url_field = url_field
        if (use_absolute_url):
            self.use_absolute_url = use_absolute_url
        if (not(self.url_field or self.use_absolute_url)):
            raise ImproperlyConfigured("'url_field' or 'use_absolute_url' attribute required")
        if (icon_ref):
            self.icon_ref=icon_ref 
        if (localize):
            self.localize=localize 
        if (disabled):
            self.disabled=disabled
        if (validators):
            self.validators=validators
        self.attrs.update(attrs)
        
    def get_menu(self, url):
        menu = []
        for o in self.queryset:
            name = o.title_field
            url = o.get_absolute_url() if (self.use_absolute_url) else o.title_field
            item = URL(name, url,
                icon_ref=self.icon_ref, 
                localize=self.localize, 
                disabled=self.disabled,
                validators=self.validators,
                attrs=self.attrs
                )
            menu.append(item)
        return menu

    @property
    def media(self):
        """Return all media required to render the widgets on this form."""
        return self.media


# May also have
# JavascriptAction?
