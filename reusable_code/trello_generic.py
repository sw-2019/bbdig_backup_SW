from trello import TrelloClient
import requests
from urllib import request, parse
import json
import sys
import pandas as pd
import json
import pytz
from datetime import datetime
from pprint import pprint
import pickle
import concurrent.futures
import threading
import time

import sys
import datetime as dt
import numpy as np

sys.path.append(r'/home/jupyter/reusable_code')
import google_api_functions as gaf
from xlsxwriter.utility import xl_rowcol_to_cell

# Used in the get_session function later
thread_local = threading.local()


def readTrelloCredsFromFile(path='trellocreds.pickle'):
    #Function assumes pickled dictionary with keys (key, secret, token)
    with open(path, 'rb') as handle:
        trellocreds = pickle.load(handle)
    
    if type(trellocreds)!=dict:
        print('ERROR: Pickle file does not contain a dictionary object. Expecting a dictionary with keys "key","secret",& "token"')
    elif 'key' not in list(trellocreds.keys()):
        print('ERROR: Pickled dictionary does not contain key with the name "key"')
    elif 'secret' not in list(trellocreds.keys()):
        print('ERROR: Pickled dictionary does not contain key with the name "secret"')    
    elif 'token' not in list(trellocreds.keys()):
        print('ERROR: Pickled dictionary does not contain key with the name "token"')
    else:
        return (trellocreds['key'],trellocreds['secret'],trellocreds['token'])

def writeTrelloCredsToFile(path,key,secret,token):
    trello_dict={'key':key,'secret':secret,'token':token}
    with open(path, "wb") as handle:
        pickle.dump(trello_dict, handle)
    print('Successfully written!')


def Generate_new_board(mykey,mysecret,mytoken,board_name, lists_to_create):
    
    #######################################################################################################################
    # Establish trello client
    #######################################################################################################################
    client = TrelloClient(api_key=mykey,api_secret=mysecret,token=mytoken)
    
    # List all the boards which are currently in existence
    all_boards = client.list_boards()

    #######################################################################################################################
    # Create the board as named
    #######################################################################################################################

    # Creates the board if it doesn't exist
    if board_name in [board.name for board in all_boards]:
        print("Board:'"+board_name+"' already exists")
        
    else:
        client.add_board(board_name,default_lists=False) 
    all_boards = client.list_boards()   
    
    # Create "this_board" object
    this_board=[board for board in all_boards if board.name==board_name][0]
    
    #######################################################################################################################
    # Add default & custom lists to the trello board
    #######################################################################################################################

    # Add each list if it doesn't already exist
    for i in reversed(lists_to_create):
        if i not in [x.name for x in this_board.list_lists()]:
            this_board.add_list(i)

    #######################################################################################################################
    #Enable custom fields on the board
    #######################################################################################################################

    url = "https://api.trello.com/1/boards/"+this_board.id+"/boardPlugins"
    querystring = {"idPlugin":"56d5e249a98895a9797bebb9","key":mykey,"token":mytoken}


    #Retrieve what plugins are already enabled
    myplugins=client.fetch_json("/boards/"+this_board.id+"/boardPlugins") #Pull a list, each item holding a dictionary for a field
    #If there are already plugins enabled and one of them is "custom fields" then skip, else enable
    if len(myplugins)>0 and max([1  if i['idPlugin']=='56d5e249a98895a9797bebb9' else 0 for i in myplugins])==1:
        print("Custom Fields already enabled")
    else:
        response = requests.request("POST", url, params=querystring)
    
    return this_board, this_board.id

def Return_board_by_name(mykey,mysecret,mytoken,board_name):
    # For given credentials and board name, returns the board object and those credentials again.

    client = TrelloClient(api_key=mykey,api_secret=mysecret,token=mytoken)
    # List all the boards which are currently in existence
    all_boards = client.list_boards()
    # Create "this_board" object
    this_board=[board for board in all_boards if board.name==board_name][0]
    
    return this_board, this_board.id,(this_board,mykey,mysecret,mytoken,this_board.id,board_name,client)

