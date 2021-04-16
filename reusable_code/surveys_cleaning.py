import pandas as pd
import os
import numpy as np
import ast
from fuzzywuzzy import process
from sheets import *


def read_files(df_sheet, 
               directory = 'resources',  
               source = 'drive', 
               folder_id = '1PTq78LHV3yeG89j-K4TVUvaOlFMI4Iz-', 
               drive = None
              ):
    final_df = pd.DataFrame()
    if source == 'drive':
        if not drive:
            drive = connect_to_drive()
        file_list = get_list_of_files_folder(folder_id,drive)
    else:
        file_list = os.listdir(directory)
    for i in file_list:
        if source == 'drive':
            filename = i['title']
            if i['mimeType'] == 'text/csv':
                downloaded = drive.CreateFile({'id':i['id']})
                downloaded.GetContentFile(filename)
        else:
            filename = i
        if filename.endswith('.csv'):
            print(filename)
            # split file name into different pieces to get the date
            split_file = filename.split('-')
            # get year and month from filename
            year, month = split_file[0], split_file[1]
            # format date
            date = f'{year}-{month}-01'
            # read csv from into a dataframe
            df = pd.read_csv(filename)
            """redesign this into selecting columns and dimensions from sheet"""
            #select columns from google sheet
            columns = list(df_sheet[df_sheet['column names'].isin(df.columns)]['column names'])
            # join questions and dimensions into one dataframe
            df = df[columns]
            df['year'] = year
            df['month'] = month
            df['date'] = pd.to_datetime(date)
            final_df = pd.concat([final_df, df], join='outer')
    final_df.reset_index(inplace = True, drop = True)
    final_df['id'] = final_df.index + 1
    return final_df


def create_question_df(df, mapping_df, question, dimensions = ['date','id','weight','age3']):
    # get dataframe with column names and aliases
    df_columns  = mapping_df[['column names','Full Q text']][mapping_df['Q lookup'] == question]
    if question == 'Q1':
        # in question one only get the recoded asnwers to avoid dealing with free text
        df_columns = df_columns[df_columns['column names'].str.contains("recoded")]
    # list of columns
    columns = list(df_columns['column names'])
    # list of aliases
    column_names = list(df_columns['Full Q text'])
    # select columns
    q = df[dimensions + columns]
    # select aliases
    q.columns = dimensions + column_names
    return q


def clean_data(df):
    # get the number of columns we'll get from the title
    columns = len(df['variable'][0].split('-'))
    # the first part of the split will be always the question title
    df['question'] = df['variable'].apply(lambda x: x.split('-')[0].strip())
    # if we have only one column name return df
    if columns == 1:
        return df
    # assign second column to x
    df['x'] = df['variable'].apply(lambda x: x.split('-')[1].strip())
    # if in the x column we get Britbox or youtube we'll know this is a brand column and 
    # we'll call that column brands, otherwise answer
    if 'BritBox' in list(df['x'].unique()) or 'YouTube' in list(df['x'].unique()):
        column_1, column_2 = ('brands' , 'answer')
    else:
        column_1, column_2 = ('answer','brands')
    df[column_1] = df['x']
    del df['x']
    # if there are three possible columns the last column will be either brands or answer
    # based on the condition above
    if columns == 3:
        df['y'] = df['variable'].apply(lambda x: x.split('-')[2].strip())    
        df[column_2] = df['y']
        del df['y']
    return df


def make_numeric(x):
    if x is np.nan:
        return np.nan
    elif x == 'selected':
        return 1
    elif x == 'not selected':
        return 0
    else:
        return x


def subscription_dimension(df, question = 'Q4'):
    # we get all the columns for question 4 which includes the services someone is susbcriber to or not
    all_questions = df.columns
    question_unique = list(filter(lambda k: question in k, all_questions))
    q_df = df[['id'] + question_unique]
    # look for the ones were people is actually subscribed
    q_df[question_unique] = q_df[question_unique] == 'selected'
    # transform it to an integer to sum the total number of subscriptions
    q_df = q_df.astype('int')
    #get total number of subscriptions per respondant
    q_df['subscription'] = q_df[question_unique].apply(lambda x: x.sum(), axis = 1)
    return q_df[['id','subscription']]


def assign_service(x,services):
    """function to unify services. I'll try to match to the most similar ones from a set list,
    using the fuzzywuzzy package"""
    value, score = process.extractOne(x, services)
    # I wasn't able to match to services with '+', so I'll remove services '+' from the list and 
    # will add a '+' to the string if the original has '+' sign
    if '+' in x:
        value = value + '+'
    if score > 80:
        return value
    return 'Other'


