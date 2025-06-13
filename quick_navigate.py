
# ##filename=quick_navigate.py, edited on 11 Feb 2021 Thu 11:35 AM

import sys
import re
import json
import os


pattern = '(.*:\/\/)?(?P<domain>[^/]+)(/)?(.*)'
domain_re = re.compile(pattern)
FILENAME = 'paths.json'
PREVIOUS_FILENAME = 'paths_old.json'
ITEMS = 'items'
TITLE = 'title'
SUBTITLE = 'subtitle'
URL = 'url'
ARG = 'arg'
VARIABLES = 'variables'
MESSAGE = 'message'
MESSAGE_TITLE = 'message_title'
DOMAIN = 'domain'
ALFREDWORKFLOW = 'alfredworkflow'
WP_ADMIN = 'wp-admin'
WP_LOGIN = 'wp-login.php'
LOCALHOST = 'localhost'
VAR_DOMAIN = '{var:domain}'
VAR_ID = '{var:id}'

def get_wordpress_domain(url):
    tokens = url.split('/')

    if WP_ADMIN in tokens or WP_LOGIN in tokens:
        result = []
        for token in tokens:
            if ':' in token:
                continue
            if len(token) == 0:
                continue
            if WP_ADMIN == token:
                break
            if WP_LOGIN == token:
                break
            result.append(token)
        return '/'.join(result)

    for token in tokens:
        if token.startswith(LOCALHOST):
            return token

    tokens.reverse()

    tokens = [token for token in tokens if '.php?' not in token]

    for token in tokens:
        _tokens = token.split('.')
        if len(_tokens) > 1:
            last_token = _tokens[-1]
            m = re.match('[a-zA-Z]{2,}', last_token)
            if m and m.group() == last_token and last_token.lower() != 'php':
                return token
    return None


def get_domain(a_string):
    global domain_re
    m = domain_re.search(a_string)
    if m:
        return m.group(DOMAIN)
    return a_string

def get_json_data(filename=FILENAME):
    with open(filename) as f:
        data = json.load(f)

    return data

def get_json_items(filename=FILENAME):
    data = get_json_data()
    items = data[ITEMS]
    return items

def get_items_count(filename=FILENAME):
    items = get_json_items()
    return len(items)

def update_script_filter_url(url, description):
    data = get_json_data()

    _items = data['items']
    initial_length = len(_items)
    _items = _delete_script_filter_url(_items, url)
    items = _add_script_filer_url(_items, url, description)
    new_items_length = len(items)
    assert new_items_length == initial_length
    data[ITEMS] = items
    save_json(data)
    return new_items_length

def _delete_script_filter_url(items, url):
    initial_length = len(items)
    for i, item in enumerate(items):
        if item['arg'] == url:
            items.remove(item)
            break
    assert len(items) < initial_length
    return items

def delete_script_filter_url(url):
    data = get_json_data()

    _items = data[ITEMS]
    items = _delete_script_filter_url(_items, url)
    data[ITEMS] = items
    save_json(data)
    return len(items)

def _add_script_filer_url(items, url, description):
    initial_length = len(items)
    d = {TITLE: description,
         SUBTITLE: description,
         URL: url,
         ARG: url,
         VARIABLES: {
            URL: url}
         }
    items.append(d)
    assert len(items) > initial_length

    return items

def add_script_filter_url(url, description):
    data = get_json_data()

    _items = data[ITEMS]
    items = _add_script_filer_url(_items, url, description)
    data[ITEMS] = items

    save_json(data)
    return len(items)

def save_json(data, filename=FILENAME):
    with open(filename, 'w') as f:
        json.dump(data, f)

def get_description_for_url(url):
    items = get_json_items()

    for item in items:
        if item[ARG] == url:
            return item[TITLE]

def check_url_for_var_id(url):
    if VAR_ID in url:
        return 'Y'
    return 'N'

def substitute_var_id(url, id):
    result = url.replace(VAR_ID, id)
    return result

def output_json(a_dict):
    sys.stdout.write(json.dumps(a_dict))


def get_items_urls(items):
    l = []
    for item in items:
        l.append(item[URL])
    return l

