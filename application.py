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

import logging
import json

import flask
from flask import request, Response

import sys
import os
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError

# Create and configure the Flask app
application = flask.Flask(__name__)
application.config.from_object('default_config')
application.debug = application.config['FLASK_DEBUG'] in ['true', 'True']

application.config['ACCESS_SQS_KEY'] =  os.environ.get('ACCESS_SQS_KEY')  
application.config['SECRET_SQS_KEY'] =  os.environ.get('SECRET_SQS_KEY')  

# Create a new SES resource and specify a region.
client = boto3.client('ses',region_name=application.config['AWS_REGION'])


# Email message vars
#SUBJECT = "Thanks for signing up!"
#BODY = "Hi %s!\n\nWe're excited that you're excited about our new product! We'll let you know as soon as it's available.\n\nThanks,\n\nA New Startup"



SUBJECT = "Lost Password Recovery"

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

@application.route('/lostpasswordWorker', methods=['POST'])
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
            if 'TopicArn' in request.json and 'Message' in request.json:
                message = json.loads(request.json['Message'])
            else:
                message = request.json
            

            client.send_email(
                Destination={
                    'ToAddresses': [
                        message['email'],
                    ],
                },
                Message={
                    'Body': {
                        'Html': {
                            'Charset': CHARSET,
                            'Data': BODY_HTML  % message['recover_url'],
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

            response = Response("", status=200)

        except Exception as ex:
            logging.exception('Error processing message: %s' % request.json)
            response = Response(ex.message, status=500)

    return response

if __name__ == '__main__':
    application.run(host='0.0.0.0')


