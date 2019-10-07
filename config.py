import os

class Config(object):
	
	AWS_REGION = 'us-west-2'
	FLASK_DEBUG = 'false'
	SOURCE_EMAIL_ADDRESS = 'ddintzner@innoceanusa.com'

	SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')  
	SQLALCHEMY_TRACK_MODIFICATIONS= False

	S3_BUCKET =   os.environ.get('S3_BUCKET')  
	S3_PUBLIC_BUCKET = os.environ.get('S3_PUBLIC_BUCKET')  
	S3_SECRET = os.environ.get('S3_SECRET')  
	S3_KEY = os.environ.get('S3_KEY') 
	S3_LOCATION =  os.environ.get('S3_LOCATION')  
	S3_FILELOCATION = os.environ.get('S3_FILELOCATION')  
	ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'tif', 'tiff'])
	SECRET_KEY =  os.environ.get('SECRET_KEY')  