def _migrate_data(old_filename=PREVIOUS_FILENAME, new_filename=FILENAME):
    old_items = get_json_items(old_filename)
    new_items = get_json_items(new_filename)

    old_items_count = len(old_items)

    old_urls = get_items_urls(old_items)
    for item in new_items:
        if item[URL] not in old_urls:
            old_items.append(item)
    d = {ITEMS: old_Items}
    save_json(d)
    return old_items_count


def migrate_data(old_filename=PREVIOUS_FILENAME, new_filename=FILENAME):
    old_items_count = _migrate_data(old_filename, new_filename)
    message = 'Retained {0} entries from previous version'.format(
        old_items_count)
    return message


def do():
    action = sys.argv[1]
    domain = ''
    result = ''
    message = ''
    message_title = ''

    if action == 'load_data':
        query = sys.argv[2].lower()
        items = get_json_items()

        l = []
        for item in items:
            if query in item[TITLE].lower():
                l.append(item)
        d = {'items': l}
        output_json(d)

    else:
        if action == 'get_url_for_domain':
            chrome_url = sys.argv[2]
            url_from_script_filter = os.environ[URL]

            domain = get_wordpress_domain(chrome_url)
            result = url_from_script_filter.replace(VAR_DOMAIN, domain)
            message = domain + result
            items_count = get_items_count()
            message_title = '{0} paths'.format(items_count)
        elif action == 'get_script_filter_for_domain':
            chrome_url = sys.argv[2]
            domain = get_wordpress_domain(chrome_url)
            url = chrome_url.replace(domain, VAR_DOMAIN)
            url = url.replace('http:', 'https:')
            message = 'url is ' + url
            result = url
            message_title = domain

        elif action == 'with_domain':
            url_from_script_filter = sys.argv[2]
            domain = get_domain(os.environ[DOMAIN])

            result = url_from_script_filter.replace(VAR_DOMAIN, domain)
            message = 'url is {0}'.format(result)
            items_count = get_items_count()
            message_title = '{0} paths'.format(items_count)

        elif action == 'add_script_filter':
            description = sys.argv[2]
            script_filter_url = os.environ[URL]
            message = 'added {0}'.format(script_filter_url)
            items_count = add_script_filter_url(script_filter_url, description)
            message_title = '{0} paths'.format(items_count)

        elif action == 'delete_script_filter':
            script_filter_url = sys.argv[2]
            items_count = delete_script_filter_url(script_filter_url)
            message = 'deleted {0}'.format(script_filter_url)
            message_title = '{0} paths'.format(items_count)

        elif action == 'update_script_filter':
            description = sys.argv[2]
            script_filter_url = os.environ[URL]
            message = 'updated {0}'.format(script_filter_url)
            items_count = update_script_filter_url(script_filter_url, description)
            message_title = '{0} paths'.format(items_count)

        elif action == 'get_description_for_url':
            script_filter_url = sys.argv[2]
            description = get_description_for_url(script_filter_url)

            result = description
            message = description
            items_count = get_items_count()
            message_title = '{0} paths'.format(items_count)

        elif action == 'check_for_var_id':
            script_filter_url = sys.argv[2]
            result = check_url_for_var_id(script_filter_url)
            message = 'check {0} for {1}'.format(script_filter_url, VAR_ID)
            items_count = get_items_count()
            message_title = '{0} paths'.format(items_count)

        elif action == 'substitute_var_id':
            id = sys.argv[2]
            script_filter_url = os.environ[URL]
            result = substitute_var_id(script_filter_url, id)
            message = result
            message_title = 'Quick Navigate with id'
            items_count = get_items_count()
            message_title = '{0} paths. {1}'.format(items_count, message_title)

        elif action == 'migrate_data':
            message_title = 'Data migration'
            message = migrate_date()

        output = {ALFREDWORKFLOW: {
            ARG: result,
            VARIABLES: {MESSAGE: message,
                        MESSAGE_TITLE: message_title,
                        DOMAIN: domain}}}
        output_json(output)

do()

'''

  31-Oct-20 Sat 04:26:59 PM
  added load_data

  added migrate_data option but not tested

'''
