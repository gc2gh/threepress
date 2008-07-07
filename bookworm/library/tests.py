#!/usr/bin/env python
# encoding: utf-8

import os
import re
import unittest
import logging

from os.path import isfile, isdir

from django.contrib.auth.models import User
from django.test import TestCase as DjangoTestCase

from models import *
from testmodels import *
from epub.toc import TOC
from epub.constants import *

# Data for public epub documents
DATA_DIR = os.path.abspath('./library/test-data/data')

# Local documents should be added here and will be included in tests,
# but not in the svn repository
PRIVATE_DATA_DIR = '%s/private' % DATA_DIR

class TestModels(unittest.TestCase):

    def setUp(self):

        # Add all our test data
        self.documents = [d for d in os.listdir(DATA_DIR) if '.epub' in d and isfile('%s/%s' % (DATA_DIR, d))]

        if isdir(PRIVATE_DATA_DIR):
            self.documents += [d for d in os.listdir(PRIVATE_DATA_DIR) if '.epub' in d and isfile('%s/%s' % (PRIVATE_DATA_DIR, d))] 

        
        self.user = User(username='testuser')
        self.user.save()

    def tearDown(self):
        self.user.delete()

    def testGetAllDocuments(self):
        '''Run through all the documents at a high level'''
        for d in self.documents:
            if d.startswith("invalid"):
                # Test bad documents here?
                pass
            else:
                doc = self.create_document(d)
                doc.explode()

    def testGetTitle(self):
        '''Did we get back the correct title?'''
        title = u'Pride and Prejudice'
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        self.assertEquals(title, document.title)

    def testSingleAuthor(self):
        '''Did we get a single author from our author() method?'''
        author = u'Jane Austen'
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        self.assertEquals(author, document.author())        

    def testGetMultipleAuthors(self):
        '''Do we return the correct number of authors in the correct order?'''
        expected_authors = [u'First Author', u'Second Author']
        opf_file = 'two-authors.opf'
        document = MockEpubArchive(name=opf_file)
        opf = document.xml_from_string(_get_file(opf_file))
        authors = [a.name for a in document.get_authors(opf)]
        self.assertEquals(expected_authors, authors)

    def testGetMultipleAuthorsAsAuthor(self):
        '''Multiple authors should be displayable in a short space.'''
        opf_file = 'two-authors.opf'
        expected_authors = [u'First Author', u'Second Author']
        document = MockEpubArchive(name=opf_file)
        document.owner = self.user
        document.save()
        opf = document.xml_from_string(_get_file(opf_file))
        
        fuzz = 4
        len_first_author = len(expected_authors[0])
        len_short_author_str = len(document.get_author(opf))
        difference = len_short_author_str - len_first_author
        self.assert_(difference < fuzz)

    def testNoAuthor(self):
        '''An OPF document with no authors should return None.'''
        no_author_opf_file = 'no-author.opf'
        no_author_document = MockEpubArchive(name=no_author_opf_file)
        no_author_document.owner = self.user
        no_author_document.save()

        opf = no_author_document.xml_from_string(_get_file(no_author_opf_file))

        author = no_author_document.get_author(opf)
        self.failIf(author)

    def testCreateDocument(self):
        '''Assert that we created a non-None document.'''
        d = self.create_document(self.documents[0])
        self.assert_(d)

    def testFindDocument(self):
        """Documents should be findable by title and author."""
        author = u'Jane Austen'
        title = u'Pride and Prejudice'
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        document.save()
        d = _get_document(title, document.id)
        self.failUnless(d)

    def testBadEpubFails(self):
        """ePub documents with missing compontent should raise errors."""
        filename = 'invalid_no_container.epub'
        document = self.create_document(filename)
        self.assertRaises(InvalidEpubException, document.explode)

    def testSafeName(self):
        """Names should be safely quoted for URLs."""
        name = u'John Q., CommasAreForbidden'
        sn = safe_name(name)
        comma_re = re.compile(",")
        result = comma_re.match(sn)
        self.failIf(result)

    def testCountTOC(self):
        '''Check that in a simple document, the number of chapter items equals the number of top-level nav items'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        document.save()

        toc = TOC(document.toc)
        self.failUnless(toc)

        chapters = HTMLFile.objects.filter(archive=document)
        self.assertEquals(len(chapters), len(toc.find_points(1)))

    def testCountDeepTOC(self):
        '''Check a complex document with multiple nesting levels'''
        toc = TOC(_get_file('complex-ncx.ncx'))
        self.failUnless(toc)
        self.assert_(len(toc.find_points(3)) > len(toc.find_points(2)) > len(toc.find_points(1)))

    def testOrderedTOC(self):
        '''TOC should preserve the playorder of the NCX'''
        toc = TOC(_get_file('complex-ncx.ncx'))
        self.failUnless(toc)
        # First item is the Copyright statement, which has no children
        copyright_statement = toc.tree[0]
        self.assertEquals(copyright_statement.title(), 'Copyright')

        # Second item should be the preface 
        preface = toc.tree[1]
        self.assertEquals(preface.title(), 'Preface')        

        # Last item is the Colophon
        colophon = toc.tree[-1:][0]
        self.assertEquals(colophon.title(), 'Colophon')

    def testGetChildren(self):
        '''Get the children of a particular nested TOC node, by node'''
        toc = TOC(_get_file('complex-ncx.ncx'))
        self.failUnless(toc)

        # First item is the Copyright statement, which has no children
        copyright_section = toc.tree[0]
        children = toc.find_children(copyright_section)
        self.failIf(children)

        # Second item is the Preface, which has 8 children
        preface = toc.tree[1]
        children = toc.find_children(preface)
        self.assertEquals(8, len(children))

    def testTOCHref(self):
        '''Ensure that we are returning the correct href for an item'''
        toc = TOC(_get_file('complex-ncx.ncx'))
        preface = toc.tree[1]
        self.assertEquals("pr02.html", preface.href())

    def testMetadata(self):
        '''All metadata should be returned using the public methods'''
        opf_file = 'all-metadata.opf'
        document = MockEpubArchive(name=opf_file)
        opf = _get_file(opf_file)

        self.assertEquals('en-US', document.get_metadata(DC_LANGUAGE_TAG, opf))
        self.assertEquals('Public Domain', document.get_metadata(DC_RIGHTS_TAG, opf))
        self.assertEquals('threepress.org', document.get_metadata(DC_PUBLISHER_TAG, opf))
        self.assertEquals(3, len(document.get_metadata(DC_SUBJECT_TAG, opf)))
        self.assertEquals('Subject 1', document.get_metadata(DC_SUBJECT_TAG, opf)[0])
        self.assertEquals('Subject 2', document.get_metadata(DC_SUBJECT_TAG, opf)[1])
        self.assertEquals('Subject 3', document.get_metadata(DC_SUBJECT_TAG, opf)[2])


    def testInvalidXHTML(self):
        '''Documents with non-XML content should be renderable'''
        document = self.create_document('invalid-xhtml.epub')
        document.explode()
        document.save()
        chapters = HTMLFile.objects.filter(archive=document)
        for c in chapters:
            c.render()

    def testHTMLEntities(self):
        '''Documents which are valid XML except for HTML entities should convert'''
        document = self.create_document('html-entities.epub')
        document.explode()
        document.save()
        chapters = HTMLFile.objects.filter(archive=document)
        for c in chapters:
            c.render()        

    def testRemoveBodyTag(self):
        '''We should not be printing the original document's <body> tag'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        document.save()
        chapters = HTMLFile.objects.filter(archive=document)
        for c in chapters:
            self.assert_('<body' not in c.render())
            self.assert_('<div id="bw-book-content"' in c.render())


    def testBinaryImage(self):
        '''Test the ImageBlob class directly'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        document.save()
        imagename = 'alice01a.gif'
        image = _get_file(imagename)
        image_obj = ImageFile(idref=imagename,
                              archive=document)
        image_obj.save()

        i = ImageBlob(archive=document,
                      idref=imagename,
                      image=image_obj,
                      data=image,
                      filename=imagename)
        i.save()
        i2 = ImageBlob.objects.filter(idref=imagename)[0]
        self.assertEquals(image, i2.get_data())
        i2.delete()

    def testBinaryImageAutosave(self):
        '''Test that an ImageFile creates a blob and can retrieve it'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        document.save()
        imagename = 'alice01a.gif'
        image = _get_file(imagename)
        image_obj = ImageFile(idref=imagename,
                              archive=document,
                              data=image)
        image_obj.save()
        i2 = ImageFile.objects.filter(idref=imagename)[0]
        self.assertEquals(image, i2.get_data())
        i2.delete()
        
    def testBinaryImageAutodelete(self):
        '''Test that an ImageFile can delete its associated blob'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        document.save()
        imagename = 'alice2.gif'
        image = _get_file(imagename)
        image_obj = ImageFile(idref=imagename,
                              archive=document,
                              data=image)
        image_obj.save()
        i2 = ImageFile.objects.filter(idref=imagename)[0]
        storage = i2._blob()._get_file()
        assert storage
        i2.delete()
        self.assert_(not os.path.exists(storage))

    def testImageWithPathInfo(self):
        filename = 'alice-fromAdobe.epub'
        document = self.create_document(filename)
        document.explode()
        document.save()

    def testBinaryEpub(self):
        '''Test the storage of an epub binary'''
        filename = 'Pride-and-Prejudice_Jane-Austen.epub'
        document = self.create_document(filename)
        document.explode()
        document.save()
        epub = _get_file(filename)
        bin = EpubBlob(idref=filename,
                       archive=document,
                       filename=filename,
                       data=epub)
        bin.save()
        b2 = EpubBlob.objects.filter(idref=filename)[0]

        # Assert that we can read the file, and it's the same
        self.assertEquals(epub, b2.get_data())

        # Assert that it's physically in the storage directory
        storage = b2._get_file()
        self.assert_(os.path.exists(storage))        

        # Assert that once we've deleted it, it's gone
        b2.delete()
        self.assert_(not os.path.exists(storage))        



    def create_document(self, document):
        epub = MockEpubArchive(name=document)
        epub.owner = self.user
        epub.save()
        epub.set_content(_get_file(document))

        return epub


class TestViews(DjangoTestCase):
    def setUp(self):
        logging.info('Calling setup')
        self.user = User.objects.create_user(username="testuser",email="test@example.com",password="testuser")
        self.user.save()        

    def tearDown(self):
        self.user.delete()

    def test_is_index_protected(self):
        response = self.client.get('/')
        self.assertRedirects(response, '/account/signin/?next=/', 
                             status_code=302, 
                             target_status_code=200)

    def test_login(self):
        self._login()
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'index.html')

    def _login(self):
        self.assertTrue(self.client.login(username='testuser', password='testuser'))

    def test_upload(self):
        response = self._upload('Pride-and-Prejudice_Jane-Austen.epub')
        self.assertRedirects(response, '/', 
                             status_code=302, 
                             target_status_code=200)

    def test_upload_with_images(self):
        response = self._upload('alice-fromAdobe.epub')
        self.assertRedirects(response, '/', 
                             status_code=302, 
                             target_status_code=200)        

    def test_upload_with_utf8(self):
        response = self._upload('The-Adventures-of-Sherlock-Holmes_Arthur-Conan-Doyle.epub')
        self.assertRedirects(response, '/', 
                             status_code=302, 
                             target_status_code=200)        

        # Make sure it's in the list
        response = self.client.get('/')
        self.assertContains(response, 'Sherlock')

    def test_delete_with_utf8(self):
        response = self._upload('The-Adventures-of-Sherlock-Holmes_Arthur-Conan-Doyle.epub')
        # Make sure it's in the list
        response = self.client.get('/')
        self.assertContains(response, 'Sherlock')

        response = self.client.post('/delete/', { 'title':'The+Adventures+of+Sherlock+Holmes',
                                       'key':'1'})
        self.assertRedirects(response, '/', 
                             status_code=302, 
                             target_status_code=200)   
        response = self.client.get('/')
        self.assertNotContains(response, 'Sherlock')


    def test_upload_with_entities(self):
        response = self._upload('html-entities.epub')
        self.assertRedirects(response, '/', 
                             status_code=302, 
                             target_status_code=200)   

    def test_view_document(self):
        self._upload('Pride-and-Prejudice_Jane-Austen.epub')
        response = self.client.get('/view/Pride-and-Prejudice/1/')
        self.assertTemplateUsed(response, 'view.html')
        self.assertContains(response, 'Pride and Prejudice', status_code=200)

    def test_view_chapter(self):
        self._upload('Pride-and-Prejudice_Jane-Austen.epub')
        response = self.client.get('/view/Pride-and-Prejudice/1/chapter-1.html')
        self.assertTemplateUsed(response, 'view.html')
        self.assertContains(response, 'It is a truth universally acknowledged', status_code=200)

    def test_delete_book(self):
        self._upload('Pride-and-Prejudice_Jane-Austen.epub')        
        response = self.client.post('/delete/', { 'title':'Pride+and+Prejudice',
                                       'key':'1'})
        self.assertRedirects(response, '/', 
                             status_code=302, 
                             target_status_code=200)   
        
    def test_view_profile(self):
        self._login()
        response = self.client.get('/account/profile/')
        self.assertTemplateUsed(response, 'auth/profile.html')
        self.assertContains(response, 'testuser', status_code=200)        

    def test_view_about_not_logged_in(self):
        '''This throws an exception if the user profile isn't properly handled for anonymous requests'''
        response = self.client.get('/about/')
        self.assertContains(response, 'About', status_code=200)                
        self.assertTemplateUsed(response, 'about.html')

    def test_register_standard(self):
        '''Register a new account using a standard Django account'''
        logging.info("This test may fail if the local client does not have a running stmp server. Try running library/smtp.py as root before calling this test.")
        response = self.client.post('/account/signup/', { 'username':'registertest',
                                                          'email':'registertest@example.com',
                                                          'password1':'registertest',
                                                          'password2':'registertest'})
        self.assertRedirects(response, '/', 
                             status_code=302, 
                             target_status_code=200)   
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'index.html')
        self.assertContains(response, 'registertest', status_code=200)

    def test_change_email(self):
        '''Change the email address in a standard Django account'''
        self.test_register_standard()
        response = self.client.post('/account/email/', { 'password':'registertest',
                                                         'email':'registertest2@example.com'})
        self.assertRedirects(response, '/account/profile/?msg=Email+changed.', 
                             status_code=302, 
                             target_status_code=200)           
        
        response = self.client.get('/account/profile/')
        self.assertContains(response, 'registertest2@example.com', status_code=200)
        self.assertNotContains(response, 'registertest@example.com', status_code=200)

    def test_change_password(self):
        '''Change a standard Django account password'''
        self.test_register_standard()
        response = self.client.post('/account/password/', { 'oldpw':'registertest',
                                                            'password1':'registertest2',
                                                            'password2':'registertest2'})
        
        self.assertRedirects(response, '/account/profile/?msg=Password+changed.', 
                             status_code=302, 
                             target_status_code=200)   
        response = self.client.get('/')
        self.assertContains(response, 'registertest', status_code=200)
        self.client.logout()
        self.assertTrue(self.client.login(username='registertest', password='registertest2'))        
        self.client.logout()
        self.assertFalse(self.client.login(username='registertest', password='registertest'))        

    def test_delete_account(self):
        self.test_register_standard()
        response = self.client.post('/account/delete/', { 'password':'registertest',
                                                          'confirm':'checked'})
        
        self.assertRedirects(response, '/account/signin/?msg=Your+account+has+been+deleted.',
                             status_code=302, 
                             target_status_code=200)   
        response = self.client.get('/')
        self.assertRedirects(response, '/account/signin/?next=/', 
                             status_code=302, 
                             target_status_code=200)   
        self.assertFalse(self.client.login(username='registertest', password='registertest'))                

        
    def _upload(self, f):
        self._login()
        fh = _get_filehandle(f)
        response = self.client.post('/upload/', {'epub':fh})
        return response

def _get_document(title, id):
    '''@todo Mock this out better instead of overwriting the real view'''
    return MockEpubArchive(id=id)

def _get_file(f):
    '''Get a file from either the public or private data directories'''
    return _get_filehandle(f).read()

def _get_filehandle(f):
    '''Get a file from either the public or private data directories'''
    try:
        return open('%s/%s' % (DATA_DIR, f))
    except IOError:
        return open('%s/%s' % (PRIVATE_DATA_DIR, f))
    
if __name__ == '__main__':
    logging.error('Invoke this using "manage.py test"')