def unique_brands(df, 
    services = ['All 4','Amazon Prime','Apple TV','BBC iPlayer','BritBox','Disney Life/Disney Masterbrand',
    'Disney Plus','Hayu','ITV Hub','My5','Netflix','None','Now TV','Other','YouTube','Acorn TV']):
    #get all the unique brands from the survey responses
    brands = pd.DataFrame(df['brands'].drop_duplicates().reset_index()['brands'])
    brands.dropna(inplace = True)
    # assign one of the predifined brands
    brands['brands_unique'] = brands['brands'].apply(lambda x: assign_service(x, services))
    return brands


def create_final_dataframe(all_dfs, 
                           df_sheet, 
                           remove_nan = False,
                           authentication_file = 'creds.json',
                           g_credentials = None
                           ):
    
    final_df = pd.DataFrame()
    # read selection of questions and dimensions from google sheet 
    selection = read_from_sheet_to_df(sheet_name = 'select_columns',    
                                      wks_name = 'Brand_tracker_columns', 
                                      authentication_file = authentication_file,
                                      g_credentials = g_credentials
                                     )
    # get selected questions
    questions_unique = list(selection['Questions'][selection['selected questions'] == 'TRUE'])
    # get bins 
    bins = list(selection['Bins'][selection['selected questions'] == 'TRUE'])
    # get selected dimensions
    dimensions_sheet = list(selection['Dimensions'][selection['selected dimensions'] == 'TRUE'])
    dimensions = ['id','date','weight'] + dimensions_sheet
    # calulcate itv hub usage if selected in dimensions
    if 'itv_hub_usage' in dimensions:
        all_dfs['itv_hub_usage'] = all_dfs['Q3_2'].fillna('Never')
    # calulcate britbox_itp if selected in dimensions
    if 'britbox_itp' in dimensions:
        all_dfs['britbox_itp'] = pd.cut(all_dfs['Q5b2_4'], 
                                        bins = [-1,4,7,10] , 
                                        labels = ['0-4','5-7','8-10']
                                       )
    # if any of the subscribed questions in dimension calculate them
    if '25_54_and_+1_svod' in dimensions or 'subscribed_any_svod' in dimensions:
        # get number of subscriptions per respondant
        q_df = subscription_dimension(all_dfs)
        all_dfs = pd.merge(all_dfs,q_df, on = 'id')
        # create subscribed to any svod dimension
        all_dfs['subscribed_any_svod'] = all_dfs['subscription'] >= 1
        # create 25 to 54 and +1 svod subscription dimension
        all_dfs['25_54_and_+1_svod'] = (all_dfs['subscription'] > 1) & (all_dfs['age'] >= 25) & (all_dfs['age'] < 55)
    
    for q,b in zip(questions_unique,bins):
        print(q,b)
        df = create_question_df(all_dfs, df_sheet, q , dimensions )
        # melt dataframe to put some of the columns into rows
        melted_df = pd.melt(df, id_vars = dimensions)
        # clean the dataframe to add questions, answers and values
        clean_df = clean_data(melted_df)
        # convert some of the values into numeric if possible
        clean_df['value_numeric'] = clean_df['value'].apply(lambda x:  make_numeric(x))
        # if I can't convert them to numeric make null
        clean_df['value_numeric'] = pd.to_numeric(clean_df['value_numeric'], errors='coerce')
        if b != '':
            bins = eval(b)
            bins_name = bins
            # make a label based on bins
            labels = [f'{a+1}-{b}' for a, b in zip(bins_name[:-1], bins_name[1:])]
            # create bins with labels
            clean_df['bins'] = pd.cut(clean_df['value_numeric'], bins = bins, labels = labels)
        # concatenate to the final dataframe to have all questions in the same df
        final_df = pd.concat([final_df, clean_df], join='outer')
    if remove_nan:
        # drop nan values
        final_df = final_df.dropna(subset =['value'])
    brands = unique_brands(final_df)
    final_df = pd.merge(final_df, brands, on = 'brands', how = 'left')
    return final_df


def final_df(directory = 'resources', name = 'survey.csv', 
    source = 'drive', drive = None ,g_credentials = None):
    # read google sheet with questions
    df_sheet = read_from_sheet_to_df(sheet_name = 'Brand Tracker Mapping Spec',    
                                     wks_name = 'Brand_tracker_columns', 
                                     authentication_file = 'creds.json',
                                     g_credentials = g_credentials
                                    )
    # get all csvs and turn it into a dataframe
    all_dfs = read_files(df_sheet,
                         directory = directory, 
                         source = source,
                         drive = drive
                        )
    # format the dataframe into the expected output
    final_df = create_final_dataframe(all_dfs = all_dfs,
                                      df_sheet = df_sheet,
                                      g_credentials = g_credentials
                                     )
    final_df.to_csv(name, index = False)
    return final_df


