## Git Workflow for Contributors

Welcome! This repository is a place where we store all our data, scripts and output. Github has version control tools to help us keep our files safe and manage a project with multiple contributors. 

This repository uses a **branch-based workflow** to keep our `main` branch stable.

If you have questions, feel free to comment in your github issue (or email) to ask Jen, @jnatali.

Please share any suggestions on how to improve these guidelines!

### New to Git?
See the "For Newbies" section below.

### Guidelines for using Git issues, branches and check-ins
- For reminders on how to use git, see on **Git Workflow Steps** section below.
- Work on your assigned *issue* and associated *branch* (which should start with the issue # and be linked/visible in the issue itself)
- When naming files, use file naming conventions (defined in sections below).
- RAW data should never be modified by scripts. Scripts should transform RAW data into derived products (e.g. a new .csv). Treat RAW data as strictly read-only.
- When possible, results should be reproducible by re-running scripts rather than manually editing files. This supports reproducible science!
- At the start of each work session, use git to Pull or "*Fetch Origin*". This will make sure you're capturing any updates from others working on the same branch.
- Commit to your branch often and push to github; these two steps backup your work. Do it every work session! Don't worry about how often or not, I'm not alerted or paying attention.
- Write short, clear commit messages. Explain what changed and why. Don't just write "update".

Good examples:

```
Add groundwater interpolation function
Fix date parsing for logger files
Update canopy temperature documentation
```

- A PULL REQUEST (PR) into the main branch can happen at any time. You can use the Pull Request to help track changes against the 'main' branch. Once your task is completed, rename your Pull Request as "Ready to Review". See the "What 'Ready for Review' Means" section below for details.
- Once you submit a PR, we'll review together, merge the code into the `main` branch, then close the issue and the sub-branch. We'll do this when the work is complete or needs to be shared, which should happen within 1-4 weeks. We'll try to keep issues focused and reviews frequent. Reviews are a standard software dev practice and should help us all become more familiar with code, solve problems and smooth collaboration.
- Our python code should follow [PEP 8](https://peps.python.org/pep-0008/) guidelines. Highlights are listed in "PEP-8 Highlights" section below. Other .py files written by Jen can be templates for how we structure files and use comments/documentation. Ask if an example would help.

### File Naming Conventions
- Use all lower case in filenames. One exception: when using names to mark the status of data files (see keyword status markers below, under data file naming conventions)
- Never use spaces in filenames, use underscore to separate words; e.g. `soil_survey.csv`
- The first word should indicate the main content or action, the second word a distinguishing characteristic; e.g. `well_dimensions.csv` is a list of wells and their dimensions, `process_raw_logger.py` processes raw logger data.
- When in doubt, look at other files in the directory and try to follow the pattern that's already there.

#### Data Filename Status Markers
* _RAW = data straight from the field (notebook or recording); also stash these files in a "RAW" directory
* _WORK = data that's being processed (in progress), not yet tested
* _FULL = data that's been fully aggregated, processed and tested, but NOT yet completely stable or finalized
* _STABLE = data that's been processed and validated, appears stable but may be some minor changes; waiting for final release of the project (i.e. when paper, data and scripts published)
* _FINAL = data that's been processed and validated, no more changes expected in this release of the research project

### Pull Requests: What "Ready for Review" Means
A pull request is ready for review when:
- The code runs successfully on representative data.
- Any known bugs or limitations have been documented in the Pull Request description.
- New functions include comments or docstrings explaining their purpose, inputs, and outputs.
- The contributor has reviewed their own changes before requesting review.
- Temporary debugging code, test files, and commented-out code have been removed or clearly identified.

Code does not need to be perfect before review. Reviews are expected to identify improvements and catch issues. However, code should be functional and understandable before requesting review.

### PEP-8 Python Style Guide Highlights

This project generally follows PEP 8. Some important conventions:

#### Naming

* `snake_case` for variables, functions, and file names

```python
groundwater_depth
load_covariate_data()
```

* `UPPER_CASE` for constants

```python
CM_PER_INCH = 2.54
```

#### Functions

Functions should do one clearly defined task. I like to start function names with a verb.

Prefer:

```python
load_groundwater_data()
validate_well_ids()
calculate_gdd()
```

over large functions that perform many unrelated operations.

#### Documentation

All public functions should include a docstring describing:

* Purpose
* Parameters
* Return value

Example:

```python
def calculate_gdd(tmin, tmax, base_temp):
    """
    Calculate growing degree days.

    Parameters
    ----------
    tmin : float
        Minimum daily temperature.
    tmax : float
        Maximum daily temperature.
    base_temp : float
        Base temperature threshold.

    Returns
    -------
    float
        Growing degree days.
    """
```

#### Imports

Place imports at the top of the file.

Group imports in this order:

1. Standard library
2. Third-party packages
3. Project modules

Example:

```python
import os
from pathlib import Path

import numpy as np
import pandas as pd

from src.validation import validate_well_ids
```

#### Line Length

Aim for lines shorter than 88 characters.

Break long statements across multiple lines for readability.

#### Comments

Write comments that explain *why*, not *what*.

Good:

```python
# Logger clocks drift by up to several hours during winter.
```

Less helpful:

```python
# Add 1 to x.
x = x + 1
```

#### Avoid Absolute Paths

Do not hard-code local computer paths.

Avoid:

```python
"/Users/jen/Documents/project/data.csv"
```

Prefer project-relative paths or configuration files. See other .py files for examples of how to do this.


## For Newbies: Getting Started with Git and Github
Please follow these steps when working on your assigned "issue" or task. You can find all issues on the  menu above, and eash one should have an assigned branch. 

#### Tools Needed
- You can use [Github Desktop](https://github.com/apps/desktop) application to manage this workflow, it's easy to learn and has everything you need. Download it here --> https://desktop.github.com/download/
- Alternatively, you can use git via the command line in a terminal window. That's more advanced, but can be quick and powerful. You can invest in installing and learning this if you want. I provide commands below, but can't offer much help beyond that.

#### Key Points
- Work in *your issue's branch*. It's your safe space to make changes with confidence. If you're not sure what branch to use, please ask. I don't mind, I want your code and results to be backed up.
- Commit to your branch often and push to github; these two steps backup your work. Do it every work session! Don't worry about how often or not, I'm not paying attention.
- Write short, clear commit messages.
- A PULL REQUEST (PR) into the main branch can happen at any time. You can use the Pull Request to help track changes against the 'main' branch. Once your task is completed, rename your Pull Request as "Ready to Review". We'll review together, merge the code, then close the issue and the sub-branch. We'll do this when the work is complete or needs to be shared, which should happen within a 1-4 weeks. We'll try to keep issues focused and reviews frequent.

### Git Workflow Steps
#### 1. *First time only:* Clone the repository ####  

On Github Desktop, goto **File -> Clone Repository** and enter the repository URL, then select your local directory for the project.  

OR with command line:
```
git clone https://github.com/jnatali/sagehen_meadows.git
cd sagehen_meadows
```

#### 2. Update your local repo at the start of each work session ####

On Github Desktop, check that you're in the `main` branch, then click **"Fetch Origin"** to pull the latest changes from github  

OR with command line:
```
git pull
```

#### 3. Switch to your assigned branch ####
On Github Desktop, click the **"Current Branch"** dropdown and select `your issue's` branch. If you don't have a branch, create one. Use a meaningful name that relates to the github issue  you're working on, i.e. use the pattern <#-brief_descriptive_phrase>, e.g. `19-canopy-temp`.

OR with command line:  
```
git checkout <issue#-name-of-your-branch>
```

#### 4. Edit scripts and data as needed. #### 
- Use your preferred editor and save your changes locally.

#### 5. Commit your changes to your branch and push to github #### 
- Commit and push often! It's a backup of your work. No matter what happens to your computer, your edits will be uploaded to github.
- Commit any chunk of work that you wouldn't want to lose.
- Commit at the end of each work session.
- Your commit description should help you differentiate your commits. I tend to have a list of short sentences. Each starts with verb then offers a brief (i.e. 1-3 word) reason for the change: "Added function to..., Fixed loop in...."

On Github Desktop, go to the **"Changes"** tab on the left, write a short summary of your commit with a description for details, then click **"Commit"** to <issue#-name-of-your-branch>. Then click **"Push origin"** at the top bar to upload your changes to github. 

OR with command line:
```
git status
```
confirm the branch (should be your issue's branch) and what has changed
```
git add <filenames or directories that relate to this commit>
git commit -m "Short description of what you changed"
git push
```

#### 6. Open a **Pull Request** to merge `your issue's branch` into `main` ####
You can open a Pull Request as soon as you start working on your issue, just name it as a DRAFT. 

Once work in your branch is fully operational (i.e. it's complete) and ready to integrate into the stable code base, we'll review it together before we inegrate into the `main` branch. To signal that the branch is ready, rename your Pull Request to READY FOR REVIEW.

To start a Pull Request:
- Go to the github repository at https://github.com/jnatali/sagehen_meadows
- Click **"Compare & pull request"** for your branch.
- Important: Make sure the base branch is your issue branch, not main.
- Add a short description of what you did.
- Click **"Create pull request"**

## More Git Resources
If you find anything useful (or not), please share so we can keep these guidelines fresh and focused!
- [Basic Git Guide](https://github.com/git-guides), says it's "everything you need to know"
- [GitHub Documentation](https://docs.github.com/en) includes a "Get Started" guide. You'll mainly need to work with repositories, branches, commits and pull requests, but at a very simple level.
- [Intro to Github online course](https://github.com/skills/introduction-to-github)
- [90-min GitHub Fundamentals Workshop](https://dlab-berkeley.github.io/dlab-workshops/workshop/git-fundamentals/) from UCB's D-Lab
- [Software Carpentry Git Lessons](https://swcarpentry.github.io/git-novice/?utm_source=chatgpt.com)

### Using Git with Visual Studio
- [Visual Studio site on github integration](https://visualstudio.microsoft.com/vs/github/)
- [Working with GitHub in VS Code tutorial](https://code.visualstudio.com/docs/sourcecontrol/github)
- 
## Coding Guidelines

### Python: Use PEP 8 Style Guide
[PEP 8](https://peps.python.org/pep-0008/) supports consistent, readable code. Please follow this standard.

### R: Use Tidyverse Style Guide
[Tidyverse Style Guide](https://style.tidyverse.org/) supports consistent, readable code. Please follow this standard.
