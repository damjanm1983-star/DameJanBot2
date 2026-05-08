# Push to GitHub Using Personal Access Token

## Problem
GitHub no longer supports password authentication. You need a Personal Access Token (PAT).

## Solution: Use GitHub Personal Access Token

### Step 1: Generate Token (if you don't have one)
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Give it a name: "DamJanBot Push"
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
5. Click "Generate token"
6. **COPY THE TOKEN IMMEDIATELY** (you won't see it again!)

### Step 2: Push Using Token

Run this command with your actual token:

```bash
cd /root/.openclaw/workspace/DamJanBot
git remote set-url origin https://damjanm1983-star:YOUR_TOKEN_HERE@github.com/damjanm1983-star/DameJanBot2.git
git push -u origin main
```

**Replace `YOUR_TOKEN_HERE` with your actual token!**

### Step 3: Reset Remote (after push)
```bash
git remote set-url origin https://github.com/damjanm1983-star/DameJanBot2.git
```

## Alternative: Use SSH Key

If you have an SSH key configured with GitHub:

```bash
cd /root/.openclaw/workspace/DamJanBot
git remote set-url origin git@github.com:damjanm1983-star/DameJanBot2.git
git push -u origin main
```

## Current Status
- ✅ 35 commits ready
- ✅ Repository cleaned
- ✅ .env removed for security
- ❌ Need authentication to push

## After Push
Verify at: https://github.com/damjanm1983-star/DameJanBot2
