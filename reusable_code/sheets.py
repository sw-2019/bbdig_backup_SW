import datetime
import logging
import re
import string

import gspread
import numpy as np
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)


# TODO:
#   duplicate workbook
#   rename workbook

def connect_to_drive():
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)
    return drive


def get_list_of_files_folder(folder_id, drive):
    # get list of folders from specific folder in drive 
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents"}).GetList()
    return file_list


def get_credentials(authentication_file):
    """Get credentials object

    Args:
        authentication_file (dict): Service account json

    Returns:
        (ServiceAccountCredentials): credentials object
    """
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        authentication_file, scope)
    return credentials


def connect_to_gg_api(authentication_file):
    """return a connected gspread client

    Args:
        authentication_file (dict): Service account json

    Returns:
        (gspread.client.Client): Client object
    """
    credentials = get_credentials(authentication_file)
    connected_client = gspread.authorize(credentials)
    return connected_client


def connect_to_workbook(authentication_file=None, wks_name=None, wks_id=None, g_credentials = None):
    """Open the workbook using id or name

    Args:
        authentication_file (dict): Service account json
        wks_name (str, optional): workbook name. Defaults to None.
        wks_id (str, optional): workbook id. Defaults to None.

    Returns:
        (type): workbook object
    """
    if not authentication_file and not g_credentials:
        raise Exception('Please provide authentication')
    if g_credentials:
        gc = g_credentials
    else:
        gc = connect_to_gg_api(authentication_file)
    if wks_id:
        workbook = gc.open_by_key(wks_id)
    elif wks_name:
        workbook = gc.open(wks_name)
    else:
        raise Exception('Specify wks_name or wks_id')
    return workbook


def calculate_dataframe_cell_range(worksheet,
                                   dataframe,
                                   add_headers=True,
                                   resize_sheet=True,
                                   top_left_cell_range='A1'):
    row_count, column_count = dataframe.shape
    top_left_row, top_left_col = gspread.utils.a1_to_rowcol(
        top_left_cell_range)
    if add_headers:
        row_count += 1
    bottom_right_row = top_left_row + row_count - 1
    bottom_right_col = top_left_col + column_count - 1
    if resize_sheet:
        worksheet.resize(bottom_right_row + 1,
                        bottom_right_col + 1)
    return worksheet.range(top_left_row,
                           top_left_col,
                           bottom_right_row,
                           bottom_right_col)


def serialize(obj):
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (str, float, bool)):
        return obj
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.strftime("%Y-%m-%d")
    else:
        return str(obj)


def write_dataframe_to_cell(worksheet,
                            dataframe,
                            top_left_cell_range='A1',
                            add_headers=True,
                            resize_sheet=True,
                            clear_cells=False):
    if clear_cells:
        logger.info('Clearing sheet {title}'.format(title=worksheet.title))
        worksheet.clear()
    rng = calculate_dataframe_cell_range(
        worksheet=worksheet,
        dataframe=dataframe,
        add_headers=add_headers,
        resize_sheet=resize_sheet,
        top_left_cell_range=top_left_cell_range)
    vals = dataframe.fillna('').values.flatten()
    if add_headers:
        vals = np.concatenate((np.array(dataframe.columns), vals))
    for cell, val in zip(rng, vals):
        cell.value = serialize(val)
    logger.info('Writing data to {sheetname}'.format(
        sheetname=worksheet.title))
    worksheet.update_cells(rng, value_input_option='USER_ENTERED')
    return True


def upload_df_to_sheet(df, wks_id, sheet_name, authentication_file,
                       x='A1', clear_cells=True, resize_sheet=True,
                       add_headers=True, quick_clear=False, y=None, 
                       g_credentials = None
                       ):
    """Upload pandas.Dataframe to google sheet

    Args:
        df (pandas.Dataframe): Data to be inserted
        wks_id (str): workbook id (from url)
        sheet_name (str): sheet name
        authentication_file (dict): Service account connection detals (json)
        x (str, optional): Where to insert. Defaults to 'A1'.
        y (str, optional): Not used here for legacy reasons
        clear_cells (bool, optional): Clear sheet before insert. Defaults to True.
        resize_sheet  (bool, optional): resize sheet to df size + 1
        add_headers (bool, optional): Include column names. Defaults to True.
    """
    workbook = connect_to_workbook(
        authentication_file=authentication_file,
        wks_id=wks_id,
        g_credentials = g_credentials
        )
    try:
        worksheet = workbook.worksheet(sheet_name)
    except Exception as e:
        # Adding sheet if it doesn't already exist
        print(e)
        worksheet = workbook.add_worksheet(
            title=sheet_name,
            rows=len(df) + 10,
            cols=len(df.columns) + 3)
    write_dataframe_to_cell(worksheet,
                            df,
                            top_left_cell_range=x,
                            add_headers=add_headers,
                            resize_sheet=resize_sheet,
                            clear_cells=clear_cells)
    return None


########################################################################
# old fuctions below
########################################################################


