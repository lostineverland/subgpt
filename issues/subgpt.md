# Subgpt

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
