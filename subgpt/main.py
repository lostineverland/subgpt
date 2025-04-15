import sublime
import sublime_plugin
import os, sys, re
import json
import urllib.request
import urllib.error
import threading
import functools

# plug-in dependencies workaround -->
sys.path.append(os.path.join(os.path.dirname(__file__), 'deps'))
# <-- plug-in dependencies workaround 

from funcypy.eager.cols import removekey as remove_dict_key, removevalnone
from funcypy.cols import flatten, nestten, removekey
from funcypy.funcy import pipe, has, juxt, rcomp, partial, complement
from funcypy import seqs
from funcypy.times import iso_ts, now
from funcypy.monitor import json_serializer
import frontmatter, yaml
from .costs import calc_cost


q_delimeter = 'Question:\n---------\n'
a_delimeter = 'Answer:\n-------\n'
s_delimeter = 'Summary Keywords'

def get_settings(window):
    settings = sublime.load_settings("subgpt.sublime-settings").to_dict()
    project_data = window.project_data() or {}
    project_settings = project_data.get('subgpt', {})
    if project_settings:
        project_settings.update(dict(base_path=window.folders()[0]))
    return {**settings, **project_settings}

class SubgptNewChatCommand(sublime_plugin.WindowCommand):
    """Open a new chat"""
    def run(self):
        # Load settings
        settings = get_settings(self.window)

        # Create a new file (view) in the current window
        new_view = self.window.new_file()

        # Set the syntax file for the new view
        # Replace 'Packages/YourPluginName/YourSyntaxFile.sublime-syntax'
        # with the correct path to your syntax file
        new_view.set_syntax_file('Packages/subgpt/subgpt.sublime-syntax')

        # Optionally, set the name of the new view (not saved) 
        file_name = iso_ts('minutes', local=True).replace(":", "-") + '.md'
        file_path = setpath(settings)
        new_view.retarget(os.path.join(file_path, file_name))
        # new_view.run_command('save')

        # Insert initial MD frontmatter
        yaml_frontmatter = "---\n{}---\n".format(
            yaml.dump(
                pipe(settings,
                    remove_dict_key(has('api_key', 'log_path', 'word_wrap', 'spell_check', 'base_path')),
                    lambda e: {**e, 'timestamp': iso_ts('minutes')}
                    )
            ))
        # Insert Question marker
        q, a = render_response('', '')
        render_view(new_view, yaml_frontmatter + '\n' + q[:-2])

        # Optionally, bring the new view to focus
        self.window.focus_view(new_view)

def render_view(view, contents, pos=0):
    run_cmd = class_to_func(SubgptRenderViewCommand)
    view.run_command(run_cmd, dict(contents=contents, pos=pos))

class SubgptRenderViewCommand(sublime_plugin.TextCommand):
    'Render contents from a window to a view'
    def run(self, edit, contents, pos=0):
        # Insert the text at the beginning of the view (position 0)
        self.view.insert(edit, pos, contents)


class SubgptSendQueryCommand(sublime_plugin.TextCommand):
    def run(self, edit, debug=False):
        # Start the request in a new thread
        thread = threading.Thread(target=self.send_query, kwargs=dict(edit=edit, debug=debug))
        thread.start()

    def send_query(self, edit, debug):
        settings = get_settings(self.view.window())
        api_key = ensure_api_key(settings)
        entire_region = sublime.Region(0, self.view.size())
        page = self.view.substr(entire_region)
        md = frontmatter.loads(page)
        messages = list(build_messages(md.content, md.metadata))
        if messages[-1].get('role') == 'user' or debug:
            status = AsyncStatusMessage(self.view, 'OpenAI', ['GPT.', 'GPT..', 'GPT...'], interval=500)
            response = callgpt(messages, md.metadata, api_key, debug=debug)
            status.clear()
            if debug or response.get('err'):
                render_view(
                    self.view,
                    "\n" + json.dumps(dict(
                        md_metadata=md.metadata,
                        messages=messages,
                        settings=settings,
                        ), indent=2),
                    self.view.size())
                render_view(
                    self.view,
                    "\nquery object\n" + json.dumps(response, indent=2) + '\n',
                    self.view.size())
            else:
                message, model = process_response(response)
                contents = format_response(message, model, response, {**settings, **md.metadata})
                render_view(
                    self.view,
                    contents,
                    self.view.size())
        else:
            print('noop')


class SubgptLinkCommand(sublime_plugin.TextCommand):
    """Insert Iso Day"""
    def run(self, edit):
        for region in self.view.sel():
            # Insert the text at the cursor position
            self.view.insert(edit, region.begin(), today())


class SubgptSummaryCommand(sublime_plugin.TextCommand):
    """Insert Iso Day"""
    def run(self, edit):
        for region in self.view.sel():
            # Insert the text at the cursor position
            self.view.insert(edit, region.begin(), now())


class AsyncStatusMessage:
    def __init__(self, view, key, messages, interval=1000):
        self.view = view
        self.key = key
        self.messages = messages
        self.interval = interval
        self.index = 0
        self.active = True
        self.animate()

    def animate(self):
        if not self.active:
            return
        message = self.messages[self.index % len(self.messages)]
        self.view.set_status(self.key, message)

        # Schedule the next update
        self.index += 1
        sublime.set_timeout_async(self.animate, self.interval)

    def clear(self):
        self.active = False
        self.view.erase_status(self.key)


def setpath(config):
    base_path = os.path.expandvars(os.path.expanduser(config.get('log_path', 'GPT_logs')))
    home = os.path.expandvars('$HOME')
    if base_path.startswith('./'):
        base_path = os.path.join(config.get('base_path', ''), base_path)
    elif not base_path.startswith(home):
        base_path = os.path.join(home, base_path)
    log_path = os.path.join(
        base_path,
        iso_ts('years', local=True),
        iso_ts('months', local=True))
    os.makedirs(
        log_path,
        exist_ok=True)
    return log_path

