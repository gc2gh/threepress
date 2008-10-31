import logging

logging.basicConfig(level=logging.DEBUG)

# Local settings; should be overridden for each checkout
DEBUG = True
TEMPLATE_DEBUG = DEBUG
   
DATABASE_ENGINE = 'mysql' 
DATABASE_NAME = 'bookworm'
DATABASE_USER = 'threepress'   
DATABASE_PASSWORD = '3press'   
DATABASE_HOST = ''             
DATABASE_PORT = ''             

SITE_ID = 2
