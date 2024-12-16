# Objective

A ChatGPT plug-in for sublime text.

# Usage

*Start a new chat*:
- MacOS: `cmd`+`opt`+`n`
- Linux: `ctrl`+`alt`+`n`
- Windows: `ctrl`+`alt`+`n`

*Send query to chatGPT*:
- MacOS: `opt`+`enter`
- Linux: `alt`+`enter`
- Windows: `alt`+`enter`

# Build & Install

```sh
# from subgpt/subgpt
➜  subgpt git:(main) ✗ rm ../dist/subgpt.sublime-package
➜  subgpt git:(main) ✗ zip --exclude .DS_Store -r ../dist/subgpt.sublime-package .
➜  subgpt git:(main) ✗ cp ../dist/subgpt.sublime-package ~/Library/Application\ Support/Sublime\ Text/Installed\ Packages/
```

