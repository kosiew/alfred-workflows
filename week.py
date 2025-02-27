
# ##filename=week.py, edited on 24 Feb 2022 Thu 09:15 AM

import re
import json
import sys
import webbrowser
from urllib.parse import urlparse

pattern = r'(?P<prefix>- )(?P<desc>.*?)(\[.+\])(\()(?P<url>http.+?)(\))'
standup_line_pattern = r'(?P<prefix>- )(?P<line_type>\[.+\]) (?P<desc>.*?)(?P<ampersand>\[&&\])?(\()?(?P<url>http[^)]+)?(?P<close_bracket>\))? +(?P<timestamp>ts\[.+\])'
standup_line_re = re.compile(standup_line_pattern)

link_re = re.compile(pattern)

timestamp_pattern = r'(?P<desc>.*?)(?P<ts>ts\[.*)'
timestamp_re = re.compile(timestamp_pattern)

translate_dict = {
  'cld.wthms.co': 'd.pr/i',
}

def find_urls(string):

    # findall() has been used
    # with valid conditions for urls in string
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?]))"
    url = re.findall(regex,string)
    return [x[0] for x in url]




def get_url_netlocs(urls):
    results = []

    for url in urls:
        netloc = urlparse(url).netloc
        results.append(netloc)

    unique_netlocs = set(results)
    return ', '.join(unique_netlocs)

def translate(text):
    global translate_dict

    _text = text
    for k, v in translate_dict.items():
        _text = _text.replace(k, v)

    return _text


def get_lines(text):
    lines = text.split('\n')
    lines = [line for line in lines if len(line) >= 0]

    return lines

def remove_timestamp(line):
    m = timestamp_re.search(line)
    if m:
        desc = m.group('desc')
    else:
        desc = line
    return desc.strip()

def get_line_items(line):
    global link_re
    _line = line.strip()
    m = link_re.search(_line)
    if m:
        prefix = m.group('prefix')
        desc = m.group('desc')
        url = m.group('url')
        desc = desc.strip()
    else:
        desc = remove_timestamp(_line)
        url = None

    return desc, url

def get_linked_line(desc, urls):
    if len(urls) == 1:
        url = urls[0]
        if url:
            line = '- ' + '[' + desc + ']' + '(' + url + ')'
        else:
            line = desc
    elif len(urls) > 1:
        _urls = []
        for i, url in enumerate(urls):
            if url:
                _url = '[#' + str(i+1) + '](' + url + '})'
                _urls.append(_url)
        line = '- ' +  desc + ' ' + ', '.join(_urls)


    return line


def dictionary_add_item(d, key, value):
    if len(key) > 0:
        i = d.get(key)
        if i:
            i.append(value)
        else:
            d[key] = [value]

    return d

def remove_href_li(link):
    return link.replace('https://href.li/?', '')



def get_daily_lines(text):
    lines = get_lines(text)
    _lines = []

    for line in lines:
        global standup_line_re
        m = standup_line_re.search(line)
        if m:
            prefix = m.group('prefix');
            desc = m.group('desc')
            url = m.group('url')
            if url:
                url = remove_href_li(url)
            desc = desc.strip()
            line = f'{prefix}{desc}'
            if url:
                line = f'{line} - {url}'
            _lines.append(line)

    return _lines

def get_linked_lines(text):
    lines = get_lines(text)
    _lines = []
    descs = {}
    for line in lines:
        desc, url = get_line_items(line)
        descs = dictionary_add_item(descs, desc, url)

    summarized_descs = []

    for line in lines:
        desc, url = get_line_items(line)
        if desc and url:
            if desc not in summarized_descs:
                urls = descs.get(desc)

                _line = get_linked_line(desc, urls)
                summarized_descs.append(desc)
            else:
                _line = None
        else:
            _line = get_linked_line(desc, [url])
        if _line is not None:
            _lines.append(_line)

    return _lines

