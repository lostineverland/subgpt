import sublime
import sublime_plugin
import json
import urllib.request
import urllib.error

# plug-in dev workaround -->
import sys
sys.path.append('/Users/carlos/code/subgpt/.venv/lib/python3.8/site-packages')
# <-- plug-in dev workaround 

from funcypy.eager.cols import removekey
from funcypy.funcy import pipe
import cligpt
import frontmatter, yaml

from funcypy.times import iso_ts, now

q_delimeter = 'Question:\n---------\n'
a_delimeter = '\n\nAnswer:\n  -------\n'
s_delimeter = '\n\nSummary Keywords'

def get_settings(window):
    settings = sublime.load_settings("subgpt.sublime-setting").to_dict()
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
                    removekey(lambda e: {'api_key', 'log_path'}.issuperset([e])),
                    lambda e: {**e, 'timestamp': iso_ts('minutes')}
                    )
            ))
        # Insert Question marker
        q, a = cligpt.render_response('', '')
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
    def run(self, edit):
        settings = get_settings(self.view.window())
        api_key = ensure_api_key(settings)
        entire_region = sublime.Region(0, self.view.size())
        page = self.view.substr(entire_region)
        md = frontmatter.loads(page)
        messages = list(build_messages(md.content, md.metadata))
        # response = callgpt(messages, md.metadata['model'], api_key)
        # message, model = process_response(reponse)
        # add_response(edit, self.view, message, model)
        self.view.insert(edit, self.view.size(), "\n" + json.dumps(md.metadata) + "\n" + json.dumps(messages, indent=4))
        # self.view.insert(edit, self.view.size(), "\n***" + json.dumps(md.content.split(q_delimeter)) + '***\n')


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
    if q_a := block.split(a_delimeter):
        if a := q_a[1:]:
            a_s = a.split(s_delimeter)
            return q_a[0], a_s[0]
        else:
            return q_a[0], None
    else:
        return None, None


def build_messages(contents, metadata):
    chat = parse_chat(contents, metadata)
    q, a, meta = next(chat)
    if q:
        yield dict(role='system', content=meta.get('role', ''))
        yield dict(role='user', content=q)
        if a: yield dict(role='assistant', content=ans)
        for q, a, meta in chat:
            yield dict(role='system', content=meta.get('role', ''))
            if q: yield dict(role='user', content=q)
            if a: yield dict(role='assistant', content=ans)


def callgpt(messages, model, api_key):
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
    req = urllib.request.Request(endpoint, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            raw_response = response.read()
            response = json.loads(raw_response.decode('utf-8'))
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

def add_response(edit, view, message, model):
    answer_meta = '  ---\n{}\n---\n'.format(yaml.dump(
            model=model,
            timestamp=iso_ts('minutes', local=True)
        ))
    answer = cligpt.render_response('', message)
    i = len(a_delimeter)
    answer = answer[:i] + answer_meta + answer[i+1:]
    view.insert(edit, view.size(), answer)

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
