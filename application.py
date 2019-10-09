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
import random
import math
import string
import logging
import json

#flask
import flask
from flask import Flask, request, Response, Markup, render_template, session, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask.ext.session import Session
from flask_bootstrap import Bootstrap
from config import Config

#S3
import boto3
from botocore.exceptions import ClientError

#create PDF
import tempfile
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import base64
from PIL import Image
import pdfkit

#email
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart


db = SQLAlchemy()


# Create and configure the Flask app
application = flask.Flask(__name__)
application.config.from_object(Config)
db.init_app(application)
bootstrap = Bootstrap(application)

application.debug = application.config['FLASK_DEBUG'] in ['true', 'True']

application.config['ACCESS_SQS_KEY'] =  os.environ.get('ACCESS_SQS_KEY')  
application.config['SECRET_SQS_KEY'] =  os.environ.get('SECRET_SQS_KEY')  



# Create a new SES resource and specify a region.
ses = boto3.client('ses',region_name=application.config['AWS_REGION'])


SUBJECT = "IWATalentRelease PDF"


# The email body for recipients with non-HTML email clients.
BODY_TEXT = ("We have your IWAtalentrelease PDF attached. Thank you")

            
# The HTML body of the email.
BODY_HTML = """<html>
<head></head>
<body>
  <h1>Thank You!</h1>
  <p>%s, your IWATalentRelease is attached. %s!\n\n</p>
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



#BOTO3
s3R = boto3.resource(
    's3',
    aws_access_key_id = application.config['S3_KEY'],
    aws_secret_access_key = application.config['S3_SECRET']

)


def get_image_from_obj(bucket_name, filepath):

    #a few steps to take so we can use 'download_fileobj' to decrypt the 'aws:kms'

    tObj = s3R.Object(bucket_name, filepath)
    tmp = tempfile.NamedTemporaryFile()

    with open(tmp.name, 'wb') as f:

        tObj.download_fileobj(f)
        imTmp = mpimg.imread(tmp.name)

        im = Image.fromarray(imTmp)
        rawBytes = io.BytesIO()

        im.save(rawBytes, "PNG")
        rawBytes.seek(0)  # return to the start of the file
        base64Img = base64.b64encode(rawBytes.read()).decode('utf-8')

        #return a 'base64' encoded image to insert in the HTML 'IMG' src like:
        # <img src="data:image/png;base64,{{base64Img}}" 

        return base64Img



def put_file_to_s3(output, bucket_name, filename):

    s3R.Object(bucket_name, filename).put(Body=output)



# C R E A T E   A N D   E M A I L   P D F

@application.route('/pdfWorker', methods=['POST'])
def customer_registered():

    response = None
    if request.json is None:
        # Expect application/json request
        response = Response("", status=415)
    else:
        message = dict()
        try:
            # If the message has an SNS envelope, extract the inner message
            if 'TopicArn' in request.json and 'Message' in request.json:
                message = json.loads(request.json['Message'])
            else:
                message = request.json

            # structure
            # {'talentreleasecode': val}
            talentreleaseQuery = TalentReleasesDB.query.filter_by(talentreleasecode=message['talentreleasecode']).first_or_404()

            release = {}
            release["talentreleasecode"] = talentreleaseQuery.talentreleasecode

            #parse our the talent release
            release["userdetails"] = json.loads(talentreleaseQuery.userdetails)
            release["images"] = talentreleaseQuery.images
            release["projectID"] = talentreleaseQuery.projectID
            release["releasetemplate"] = talentreleaseQuery.releasetemplate
            release["verified"] = talentreleaseQuery.verified
            release["createdby"] = talentreleaseQuery.createdby
            release["createddate"] = talentreleaseQuery.createddate
            release["uploadeddate"] = talentreleaseQuery.uploadeddate
            release["images"] = talentreleaseQuery.images
            release["notes"] = talentreleaseQuery.notes



            def sendEmail(fileName, release, emailTo, releaseCreated):

              #https://docs.aws.amazon.com/ses/latest/DeveloperGuide/send-email-raw.html

              # Build an email
              msg = MIMEMultipart()
              msg['Subject'] = "IWATalentRelease PDF"
              msg['From'] = application.config['SOURCE_EMAIL_ADDRESS']
              msg['To'] = emailTo

              # Create a multipart/alternative child container.
              msg_body = MIMEMultipart('alternative')

              # Encode the text and HTML content and set the character encoding. This step is
              # necessary if you're sending a message with characters outside the ASCII range.
              textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
              htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)

              # Add the text and HTML parts to the child container.
              msg_body.attach(textpart)
              msg_body.attach(htmlpart)

              msg.attach(msg_body)

              # The attachment
              part = MIMEApplication(release.getvalue())
              part.add_header('Content-Disposition', 'attachment', filename=fileName)

              msg.attach(part)

              try:
                # And finally, send the email
                ses.send_raw_email(
                    
                    Source=application.config['SOURCE_EMAIL_ADDRESS'],
                    Destinations=[emailTo, releaseCreated],
                    RawMessage={
                        'Data': msg.as_string(),
                    }
                )

              # Display an error if something goes wrong. 
              except ClientError as e:
                  print(e.response['Error']['Message'])

              else:
                  print("Email sent! Message ID:"),
                  print(response['MessageId'])



            #talent release rendered

            talentRelease = {}
            talentRelease['date'] = release['userdetails']['date']
            talentRelease['firstname'] = release['userdetails']['firstname']
            talentRelease['lastname'] = release['userdetails']['lastname']
            talentRelease['street'] = release['userdetails']['street']
            talentRelease['phone'] = release['userdetails']['phone']
            talentRelease['state'] = release['userdetails']['state']
            talentRelease['city'] = release['userdetails']['city']
            talentRelease['email'] = release['userdetails']['email']


            #TODO: ADD LEGAL TITLE AND LEGAL VARS TO TALENTDB
            talentRelease['releaseLegalCopy'] = release['releasetemplate']['copy']  
            talentRelease['releaseLegalTitle'] = release['releasetemplate']['name'] 

            #images details
            images = {}
            uploaded_files = []
            uploadedimages = []
 

            imagePhoto  = get_image_from_obj(application.config["S3_BUCKET"], release['images']['imagePortrait'] )
            uploadedimages.append(imagePhoto)


            imageSignature = get_image_from_obj(application.config["S3_BUCKET"], release['images']['imageSignature'] )
            uploadedimages.append(imageSignature)


            #if template is for minor, capture the name
            if release['releasetemplate']['type'] == 'Minor':
                talentRelease['minor_firstname'] = release['userdetails']['minor_firstname']
                talentRelease['minor_lastname'] = release['userdetails']['minor_lastname']

            copy = talentRelease['releaseLegalCopy'].replace("\r\n", "<br />")
            copy = Markup(copy)

            typeSuffix = 'minor' if release['releasetemplate']['type'] == 'Minor' else 'standard'

            #create pdf template
            rendered = render_template('renderrelease_' + typeSuffix + '.html',  talentRelease=release['releasetemplate']['copy'], uploadedimages=uploadedimages, legalCopy=copy)

            # pdf path
            filename =  "{0}-{1}{2}.pdf".format(release["talentreleasecode"] , talentRelease['firstname'], talentRelease['lastname'])
            pdfpath = "{0}/{1}".format(release["projectID"], filename)  

            #render pdf
            pdf = pdfkit.from_string(rendered, False)
            put_file_to_s3(pdf, application.config["S3_BUCKET"], pdfpath)

            #update talentrelease db with new settings
            talentreleaseQuery.pdflocation = pdfpath
            db.session.commit()



            sendEmail(filename, pdf, talentRelease['email'], release["createdby"])
            response = Response("", status=200)


        except Exception as ex:
            logging.exception('Error processing message: %s' % request.json)
            response = Response(ex.message, status=500)

    return response

if __name__ == '__main__':
    application.run(host='0.0.0.0')


