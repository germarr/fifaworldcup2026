# Tailwind CSS Setup Guide

This project uses Tailwind CSS with PostCSS for the quickgame feature templates. This guide explains how to set up and compile the CSS files.

## Prerequisites

- Node.js and npm installed on your system
- The project cloned to your local machine

## Installation

1. Install all required dependencies:

```bash
npm install
```

This will install:
- `tailwindcss` - The Tailwind CSS framework
- `@tailwindcss/postcss` - PostCSS plugin for Tailwind v4
- `postcss` and `postcss-cli` - PostCSS processor
- `autoprefixer` - Adds vendor prefixes for browser compatibility
- `cssnano` - Minifies CSS for production

## Building the CSS

### Production Build

To compile the Tailwind CSS for production (minified):

```bash
npm run build:css
```

This generates `./static/css/tailwind.output.css` from the source file `./static/css/tailwind.input.css`.

### Development Mode

For development with automatic rebuilding when templates change:

```bash
npm run watch:css
```

This watches for changes in the quickgame templates and rebuilds the CSS automatically.

### Production Build (Explicit)

For an explicit production build with NODE_ENV set:

```bash
npm run build:css:prod
```

## File Structure

```
.
├── tailwind.config.js              # Tailwind configuration
├── postcss.config.js               # PostCSS plugins configuration
├── static/
│   └── css/
│       ├── tailwind.input.css      # Source file (tracked in git)
│       └── tailwind.output.css     # Compiled CSS (not tracked in git)
└── templates/
    ├── quickgame_start.html        # Uses compiled Tailwind CSS
    ├── quickgame_groups.html       # Uses compiled Tailwind CSS
    ├── quickgame_knockout.html     # Uses compiled Tailwind CSS
    └── quickgame_results.html      # Uses compiled Tailwind CSS
```

## Configuration Files

### tailwind.config.js

Configures which files Tailwind should scan for class names:

```javascript
module.exports = {
  content: [
    "./templates/quickgame_start.html",
    "./templates/quickgame_groups.html",
    "./templates/quickgame_knockout.html",
    "./templates/quickgame_results.html",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### postcss.config.js

Configures PostCSS plugins for processing:

```javascript
module.exports = {
  plugins: {
    '@tailwindcss/postcss': {},  // Tailwind CSS processing
    autoprefixer: {},             // Browser vendor prefixes
    cssnano: {                    // Minification
      preset: 'default',
    },
  },
}
```

## Important Notes

1. **The compiled CSS file (`tailwind.output.css`) is not tracked in git** - It's listed in `.gitignore` and must be generated locally or during deployment.

2. **You must run the build command** after cloning the repository and before starting the application.

3. **File size**: The compiled CSS is approximately 5.9KB (minified), much smaller than the CDN version (~300KB).

4. **Template changes**: If you modify the Tailwind classes in any quickgame template, run the build command again to regenerate the CSS with the new utilities.

## Troubleshooting

### Missing CSS file error

If you see styling issues or missing CSS errors:

```bash
npm install
npm run build:css
```

### Changes not appearing

If CSS changes aren't reflecting:

1. Make sure you saved the template file
2. Run `npm run build:css` again
3. Clear browser cache or do a hard refresh (Cmd/Ctrl + Shift + R)

### Build errors

If you encounter build errors:

1. Delete `node_modules` and reinstall:
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   npm run build:css
   ```

2. Verify all dependencies are installed:
   ```bash
   npm list @tailwindcss/postcss postcss postcss-cli autoprefixer cssnano
   ```

## Deployment

For deployment, you have two options:

### Option 1: Build during deployment (Recommended)

Add the build command to your deployment script:

```bash
npm install
npm run build:css
# Then start your application
```

### Option 2: Commit the compiled CSS

If you prefer to commit the compiled CSS:

1. Remove `/static/css/tailwind.output.css` from `.gitignore`
2. Build the CSS: `npm run build:css`
3. Commit the generated file

## Additional Resources

- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [PostCSS Documentation](https://postcss.org/)
- [Tailwind CSS v4 PostCSS Plugin](https://tailwindcss.com/docs/installation/using-postcss)
