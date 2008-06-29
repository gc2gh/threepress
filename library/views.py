import logging, sys
from zipfile import BadZipfile

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django import oldforms 
from django.contrib.auth.forms import UserCreationForm
from django.contrib import auth

from models import EpubArchive, HTMLFile, UserPref, StylesheetFile, ImageFile, SystemInfo
from forms import EpubValidateForm
from epub import constants as epub_constants
from epub import InvalidEpubException


def register(request):
    form = UserCreationForm()
                                            
    if request.method == 'POST':
        data = request.POST.copy()
        errors = form.get_validation_errors(data)
        if not errors:
            new_user = form.save(data)
            user = auth.authenticate(username=new_user.username, password=request.POST['password1'])
            if user is not None and user.is_active:
                auth.login(request, user)
                return HttpResponseRedirect(reverse('library.views.index'))
    else:
        data, errors = {}, {}

    return render_to_response("auth/register.html", {
        'form' : oldforms.FormWrapper(form, data, errors)
    })


@login_required
def index(request):
    common = _common(request, load_prefs=True)
    user = request.user
    documents = EpubArchive.objects.filter(owner=user)
    return render_to_response('index.html', {'documents':documents, 
                                             'common':common})

@login_required
def profile(request):
    common = _check_switch_modes(request)
    uprofile = common['user'].get_profile()
    sreg = request.openid.sreg

    # If we have the email from OpenID and not in their profile, pre-populate it
    if not common['user'].email and sreg.has_key('email'):
        common['user'].email = sreg['email']
    if sreg.has_key('fullname'):
        uprofile.fullname = sreg['fullname']
    if sreg.has_key('nickname'):
        uprofile.nickname = sreg['nickname']
    if sreg.has_key('timezone'):
        uprofile.timezone = sreg['timezone']
    if sreg.has_key('language'):
        uprofile.language = sreg['language']
    if sreg.has_key('country'):
        uprofile.country = sreg['country']
    uprofile.save()
    common['prefs'] = uprofile
    return render_to_response('auth/profile.html', { 'common':common })

@login_required
def view(request, title, key):
    logging.info("Looking up title %s, key %s" % (title, key))
    common = _check_switch_modes(request)
    document = _get_document(request, title, key)
    
    toc = HTMLFile.objects.filter(archive=document).order_by('order')
    
    return render_to_response('view.html', {'document':document, 
                                            'toc':toc,
                                            'common':common})

def about(request):
    common = _common(request)
    return render_to_response('about.html', {'common': common})
    
@login_required
def delete(request):
    '''Delete a book and associated metadata, and decrement our total books counter'''

    if request.POST.has_key('key') and request.POST.has_key('title'):
        title = request.POST['title']
        key = request.POST['key']
        logging.info("Deleting title %s, key %s" % (title, key))
        if request.user.is_superuser:
            document = _get_document(request, title, key, override_owner=True)
        else:
            document = _get_document(request, title, key)
        _delete_document(request, document)

    return HttpResponseRedirect('/')

@login_required
def profile_delete(request):
    common = _common(request)

    if not request.POST.has_key('delete'):
        # Extra sanity-check that this is a POST request
        logging.error('Received deletion request but was not POST')
        message = "There was a problem with your request to delete this profile."
        return render_to_response('profile.html', { 'common':common, 'message':message})

    if not request.POST['delete'] == request.user.email:
        # And that we're POSTing from our own form (this is a sanity check, 
        # not a security feature.  The current logged-in user profile is always
        # the one to be deleted, regardless of the value of 'delete')
        logging.error('Received deletion request but nickname did not match: received %s but current user is %s' % (request.POST['delete'], request.user.nickname()))
        message = "There was a problem with your request to delete this profile."
        return render_to_response('profile.html', { 'common':common, 'message':message})

    userprefs = _prefs(request)
    userprefs.delete()

    # Decrement our total-users counter
    counter = _get_system_info(request)
    counter.decrement_total_users()

    # Delete all their books (this is likely to time out for large numbers of books)
    documents = EpubArchive.objects.filter(owner=request.user)

    for d in documents:
        _delete_document(request, d)
    

    return HttpResponseRedirect('/') # fixme: actually log them out here