def Return_custom_fields_on_a_board(myboard_creds):
    myboard, mykey,mysecret,mytoken,myboard_id, myboard_name,client=myboard_creds
    
    mycustfields=client.fetch_json("/boards/"+myboard.id+"/customFields") #Pull a list, 
    if len(mycustfields)>0:
        cust_field_names=[i['name'] for i in mycustfields]
    else:
        cust_field_names=[]
        
    return cust_field_names,mycustfields

def customFieldFullLookup(board_creds):
    # Function just calls to get the custom fields JSON for a board and then flattens lists etc to create a name lookup and a value lookup (lists only)
    boardFields=Return_custom_fields_on_a_board(board_creds)

    # Lookup for Field ID >> Name and Vice Versa
    customFieldNameLookup=[{'fieldId':field['id'],'fieldName':field['name'],'fieldType':field['type']} for field in boardFields[1]]

    # Lookup for List Custom Field Values 
    customFieldListValueLookup=[{'fieldId':val['idCustomField'],'valueId':val['id'],'value':val['value']['text'],'colour':val['color']} for sublist in \
    [field['options'] for field in boardFields[1] if field['type']=='list' and len(field['options'])>0] for val in sublist]

    return customFieldNameLookup,customFieldListValueLookup
        
def Return_field_id(myboard_creds,field_name):

    # Returns the trello ID of a specific named field on a given board
    # Unpack board and credentials attributes
    myboard, mykey,mysecret,mytoken,myboard_id, myboard_name,client=myboard_creds
    
    mycustfields=Return_custom_fields_on_a_board(myboard_creds)[1] #Pull a list, 
    field_id=[i['id'] for i in mycustfields if i['name']==field_name][0]
    return field_id

def Return_field_type(myboard_creds,field_name):
   
    # Unpack board and credentials attributes
    myboard, mykey,mysecret,mytoken,myboard_id, myboard_name,client=myboard_creds
    mycustfields=Return_custom_fields_on_a_board(myboard_creds)[1] #Pull a list, 
    field_type=[i['type'] for i in mycustfields if i['name']==field_name][0]
    return field_type

def Return_list_field_mappings(myboard_creds,field_name):
    # Unpack board and credentials attributes
    myboard, mykey,mysecret,mytoken,myboard_id, myboard_name,client=myboard_creds
    
    Value_mapping={}
    mycustfields=Return_custom_fields_on_a_board(myboard_creds)[1] #Pull a list, 
    
    for i in mycustfields:
        if i['name']==field_name:
            if 'options' in i.keys():
                for x in i['options']:
                    Value_mapping[x['value']['text']]=x['id']
                    

    return Value_mapping

def Update_custom_field(myboard_creds,cardId,customFieldname,value):
    
    # Unpack board and credentials attributes
    myboard, mykey,mysecret,mytoken,myboard_id, myboard_name,client=myboard_creds
    
    # Get field attributes
    customFieldId=Return_field_id(myboard_creds,customFieldname)
    field_type=Return_field_type(myboard_creds,customFieldname)
    Value_mapping=Return_list_field_mappings(myboard_creds,customFieldname)
    
    data={}
    if len(str(value))==0:
        status_code='N/A'
    elif str(value)=='nan':
        status_code='N/A'
    else:
        if field_type=="list":
            #print("Original value is: ", value)
            try:
              #  print("Which resolves to: ",Value_mapping[value])
                data = { "idValue": Value_mapping[value] } 
            except:
                return
        else:
            if field_type =="text":
                data= { "value": { "text": value } }

            elif field_type =="number":
                data= { "value": { "number": str(value) } }

            elif field_type=="checkbox":
                if value in [1,"Yes","yes","y","Y","True","true","TRUE"]:
                    new_value="true"
                else:
                    new_value="false"
                data={ "value": { "checked": new_value } }
                
            elif field_type=="date":
                if value==None:
                    new_value=value
                elif len(value)>0:
                    new_value=value+"T12:00:00.000Z"
                else:
                    new_value=value
                #print(new_value)
                data={ "value": { "date": new_value } }

        url = f'https://api.trello.com/1/card/{cardId}/customField/{customFieldId}/item?&key={mykey}&token={mytoken}'
        response = requests.put(url, json=data)

        status_code=response.status_code
        if status_code!=200 and value!=None:
            print(customFieldname," was unable to be set to ",value)
        
            
