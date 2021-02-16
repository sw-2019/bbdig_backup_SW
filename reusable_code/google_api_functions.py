from google_auth_oauthlib import flow # To authorise as user
from googleapiclient.discovery import build # To pull in from sheets, slides etc. API
from google.auth.transport.requests import Request
from google.cloud.bigquery import magics
import os
import pickle

from xlsxwriter.utility import xl_rowcol_to_cell
import json
import pandas as pd

def Authenticate_Google(credentials_json_path=None, scopelist=['https://www.googleapis.com/auth/bigquery',\
                    'https://www.googleapis.com/auth/spreadsheets',\
                    'https://www.googleapis.com/auth/documents',\
                   'https://www.googleapis.com/auth/presentations',\
'https://www.googleapis.com/auth/drive'\
],launch_browser = False):

    # This function runs the google authorisation flow. It also stores the returned credentials into a "pickle" file. This shows that the authorisation has been run before.
    # The code first looks for a pickle in the specified path (or the home/ root directory if no path specified)
    # If a pickle file is found, it loads those credentials.
    # If the pickle file is not found, then it runs the manual login flow and saves the results for re-use later.
    
     
    # If a path is specified within the pass through then grab the Client Secret from there, and put the pickle there
    if credentials_json_path:
        full_creds_path=credentials_json_path+'client_secrets.json'
        full_pickle_path=credentials_json_path+'token.pickle'
    else:
        full_creds_path='client_secrets.json'
        full_pickle_path='token.pickle'
    
    
    credentials = None
    
    # The file token.pickle stores the user's access and refresh tokens, and is created automatically when the authorization flow completes for the first time.
    
    # Load "pickle" if it exists
    if os.path.exists(full_pickle_path):
        with open(full_pickle_path, 'rb') as token:
            credentials = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
    
    # If above step did not work, run authorisation flow
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            appflow = flow.InstalledAppFlow.from_client_secrets_file(full_creds_path,\
            scopes=scopelist)
            
            if launch_browser:
                appflow.run_local_server()
            else:
                appflow.run_console()

            credentials = appflow.credentials
            
            # Save the credentials for the next run
            with open(full_pickle_path, 'wb') as token:
                pickle.dump(credentials, token)

    return credentials


def read_google_sheets_as_rows(Sheet_ID,Range_spec,creds,header_row=0):

    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=Sheet_ID,
                                    range=Range_spec).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
    else:
        print('Sheet returned successfully!')
    
    
    sheet_df = pd.DataFrame.from_records(values, columns=values[header_row])
    # It'll re-read the first row with headers as actual data.  We want this so it gets the width right but want to now drop it.
    sheet_df=sheet_df[header_row+1:]
    
    # Convert imported sheet into a dictionary
    sheet_dict=sheet_df.to_dict(orient='records')
    
    return values,sheet_df

def read_google_docs(DOCUMENT_ID,creds):
    
    service = build('docs', 'v1', credentials=creds)

    # Retrieve the documents contents from the Docs service.
    document = service.documents().get(documentId=DOCUMENT_ID).execute()

    print('The title of the document is: {}'.format(document.get('title')))

    return document


    
def Get_cell_ref(rownum,column_name,gsheet_list):
    #### For this project, the sheet being searched is hard coded (always "google_sheet_rows")
    #### The row to search for headers is also hard coded(always first row, 0)
    col_num=[n for n,x in enumerate(gsheet_list[0]) if x==column_name][0]
    cell = xl_rowcol_to_cell(rownum, col_num)  # C2
    return cell

def Update_cell(creds,spreadsheet_id,sheetname,cellref,value_to_update,value_input_option = 'RAW'):

    service = build('sheets', 'v4', credentials=creds)
    
    # The A1 notation of the values to update.
    range_ = '{}!{}'.format(sheetname,cellref)  # The specific sheet and cell(s) to update 
    
    # How the input data should be interpreted.
      # Can also be set to a user_inputted value which would e.g. resolve formulae

    value_range_body = {
      "values": [
        [
          value_to_update
        ]
      ]
    }

    request = service.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=range_, valueInputOption=value_input_option, body=value_range_body)
    response = request.execute()
    
    
def Write_whole_df_to_gsheet(creds,df,spreadsheetId,Sheetname,valueInputOption='RAW',append_overwrite='overwrite',headers='Y',topleftcell='A1'):
    
    # Establish Google sheets service
    service = build('sheets', 'v4', credentials=creds)
    
    # Set up the range parameter
    range_ = '{}!{}'.format(Sheetname,topleftcell)

    # Turn Dataframe into a list of lists, this is how the Google Sheets API likes the information in the request
    df_json=df.to_json(orient='split') # Convert the dataframe to a JSON
    df_dict=json.loads(df_json)  # Then convert the JSON to a dictionary containing lists
    data=df_dict['data'] # Pull out the data list  
    if headers=='Y':
        data.insert(0,df_dict['columns']) # Add column headers if they are requested

    # Store as a parameter to pass in API request
    value_range_body = {
      "values": data
    }
        
        
    if append_overwrite=='overwrite':
        # Clear all values from sheet
        request = service.spreadsheets().values().clear(spreadsheetId=spreadsheetId,range=Sheetname)
        response = request.execute()
        
        request = service.spreadsheets().values().update(spreadsheetId=spreadsheetId,\
                                                         range=range_, valueInputOption=valueInputOption,\
                                                         body=value_range_body)
        
    elif append_overwrite=='append':
        request = service.spreadsheets().values().append(spreadsheetId=spreadsheetId,\
                                                 range=range_, valueInputOption=valueInputOption,\
                                                 body=value_range_body)

    else:
        print('Please set parameter "append_overwrite" to either "append" or "overwrite" ')
        return
    
    response = request.execute()