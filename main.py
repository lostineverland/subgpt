import sublime
import sublime_plugin

class SubgptChatCommand(sublime_plugin.TextCommand):
    """Insert Iso Day"""
    def run(self, edit):
        for region in self.view.sel():
            # Insert the text at the cursor position
            self.view.insert(edit, region.begin(), week())


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
