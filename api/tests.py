import os
from lxml import etree

from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.sites.models import Site

from bookworm.api import models
from bookworm.library import models as library_models

class Tests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(username="testapi",email="testapi@example.com",password="testapi")
        self.user2 = User.objects.create_user(username="testapi2",email="testapi2@example.com",password="testapi2")
        self.userpref = library_models.UserPref.objects.create(user=self.user)
        self.userpref2 = library_models.UserPref.objects.create(user=self.user2)
        Site.objects.get_or_create(id=1)

    def _login(self):
        self.assertTrue(self.client.login(username='testapi', password='testapi'))

    def test_generate_key(self):
        '''The system should be able to generate a random key'''
        self._reset()
        k = models.APIKey.objects.create(user=self.user)
        assert k.key is not None
        # Does it seem vaguely uuid4-ish?
        assert len(k.key) == 32
    
    def test_generate_key_unique(self):
        '''Keys should be unique UUIDs'''
        self._reset()
        k = models.APIKey.objects.create(user=self.user)
        k2 = models.APIKey.objects.create(user=self.user2)
        assert k.key != k2.key

    def test_generate_key_once(self):
        '''Keys should persist once created'''
        self._reset()
        (k, created1) = models.APIKey.objects.get_or_create(user=self.user)
        assert created1
        (k2, created2) = models.APIKey.objects.get_or_create(user=self.user)
        assert not created2
        assert k.key == k2.key
        
    def test_authenticate_key(self):
        '''It should be possible to test whether an API key is correct'''
        self._reset()
        k = models.APIKey.objects.create(user=self.user)
        key = k.key
        assert k.is_valid(key)
        assert not k.is_valid('Not valid')

    def test_authenticate_key_by_user(self):
        '''It should be possible to test whether an API key is correct for any named user'''
        self._reset()
        k = models.APIKey.objects.create(user=self.user)
        k2 = models.APIKey.objects.create(user=self.user2)
        key = k.key
        assert key is not None

        assert models.APIKey.objects.is_valid(key, self.user)

        # It shouldn't be valid for user2
        assert not models.APIKey.objects.is_valid(key, self.user2)


        # It should also work if k2 doesn't have any key at all, but raise an exception
        k2.delete()
        self.assertRaises(models.APIException, models.APIKey.objects.is_valid, key, self.user2)

        # Some random string should also not be valid
        assert not models.APIKey.objects.is_valid('not valid', self.user)

    def test_get_key_from_profile_no_key(self):
        '''There should be a method to create an API key by having the user's profile object, even if they have not already created one before.'''
        profile = self.user.get_profile()
        assert profile

        assert models.APIKey.objects.filter(user=self.user).count() == 0
        apikey = profile.get_api_key()
        assert apikey

    def test_get_key_from_profile_existing_key(self):
        '''There should be a method to retrieve an API key by having the user's profile object.'''
        profile = self.user.get_profile()
        assert profile

        # Manually create a key
        apikey1 = models.APIKey.objects.create(user=self.user)
        apikey2 = profile.get_api_key()
        assert apikey1 == apikey2

    def test_view_api_key_on_profile_page(self):
        '''The user's API key should appear on their profile page'''
        self._login()
        response = self.client.get('/account/profile/')
        self.assertTemplateUsed(response, 'auth/profile.html')
        self.assertContains(response, 'testapi', status_code=200)        

        # Get this API key
        key = self.user.get_profile().get_api_key().key
        assert key is not None
        assert len(key) == 32

        assert key in response.content
        
    def test_api_key_change_on_username_change(self):
        '''The user's API key should change when their username is updated'''
        user = User.objects.create_user(username="usernamechange",email="usernamechange@example.com",password="usernamechange")
        library_models.UserPref.objects.create(user=user)
        key1 = user.get_profile().get_api_key().key
        
        user.username = 'username2'
        user.save()

        assert key1 != user.get_profile().get_api_key().key

    def test_api_key_change_on_password_change(self):
        '''The user's API key should change when their password is updated'''
        user = User.objects.create_user(username="passwordchange",email="passwordchange@example.com",password="passwordchange")
        library_models.UserPref.objects.create(user=user)
        key1 = user.get_profile().get_api_key().key
        
        user.password = 'password2'
        user.save()

        assert key1 != user.get_profile().get_api_key().key


    def test_api_key_change_not_on_email_change(self):
        '''The user's API key should NOT change when their email is updated'''
        user = User.objects.create_user(username="emailchange",email="emailchange@example.com",password="emailchange")
        library_models.UserPref.objects.create(user=user)
        key1 = user.get_profile().get_api_key().key
        
        user.email = 'email2@example.com'
        user.save()

        assert key1 == user.get_profile().get_api_key().key

    def test_api_key_change_on_password_web(self):
        '''The user's API key should visibly change on the web site after updating their password from the web'''
        username = 'test_change_password'
        email = 'test_change_password@example.com'
        password = 'test_change_password'
        self._register_standard(username, email, password)
        user = User.objects.get(username=username)
        response = self.client.get('/account/profile/')
        self.assertTemplateUsed(response, 'auth/profile.html')
        self.assertContains(response, username, status_code=200)        

        # Get this API key
        key = user.get_profile().get_api_key().key
        assert key is not None
        assert len(key) == 32
        assert key in response.content

        response = self.client.post('/account/password/', { 'oldpw':password,
                                                            'password1':'registertest2',
                                                            'password2':'registertest2'})
        self.assertRedirects(response, '/account/profile/?msg=Password+changed.', 
                             status_code=302, 
                             target_status_code=200)           
        
        response = self.client.get('/account/profile/')

        key2 = user.get_profile().get_api_key().key
        assert len(key2) == 32
        assert key not in response.content
        assert key2 in response.content
        assert key2 != key

    def test_api_key_change_on_email_web(self):
        '''The user's API key should NOT visibly change on the web site after updating their email from the web'''
        username = 'test_change_email'
        email = 'test_change_email@example.com'
        password = 'test_change_email'
        self._register_standard(username, email, password)
        user = User.objects.get(username=username)
        response = self.client.get('/account/profile/')
        self.assertTemplateUsed(response, 'auth/profile.html')
        self.assertContains(response, username, status_code=200)        

        # Get this API key
        key = user.get_profile().get_api_key().key
        assert key is not None
        assert len(key) == 32
        assert key in response.content

        response = self.client.post('/account/email/', { 'password':password,
                                                         'email':'changedemail@example.com'})

        self.assertRedirects(response, '/account/profile/?msg=Email+changed.', 
                             status_code=302, 
                             target_status_code=200)           
        
        response = self.client.get('/account/profile/')
        assert 'changedemail@example.com' in response.content

        assert key in response.content


    def test_api_key_change_on_username_web(self):
        '''The user's API key should visibly change on the web site after updating their username from the web'''
        pass # There's no method to change a username on Bookworm via the web API

    def test_api_fail_anon(self):
        '''An anonymous user should not be able to log in to the API without an API key'''
        self.assertRaises(models.APIException, self.client.get, '/api/list/')

    def test_api_fail_logged_in(self):
        '''A logged-in user should not be able to log in to the API without an API key'''
        self._login()
        self.assertRaises(models.APIException, self.client.get, '/api/list/')

    def test_api_fail_bad_key(self):
        '''A logged-in user should not be able to log in to the API with the wrong API key'''
        self._login()
        self.assertRaises(models.APIException, self.client.get, '/api/list/', { 'api_key': 'None'})

    def test_api_list_no_results(self):
        '''A user should be able to log in to the API with the correct API key and get a valid page even with no books.'''
        self._login()
        key = self.userpref.get_api_key().key
        response = self.client.get('/api/list/', { 'api_key': key})
        assert '<html' in response.content
        self._validate_page(response)

    def _validate_page(self, response):
        '''Validate that this response contains a valid XHTML result'''
        page = etree.fromstring(response.content)
        assert page is not None

        schema_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'schema', 'xhtml', 'xhtml-strict.rng')
        schema = etree.parse(schema_file)
        relaxng = etree.RelaxNG(schema)
        relaxng.assertValid(page)

        
    def _register_standard(self, username, email, password):
        '''Register a new account using a standard Django account'''
        response = self.client.post('/account/signup/', { 'username':username,
                                                          'email':email,
                                                          'password1':password,
                                                          'password2':password})
        self.assertRedirects(response, '/library/', 
                             status_code=302, 
                             target_status_code=200)   
        response = self.client.get('/library/')
        self.assertTemplateUsed(response, 'index.html')
        self.assertContains(response, username, status_code=200)

        
    def _reset(self):
        '''Delete any apikey assignments between runs'''        
        [a.delete() for a in models.APIKey.objects.all() ]