def Add_list_field_option(myboard_creds,field_name,field_value):
    
    # Unpack board and credentials attributes
    myboard, mykey,mysecret,mytoken,myboard_id, myboard_name,client=myboard_creds
    
    # Adds a single option to a list style custom field

    
    
    # Retrieve the JSON for the specific custom field as it is
    try:
        existing_field_info=Return_custom_fields_on_a_board(myboard_creds)[1]
        
        existing_list_value=Return_list_field_mappings(myboard_creds,field_name)
        field_type=Return_field_type(myboard_creds,field_name)
        field_id=Return_field_id(myboard_creds,field_name)
    
        # Check if the field is actually a list, do not process further if not and just print an error
        if field_type !='list':
            print("No options added, variable is a "+field_type+" variable rather than a list variable")
        else:
            # Retrieve existing values held by the list variable
            
            if field_value in existing_list_value:
                print("Value:'"+field_value+"' already exists. Not added again!")
            else:        
                url = 'https://api.trello.com/1/customFields/'+field_id+'/options?key='+mykey+'&token='+mytoken
                #print(url)
                payload = {"value": { "text": field_value }}
                headers = {
                    'Content-Type': 'application/json',
                }
                response = requests.post(url, data=json.dumps(payload), headers=headers)
                if response.__nonzero__()==True:
                    print("Field updated successfully")
                else:
                    print("Field update failed")
    except:
        print("Field does not exist")
        
def MoveCard(card,listid,mykey,mytoken,boardid=None):
    # Establish basic parameters which are always passed
    headers = {"Accept": "application/json"}
    basequery = {'key': '{}'.format(mykey),'token': '{}'.format(mytoken)}

    # If boardid not specified, go and get it. Despite list IDs being unique, bizarrely Trello still needs it passed if moving between boards, so it's easiest to pass by default
    if boardid==None:
        # Find out what board destination list is currently on
        url = "https://api.trello.com/1/lists/{}/board".format(listid)
        response = requests.request("GET",url,params=basequery)
        boardid = json.loads(response.text)['id']

    # Add more items to the parameters
    query = basequery.copy()
    query['idList']='{}'.format(listid) # Add list ID to move to, to the parameters to pass
    query['idBoard']='{}'.format(boardid) # Add board ID to move to, to the parameters to pass

    url = "https://api.trello.com/1/cards/{}".format(card.id)
    response = requests.request("PUT",url,headers=headers,params=query)
    return response

def add_custom_field_to_board(myboard_creds,field_name,field_type,list_values=[]):
    
    myboard, mykey,mysecret,mytoken,myboard_id, myboard_name,client=myboard_creds
   
    #Retrieve the fields currently on the board (if any)
    field_names, custom_fields=Return_custom_fields_on_a_board(myboard_creds)
   
    # Create the field if it doesn't exist already
    if field_name not in field_names: 
        data_dict={"key":mykey,
                   "token":mytoken,\
                   "idModel":myboard_id, \
                   "modelType":"board", \
                   "name":field_name, \
                   "pos":0, \
                   "type":field_type, \
                   "display_cardFront": "true"
        }
        data = parse.urlencode(data_dict).encode()
        req =  request.Request("https://api.trello.com/1/customFields", data=data) # this will make the method "POST"
        resp = request.urlopen(req)
        print("Field '{}' created succesfully!".format(field_name))

    else:
        print("Field '{}' not added as it exists on the board already".format(field_name))

    ########################################################################################
    #If it's a list field and values have been provided, add them
    ########################################################################################

    if len(list_values)>0 and field_type=="list":
        # Refresh the field list
        custom_fields=client.fetch_json("/boards/"+myboard_id+"/customFields") #Pull a list, each item holding a dictionary for a field
        try:
            field_id=[i['id'] for i in custom_fields if i['name']==field_name][0]
            for i in list_values:
                Add_list_field_option(field_id,mykey,mytoken,i)
        except:
            print('ERROR: List items not added successfully')