def resize_sheet_if_required(wks, rows_needed, cols_needed):
    row_num = wks.row_count
    if not row_num > rows_needed + 10:
        rows_to_add = rows_needed + 10 - row_num
        wks.add_rows(rows_to_add)
    col_num = wks.col_count
    if not col_num > cols_needed:
        cols_to_add = cols_needed + 2 - col_num
        wks.add_cols(cols_to_add)

    return wks


def clean_cells_in_batch(wks, x, y, value):
    # Clean the sheet first to update with new names
    print("Clearing worksheet")
    cell_range = x + ':' + y
    cell_list = wks.range(cell_range)
    cell_num = 0
    cell_batch = []
    for cell in cell_list:
        cell_in_list = cell_list.index(cell)
        cell.value = value
        cell_num += 1
        cell_batch.append(cell)
        if cell_num == 20000 or cell_in_list >= len(cell_list) - 1:
            wks.update_cells(cell_batch)
            cell_num = 0
            cell_batch = []
            print("cleared cells up to {cell} of {cells}".format(
                cell=cell_list.index(cell), cells=len(cell_list)))

    # Recurring Function to update cells


def upload_list_to_sheet(l, wks_id, sheet_name, authentication_file, x='A1',
                         direction='h', clear_cells=True, g_credentials = None):
    sh = connect_to_workbook(
        wks_id=wks_id, authentication_file=authentication_file, g_credentials = g_credentials)
    try:
        wks = sh.worksheet(sheet_name)
        cols_needed = len(l)
        if type(l[0]) == list:
            cols_needed = len(l[0])
        wks = resize_sheet_if_required(
            wks=wks, rows_needed=len(l), cols_needed=cols_needed)
    except Exception:
        # Adding sheet if it doesn't already exist
        wks = sh.add_worksheet(
            sheet_name, rows=len(l) + 10, cols=len(l[0]) + 3)
    if direction == 'h':
        y = (chr(int(((len(l) - 1) / 26) + 64)) +
             chr(int(len(l) - (((len(l) - 1) / 26) * 26) + 64))
             ).lstrip('@') + re.sub('([A-Z]{1,6})', '', x)

    elif direction == 'v':
        y = re.sub('([0-9]{1,6})', '', x) + str(len(l))
    if clear_cells:
        clean_cells_in_batch(wks, x, y, '')
    cell_range = x + ':' + y
    cell_list = wks.range(cell_range)
    for index, cell in enumerate(cell_list):
        cell.value = l[index]
    wks.update_cells(cell_list)
    return None


def read_from_sheet_to_df(sheet_name, authentication_file, wks_name = None, wks_id = None, columns=None, g_credentials=None):
    if wks_id:
        sh = connect_to_workbook(
            wks_id=wks_id, authentication_file=authentication_file, g_credentials=g_credentials)
    elif wks_name:
        sh = connect_to_workbook(
            wks_name=wks_name, authentication_file=authentication_file, g_credentials=g_credentials)

    wks = sh.worksheet(sheet_name)
    if columns:
        df = pd.DataFrame(wks.get_all_records()).loc[:, columns]
    else:
        df = pd.DataFrame(wks.get_all_records())
    return df


def update_worksheet_index(workbook, sheet_name, new_index):
    sheet_to_move = workbook.worksheet(sheet_name)
    ix_update = {
        'requests': [{
            'updateSheetProperties': {
                'properties': {
                    'sheetId': sheet_to_move.id,
                    'index': new_index
                },
                'fields': 'index'
            }
        }]
    }
    sheet_to_move.spreadsheet.batch_update(ix_update)
    return True


def update_cell_range_in_batch(wks, cell_range, df, offset=1000):
    if df.shape[0] == 0:
        return
    col_names = re.sub('([0-9]{1,6}|:)', '', cell_range).upper()
    n_cols = (26 * (len(col_names) - 2)) + string.ascii_uppercase.index(col_names[-1]) - \
        string.ascii_uppercase.index(col_names[0]) + 1
    i = 1
    x = cell_range.split(':')[0]
    z = int(re.sub('[A-Z]', '', cell_range.split(':')[0])) - 1
    y = re.sub('[A-Z]', '', cell_range.split(':')[1])
    cell_ranges = [x + ':' + col_names[1:] + str(offset + z)]
    data = [df.iloc[:offset, :]]
    while int(re.sub('[A-Z]', '', cell_ranges[-1].split(':')[1])) < int(y):
        cell_ranges.append(
            col_names[0] + str(i * offset + 1 + z) + ':' +
            col_names[1:] + str(((i + 1) * offset) + z))
        data.append(df.iloc[i * offset:(i + 1) * offset, :])
        i = i + 1
    cell_ranges[-1] = cell_ranges[-1].split(':')[0] + \
        ':' + col_names[1:] + str(y)

    for cell_range, df in zip(cell_ranges, data):
        cell_list = wks.range(cell_range)
        for i, cell in enumerate(cell_list):
            row = i // n_cols
            col = i % n_cols
            cell.value = serialize(df.iloc[row, col])
        wks.update_cells(cell_list)
