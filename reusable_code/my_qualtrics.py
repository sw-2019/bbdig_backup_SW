import requests
import time
import zipfile
import io
from pprint import pprint
import json
import pandas as pd

# Get organisation info
class session:

    def __init__(self,mytoken):
        self.mytoken = mytoken
    
    def Get_Account_Info(self,org_id):
        url = "https://eu.qualtrics.com/API/v3/organizations/{}".format(org_id)
        headers={"X-API-TOKEN": self.mytoken}
        response = requests.request("GET", url, headers=headers)
        return json.loads(response.text)

    def Get_list_of_surveys(self):
        url = "https://eu.qualtrics.com/API/v3/surveys"
        headers = {
        "x-api-token": self.mytoken,
        }

        response = requests.get(url, headers=headers)
        return json.loads(response.text)['result']['elements']
    
    def Get_survey_id_from_name(self,survey_name):
        survey_id=[i['id'] for i in self.Get_list_of_surveys() if i['name']==survey_name][0]
        return survey_id
    
    def Get_survey_name_from_id(self,survey_id):
        survey_name=[i['name'] for i in self.Get_list_of_surveys() if i['id']==survey_id][0]
        return survey_name
    
    def Get_Survey_Info(self,surveyid):
    # Setting user Parameters
        url = "https://eu.qualtrics.com/API/v3/surveys/{}".format(surveyid)
        headers = {
            "x-api-token": self.mytoken,
            }

        response = requests.get(url, headers=headers)
        return json.loads(response.text)['result']

    def Download_survey_responses(self,surveyid,from_time=None,to_time=None,seenUnansweredRecode=-999,multiselectSeenUnansweredRecode=-999):
        
        survey_name=self.Get_survey_name_from_id(surveyid)
        print("Downloading {}".format(survey_name))
        
        if from_time and to_time:
            data_string='''{{"format":"csv","startDate":"{}","endDate":"{}","seenUnansweredRecode":{},"multiselectSeenUnansweredRecode":{}}}'''.format(from_time,to_time,seenUnansweredRecode,multiselectSeenUnansweredRecode)
            #print(data_string)
        else:
            data_string='''{{"format":"csv","seenUnansweredRecode":{},"multiselectSeenUnansweredRecode":{}}}'''.format(seenUnansweredRecode,multiselectSeenUnansweredRecode)
                        
        ####### Start the survey download
        url = "https://eu.qualtrics.com/API/v3/surveys/{}/export-responses".format(surveyid)
        headers = {"content-type": "application/json",
            "X-API-TOKEN": self.mytoken,
            'Accept-Charset': 'UTF-8',
            'compress':'true'
            }
        response = requests.request("POST", url, headers=headers, data=data_string)
        progressID=json.loads(response.text)['result']['progressId'] # Get the ID for the download

        ####### Check if export complete
        url = "https://eu.qualtrics.com/API/v3/surveys/{}/export-responses/{}".format(surveyid,progressID)
        headers = {"content-type": "application/json",
                "X-API-TOKEN": self.mytoken
                }

        export_complete=False  #Assume not complete
        while export_complete==False:
            response = requests.request("GET", url, headers=headers, data='{"format":"csv"}')
            response_dict=json.loads(response.text)['result']

            if float(response_dict['percentComplete'])>=100: #If complete, update value to break loop
                export_complete=True
                break
            time.sleep(2) #Wait 1 second before restarting loop if not


        fileId=response_dict['fileId'] #Retrieve the file ID of the download    

        ####### Check if export complete

        url = "https://eu.qualtrics.com/API/v3/surveys/{}/export-responses/{}/file".format(surveyid,fileId)
        headers = {"content-type": "application/json",
                "X-API-TOKEN": self.mytoken
                }
        response = requests.request("GET", url, headers=headers, stream=True)
        # Step 4: Unzipping the file and storing it locally
#       return response.content
        survey_results=pd.read_csv(zipfile.ZipFile(io.BytesIO(response.content)).open('{}.csv'.format(survey_name)))[2:].set_index('ResponseId')
        print("Collected {}".format(survey_name))
        
        
        dropkeys=['RecipientLastName','RecipientFirstName','IPAddress','LocationLatitude','LocationLongitude','RecipientEmail',\
         'Finished','Progress','DistributionChannel','ExternalReference','UserLanguage'] # Remove any potential PII
        keep_keys=[i for i in survey_results.keys() if i not in dropkeys]

        to_return=survey_results[survey_results['Finished']=='1'][keep_keys] #Keep only permitted fields and completed responses
        return to_return
