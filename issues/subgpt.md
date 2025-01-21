# Subgpt

# Links

- [GPT: Plugin Window](../GPT_logs/2024/2024-11/2024-11-09-sublime-plugin-window.md)
- [Package Control](https://packagecontrol.io/docs)
- [Sublime Docs](https://www.sublimetext.com/docs/index.html)
- [Sublime API Ref](https://www.sublimetext.com/docs/api_reference.html)

# Logs
## 2024-W47
- There's a need to split out the composable components out of the classes.
  - each subclass of these should be very small:
    - sublime_plugin.WindowCommand
    - sublime_plugin.TextCommand
  - window and view objects can be passed
  - the edit objects need a bit more thought
  - but things like these should be composable functions
    - read/parse window contents
    - inserts
    - identify scope
- In order to render things properly on pages I may want to include tags in the messages that get passed around
## 2025-W03
- I'm going to keep an `easy` and an `advance` version, where the difference is in the default values.
  - This is so that I can give the girls a version that "just works" 
