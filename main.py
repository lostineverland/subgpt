import sublime
import sublime_plugin

from funcy.times import iso_ts

class SubgptNewChatCommand(sublime_plugin.WindowCommand):
    """Open a new chat"""
    def run(self, edit):
        # Create a new file (view) in the current window
        new_view = self.window.new_file()

        # Set the syntax file for the new view
        # Replace 'Packages/YourPluginName/YourSyntaxFile.sublime-syntax'
        # with the correct path to your syntax file
        new_view.set_syntax_file('Packages/subgpt/subgpt.sublime-syntax')

        # Optionally, set the name of the new view (not saved)
        new_view.set_name(iso_ts('minutes', local=True) + '.md')

        # Optionally, bring the new view to focus
        self.window.focus_view(new_view)


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
