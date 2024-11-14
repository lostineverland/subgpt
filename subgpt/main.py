import sublime
import sublime_plugin
import os
import json
import urllib.request
import urllib.error

# plug-in dev workaround -->
import sys
sys.path.append('/Users/carlos/code/subgpt/.venv/lib/python3.8/site-packages')
# <-- plug-in dev workaround 

from funcypy.eager.cols import removekey
from funcypy.funcy import pipe, has
from funcypy import seqs
from funcypy.times import iso_ts, now
import cligpt
import frontmatter, yaml


q_delimeter = 'Question:\n---------\n'
a_delimeter = 'Answer:\n-------\n'
s_delimeter = 'Summary Keywords'

def get_settings(window):
    settings = sublime.load_settings("subgpt.sublime-settings").to_dict()
    project_settings = window.project_data().get('settings', {})
    return {**settings, **project_settings}

class SubgptNewChatCommand(sublime_plugin.WindowCommand):
    """Open a new chat"""
    def run(self):
        # Create a new file (view) in the current window
        new_view = self.window.new_file()

        # Set the syntax file for the new view
        # Replace 'Packages/YourPluginName/YourSyntaxFile.sublime-syntax'
        # with the correct path to your syntax file
        new_view.set_syntax_file('Packages/subgpt/subgpt.sublime-syntax')

        # Optionally, set the name of the new view (not saved)
        new_view.set_name(iso_ts('minutes', local=True).replace(":", "-") + '.md')

        # Insert initial MD frontmatter
        yaml_frontmatter = "---\n{}---\n".format(
            yaml.dump(
                pipe(self.window,
                    get_settings,
                    removekey(has('api_key', 'log_path')),
                    lambda e: {**e, 'timestamp': iso_ts('minutes')}
                    )
            ))
        # Insert Question marker
        q, a = render_response('', '')
        new_view.run_command('subgpt_create_new_chat', {
            "contents": yaml_frontmatter + '\n' + q[:-2]
        })

        # Optionally, bring the new view to focus
        self.window.focus_view(new_view)


class SubgptCreateNewChatCommand(sublime_plugin.TextCommand):
    def run(self, edit, contents):
        # Insert the text at the beginning of the view (position 0)
        self.view.insert(edit, 0, contents)


class SubgptSendQueryCommand(sublime_plugin.TextCommand):
    def run(self, edit, debug=False):
        settings = get_settings(self.view.window())
        api_key = ensure_api_key(settings)
        entire_region = sublime.Region(0, self.view.size())
        page = self.view.substr(entire_region)
        md = frontmatter.loads(page)
        messages = list(build_messages(md.content, md.metadata))
        if messages[-1].get('role') == 'user' or debug:
            response = callgpt(messages, md.metadata['model'], api_key, debug=debug)
            if not debug:
                message, model = process_response(response)
                add_response(edit, self.view, message, model, response)
            else:
                self.view.insert(edit, self.view.size(),
                    "\n" + json.dumps(md.metadata) + \
                    "\n" + json.dumps(messages, indent=4) + \
                    "\n" + json.dumps(settings, indent=4)
                )
                self.view.insert(edit, self.view.size(), "\nquery object\n" + json.dumps(response, indent=2) + '\n')
        else:
            print('noop')


class SubgptRenderQueryCommand(sublime_plugin.TextCommand):
    pass

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


class SubgptDisplayLineCommand(sublime_plugin.TextCommand):
    """exploring the sublime api"""
    def run(self, edit):
        lines = self.view.lines(self.view.sel()[0])
        contents = display('/n'.join(map(self.view.substr, lines)))
        line = self.view.line(self.view.sel()[0])
        content = self.view.substr(line)
        self.view.show_popup(contents, max_width=600, max_height=7000)


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
        yield dict(role='system', content=meta.get('role', ''))
        yield dict(role='user', content=q)
        if a: yield dict(role='assistant', content=frontmatter.loads(dedent(2, a)).content)
        for q, a, meta in chat:
            if q: yield dict(role='user', content=q)
            if a: yield dict(role='assistant', content=frontmatter.loads(dedent(2, a)).content)


def callgpt(messages, model, api_key, debug=False):
    endpoint = 'https://api.openai.com/v1/chat/completions'
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(api_key)
    }
    data = json.dumps({
             "model": model,
             "messages": messages,
             "temperature": 0.7
           }).encode('utf-8')
    if debug: return dict(endpoint=endpoint, data=json.loads(data), headers=headers)
    print('Querying OpenAI...', flush=True)
    req = urllib.request.Request(endpoint, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            raw_response = response.read()
            response = json.loads(raw_response.decode('utf-8'))
            print('Querying done')
            return response
    except urllib.error.URLError as e:
        raise e

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

def add_response(edit, view, message, model, response):
    q, answer = render_response('', message['content'], dict(
                model=model,
                timestamp=iso_ts('minutes', local=True)
            ))
    indented_answer ='\n\n' + indent(2, answer)
    view.insert(edit, view.size(), indented_answer + q)

def indent(n, s):
    return '\n'.join(map(lambda s: ' ' * n + s, s.split('\n')))

def dedent(n, s):
    return '\n'.join(map(lambda s: s[n:], s.split('\n')))

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
