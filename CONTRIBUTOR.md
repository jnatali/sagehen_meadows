## Git Workflow for Contributors

Welcome! This repository uses a **branch-based workflow** to keep our `main` branch stable.  
Please follow these steps when working on your assigned issue.

Key Points
- Work in your branch, it's your safe space to make changes with confidence
- Commit to your branch often and push to github; these two steps backup your work. Do it every work session! Don't worry about how often or not, I'm not paying attention.
- Write short, clear commit messages.
- Don't push directly to main. We'll do this when the work is complete or needs to be shared. If you try to push to main, your request should be blocked.

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
git checkout main
git pull origin main
git fetch origin
```

#### 3. Switch to your assigned branch ####
On Github Desktop, click the **"Current Branch"** dropdown and select `your issue's` branch, e.g. `19-canopy-temp`  

OR with command line:  
```
git checkout <issue#-name-of-your-branch>
```

#### 4. Edit scripts and data as needed. #### 
- Use your preferred editor and save your changes locally.

#### 5. Commit your changes and push to github #### 
- Commit and push often! It's a backup of your work. No matter what happens to your computer, your edits will be uploaded to github.
- Commit any chunk of work that you wouldn't want to lose.
- Commit at the end of each work session.
- Your commit description should help you differentiate your commits. I tend to have a list of short sentences. Each starts with verb then offers a brief (i.e. 1-3 word) reason for the change: "Added function to..., Fixed loop in...."

On Github Desktop, go to the **"Changes"** tab on the left, write a short summary of your commit with a description for details, then click **"Commit"** to <issue#-name-of-your-branch>. Then click **"Push origin"** at the top bar to upload your changes to github. 

OR with command line:
```
git add .
git commit -m "Short description of what you changed"
git push origin <issue#-name-of-your-branch>
```

#### 6. Open a **Pull Request** to merge `your issue's branch` into `main` ####
Do this once the work in your branch is fully operational and ready to integrate into the stable code base
The request will need to be reviewed before it's integrated into `main` 

- Go to the github repository at https://github.com/jnatali/sagehen_meadows
- Click **"Compare & pull request"** for your branch.
- Important: Make sure the base branch is your issue branch, not main.
- Add a short description of what you did.
- Click **"Create pull request"**