def _check_switch_modes(request):
    '''Did they switch viewing modes?'''
    common = _common(request, load_prefs=True)
    userprefs = common['prefs']

    if request.GET.has_key('iframe'):
        userprefs.use_iframe = (request.GET['iframe'] == 'yes')
        userprefs.save()

    if request.GET.has_key('iframe_note'):
        userprefs.show_iframe_note = (request.GET['iframe_note'] == 'yes')
        userprefs.save()

    return common

@login_required    
def view_chapter(request, title, key, chapter_id):
    logging.info("Looking up title %s, key %s, chapter %s" % (title, key, chapter_id))    
    document = _get_document(request, title, key)

    chapter = get_object_or_404(HTMLFile,archive=document, idref=chapter_id)
    stylesheets = StylesheetFile.objects.filter(archive=document)
    next = _chapter_next_previous(document, chapter, 'next')
    previous = _chapter_next_previous(document, chapter, 'previous')

    parent_chapter = None
    subchapter_href = None

    toc = document.get_top_level_toc()

    for t in toc:
        href = chapter.idref.encode(epub_constants.ENC)
        if href in [c.href() for c in t.find_children()]:
            parent_chapter = t
            subchapter_href = href
            break

    common = _check_switch_modes(request)
        
    return render_to_response('view.html', {'common':common,
                                            'document':document,
                                            'next':next,
                                            'toc':toc,
                                            'subchapter_href':subchapter_href,
                                            'parent_chapter':parent_chapter,
                                            'stylesheets':stylesheets,
                                            'previous':previous,
                                            'chapter':chapter})

def _chapter_next_previous(document, chapter, dir='next'):
    if dir == 'next':
        q = document.htmlfile_set.filter(order__gte=chapter.order+1)
    else :
        q = document.htmlfile_set.filter(order__lte=chapter.order-1).order_by('-order')
    if len(q) > 0:
        return q[0]
    return q

@login_required    
def view_chapter_image(request, title, key, image):
    logging.info("Image request: looking up title %s, key %s, image %s" % (title, key, image))        
    document = _get_document(request, title, key)
    image = get_object_or_404(ImageFile, archive=document, idref=image)
    response = HttpResponse(content_type=image.content_type)
    if image.content_type == 'image/svg+xml':
        response.content = image.file
    else:
        response.content = image.get_data()

    return response

@login_required
def view_chapter_frame(request, title, key, chapter_id):
    '''Generate an iframe to display the document online, possibly with its own stylesheets'''
    document = _get_document(request, title, key)
    chapter = HTMLFile.objects.get(archive=document, idref=chapter_id)
    stylesheets = StylesheetFile.objects.filter(archive=document)
    next = _chapter_next_previous(document, chapter, 'next')
    previous = _chapter_next_previous(document, chapter, 'previous')

    return render_to_response('frame.html', {'document':document, 
                                             'chapter':chapter, 
                                             'next':next,
                                             'previous':previous,
                                             'stylesheets':stylesheets})

@login_required
def view_stylesheet(request, title, key, stylesheet_id):
    document = _get_document(request, title, key)
    logging.info('getting stylesheet %s' % stylesheet_id)
    stylesheet = get_object_or_404(StylesheetFile, archive=document,idref=stylesheet_id)
    response = HttpResponse(content=stylesheet.file, content_type='text/css')
    response['Cache-Control'] = 'public'

    return response

@login_required
def download_epub(request, title, key):
    document = _get_document(request, title, key)
    response = HttpResponse(content=document.get_content(), content_type=epub_constants.MIMETYPE)
    response['Content-Disposition'] = 'attachment; filename=%s' % document.name
    return response

