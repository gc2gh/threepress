from django.test import TestCase
from django.contrib.auth.models import User

from bookworm.api import models
from bookworm.library import models as library_models

class Tests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create(username='testapi')
        self.user2 = User.objects.create(username='testapi2')
        library_models.UserPref.objects.create(user=self.user)
        library_models.UserPref.objects.create(user=self.user2)

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


        
    def _reset(self):
        '''Delete any apikey assignments between runs'''        
        [a.delete() for a in models.APIKey.objects.all() ]