def get_question_data(df, questions, trended = False, brand_filters = False, drop_nan = False, age_filter = False, months = 12):
    #filter by question name
    questions = questions.split(';')
    questions = [i.strip() for i in questions]
    q = df[df['question'].isin(questions)]
    # filter brand
    if brand_filters:
        brand_filters = brand_filters.split(';')
        brand_filters = [i.strip() for i in brand_filters]
        q = q[q.brands_unique.isin(brand_filters)]
    #filter date
    if trended:
        q['date'] = pd.to_datetime(q['date'])
        filter_date = q.date.max() - pd.DateOffset(months=months)
        q = q[q.date > filter_date]
    else:
        q = q[q.date == q.date.max()]
    # #drop nan in value
    if drop_nan:
        drop_nan = drop_nan.split(';')
        drop_nan = [i.strip() for i in drop_nan]
        q = q.dropna(subset = drop_nan)
    if age_filter:
        min_age, max_age = [int(i) for i in age_filter.split('-')]
        q = q[(q.age >= min_age) & (q.age <= max_age)]
    return q


def create_percent_total(df, 
                         index, 
                         columns = False, 
                         total_aggregate = 'group', 
                         values = 'selected', 
                         aggregation = {'weight':'sum'}
                        ):
    # if no columns just use the index for the group by
    group = [index]
    if columns:
        group = [index, columns]
    # decide what aggragate to calculate totals
    total_group = group
    if total_aggregate == 'index':
        total_group = index
    elif total_aggregate == 'column':
        total_group = columns
    # calculate totals
    total = df.groupby(total_group).agg(aggregation).reset_index()
    # get list of values
    values = values.split(';')
    values = [i.strip() for i in values]
    if values[0].isdigit():
        values = [float(i) for i in values]
    # turn values into selected
    df['value'] = df['value'].apply(lambda x: 'selected' if x in values else x) 
    selected = df.pivot_table(index = group,
                              columns = 'value',
                              values = 'weight',
                              aggfunc = 'sum'
                             ).reset_index()
    # join selected and total df
    final = pd.merge(total, selected, on = total_group)
    # calculate proportion
    final['proportion'] = final['selected'] / final['weight']
    final = final[group + ['proportion']]
    return final


def update_question_data(df,
                         questions,
                         index,
                         sheet_name = '',
                         trended = False, 
                         brand_filters = False, 
                         drop_nan = False,
                         columns = False, 
                         total_aggregate = 'group', 
                         values = 'selected', 
                         aggregation = {'weight':'sum'},
                         age_filter = False,
                         months = 12
                        ):
    # get the data for each of the questions
    question = get_question_data(df, questions, trended, brand_filters, drop_nan,age_filter, months)
    # get percent of totals for the each of the questions 
    final_data = create_percent_total(question,index, columns, total_aggregate, values, aggregation)
    # format the data with the right index and columns for the final graph
    if columns:
        pivot = final_data.pivot_table(index = index,
                                       columns = columns,
                                       values = 'proportion',
                                       aggfunc = 'sum'
                                      ).reset_index()
    else:
        pivot = final_data.sort_values(by = 'proportion', ascending = False)

    if columns == 'date':
        # if we have data in the columns format them into strings so we can have the right format in the spreadsheet
        final_data['date_string'] = final_data['date'].apply(lambda x: format_date(x))
        dates = final_data[['date','date_string']].drop_duplicates()
        columns_name = {row['date']:row['date_string'] for index, row in dates.iterrows()}
        pivot.rename(columns=columns_name, inplace = True)

    if index == 'date':
        # if we have data in the index format them into strings so we can have the right format in the spreadsheet
        pivot['date'] = pivot['date'].apply(lambda x: format_date(x))
    
    return pivot


def convert_to_boolean(string):
    # convert string to a boolean based on the text.    
    if string in ('False','',' ','FALSE','false'):
        return False
    elif string in ('True', 'TRUE', 'true'):
        return True
    else:
        return string


def format_date(x):
    # convert date to string format
    month = x.month_name()[:3]
    year = x.year
    return f'{month} {year}'