@login_required
def upload(request):
    '''Uploads a new document and stores it in the datastore'''
    
    common = _common(request)
    
    document = None 
    
    if request.method == 'POST':
        form = EpubValidateForm(request.POST, request.FILES)
        if form.is_valid():

            data = form.cleaned_data['epub'].content
            document_name = form.cleaned_data['epub'].filename
            logging.info("Document name: %s" % document_name)
            document = EpubArchive(name=document_name)
            document.owner = request.user
            document.save()
            document.set_content(data)

            try:
                document.explode()
                document.save()
                sysinfo = _get_system_info(request)
                sysinfo.increment_total_books()
                # Update the cache
                #memcache.set('total_books', sysinfo.total_books)

            except BadZipfile:
                logging.error('Non-zip archive uploaded: %s' % document_name)
                logging.error(sys.exc_value)
                message = 'The file you uploaded was not recognized as an ePub archive and could not be added to your library.'
                document.delete()
                return render_to_response('upload.html', {'common':common,
                                                          'form':form, 
                                                          'message':message})
            except InvalidEpubException:
                logging.error('Non epub zip file uploaded: %s' % document_name)
                message = 'The file you uploaded was a valid zip file but did not appear to be an ePub archive.'
                document.delete()
                return render_to_response('upload.html', {'common':common,
                                                          'form':form, 
                                                          'message':message})                
            except:
                # If we got any error, delete this document
                logging.error('Got unknown error on request, deleting document')
                logging.error(sys.exc_value)
                document.delete()
                raise
            
            logging.info("Successfully added %s" % document.title)
            return HttpResponseRedirect('/')

        return HttpResponseRedirect('/')

    else:
        form = EpubValidateForm()        

    return render_to_response('upload.html', {'common':common,
                                              'form':form, 
                                              'document':document})



def _delete_document(request, document):
    # Delete the chapters of the book 
    toc = HTMLFile.objects.filter(archive=document)
    if toc:
        for t in toc:
            t.delete()

    # Delete all the stylesheets in the book
    css = StylesheetFile.objects.filter(archive=document)
    if css:
        for c in css:
            c.delete()

    # Delete all the images in the book
    images = ImageFile.objects.filter(archive=document)
    if images:
        for i in images:
            i.delete()

    # Delete the book itself, and decrement our counter
    document.delete()
    sysinfo = _get_system_info(request)
    sysinfo.decrement_total_books()

def _get_document(request, title, key, override_owner=False):
    '''Return a document by Google key and owner.  Setting override_owner
    will search regardless of ownership, for use with admin accounts.'''
    user = request.user

    document = get_object_or_404(EpubArchive, pk=key)

    if not override_owner and document.owner != user and not user.is_superuser:
        logging.error('User %s tried to access document %s, which they do not own' % (user, title))
        raise Http404

    return document



def _greeting(request):
    if request.user.is_authenticated():
        
        text = ('Signed in as %s: <a href="%s">logout</a> | <a href="%s">edit profile</a>' % 
                (request.user.username, 
                 '/accounts/logout/',
                 reverse('library.views.profile')
                 )
                )
        if request.user.is_superuser:
            text += ' | <a href="%s">admin</a> ' % reverse('library.admin.search')
        return text

    return ("<a name='signin' href=\"%s\">Sign in or register</a>." % '/accounts/login/')


def _prefs(request):
    '''Get (or create) a user preferences object for a given user.
    If created, the total number of users counter will be incremented and
    the memcache updated.'''
    user = request.user
    try:
        userprefs = user.get_profile()
    except UserPref.DoesNotExist:
        logging.info('Creating a userprefs object for %s' % user.username)
        # Create a preference object for this user
        userprefs = UserPref(user=user)
        userprefs.save()

        # Increment our total-users counter
        counter = _get_system_info(request)

        counter.increment_total_users()
  
    return userprefs

def _common(request, load_prefs=False):
    '''Builds a dictionary of common 'globals' 
    @todo cache some of this, like from sysinfo'''

    common = {}
    user = request.user
    common['user']  = user
    common['is_admin'] = user.is_superuser

    # Don't load user prefs unless we need to
    if load_prefs:
        common['prefs'] = _prefs(request)

    #cached_total_books = memcache.get('total_books')

    #if cached_total_books is not None:
    #    common['total_books'] = cached_total_books
    #else:
    #sysinfo = get_system_info()
    #common['total_books'] = sysinfo.total_books
    #memcache.set('total_books', sysinfo.total_books)

    #cached_total_users = memcache.get('total_users')

    #if cached_total_users is not None:
    #    common['total_users'] = cached_total_users
    #else:
    #    if not sysinfo:
    #sysinfo = get_system_info()            
    
    common['total_users'] = _get_system_info(request).get_total_users()
    common['total_books'] = _get_system_info(request).get_total_books()

    #    memcache.set('total_users', sysinfo.total_users)

    common['greeting'] = _greeting(request)

    common['upload_form'] = EpubValidateForm()        
    return common


def _get_system_info(request):
    '''Super-primitive caching system'''
    if not request.session.has_key('system_info'):
        request.session['system_info'] = SystemInfo()
    return request.session['system_info']
    