def Export_dataframe_to_excel(df_to_export,Filename,column_width_cap,export_index=True,Include_date='N'):

    
    if Include_date=='N':
        writer = pd.ExcelWriter(Filename+'.xlsx', engine='xlsxwriter') #Define excel export writer, and filename
    else:
        writer = pd.ExcelWriter(datetime.strftime(date.today(),"%Y%m%d")+' '+Filename+'.xlsx', engine='xlsxwriter') #Define excel export writer, and filename
        
    df_to_export.to_excel(writer, index=export_index)
    worksheet = writer.sheets['Sheet1']
    for idx, col in enumerate(df_to_export):  # loop through all columns
        series = df_to_export[col]
        max_len = min((max((
            series.astype(str).map(len).max(),  # len of largest item
            len(str(series.name))  # len of column name/header
            )) + 1,column_width_cap))  # adding a little extra space
        #print(series.name+" has a max length of "+str(series.astype(str).map(len).max())+" and a header length of "+\
        #      str(len(str(series.name)))+" so we set column width to "+str(max_len))
        if export_index==True:
            worksheet.set_column(idx+1, idx+1, max_len)  # set column width
        else:
            worksheet.set_column(idx, idx, max_len)  # set column width
            
    #Automatically apply a filter
        #worksheet.autofilter(0,0,df_to_export.shape[0],df_to_export.shape[1])
        #worksheet.filter_column_list(0, 'Team Relevant'==True)
    writer.save()


def Read_Google_Sheet_into_Cards(myboard_creds,default_field_dict,custom_field_dict,google_creds,spreadsheet_id,sheetname):
    
    ##########################################################################################################
    ##### Read the Google sheet into a dataframe and then list of dictionaries. This first section could be altered
    ##### if we wanted to make it read from a local CSV or Excel file instead, along with the last section
    ##########################################################################################################
 
    # Read in the specified sheet as a list of lists
    google_sheet_rows,sheet_df=gaf.read_google_sheets_as_rows(spreadsheet_id,sheetname,google_creds)
    
    # Convert imported sheet into a dictionary
    sheet_dict=sheet_df.to_dict(orient='records')
    
    ##########################################################################################################
    # Unpack Trello board and credentials attributes
    ##########################################################################################################
   
    myboard, mykey,mysecret,mytoken,myboard_id, myboard_name,client=myboard_credsmyboard, mykey,mysecret,mytoken,myboard_id, myboard_name,client=myboard_creds
    
    ##########################################################################################################
    ##### Evaluate the accuracy of the dictionaries passed through. By assigning here, it'll throw an error  ##############
    ##########################################################################################################
    try:
        sheet_df[default_field_dict["list name"]]
    except:
        print("List name field '{}' not found".format(default_field_dict["list name"]))
        return
    
    try:
        sheet_df[default_field_dict["name"]]
    except:
        print("Card name field '{}' not found".format(default_field_dict["name"]))
        return
    
    try:
        sheet_df[default_field_dict["desc"]]
    except:
        print("Description field '{}'' not found".format(default_field_dict["desc"]))
        return
    
    try:
        sheet_df[default_field_dict["Trello Key"]]
    except:
        print("Trello Key field {} not found".format(default_field_dict["Trello Key"]))
        return
    
    for i in default_field_dict["labels"]:
        try:
            sheet_df[[i]]
        except:
            print("Label field {} not found".format([i]))
            return

    ##########################################################################################################
    ##### Loop each row in the table ##############
    ##########################################################################################################     
    for n,card in enumerate(sheet_dict):
        if card[default_field_dict["Trello Key"]] is not None and len(card[default_field_dict["Trello Key"]])>0:
            print("Card {} already on board".format(card[default_field_dict["name"]]))
        else:
        ##########################################################################################################
        ##### Parse the list of variables holding labels into sublists ##############
        ##########################################################################################################  
            card_labels=[]
            for j in default_field_dict["labels"]: # For each column holding labels
                try:
                    [card_labels.append(x.strip()) for x in card[j].split(',')]
                except:
                    pass
            card_label_ids=[x for x in myboard.get_labels() if x.name in card_labels]
            #print(card_labels)
            #print(card_label_ids)


        ##########################################################################################################
        ##### Get list that the card will be added to ##############
        ##########################################################################################################
            try:
                list_to_add_to=[x for x in myboard.list_lists() if x.name==card[default_field_dict["list name"]]][0]
            except:
                print("List '"+list_name+"' cannot be found, skipping card"+card[default_field_dict["name"]])
                break

        ##########################################################################################################
        ##### Add the card to the list ##############
        ##########################################################################################################    
            this_card=list_to_add_to.add_card(name=card[default_field_dict["name"]],\
                    desc=card[default_field_dict["desc"]]\
                                              ,labels=card_label_ids)



        ##########################################################################################################
        ##### Loop through custom fields adding them ##############
        ##########################################################################################################   
            for key in custom_field_dict:
                #print(key)
                #print(card[custom_field_dict[key]])
                Update_custom_field(myboard_creds,this_card.id,key,card[custom_field_dict[key]])

        ##########################################################################################################
        ##### Return the Trello Card ID and add it back into the Google sheet ##############
        ##########################################################################################################   
            gaf.Update_cell(google_creds,spreadsheet_id,sheetname,gaf.Get_cell_ref(n+1,default_field_dict["Trello Key"],google_sheet_rows),this_card.id,value_input_option = 'RAW')
            gaf.Update_cell(google_creds,spreadsheet_id,sheetname,gaf.Get_cell_ref(n+1,default_field_dict['Trello Link'],google_sheet_rows), this_card.short_url, value_input_option = 'RAW')

    
    return

