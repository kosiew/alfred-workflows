
# ##filename=weekly_note.py, edited on 02 Mar 2023 Thu 10:06 AM

import sys
from pathlib import Path

import re
import json
import os
from datetime import date
import datetime
SOURCE_DIR = Path("/Users/kosiew/GitHub/python-scripts")
sys.path.insert(0, str(SOURCE_DIR))

print("AFTER insert sys.path[0:3]:", sys.path[:3], file=sys.stderr)
print("Expect inserted[0]:", sys.path[0], file=sys.stderr)
print("alias_llm exists?:", (SOURCE_DIR / "alias_llm.py").exists(), file=sys.stderr)
import alias_llm as _llm

ITEMS = 'items'
TITLE = 'title'
SUBTITLE = 'subtitle'
ARG = 'arg'
VARIABLES = 'variables'
MESSAGE = 'message'
MESSAGE_TITLE = 'message_title'
LINK = 'link'
ALFREDWORKFLOW = 'alfredworkflow'
NOTEBOOK = os.getenv('notebook')
IGNORE_LINK = 'xxx'
ENTRY = 'entry'
VAR_LINK = 'var_link'
GET_CLIPBOARD_AS_LINK = 'ccc'

def output_json(a_dict):
    sys.stdout.write(json.dumps(a_dict))

def remove_href_li(link):
    return link.replace('https://href.li/?', '')

def get_var_link(link, entry):
    message = ''
    var_link = ''
    modified_entry = entry

    if entry.endswith(IGNORE_LINK):
        message_title = 'Ignoring clipboard'
        message = f'entry ends with {IGNORE_LINK}'
        modified_entry = entry[:-len(IGNORE_LINK)]
    elif entry.endswith(GET_CLIPBOARD_AS_LINK):
        _entry = entry[:-len(GET_CLIPBOARD_AS_LINK)]
        link = os.getenv('clipboard')
        return get_var_link(link, _entry)
    else:
        if link.startswith('http'):
            link = remove_href_li(link)
            var_link = '[&&]({0})'.format(link)
            message = link
            message_title = f'Using {link}'
        else:
            message_title = 'No http link in clipboard'
            message = link

    return message_title, message, var_link, modified_entry

def copy_file_to(from_file, to_file):

    f1 = open(to_file, 'a+')
    f2 = open(from_file, 'r+')

    days_from_monday = get_today_weekday()
    if days_from_monday == 0:
        days_from_monday = 7
    last_monday = _today() - datetime.timedelta(days=days_from_monday)
    last_monday = last_monday.strftime('%Y-%m-%d')
    f1.write(f'\nNEW WEEK - {last_monday}\n\n')
    f1.write(f2.read())

# relocating the cursor of the files at the beginning
    f1.seek(0)
    f2.truncate(0)

# closing the files
    f1.close()
    f2.close()


def get_last_line_date():
    pattern = '(?P<prefix>ts\[)(?P<date>\S+)'

    lines = []
    with open(os.path.expanduser(NOTEBOOK), 'r') as file:
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

def write_new_date_marker(today, file_path = os.path.expanduser(NOTEBOOK), prefix = ''):
    today_string = today.strftime('%Y-%m-%d %a')
    line = f'\n\n{prefix} {today_string}\n'
    with open(file_path, 'a+') as file:
        file.write(line)

def mark_new_date(file_path = os.path.expanduser(NOTEBOOK)):
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
    if action == 'copy_to_history':

        source_file = os.path.expanduser(sys.argv[2])
        destination_file = os.path.expanduser(sys.argv[3])

        message = 'to ' + destination_file
        message_title = 'Copied {0}'.format(source_file)

        copy_file_to(source_file, destination_file)

        output = {ALFREDWORKFLOW: {
            ARG: result,
            VARIABLES: {MESSAGE: message,
                        MESSAGE_TITLE: message_title
                        }}}
        output_json(output)
    elif action == 'get_var_link':
        mark_new_date()
        link = sys.argv[2]
        entry = os.getenv('entry')
        message_title, message, var_link, modified_entry = get_var_link(link, entry)
        prompt = (
            "Generate a concise summary of the following journal entry."
            "Ensure it captures the main theme of the entry."
        )
        summary = _llm.process(prompt, modified_entry)
        # result appears in Alfred debug and is useful for debugging
        result = var_link
        # entry = os.getenv('entry')
        output = {ALFREDWORKFLOW: {
            ARG: result,
            VARIABLES: {MESSAGE: message,
                        MESSAGE_TITLE: message_title,
                        ENTRY: f"modified_entry/n summary:{summary}/n",
                        VAR_LINK: var_link
                        }}}
        output_json(output)

do()