def _remove_timestamps_lines(block):
    r = re.compile('(?P<pre>.*)(?P<timestamp>ts\[.*M\])(?P<post>.*)')
    lines = get_lines(block)
    _lines = []
    for line in lines:
        m = r.search(line)
        if m:
            pre = m.group('pre')
            post = m.group('post')
            _line = '{0} {1}'.format(pre, post.strip())
            _lines.append(_line)
        else:
            _lines.append(line)

    return _lines

def remove_timestamps(block):
    _lines = _remove_timestamps_lines(block)
    return '\n'.join(_lines)



def get_linked_entries(text):
    lines = get_linked_lines(text)
    return '\n'.join(lines)

def get_daily_entries(text):
    lines = get_daily_lines(text)
    return '\n'.join(lines)


def output_json(a_dict):
    sys.stdout.write(json.dumps(a_dict))


# abbreviate from first letters of each word
def get_first_letter_or_entire_number(w):
    try:
        i = int(w)
    except ValueError as ve:
        return w[0]
    return w

def get_abbreviation(text):
    words = text.split()
    first_letters = [get_first_letter_or_entire_number(word) for word in words]
    result = ''.join(first_letters)
    return result

def do():
    query = sys.argv[1]
    clipboard_contents = query

    abbreviation = get_abbreviation(clipboard_contents)

    message = '->{0}'.format(abbreviation)
    output = {"alfredworkflow": {
        "arg": abbreviation,
        "variables": {"message": message}}}
    sys.stdout.write( json.dumps (output))

def do():
    action = sys.argv[1]
    result = ''
    message = ''
    message_title = 'Abbreviated'

    result = 'OK'
    if action == 'abbreviate':
        query = sys.argv[2]
        clipboard_contents = query

        abbreviation = get_abbreviation(clipboard_contents)
        message = '->{0}'.format(abbreviation)
        output = {"alfredworkflow": {
            "arg": abbreviation,
            "variables": {"message": message, "message_title":
                          message_title}}}

        output_json(output)
    elif action == 'daily_standup':
        query = sys.argv[2]
        clipboard_contents = query

        abbreviation = get_daily_entries(clipboard_contents)

        message = '->{0}'.format(abbreviation)
        output = {"alfredworkflow": {
            "arg": abbreviation,
            "variables": {"message": message, "message_title":
                          message_title}}}
        output_json(output)
    elif action == 'weekly_update':
        query = sys.argv[2]
        clipboard_contents = query

        abbreviation = get_linked_entries(clipboard_contents)

        message = '->{0}'.format(abbreviation)
        output = {"alfredworkflow": {
            "arg": abbreviation,
            "variables": {"message": message, "message_title":
                          message_title}}}
        output_json(output)
    elif action == 'remove_timestamp':
        query = sys.argv[2]
        clipboard_contents = query

        abbreviation = remove_timestamps(clipboard_contents)
        message = '->{0}'.format(abbreviation)
        output = {"alfredworkflow": {
            "arg": abbreviation,
            "variables": {"message": message, "message_title":
                          message_title}}}
        output_json(output)
    elif action == 'new_droplr':
        query = sys.argv[2]
        clipboard_contents = query

        translated = translate(clipboard_contents)
        message = '{0}->{1}'.format(clipboard_contents, translated)
        output = {"alfredworkflow": {
            "arg": translated,
            "variables": {"message": message, "message_title":
                          message_title}}}
        output_json(output)
    elif action == 'open_urls':
        query = sys.argv[2]
        urls = find_urls(query)
        for url in urls:
            webbrowser.open(url)
        url_count = len(urls)
        url_netlocs = get_url_netlocs(urls)

        if url_count > 1:
            suffix = ' links'
        else:
            suffix = ' link'
        message = 'opened ' + url_netlocs + suffix
        message_title = 'Opened links'
        output = {"alfredworkflow": {
            "arg": urls,
            "variables": {"message": message, "message_title":
                          message_title}}}
        output_json(output)







do()
