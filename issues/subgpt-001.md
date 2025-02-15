---
- status: done
---
# Subgpt-001: New File Name

When opening a new chat:
  - create the file (empty file), so that the name and path can be set
  - if the file is closed w/o changes, delete the file
    - this way I can feel free to create any chat at will
    - delete the contents so that it doesn't prompt to save
    - trigger an event