def parse_chat(contents, metadata):
    for block in contents.split(q_delimeter)[1:]:
        q, a = parse_block(block)
        yield q, a, metadata

def parse_block(block):
    'handle question/answer/summary block'
    return map(dict(zip(
            # split string by a_delimeter then by s_delimeter and concat into a single list
                range(3),
                seqs.concat(*(i.split(s_delimeter) for i in block.split(indent(2, a_delimeter)[:-2]))),
            )).get,
        # because I always want to return 2 values make sure they're allocated with None when
        # not enough are present
        range(2))

def build_messages(contents, metadata):
    chat = parse_chat(contents, metadata)
    q, a, meta = next(chat, [None, None, None])
    if q:
        # allow for a dictionary entry to define role
        if isinstance(role := meta.get('role', ''), dict):
            yield dict(role=list(role.keys())[0], content=list(role.vals())[0])
        # allow for a list entry to define role (for extra instructions to the `developer` role)
        if isinstance(role := meta.get('role', ''), list):
            yield dict(role='developer', content='- ' + '\n- '.join(meta.get('role')))
        elif role := meta.get('role', ''): 
            yield dict(role='developer', content=meta.get('role'))
        yield dict(role='user', content=clean_white_space(q))
        if a: yield dict(role='assistant', content=clean_white_space(frontmatter.loads(dedent(2, a)).content))
        for q, a, meta in chat:
            if q: yield dict(role='user', content=clean_white_space(q))
            if a: yield dict(role='assistant', content=clean_white_space(frontmatter.loads(dedent(2, a)).content))


def callgpt(messages, meta, api_key, debug=False):
    endpoint = 'https://api.openai.com/v1/chat/completions'
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(api_key)
    }
    data = json.dumps(removevalnone({
                 "model": meta.get('model'),
                 "reasoning_effort": meta.get('reasoning_effort'),
                 "messages": messages,
                 "temperature": meta.get('temperature')
               })).encode('utf-8')
    if debug: return dict(endpoint=endpoint, data=json.loads(data), headers=headers)
    req = urllib.request.Request(endpoint, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            raw_response = response.read()
            response = json.loads(raw_response.decode('utf-8'))
            return response
    except urllib.error.URLError as e:
        return dict(endpoint=endpoint, data=json.loads(data), headers=headers, err=json.loads(json.dumps(e, default=json_serializer)))

def process_response(resp):
    message = resp['choices'][0]['message']
    model = resp['model']
    return message, model

def ensure_api_key(settings):
    api_key = settings.get('api_key')
    assert api_key, "An api_key must be provided"
    assert "#######" not in api_key, "A valid api_key must be provided, make sure to replace it in your settings file"
    return api_key

def render_response(query, answer, metadata=None):
    u_ = lambda s: '-' * len(s) # underline function
    q = 'Question:'
    a = 'Answer:'
    rendered_q = f'\n{q}\n{u_(q)}\n{query}\n\n'
    if metadata:
        rendered_a = f'\n\n{a}\n{u_(a)}\n---\n{yaml.dump(metadata)}---\n\n{answer}\n\n\n'
    else:
        rendered_a = f'\n\n{a}\n{u_(a)}\n{answer}\n\n\n'
    return rendered_q, rendered_a

def filter_response_meta(*fields):
    has_substr = partial(lambda substr, key: substr in key)
    wild_cards = lambda key: rcomp(juxt(*[has_substr(i) for i in key.split('*')]), all)
    verbatim = partial(lambda substr, key: substr == key)
    return rcomp(juxt(
                *map(wild_cards, filter(has_substr('.*'), fields)),
                *map(verbatim, filter(complement(has_substr('.*')), fields))),
                any)

def format_response(message, model, response, settings):
    meta = dict(
        model=model,
        cost=calc_cost(settings.get('model'), response),
        timestamp=iso_ts('minutes', local=True))
    if settings.get('include_meta'):
        meta = dict(
            response=pipe(response,
                    functools.partial(flatten, follow_list=True),
                    removekey(filter_response_meta(
                        'rechoices.*.index',
                        'choices.*.message.role',
                        'choices.*.message.content',
                        'created',
                        'id',
                        'model',
                        'system_fingerprint',
                        'usage.completion_tokens_details.*',
                        )),
                    nestten,
                    dict
                ),
            **meta
        )
    q, answer = render_response('', message['content'], meta)
    indented_answer ='\n\n' + indent(2, answer)
    return indented_answer + q

def indent(n, s):
    return '\n'.join(map(lambda s: ' ' * n + s, s.split('\n')))

def dedent(n, s):
    return '\n'.join(map(lambda s: s[n:], s.split('\n')))


def status_update(view, key, messages):
    sublime.set_timeout_async(lambda: self.view.erase_status(key), 0)

def clean_white_space(s):
    start, end = (lambda i: (i[0], i[-1]))(s.split())
    start_index = s.find(start)
    end_index = s.rfind(end) + len(end)
    return s[start_index:end_index]

def class_to_func(cls):
    # Convert PascalCase to snake_case Command Name
    name = cls.__name__
    s1 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    return s1.lower().rsplit('_', 1)[0]

def display(s):
    return """
        <body id=display-line>
            <style>
                p {
                    margin-top: 20;
                    max-height: 80;
                }
                a {
                    font-family: system;
                    font-size: 1.05rem;
                }
            </style>
            <p>{s}</p>
        </body>
    """.replace('{s}', s)
