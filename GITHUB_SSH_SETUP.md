# GitHub SSH Setup for Private Repository

## 🎯 Purpose

This guide helps you set up SSH key authentication so your production server can pull from your **private GitHub repository**.

---

## 📋 Prerequisites

- Production server running at `15.157.56.64`
- SSH access to production server
- GitHub account with access to `antarpreetsinghk/bella_v3` repository

---

## 🚀 Quick Start

### **Step 1: Run the Setup Script**

```bash
cd /home/antarpreet/Projects/bella_v3
./scripts/setup_github_ssh_on_production.sh
```

### **Step 2: Follow the Interactive Prompts**

The script will:
1. ✅ Ask for your production server username
2. ✅ Check current git configuration
3. ✅ Generate SSH key on production server (if not exists)
4. ✅ Display the public key
5. ✅ Pause for you to add key to GitHub
6. ✅ Test SSH connection to GitHub
7. ✅ Update git remote from HTTPS to SSH
8. ✅ Test git pull

### **Step 3: Add SSH Key to GitHub**

When the script displays the public key:

1. Copy the entire key (starts with `ssh-ed25519...`)
2. Go to: https://github.com/settings/keys
3. Click **"New SSH key"**
4. Fill in:
   - **Title**: `Bella V3 Production Server`
   - **Key type**: `Authentication Key`
   - **Key**: Paste the copied key
5. Click **"Add SSH key"**
6. Return to terminal and press ENTER

### **Step 4: Make Repository Private**

After SSH setup is complete:

1. Go to: https://github.com/antarpreetsinghk/bella_v3/settings
2. Scroll to **"Danger Zone"**
3. Click **"Change visibility"**
4. Select **"Make private"**
5. Type repository name to confirm
6. Click **"I understand, make this repository private"**

### **Step 5: Test Private Repo Access**

```bash
# SSH to production
ssh your-user@15.157.56.64

# Navigate to project
cd /home/antarpreet/Projects/bella_v3

# Test git pull (should work even with private repo!)
git pull origin main
```

---

## 🔍 What the Script Does

### **Behind the Scenes**

1. **Connects to Production Server**
   - Uses SSH to access `15.157.56.64`
   - Navigates to `/home/antarpreet/Projects/bella_v3`

2. **Generates SSH Key**
   - Creates ED25519 key (most secure modern format)
   - Stored at: `~/.ssh/id_ed25519_github_bella`
   - No passphrase (for automated deployments)

3. **Updates SSH Config**
   - Adds GitHub configuration to `~/.ssh/config`
   - Ensures correct key is used for GitHub

4. **Changes Git Remote**
   - **Before**: `https://github.com/antarpreetsinghk/bella_v3.git`
   - **After**: `git@github.com:antarpreetsinghk/bella_v3.git`

5. **Tests Everything**
   - Tests SSH connection: `ssh -T git@github.com`
   - Tests git pull: `git pull origin main`

---

## ✅ Verification

### **Test 1: SSH Connection**

```bash
ssh your-user@15.157.56.64 "ssh -T git@github.com"
```

**Expected output:**
```
Hi antarpreetsinghk! You've successfully authenticated, but GitHub does not provide shell access.
```

### **Test 2: Git Pull**

```bash
ssh your-user@15.157.56.64 "cd /home/antarpreet/Projects/bella_v3 && git pull origin main"
```

**Expected output:**
```
Already up to date.
```

### **Test 3: Deployment Workflow**

```bash
# On local machine - make a test change
echo "# SSH deployment test" >> README.md
git add README.md
git commit -m "test: verify private repo SSH deployment"
git push origin main

# On production - pull the change
ssh your-user@15.157.56.64 "cd /home/antarpreet/Projects/bella_v3 && git pull origin main"
```

**Expected output:**
```
Updating abc1234..def5678
Fast-forward
 README.md | 1 +
 1 file changed, 1 insertion(+)
```

---

## 🔧 Troubleshooting

### **Problem: "Permission denied (publickey)"**

**Cause**: SSH key not added to GitHub or not configured correctly

**Solution**:
```bash
# On production server
ssh -T git@github.com

# Should see:
# "Hi antarpreetsinghk! You've successfully authenticated..."

# If not, check:
1. Key is added to GitHub: https://github.com/settings/keys
2. Copy ENTIRE key including "ssh-ed25519" prefix
3. Wait 1 minute for GitHub to propagate the key
```

### **Problem: "Host key verification failed"**

**Cause**: GitHub's fingerprint not in known_hosts

**Solution**:
```bash
# On production server
ssh-keyscan github.com >> ~/.ssh/known_hosts
```

### **Problem: "Repository not found"**

**Cause**: Either repo is private and SSH key not configured, or repo name is wrong

**Solution**:
```bash
# Check remote URL
git remote -v

# Should show:
# git@github.com:antarpreetsinghk/bella_v3.git

# If wrong, fix it:
git remote set-url origin git@github.com:antarpreetsinghk/bella_v3.git
```

### **Problem: Git pull asks for password**

**Cause**: Still using HTTPS instead of SSH

**Solution**:
```bash
# Check current remote
git remote -v

# If shows https://, change to SSH:
git remote set-url origin git@github.com:antarpreetsinghk/bella_v3.git
```

---

## 🔄 Rollback

If you need to revert to HTTPS (public repo):

```bash
# SSH to production
ssh your-user@15.157.56.64
cd /home/antarpreet/Projects/bella_v3

# Change back to HTTPS
git remote set-url origin https://github.com/antarpreetsinghk/bella_v3.git

# Test
git pull origin main
```

---

## 📊 Before vs After

### **Before (Public Repo + HTTPS)**
```bash
# Git remote
origin  https://github.com/antarpreetsinghk/bella_v3.git

# Deployment
git pull origin main  # Works, no password needed (public repo)
```

### **After (Private Repo + SSH)**
```bash
# Git remote
origin  git@github.com:antarpreetsinghk/bella_v3.git

# Deployment
git pull origin main  # Works, no password needed (SSH key auth)
```

---

## 🎯 Next Steps

After successful setup:

1. ✅ **Make repo private** (if not already done)
2. ✅ **Test deployment workflow** (make commit, pull on production)
3. ✅ **Update deployment docs** (if you have any)
4. 🔄 **Part 2**: Run credential rotation script (coming next)

---

## 🔒 Security Notes

- ✅ ED25519 keys are modern and secure
- ✅ No passphrase for production (needed for automated deploys)
- ✅ SSH key only on production server (not shared)
- ✅ Private key never leaves production server
- ✅ Can revoke key anytime from GitHub settings

---

## 📞 Support

If you encounter issues:

1. Check GitHub SSH key is added: https://github.com/settings/keys
2. Verify SSH connection: `ssh -T git@github.com`
3. Check git remote: `git remote -v`
4. Review script output for error messages

---

**Script Location**: `scripts/setup_github_ssh_on_production.sh`

**Created**: 2025
**Last Updated**: 2025-10-14