def update_charts(df, credentials = None, g_credentials = None):
    # combine all the functions to update final charts.
    # read index tab from the sheet to get inputs for the function
    index = read_from_sheet_to_df(sheet_name = 'Index',    
                                  wks_name = 'bar_chart_1', 
                                  authentication_file = credentials,
                                  g_credentials = g_credentials
                                 )
    # convert to boolean if needed.
    index_new = index.applymap(convert_to_boolean)
    # convert filter month to integer
    index_new['Filter_month'] = index_new['Filter_month'].astype('int')
    # update all the questions
    for i in range(len(index_new)):
        x = index_new.iloc[i,:]
        print(x.Sheet)
        # format data for the charts
        q = update_question_data(df,
                                 questions = x.Question,
                                 index = x.Index,
                                 sheet_name = x.Sheet,
                                 trended = x.Trended, 
                                 brand_filters = x.Brands_filter, 
                                 drop_nan = x.Dropna,
                                 columns = x.Column, 
                                 total_aggregate = x.Total_aggregate, 
                                 values = x.Numerator, 
                                 age_filter = x.Age_filter,
                                 months = x.Filter_month
                                )
        # if question is brand statemenst we have to sort it in a specific order.
        if x.Question == 'Brand statements':
            # sort brand statements in the right order for presentation
            brands_categories = ['Makes its own programmes', 
                                 'Has a good range of programmes available',
                                 'Has a large catalogue of programmes',
                                 'Programmes updated every week',
                                 'Is ad free',
                                 'Has quality programmes',
                                 'Has something I want to watch',
                                 'Has programmes you wont find elsewhere',
                                 'Is good value for money'
                                ]
            q['answer'] = pd.Categorical(q.answer,categories=brands_categories)
            q = q.sort_values(by = 'answer').reset_index(drop = True)
            q['answer'] = q['answer'].astype('str')
        # upload data to google sheet
        upload_df_to_sheet(q, 
                           wks_id = '1Qr4pikabBtff7M3fRJI-8l858C66pjp0ZRWEmbwgxlg', 
                           authentication_file = credentials,
                           g_credentials = g_credentials,
                           sheet_name = x.Sheet, 
                           x = 'A1',
                           clear_cells = False,
                           add_headers = True,
                           resize_sheet = False
                          )
    return 'finished'


 #----------------------------------------------Joiners Survey------------------------------------------------#   

def get_shows_list(authentication_file = None, gc = None):
    # read from file with all the shows
    unique_shows = read_from_sheet_to_df(sheet_name = 'Extract 1',    
                                         wks_name = 'Unique Programme List', 
                                         authentication_file = authentication_file,
                                         g_credentials = gc
                                        )
    return unique_shows


def get_shows_assigned(df, 
                       question = 'You mentioned you joined BritBox to watch a particular show or film. Which show or film was this?',
                       authentication_file = None, 
                       gc = None
                      ):
    # filter df by question
    x = df[df.question == question]
    # get base columns
    base_columns = x.columns
    # split value new column into multiple columns
    new = x['value_new'].str.split(' and |,|\&|/|\(|\.|-| of course', n = 10, expand = True)
    # join with df
    new_x = x.join(new)
    # melt df to have multiple rows per user with the different values
    new_x_melted = pd.melt(new_x, id_vars=base_columns)
    # drop nan and empty rows
    new_x_melted = new_x_melted[(new_x_melted['value'] != '')].dropna(subset=['value'])
    # get unique list of shows in the free text
    shows = new_x_melted[['value_new','value']].drop_duplicates()
    # get list of all the shows 
    shows_df = get_shows_list(authentication_file = authentication_file, gc = gc)
    shows_df['programme_title'] = shows_df['programme_title'].apply(lambda x: x.lower())
    show_list = list(shows_df['programme_title'])
    # assign shows from the list of shows
    shows['programme_title'] = shows.apply(lambda x: assign_show(show_list, x.value_new, x.value),axis = 1)
    # dataframe with all shows info
    final_shows = pd.merge(shows, shows_df, on = 'programme_title', how = 'left' )
    # merge all the shows info with the dataframe with users
    clean_df = pd.merge(new_x_melted,final_shows, on = ['value_new','value'], how = 'left')
    # format programme title to have first letter uppercase
    clean_df['programme_title'] = clean_df['programme_title'].apply(lambda x: x.title())
    # count the number of programmes matched per user to filter out later duplicates
    count_series = clean_df.groupby('UZ_ID').agg({'programme_id':'count'}).reset_index()
    count_series = count_series.rename(columns = {'programme_id':'count'})
    # merge count of programmes with users
    clean_df = pd.merge(clean_df, count_series, on = 'UZ_ID')
    # filter out duplicates
    clean_df = clean_df[(~clean_df['programme_id'].isnull()) | ((clean_df['variable'] == 0) & (clean_df['count'] == 0))]
    # list of final columns
    final_columns = list(base_columns) + list(shows_df.columns)
    # final dataframe
    return clean_df[final_columns]


