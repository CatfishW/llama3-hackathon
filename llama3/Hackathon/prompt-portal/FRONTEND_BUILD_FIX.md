# Frontend Build Fix - Quick Manual Steps

If you're getting TypeScript build errors, follow these steps:

## Step 1: Fix TypeScript Configuration

Replace the content of `tsconfig.json` with:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": false,
    "allowSyntheticDefaultImports": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist"]
}
```

## Step 2: Clean and Reinstall Dependencies

```bash
# Remove old dependencies
rm -rf node_modules package-lock.json dist

# Reinstall with legacy peer deps
npm install --legacy-peer-deps

# Try building
npm run build
```

## Step 3: Alternative Commands

If the above doesn't work, try:

```bash
# Force install
npm install --force

# Build with specific flags
npm run build -- --force

# Or use yarn instead
yarn install
yarn build
```

## Step 4: Check Node Version

Make sure you're using Node.js 16 or higher:

```bash
node --version
# Should show v16.x.x or higher
```

If you have an older version, update Node.js and try again.

## Step 5: Manual TypeScript Check

Test TypeScript configuration:

```bash
npx tsc --noEmit
```

If this fails, there are syntax errors in your TypeScript files that need to be fixed.

## For Ubuntu/Linux Users

If you're on the server and getting permission errors:

```bash
# Make sure you have proper permissions
sudo chown -R $USER:$USER .

# Install Node.js if missing
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Then try the build steps above
```
