
# ##filename=journal.py, edited on 17 Oct 2022 Mon 11:48 AM

import sys
import re
import json
import os
from datetime import date
import datetime

ITEMS = 'items'
TITLE = 'title'
SUBTITLE = 'subtitle'
ARG = 'arg'
VARIABLES = 'variables'
MESSAGE = 'message'
MESSAGE_TITLE = 'message_title'
LINK = 'link'
ALFREDWORKFLOW = 'alfredworkflow'
JOURNAL = os.getenv('journal')
ENTRY = 'entry'
VAR_LINK = 'var_link'

def output_json(a_dict):
    sys.stdout.write(json.dumps(a_dict))


def get_last_line_date():
    pattern = '(?P<prefix>ts\[)(?P<date>\S+)'

    lines = []
    with open(os.path.expanduser(JOURNAL), 'r') as file:
        for line in file:
            lines.append(line)

    lines = [line for line in lines if len(line.strip()) > 0]
    if len(lines) > 0:
        last_line = lines[-1]
        m = re.search(pattern, last_line)
        if m:
            return m.group('date')

    return ''

def _today():
    return date.today()


def get_today_weekday():
    return _today().weekday()

def get_year_month_day(d):
    return d.strftime('%Y-%m-%d')

def get_today(return_year_month_day = True):
    today = _today()
    if return_year_month_day:
        return get_year_month_day(today)
    return today

def write_new_date_marker(today, file_path = os.path.expanduser(JOURNAL), prefix = ''):
    today_string = today.strftime('%Y-%m-%d %a')
    line = f'\n\n{prefix} {today_string}\n'
    with open(file_path, 'a+') as file:
        file.write(line)

def mark_new_date(file_path = os.path.expanduser(JOURNAL)):
    last_line_date = get_last_line_date()
    today = get_today(False)
    if last_line_date != get_year_month_day(today):
        write_new_date_marker(today, file_path)


def do():
    action = sys.argv[1]
    result = ''
    message = ''
    message_title = ''

    result = 'OK'
    if action == 'mark_new_date':
        mark_new_date()
        message = 'marked new date'
        message_title = 'Notice'
        output = {ALFREDWORKFLOW: {
            ARG: result,
            VARIABLES: {MESSAGE: message,
                        MESSAGE_TITLE: message_title,
                        }}}
        output_json(output)

do()