def Get_board_creation_time(board_id):
    creation_time = datetime.fromtimestamp(int(board_id[0:8],16))
    utc_creation_time = pytz.utc.localize(creation_time)
    return utc_creation_time





def get_session():
    # Function for use elsewhere for parallel processing
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
    return thread_local.session

def loadCard(card,n=1,naming_dict={'name':'Name','labels':'Labels','list':'List'}\
                      ,labels_as_binary_flags=False\
                        ,label_colours=False\
                       ,comment_names=False\
                       ,checklist_options='Numbered'\
                       ,checklist_names=[]\
                       ,delimiter='| '\
                       ,get_attachments=False\
             ,my_lists=[],board_labels=None,mykey=None, mytoken=None,boardLookups=None):

    # This creates a threaded session facilitating parallel requests
    session = get_session()
    
    # apicheck1=session.get('https://api.trello.com/1/members/me',params={'key':mykey,'token':mytoken}) 
   
    ################### Card basic info #####################################################################
    # 0 API calls
    card_dict={}
    #print(n,': ',card.name,)
    card_dict[naming_dict['name']]=card.name
    card_dict['Description']=card.description
    
    card_list_name=[x.name for x in my_lists if x.id==card.list_id][0] # Store in a variable for use later, retrieve without another call
    card_dict[naming_dict['list']]=card_list_name
    card_dict['Due Date']=card.due_date
    card_dict['Trello ID']=card.id
    card_dict['Trello URL']=card.short_url
    card_dict['Card Object']=card

    ################### Creation date #####################################################################
    # 0 API calls
    creation=card.card_created_date
    try:
        card_dict['Card Created Date']=str(creation)[:10]
    except:
        pass


    ################### Checklists #####################################################################
    # N API calls where N=num checklists
    
    if len(checklist_names)>0: #If there are no listed checklists, take them all
        checklists_to_export=card.checklists
    else:
        checklists_to_export=[i for i in card.checklists if i.name in checklist_names]

    if checklist_options in ['Numbered','Columns']:
        for m,i in enumerate(checklists_to_export):
            url = "https://api.trello.com/1/checklists/{}/checkItems".format(i.id)
            querystring = {"filter":'all',"fields":'all',"key":mykey,"token":mytoken}
            
            ### Utilise the threaded/ parallelised session to get the response
            #response = requests.request("GET", url, params=querystring)
            response = session.get(url,params=querystring) 
            
            if checklist_options=='Numbered': #Store checklist values in a column named checklist 1, checklist 2 etc.
                card_dict['Checklist_{}'.format(m)]=delimiter.join(['List ({}) Item ('.format(i.name)+x['name']+'):'+x['state'] for x in json.loads(response.text)])

            elif checklist_options=='Columns': # Store each checklist in a unique column
                card_dict[i.name]=delimiter.join([x['name']+':'+x['state'] for x in json.loads(response.text)])

    ################### Comments #####################################################################
    # 0 API calls
    if comment_names==False:
        card_dict['Comments']=delimiter.join([x['data']['text'] for x in card.comments])
    else:
        card_dict['Comments']=delimiter.join([x['memberCreator']['username']+': '+x['data']['text'] for x in card.comments])

    ################### Labels #####################################################################
    # 0 API calls
    if card.labels==None:
        pass
    else:
        if label_colours==False:
            card_dict[naming_dict['labels']]=delimiter.join([x.name for x in card.labels])   
        else:
            card_dict[naming_dict['labels']]=delimiter.join([x.name+': '+x.color for x in card.labels])

        if labels_as_binary_flags==True:
            for x in board_labels:
                if x in card.labels:
                    card_dict[x.name]=True
                else:
                    card_dict[x.name]=False
    
    ################### Attachments #####################################################################
    if get_attachments==True:
        card_attachments=card.get_attachments()
        card_dict['Trello attachments']=delimiter.join([i.url for i in card_attachments if 'trello' in i.url])
        card_dict['Other attachments']=delimiter.join([i.url for i in card_attachments if 'trello' not in i.url])

    ################### List Movements #####################################################################
   
    movements=card.list_movements() # Get card movements

    movements2=[{'from':i['source']['name'],\
                'to':i['destination']['name'],\
                'when':i['datetime'].replace(tzinfo=None)} for i in movements] # Rename & subset the fields
    
    ### Add in records for "creation">> first list and current_list to "now"
    if len(movements2)==0:
        movements2=[{'from':'Nothing','to':card_list_name,'when':creation},\
                   {'from':card_list_name,'to':'Refresh','when':datetime.now()}\
                   ]

    else:
        movements2.append({'from':'Nothing','to':movements2[-1]['from'], 'when':creation})
        movements2.append({'from':card_list_name,'to':'Refresh','when':datetime.now()})
    
    # Convert to a dataframe and order by time for further analysis
    movement_df=pd.DataFrame(movements2).sort_values(by='when')
    
    movement_df=movement_df.rename(columns={'when':'exitedTime','from':'enteredList','to':'exitedTo'}) # Rename cols (again)
    movement_df['enteredTime']=movement_df['exitedTime'].shift(1) # Get lagged value of list exited to get list entered date 
    movement_df['timeSpent']=(movement_df['exitedTime']-movement_df['enteredTime']).dt.days # Calc days in list
    movement_df['isCurrent']=movement_df['enteredList'].apply(lambda x: 1 if x==card_list_name else 0) # Flag current list
    
    ### Summary stats
    summary_df=movement_df[['isCurrent','enteredList','timeSpent','enteredTime','exitedTime']].groupby(['isCurrent','enteredList']).\
        agg({'timeSpent' : [np.sum, 'count'],\
    'enteredTime' : [np.min, np.max],'exitedTime':'max'}).\
        rename(columns={'sum':'timeSpent','count':'timesEntered','amin':'FirstEntered','amax':'LastEntered',\
                        'max':'LastExited'}).droplevel(level=0,axis=1)
    
    ### Convert back to dict
    summary_dict=summary_df.reset_index().to_dict(orient='rows')
    current_list_summary=[i for i in summary_dict if i['isCurrent']==1][0] # Subset to just current row
    
    card_dict['listMovementHistory']=movement_df.reset_index(drop=True).to_dict(orient='rows')
    card_dict['listMovementSummary']=summary_dict
    
    card_dict['currentListTimeSpent']=current_list_summary['timeSpent']
    card_dict['currentListTimesEntered']=current_list_summary['timesEntered']
    card_dict['currentListFirstEntered']=current_list_summary['FirstEntered']
    card_dict['currentListLastEntered']=current_list_summary['LastEntered']
    
    
    ################### Custom Field Info #####################################################################
    
    # Option 1: Using Trello class 
    ################ There is an inbuilt function in the Trello Class, but it makes a lot of API calls, smashing the limit and preventing parallel running
    #card_fields=card.fetch_custom_fields()
    #for field in card_fields:
    #    card_dict[field.name]=field.value
        #field.type may be useful
    ################
        
    # Option 2: Using requests 
    ############### So instead I look up info once at a board level
        
    # Get cards fields JSON (one call)
    #cardFields=json.loads(requests.request("GET", 'https://api.trello.com/1/cards/{}/customFieldItems'.format(card.id), params={'key':mykey,'token':mytoken}).text)
    cardFields = json.loads(session.get('https://api.trello.com/1/cards/{}/customFieldItems'.format(card.id),params={'key':mykey,'token':mytoken}).text)
    
    # id is the card ID, idCustomField is hte field ID , idValue is the lookup list value
    
    # Required boardLookup object as returned by customFieldFullLookup function>> This is to save on multiple calls to determine each field type
    for i in cardFields:
        fieldDict={}

        # Lookup field name and type
        for j in boardLookups[0]:
            if i['idCustomField']==j['fieldId']:
                fieldDict['name']=j['fieldName']
                fieldDict['type']=j['fieldType']

        # Return value
        # If list, value needs looking up
        if fieldDict['type']=='list':
            for k in boardLookups[1]: # k is the list field value lookup, i is the actual values on the card for a given field
                if i['idCustomField']==k['fieldId'] and i['idValue']==k['valueId']:
                    fieldDict['value']=k['value']

        # If other type, value held directly
        elif fieldDict['type']=='checkbox':
            fieldDict['value']=i['value']['checked']
        elif fieldDict['type']=='number':
            fieldDict['value']=i['value']['number']
        elif fieldDict['type']=='text':
            fieldDict['value']=i['value']['text']
        elif fieldDict['type']=='date':
            fieldDict['value']=i['value']['date'][:10] # Remove mess
        card_dict[fieldDict['name']]=fieldDict['value']

     ################### END of Custom Field Info #####################################################################


    
    
    
    apicheck2=session.get('https://api.trello.com/1/members/me',params={'key':mykey,'token':mytoken}) 
    # calls_used=int(apicheck1.headers['X-Rate-Limit-Api-Token-Remaining'])-int(apicheck2.headers['X-Rate-Limit-Api-Token-Remaining'])
    # print('There are {} calls remaining in quota. This card used {} calls.'.format(apicheck2.headers['X-Rate-Limit-Api-Token-Remaining'],calls_used)) # See if hitting up against rate limits
    
    time.sleep(10/(int(apicheck2.headers['X-Rate-Limit-Api-Token-Remaining'])+1))
    #if int(apicheck2.headers['X-Rate-Limit-Api-Token-Remaining'])<50:
    #    time.sleep(.5)

    return card_dict
    
