## Git Workflow for Contributors

Welcome! This repository uses a **branch-based workflow** to keep our `main` branch stable.  
Please follow these steps when working on your assigned issue.

Tools Needed
- You can use [Github Desktop](https://github.com/apps/desktop) application to manage this workflow, it's easy to learn and has everything you need. See https://desktop.github.com/download/
- Alternatively, you can use git via the command line in a terminal window. That's more advanced, but can be quick and powerful. You can invest in installing and learning this if you want. I provide commands below, but can't offer much help beyond that.

Key Points
- Work in your branch, it's your safe space to make changes with confidence
- Commit to your branch often and push to github; these two steps backup your work. Do it every work session! Don't worry about how often or not, I'm not paying attention.
- Write short, clear commit messages.
- Don't push directly to main. We'll do this when the work is complete or needs to be shared. If you try to push to `main`, your request should be blocked.


### Workflow Steps
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
Do this once the work in your branch is fully operational (i.e. it's complete) and ready to integrate into the stable code base. 
The request will need to be reviewed before it's integrated into `main` 

- Go to the github repository at https://github.com/jnatali/sagehen_meadows
- Click **"Compare & pull request"** for your branch.
- Important: Make sure the base branch is your issue branch, not main.
- Add a short description of what you did.
- Click **"Create pull request"**

## More Git Resources
- [Basic Git Guide](https://github.com/git-guides), says it's "everything you need to know"
- [GitHub Documentation](https://docs.github.com/en) includes a "Get Started" guide. You'll mainly need to work with repositories, branches, commits and pull requests, but at a very simple level.
- [Intro to Github online course](https://github.com/skills/introduction-to-github)
- [90-min GitHub Fundamentals Workshop](https://dlab-berkeley.github.io/dlab-workshops/workshop/git-fundamentals/) from UCB's D-Lab

### Using Git with Visual Studio
- [Visual Studio site on github integration](https://visualstudio.microsoft.com/vs/github/)
- [Working with GitHub in VS Code tutorial](https://code.visualstudio.com/docs/sourcecontrol/github)

