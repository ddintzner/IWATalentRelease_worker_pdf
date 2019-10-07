# Copyright 2013. Amazon Web Services, Inc. All Rights Reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os
from datetime import datetime, timedelta, timezone
import io
from config import Config

import logging
import json

import flask
from flask import request, Response
from flask_sqlalchemy import SQLAlchemy

import pdfkit

import boto3

from botocore.exceptions import ClientError

db = SQLAlchemy()

# Create and configure the Flask app
application = flask.Flask(__name__)
application.config.from_object(Config)
db.init_app(application)
application.debug = application.config['FLASK_DEBUG'] in ['true', 'True']

application.config['ACCESS_SQS_KEY'] =  os.environ.get('ACCESS_SQS_KEY')  
application.config['SECRET_SQS_KEY'] =  os.environ.get('SECRET_SQS_KEY')  

# Create a new SES resource and specify a region.
client = boto3.client('ses',region_name=application.config['AWS_REGION'])





SUBJECT = "IWATalentRelease "

# The email body for recipients with non-HTML email clients.
BODY_TEXT = ("Lost password for IWATalent Release\r\n"
             "Follow the link below to reset "
             "AWS SDK for Python (Boto)."
            )
            
# The HTML body of the email.
BODY_HTML = """<html>
<head></head>
<body>
  <h1>Lost Password recovery</h1>
  <p>Click link to reset password: %s!\n\n</p>
</body>
</html>
            """     

# The character encoding for the email.
CHARSET = "UTF-8"


class TalentReleasesDB(db.Model):
       __tablename__ = 'releases'
       
       talentreleasecode = db.Column(db.String, primary_key=True)
       userdetails = db.Column(db.JSON)
       images = db.Column(db.JSON)
       pdflocation = db.Column(db.String)
       projectID = db.Column(db.String)
       releasetemplate = db.Column(db.String)
       createdby = db.Column(db.String)
       createddate = db.Column(db.Date)
       uploadeddate = db.Column(db.Date)
       emailedtalent = db.Column(db.Boolean)
       emailtalentdate = db.Column(db.Date)
       verified = db.Column(db.Boolean)
       verifieddate = db.Column(db.Date)
       notes = db.Column(db.Date)


@application.route('/pdfWorker', methods=['POST'])
def customer_registered():
    """Send an e-mail using SES"""

    response = None
    if request.json is None:
        # Expect application/json request
        response = Response("", status=415)
    else:
        message = dict()
        try:
            # If the message has an SNS envelope, extract the inner message
            message = request.json

            # structure
            # {'talentreleasecode': val}

            talentrelease = TalentReleasesDB.query.filter_by(email=message['talentreleasecode']).first()

            legalCopy = talentrelease['releasetemplate']['copy']

            client.send_email(
                Destination={
                    'ToAddresses': [
                        'dkdin@hotmail.com',
                    ],
                },
                Message={
                    'Body': {
                        'Html': {
                            'Charset': CHARSET,
                            'Data': BODY_HTML  % legalCopy,
                        },
                        'Text': {
                            'Charset': CHARSET,
                            'Data': BODY_TEXT,
                        },
                    },
                    'Subject': {
                        'Charset': CHARSET,
                        'Data': SUBJECT,
                    },
                },

            Source=application.config['SOURCE_EMAIL_ADDRESS'])

            


            '''
            copy = legalCopy.replace("\r\n", "<br />")
            copy = Markup(copy)


            typeSuffix = 'minor' if releases.type == 'Minor' else 'standard'


            uploadedimages = []

            imagePhoto  = get_image_from_obj(file, app.config["S3_BUCKET"], message['photo'])
            imageSignature = get_image_from_obj(file, app.config["S3_BUCKET"], message['signature'])

            uploadedimages.append(imagePhoto)
            uploadedimages.append(imageSignature)


            rendered = render_template('renderrelease_' + typeSuffix + '.html',  talentRelease=talentRelease, uploadedimages=uploadedimages, legalCopy=message['copy'])

            filename =  "{0}-{1}{2}.pdf".format(talentReleaseID , talentRelease['firstname'], talentRelease['lastname'])


            pdf = pdfkit.from_string(rendered, False)
            pdfpath = "{0}/{1}".format(form.projectID.data, filename)  


            put_file_to_s3(pdf, app.config["S3_BUCKET"], pdfpath)

            newTalentRelease.pdflocation = pdfpath

            '''


            response = Response("", status=200)

        except Exception as ex:
            logging.exception('Error processing message: %s' % request.json)
            response = Response(ex.message, status=500)

    return response

if __name__ == '__main__':
    application.run(host='0.0.0.0')