def assign_show(shows_list, first_show, second_show):
    first_show = str(first_show).lower()
    second_show = str(second_show).lower()
    # assign a program from the programme list and a score of similarity to first show
    value_1, score_1 = process.extractOne(first_show, shows_list)
    # assign a program from the programme list and a score of similarity to second show
    value_2, score_2 = process.extractOne(second_show, shows_list)
    # only return matches with at least a score of 90
    if score_1 >= 90 and score_1 > score_2:
        return value_1
    elif score_2 >= 90 and score_2 >= score_1:
        return value_2
    else:
        return first_show


def convert_to_dict(x):
    if '=' in x:
        clean_string = x.replace('[','"').replace(']','"').replace('=',':')
        dict_string = '{'+clean_string+'}'
        return ast.literal_eval(dict_string)
    else:
        return x


def get_answer(x):
    x = x.split(' - ')
    if len(x) == 2:
        answer = x[1]
    elif len(x) == 3:
        answer = x[1] +' - '+ x[2]
    else: 
        answer = np.nan
    return answer


def question_to_dimensions(df, question, dim_name):
    dim_df = df[df['question'] == question]
    dim_df[dim_name] = dim_df['value_new']
    dim_df = dim_df[['UZ_ID',dim_name]]
    df_final = pd.merge(df, dim_df, on = 'UZ_ID')
    return df_final


def get_new_value(x, series):
    if x.value not in [9999,999,99999] and x.variable not in list(series):
        return x.Values[x.value]
    else:
        return x.value


def get_joiners_df(authentication_file = None, gc = None):
    # read Quantitative_Variables dataframe
    questions = read_from_sheet_to_df(sheet_name = 'Quantitative_Variables',    
                                      wks_name = 'new_joiners', 
                                      authentication_file = authentication_file,
                                      g_credentials = gc
                                     )
    # read Qualitative_Variables dataframe
    questions_qualitative = read_from_sheet_to_df(sheet_name = 'Qualitative_Variables',    
                                                  wks_name = 'new_joiners', 
                                                  authentication_file = authentication_file,
                                                  g_credentials = gc
                                                 )
    # Join qualitative and quantitave dataframe
    questions = pd.concat([questions, questions_qualitative], join='outer')
    # convert values to a dict to be able to match column names later using a dictionary
    questions['Values'] = questions['Values'].fillna('none')
    questions['Values'] = questions['Values'].apply(lambda x: convert_to_dict(x))
    # read Quantitative_RawData dataframe
    df = read_from_sheet_to_df(sheet_name = 'Quantitative_RawData',    
                               wks_name = 'new_joiners', 
                               authentication_file = authentication_file,
                               g_credentials = gc
                              )
    # read Qualitative_RawData dataframe
    df_qualitative = read_from_sheet_to_df(sheet_name = 'Qualitative_RawData',    
                                           wks_name = 'new_joiners', 
                                           authentication_file = authentication_file,
                                           g_credentials = gc
                                          )
    # join Quantitative and Qualitative dataframes
    df = pd.merge(df, df_qualitative, on = 'UZ_ID')
    # assign fix_dimensions
    fix_dimensions = ['UZ_ID',
                      'DataSegment',
                      'Study_Time',
                      'StartDate',
                      'EndDate']
    # melt quantitative raw dataframe to be able to give each question a name and answer
    df_melted = df.melt(id_vars = fix_dimensions)
    # join questions and df_melted based on the question code 
    df_final = pd.merge(df_melted,questions,left_on = 'variable',right_on = 'Variables')
    # fill nan values with 99999
    df_final['value'] = df_final['value'].fillna(99999)
    # convert code of each question to text using the dictionary we created above
    df_final['value_new'] = df_final.apply(lambda x: get_new_value(x,df_qualitative.columns), axis = 1)
    # get question from the label text
    df_final['question'] = df_final['Label'].apply(lambda x: x.split(' - ')[0].strip())
    # get answer from the label text
    df_final['answer'] = df_final['Label'].apply(lambda x: get_answer(x))
    # add age as another dimension
    df_final = question_to_dimensions(df_final,'How old are you?','Age')
    # get only the needed columns
    df_final = df_final[fix_dimensions + ['Age','question','answer','value_new']]
    # assign closer show from list of shows.
    shows = get_shows_assigned(df_final, 
                               authentication_file = authentication_file,
                               gc = gc)
    #filter out the question with shows from the main dataframe
    df_final = df_final[df_final.question != shows.question.unique()[0]]
    # merge final dataframe with shows dataframe
    final_df_shows = pd.concat([df_final, shows], join='outer')
    return final_df_shows