def cards_to_dataframe(myboard_creds\
                       ,naming_dict={'name':'Name','labels':'Labels','list':'List'}\
                      ,labels_as_binary_flags=False\
                        ,label_colours=False\
                       ,comment_names=False\
                       ,checklist_options='Numbered'\
                       ,checklist_names=[]\
                       ,delimiter='| '\
                       ,card_number_cutoff=10000\
                       ,get_attachments=False\
                       ,lists_to_exclude=None
                      ):
    
  
    
    # Error catching
    if 'name' not in naming_dict.keys():
        print("ERROR: naming dictionary needs a key-value for 'name' or to not be passed at all")
    if 'labels' not in naming_dict.keys():
        print("ERROR: naming dictionary needs a key-value for 'name' or to not be passed at all")
    if 'list' not in naming_dict.keys():
        print("ERROR: naming dictionary needs a key-value for 'name' or to not be passed at all")
    
      
    # Unpack board and credentials attributes
    myboard, mykey,mysecret,mytoken,myboard_id, myboard_name,client=myboard_creds
  
    # Get board properties once so that API call isn't made for each card
    if labels_as_binary_flags==True:
        board_labels=myboard.get_labels() #Retrieve all labels on board for reference
    else:
        board_labels=None
    

    
    my_lists=myboard.list_lists()
    
    # Conditionally load cards depending on whether they are in appropriate list
    if lists_to_exclude:
        filteredLists=[listObj for listObj in my_lists if listObj.name not in lists_to_exclude] # Create a filtered list of lists
        my_cards=[cardObj for cardObj in [listObj.list_cards() for listObj in filteredLists]] # Load only cards on those lists
        my_cards = [cardObj for cardList  in my_cards for cardObj in cardList ] # Flatten list out
    else:
        my_cards=myboard.get_cards() # Single call to get all cards on board

    boardLookups=customFieldFullLookup(myboard_creds) # Lookup tables for Custom Field Names and Custom Field Values (if a list)
    
    # Store these so they can be passed onwards to each individual card load later
    paramsToInherit={'naming_dict':naming_dict\
                      ,'labels_as_binary_flags':labels_as_binary_flags\
                        ,'label_colours':label_colours\
                       ,'comment_names':comment_names\
                       ,'checklist_options':checklist_options\
                       ,'checklist_names':checklist_names\
                       ,'delimiter':delimiter\
                       ,'get_attachments':get_attachments\
                        ,'my_lists':my_lists\
                     ,'board_labels':board_labels\
                    ,'mykey':mykey\
                    ,'mytoken':mytoken,
                    'boardLookups':boardLookups}
    
    card_list=[]

    
    
    
    cardLoop=enumerate(my_cards) # Store cards to load in an enumerated iterable
    cardLoop=[{**{'card':i[1],'n':i[0]},**paramsToInherit} for i in cardLoop if i[0]<=card_number_cutoff] # Convert to list and subset to only the number of cards specified in function call. Also make the card object the first argument and n the second
   
    # Log start time
    start_time = time.time()
    
    ###########################
    # Run in PARALLEL
    # In testing, it took 45s for serial processing of 70 cards, 1.7s for parallel processing of 
    ###########################

    # The .map function takes lists of parameters e.g. 
    # rather than (param1=a, param2=1), (param1=b, param2=2),(param1=c, param2=3)
    # it wants [a,b,c],[1,2,3]
    
    listofLists=[]
    for key in cardLoop[0]:
        listofLists.append([x[key] for x in cardLoop])
    
    # max_workers=None defaults to num_CPUs*5 . This can be hard overwritten with a number. The None option was too fast and hit up against API rate limits, so hard coded.
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        card_list=executor.map(loadCard, *listofLists)
        
        
    ###########################
    # Run in SERIAL
    ###########################
    #    [card_list.append(loadCard(**i)) for i in cardLoop]
    
    # Calculate time taken to get through list of cards
    
    
    duration = time.time() - start_time
    print("Downloaded {} in {} seconds".format(len(cardLoop),duration))
    
    
    
    
    ###########################
    # Get positional information
    ###########################
    list_names={i.id:i.name for i in my_lists} # List Name lookup
    list_pos={i.id:n+1 for n,i in enumerate(my_lists)} # List Position lookup
    cardpos=pd.DataFrame([{'cardid':card.id,'name':card.name, 'pos': card.pos, 'list':list_names[card.list_id],\
                           'listpos':list_pos[card.list_id]} for card in my_cards]).sort_values(by=['listpos','pos'])
    cardpos['boardpos']=cardpos.reset_index().index+1
    cardpos['cardpos']=cardpos.groupby('listpos').cumcount()+1
    #cardpos=[i['listpos']:list_pos[i['list']] for i in cardpos ]
    poslist=cardpos.drop(columns=['pos']).to_dict(orient='rows')
    
    card_list_withPos=[]
    for card in card_list:
        for matched_card in poslist:
            if card['Trello ID']==matched_card['cardid']:
                card['listpos']=matched_card['listpos']
                card['cardpos']=matched_card['cardpos']
                card['boardpos']=matched_card['boardpos']
                card['coordinates']=(matched_card['listpos'],matched_card['cardpos'])                
                card_list_withPos.append(card)
    
    #card_list=list(card_list)
    card_list_for_df=[{key:val for key, val in i.items() if key != 'Card Object'} for i in card_list_withPos]
    card_df=pd.DataFrame(card_list_for_df) # Store as a dataframe
    
    
    return card_df,card_list_withPos
    
    
     